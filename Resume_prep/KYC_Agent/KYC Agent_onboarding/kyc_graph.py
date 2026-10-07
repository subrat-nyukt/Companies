"""
KYC Onboarding Agent — LangGraph Supervisor Pipeline
=====================================================
Workflow (5 nodes):
  1. supervisor      → routes payload to image or doc parser (or both)
  2. image_parser    → Azure Vision  → extracts text/tags from image files
  3. doc_parser      → Azure Form Recognizer → extracts text/tables from PDFs
  4. validator       → GPT-4o cross-references extracted data, returns confidence
  5. decision        → confidence >= threshold → auto-approve DB update
                       confidence  < threshold → pause & send to HITL queue

Run:
    python kyc_graph.py --image path/to/id.jpg --doc path/to/form.pdf
"""

import asyncio
import json
import logging
import argparse
from typing import TypedDict, Optional, Dict, Any, List

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
# 1. GRAPH STATE  (shared memory across all nodes)
# ──────────────────────────────────────────────────────────────────────────────

class KYCState(TypedDict):
    # Inputs
    image_path: Optional[str]
    doc_path: Optional[str]

    # Extracted data from each specialist agent
    image_data: Optional[Dict[str, Any]]
    doc_data: Optional[Dict[str, Any]]

    # Validation output
    validation_result: Optional[str]   # raw LLM response
    confidence_score: float            # 0.0 – 1.0
    extracted_fields: Dict[str, Any]   # parsed KYC fields (name, dob, id_no…)

    # Decision
    decision: str           # "approved" | "hitl_review" | "pending"
    hitl_reason: str        # reason for escalation (if any)

    # AML Check Result
    aml_result: Optional[Dict[str, Any]]

    # Routing
    route: List[str]        # which parser nodes to run


# ──────────────────────────────────────────────────────────────────────────────
# 2. NODE: SUPERVISOR
#    Inspects payload and decides which parsers to invoke
# ──────────────────────────────────────────────────────────────────────────────

def supervisor(state: KYCState) -> KYCState:
    """Route the payload to the correct downstream agents."""
    route = []
    if state.get("image_path"):
        route.append("image_parser")
    if state.get("doc_path"):
        route.append("doc_parser")

    if not route:
        raise ValueError("No image_path or doc_path provided to supervisor.")

    logger.info(f"[Supervisor] Routing to: {route}")
    return {**state, "route": route, "decision": "pending", "confidence_score": 0.0,
            "extracted_fields": {}, "hitl_reason": ""}


# ──────────────────────────────────────────────────────────────────────────────
# 3. NODE: IMAGE PARSER (Azure Vision)
# ──────────────────────────────────────────────────────────────────────────────

async def image_parser(state: KYCState) -> KYCState:
    """Call Azure Vision and store raw extracted data."""
    logger.info(f"[ImageParser] Processing: {state['image_path']}")
    result = await vision_analyzer.process_document(state["image_path"])
    if result is None:
        logger.warning("[ImageParser] Extraction returned None — marking as empty.")
        result = {}
    return {**state, "image_data": result}


# ──────────────────────────────────────────────────────────────────────────────
# 4. NODE: DOCUMENT PARSER (Azure Form Recognizer)
# ──────────────────────────────────────────────────────────────────────────────

async def doc_parser(state: KYCState) -> KYCState:
    """Call Azure Form Recognizer and store raw extracted data."""
    logger.info(f"[DocParser] Processing: {state['doc_path']}")
    result = await document_ingestor.parse_document(state["doc_path"])
    if result is None:
        logger.warning("[DocParser] Extraction returned None — marking as empty.")
        result = {}
    return {**state, "doc_data": result}


# ──────────────────────────────────────────────────────────────────────────────
# 5. NODE: VALIDATOR (GPT-4o cross-reference + AML mock)
# ──────────────────────────────────────────────────────────────────────────────

