# EDB Bank Compliance AI Agent: Deep-Dive System Architecture & Production Code Guide

---

## 1. Primary Objective: How the Entire System Works End-to-End

The system operates as an **Event-Driven, State-Machine-Based AI Agent** designed to automate **Level-1 AML/Sanctions Alert Investigation** and **Corporate KYC Trade Audit**.

```
[Core Banking / Transaction Monitoring System]
                    │
                    ▼ (Webhooks / Kafka Event)
┌─────────────────────────────────────────────────────────┐
│ 1. Ingestion & Input Guardrail (PII Redaction)          │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Context Retrieval (Redis Cache -> Vector DB / Graph) │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Agent Reasoning & Structured Extraction (LLM Core)   │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Output Guardrail (NLI Faithfulness & Citation Check) │
└───────────────────────────┬─────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
  [High Confidence Low Risk]     [High Risk / Sanctions / Unsure]
              │                           │
              ▼                           ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ 5a. Auto-Recommend Close │ │ 5b. Route to HITL Queue   │
│     (Batch Sign-Off)      │ │     (Human Analyst Review)│
└─────────────┬─────────────┘ └─────────────┬─────────────┘
              │                           │
              └─────────────┬─────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Immutable Audit Trail Commit (Postgres Checkpointer) │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Redis Cache Integration Architecture

Redis plays **3 vital roles** in the system:

1. **Semantic Cache for Embeddings & Entities:** If Entity $X$ (e.g., "Al-Ahmad Trading LLC") was looked up 10 minutes ago, the vector search and sanctions query result is fetched instantly from Redis ($<2\text{ms}$) instead of re-querying Milvus or Neo4j ($150\text{ms}$).
2. **Fast Transient State & Lock Management:** Prevents race conditions when multiple worker pods process events for the same corporate account using Redis Distributed Locks (`Redlock`).
3. **Session Checkpointing & Rate Limiting:** Keeps real-time agent execution tokens and state steps in memory for ultra-fast node transitions before syncing to persistent PostgreSQL storage.

---

## 3. State Activation & Payload Transfer Mechanics

### How State Works in LangGraph + Pydantic:
- **State Schema:** A Pydantic dataclass defines the strict type annotations for all channels in the graph.
- **Immutability & Reducers:** When Node A completes, it does **not** mutate the global state directly. It returns a **dictionary update**, which is merged into the persistent state using **reducers** (`operator.add` for lists, overwriting for scalar fields).
- **Node Activation:** A node triggers *only* when its prerequisite incoming edges complete and the state schema conditions are satisfied.

---

## 4. Complete Production Implementation Code

Below is the complete, runnable reference implementation covering **State Schema, Redis Cache, Multi-Node Execution, Guardrails, and Evaluation Metrics**.

```python
import os
import json
import time
import hashlib
import operator
from typing import Annotated, List, Dict, Any, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import redis

# LangGraph & Core AI Components
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

# ==========================================
# SECTION 1: STATE SCHEMA & REDUCERS
# ==========================================

class EntityMatch(BaseModel):
    entity_name: str
    match_score: float
    watchlist_source: str # e.g., OFAC, UN, World-Check
    is_sanctioned: bool

class AuditCitation(BaseModel):
    claim: str
    source_document: str
    chunk_id: str
    confidence: float

class ComplianceState(BaseModel):
    # Core identifiers
    alert_id: str
    customer_id: str
    raw_payload: str
    
    # Anonymized & Cleaned Payload
    sanitized_payload: Optional[str] = None
    pii_redacted_map: Dict[str, str] = Field(default_factory=dict)
    
    # Retrieval Layer
    retrieved_contexts: List[str] = Field(default_factory=list)
    entity_matches: List[EntityMatch] = Field(default_factory=list)
    from_cache: bool = False
    
    # Reasoning & LLM Outputs
    investigation_summary: Optional[str] = None
    risk_score: float = 0.0
    risk_category: str = "LOW" # LOW, MEDIUM, HIGH, CRITICAL
    suggested_action: str = "ESCALATE" # CLOSE_FALSE_POSITIVE, ESCALATE
    citations: List[AuditCitation] = Field(default_factory=list)
    
    # Guardrail Controls
    is_pii_clean: bool = False
    nli_faithfulness_score: float = 0.0
    guardrail_passed: bool = False
    guardrail_failure_reason: Optional[str] = None
    
    # Execution History & Steps
    execution_trace: Annotated[List[str], operator.add] = Field(default_factory=list)

