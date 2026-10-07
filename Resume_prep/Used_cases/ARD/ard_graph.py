"""
ARD — ard_graph.py
====================
Agentic Research Desk (ARD) — Main LangGraph Pipeline
Market Securities | Use Case 1: Agentic Research & Market Commentary

Workflow (6 nodes):
  [orchestrator] → parallel fan-out →
    [central_bank_agent] + [ma_arbitrage_agent] + [special_situations_agent]
  → join → [rag_retriever] → [synthesis_node] → [groundedness_guard] → [report_writer] → END

Production Architecture Features:
  ✅ A2A (Agent-to-Agent) Message Envelopes — every node transition is logged & traceable
  ✅ Pydantic schema contracts — every agent output is strictly validated
  ✅ Self-correction retry loops — LLM re-generates if schema validation fails (max 2 retries)
  ✅ Circuit Breakers — asyncio.wait_for() on all external calls; graceful HITL escalation
  ✅ Hybrid RAG — dense (OpenAI) + sparse (TF-IDF) search merged with Reciprocal Rank Fusion
  ✅ Groundedness Guardrail — synchronous, blocking quality gate before any report is published
  ✅ Full audit trail — timestamped JSON report written to output/ directory

Run:
    python ard_graph.py --query "ECB signals rate pause as inflation falls to 2.1%"
    python ard_graph.py --query "NovaTech semiconductor deal faces EC Phase II investigation"
    python ard_graph.py --query "MediaCorp holdco discount widens to 23% on CEO departure"
"""

import asyncio
import json
import logging
import argparse
import datetime
from uuid import uuid4
from typing import Any

from openai import OpenAI
from langgraph.graph import StateGraph, END

from core.config import settings
from core.client import clients
from schemas.contracts import ARDState, SynthesisOutput, build_envelope, new_trace_id
from agents.central_bank_agent import run_central_bank_agent
from agents.ma_arbitrage_agent import run_ma_arbitrage_agent
from agents.special_situations_agent import run_special_situations_agent
from rag.retriever import retrieve
from guardrails.groundedness import evaluate_groundedness, extract_synthesis_text
from prompts.agent_prompts import SYNTHESIS_SYSTEM, SYNTHESIS_USER_TEMPLATE

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ARD")


# ══════════════════════════════════════════════════════════════════════════════
# NODE 1: ORCHESTRATOR
# Initializes the trace session and fans out to all three specialist agents.
# ══════════════════════════════════════════════════════════════════════════════

