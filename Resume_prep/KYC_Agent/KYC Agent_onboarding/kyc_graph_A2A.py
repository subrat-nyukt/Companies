"""
KYC Onboarding Agent — LangGraph Supervisor Pipeline with A2A Protocol
=====================================================================
Workflow (5 nodes) implementing:
  1. Agent-to-Agent (A2A) Message Envelope tracing & schema contracts.
  2. Structured validation with Pydantic schemas.
  3. Self-correction retry loops inside the validator node.
  4. Circuit Breakers (Graceful Fallback) for parser/LLM timeouts and failures.

Run:
    python kyc_graph_A2A.py --image path/to/id.jpg --doc path/to/form.pdf
"""

import asyncio
import json
import logging
import argparse
import datetime
from uuid import uuid4
from typing import TypedDict, Optional, Dict, Any, List

from pydantic import BaseModel, Field, ValidationError
from langgraph.graph import StateGraph, END
from core.config import settings
from core.client import azure_clients
from vision.analysis import vision_analyzer
from rag.ingest import document_ingestor
from prompts.v1.agent_prompt import SYSTEM_PROMPT, VALIDATION_PROMPT
from tools.aml_screening import check_aml_database

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# NVIDIA NEMO GUARDRAILS CONFIGURATION & MOCK FALLBACK
# ──────────────────────────────────────────────────────────────────────────────

try:
    from nemoguardrails import RailsConfig, LLMRails
    NEMO_AVAILABLE = True
except ImportError:
    NEMO_AVAILABLE = False
    
    # Mock fallback classes to keep the script 100% runnable without the package
    class RailsConfig:
        @classmethod
        def from_content(cls, colang_content: str, yaml_content: str):
            return cls()

    class LLMRails:
        def __init__(self, config):
            pass
        async def generate_async(self, prompt: str) -> str:
            # Mock behavior: return empty to indicate no policy violation triggered
            return ""

# 1. Define Colang boundaries to block compliance bypass or document forgery attempts
colang_rules = """
define user ask about compliance bypass
  "how can I bypass the KYC process?"
  "can you skip the AML check?"
  "help me forge a document"
  "can we use fake data for verification?"

define bot refuse compliance bypass
  "POLICY VIOLATION: I am configured to enforce regulatory compliance rules. I cannot assist in bypassing security controls, document parsing, or sanctions checks."

define flow compliance bypass attempt
  user ask about compliance bypass
  bot refuse compliance bypass
"""

yaml_config = """
models:
  - type: main
    engine: openai
    model: gpt-4o
"""

def init_nemo_guardrails() -> Optional[LLMRails]:
    if not NEMO_AVAILABLE:
        logger.warning("[NeMo Guardrails] 'nemoguardrails' package is not installed. Initializing in MOCK mode.")
        return LLMRails(None)
    try:
        config = RailsConfig.from_content(colang_content=colang_rules, yaml_content=yaml_config)
        return LLMRails(config)
    except Exception as e:
        logger.error(f"[NeMo Guardrails] Failed to initialize: {e}. Falling back to MOCK.")
        return LLMRails(None)

nemo_rails = init_nemo_guardrails()



# ──────────────────────────────────────────────────────────────────────────────
# 1. A2A PROTOCOL SCHEMAS & CONTRACTS
# ──────────────────────────────────────────────────────────────────────────────

class A2AMessageEnvelope(BaseModel):
    """
    Standardized message envelope for all Agent-to-Agent (A2A) communications.
    Enforces trace IDs, timestamps, and routing/validation states.
    """
    trace_id: str
    sender_agent: str
    target_agent: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    payload: Dict[str, Any]
    validation_status: str = "valid"  # "valid" | "malformed" | "invalid"
    error_message: Optional[str] = None


class KYCValidationOutputSchema(BaseModel):
    """
    Strict validation contract for the Validator Agent's output.
    Any output from the validator LLM must parse into this schema.
    """
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0)
    fields: Dict[str, Any] = Field(..., description="Key-value pairs of extracted KYC info (e.g. name, id_number, dob)")
    reason: str = Field(..., description="Rationale for the confidence score and triage decision")


# ──────────────────────────────────────────────────────────────────────────────
# 2. GRAPH STATE (Shared Memory State Monad)
# ──────────────────────────────────────────────────────────────────────────────