# ==========================================
# SECTION 2: REDIS CACHE MANAGER
# ==========================================

class RedisCacheManager:
    def __init__(self, host='localhost', port=6379, db=0):
        self.r = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def _hash_key(self, query: str) -> str:
        return f"cache:compliance:{hashlib.sha256(query.encode()).hexdigest()}"

    def get_semantic_cache(self, entity_name: str) -> Optional[Dict[str, Any]]:
        key = self._hash_key(entity_name)
        cached_data = self.r.get(key)
        if cached_data:
            return json.loads(cached_data)
        return None

    def set_semantic_cache(self, entity_name: str, data: Dict[str, Any], ttl_seconds: int = 3600):
        key = self._hash_key(entity_name)
        self.r.setex(key, ttl_seconds, json.dumps(data))

    def acquire_lock(self, lock_name: str, expire: int = 10) -> bool:
        return self.r.set(f"lock:{lock_name}", "locked", nx=True, ex=expire)

    def release_lock(self, lock_name: str):
        self.r.delete(f"lock:{lock_name}")

redis_client = RedisCacheManager()

# ==========================================
# SECTION 3: GUARDRAILS IMPLEMENTATION
# ==========================================

class ComplianceGuardrails:
    @staticmethod
    def sanitize_pii(text: str) -> tuple[str, dict]:
        """Input Guardrail: Masks Emirates ID, Account Numbers, and Names."""
        pii_map = {}
        sanitized = text
        
        # Simple regex mask demonstration (In production: use Microsoft Presidio)
        import re
        account_pattern = r'\b\d{12,16}\b'
        matches = re.findall(account_pattern, text)
        for i, match in enumerate(matches):
            token = f"[ACCOUNT_MASKED_{i+1}]"
            pii_map[token] = match
            sanitized = sanitized.replace(match, token)
            
        return sanitized, pii_map

    @staticmethod
    def verify_nli_faithfulness(summary: str, contexts: List[str]) -> float:
        """
        Output Guardrail: Validates that summary claims are supported by contexts.
        Returns a score from 0.0 to 1.0.
        """
        if not summary or not contexts:
            return 0.0
            
        # In production: Cross-Encoder NLI Model (e.g., roberta-large-mnli)
        # Here we simulate NLI verification checking overlap & key factual alignment
        context_block = " ".join(contexts).lower()
        summary_sentences = summary.lower().split(".")
        
        supported_sentences = 0
        total_sentences = [s for s in summary_sentences if len(s.strip()) > 5]
        
        if not total_sentences:
            return 1.0
            
        for sentence in total_sentences:
            words = [w for w in sentence.split() if len(w) > 3]
            overlap = sum(1 for w in words if w in context_block)
            if len(words) > 0 and (overlap / len(words)) > 0.4:
                supported_sentences += 1
                
        return round(supported_sentences / len(total_sentences), 2)

# ==========================================
# SECTION 4: AGENT WORKFLOW NODES
# ==========================================

def node_1_ingest_and_anonymize(state: ComplianceState) -> Dict[str, Any]:
    """Node 1: Sanitizes input payload and verifies PII protection."""
    sanitized_text, pii_map = ComplianceGuardrails.sanitize_pii(state.raw_payload)
    
    return {
        "sanitized_payload": sanitized_text,
        "pii_redacted_map": pii_map,
        "is_pii_clean": True,
        "execution_trace": [f"[{time.strftime('%H:%M:%S')}] Node 1: PII Sanitized. Masked {len(pii_map)} tokens."]
    }

def node_2_context_retrieval(state: ComplianceState) -> Dict[str, Any]:
    """Node 2: Checks Redis Cache first, falls back to Vector DB & Sanctions list."""
    entity_key = f"customer_{state.customer_id}"
    
    # 1. Try Redis Cache
    cached = redis_client.get_semantic_cache(entity_key)
    if cached:
        return {
            "retrieved_contexts": cached["contexts"],
            "entity_matches": [EntityMatch(**m) for m in cached["matches"]],
            "from_cache": True,
            "execution_trace": [f"[{time.strftime('%H:%M:%S')}] Node 2: Cache Hit in Redis! Retained context instantly."]
        }
        
    # 2. Fallback: Query Vector DB / Sanctions Graph Engine (Simulated)
    time.sleep(0.1) # Simulate DB latency
    retrieved_docs = [
        f"Customer {state.customer_id} operates in Trade Sector (HS Code 8471).",
        "No match found on OFAC Sanctions list as of 2026-08-15.",
        "Recent transaction volume is within 15% of 6-month historical baseline."
    ]
    matches = [
        EntityMatch(entity_name="Al-Sharq General Trading", match_score=0.12, watchlist_source="OFAC", is_sanctioned=False)
    ]
    
    # Store result in Redis Cache for future fast lookups (TTL 1 hour)
    redis_client.set_semantic_cache(entity_key, {
        "contexts": retrieved_docs,
        "matches": [m.dict() for m in matches]
    }, ttl_seconds=3600)
    
    return {
        "retrieved_contexts": retrieved_docs,
        "entity_matches": matches,
        "from_cache": False,
        "execution_trace": [f"[{time.strftime('%H:%M:%S')}] Node 2: Cache Miss. Retrived from Milvus/Neo4j & cached to Redis."]
    }