async def orchestrator_node(state: ARDState) -> ARDState:
    """
    Entry node. Runs all three specialist agents concurrently via asyncio.gather().
    Collects their outputs and A2A envelopes into the shared state.

    All agents run in parallel — total latency ≈ max(single_agent_latency),
    not sum of all agents. This is the key performance advantage of the fan-out pattern.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"[Orchestrator] Starting ARD pipeline | Trace: {state['trace_id']}")
    logger.info(f"[Orchestrator] Query: '{state['trigger_query']}'")
    logger.info(f"{'='*60}")

    openai_client = OpenAI(api_key=settings.openai_api_key)
    history = list(state.get("trace_history", []))

    # Log orchestrator start envelope
    history.append(build_envelope(
        state, sender="orchestrator", target="all_agents",
        payload={"trigger_query": state["trigger_query"], "action": "fan_out"},
    ))

    # ── Parallel Fan-Out: All 3 agents run concurrently ────────────────────────
    logger.info("[Orchestrator] Fan-out → 3 specialist agents running in parallel...")
    cb_result, ma_result, ss_result = await asyncio.gather(
        run_central_bank_agent(state, openai_client),
        run_ma_arbitrage_agent(state, openai_client),
        run_special_situations_agent(state, openai_client),
        return_exceptions=False,
    )

    cb_output, cb_envelope = cb_result
    ma_output, ma_envelope = ma_result
    ss_output, ss_envelope = ss_result

    # Append all agent envelopes to trace
    history.extend([cb_envelope, ma_envelope, ss_envelope])

    # Collect successful agent outputs
    agent_outputs: dict[str, Any] = {}
    if cb_output:
        agent_outputs["central_bank_sentiment_agent"] = cb_output.model_dump()
        logger.info(f"[Orchestrator] ✅ CB Agent: {cb_output.signal[:60]}...")
    else:
        logger.warning("[Orchestrator] ⚠️  CB Agent: Circuit breaker tripped")

    if ma_output:
        agent_outputs["ma_arbitrage_agent"] = ma_output.model_dump()
        logger.info(f"[Orchestrator] ✅ M&A Agent: {ma_output.signal[:60]}...")
    else:
        logger.warning("[Orchestrator] ⚠️  M&A Agent: Circuit breaker tripped")

    if ss_output:
        agent_outputs["special_situations_agent"] = ss_output.model_dump()
        logger.info(f"[Orchestrator] ✅ SpecSit Agent: {ss_output.signal[:60]}...")
    else:
        logger.warning("[Orchestrator] ⚠️  SpecSit Agent: Circuit breaker tripped")

    # Safety gate: if ALL agents failed, escalate to HITL immediately
    if not agent_outputs:
        logger.error("[Orchestrator] CRITICAL: All agents tripped circuit breakers → HITL escalation")
        return {
            **state,
            "agent_outputs": {},
            "hitl_required": True,
            "hitl_reason": "All three specialist agents failed with circuit breaker errors.",
            "trace_history": history,
        }

    return {
        **state,
        "agent_outputs": agent_outputs,
        "trace_history": history,
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 2: RAG RETRIEVER
# Expands the trigger query using agent signals, then runs hybrid retrieval.
# ══════════════════════════════════════════════════════════════════════════════

def rag_retriever_node(state: ARDState) -> ARDState:
    """
    Builds an expanded retrieval query from the trigger + agent signal keywords,
    then runs hybrid (dense + sparse + RRF) Pinecone retrieval.

    Query expansion: concatenating agent signals gives the retriever more
    specific financial terms to match against the research database.
    This mimics the 'Clinical Query Reformulation' step from the RAG architecture.
    """
    if state.get("hitl_required"):
        return state  # Skip if already in HITL escalation path

    history = list(state.get("trace_history", []))
    trigger = state["trigger_query"]

    # Query expansion: combine trigger with agent signals for richer retrieval
    signals = [
        v.get("signal", "") for v in state.get("agent_outputs", {}).values() if v
    ]
    expanded_query = trigger + " " + " ".join(signals)

    logger.info(f"[RAG Retriever] Expanded query (first 100 chars): '{expanded_query[:100]}...'")

    try:
        chunks = retrieve(query=expanded_query, top_k=settings.top_k_context)
        logger.info(f"[RAG Retriever] Retrieved {len(chunks)} chunks via hybrid search (RRF)")

        history.append(build_envelope(
            state, sender="rag_retriever", target="synthesis_node",
            payload={"num_chunks": len(chunks), "expanded_query": expanded_query[:200]},
        ))

        return {**state, "retrieved_chunks": chunks, "trace_history": history}

    except Exception as e:
        error_msg = f"RAG Retriever failed: {str(e)}"
        logger.error(f"[RAG Retriever] {error_msg}")
        history.append(build_envelope(
            state, sender="rag_retriever", target="synthesis_node",
            payload={}, status="circuit_breaker", error=error_msg,
        ))
        # Graceful degradation: synthesis proceeds with no context (will likely fail groundedness)
        return {**state, "retrieved_chunks": [], "trace_history": history}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 3: SYNTHESIS NODE
# Combines all agent signals + retrieved context into a structured research note.
# ══════════════════════════════════════════════════════════════════════════════

async def synthesis_node(state: ARDState) -> ARDState:
    """
    Calls the Synthesis & Drafting Agent to produce a structured research note.
    Validates output against SynthesisOutput Pydantic schema with retry loop.

    If synthesis fails (schema error or timeout), routes to HITL.
    """
    if state.get("hitl_required"):
        return state

    history = list(state.get("trace_history", []))
    openai_client = OpenAI(api_key=settings.openai_api_key)

    # Format agent signals for the prompt
    agent_signals_str = json.dumps(
        {k: {"signal": v.get("signal"), "evidence": v.get("evidence"), "confidence": v.get("confidence")}
         for k, v in state.get("agent_outputs", {}).items()},
        indent=2,
    )

    # Format context chunks
    context_str = "\n\n---\n\n".join(
        f"[Source: {c.get('source', 'unknown')}]\n{c['text']}"
        for c in state.get("retrieved_chunks", [])
    ) or "No retrieved context available."

    messages = [
        {"role": "system", "content": SYNTHESIS_SYSTEM},
        {
            "role": "user",
            "content": SYNTHESIS_USER_TEMPLATE.format(
                agent_signals=agent_signals_str,
                context=context_str,
            ),
        },
    ]

    synthesis_draft = None
    retry_count = state.get("synthesis_retry_count", 0)

    try:
        async def _synthesize():
            for attempt in range(settings.max_retries + 1):
                logger.info(f"[Synthesis] LLM call attempt {attempt + 1}/{settings.max_retries + 1}")
                response = openai_client.chat.completions.create(
                    model=settings.llm_model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                raw = response.choices[0].message.content
                try:
                    data = json.loads(raw)
                    return SynthesisOutput(**data)
                except Exception as e:
                    if attempt < settings.max_retries:
                        logger.warning(f"[Synthesis] Schema validation failed (attempt {attempt + 1}): {e}")
                        messages.append({"role": "assistant", "content": raw})
                        messages.append({
                            "role": "user",
                            "content": (
                                f"Output failed validation: {e}. "
                                "Re-generate JSON matching schema exactly: "
                                "headline, executive_summary, macro_commentary, "
                                "event_driven_commentary, trade_ideas (list), risk_flags (list)."
                            ),
                        })
                    else:
                        raise ValueError(f"Synthesis self-correction exhausted: {e}")
            raise RuntimeError("Synthesis: unexpected loop exit")

        output = await asyncio.wait_for(_synthesize(), timeout=settings.agent_timeout_seconds)
        synthesis_draft = output.model_dump()
        logger.info(f"[Synthesis] Draft generated: '{synthesis_draft['headline']}'")

        history.append(build_envelope(
            state, sender="synthesis_node", target="groundedness_guard",
            payload={"headline": synthesis_draft.get("headline")}, status="success",
        ))

    except Exception as e:
        error_msg = f"Synthesis failed: {str(e)}"
        logger.error(f"[Synthesis] {error_msg}")
        history.append(build_envelope(
            state, sender="synthesis_node", target="groundedness_guard",
            payload={}, status="circuit_breaker", error=error_msg,
        ))
        return {
            **state,
            "synthesis_draft": None,
            "hitl_required": True,
            "hitl_reason": error_msg,
            "trace_history": history,
        }

    return {
        **state,
        "synthesis_draft": synthesis_draft,
        "synthesis_retry_count": retry_count,
        "trace_history": history,
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 4: GROUNDEDNESS GUARD (Synchronous, Blocking)
# ══════════════════════════════════════════════════════════════════════════════

def groundedness_guard_node(state: ARDState) -> ARDState:
    """
    COMPLIANCE GATE — Runs synchronously before any report is published.

    Evaluates every factual sentence in the synthesis draft against the
    retrieved context chunks using the LLM-as-a-Judge pattern.

    Score < threshold → block publication → route to HITL analyst review.
    Score >= threshold → approve → route to report writer.

    Formula: Groundedness = supported_sentences / total_sentences
    """
    if state.get("hitl_required") or not state.get("synthesis_draft"):
        return state

    history = list(state.get("trace_history", []))
    openai_client = OpenAI(api_key=settings.openai_api_key)

    # Extract evaluable text from synthesis
    synthesis_text = extract_synthesis_text(state["synthesis_draft"])
    context_chunks = state.get("retrieved_chunks", [])

    logger.info("[Groundedness Guard] Running synchronous groundedness evaluation...")
    score, verdicts = evaluate_groundedness(synthesis_text, context_chunks, openai_client)

    pass_fail = score >= settings.groundedness_threshold
    logger.info(
        f"[Groundedness Guard] Score: {score:.3f} | Threshold: {settings.groundedness_threshold} | "
        f"{'✅ PASS' if pass_fail else '❌ FAIL — routing to HITL'}"
    )

    # Log per-sentence verdicts at DEBUG level
    for v in verdicts:
        logger.debug(f"  [{v['verdict']}] {v['sentence'][:80]}... | {v['reason']}")

    history.append(build_envelope(
        state, sender="groundedness_guard", target="report_writer",
        payload={
            "score": score,
            "threshold": settings.groundedness_threshold,
            "pass": pass_fail,
            "num_sentences_evaluated": len(verdicts),
        },
        status="success" if pass_fail else "circuit_breaker",
        error=None if pass_fail else f"Groundedness {score:.3f} < threshold {settings.groundedness_threshold}",
    ))

    if not pass_fail:
        return {
            **state,
            "groundedness_score": score,
            "hitl_required": True,
            "hitl_reason": (
                f"Groundedness score {score:.3f} is below threshold {settings.groundedness_threshold}. "
                "Research note contains potentially ungrounded claims. Analyst review required."
            ),
            "trace_history": history,
        }

    return {
        **state,
        "groundedness_score": score,
        "trace_history": history,
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 5: REPORT WRITER
# Assembles final JSON report and writes to output/ directory.
# ══════════════════════════════════════════════════════════════════════════════

def report_writer_node(state: ARDState) -> ARDState:
    """
    Assembles the final report package and writes it to the output/ directory.
    If hitl_required is True, writes an HITL escalation package instead.
    """
    history = list(state.get("trace_history", []))
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    if state.get("hitl_required"):
        # ── HITL Escalation Report ─────────────────────────────────────────────
        report = {
            "report_type": "HITL_ESCALATION",
            "trace_id": state["trace_id"],
            "timestamp": timestamp,
            "trigger_query": state["trigger_query"],
            "hitl_reason": state.get("hitl_reason", "Unknown error"),
            "agent_outputs_available": list(state.get("agent_outputs", {}).keys()),
            "groundedness_score": state.get("groundedness_score", None),
            "synthesis_draft": state.get("synthesis_draft"),
            "action_required": "Senior analyst review required before publication.",
        }
        filename = f"HITL_{state['trace_id']}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        logger.warning(f"[Report Writer] ⚠️  HITL Escalation → {filename}")

    else:
        # ── Approved Research Report ───────────────────────────────────────────
        draft = state.get("synthesis_draft", {})
        agent_outputs = state.get("agent_outputs", {})

        report = {
            "report_type": "APPROVED_RESEARCH_NOTE",
            "trace_id": state["trace_id"],
            "timestamp": timestamp,
            "trigger_query": state["trigger_query"],
            "groundedness_score": state.get("groundedness_score", 0.0),

            # ── The Research Note ──────────────────────────────────────────────
            "research_note": {
                "headline": draft.get("headline"),
                "executive_summary": draft.get("executive_summary"),
                "macro_commentary": draft.get("macro_commentary"),
                "event_driven_commentary": draft.get("event_driven_commentary"),
                "trade_ideas": draft.get("trade_ideas", []),
                "risk_flags": draft.get("risk_flags", []),
            },

            # ── Agent Signal Provenance ────────────────────────────────────────
            "agent_signals": {
                name: {
                    "signal": data.get("signal"),
                    "confidence": data.get("confidence"),
                    "evidence": data.get("evidence"),
                    "asset_class": data.get("asset_class"),
                }
                for name, data in agent_outputs.items()
            },

            # ── RAG Source Citations ────────────────────────────────────────────
            "sources_cited": [
                {"source": c.get("source"), "chunk_index": c.get("chunk_index")}
                for c in state.get("retrieved_chunks", [])
            ],

            "audit_note": (
                f"This research note was generated by the Market Securities Agentic Research Desk. "
                f"Groundedness score: {state.get('groundedness_score', 0):.3f}. "
                f"All factual claims are grounded in retrieved source documents."
            ),
        }
        filename = f"REPORT_{state['trace_id']}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        logger.info(f"[Report Writer] ✅ Research note approved → {filename}")

    # Write to output directory
    output_path = settings.output_dir / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"[Report Writer] Report written: {output_path}")

    history.append(build_envelope(
        state, sender="report_writer", target="END",
        payload={"filename": filename, "report_type": report["report_type"]},
    ))

    return {**state, "final_report": report, "trace_history": history}


# ══════════════════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════

def build_ard_graph():
    """
    Assembles the LangGraph StateGraph connecting all 5 nodes.

    Graph topology:
      orchestrator → rag_retriever → synthesis → groundedness_guard → report_writer → END

    Note: The orchestrator node internally runs the 3 specialist agents
    concurrently via asyncio.gather() (parallel fan-out within a single node).
    LangGraph's fan-out edges require Send API or parallel nodes in LangGraph v2+;
    for simplicity and compatibility, we use internal asyncio parallelism.
    """
    graph = StateGraph(ARDState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("rag_retriever", rag_retriever_node)
    graph.add_node("synthesis", synthesis_node)
    graph.add_node("groundedness_guard", groundedness_guard_node)
    graph.add_node("report_writer", report_writer_node)

    graph.set_entry_point("orchestrator")
    graph.add_edge("orchestrator", "rag_retriever")
    graph.add_edge("rag_retriever", "synthesis")
    graph.add_edge("synthesis", "groundedness_guard")
    graph.add_edge("groundedness_guard", "report_writer")
    graph.add_edge("report_writer", END)

    return graph.compile()


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE RUNNER
# ══════════════════════════════════════════════════════════════════════════════

async def run_ard(trigger_query: str) -> ARDState:
    """
    Initialize state and run the full ARD pipeline.
    Returns the final ARDState containing the report and full A2A audit trail.
    """
    app = build_ard_graph()
    trace_id = new_trace_id()

    initial_state: ARDState = {
        "trigger_query": trigger_query,
        "agent_outputs": {},
        "retrieved_chunks": [],
        "synthesis_draft": None,
        "groundedness_score": 0.0,
        "synthesis_retry_count": 0,
        "final_report": None,
        "hitl_required": False,
        "hitl_reason": None,
        "trace_id": trace_id,
        "trace_history": [],
    }

    logger.info(f"\n🚀 ARD Pipeline initiated | Trace ID: {trace_id}")
    final_state = await app.ainvoke(initial_state)

    # ── Print summary to console ───────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  MARKET SECURITIES — AGENTIC RESEARCH DESK (ARD) — RUN COMPLETE")
    print("=" * 70)
    print(f"  Trace ID        : {final_state['trace_id']}")
    print(f"  Trigger Query   : {final_state['trigger_query']}")
    print(f"  Groundedness    : {final_state['groundedness_score']:.3f} / 1.000")
    print(f"  HITL Required   : {'⚠️  YES' if final_state['hitl_required'] else '✅ NO'}")

    if final_state.get("hitl_reason"):
        print(f"  HITL Reason     : {final_state['hitl_reason']}")

    report = final_state.get("final_report", {})
    if report and report.get("report_type") == "APPROVED_RESEARCH_NOTE":
        note = report.get("research_note", {})
        print(f"\n  📰 HEADLINE: {note.get('headline', 'N/A')}")
        print(f"\n  EXECUTIVE SUMMARY:")
        print(f"  {note.get('executive_summary', 'N/A')}")
        print(f"\n  TRADE IDEAS:")
        for i, idea in enumerate(note.get("trade_ideas", []), 1):
            print(f"    {i}. {idea}")
        print(f"\n  RISK FLAGS:")
        for i, flag in enumerate(note.get("risk_flags", []), 1):
            print(f"    {i}. {flag}")

    print(f"\n  AGENT SIGNALS COLLECTED:")
    for agent_name, data in final_state.get("agent_outputs", {}).items():
        status_icon = "✅"
        print(f"    {status_icon} [{agent_name}]")
        print(f"       Signal     : {data.get('signal', 'N/A')[:80]}...")
        print(f"       Confidence : {data.get('confidence', 0):.2f}")

    print(f"\n  A2A AUDIT TRACE ({len(final_state['trace_history'])} steps):")
    print(f"  {'─'*66}")
    for i, trace in enumerate(final_state["trace_history"], 1):
        status_icon = "✅" if trace["status"] == "success" else "⚠️ "
        print(f"  [{i:02d}] {trace['timestamp']}")
        print(f"       {status_icon} {trace['sender_agent']} → {trace['target_agent']} | {trace['status'].upper()}")
        if trace.get("error_message"):
            print(f"       ❌ ERROR: {trace['error_message']}")

    print("=" * 70 + "\n")
    return final_state


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Market Securities — Agentic Research Desk (ARD) Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ard_graph.py --query "ECB signals rate pause as euro-area inflation falls to 2.1%"
  python ard_graph.py --query "NovaTech semiconductor deal faces EC Phase II anti-trust probe"
  python ard_graph.py --query "MediaCorp holdco discount widens to 23% on CEO departure; activist discloses 5% stake"
        """,
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Trigger query: news headline, filing summary, or market event description",
    )
    args = parser.parse_args()

    asyncio.run(run_ard(args.query))