class KYCState(TypedDict):
    # Inputs
    image_path: Optional[str]
    doc_path: Optional[str]

    # Extracted data (wrapped in payloads)
    image_data: Optional[Dict[str, Any]]
    doc_data: Optional[Dict[str, Any]]

    # Validation output
    validation_result: Optional[str]   # raw LLM response
    confidence_score: float            # 0.0 – 1.0
    extracted_fields: Dict[str, Any]   # parsed KYC fields (name, dob, id_no…)

    # Decision
    decision: str                      # "approved" | "hitl_review" | "pending"
    hitl_reason: str                   # reason for escalation (if any)

    # AML Check Result
    aml_result: Optional[Dict[str, Any]]

    # Routing & Tracking
    route: List[str]                   # which parser nodes to run
    trace_id: str                      # global tracking id
    trace_history: List[Dict[str, Any]] # A2A audit log trail


def log_a2a_message(state: KYCState, sender: str, target: str, payload: Any, status: str = "valid", error: Optional[str] = None) -> Dict[str, Any]:
    """Helper to generate and trace-log a standardized A2A Message Envelope."""
    envelope = A2AMessageEnvelope(
        trace_id=state.get("trace_id", "unknown"),
        sender_agent=sender,
        target_agent=target,
        payload=payload,
        validation_status=status,
        error_message=error
    )
    logger.info(f"[A2A Trace] {sender} -> {target} | Status: {status.upper()} | ID: {envelope.trace_id}")
    return envelope.dict()


# ──────────────────────────────────────────────────────────────────────────────
# 3. NODE: SUPERVISOR (Orchestration entry)
# ──────────────────────────────────────────────────────────────────────────────

def supervisor(state: KYCState) -> KYCState:
    """Route the payload and initialize the A2A tracing session."""
    trace_id = state.get("trace_id") or f"tx_{uuid4().hex[:8]}"
    route = []
    if state.get("image_path"):
        route.append("image_parser")
    if state.get("doc_path"):
        route.append("doc_parser")

    if not route:
        raise ValueError("No image_path or doc_path provided to supervisor.")

    history = list(state.get("trace_history") or [])
    
    # Pack initial routing event
    envelope = log_a2a_message(
        {"trace_id": trace_id}, 
        sender="supervisor", 
        target="orchestrator", 
        payload={"route": route}
    )
    history.append(envelope)

    logger.info(f"[Supervisor] Dispatching route: {route} | Trace ID: {trace_id}")
    return {
        **state,
        "trace_id": trace_id,
        "route": route,
        "decision": "pending",
        "confidence_score": 0.0,
        "extracted_fields": {},
        "hitl_reason": "",
        "trace_history": history
    }


# ──────────────────────────────────────────────────────────────────────────────
# 4. NODE: IMAGE PARSER (With Circuit Breaker)
# ──────────────────────────────────────────────────────────────────────────────

async def image_parser(state: KYCState) -> KYCState:
    """Call Azure Vision to extract image data, wrapped in an A2A envelope with a timeout circuit breaker."""
    logger.info(f"[ImageParser] Processing: {state['image_path']}")
    history = list(state.get("trace_history") or [])
    
    try:
        # Wrap API call in timeout circuit breaker (15 seconds)
        result = await asyncio.wait_for(
            vision_analyzer.process_document(state["image_path"]),
            timeout=15.0
        )
        if result is None:
            raise ValueError("Azure Vision returned None or empty response")
            
        envelope = log_a2a_message(state, sender="image_parser", target="validator", payload=result)
        history.append(envelope)
        return {**state, "image_data": result, "trace_history": history}

    except Exception as e:
        # Circuit Breaker Trips: Handle error gracefully, direct to HITL review, and log invalid trace status
        error_msg = f"Image Parser Circuit Breaker Tripped: {str(e)}"
        logger.error(f"[ImageParser] {error_msg}")
        
        envelope = log_a2a_message(state, sender="image_parser", target="validator", payload={}, status="malformed", error=error_msg)
        history.append(envelope)
        
        return {
            **state,
            "image_data": {},
            "decision": "hitl_review",
            "hitl_reason": error_msg,
            "trace_history": history
        }


# ──────────────────────────────────────────────────────────────────────────────
# 5. NODE: DOCUMENT PARSER (With Circuit Breaker)
# ──────────────────────────────────────────────────────────────────────────────