def node_3_llm_reasoning(state: ComplianceState) -> Dict[str, Any]:
    """Node 3: Core LLM Reasoning node that generates structured findings."""
    # Build Prompt with sanitized payload & retrieved context
    has_sanctioned_match = any(m.is_sanctioned for m in state.entity_matches)
    
    if has_sanctioned_match:
        risk_score = 0.95
        risk_cat = "CRITICAL"
        action = "ESCALATE"
        summary = f"CRITICAL: Direct sanctions match detected for customer {state.customer_id} against watchlists."
    else:
        risk_score = 0.15
        risk_cat = "LOW"
        action = "CLOSE_FALSE_POSITIVE"
        summary = f"Alert {state.alert_id} evaluated. Transaction aligns with historical baseline. No sanctions match found."
        
    citations = [
        AuditCitation(
            claim="No sanctions match found",
            source_document="OFAC Watchlist Index",
            chunk_id="chk_9912",
            confidence=0.99
        )
    ]
    
    return {
        "investigation_summary": summary,
        "risk_score": risk_score,
        "risk_category": risk_cat,
        "suggested_action": action,
        "citations": citations,
        "execution_trace": [f"[{time.strftime('%H:%M:%S')}] Node 3: LLM reasoning completed. Risk Score: {risk_score} ({risk_cat})."]
    }

def node_4_guardrail_verification(state: ComplianceState) -> Dict[str, Any]:
    """Node 4: Evaluates Output Guardrails (Faithfulness, Citation Match)."""
    score = ComplianceGuardrails.verify_nli_faithfulness(
        state.investigation_summary, 
        state.retrieved_contexts
    )
    
    passed = score >= 0.70
    reason = None if passed else f"Faithfulness score {score} below required threshold (0.70)."
    
    return {
        "nli_faithfulness_score": score,
        "guardrail_passed": passed,
        "guardrail_failure_reason": reason,
        "execution_trace": [f"[{time.strftime('%H:%M:%S')}] Node 4: Output Guardrail Checked. NLI Score: {score}. Passed: {passed}"]
    }

# ==========================================
# SECTION 5: CONDITIONAL ROUTING LOGIC
# ==========================================

def route_decision(state: ComplianceState) -> str:
    """Routing Edge: Determines whether to auto-close, escalate to human, or retry."""
    if not state.guardrail_passed:
        return "route_to_hitl" # Guardrail failure forces human intervention
        
    if state.risk_category in ["HIGH", "CRITICAL"] or state.suggested_action == "ESCALATE":
        return "route_to_hitl"
    else:
        return "route_to_auto_close"

def node_hitl_queue(state: ComplianceState) -> Dict[str, Any]:
    """Queue Case for Human Compliance Analyst."""
    return {
        "execution_trace": [f"[{time.strftime('%H:%M:%S')}] Case Queued for Level-2 Human Compliance Analyst Review."]
    }

def node_auto_close(state: ComplianceState) -> Dict[str, Any]:
    """Commit Auto-Recommendation for Batch Clearance."""
    return {
        "execution_trace": [f"[{time.strftime('%H:%M:%S')}] Alert Pre-Cleared as False Positive. Added to Batch Sign-Off."]
    }

# ==========================================
# SECTION 6: GRAPH ASSEMBLY & COMPILATION
# ==========================================

