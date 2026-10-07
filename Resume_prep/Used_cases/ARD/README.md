# Market Securities — Agentic Research Desk (ARD)

**Use Case 1 from the Market Securities Agentic AI Case Study.**

A production-grade, multi-agent research pipeline that autonomously monitors macroeconomic signals, M&A filings, and special situations — then synthesizes them into a grounded, auditable institutional research note.

---

## Architecture

```
[Orchestrator Node]
        │
        ├── asyncio.gather() ──► [Central Bank Sentiment Agent]
        ├──────────────────────► [M&A Anti-Trust Arbitrage Agent]   (parallel)
        └──────────────────────► [Relative Value / Special Sits Agent]
                                              │
                                     [RAG Retriever Node]
                                    (Dense + Sparse + RRF)
                                              │
                                      [Synthesis Node]
                                    (LLM draft + retry)
                                              │
                                  [Groundedness Guard]  ← Blocking gate
                                    (LLM-as-a-Judge)
                                              │
                                     [Report Writer]
                                              │
                                      output/REPORT_*.json
```

---

## Production Features

| Feature | Implementation |
|---|---|
| **A2A Trace Envelopes** | Every node-to-node message is a Pydantic-validated `A2AMessageEnvelope` with `trace_id`, `timestamp`, `status` |
| **Circuit Breakers** | All external calls wrapped in `asyncio.wait_for(timeout=30s)` — failures route to HITL |
| **Schema Validation** | All agent outputs validated against `AgentOutput` Pydantic model |
| **Self-Correction Loops** | LLM is asked to fix its own output on schema errors (max 2 retries) |
| **Hybrid RAG** | Dense (OpenAI `text-embedding-3-small`) + Sparse (TF-IDF) merged via **Reciprocal Rank Fusion** |
| **Groundedness Guardrail** | Synchronous, blocking sentence-level SUPPORTED/CONTRADICTED/NEUTRAL check before publication |
| **HITL Escalation** | Any failure routes to `HITL_*.json` report for analyst review |
| **Full Audit Trail** | Timestamped JSON output with agent signals, sources cited, groundedness score |

---

## Setup

### 1. Install dependencies
```bash
cd ARD
pip install -r requirements.txt
```

### 2. Configure API keys
Edit `.env`:
```
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=ard-research-index
```

### 3. Ingest research corpus (run once)
```bash
python -m rag.ingest
```
This auto-creates 5 sample research files in `data/` and indexes them into Pinecone.

### 4. Run the pipeline
```bash
# Macro / central bank query
python ard_graph.py --query "ECB signals rate pause as inflation falls to 2.1%"

# M&A / event-driven query
python ard_graph.py --query "NovaTech semiconductor deal faces EC Phase II anti-trust probe"

# Special situations query
python ard_graph.py --query "MediaCorp holdco discount widens to 23% on CEO departure; activist discloses 5% stake"
```

---

## File Structure

```
ARD/
├── .env                          # API keys (never commit)
├── requirements.txt              # pip dependencies
├── ard_graph.py                  # 🔑 Main pipeline entry point
│
├── core/
│   ├── config.py                 # Pydantic settings
│   └── client.py                 # Singleton API clients
│
├── agents/
│   ├── central_bank_agent.py     # Hawkish/dovish sentiment analysis
│   ├── ma_arbitrage_agent.py     # Deal risk / anti-trust signals
│   └── special_situations_agent.py  # Holdco discounts, rebalancing, rights
│
├── rag/
│   ├── ingest.py                 # One-shot corpus ingestion to Pinecone
│   └── retriever.py              # Hybrid search + RRF
│
├── guardrails/
│   └── groundedness.py           # LLM-as-a-Judge groundedness evaluator
│
├── prompts/
│   └── agent_prompts.py          # All LLM system + user prompts
│
├── schemas/
│   └── contracts.py              # Pydantic A2A contracts, ARDState TypedDict
│
├── data/                         # Research corpus (auto-created on first ingest)
└── output/                       # Generated reports (auto-created)
```

---

## Output Example

### Approved Research Note (`output/REPORT_*.json`)
```json
{
  "report_type": "APPROVED_RESEARCH_NOTE",
  "trace_id": "ard_a3f2b91c",
  "groundedness_score": 0.92,
  "research_note": {
    "headline": "ECB Holds Steady as Euro-Area Inflation Approaches Target",
    "executive_summary": "...",
    "macro_commentary": "...",
    "event_driven_commentary": "...",
    "trade_ideas": ["Long Bunds vs UST 10yr", "..."],
    "risk_flags": ["Wage growth remains above target", "..."]
  },
  "agent_signals": { ... },
  "sources_cited": [ ... ]
}
```

### HITL Escalation (`output/HITL_*.json`)
Written when groundedness < 0.85 or any circuit breaker trips.
Analyst reviews draft, corrects, and re-approves manually.