async def doc_parser(state: KYCState) -> KYCState:
    """Call Azure Form Recognizer, wrapped in an A2A envelope with a timeout circuit breaker."""
    logger.info(f"[DocParser] Processing: {state['doc_path']}")
    history = list(state.get("trace_history") or [])
    
    try:
        # Wrap API call in timeout circuit breaker (15 seconds)
        result = await asyncio.wait_for(
            document_ingestor.parse_document(state["doc_path"]),
            timeout=15.0
        )
        if result is None:
            raise ValueError("Form Recognizer returned None or empty response")
            
        envelope = log_a2a_message(state, sender="doc_parser", target="validator", payload=result)
        history.append(envelope)
        return {**state, "doc_data": result, "trace_history": history}

    except Exception as e:
        # Circuit Breaker Trips
        error_msg = f"Doc Parser Circuit Breaker Tripped: {str(e)}"
        logger.error(f"[DocParser] {error_msg}")
        
        envelope = log_a2a_message(state, sender="doc_parser", target="validator", payload={}, status="malformed", error=error_msg)
        history.append(envelope)
        
        return {
            **state,
            "doc_data": {},
            "decision": "hitl_review",
            "hitl_reason": error_msg,
            "trace_history": history
        }


# ──────────────────────────────────────────────────────────────────────────────
# 6. NODE: VALIDATOR (With A2A Contract validation & self-correction retry loop)
# ──────────────────────────────────────────────────────────────────────────────