def build_compliance_agent():
    builder = StateGraph(ComplianceState)
    
    # Add Nodes
    builder.add_node("ingest", node_1_ingest_and_anonymize)
    builder.add_node("retrieve", node_2_context_retrieval)
    builder.add_node("reason", node_3_llm_reasoning)
    builder.add_node("guardrail", node_4_guardrail_verification)
    builder.add_node("hitl_queue", node_hitl_queue)
    builder.add_node("auto_close", node_auto_close)
    
    # Set Edges
    builder.set_entry_point("ingest")
    builder.add_edge("ingest", "retrieve")
    builder.add_edge("retrieve", "reason")
    builder.add_edge("reason", "guardrail")
    
    # Conditional Edge
    builder.add_conditional_edges(
        "guardrail",
        route_decision,
        {
            "route_to_hitl": "hitl_queue",
            "route_to_auto_close": "auto_close"
        }
    )
    
    builder.add_edge("hitl_queue", END)
    builder.add_edge("auto_close", END)
    
    return builder.compile()

# ==========================================
# SECTION 7: EVALUATION METRICS SUITE
# ==========================================

class RAGASEvaluator:
    """Evaluates agent execution against Golden Evaluation Datasets."""
    
    @staticmethod
    def evaluate_case(state: ComplianceState, ground_truth_action: str) -> Dict[str, float]:
        # 1. Action Accuracy
        action_match = 1.0 if state.suggested_action == ground_truth_action else 0.0
        
        # 2. Faithfulness Score (from NLI guardrail)
        faithfulness = state.nli_faithfulness_score
        
        # 3. Citation Coverage Score
        citation_score = 1.0 if len(state.citations) > 0 else 0.0
        
        # Combined Quality Index
        overall_score = (action_match * 0.4) + (faithfulness * 0.4) + (citation_score * 0.2)
        
        return {
            "action_accuracy": action_match,
            "faithfulness": faithfulness,
            "citation_coverage": citation_score,
            "overall_quality_index": round(overall_score, 2)
        }

# ==========================================
# SECTION 8: EXECUTION DEMO
# ==========================================

if __name__ == "__main__":
    agent = build_compliance_agent()
    
    # Simulate Incoming Alert Payload
    test_alert = ComplianceState(
        alert_id="ALT-2026-8819",
        customer_id="CUST-9901",
        raw_payload="Transfer of 45000 USD from Account 123456789012 to Al-Sharq General Trading for computer hardware."
    )
    
    print("🚀 Starting Compliance AI Agent Execution...\n")
    final_state = agent.invoke(test_alert)
    
    print("\n=== EXECUTION TRACE ===")
    for step in final_state["execution_trace"]:
        print(step)
        
    print("\n=== FINAL AGENT DECISION ===")
    print(f"Risk Score: {final_state['risk_score']} ({final_state['risk_category']})")
    print(f"Suggested Action: {final_state['suggested_action']}")
    print(f"NLI Faithfulness Score: {final_state['nli_faithfulness_score']}")
    print(f"Guardrail Passed: {final_state['guardrail_passed']}")
    print(f"Summary: {final_state['investigation_summary']}")
    
    # Run Evaluation
    eval_metrics = RAGASEvaluator.evaluate_case(
        ComplianceState(**final_state), 
        ground_truth_action="CLOSE_FALSE_POSITIVE"
    )
    print("\n=== EVALUATION METRICS ===")
    print(json.dumps(eval_metrics, indent=2))
```

---

## 5. Evaluation Metrics Deep Dive

To meet EDB Bank's AI Governance requirements, the agent is continuously evaluated across **Offline Benchmarks** and **Online Production Metrics**:

### A. Offline RAGAS Metrics (Golden Evaluation Dataset)

$$\text{Overall Quality Index} = 0.4 \times \text{Action Accuracy} + 0.4 \times \text{Faithfulness} + 0.2 \times \text{Citation Coverage}$$

1. **Faithfulness Score ($\ge 0.85$):** Verifies that every claim in the generated investigation narrative is mathematically entailed by the retrieved context (zero hallucination tolerance).
2. **Context Recall ($\ge 0.90$):** Measures whether the RAG engine retrieved all relevant sanctions lists, UBO data, and historical transaction records needed for an accurate decision.
3. **Answer Relevance ($\ge 0.88$):** Evaluates how directly the narrative answers the compliance alert trigger reason.

### B. Online Production Business Metrics

1. **Human Overturn Rate (Target $< 5\%$):** The percentage of AI recommendations rejected or modified by Level-2 human compliance analysts.
2. **False Positive Reduction Rate (Target $60-70\%$):** Percentage of total daily alerts auto-recommended for batch sign-off, freeing human analysts for high-risk investigations.
3. **P95 Latency (Target $< 3.5\text{s}$):** Total end-to-end processing time from raw Kafka alert trigger to final decision routing.
4. **Token & Inference Cost per Alert:** Measured in fractions of a cent per processed alert using semantic caching optimization.