async def validator(state: KYCState) -> KYCState:
    """
    Send extracted data to GPT-4o for KYC validation.
    The LLM is provided an AML screening tool to check name and ID against lists.
    """
    combined_context = json.dumps({
        "image_data": state.get("image_data", {}),
        "doc_data": state.get("doc_data", {}),
    }, indent=2)

    prompt = VALIDATION_PROMPT.format(extracted_data=combined_context)

    # Define the AML tool as a function schema for GPT-4o
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

    logger.info("[Validator] Sending to GPT-4o (with AML tools)…")
    response = await azure_clients.llm.chat.completions.create(
        model=settings.azure_openai_deployment_name,
        messages=messages,
        tools=[aml_tool],
        tool_choice="auto",
        temperature=0.1
    )

    response_message = response.choices[0].message
    aml_result = None

    # If GPT chose to call the AML tool:
    if response_message.tool_calls:
        tool_call = response_message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)

        logger.info(f"[Validator] GPT-4o invoked AML tool for {args.get('full_name')}...")
        
        # Execute the actual AML check
        aml_result = await check_aml_database(
            name=args.get("full_name"),
            id_number=args.get("id_number")
        )

        # Feed result back to GPT for final decision
        messages.append(response_message) # Append assistant's tool call message
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(aml_result)
        })

        logger.info("[Validator] AML complete. Asking GPT-4o for final confidence judgment...")
        # Get final confidence string expecting JSON object this time
        final_response = await azure_clients.llm.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1
        )
        raw = final_response.choices[0].message.content
    else:
        # GPT did not call tool (maybe no name/ID extracted?)
        raw = response_message.content

    logger.info(f"[Validator] Raw LLM final response: {raw}")

    try:
        parsed = json.loads(raw)
        confidence = float(parsed.get("confidence", 0.0))
        extracted_fields = parsed.get("fields", {})
        hitl_reason = parsed.get("reason", "")
    except (json.JSONDecodeError, ValueError):
        logger.error("[Validator] Could not parse LLM JSON — defaulting to 0.0")
        confidence, extracted_fields, hitl_reason = 0.0, {}, "LLM parse failure"

    # If there was a true AML match, we hard-set confidence to 0.0 regardless of GPT's document assessment
    if aml_result and aml_result.get("is_match"):
        logger.warning(f"[Validator] AML Sanctions hit: {aml_result['match_detail']}")
        confidence = 0.0
        hitl_reason = f"AML MATCH: {aml_result['match_detail']} (List: {aml_result.get('list', 'Unknown')})"

    return {
        **state,
        "validation_result": raw,
        "confidence_score": confidence,
        "extracted_fields": extracted_fields,
        "hitl_reason": hitl_reason,
        "aml_result": aml_result,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 6. NODE: DECISION (auto-approve vs HITL)
# ──────────────────────────────────────────────────────────────────────────────

def decision(state: KYCState) -> KYCState:
    """
    High confidence  → auto-approve (write to DB in production).
    Low confidence   → pause state and route to Human-In-The-Loop queue.
    """
    threshold = settings.confidence_threshold
    score = state["confidence_score"]

    if score >= threshold:
        logger.info(f"[Decision] AUTO-APPROVED  (score={score:.2f} >= {threshold})")
        # In production: db.update(user_id, status="approved", fields=state["extracted_fields"])
        decision_val = "approved"
    else:
        logger.warning(f"[Decision] HITL REQUIRED  (score={score:.2f} < {threshold}) — reason: {state['hitl_reason']}")
        # In production: hitl_queue.push(ticket_id, state)
        decision_val = "hitl_review"

    return {**state, "decision": decision_val}


# ──────────────────────────────────────────────────────────────────────────────
# 7. ROUTING HELPER  (conditional edges from supervisor)
# ──────────────────────────────────────────────────────────────────────────────

def route_after_supervisor(state: KYCState) -> List[str]:
    """Return the list of parser nodes that should run next."""
    return state["route"]   # e.g. ["image_parser", "doc_parser"]


# ──────────────────────────────────────────────────────────────────────────────
# 8. BUILD THE GRAPH
# ──────────────────────────────────────────────────────────────────────────────

def build_kyc_graph():
    graph = StateGraph(KYCState)

    # Register nodes
    graph.add_node("supervisor", supervisor)
    graph.add_node("image_parser", image_parser)
    graph.add_node("doc_parser", doc_parser)
    graph.add_node("validator", validator)
    graph.add_node("decision", decision)

    # Entry point
    graph.set_entry_point("supervisor")

    # Supervisor fans out to whichever parsers are needed
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "image_parser": "image_parser",
            "doc_parser": "doc_parser",
        },
    )

    # Both parsers feed into the validator
    graph.add_edge("image_parser", "validator")
    graph.add_edge("doc_parser", "validator")

    # Validator → decision → END
    graph.add_edge("validator", "decision")
    graph.add_edge("decision", END)

    return graph.compile()


# ──────────────────────────────────────────────────────────────────────────────
# 9. ENTRYPOINT  (run from terminal for testing)
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
    }

    final_state = await app.ainvoke(initial_state)

    print("\n" + "="*60)
    print("KYC PIPELINE COMPLETE")
    print("="*60)
    print(f"  Decision        : {final_state['decision'].upper()}")
    print(f"  Confidence Score: {final_state['confidence_score']:.0%}")
    print(f"  Extracted Fields: {json.dumps(final_state['extracted_fields'], indent=4)}")
    if final_state["decision"] == "hitl_review":
        print(f"  HITL Reason     : {final_state['hitl_reason']}")
    print("="*60)
    return final_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the KYC LangGraph pipeline.")
    parser.add_argument("--image", type=str, default=None, help="Path to ID card image (JPG/PNG)")
    parser.add_argument("--doc",   type=str, default=None, help="Path to KYC document (PDF)")
    args = parser.parse_args()

    if not args.image and not args.doc:
        parser.error("Provide at least one of --image or --doc")

    asyncio.run(run_kyc(image_path=args.image, doc_path=args.doc))