async def validator(state: KYCState) -> KYCState:
    """
    Validates parsed KYC data using GPT-4o. Integrates:
      1. Inputs verified from predecessor A2A message payloads.
      2. Self-correction loop (max 2 retries) checking schema formatting via Pydantic.
      3. Global validation circuit breaker.
    """
    # If a circuit breaker already tripped in a prior node, skip validation execution
    if state.get("decision") == "hitl_review" and "Circuit Breaker" in state.get("hitl_reason", ""):
        logger.warning("[Validator] Downstream circuit breaker is active. Skipping validation.")
        return state

    history = list(state.get("trace_history") or [])
    
    # Verify input data payloads from A2A history
    image_envelope = next((h for h in history if h["sender_agent"] == "image_parser"), None)
    doc_envelope = next((h for h in history if h["sender_agent"] == "doc_parser"), None)
    
    image_payload = image_envelope["payload"] if image_envelope else {}
    doc_payload = doc_envelope["payload"] if doc_envelope else {}
    
    combined_context = json.dumps({
        "image_data": image_payload,
        "doc_data": doc_payload,
    }, indent=2)

    prompt = VALIDATION_PROMPT.format(extracted_data=combined_context)

    # Function calling tool description
    aml_tool = {
        "type": "function",
        "function": {
            "name": "check_aml_database",
            "description": "Screens a person's name and ID number against AML sanctions lists (OFAC, UN, UAE Central Bank)",
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {
                        "type": "string",
                        "description": "Full legal name extracted from the ID document"
                    },
                    "id_number": {
                        "type": "string",
                        "description": "National ID or passport number"
                    }
                },
                "required": ["full_name", "id_number"]
            }
        }
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    max_retries = 2
    retry_count = 0
    raw_output = ""
    parsed_output = None
    aml_result = None

    try:
        # Run NeMo Guardrail checks on the prompt to detect compliance bypass or forgery attempts
        if nemo_rails:
            logger.info("[Validator] Evaluating prompt using NVIDIA NeMo Guardrails...")
            guard_resp = await nemo_rails.generate_async(prompt=prompt)
            if "POLICY VIOLATION" in guard_resp:
                logger.warning("[Validator] NeMo Guardrails triggered! Compliance bypass attempt detected.")
                envelope = log_a2a_message(state, sender="nemo_guardrails", target="decision", payload={"response": guard_resp}, status="invalid", error="Compliance bypass policy violation")
                history.append(envelope)
                return {
                    **state,
                    "confidence_score": 0.0,
                    "hitl_reason": f"NeMo Guardrail Refusal: {guard_resp}",
                    "decision": "hitl_review",
                    "trace_history": history
                }

        while retry_count <= max_retries:
            logger.info(f"[Validator] Invoking LLM (Attempt {retry_count + 1}/{max_retries + 1})...")
            
            # GPT-4o Call
            response = await azure_clients.llm.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=messages,
                tools=[aml_tool] if retry_count == 0 else [],  # Call tools only on initial attempt
                tool_choice="auto" if retry_count == 0 else "none",
                temperature=0.1
            )
            
            response_message = response.choices[0].message
            
            # Executing database lookups (AML Screening)
            if response_message.tool_calls and retry_count == 0:
                tool_call = response_message.tool_calls[0]
                args = json.loads(tool_call.function.arguments)
                
                logger.info(f"[Validator] AML Tool Call executed for: {args.get('full_name')}...")
                aml_result = await check_aml_database(
                    name=args.get("full_name"),
                    id_number=args.get("id_number")
                )
                
                messages.append(response_message)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(aml_result)
                })
                
                # Fetch final decision after tool call
                final_response = await azure_clients.llm.chat.completions.create(
                    model=settings.azure_openai_deployment_name,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                raw_output = final_response.choices[0].message.content
            else:
                raw_output = response_message.content

            # A2A Contract validation: Check output against KYCValidationOutputSchema Pydantic model
            try:
                raw_json = json.loads(raw_output)
                parsed_output = KYCValidationOutputSchema(**raw_json)
                
                logger.info("[Validator] A2A schema contract validation SUCCESS.")
                break  # Validation passed, exit loop
                
            except (json.JSONDecodeError, ValidationError) as e:
                retry_count += 1
                error_details = str(e)
                logger.warning(f"[Validator] Validation failed (Attempt {retry_count}): {error_details}")
                
                # Log the parsing failure to trace history
                envelope = log_a2a_message(state, sender="validator", target="validator_self", payload={"raw_output": raw_output}, status="malformed", error=error_details)
                history.append(envelope)
                
                if retry_count <= max_retries:
                    # Request self-correction
                    messages.append({"role": "assistant", "content": raw_output})
                    messages.append({
                        "role": "user",
                        "content": f"The output format was invalid. Error: {error_details}. Please correct the formatting and re-generate the JSON matching the required Pydantic contract (containing 'confidence', 'fields', and 'reason')."
                    })
                else:
                    # Retries exhausted
                    raise ValueError(f"Self-correction loop exhausted. Schema validation failed: {error_details}")

        # Post-validation processing
        confidence = parsed_output.confidence
        extracted_fields = parsed_output.fields
        hitl_reason = parsed_output.reason

        # Handle AML screening matches (hard override to confidence = 0.0)
        if aml_result and aml_result.get("is_match"):
            logger.warning(f"[Validator] AML Sanctions match found: {aml_result['match_detail']}")
            confidence = 0.0
            hitl_reason = f"AML MATCH: {aml_result['match_detail']} (List: {aml_result.get('list', 'Unknown')})"

        envelope = log_a2a_message(state, sender="validator", target="decision", payload={
            "confidence": confidence,
            "fields": extracted_fields,
            "reason": hitl_reason,
            "aml_result": aml_result
        })
        history.append(envelope)

        return {
            **state,
            "validation_result": raw_output,
            "confidence_score": confidence,
            "extracted_fields": extracted_fields,
            "hitl_reason": hitl_reason,
            "aml_result": aml_result,
            "trace_history": history
        }

    except Exception as e:
        # Circuit Breaker Trips
        error_msg = f"Validator Circuit Breaker Tripped: {str(e)}"
        logger.error(f"[Validator] {error_msg}")
        
        envelope = log_a2a_message(state, sender="validator", target="decision", payload={}, status="invalid", error=error_msg)
        history.append(envelope)
        
        return {
            **state,
            "validation_result": None,
            "confidence_score": 0.0,
            "extracted_fields": {},
            "hitl_reason": error_msg,
            "decision": "hitl_review",
            "trace_history": history
        }


# ──────────────────────────────────────────────────────────────────────────────
# 7. NODE: DECISION
# ──────────────────────────────────────────────────────────────────────────────

def decision(state: KYCState) -> KYCState:
    """Evaluate decision parameters and wrap final output payload for database/HITL routing."""
    history = list(state.get("trace_history") or [])
    
    # If a circuit breaker tripped downstream
    if state.get("decision") == "hitl_review":
        logger.warning(f"[Decision] Downstream circuit breaker triggered. Escalating to HITL: {state.get('hitl_reason')}")
        envelope = log_a2a_message(state, sender="decision", target="hitl_queue", payload={"action": "escalate", "reason": state["hitl_reason"]})
        history.append(envelope)
        return {**state, "trace_history": history}

    threshold = settings.confidence_threshold
    score = state["confidence_score"]

    if score >= threshold:
        logger.info(f"[Decision] AUTO-APPROVED (score={score:.2f} >= {threshold})")
        decision_val = "approved"
        envelope = log_a2a_message(state, sender="decision", target="database", payload={"action": "write_to_db", "fields": state["extracted_fields"]})
    else:
        logger.warning(f"[Decision] HITL REQUIRED (score={score:.2f} < {threshold}) — reason: {state['hitl_reason']}")
        decision_val = "hitl_review"
        envelope = log_a2a_message(state, sender="decision", target="hitl_queue", payload={"action": "escalate", "fields": state["extracted_fields"], "reason": state["hitl_reason"]})

    history.append(envelope)
    return {**state, "decision": decision_val, "trace_history": history}


# ──────────────────────────────────────────────────────────────────────────────
# 8. ROUTING & GRAPH CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

def route_after_supervisor(state: KYCState) -> List[str]:
    return state["route"]


def build_kyc_graph():
    graph = StateGraph(KYCState)

    # Add Nodes
    graph.add_node("supervisor", supervisor)
    graph.add_node("image_parser", image_parser)
    graph.add_node("doc_parser", doc_parser)
    graph.add_node("validator", validator)
    graph.add_node("decision", decision)

    # Set Entry
    graph.set_entry_point("supervisor")

    # Conditional fan-out edges from supervisor
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "image_parser": "image_parser",
            "doc_parser": "doc_parser",
        },
    )

    # Join edges to validator
    graph.add_edge("image_parser", "validator")
    graph.add_edge("doc_parser", "validator")

    # Final routing
    graph.add_edge("validator", "decision")
    graph.add_edge("decision", END)

    return graph.compile()


