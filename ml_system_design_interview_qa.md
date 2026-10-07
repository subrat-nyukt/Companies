# ML System Design — Interview Questions & Answers
> **Scope:** End-to-end LLM / RAG / Recommendation systems, MLOps, and fundamentals.  
> Each section includes the question, a structured answer, and follow-up angles the interviewer may explore.

---

## Table of Contents
1. [End-to-End System Design (Ingestion → Serving)](#1-end-to-end-system-design)
2. [Cost Estimation & Reduction](#2-cost-estimation--reduction)
3. [Latency Reduction & Quality Trade-offs](#3-latency-reduction--quality-trade-offs)
4. [Self-Hosted vs. API LLMs](#4-self-hosted-vs-api-llms)
5. [Fine-Tuning on User Behavior](#5-fine-tuning-on-user-behavior)
6. [Dataset Construction, Loss Functions & MLOps](#6-dataset-construction-loss-functions--mlops)
7. [Database Selection: Vector, SQL, NoSQL](#7-database-selection)
8. [Metrics & Tracking](#8-metrics--tracking)
9. [System Monitoring & Debugging](#9-system-monitoring--debugging)
10. [Feedback Loop & Evaluation](#10-feedback-loop--evaluation)
11. [Making Systems More Deterministic](#11-making-systems-more-deterministic)
12. [Replacing Embedding Models Without Downtime](#12-replacing-embedding-models-without-downtime)
13. [Fallback Mechanisms](#13-fallback-mechanisms)

### Deep-Dive Favourites
14. [Solving Without LLMs or Vector DBs](#14-solving-without-llms-or-vector-dbs)
15. [Classical IR, Rules & Heuristics](#15-classical-ir-rules--heuristics)
16. [Making Systems More Deterministic (Deep Dive)](#16-making-systems-more-deterministic-deep-dive)
17. [Tokenization & Embeddings From Scratch](#17-tokenization--embeddings-from-scratch)
18. [What Happens During Fine-Tuning?](#18-what-happens-during-fine-tuning)

---

## 1. End-to-End System Design

### Q: Can you design a system end-to-end from ingestion to serving? What are the bottlenecks?

### Answer

#### High-Level Architecture

```
Raw Data Sources
      │
      ▼
[Ingestion Layer]
  - Batch: S3 + Spark / Kafka Connect
  - Streaming: Kafka → Flink / Spark Streaming
      │
      ▼
[Pre-processing & Feature Engineering]
  - Text cleaning, chunking, deduplication
  - Embedding generation (GPU batch workers)
      │
      ▼
[Storage Layer]
  - Raw: Data Lake (S3/GCS)
  - Features: Feature Store (Feast/Tecton)
  - Vectors: Vector DB (Pinecone / Weaviate / pgvector)
  - Metadata: PostgreSQL / DynamoDB
      │
      ▼
[Serving Layer]
  - API Gateway (rate limiting, auth)
  - Retrieval Service (ANN search)
  - LLM Orchestration (LangChain / custom)
  - LLM Inference (vLLM / TGI / OpenAI API)
      │
      ▼
[Observability]
  - Metrics: Prometheus + Grafana
  - Traces: OpenTelemetry + Jaeger
  - Logs: ELK / Loki
  - LLM Eval: Ragas / custom judges
```

#### Key Bottlenecks

| Stage | Bottleneck | Mitigation |
|---|---|---|
| **Ingestion** | I/O throughput, parsing PDFs/HTML | Parallelise workers, use Tika/Unstructured |
| **Embedding generation** | GPU cost & time | Batch-encode offline; cache embeddings |
| **ANN search** | Index freshness vs. recall trade-off | Use HNSW with ef_search tuning; async index updates |
| **LLM inference** | Token generation latency (TTFT, TPS) | vLLM continuous batching; speculative decoding |
| **Context window** | Long documents blow up cost & latency | Aggressive chunking + re-ranking top-k |
| **Retrieval quality** | Low recall → bad answers | Hybrid search (BM25 + dense); re-rankers |
| **Concurrency** | Single LLM node saturates | Autoscaling replicas; async queuing |

#### Chunking Strategy (often overlooked)
- **Fixed-size:** Simple, fast. Bad for semantic coherence.
- **Sentence/paragraph-aware:** Better coherence; use `spacy` or `nltk`.
- **Sliding window with overlap:** Prevents boundary artifacts.
- **Semantic chunking:** Embed then split where cosine distance jumps. Most expensive, highest quality.

#### Follow-up angles
- How do you handle document updates (mutation problem in vector DBs)?
- How do you handle multi-modal data (images, tables)?
- What's your strategy for cold-start when the vector index is empty?

---

## 2. Cost Estimation & Reduction

### Q: How would you estimate costs? How to reduce them?

### Answer

#### Cost Model for an LLM RAG System

```
Total Cost = Ingestion Cost + Storage Cost + Serving Cost

Ingestion:
  = N_docs × avg_chunks_per_doc × embedding_cost_per_chunk
  = 1M docs × 10 chunks × $0.0001/chunk (OpenAI ada-002) = $1,000/run

Storage:
  = N_vectors × dimension × bytes_per_float / GB_price
  = 10M × 1536 × 4B / 1e9 × $0.023/GB-month = ~$1.4/month (just raw data)
  (Managed vector DB: Pinecone at $70/pod/month is dominant)

Serving (LLM):
  = QPS × avg_tokens_per_request × price_per_1k_tokens
  = 100 QPS × 2000 tokens × ($0.002/1k) = $0.40/s = $34,560/day
  → This is where 90% of cost lives.
```

#### Cost Reduction Strategies

**1. Prompt compression**
- Remove redundant context before sending to LLM.
- Tools: LLMLingua, Selective Context.
- Can reduce token count 30–50% with <5% quality loss.

**2. Model routing (tiered inference)**
- Route simple queries → cheap small model (GPT-3.5, Mistral-7B).
- Route complex queries → expensive large model (GPT-4o, Claude Opus).
- Use a fast classifier (e.g., fine-tuned BERT) as the router.
- Typical savings: 60–80% cost reduction if 70% of queries are "simple."

**3. Caching**
- **Exact cache:** Hash prompt → cache response. High hit rate for FAQ-style.
- **Semantic cache:** Embed query → find near-duplicate cached answer (e.g., GPTCache).
- **KV cache reuse:** Keep system prompt KV cache warm (supported in vLLM, Anthropic).

**4. Quantization**
- INT8 / INT4 quantization of self-hosted models: 2–4× throughput, minimal quality drop.
- Use bitsandbytes, GPTQ, AWQ.

**5. Batching & throughput optimization**
- Continuous batching (vLLM): Eliminates GPU idle time between requests.
- Speculative decoding: Draft model generates tokens, large model verifies in parallel.

**6. Right-sizing retrieval**
- Smaller embedding models (MiniLM-L6 vs. text-embedding-3-large): 10× cheaper.
- Use ANN instead of exact search: Much cheaper at scale.
- Re-rank only top-K (K=50) rather than passing all to LLM.

**7. Data tiering**
- Hot: Fast vector DB (in-memory HNSW).
- Warm: Disk-based ANN (DiskANN, Faiss + mmap).
- Cold: Archive; only search on explicit request.

#### Follow-up angles
- How do you build a cost dashboard (per-query cost attribution)?
- How do you handle cost spikes (e.g., a viral event)?

---

## 3. Latency Reduction & Quality Trade-offs

### Q: How would you reduce latency? What is a good trade-off of latency vs. quality?

### Answer

#### Latency Budget Decomposition

```
Total P99 latency = 
  Auth/routing          (5ms)
+ ANN retrieval         (20ms)
+ Re-ranking            (50ms)
+ Prompt construction   (5ms)
+ LLM TTFT (time-to-first-token) (200–800ms)
+ LLM generation        (depends on output length)
+ Post-processing       (10ms)

Target: P50 < 1s, P99 < 3s for interactive use cases
```

#### Latency Reduction Techniques

**Retrieval tier**
| Technique | Latency Gain | Quality Impact |
|---|---|---|
| ANN (HNSW ef_search=50) vs exact | 10–100× faster | ~1–2% recall loss |
| Reduce top-k (100→20) | 2× faster | Risk of missing relevant docs |
| Cache popular queries | Near-zero | None |
| Co-locate vector DB with LLM | Save network RTT | None |

**LLM inference tier**
| Technique | Latency Gain | Quality Impact |
|---|---|---|
| Streaming (token-by-token) | Perceived latency ↓ | None (UX trick) |
| Smaller model (GPT-4o → GPT-3.5) | 3–5× faster | Significant for complex tasks |
| Speculative decoding | 2–3× on generation | Minimal |
| Flash Attention 2 | 2× on TTFT | None |
| vLLM continuous batching | Throughput ↑ | None |
| Reduce max output tokens | Linear with tokens | May truncate |
| Quantization (INT8) | 1.5–2× | <1% on benchmarks |

#### Good Trade-off Points

**Interactive chat (sub-2s required):**
- Use smaller model + aggressive caching + streaming.
- Accept slight quality drop; user gets fast, good-enough responses.
- Fallback to re-try with larger model if small model says "I don't know."

**Async workflows (minutes acceptable):**
- Use largest model, no caching needed.
- Full re-ranking pipeline, no compromise on quality.

**Batch analytics (hours acceptable):**
- Cheapest model, maximum batching, no latency concern.

#### The Latency vs. Quality Curve
```
Quality
  ↑
  |        ✦ GPT-4 + full pipeline
  |      ✦ GPT-4 + no reranker
  |    ✦ GPT-3.5 + reranker
  |  ✦ GPT-3.5 + no reranker
  |✦ Rule-based
  +---------------------------→ Latency (low = fast)
```
Sweet spot: **GPT-3.5-class model + lightweight re-ranker** often gives 80% of GPT-4 quality at 20% of cost and 3× lower latency.

---

## 4. Self-Hosted vs. API LLMs

### Q: Do you really need self-hosted LLMs? When is it needed?

### Answer

#### Decision Framework

| Factor | Use API (e.g., OpenAI) | Self-Host (e.g., vLLM + Llama) |
|---|---|---|
| **Data privacy** | Low sensitivity OK | PII, PHI, regulated data → must self-host |
| **Cost at scale** | < 1M tokens/day: API cheaper | > 10M tokens/day: self-host breaks even |
| **Customization** | Prompt engineering only | Fine-tuning, RLHF, custom tokenizer |
| **Latency SLA** | P50 500ms–2s | Can achieve P50 < 200ms with proper setup |
| **Model control** | No control over model updates | Full control over version pinning |
| **Compliance** | GDPR, HIPAA may prohibit | Required for air-gapped environments |
| **Operational burden** | None | Significant: GPU infra, updates, SRE |
| **Availability** | Provider SLA (99.9%) | You own it; requires HA design |

#### When Self-Hosting Is Required
1. **Regulated industries:** Healthcare (HIPAA), Finance (SOC2), Government (FedRAMP).
2. **Air-gapped environments:** Defense, classified systems.
3. **High QPS at large scale:** >1B tokens/day where API cost is prohibitive.
4. **Need for fine-tuned models:** Domain adaptation that API vendors don't support.
5. **Inference latency < 100ms:** API network overhead alone exceeds this.
6. **Multi-tenant isolation:** Need strict tenant-level model isolation.

#### Self-Hosting Stack
```
Model: Llama 3.1, Mistral, Qwen, Falcon
Inference Server: vLLM (recommended) / TGI / Triton + TensorRT
Hardware: A100/H100 for large models; L4/A10G for smaller ones
Scaling: Kubernetes + GPU operator + HPA
Monitoring: Prometheus + custom LLM metrics (TTFT, TPS, queue depth)
```

#### Cost Crossover Point (rule of thumb)
- A100 80GB instance: ~$3/hour on-demand, ~$1.5/hour reserved.
- Can serve Llama-3-70B at ~500 tokens/s.
- OpenAI GPT-4o: $5/1M input tokens.
- At 500 tokens/s continuous load: $1.8/hr cost vs. $9/hr API cost → self-host wins.
- Below ~20% GPU utilization: API is cheaper (you pay for idle GPU).

---

## 5. Fine-Tuning on User Behavior

### Q: How would you fine-tune language models on user behavior? Which framework? What about model serving?

### Answer

#### Types of Fine-Tuning

| Type | What it learns | Data needed | Use case |
|---|---|---|---|
| **Supervised Fine-Tuning (SFT)** | Imitate examples | (prompt, ideal response) pairs | Domain adaptation, style |
| **RLHF** | Human preferences | Pairwise rankings | Align to user satisfaction |
| **DPO (Direct Preference Optimization)** | Preferences without RL | (prompt, chosen, rejected) | Simpler alternative to RLHF |
| **ORPO** | Single-stage preference | Same as DPO | Even simpler, newer |

#### Collecting User Behavior Data

**Implicit signals:**
- Thumbs up/down on responses.
- Copy-to-clipboard events (strong positive signal).
- Re-generation requests (negative signal).
- Dwell time on response.
- Follow-up questions asking for clarification (negative).

**Explicit signals:**
- Star ratings.
- "Report a problem" with category.
- A/B test outcomes (conversion, task completion).

**Data Pipeline:**
```
User interaction events
    → Kafka topic
    → Flink/Spark processing
    → Deduplicate, filter low-quality
    → Label studio / annotation pipeline (for ambiguous cases)
    → Training dataset (Parquet on S3)
    → Fine-tuning job trigger
```

#### Framework Recommendation

| Framework | Best for | Notes |
|---|---|---|
| **Hugging Face TRL** | SFT, DPO, RLHF | Most widely used; great ecosystem |
| **Axolotl** | SFT + QLoRA | Config-driven; production-friendly |
| **LLaMA-Factory** | Multi-method fine-tuning | Excellent for Llama family |
| **Unsloth** | Fast LoRA on consumer GPU | 2× speed vs. HF TRL |
| **OpenRLHF** | Large-scale RLHF (Ray-based) | For serious RLHF at scale |

**Recommended stack for most teams:**
```
Fine-tuning: Axolotl or TRL + LoRA/QLoRA
Orchestration: Kubernetes + Ray Train (distributed)
Experiment tracking: MLflow or W&B
Model registry: MLflow or HuggingFace Hub (private)
```

#### LoRA Configuration (typical)
```python
lora_config = LoraConfig(
    r=16,                    # Rank: 8–64, higher = more capacity
    lora_alpha=32,           # Scaling factor; often 2×r
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM"
)
```

#### Model Serving After Fine-Tuning
1. **Merge LoRA weights** into base model (`merge_and_unload()`).
2. **Quantize** to INT8/INT4 (optional, for cost/speed).
3. **Convert** to optimized format (vLLM auto-handles HF models; or use TensorRT-LLM for max performance).
4. **Deploy** behind vLLM with an OpenAI-compatible API.
5. **Shadow deploy** first: Route 5% traffic, compare against production model.
6. **Blue-green or canary** rollout after quality validation.

---

## 6. Dataset Construction, Loss Functions & MLOps

### Q: How would you construct the dataset, what about loss function, and MLOps?

### Answer

#### Dataset Construction

**Step 1: Source identification**
- Domain documents (PDFs, wikis, internal KB).
- User query logs (with PII scrubbed).
- Expert-written Q&A pairs.
- Synthetic data generated by a stronger model (GPT-4 as teacher).

**Step 2: Quality filters**
```python
filters = [
    "length_filter",        # Remove < 50 or > 4096 tokens
    "language_filter",      # English-only if needed
    "dedup_minhash",        # MinHash LSH deduplication
    "perplexity_filter",    # Remove low-perplexity (templated) text
    "toxicity_filter",      # Remove harmful content
    "pii_scrubber",         # Remove emails, phone numbers, SSN
]
```

**Step 3: Dataset format (SFT)**
```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful data quality expert."},
    {"role": "user", "content": "What does NULL mean in this column?"},
    {"role": "assistant", "content": "A NULL value indicates..."}
  ]
}
```

**Step 4: Train/val/test splits**
- 80/10/10 for SFT.
- Ensure temporal split if using user logs (train on old data, eval on recent).
- Ensure no leakage between splits (deduplicate across splits).

#### Loss Functions

**Supervised Fine-Tuning (SFT):**
```
L_SFT = -Σ log P(y_t | y_{<t}, x)
```
- Standard causal language modeling loss.
- Only compute loss on **assistant tokens**, not prompt tokens (mask the prompt).
- Use `DataCollatorForSeq2Seq` with appropriate attention masks in HF.

**DPO (Direct Preference Optimization):**
```
L_DPO = -log σ(β * log[π_θ(y_w|x)/π_ref(y_w|x)] - β * log[π_θ(y_l|x)/π_ref(y_l|x)])
```
- `y_w` = chosen (winner) response, `y_l` = loser (rejected) response.
- β controls divergence from reference model (typically 0.1–0.5).
- Requires a frozen reference model.

**RLHF (PPO):**
```
L_PPO = E[r(x, y)] - β * KL(π_θ || π_ref)
```
- Reward model scores responses.
- KL penalty prevents reward hacking.
- More complex, requires separate reward model training.

#### MLOps Pipeline

```
Code change (Git PR)
    → CI: unit tests, lint, schema validation
    → Dataset versioning: DVC or Delta Lake
    → Training job: Kubernetes Job / Ray Train
    → Experiment tracking: W&B / MLflow
    → Model evaluation: automated test suite (Ragas, custom evals)
    → Model registry: MLflow or HF Hub (versioned, tagged)
    → Staging deploy: shadow traffic (5%)
    → A/B test: 10% canary
    → Full rollout: if metrics pass gates
    → Monitoring: track production metrics vs. pre-deploy baseline
    → Auto-rollback: if error rate or quality metrics degrade
```

**Key MLOps Principles:**
- **Reproducibility:** Pin dataset version, model checkpoint, and library versions together.
- **Data lineage:** Track which data version trained which model.
- **Evaluation gates:** No model ships without passing offline evals (ROUGE, BLEU, custom LLM judge).
- **Drift detection:** Monitor embedding drift and output distribution over time.

---

## 7. Database Selection

### Q: Which database would you use and why? Vector DB? SQL? NoSQL?

### Answer

#### Decision Matrix

| Data type | Database | Why |
|---|---|---|
| User profiles, metadata | **PostgreSQL** | ACID, complex queries, relations |
| High-throughput events/logs | **Cassandra / DynamoDB** | Write-heavy, horizontal scale |
| Session / ephemeral state | **Redis** | Sub-ms reads, TTL support |
| Document store (flexible schema) | **MongoDB / Firestore** | Semi-structured data, flexible fields |
| Search / BM25 | **Elasticsearch / OpenSearch** | Full-text search, faceted filtering |
| Vectors / semantic search | **pgvector / Pinecone / Weaviate** | ANN search |
| Analytics / OLAP | **BigQuery / Snowflake / ClickHouse** | Column-store, fast aggregations |
| Feature store | **Redis + S3 (Feast)** | Online + offline feature serving |

#### Vector DB Comparison

| DB | Strengths | Weaknesses | Best for |
|---|---|---|---|
| **pgvector** | Free, existing Postgres | Slower ANN at >10M vecs | Small-medium scale |
| **Pinecone** | Managed, fast, simple API | Expensive, proprietary | Quick MVP, managed |
| **Weaviate** | Hybrid search built-in, open-source | Complex ops | Hybrid BM25+dense |
| **Qdrant** | Rust-based, fast, payloads | Newer, smaller community | Performance-critical |
| **Milvus** | Cloud-native, massive scale | Complex to operate | Large-scale enterprise |
| **Chroma** | Dev-friendly, embedded | Not production-ready | Local dev / prototyping |

#### Architecture Pattern (RAG system)

```
PostgreSQL:
  - users, documents, chunks metadata
  - query logs, feedback

pgvector (or Pinecone):
  - chunk_id → embedding
  - Filtered ANN search by doc_id, date range

Redis:
  - Semantic cache (query hash → response)
  - Rate limiting counters
  - Session state

Elasticsearch:
  - BM25 keyword search
  - Combined with vector search for hybrid retrieval

S3 / GCS:
  - Raw documents
  - Model checkpoints
  - Training datasets (versioned)
```

#### Why Not One Database for Everything?
- **Polyglot persistence** is the norm in production: each store is optimized for its access pattern.
- The overhead of managing multiple stores is worth the performance and cost gains.
- **Exception:** For small projects, Postgres + pgvector + Elasticsearch covers most needs.

---

## 8. Metrics & Tracking

### Q: What metrics would you track? How?

### Answer

#### Metric Categories

**Business Metrics (Outcome)**
- Task completion rate (did user achieve their goal?).
- User retention (DAU/MAU).
- Revenue per interaction (for commercial products).
- Session length, re-engagement rate.

**Product Metrics (Usage)**
- Query volume (QPS, total queries/day).
- Thumbs up/down ratio.
- Re-generation rate (negative signal).
- Abandonment rate (user leaves without getting answer).

**LLM Quality Metrics (Offline)**
| Metric | What it measures | Tool |
|---|---|---|
| ROUGE-L | Recall of reference text | `evaluate` library |
| BLEU | N-gram precision | `sacrebleu` |
| BERTScore | Semantic similarity | `bert-score` |
| G-Eval | LLM-as-judge (faithfulness, coherence) | Ragas, custom |
| Faithfulness | Is answer grounded in retrieved docs? | Ragas |
| Answer Relevancy | Does answer address the question? | Ragas |
| Context Recall | Did retrieval find the right docs? | Ragas |

**System Metrics (Infrastructure)**
- P50/P90/P99 latency (per stage).
- Time-to-first-token (TTFT).
- Tokens per second (TPS).
- GPU utilization, memory usage.
- Cache hit rate.
- Error rate, 4xx/5xx ratio.
- Queue depth (backpressure indicator).

**Cost Metrics**
- Cost per query.
- Cost per 1M tokens (input vs. output).
- Total inference spend per day.

#### Tracking Stack

```
Application metrics:
  Python → prometheus_client → Prometheus → Grafana dashboards

LLM-specific:
  LangSmith / W&B Traces / Arize Phoenix → Trace individual LLM calls

Logs:
  Structured JSON logs → Loki / ELK → Kibana / Grafana

Experiments:
  W&B / MLflow → Compare model versions, hyperparameters

Alerts:
  Prometheus AlertManager → PagerDuty / Slack
```

---

## 9. System Monitoring & Debugging

### Q: What about system monitoring? How would you debug failure cases?

### Answer

#### Monitoring Architecture

```
                    ┌─────────────────┐
                    │   Grafana       │ ← Dashboards
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         Prometheus      Loki/ELK      Jaeger/Tempo
         (metrics)       (logs)        (traces)
              │              │              │
    ─────────────────────────────────────────
         Application, LLM, Vector DB, GPU nodes
```

#### What to Monitor

**Four Golden Signals (SRE classic):**
1. **Latency:** P50, P95, P99 of end-to-end and per-stage.
2. **Traffic:** QPS, concurrent requests.
3. **Errors:** HTTP 5xx, LLM API failures, timeout rate.
4. **Saturation:** GPU utilization, memory pressure, queue depth.

**LLM-Specific:**
- Output token length distribution (detect prompt injection / jailbreaks causing long outputs).
- Refusal rate (model saying "I can't help with that").
- Hallucination rate (use LLM-as-judge on sample of traffic).
- Retrieval quality (context relevance score).

#### Debugging Failure Cases

**Failure taxonomy:**
```
1. Retrieval failure    → Wrong or no docs retrieved
2. Hallucination        → LLM generates false info
3. Refusal             → LLM refuses valid query
4. Latency spike       → P99 blows up
5. Token overflow      → Context exceeds window
6. Cascade failure     → Upstream service down
```

**Debug workflow:**
```
Alert fires (e.g., user satisfaction drop)
    ↓
Check Grafana: which metric degraded? when did it start?
    ↓
Check logs: are there error patterns? new query types?
    ↓
Trace a failing request end-to-end in Jaeger
    ↓
Reproduce in staging with same input
    ↓
Root cause: retrieval? LLM? prompt? data?
    ↓
Fix: patch prompt, re-index, add guardrail, tune ef_search
    ↓
Validate fix in staging → canary → full rollout
```

**Practical debugging tips:**
- Log **every LLM request and response** (with sampling for high QPS).
- Log **retrieved document IDs and scores** for every query.
- Use **request IDs** propagated through all services (correlation ID).
- Maintain a **golden test set** of known good (query, expected answer) pairs; run on every deploy.

---

## 10. Feedback Loop & Evaluation

### Q: What about feedback loop? How would we track and evaluate?

### Answer

#### Feedback Collection Architecture

```
User Interaction
    │
    ├── Explicit: thumbs up/down, star rating, corrections
    └── Implicit: dwell time, copy, re-generate, click-through

    ↓
Event Stream (Kafka)
    ↓
Feedback Processor (Flink)
    ↓
Feedback Store (PostgreSQL)
    ↓
    ├── Online: Update user preference model (cold-start mitigation)
    ├── Periodic: Build DPO training pairs (chosen/rejected)
    └── Batch: Trigger retraining when data threshold met
```

#### Evaluation Framework (Online + Offline)

**Offline Evaluation (pre-deploy)**
```
Golden test set → Run candidate model → Score with:
  - Automated metrics (ROUGE, BERTScore)
  - LLM judge (GPT-4o rates faithfulness, coherence 1–5)
  - Regression suite (known bad behaviors that must not recur)
  
Threshold: Must improve on 3 of 5 metrics, no regression on any.
```

**Online Evaluation (post-deploy)**
```
A/B test: 5% new model, 95% control
Track:
  - Thumbs up rate (primary metric)
  - Re-generation rate (negative)
  - Task completion (via downstream conversion)
  - Latency delta

Decision rule: Statistical significance (p < 0.05) AND practical significance (>2% improvement)
```

**Human Evaluation (periodic)**
- Weekly "red team" session: QA team tries to break the system.
- Monthly "eval sprint": 200 randomly sampled queries rated by 3 annotators.
- Inter-annotator agreement tracked (Cohen's κ > 0.7 required).

#### Closing the Loop

```
Data → Train → Deploy → Monitor → Collect feedback → Data
  ↑_______________________________________________|
```

- **Flywheel effect:** More users → more data → better model → more users.
- **Avoid data poisoning:** Filter adversarial feedback (bot traffic, coordinated downvoting).
- **Label efficiency:** Use active learning to select the most informative samples for human labeling.

---

## 11. Making Systems More Deterministic

### Q: How would you make the system more deterministic?

### Answer

#### Sources of Non-Determinism in LLM Systems

1. **Temperature > 0** in LLM sampling.
2. **Top-p / top-k** sampling randomness.
3. **Non-deterministic ANN search** (approximate, not exact).
4. **Floating-point non-determinism** in GPU operations.
5. **Prompt variability** (date injection, dynamic context).
6. **Model updates** by API providers (breaking changes).

#### Strategies for Determinism

**At inference:**
```python
# Force deterministic LLM output
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    temperature=0,        # Greedy decoding
    seed=42,              # OpenAI reproducibility seed (best-effort)
    top_p=1,
)
```

**At retrieval:**
- Use **exact search** (Faiss `IndexFlatIP`) instead of ANN for determinism.
- Fix the ANN index version; don't update during a request.

**At the prompt level:**
- **Remove dynamic elements** (e.g., current date) if they affect output.
- **Pin examples** in few-shot prompts; don't shuffle them.
- Use **structured output** (JSON mode, grammar-constrained decoding).

**At the system level:**
- **Version-pin** the model: Use `gpt-4o-2024-08-06` not `gpt-4o` (which can change).
- **Snapshot the index:** Tag and lock the vector DB version used for a given experiment.
- **Freeze the prompt template** in code review before experiments.

**Grammar-constrained decoding (most powerful):**
```python
# Using Outlines / guidance / LM-format-enforcer
from outlines import models, generate

model = models.transformers("mistralai/Mistral-7B")
generator = generate.json(model, OutputSchema)
result = generator(prompt)  # Guaranteed valid JSON
```

#### Trade-off
- **Full determinism** (temperature=0, exact search) → Lower diversity, may miss correct answers that require exploration.
- **Sweet spot:** Temperature=0 for classification/extraction; temperature=0.3 for open-ended generation.

---

## 12. Replacing Embedding Models Without Downtime

### Q: How would you replace embedding models and backfill embeddings without any downtime?

### Answer

#### The Problem
- Embeddings from Model A and Model B are **incompatible** (different vector spaces).
- You cannot mix them in the same index.
- You have 10M+ documents to re-embed.
- System must serve traffic throughout.

#### Solution: Blue-Green Index Migration

```
Phase 1: Build shadow index (offline)
  - Spin up embedding workers (GPU batch)
  - Re-embed all documents with Model B
  - Write to NEW vector index (Pinecone namespace B / new Weaviate class)
  - Run in parallel with live index (Model A)

Phase 2: Validate (offline)
  - Run retrieval quality tests on both indexes
  - Compare NDCG, recall@K on golden query set
  - Confirm Model B ≥ Model A quality threshold

Phase 3: Shadow traffic (no user impact)
  - Route 100% of queries to Model A (live) + Model B (shadow)
  - Log both results, compare offline
  - Do NOT serve Model B results yet

Phase 4: Canary switch (5% traffic)
  - Route 5% of queries to Model B index
  - Monitor: latency, error rate, user satisfaction
  - Hold for 24–48h

Phase 5: Full cutover
  - Gradually increase to 100%
  - Keep Model A index warm for 1 week (instant rollback)

Phase 6: Cleanup
  - Decommission Model A index
  - Remove shadow query routing
```

#### Key Details

**Re-embedding at scale:**
```python
# Batch re-embedding with async workers
async def embed_batch(chunks: List[str], model) -> List[np.ndarray]:
    embeddings = await model.aencode(chunks, batch_size=256)
    return embeddings

# Use Ray or Celery for distributed backfill
# Typical throughput: 10M chunks / hour on 4× A10G GPUs
```

**Handling new documents during migration:**
- Write to **both** indexes during transition (dual-write pattern).
- After cutover, stop dual-write.

**Rollback:**
- Keep old index alive.
- Toggle feature flag to switch back to Model A index.
- Zero-downtime rollback in seconds.

---

## 13. Fallback Mechanisms

### Q: What are the fallback mechanisms?

### Answer

#### Failure Modes & Fallbacks

| Failure | Detection | Fallback |
|---|---|---|
| LLM API timeout | Latency > threshold | Retry → smaller model → cached response → graceful error |
| LLM hallucination | Faithfulness score < 0.5 | Return retrieved text directly (no generation) |
| Vector DB down | Health check fail | Fall back to Elasticsearch BM25 search |
| No relevant docs found | Retrieval score < threshold | Trigger keyword search; ask user to rephrase |
| Rate limit hit | 429 response | Queue request; exponential backoff; secondary API key |
| Model quality regression | Online metrics drop | Auto-rollback to previous model version |
| Prompt injection detected | Rule-based or LLM guard | Reject request, log, alert security team |
| Context overflow | Token count > limit | Truncate context; summarize oldest chunks |

#### Fallback Chain Example

```
User query
    ↓
Try primary LLM (GPT-4o)
    ↓ (failure / timeout)
Try secondary LLM (Claude Sonnet)
    ↓ (failure / timeout)
Try self-hosted model (Llama-3-8B)
    ↓ (failure)
Return cached response if available
    ↓ (no cache)
Return extracted text from top retrieved document (no generation)
    ↓ (retrieval also failed)
Graceful error: "I'm unable to answer right now. Please try again."
```

#### Circuit Breaker Pattern

```python
from pybreaker import CircuitBreaker

# Opens circuit after 5 failures in 60s; resets after 30s
llm_breaker = CircuitBreaker(fail_max=5, reset_timeout=30)

@llm_breaker
def call_llm(prompt):
    return openai_client.chat.completions.create(...)

# When circuit is open, falls through to fallback immediately
# Prevents cascading failures from hammering a down service
```

---

---

# Deep-Dive Favourites

---

## 14. Solving Without LLMs or Vector DBs

### Q: How would you solve this problem without LLMs or vector DBs?

### Answer (using a RAG/Q&A system as example)

#### Classical Approach Stack

```
User query
    ↓
Query preprocessing:
  - Spelling correction (SymSpell, pyspellchecker)
  - Synonym expansion (WordNet)
  - Named entity extraction (spaCy NER)
    ↓
BM25 / TF-IDF search (Elasticsearch / Whoosh)
    ↓
Rule-based ranking:
  - Recency boost
  - Source authority score
  - Exact match bonus
    ↓
Template-based answer generation:
  - Extract top-ranked sentence
  - Fill template: "Based on [source], [sentence]"
    ↓
Response
```

#### When This Works Better Than LLMs
- **High-precision requirements:** Legal, compliance — LLMs hallucinate; rule systems don't.
- **Low latency (<10ms):** BM25 search is orders of magnitude faster.
- **Explainability required:** Can trace exactly why a result was returned.
- **Small domain:** 10,000 documents × well-defined vocabulary → BM25 recall is excellent.
- **Low budget:** No GPU, no API cost.

#### Practical Example: FAQ bot without LLMs
```python
from rank_bm25 import BM25Okapi
import spacy

nlp = spacy.load("en_core_web_sm")
faq_texts = [...]  # List of FAQ strings
tokenized = [nlp(t) for t in faq_texts]
bm25 = BM25Okapi([[tok.lemma_.lower() for tok in doc 
                   if not tok.is_stop] for doc in tokenized])

def answer(query):
    tokens = [tok.lemma_.lower() for tok in nlp(query) if not tok.is_stop]
    scores = bm25.get_scores(tokens)
    top_idx = scores.argmax()
    if scores[top_idx] > 2.0:  # Confidence threshold
        return faq_texts[top_idx]
    return "Sorry, I couldn't find a relevant answer."
```

---

## 15. Classical IR, Rules & Heuristics

### Q: Can you solve the problem with classical IR, rules, and heuristics?

### Answer

#### Classical IR Toolkit

**TF-IDF (Term Frequency-Inverse Document Frequency):**
```
TF(t, d)  = count(t in d) / total_words(d)
IDF(t)    = log(N / df(t))  # N = total docs, df = docs containing t
TF-IDF    = TF × IDF
```
Good for: keyword matching, document similarity, feature engineering.

**BM25 (Best Match 25):**
```
BM25(q, d) = Σ IDF(q_i) × [f(q_i, d) × (k1+1)] / [f(q_i, d) + k1×(1 - b + b×|d|/avgdl)]
```
- k1 ∈ [1.2, 2.0]: term frequency saturation.
- b = 0.75: document length normalization.
- **Default gold standard for keyword search;** beats neural search on out-of-domain data.

**Rule-Based Systems:**
```python
# Data quality rule recommendation (relevant to your codebase)
rules = {
    "null_check": lambda col: col.isnull().any(),
    "range_check": lambda col, lo, hi: ((col < lo) | (col > hi)).any(),
    "format_check": lambda col, pattern: ~col.str.match(pattern).all(),
    "uniqueness_check": lambda col: col.duplicated().any(),
}

def recommend_rules(df):
    recommendations = []
    for col in df.columns:
        for rule_name, condition in rules.items():
            try:
                if condition(df[col]):
                    recommendations.append((col, rule_name))
            except TypeError:
                pass
    return recommendations
```

**Heuristics for ranking:**
- Recency: `score += (1 / days_since_update) × recency_weight`
- Popularity: `score += log(1 + click_count) × popularity_weight`
- Exact match bonus: `score *= 2.0 if query_term in title else 1.0`

#### Hybrid Approach (Best of Both Worlds)
```
Final score = α × BM25_score + (1-α) × dense_score
```
- α ∈ [0.3, 0.7] tuned on validation set.
- **Reciprocal Rank Fusion (RRF)** is a parameter-free alternative:
  ```
  RRF(d) = Σ 1 / (k + rank_i(d))   # k=60 is standard
  ```

---

## 16. Making Systems More Deterministic (Deep Dive)

*(See [Section 11](#11-making-systems-more-deterministic) for the full answer)*

### Additional depth: Why is LLM non-determinism a problem?

- **Reproducibility:** Cannot reproduce a bug because the same prompt gives different outputs.
- **Testing:** Unit tests on LLM outputs are flaky.
- **Trust:** Users see inconsistent answers to the same question.
- **Auditing:** Cannot explain why a specific answer was generated.

### Structured Outputs (most practical fix)
Force the model to output a predefined schema:
```python
from pydantic import BaseModel
from openai import OpenAI

class DataQualityRule(BaseModel):
    rule_name: str
    column: str
    threshold: float
    severity: Literal["low", "medium", "high"]

client = OpenAI()
response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}],
    response_format=DataQualityRule,
    temperature=0,
)
rule = response.choices[0].message.parsed
# Guaranteed to be a valid DataQualityRule object
```

---

## 17. Tokenization & Embeddings From Scratch

### Q: Can you explain tokenization and embeddings from scratch?

### Answer

#### Tokenization

**What is it?**
Converting raw text into a sequence of integers (token IDs) that a model can process.

**Why not just use characters or words?**
- Characters: Sequences are very long (25k chars for this document). Hard to learn long-range dependencies.
- Words: Vocabulary explosion (>1M unique words). Can't handle unknown words (OOV problem).
- **Subwords (BPE/WordPiece):** Middle ground — frequent words are one token; rare words split into subwords. Vocabulary stays manageable (~32K–128K tokens).

**Byte Pair Encoding (BPE) — how it works:**
```
Step 1: Start with character vocabulary
  "low", "lower", "newest", "widest"
  → l, o, w, e, r, n, s, t, i, d, </w>

Step 2: Count most frequent adjacent pair
  ("e", "s") appears most → merge to "es"
  Vocabulary: l, o, w, e, r, n, es, t, i, d, </w>

Step 3: Repeat until vocabulary reaches target size
  ("es", "t") → "est"
  ("l", "o") → "lo"
  ("lo", "w") → "low"
  ...

Result: Common words = 1 token; rare words = multiple tokens
  "tokenization" → ["token", "ization"]
  "supercalifragilistic" → ["super", "cal", "if", "rag", "ilis", "tic"]
```

**WordPiece (BERT):** Similar to BPE but merges based on likelihood gain:
```
score(A, B) = P(AB) / (P(A) × P(B))
```
Uses `##` prefix to mark continuation: `playing` → `play`, `##ing`.

**SentencePiece (Llama, T5):**
- Treats input as a raw byte stream (no pre-tokenization on whitespace).
- Language-agnostic; works well for multilingual models.

**Why does tokenization matter?**
- Costs: You pay per token, not per character.
- Context window: 4096 tokens ≠ 4096 words. English: ~1 token per 0.75 words.
- Performance: Some languages (Chinese, Arabic) tokenize very inefficiently in Western-trained models.
- Prompt sensitivity: Changing a single character can change token boundaries and alter behavior.

#### Embeddings

**What is an embedding?**
A dense vector representation of a discrete object (token, sentence, document) in a continuous vector space, where **semantic similarity ≈ geometric proximity**.

**How word embeddings are learned (Word2Vec intuition):**
```
Training objective (Skip-gram):
  "The cat sat on the mat"
  Predict context words given center word:
  P("cat" | "sat") should be high
  P("dog" | "sat") should also be moderate (semantically similar)

The neural network learns:
  cat  → [0.2, -0.8, 0.4, ..., 0.1]  (300-dim)
  dog  → [0.3, -0.7, 0.5, ..., 0.2]  (similar direction)
  king → [0.9,  0.3, 0.1, ..., 0.8]
  
Famous: king - man + woman ≈ queen  (vector arithmetic on meaning)
```

**Transformer embeddings (BERT, sentence-transformers):**

*Token embeddings:*
```
Each token ID → lookup in embedding matrix E ∈ R^(vocab_size × d_model)
+ positional encoding (to inject order information)
```

*Positional encoding (original Transformer):*
```
PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
```
Learned positional embeddings (GPT, BERT) are also common.

*Sentence / document embeddings:*
```
Option 1: [CLS] token output from BERT (fine-tuned for similarity)
Option 2: Mean pooling of all token outputs
Option 3: Dedicated model: sentence-transformers (all-MiniLM-L6-v2)

Trained with contrastive loss:
  L = -log[exp(sim(q, d+)/τ) / Σ exp(sim(q, d_i)/τ)]
  q = query, d+ = positive doc, d_i = all docs in batch
  τ = temperature (e.g., 0.07)
```

**Cosine similarity:**
```
cos(A, B) = (A · B) / (||A|| × ||B||)

Range: [-1, 1]
1   = identical direction (same meaning)
0   = orthogonal (unrelated)
-1  = opposite (antonyms)
```

**Why high dimensions (768, 1536)?**
- Higher dimensions → more capacity to encode semantic nuance.
- But: "curse of dimensionality" — ANN search gets harder.
- Practical sweet spot: 256–1024 dims for most applications.
- Matryoshka embeddings (OpenAI's approach): Train so that first 256 dims already encode the most important information; truncate for speed.

---

## 18. What Happens During Fine-Tuning?

### Q: What happens during fine-tuning? optimizer, learning rate, layer freezing? — not just "let's use LoRA"

### Answer

#### The Full Picture

Fine-tuning = continuing gradient descent on a pre-trained model's weights using a task-specific dataset.

#### Forward Pass
```
Input tokens → Embedding layer → N × Transformer blocks → Output logits → Loss
```

Each transformer block computes:
```
Attention:
  Q = X @ W_Q,  K = X @ W_K,  V = X @ W_V
  Attention = softmax(QK^T / √d_k) @ V
  
FFN:
  h = GELU(X @ W_1 + b_1) @ W_2 + b_2
  
Add residual connections + LayerNorm at each step
```

#### Backward Pass
```
Loss → ∂L/∂output → backprop through each layer → ∂L/∂W for every parameter
```

**Why is this expensive?**
- GPT-3 (175B params): Gradients alone require 175B × 4 bytes = 700GB (fp32).
- Full optimizer state (Adam): 3× weights = 2.1TB for GPT-3 alone.
- This is why we use LoRA, mixed precision, and gradient checkpointing.

#### Optimizer

**Adam (most common):**
```
m_t = β₁ × m_{t-1} + (1-β₁) × g_t         # 1st moment (momentum)
v_t = β₂ × v_{t-1} + (1-β₂) × g_t²        # 2nd moment (adaptive scale)
m̂_t = m_t / (1-β₁^t)                       # Bias correction
v̂_t = v_t / (1-β₂^t)
θ_t = θ_{t-1} - α × m̂_t / (√v̂_t + ε)
```
- β₁ = 0.9, β₂ = 0.999, ε = 1e-8 (defaults).
- Adapts learning rate per-parameter based on gradient history.
- **AdamW:** Adam + weight decay decoupled from gradient update (regularization).

**Why not SGD?**
- LLMs have very non-uniform gradient scales across layers.
- Adam's per-parameter learning rates handle this naturally.
- SGD requires very careful learning rate tuning and momentum.

#### Learning Rate

**Why LR matters most in fine-tuning:**
- Too high: Catastrophic forgetting — overwrites pre-trained knowledge.
- Too low: No learning (gradient updates too small to matter).

**Typical values:**
- Full fine-tuning: 1e-5 to 5e-5 (start low; model is fragile).
- LoRA fine-tuning: 1e-4 to 3e-4 (LoRA weights start from zero; need larger LR).

**Learning rate schedule:**

*Warmup + cosine decay (most common):*
```
Warmup (0 → lr_max over N_warmup steps):
  lr = lr_max × (step / N_warmup)

Cosine decay (lr_max → lr_min over N_total steps):
  lr = lr_min + 0.5 × (lr_max - lr_min) × (1 + cos(π × step / N_total))
```

*Why warmup?*
- At step 0, Adam's moment estimates are near zero → biased.
- Gradients at initialization can be large and noisy.
- Warmup prevents early unstable updates from derailing training.

#### Layer Freezing

**What is it?**
Setting `requires_grad = False` on specific parameters — their weights don't update.

**Why freeze?**
- Prevent catastrophic forgetting of pre-trained knowledge.
- Reduce GPU memory usage (no gradient storage for frozen params).
- Speed up training (no backward pass through frozen layers).

**Strategies:**

*Freeze embeddings only:*
```python
for param in model.model.embed_tokens.parameters():
    param.requires_grad = False
```
Keeps word representations stable; allows all transformer layers to adapt.

*Progressive unfreezing:*
```
Epoch 1: Train only top 2 layers (classifier head)
Epoch 2: Unfreeze top 4 layers
Epoch 3: Unfreeze all layers with small LR
```
Gradually adapts from task-specific to general features.

*Freeze all, train only head:*
```python
for param in model.parameters():
    param.requires_grad = False
for param in model.lm_head.parameters():
    param.requires_grad = True
```
Useful when pre-trained features are already good; just adapt the output mapping.

#### LoRA — What Actually Happens
LoRA doesn't "just use LoRA." Here's what it does:

```
Original weight matrix W ∈ R^(d_out × d_in)
  - Frozen during fine-tuning (requires_grad = False)

LoRA adds:
  ΔW = B @ A   where B ∈ R^(d_out × r), A ∈ R^(r × d_in), r << d
  
Forward pass:
  h = W x + (B @ A) x × (α / r)

Initialization:
  A ~ N(0, σ²)   (random)
  B = 0           (so ΔW = 0 at init; training starts from pretrained behavior)

Only A and B are trained.
Parameter reduction: instead of d_out × d_in, train d_out×r + r×d_in
Example: d_out=4096, d_in=4096, r=16
  Full: 16.7M params per layer
  LoRA: 4096×16 + 16×4096 = 131K params per layer (127× reduction)
```

**Which matrices to apply LoRA to?**
```python
target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",  # Attention
                  "gate_proj", "up_proj", "down_proj"]       # FFN (optional)
```
Adding FFN layers increases capacity; often needed for domain-heavy fine-tuning.

#### Mixed Precision Training
```
Weights stored in: fp16 or bf16 (half precision)
  → 2× memory savings vs fp32
  → Faster GPU operations (Tensor Cores optimized for fp16)

Master weights (optimizer state): fp32
  → Prevents precision loss during gradient accumulation

bf16 vs fp16:
  fp16: 5 exponent bits, 10 mantissa bits → overflow risk at large values
  bf16: 8 exponent bits, 7 mantissa bits → same range as fp32, safer for LLMs
  → Use bf16 on A100/H100 (native support); fp16 on older GPUs
```

#### Gradient Checkpointing
```
Normal training:
  Store all activations in memory during forward pass for backward pass
  Memory: O(N_layers × batch_size × seq_len × d_model)
  
Gradient checkpointing:
  Only store activations at checkpoint boundaries
  Recompute intermediate activations during backward pass
  Memory: O(√N_layers) — significant savings
  Cost: ~30% slower training (recomputation)
```

#### Common Pitfalls in Fine-Tuning
1. **Catastrophic forgetting:** Too high LR or too many steps → model forgets pre-training.
   Fix: Lower LR, fewer epochs, add replay data from pre-training.
2. **Overfitting:** Loss on train set drops; val set loss increases.
   Fix: More data, LoRA (lower capacity), dropout, early stopping.
3. **Reward hacking (RLHF):** Model learns to exploit reward model weaknesses.
   Fix: KL penalty, diverse reward model ensemble.
4. **Data contamination:** Test examples leaked into training.
   Fix: Rigorous deduplication across splits before training.
5. **Wrong loss masking:** Computing loss on prompt tokens, not just completions.
   Fix: Ensure `attention_mask` / `labels = -100` on prompt positions.

---

## Summary Cheat Sheet

| Topic | Key Points |
|---|---|
| System design | Ingestion → Embedding → Storage → Retrieval → LLM → Serve. Bottlenecks: GPU for embedding, LLM TTFT, ANN recall |
| Cost | 90% of cost is LLM tokens. Fix: routing, caching, quantization |
| Latency | Stream output. Small model + reranker > large model alone |
| Self-host | Required for privacy, compliance, >10M tokens/day, fine-tuned models |
| Fine-tuning | SFT → DPO. Use TRL/Axolotl. Collect implicit signals |
| Dataset | Filter → format → temporal split. Loss on assistant tokens only |
| Database | Postgres + pgvector + Redis + Elasticsearch covers 80% of needs |
| Metrics | TTFT, TPS, faithfulness, thumbs-up rate, cost/query |
| Monitoring | 4 golden signals + LLM-specific (refusal rate, hallucination rate) |
| Feedback loop | Implicit signals → DPO pairs → periodic retraining |
| Determinism | temp=0, seed, structured output, version-pin models |
| Embedding migration | Blue-green index, dual-write, canary cutover |
| Fallbacks | Circuit breaker, model cascade, BM25 fallback, cached response |
| Without LLMs | BM25 + rules + templates — often better for narrow, precision-critical domains |
| Tokenization | BPE/WordPiece subword. 1 token ≈ 0.75 English words |
| Embeddings | Dense vectors from contrastive learning. Cosine similarity for retrieval |
| Fine-tuning internals | AdamW + warmup/cosine LR. LoRA adds low-rank ΔW=BA. bf16 + gradient checkpointing |