# ──────────────────────────────────────────────────────────────────────────────
# 9. RUN PIPELINE
# ──────────────────────────────────────────────────────────────────────────────

async def run_kyc(image_path: str = None, doc_path: str = None):
    app = build_kyc_graph()

    initial_state: KYCState = {
        "image_path": image_path,
        "doc_path": doc_path,
        "image_data": None,
        "doc_data": None,
        "validation_result": None,
        "confidence_score": 0.0,
        "extracted_fields": {},
        "decision": "pending",
        "hitl_reason": "",
        "aml_result": None,
        "route": [],
        "trace_id": f"tx_{uuid4().hex[:8]}",
        "trace_history": []
    }

    final_state = await app.ainvoke(initial_state)

    print("\n" + "="*60)
    print("KYC A2A PIPELINE RUN COMPLETE")
    print("="*60)
    print(f"  Trace Session ID: {final_state['trace_id']}")
    print(f"  Final Decision  : {final_state['decision'].upper()}")
    print(f"  Confidence Score: {final_state['confidence_score']:.0%}")
    print(f"  Extracted Fields: {json.dumps(final_state['extracted_fields'], indent=4)}")
    if final_state["decision"] == "hitl_review":
        print(f"  HITL Reason     : {final_state['hitl_reason']}")
    
    print("\n" + "-"*30 + " A2A AUDIT TRACE LOGS " + "-"*30)
    for idx, trace in enumerate(final_state["trace_history"]):
        print(f"[{idx+1}] Timestamp: {trace['timestamp']}")
        print(f"    Agent path: {trace['sender_agent']} -> {trace['target_agent']}")
        print(f"    Status    : {trace['validation_status'].upper()}")
        if trace['error_message']:
            print(f"    Error Log : {trace['error_message']}")
    print("="*60)
    
    return final_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the KYC LangGraph pipeline with A2A Protocols.")
    parser.add_argument("--image", type=str, default=None, help="Path to ID card image (JPG/PNG)")
    parser.add_argument("--doc",   type=str, default=None, help="Path to KYC document (PDF)")
    args = parser.parse_args()

    if not args.image and not args.doc:
        parser.error("Provide at least one of --image or --doc")

    asyncio.run(run_kyc(image_path=args.image, doc_path=args.doc))
