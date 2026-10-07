# ML System Design — Explained With Real Examples
> **Running Example throughout this document:**  
> 🏦 **"BankBot"** — An internal AI assistant for a bank's 5,000 customer service agents.  
> Agents type questions like *"What is the penalty for early FD withdrawal?"* and BankBot retrieves answers from 50,000 internal policy documents and product manuals.

---

## Table of Contents
1. [End-to-End System (Ingestion → Serving)](#1-end-to-end-system)
2. [Cost Estimation & Reduction](#2-cost-estimation--reduction)
3. [Latency Reduction & Quality Trade-offs](#3-latency-reduction--quality-trade-offs)
4. [Self-Hosted vs. API LLMs](#4-self-hosted-vs-api-llms)
5. [Fine-Tuning on User Behavior](#5-fine-tuning-on-user-behavior)
6. [Dataset Construction, Loss Functions & MLOps](#6-dataset-construction-loss-functions--mlops)
7. [Database Selection](#7-database-selection)
8. [Metrics & Tracking](#8-metrics--tracking)
9. [System Monitoring & Debugging](#9-system-monitoring--debugging)
10. [Feedback Loop & Evaluation](#10-feedback-loop--evaluation)
11. [Making the System Deterministic](#11-making-the-system-deterministic)
12. [Replacing Embedding Models Without Downtime](#12-replacing-embedding-models-without-downtime)
13. [Fallback Mechanisms](#13-fallback-mechanisms)
14. [Solving Without LLMs or Vector DBs](#14-solving-without-llms-or-vector-dbs)
15. [Tokenization & Embeddings From Scratch](#15-tokenization--embeddings-from-scratch)
16. [What Happens During Fine-Tuning?](#16-what-happens-during-fine-tuning)

---

## 1. End-to-End System

### 🏦 Real Scenario
The bank has 50,000 PDF/Word policy documents — loan terms, FD rates, KYC rules, compliance manuals. Each document is updated quarterly. Agents ask ~10,000 questions/day.

### What happens step by step

#### STEP 1 — Ingestion (getting documents in)

```
Every Monday at 2 AM (batch job):
  SharePoint / internal CMS
        ↓
  Python script pulls new/updated files
        ↓
  Uploads raw files to S3:
    s3://bankbot-raw/policy-docs/2024-Q3/loan_policy_v7.pdf
        ↓
  Kafka message published:
    { "event": "doc_uploaded", "s3_key": "policy-docs/2024-Q3/loan_policy_v7.pdf" }
```

**Why Kafka?** If S3 upload triggers the embedding job directly and the embedding GPU crashes, you lose the event. Kafka retains the message — the consumer retries automatically.

**Real code — publishing to Kafka:**
```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=["kafka-broker:9092"],
    value_serializer=lambda v: json.dumps(v).encode()
)

def on_document_uploaded(s3_key: str, doc_id: str):
    producer.send("doc-ingestion-events", {
        "event": "new_document",
        "doc_id": doc_id,
        "s3_key": s3_key,
        "timestamp": "2024-09-01T02:00:00Z"
    })
```

---

#### STEP 2 — Pre-processing (cleaning + chunking)

The PDF `loan_policy_v7.pdf` has 120 pages.  
**Problem:** An LLM context window holds ~4,000 tokens ≈ ~3,000 words. You can't send all 120 pages.  
**Solution:** Split into overlapping chunks.

```
loan_policy_v7.pdf (120 pages)
        ↓
[Text Extraction — pdfminer / Unstructured]
        ↓
[Cleaning]
  Remove headers: "Page 1 of 120", "CONFIDENTIAL - INTERNAL ONLY"
  Remove footers, fix encoding issues ("â€™" → "'")
  Remove duplicate lines (copy-paste artifacts in PDFs)
        ↓
[Chunking — sliding window, 512 tokens, 50 token overlap]
  Chunk 1:  "Section 3.1: Early Withdrawal Penalty. Fixed Deposits closed before..."
  Chunk 2:  "...before maturity incur a 1% penalty on principal. Exception: medical..."
  Chunk 3:  "...medical emergency documented with hospital certificate. The penalty..."
  ...
  → 847 chunks from this one document
```

**Why overlap?** Without it, a sentence at the boundary of chunk 1 and chunk 2 would be split mid-thought, and a query about it might retrieve an incomplete chunk.

**Real code — chunking:**
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,          # tokens per chunk
    chunk_overlap=50,        # overlap between consecutive chunks
    separators=["\n\n", "\n", ". ", " "],  # prefer splitting on paragraph > sentence > word
)

with open("loan_policy_v7.txt") as f:
    text = f.read()

chunks = splitter.split_text(text)
print(f"Created {len(chunks)} chunks")
# Created 847 chunks
```

---

#### STEP 3 — Embedding generation

Each chunk is converted into a **vector** (list of numbers) that captures its meaning.

```
Chunk: "Early Withdrawal Penalty. FDs closed before maturity incur a 1% penalty."
        ↓
[Embedding Model: text-embedding-3-small (OpenAI) or all-MiniLM-L6-v2 (local)]
        ↓
Vector: [0.23, -0.87, 0.41, 0.09, -0.33, ..., 0.71]  ← 1536 numbers
```

**Why 1536 numbers?** Each number captures a different "dimension of meaning." Dimension 42 might loosely correspond to "legal/regulatory tone." Dimension 187 might loosely capture "financial product." The model learns these during training.

**Real code — batch embedding:**
```python
import openai
import numpy as np

client = openai.OpenAI()

def embed_chunks(chunks: list[str]) -> list[list[float]]:
    # Send 100 chunks at a time (API limit)
    embeddings = []
    for i in range(0, len(chunks), 100):
        batch = chunks[i:i+100]
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch
        )
        embeddings.extend([r.embedding for r in response.data])
    return embeddings

# For 847 chunks: 9 API calls, ~$0.0001 each = $0.001 total
embeddings = embed_chunks(chunks)
```

---

#### STEP 4 — Storing in Vector DB

```
Each chunk stored as a record:
{
  "id": "loan_policy_v7_chunk_42",
  "vector": [0.23, -0.87, 0.41, ...],   ← for similarity search
  "metadata": {
    "doc_id": "loan_policy_v7",
    "page": 12,
    "section": "3.1",
    "text": "Early Withdrawal Penalty. FDs closed before maturity incur a 1% penalty.",
    "last_updated": "2024-09-01"
  }
}
```

**Real code — inserting into pgvector (PostgreSQL extension):**
```python
import psycopg2

conn = psycopg2.connect("postgresql://bankbot:pass@db:5432/bankbot")
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id TEXT PRIMARY KEY,
        doc_id TEXT,
        chunk_text TEXT,
        page_number INT,
        embedding vector(1536)
    )
""")

for chunk_id, text, embedding in zip(chunk_ids, chunks, embeddings):
    cur.execute("""
        INSERT INTO chunks (id, doc_id, chunk_text, page_number, embedding)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding
    """, (chunk_id, "loan_policy_v7", text, page_num, str(embedding)))

conn.commit()
```

---

#### STEP 5 — Query time (Agent asks a question)

```
Agent types: "What is the penalty for early FD withdrawal?"
        ↓
[Embed the query with the same model]
Query vector: [0.19, -0.81, 0.39, 0.12, -0.28, ..., 0.68]
        ↓
[ANN Search — find top-5 most similar chunks]
  Result 1: "FDs closed before maturity incur a 1% penalty..." (score: 0.94)
  Result 2: "Exception: medical emergency..." (score: 0.89)
  Result 3: "Table 3: FD Penalty Schedule..." (score: 0.82)
  Result 4: "Recurring Deposits follow same penalty rules..." (score: 0.71)
  Result 5: "Savings account early closure..." (score: 0.63)
        ↓
[Re-rank: use a cross-encoder to re-score top-5]
  Re-ranked Result 1: score 0.97 → "FDs closed before maturity..."
  Re-ranked Result 2: score 0.91 → "Table 3: FD Penalty Schedule..."
  (Savings account result drops to 5th — less relevant)
        ↓
[Prompt construction]
  System: "You are BankBot. Answer using ONLY the context below."
  Context: [Top 3 re-ranked chunks concatenated]
  User: "What is the penalty for early FD withdrawal?"
        ↓
[LLM: GPT-4o]
        ↓
Response: "Based on Section 3.1 of the Loan Policy, Fixed Deposits closed before 
           maturity incur a 1% penalty on the principal amount. This penalty is 
           waived in case of documented medical emergencies."
```

**Real code — ANN search in pgvector:**
```sql
-- Find top 5 most similar chunks using cosine similarity
SELECT id, chunk_text, 1 - (embedding <=> '[0.19, -0.81, ...]') AS similarity
FROM chunks
ORDER BY embedding <=> '[0.19, -0.81, ...]'
LIMIT 5;
```

---

#### The Bottlenecks (with real numbers)

| Stage | Time in BankBot | Why it's slow |
|---|---|---|
| PDF parsing | 2–5s per doc | Complex PDFs with tables, images |
| Embedding 847 chunks | 8 seconds | 9 API calls, rate limited |
| ANN search | 15ms | 50,000 × 1536 dimensions |
| Re-ranking | 45ms | Cross-encoder runs inference |
| GPT-4o generation | 600ms–2s | Token-by-token generation |
| **Total (batch)** | **~10s/doc** | — |
| **Total (query time)** | **~800ms** | — |

---

## 2. Cost Estimation & Reduction

### 🏦 Real Numbers for BankBot

```
Documents: 50,000 PDFs, avg 5 pages each
Avg chunks per doc: 30 chunks
Total chunks: 50,000 × 30 = 1,500,000 chunks

INGESTION COST (one-time):
  Embedding cost = 1.5M chunks × 512 tokens × $0.02/1M tokens
                 = 1.5M × 512 / 1M × $0.02
                 = $15.36   ← very cheap, one-time

SERVING COST (daily):
  10,000 queries/day
  Each query:
    - Input tokens: system prompt (200) + 3 chunks (600) + query (30) = 830 tokens
    - Output tokens: ~150 tokens
  
  Cost per query = (830 × $5/1M) + (150 × $15/1M)   [GPT-4o pricing]
                 = $0.00415 + $0.00225
                 = $0.0064 per query
  
  Daily cost = 10,000 × $0.0064 = $64/day = $1,920/month
```

**That's $23,040/year just for LLM inference.** Here's how you cut it:

---

### Strategy 1: Model Routing (saves 60–70%)

Not every query needs GPT-4o. Most queries are simple lookups.

```
Query: "What is the IFSC code for Mumbai branch?"
  → Simple factual lookup → Route to GPT-3.5-turbo ($0.0005 per query)

Query: "Explain the tax implications of breaking an FD and reinvesting in MF"
  → Complex multi-step reasoning → Route to GPT-4o ($0.0064 per query)
```

**How to build a router:**
```python
from transformers import pipeline

# Fine-tuned BERT classifier: "simple" vs "complex" query
router = pipeline("text-classification", model="bankbot/query-complexity-classifier")

def route_query(query: str) -> str:
    result = router(query)[0]
    if result["label"] == "SIMPLE" and result["score"] > 0.85:
        return "gpt-3.5-turbo"   # 10× cheaper
    return "gpt-4o"

# After routing:
# 70% queries → gpt-3.5-turbo
# 30% queries → gpt-4o

# New daily cost:
# 7,000 × $0.0005 + 3,000 × $0.0064 = $3.5 + $19.2 = $22.7/day
# Was $64/day → 65% savings
```

---

### Strategy 2: Semantic Caching (saves additional 20%)

Many agents ask the **same question** throughout the day.

```
9:02 AM — Agent A: "What documents are needed for KYC?"
9:15 AM — Agent B: "What are the KYC document requirements?"
9:47 AM — Agent C: "List of documents for KYC verification?"
```

These are semantically identical. Cache the first answer and return it for similar queries.

```python
import redis
import numpy as np

cache = redis.Redis(host="redis", port=6379)

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_cached_response(query_embedding: list, threshold: float = 0.95):
    # Check all cached query embeddings (stored as Redis hashes)
    for key in cache.scan_iter("cache:*"):
        cached_embedding = np.frombuffer(cache.hget(key, "embedding"))
        similarity = cosine_similarity(query_embedding, cached_embedding)
        if similarity > threshold:
            return cache.hget(key, "response").decode()
    return None

def answer_query(query: str):
    query_embedding = embed(query)
    
    # Check cache first
    cached = get_cached_response(query_embedding)
    if cached:
        return cached  # FREE! No LLM call needed
    
    # Not cached — call LLM
    response = call_llm(query, retrieve_context(query_embedding))
    
    # Store in cache with 24-hour TTL
    cache.hset(f"cache:{hash(query)}", mapping={
        "embedding": np.array(query_embedding).tobytes(),
        "response": response
    })
    cache.expire(f"cache:{hash(query)}", 86400)
    
    return response
```

**After all optimizations:**
```
Original:   $64/day ($1,920/month)
After routing: $22.7/day
After caching (25% hit rate): $17/day ($510/month)
→ 73% cost reduction
```

---

## 3. Latency Reduction & Quality Trade-offs

### 🏦 Real BankBot Latency Problem

At 9 AM (shift start), 500 agents log in simultaneously. P99 latency hits **8 seconds**. Agents complain.

**Latency breakdown before optimization:**
```
Auth check:              10ms
Query embedding:        120ms  ← API call
ANN search (exact):     800ms  ← scanning all 1.5M vectors!
Re-ranking:             200ms
Prompt construction:     10ms
GPT-4o (first token):   900ms
GPT-4o (full response): 1200ms
Post-processing:         20ms
─────────────────────────────
Total:                  3260ms  (P50)
P99 (peak load):        8000ms
```

### Fix 1: Switch from Exact Search to ANN

```python
# BEFORE: Exact search (pgvector default on small tables)
# SELECT ... ORDER BY embedding <=> query_vec LIMIT 5
# Time: 800ms for 1.5M vectors

# AFTER: HNSW index (Approximate Nearest Neighbor)
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

# Now the same query takes 15ms
# Trade-off: ~1% recall loss (very occasionally misses a relevant chunk)
# Worth it: 53× faster
```

**How HNSW works (intuition):**  
Instead of checking all 1.5M vectors, it builds a graph where similar vectors are connected. Finding nearest neighbors = walking the graph from a random start point, always moving to "more similar" neighbors. Like finding a restaurant by asking "is there anything closer?" instead of checking every restaurant on the map.

### Fix 2: Streaming (most impactful UX improvement)

```python
# BEFORE: Wait 1200ms for full response, then display
response = client.chat.completions.create(model="gpt-4o", messages=msgs)
return response.choices[0].message.content  # User waits 1.2s

# AFTER: Stream token by token (perceived latency = time to first token)
stream = client.chat.completions.create(model="gpt-4o", messages=msgs, stream=True)
for chunk in stream:
    if chunk.choices[0].delta.content:
        yield chunk.choices[0].delta.content  # User sees text appearing immediately
```

**Result:** Time-to-first-token = 900ms. Agent sees words appearing after 900ms and reads as it streams. **Perceived latency drops from 3.2s to ~900ms** even though total time is the same.

### Fix 3: Parallel retrieval

```python
import asyncio

async def answer_with_parallel_retrieval(query: str):
    # Run embedding + BM25 keyword search in parallel
    query_embedding, bm25_results = await asyncio.gather(
        async_embed(query),          # 120ms
        bm25_search(query),          # 20ms (runs simultaneously)
    )
    
    # ANN search needs embedding result, so it runs after
    ann_results = await ann_search(query_embedding)  # 15ms
    
    # Combine results (Reciprocal Rank Fusion)
    combined = rrf_combine(ann_results, bm25_results)
    
    # Total: max(120, 20) + 15 = 135ms  vs.  120 + 20 + 15 = 155ms
    # Small saving, but pattern matters at scale
```

### Latency vs. Quality Trade-off Table (Real Numbers for BankBot)

| Config | P50 Latency | Cost/query | Answer Quality (human eval) |
|---|---|---|---|
| GPT-4o + exact search + reranker | 3.2s | $0.0064 | 94% |
| GPT-4o + HNSW + reranker | 1.1s | $0.0064 | 93.2% |
| GPT-3.5 + HNSW + reranker | 0.4s | $0.0005 | 87% |
| GPT-3.5 + HNSW + no reranker | 0.3s | $0.0004 | 82% |
| BM25 only (no LLM) | 0.02s | ~$0 | 71% |

**Sweet spot for BankBot:** GPT-4o for complex queries + GPT-3.5 for simple + HNSW + reranker  
→ **P50: 0.7s, cost: $0.002/query, quality: 91%**

---

## 4. Self-Hosted vs. API LLMs

### 🏦 Real Decision for BankBot

The bank's **CISO** raises a concern:  
*"We're sending customer account questions and internal policy details to OpenAI. That's a GDPR and RBI data localization violation."*

**Decision: Self-host.**

### The Real Cost Calculation

```
Current: OpenAI API
  Daily tokens: 10,000 queries × 980 tokens = 9.8M tokens/day
  Cost: 9.8M × $0.005/1K = $49/day = $17,850/year

Self-hosted: 2× NVIDIA A10G GPU (24GB VRAM each)
  Model: Llama-3-8B-Instruct (fits in 16GB with INT8)
  Throughput: ~300 tokens/second per GPU
  Peak demand: 10,000 queries × 980 tokens / 8 hours = ~340 tokens/s
  → Need 2 GPUs to cover peak

  AWS g5.xlarge (A10G): $1.006/hour on-demand
  2 GPUs × $1.006 × 24 hours = $48.3/day
  
  API cost: $49/day
  Self-host: $48.3/day  ← Almost break-even at this scale!
  
  But with 3-year reserved instances:
  2 GPUs × $0.40/hour × 24 = $19.2/day = $7,008/year
  Savings: $10,842/year AND full data control
```

### Self-Hosting Stack (Real)

```
Model:   Llama-3-8B-Instruct
         → Quantized to INT8 with bitsandbytes (8GB VRAM, from 16GB)
         → Fits 2× on single A10G (24GB)

Server:  vLLM
         → Continuous batching (no idle GPU time between requests)
         → OpenAI-compatible API (no code changes needed!)

Deploy:  Kubernetes + GPU Operator
         → Auto-scale from 1 to 4 replicas based on queue depth

Load balancer: NGINX → routes to available vLLM pods
```

**Start serving in 10 minutes:**
```bash
# Install vLLM and serve Llama 3 8B
pip install vllm

python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Meta-Llama-3-8B-Instruct \
  --quantization bitsandbytes \
  --load-format bitsandbytes \
  --gpu-memory-utilization 0.9 \
  --host 0.0.0.0 \
  --port 8000

# Your existing OpenAI SDK code works unchanged:
client = openai.OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")
response = client.chat.completions.create(model="meta-llama/Meta-Llama-3-8B-Instruct", ...)
```

---

## 5. Fine-Tuning on User Behavior

### 🏦 Real Problem

Base Llama-3 sometimes gives answers like:  
*"The specific penalty rate may vary. Please refer to the bank's official terms and conditions."*  

That's useless. The agent HAS the policy doc. We want it to say:  
*"Per Section 3.1, the penalty is 1% of principal."*

Also, agents use **banking jargon**: "MCLR", "TDS deduction", "Section 194A", "KYC re-verification". The base model stumbles on these.

**Solution: Fine-tune on historical Q&A pairs.**

### Step 1: Collect Training Data from Behavior

```python
# Every resolved conversation is logged:
conversation_log = {
    "session_id": "sess_20240901_1234",
    "query": "What TDS is deducted on FD interest above 40,000?",
    "retrieved_chunks": ["chunk_42", "chunk_89"],
    "llm_response": "TDS is deducted at 10% under Section 194A if interest exceeds ₹40,000 in a financial year.",
    "agent_feedback": "thumbs_up",        # ← Explicit signal
    "agent_edited": False,                # ← Did agent copy-paste with edits? If yes → negative signal
    "time_on_page_seconds": 8,           # ← High dwell = good
    "follow_up_query": None,             # ← No follow-up = query resolved
}
```

**Signal quality ranking:**
```
STRONG POSITIVE:  Agent copies response without editing + closes ticket
MEDIUM POSITIVE:  Thumbs up
WEAK POSITIVE:    High dwell time (>5 sec), no follow-up
WEAK NEGATIVE:    Follow-up "can you clarify?" within 30 seconds
MEDIUM NEGATIVE:  Agent edits response before sending to customer
STRONG NEGATIVE:  Thumbs down, "regenerate", low dwell (<2 sec)
```

### Step 2: Build DPO Training Pairs

```python
# From strong positive + strong negative pairs:

dpo_sample = {
    "prompt": "What TDS is deducted on FD interest above 40,000?",
    
    "chosen": 
        "TDS is deducted at 10% under Section 194A if annual FD interest exceeds "
        "₹40,000 (₹50,000 for senior citizens). You can submit Form 15G/15H to "
        "avoid TDS deduction if total income is below taxable limit.",
    
    "rejected": 
        "The TDS deduction on Fixed Deposit interest depends on various factors. "
        "Please refer to the latest RBI circular or consult a tax advisor for "
        "accurate information."
}
# The model learns: be specific and cite the section. Don't be vague.
```

### Step 3: Fine-Tuning with TRL + LoRA

```python
from trl import DPOTrainer, DPOConfig
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load base model
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Meta-Llama-3-8B-Instruct",
    torch_dtype=torch.bfloat16,  # bf16: same range as fp32, 2× memory efficient
    device_map="auto"
)

# Add LoRA adapters
lora_config = LoraConfig(
    r=16,                    # Rank: how many "dimensions of adaptation"
    lora_alpha=32,           # Scale factor (usually 2×r)
    # Only adapt the attention layers (query, key, value, output projections)
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none"
)
model = get_peft_model(model, lora_config)
# Result: 8B params → only 13M params are trainable (LoRA weights)
# Memory: from 16GB to 4GB for optimizer states!

# DPO training
trainer = DPOTrainer(
    model=model,
    ref_model=None,       # TRL creates a frozen copy automatically
    args=DPOConfig(
        beta=0.1,         # KL penalty strength (higher = stay closer to base model)
        learning_rate=5e-5,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        warmup_ratio=0.1,
        bf16=True,
        logging_steps=10,
        output_dir="./bankbot-dpo-checkpoint"
    ),
    train_dataset=dpo_dataset,
)

trainer.train()

# After training: merge LoRA weights into base model for serving
merged_model = model.merge_and_unload()
merged_model.save_pretrained("./bankbot-finetuned-v1")
```

---

## 6. Dataset Construction, Loss Functions & MLOps

### 🏦 Real Dataset Pipeline for BankBot

#### Dataset Sources
```
Source 1: Expert-written Q&A
  - HR asked 10 senior agents to write 500 ideal Q&A pairs
  - Format: query → ideal answer (citing section)
  - Quality: High. Quantity: Low.

Source 2: Historical resolved tickets
  - 6 months of tickets where CSAT ≥ 4/5
  - Format: ticket_text → agent_response
  - Quality: Medium (agents aren't perfect). Quantity: High (50,000 pairs).

Source 3: Synthetic data (GPT-4 as teacher)
  - Give GPT-4o each policy document chunk
  - Ask it: "Generate 5 Q&A pairs from this chunk"
  - Quality: High. Quantity: Scalable.
  - Cost: 1.5M chunks × 5 Q&As × $0.005/1K tokens ≈ $37,500 (do this once)
```

#### Data Quality Pipeline
```python
import hashlib
from datasketch import MinHash, MinHashLSH

def build_clean_dataset(raw_samples):
    clean = []
    
    # Step 1: Length filter
    samples = [s for s in raw_samples 
               if 20 < len(s["query"].split()) < 100
               and 30 < len(s["answer"].split()) < 500]
    
    # Step 2: Deduplicate with MinHash (catches near-duplicates)
    lsh = MinHashLSH(threshold=0.8, num_perm=128)
    unique = []
    for i, sample in enumerate(samples):
        mh = MinHash(num_perm=128)
        for word in sample["query"].lower().split():
            mh.update(word.encode())
        
        if not lsh.query(mh):  # No near-duplicate found
            lsh.insert(f"id_{i}", mh)
            unique.append(sample)
    
    # Step 3: PII scrubbing
    import re
    for sample in unique:
        # Remove account numbers, Aadhaar, phone numbers
        sample["query"] = re.sub(r'\b\d{12}\b', '[AADHAAR]', sample["query"])
        sample["query"] = re.sub(r'\b\d{10}\b', '[PHONE]', sample["query"])
        sample["answer"] = re.sub(r'ACC\d{9}', '[ACCOUNT]', sample["answer"])
    
    return unique

# Result: 50,000 raw → 34,000 after dedup and quality filters
```

#### Loss Function — What Actually Happens

**SFT (Supervised Fine-Tuning) Loss — plain English:**

The model is told: *"Given this query and context, the correct answer is: 'TDS is deducted at 10%...'"*

It learns to predict each word of the answer, given all previous words.

```
Answer tokens: ["TDS", "is", "deducted", "at", "10%", "under", "Section", "194A"]

At each step, the model predicts:
  After ["TDS"] → predict "is"        → probability 0.91 (good, learn little)
  After ["TDS", "is"] → predict "deducted" → probability 0.73 (ok)
  After [...] → predict "10%" → probability 0.12 (bad! punished heavily)
  After [...] → predict "194A" → probability 0.08 (very bad! large gradient update)

Loss = -log(0.91) - log(0.73) - log(0.12) - log(0.08) - ...
     = 0.09 + 0.31 + 2.12 + 2.53 + ...

The model is updated to increase the probability of the correct tokens.
After 3 epochs: probability of "10%" jumps from 0.12 to 0.78.
```

**CRITICAL: Only compute loss on the answer, NOT the prompt.**

```python
# WRONG: Computing loss on the whole conversation
labels = tokenizer.encode(full_conversation)  # loss computed on "User: What is..."

# RIGHT: Mask the prompt (set to -100 = ignored by loss function)
labels = [-100] * len(prompt_tokens) + tokenizer.encode(answer)
#          ↑ prompt tokens ignored      ↑ only these tokens contribute to loss
```

Why? You don't want the model to "learn" to produce the query — you want it to learn to produce the answer.

---

#### MLOps Pipeline (Real)

```
Day 1: New policy document uploaded to SharePoint
  ↓
Automated trigger: GitHub Actions workflow "policy-update"
  ↓
Step 1: Re-embed changed chunks only (diff-based)
  ↓
Step 2: Update vector DB (upsert, not full rebuild)
  ↓
Step 3: Run retrieval regression tests
  "Does query X still retrieve chunk Y?" (golden test set)
  If fail → alert Slack channel #bankbot-alerts → human review
  ↓
Every 2 weeks: Collect new DPO training pairs (from feedback)
  ↓
If > 500 new pairs accumulated:
  Trigger fine-tuning job (Kubernetes GPU job)
  Track in W&B: loss curves, eval ROUGE score
  ↓
Automated eval: run against 200-query golden test set
  If new model beats current by >2%:
    → Deploy to staging (shadow traffic)
    → 24h canary (5% real traffic)
    → Full rollout
  Else:
    → Alert team, log experiment, keep current model
```

---

## 7. Database Selection

### 🏦 Why BankBot Uses 4 Different Databases

```
┌─────────────────────────────────────────────────────────┐
│                    BankBot System                       │
│                                                         │
│  PostgreSQL + pgvector                                  │
│    - chunks table (text + vectors)                      │
│    - documents table (metadata, version history)        │
│    - users table (agent profiles)                       │
│    - query_logs table (for feedback collection)         │
│                                                         │
│  Redis                                                  │
│    - Semantic cache (query embedding → cached response) │
│    - Rate limiting counters per agent                   │
│    - Session state (which docs agent is viewing)        │
│                                                         │
│  Elasticsearch                                          │
│    - BM25 keyword search (fallback + hybrid)            │
│    - Audit log search ("show all queries about FD")     │
│    - Full-text search for document management           │
│                                                         │
│  S3 (Object Store)                                      │
│    - Raw PDF/Word documents (source of truth)           │
│    - Model checkpoints                                  │
│    - Training datasets (versioned with DVC)             │
└─────────────────────────────────────────────────────────┘
```

### Why Not Just One Database?

**"Why not store everything in MongoDB?"**
```
MongoDB:
  ✓ Great for flexible JSON documents
  ✗ No native vector search at scale
  ✗ ANN search is bolted on, not optimized
  ✗ No sub-ms caching (no Redis TTL semantics)

PostgreSQL + pgvector:
  ✓ Full ACID for document metadata
  ✓ JOIN queries: "Find all chunks from documents updated this week"
  ✓ Native vector search via pgvector extension
  ✓ You already know SQL
  ✗ Slower than Pinecone at 100M+ vectors (pgvector sweet spot: <20M)
```

**When to upgrade from pgvector to Pinecone/Qdrant:**
```
pgvector is fine for:   < 5M vectors, < 100 QPS
Switch to Pinecone for: > 20M vectors OR > 500 QPS OR need multi-tenancy
```

### Real Query Example (Hybrid Search)

```python
def hybrid_search(query: str, query_embedding: list, top_k: int = 10):
    """Combine BM25 (Elasticsearch) + Dense (pgvector) using RRF"""
    
    # BM25 search (keyword)
    bm25_results = es.search(index="bankbot-chunks", body={
        "query": {"match": {"text": query}},
        "size": top_k
    })["hits"]["hits"]
    # Returns: [{"_id": "chunk_42", "_score": 12.3}, ...]
    
    # Dense search (semantic)
    dense_results = db.execute("""
        SELECT id, chunk_text, 
               1 - (embedding <=> %s) as score
        FROM chunks
        ORDER BY embedding <=> %s
        LIMIT %s
    """, (str(query_embedding), str(query_embedding), top_k))
    # Returns: [("chunk_89", "FDs closed before maturity...", 0.94), ...]
    
    # Reciprocal Rank Fusion: no hyperparameters needed
    k = 60  # RRF constant
    rrf_scores = {}
    
    for rank, result in enumerate(bm25_results):
        doc_id = result["_id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1/(k + rank + 1)
    
    for rank, result in enumerate(dense_results):
        doc_id = result[0]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1/(k + rank + 1)
    
    # Sort by combined score
    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
```

**Why hybrid beats either alone:**
- Pure BM25: Misses "What's the fee for closing an account early?" (doesn't contain "FD" or "penalty")
- Pure dense: Misses "Section 194A TDS" (BM25 handles exact legal citations better)
- Hybrid RRF: Gets both

---

## 8. Metrics & Tracking

### 🏦 BankBot Dashboard (Real Metrics)

```
BUSINESS METRICS (weekly review by product team)
┌────────────────────────────────┐
│ Task Resolution Rate: 87.3%   │  ← Did query get resolved without escalation?
│ Agent Satisfaction: 4.2/5.0   │  ← Post-session survey
│ Escalations reduced: 34%      │  ← vs. pre-BankBot baseline
│ Avg handle time: -2.3 min     │  ← Time saved per interaction
└────────────────────────────────┘

QUALITY METRICS (daily automated)
┌────────────────────────────────┐
│ Faithfulness: 0.91            │  ← Is answer grounded in retrieved docs?
│ Answer Relevancy: 0.88        │  ← Does answer address the question?
│ Context Recall: 0.84          │  ← Did we retrieve the right chunks?
│ Thumbs Up Rate: 78%           │  ← Direct agent feedback
│ Regeneration Rate: 8%         │  ← Agent clicked "regenerate"
└────────────────────────────────┘

SYSTEM METRICS (real-time Grafana)
┌────────────────────────────────┐
│ P50 latency: 0.8s             │
│ P99 latency: 2.1s             │
│ TTFT (first token): 420ms     │
│ Error rate: 0.3%              │
│ GPU utilization: 67%          │
│ Cache hit rate: 31%           │
│ QPS: 12.4                     │
└────────────────────────────────┘
```

### Measuring Faithfulness (Real Implementation)

```python
# Faithfulness: Did the model make up anything not in the retrieved chunks?
# Use GPT-4o as a judge (LLM-as-judge pattern)

def measure_faithfulness(query, context_chunks, response):
    judge_prompt = f"""
    You are evaluating an AI assistant's response for faithfulness.
    
    Context (retrieved documents):
    {chr(10).join(context_chunks)}
    
    User question: {query}
    
    AI Response: {response}
    
    Task: Is every claim in the AI Response supported by the Context above?
    Answer with JSON: {{"score": 0-1, "issues": ["list any unsupported claims"]}}
    """
    
    result = gpt4o.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": judge_prompt}],
        response_format={"type": "json_object"},
        temperature=0
    )
    return json.loads(result.choices[0].message.content)

# Run on 5% sample of all queries (cost-effective)
# Example output:
{
    "score": 0.3,
    "issues": [
        "Response claims penalty is 0.5% but context says 1%",
        "Response mentions Form 15H but context only mentions Form 15G"
    ]
}
# → Alert! Model hallucinating on this query type
```

---

## 9. System Monitoring & Debugging

### 🏦 Real Incident: BankBot P99 Spikes to 12 Seconds

**Monday 9:15 AM:** Grafana alert fires. P99 latency = 12.3s. Agent complaints in Slack.

**Debugging Playbook:**

```
Step 1: Check the Grafana overview dashboard
  Latency breakdown:
    Auth:            12ms  ✓ normal
    Embedding:       580ms ← WAS 120ms. Something wrong here.
    ANN search:      18ms  ✓ normal
    LLM generation:  1400ms ✓ normal (slightly slow but OK)
  
  → Bottleneck is in embedding step

Step 2: Check embedding service logs (Loki)
  grep "embedding" logs | grep "ERROR"
  Output:
  [09:01] ERROR: OpenAI API rate limit hit. Retry in 20s.
  [09:01] ERROR: OpenAI API rate limit hit. Retry in 20s.
  [09:03] ERROR: OpenAI API rate limit hit. Retry in 20s.
  ... (hundreds of lines)
  
  → OpenAI rate limit! Too many concurrent agents at shift start.

Step 3: Check concurrency metrics
  Peak concurrent embedding requests at 9:00 AM: 347
  OpenAI TPM (tokens per minute) limit: 1,000,000
  347 agents × 512 token queries × 60 = 10.6M TPM → 10× over limit!

Step 4: Root cause identified
  Monday shift start: all 500 agents log in simultaneously
  All pre-warm the app by asking a test query
  → 347 simultaneous embedding requests

Step 5: Fix
  Option A (immediate): Add request queuing with max 50 concurrent embeddings
  Option B (better): Switch to local embedding model for query embedding
    - Query embedding: use all-MiniLM-L6-v2 locally (120ms → 8ms, no rate limit)
    - Keep OpenAI only for document ingestion (offline, rate limit OK)

Step 6: Deploy fix, verify
  P99 latency drops to 1.8s within 10 minutes of deploying local embedder
```

**Implementing the circuit breaker to prevent future cascades:**
```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"     # Normal operation
    OPEN = "open"         # Failing, reject fast
    HALF_OPEN = "half_open"  # Testing recovery

class EmbeddingCircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=30):
        self.failures = 0
        self.threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
    
    def call(self, embedding_fn, text):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = CircuitState.HALF_OPEN  # Try again
            else:
                # Fast fail: use local model immediately
                return local_embedding_model.encode(text)
        
        try:
            result = embedding_fn(text)  # OpenAI API
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED  # Recovered!
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.threshold:
                self.state = CircuitState.OPEN
                print(f"Circuit OPENED after {self.failures} failures")
            return local_embedding_model.encode(text)  # Fallback
```

---

## 10. Feedback Loop & Evaluation

### 🏦 BankBot's Continuous Improvement Cycle

**Real flywheel:**
```
Week 1: Deploy BankBot v1. Agents ask questions.
Week 2: Collect feedback (thumbs up/down, edits, dwell time)
Week 3: Find patterns in negative feedback:
  "Answers about NRI accounts are often wrong" (low thumbs up cluster)
  "Model says 'consult an advisor' for TDS questions instead of answering"
Week 4: Curate 300 new training pairs for NRI accounts + TDS
Week 5: Fine-tune v2. Evaluate on golden set. Deploy.
Week 6: NRI accuracy goes from 62% to 84%. Thumbs up rate: 78% → 83%.
Week 8: New data collected... cycle repeats.
```

### A/B Testing Framework

```python
import hashlib
import random

def get_model_for_user(agent_id: str, experiment_id: str) -> str:
    """
    Deterministic assignment: same agent always gets same model.
    Prevents confounding from agents switching models mid-shift.
    """
    hash_val = int(hashlib.md5(f"{agent_id}{experiment_id}".encode()).hexdigest(), 16)
    bucket = hash_val % 100  # 0–99
    
    if bucket < 10:
        return "bankbot-v2-candidate"  # 10% canary
    return "bankbot-v1-production"     # 90% control

# After 48 hours of canary:
experiment_results = {
    "v1_thumbs_up_rate": 0.78,
    "v2_thumbs_up_rate": 0.83,
    "p_value": 0.02,          # Statistically significant (p < 0.05)
    "lift": "+6.4%",
    "v1_latency_p50": "0.81s",
    "v2_latency_p50": "0.79s",
    "decision": "SHIP v2 to 100%"
}
```

---

## 11. Making the System Deterministic

### 🏦 Real Problem

An auditor asks: *"On September 1st at 2:15 PM, agent Priya asked 'What is the FD rate for senior citizens?' and BankBot said 6.8%. Our actual rate was 7.2%. Can you reproduce exactly what happened?"*

**Non-deterministic system:** You cannot reproduce it. The LLM used temperature=0.7, and you don't know what it generated.

**Fix: Full determinism chain**

```python
import hashlib
import json

def deterministic_answer(query: str, agent_id: str) -> dict:
    # 1. Deterministic retrieval: log exact chunk IDs retrieved
    query_embedding = embed(query)  # Same model, same output
    retrieved_chunks = ann_search(query_embedding, top_k=5)
    chunk_ids = [c["id"] for c in retrieved_chunks]  # e.g., ["chunk_42", "chunk_89", ...]
    
    # 2. Deterministic LLM call
    response = openai_client.chat.completions.create(
        model="gpt-4o-2024-08-06",   # ← PINNED version, not "gpt-4o" (which changes!)
        messages=build_prompt(query, retrieved_chunks),
        temperature=0,               # ← Greedy decoding: always pick most likely token
        seed=42,                     # ← OpenAI reproducibility seed
        top_p=1,                     # ← No nucleus sampling
        frequency_penalty=0,
        presence_penalty=0
    )
    
    answer = response.choices[0].message.content
    
    # 3. Log everything for audit
    audit_record = {
        "timestamp": "2024-09-01T14:15:32Z",
        "agent_id": agent_id,
        "query": query,
        "query_embedding_hash": hashlib.md5(str(query_embedding).encode()).hexdigest(),
        "retrieved_chunk_ids": chunk_ids,        # ← Exact chunks used
        "model": "gpt-4o-2024-08-06",           # ← Exact model version
        "seed": 42,
        "temperature": 0,
        "response": answer,
        "response_fingerprint": response.system_fingerprint  # OpenAI's internal hash
    }
    
    return audit_record
```

**Now the auditor CAN reproduce:**
```
Given the logs from Sep 1 14:15:32:
- Retrieved chunks: ["chunk_42", "chunk_89", "chunk_103"]
- Chunk 42 contained: "Senior citizen FD rates: 6.8% for 1-year tenure" 
  (this was outdated! Updated to 7.2% on Sep 3rd)
- Model: gpt-4o-2024-08-06, temperature=0, seed=42

Root cause: The vector DB had stale data.
The document was updated in SharePoint on Aug 28th but the ingestion 
pipeline had a bug and didn't re-index it. Fixed in v1.2.3.
```

### Structured Output (Guarantees Valid Format)

```python
from pydantic import BaseModel, Field
from typing import Literal
from openai import OpenAI

class BankBotResponse(BaseModel):
    answer: str = Field(description="Direct answer to the query")
    source_section: str = Field(description="Policy section cited, e.g. 'Section 3.1'")
    confidence: Literal["high", "medium", "low"]
    disclaimer_needed: bool = Field(description="True if agent should add a disclaimer")

client = OpenAI()
response = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=messages,
    response_format=BankBotResponse,
    temperature=0,
)

# GUARANTEED to return valid BankBotResponse object. Never hallucinated JSON.
result: BankBotResponse = response.choices[0].message.parsed
print(result.answer)          # "TDS deducted at 10% under Section 194A"
print(result.source_section)  # "Section 194A, Income Tax Act"
print(result.confidence)      # "high"
print(result.disclaimer_needed)  # False
```

---

## 12. Replacing Embedding Models Without Downtime

### 🏦 Real Scenario

BankBot is using `text-embedding-ada-002` (1536 dims). OpenAI releases `text-embedding-3-large` (3072 dims, 15% better recall). You want to upgrade without the 5,000 agents experiencing any degradation.

**The challenge:** If you have 1,500,000 chunks embedded with ada-002, you **cannot** mix them with text-embedding-3-large in the same index. The vector spaces are incompatible.

### Full Migration Plan (Real)

```
WEEK 1: Build shadow index (background, no user impact)
─────────────────────────────────────────────────────
# Spin up GPU batch workers on Kubernetes
kubectl apply -f reembedding-job.yaml

# reembedding-job.yaml:
# image: bankbot/embedding-worker
# resources: requests: nvidia.com/gpu: "1"
# command: python reembed_all.py --model text-embedding-3-large --target-index bankbot-v2

# Python worker (runs in background):
def reembed_all_chunks():
    chunks = db.execute("SELECT id, chunk_text FROM chunks ORDER BY id")
    
    # Process in batches of 1000 (GPU optimal batch size)
    for batch in chunks.batches(1000):
        new_embeddings = openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=[c.chunk_text for c in batch]
        ).data
        
        # Write to NEW index (bankbot-v2), not touching bankbot-v1
        pinecone_v2.upsert([
            (c.id, emb.embedding, c.metadata)
            for c, emb in zip(batch, new_embeddings)
        ])
    
    # Time: 1.5M chunks / (1000/batch × 2 batches/sec) ≈ 12.5 minutes

WEEK 1: Dual-write for new documents
─────────────────────────────────────────────────────
# Any new document ingested DURING migration goes to BOTH indexes
def ingest_document(doc):
    chunks = chunk_document(doc)
    
    ada_embeddings = embed(chunks, model="text-embedding-ada-002")
    large_embeddings = embed(chunks, model="text-embedding-3-large")
    
    pinecone_v1.upsert(zip(chunk_ids, ada_embeddings))    # Old index
    pinecone_v2.upsert(zip(chunk_ids, large_embeddings))  # New index
    # Dual-write ensures no document is missing from either index

WEEK 2: Validate new index offline
─────────────────────────────────────────────────────
# Golden test set: 200 queries with known correct chunk IDs
for query, expected_chunk_ids in golden_test_set:
    v1_results = search_v1(query)
    v2_results = search_v2(query)
    
    v1_recall = len(set(v1_results) & set(expected_chunk_ids)) / len(expected_chunk_ids)
    v2_recall = len(set(v2_results) & set(expected_chunk_ids)) / len(expected_chunk_ids)

# Results:
# v1 (ada-002): Recall@5 = 0.82
# v2 (3-large): Recall@5 = 0.91   ← 11% improvement! Worth migrating.

WEEK 2: Shadow traffic (no user impact)
─────────────────────────────────────────────────────
def search(query):
    query_v1_emb = embed(query, model="text-embedding-ada-002")
    query_v2_emb = embed(query, model="text-embedding-3-large")
    
    # Serve from v1 to users (no change)
    results_served = pinecone_v1.query(query_v1_emb, top_k=5)
    
    # Shadow query v2 (background, results discarded)
    results_shadow = pinecone_v2.query(query_v2_emb, top_k=5)
    
    # Log both for comparison
    log_shadow_comparison(query, results_served, results_shadow)
    
    return results_served  # User gets v1 results

# After 48h of shadow traffic:
# v2 returns same or better top-3 chunks in 89% of queries
# Green light to proceed

WEEK 3: Canary switch (5% of agents)
─────────────────────────────────────────────────────
FEATURE_FLAG = {
    "v2_canary_percentage": 5,
    "v2_model": "text-embedding-3-large",
    "v2_index": "bankbot-v2"
}

def search_with_canary(query, agent_id):
    bucket = hash(agent_id) % 100
    if bucket < FEATURE_FLAG["v2_canary_percentage"]:
        emb = embed(query, model="text-embedding-3-large")
        return pinecone_v2.query(emb, top_k=5)
    else:
        emb = embed(query, model="text-embedding-ada-002")
        return pinecone_v1.query(emb, top_k=5)

# After 48h canary:
# Thumbs up rate: canary=81%, control=78%  → v2 is better
# Latency: canary=95ms, control=15ms  → v2 is slower (larger model)
# Decision: acceptable trade-off. Proceed to full rollout.

WEEK 3: Full cutover + cleanup
─────────────────────────────────────────────────────
FEATURE_FLAG["v2_canary_percentage"] = 100  # All traffic to v2

# Keep v1 index for 7 days (instant rollback if issues emerge)
# After 7 days with no issues: delete v1 index
# Stop dual-write in ingestion pipeline
```

---

## 13. Fallback Mechanisms

### 🏦 Real Outage: OpenAI API Down

**Tuesday 3 PM:** OpenAI status page shows "API Degraded." All BankBot LLM calls failing.

**Without fallbacks:** 5,000 agents get error screens. Chaos.

**With fallback chain:**

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class BankBotOrchestrator:
    def answer(self, query: str, context_chunks: list) -> str:
        
        # Stage 1: Try primary LLM (GPT-4o via API)
        try:
            return self._call_gpt4o(query, context_chunks)
        except Exception as e:
            log.warning(f"GPT-4o failed: {e}. Trying fallback.")
        
        # Stage 2: Try self-hosted Llama (always available, our servers)
        try:
            return self._call_llama_local(query, context_chunks)
        except Exception as e:
            log.warning(f"Llama-local failed: {e}. Trying cache.")
        
        # Stage 3: Return cached response for semantically similar query
        cached = semantic_cache.get(query, threshold=0.92)
        if cached:
            return f"[Cached response] {cached}"
        
        # Stage 4: Return top retrieved chunk directly (no generation)
        if context_chunks:
            return (
                f"Here is the most relevant section I found:\n\n"
                f"{context_chunks[0]['text']}\n\n"
                f"(Source: {context_chunks[0]['metadata']['section']})"
            )
        
        # Stage 5: BM25 keyword search (no vectors, no LLM)
        bm25_results = elasticsearch.search(query, size=1)
        if bm25_results:
            return f"Related information: {bm25_results[0]['_source']['text']}"
        
        # Stage 6: Graceful degradation
        return (
            "I'm experiencing technical difficulties right now. "
            "Please try again in a few minutes or contact the policy helpdesk at ext. 1234."
        )

    @retry(
        stop=stop_after_attempt(2),       # Try twice
        wait=wait_exponential(min=1, max=4)  # Wait 1s, then 4s
    )
    def _call_gpt4o(self, query, chunks):
        response = openai_client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=self._build_prompt(query, chunks),
            timeout=5.0   # Hard timeout: don't wait more than 5s
        )
        return response.choices[0].message.content
```

**Result during OpenAI outage:**
```
1,200 requests failed → GPT-4o (Stage 1 failed)
1,200 requests served → Llama-3 local (Stage 2)
Agents noticed slightly different response quality but no downtime
SLA maintained. Zero tickets from outage.
```

---

## 14. Solving Without LLMs or Vector DBs

### 🏦 Real Alternative: BankBot v0 (before LLMs)

Before GPT-4 was available, the bank had a simpler system. Let's see what it looked like and when it's actually better.

```python
from rank_bm25 import BM25Okapi
import spacy
import json

nlp = spacy.load("en_core_web_sm")

# Load all FAQ pairs (written by policy team)
with open("banking_faqs.json") as f:
    faqs = json.load(f)
# [
#   {"q": "What is the penalty for early FD withdrawal?", "a": "1% of principal per Section 3.1"},
#   {"q": "What documents needed for KYC?", "a": "Aadhaar, PAN, address proof"},
#   ...  (2,000 FAQs)
# ]

# Build BM25 index
def preprocess(text):
    doc = nlp(text.lower())
    return [token.lemma_ for token in doc 
            if not token.is_stop and not token.is_punct]

tokenized_questions = [preprocess(faq["q"]) for faq in faqs]
bm25 = BM25Okapi(tokenized_questions)

def answer_classical(query: str) -> str:
    tokens = preprocess(query)
    scores = bm25.get_scores(tokens)
    
    top_idx = scores.argmax()
    top_score = scores[top_idx]
    
    if top_score < 1.5:  # Confidence threshold
        return None  # Not confident enough
    
    return {
        "answer": faqs[top_idx]["a"],
        "confidence": float(top_score),
        "matched_question": faqs[top_idx]["q"],
        "method": "bm25"
    }
```

**Where BM25 + Rules BEATS LLMs:**

```
Query: "194A"   (agent just types the section number)
  BM25: Returns the TDS FAQ immediately (exact match on "194A")
  LLM:  Might say "Section 194A relates to..." (verbose, slower)
  Winner: BM25 (faster, exact)

Query: "Penalty Section 3.1 FD"
  BM25: Exact match → 0ms, $0 cost
  LLM:  150ms + $0.0064
  Winner: BM25

Query: "If a customer opened FD in Feb 2023 with auto-renewal, closes it in Nov 
        2024 during a declared emergency, and the nomination was not updated after 
        marriage, what rules apply?"
  BM25: Returns "early closure FAQ" (misses nomination/marriage angle)
  LLM:  Synthesizes from multiple policy sections correctly
  Winner: LLM (complex multi-hop reasoning)
```

**Hybrid approach (best of both worlds):**
```python
def answer(query: str) -> str:
    # Try BM25 first (free, fast)
    bm25_result = answer_classical(query)
    
    if bm25_result and bm25_result["confidence"] > 3.0:
        # High confidence BM25 match → return immediately, no LLM cost
        return bm25_result
    
    # BM25 not confident → use LLM with RAG
    return answer_with_rag(query)

# Real impact: 40% of queries resolved by BM25 → 40% LLM cost savings
# These are simple, repetitive queries that BM25 handles perfectly
```

---

## 15. Tokenization & Embeddings From Scratch

### Tokenization — Building BPE Step by Step

**Input text from BankBot training corpus:**
```
"fixed deposit fd maturity"
```

**Step 1: Start with characters (+ end-of-word marker)**
```
Vocabulary: {f, i, x, e, d, " ", p, o, s, t, a, m, u, r, y, </w>}

Words as character sequences:
  "fixed"   → [f, i, x, e, d, </w>]
  "deposit" → [d, e, p, o, s, i, t, </w>]
  "fd"      → [f, d, </w>]
  "maturity"→ [m, a, t, u, r, i, t, y, </w>]
```

**Step 2: Count most frequent adjacent pairs across the whole corpus**
```
Let's say our corpus has thousands of banking documents:

Pair frequencies:
  ("i", "t") → 847 times  ← Most frequent pair!
  ("e", "d") → 612 times
  ("f", "d") → 589 times
  ("a", "t") → 441 times
  ...

Merge ("i", "t") → "it"
New vocabulary: {f, i, x, e, d, " ", p, o, s, t, a, m, u, r, y, </w>, it}
```

**Step 3: Continue merging (50,000 iterations for GPT-4)**
```
Iteration 2:  ("f", "d") → "fd"      (banking abbreviation appears a lot!)
Iteration 3:  ("e", "d") → "ed"
Iteration 4:  ("fix", "ed") → "fixed"
Iteration 5:  ("mat", "ur") → "matur"
...
Iteration 489: ("fixed", " deposit") → "fixed deposit"
Iteration 490: ("fixed deposit", " ") → "fixed_deposit"  ← Whole phrase becomes 1 token!
```

**Why does this matter?**
```
"fixed deposit"    → 1 token  (common in banking corpus)
"supercalifragilistic" → 6 tokens (rare word, split up)
"KYC"             → 1 token  (if in vocab)  or  3 tokens [K, Y, C]  (if not)

Real cost implication:
  Sentence: "The FD maturity date is..."
  With banking-tuned tokenizer: 7 tokens
  With general tokenizer: 9 tokens  ← 28% more expensive to process!
```

---

### Embeddings — How Similarity Actually Works

**Word2Vec training on BankBot corpus:**

```
Training sentence: "The fixed deposit penalty is one percent of principal"

Window size = 2: For center word "penalty":
  Context words: ["deposit", "is", "one", "percent"]

Model learns: "penalty" appears near "deposit", "percent", "principal"
              NOT near "customer", "branch", "account"

After training:
  penalty  → [0.23, 0.87, -0.41, ...]   
  charge   → [0.21, 0.85, -0.39, ...]   ← Similar direction! (synonyms)
  interest → [0.19, 0.72, -0.21, ...]   ← Somewhat similar (financial context)
  mango    → [-0.81, 0.12, 0.77, ...]   ← Completely different direction
```

**Cosine similarity — how retrieval actually works:**

```python
import numpy as np

# Agent asks: "What is the fee for closing FD early?"
query_embedding = np.array([0.22, 0.83, -0.38, 0.11, ...])  # 1536 dims

# Document chunk 1: "Early FD closure incurs 1% penalty on principal"
chunk1_embedding = np.array([0.21, 0.85, -0.40, 0.10, ...])

# Document chunk 2: "Savings account minimum balance requirements"
chunk2_embedding = np.array([-0.52, 0.21, 0.67, -0.33, ...])

# Cosine similarity calculation:
def cosine_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

sim_query_chunk1 = cosine_sim(query_embedding, chunk1_embedding)
# = (0.22×0.21 + 0.83×0.85 + (-0.38)×(-0.40) + ...) / (||query|| × ||chunk1||)
# ≈ 0.94  ← High similarity! Same topic.

sim_query_chunk2 = cosine_sim(query_embedding, chunk2_embedding)
# ≈ 0.31  ← Low similarity. Different topic.
```

**Why cosine and not Euclidean distance?**
```
Vector A = [1, 0, 0]      (short vector, "cat")
Vector B = [100, 0, 0]    (long vector, also "cat" but scaled)
Vector C = [0, 1, 0]      ("dog")

Euclidean: distance(A, B) = 99  → A and B seem very different!
Cosine:    similarity(A, B) = 1.0  → A and B are perfectly similar ✓
           similarity(A, C) = 0.0  → A and C are unrelated ✓

Cosine ignores magnitude, only cares about direction (meaning).
```

---

## 16. What Happens During Fine-Tuning?

### 🏦 Real Fine-Tuning Walkthrough for BankBot

**Starting point:** Base Llama-3-8B weights: 8 billion numbers, each a float (4 bytes) = 32GB.

**We want it to learn:** When asked about banking, give specific answers citing policy sections.

---

### Forward Pass (in detail)

```
Input: "What is the TDS rate for FD interest?"
Tokenized: [1, 1724, 338, 278, 323, 9310, 4338, 363, 383, 360, 4066, 29973]
           [BOS, "What", "is", "the", "TDS", "rate", "for", "FD", "interest", "?"]

Layer 1 — Self-Attention:
  Each token looks at every other token:
  "TDS" pays attention to:
    "rate" (70% weight) ← strong relation
    "FD"   (60% weight) ← strong relation  
    "What" (10% weight) ← weak, just context
  
  This creates a context-aware representation of "TDS":
  Before attention: [0.2, -0.5, 0.8, ...]   (just "TDS" in isolation)
  After attention:  [0.6, -0.1, 0.4, ...]   ("TDS" knowing it's about "rate for FD")

Layer 1 — FFN (Feed Forward Network):
  This is where "knowledge" is stored (key insight from recent research!)
  h = GELU(embedding @ W1 + b1) @ W2 + b2
  
  Think of W1 (dimension: 4096 × 14336) as a giant lookup:
  "TDS + rate + FD" pattern → activates neurons 1,847 and 3,291
  Those neurons correspond to "10%, Section 194A" knowledge

Continue through 32 layers...

Output layer:
  Final hidden state → multiply by vocab embedding matrix (shape: 4096 × 128256)
  Output: probability distribution over all 128,256 tokens
  
  Top predictions for next token after "FD interest?":
  "TDS" → 0.001  (wait, that's the input...)
  
  Actually, we're training on:
  Input:  "What is the TDS rate for FD interest?"
  Target: "TDS is deducted at 10% under Section 194A if annual interest exceeds ₹40,000."
  
  Model predicts next token after full input + partial answer:
  After "TDS is deducted at " → predictions:
    "10%"    → probability 0.12  (model is unsure)
    "2%"     → probability 0.08
    "5%"     → probability 0.15
    "0.5%"   → probability 0.19
  
  LOSS = -log(0.12) = 2.12   ← Large loss! The model doesn't know the rate yet.
```

---

### Backward Pass (Gradient Descent)

```
Loss = 2.12

Backpropagation:
  ∂Loss/∂W_output = how much does changing each output weight reduce loss?
  ∂Loss/∂W_ffn_32 = gradient flows backward through Layer 32's FFN
  ∂Loss/∂W_ffn_31 = gradient flows backward through Layer 31's FFN
  ...
  ∂Loss/∂W_embed  = gradient reaches embedding layer

Adam optimizer update:
  For each parameter W:
    momentum = 0.9 × old_momentum + 0.1 × gradient
    variance = 0.999 × old_variance + 0.001 × gradient²
    W = W - (lr × momentum / √variance)
  
  Effectively: "Nudge the weight slightly in the direction that reduces loss"
  
After one step:
  The neuron that was supposed to activate for "10%" gets a tiny bump.
  Probability of "10%" → 0.12 → 0.13 (barely changed from one example)
  
After 500 examples of TDS:
  Probability of "10%" after "TDS is deducted at " → 0.78
  Model has learned!
```

---

### LoRA — What's Really Happening

```
Full fine-tuning changes ALL 8B parameters.
LoRA changes only 13M parameters (0.16% of the model).

How?

Original weight matrix W (frozen, never changes):
  W ∈ R^(4096 × 4096)   [4096 input dims → 4096 output dims]
  4096 × 4096 = 16.7M parameters

LoRA adds:
  A ∈ R^(4096 × 16)     [16 = rank r]
  B ∈ R^(16 × 4096)
  Combined: 4096×16 + 16×4096 = 131,072 parameters
  
During forward pass:
  output = x @ W + x @ A @ B × (32/16)
           ────────   ──────────────────
           frozen      LoRA adaptation
           base        (trained)

Intuition: W already "knows" language, grammar, reasoning.
           A and B learn the "delta" — the banking-specific adaptation.
           
Example:
  W(Q) projects "TDS" to general query space: [finance, question, regulatory, ...]
  A@B shifts this projection toward: [banking, India, tax, specific_rate, ...]
  
After fine-tuning: "TDS" queries get routed to "10%, Section 194A" answers.
Base model knowledge (grammar, reasoning) completely preserved.
```

### Learning Rate Warmup — Why It Matters

```
Training step 1:
  Adam's momentum estimate m_0 = 0  (initialized to zero)
  Adam's variance estimate  v_0 = 0
  
  Bias-corrected variance: v̂ = v/(1-0.999^1) = 0/0.001 ≈ 0
  
  Update: W = W - lr × m̂ / (√v̂ + 1e-8)
            = W - lr × m̂ / (0 + 1e-8)
            = W - lr × m̂ × 100,000,000
  
  EXPLOSION! The first gradient step is multiplied by ~100M.
  This destroys fine-tuning before it even starts.

Without warmup:
  lr = 1e-4 from step 1 → gradient explodes → loss → NaN → training fails

With warmup (first 100 steps, lr ramps from 0 to 1e-4):
  Step 1:  lr = 1e-6   (tiny, safe)
  Step 10: lr = 1e-5   (still small)
  Step 50: lr = 5e-5   (warming up)
  Step 100: lr = 1e-4  (target reached, Adam estimates stable by now)

After step 100: Adam's estimates are stable.
  m̂ ≈ actual gradient direction (momentum accumulated)
  v̂ ≈ actual gradient variance (adaptive scaling ready)
  Updates are now well-calibrated: large for uncertain params, small for stable ones.
```

### Layer Freezing in Practice

```python
# BankBot fine-tuning strategy:
# The bank's domain is specific (Indian banking).
# We want to keep general reasoning but adapt domain knowledge.

for name, param in model.named_parameters():
    if any(layer in name for layer in [
        "embed_tokens",           # Word embeddings: keep frozen
        "model.layers.0.",        # Layer 0: general syntax, keep frozen
        "model.layers.1.",        # Layer 1: general semantics, keep frozen
    ]):
        param.requires_grad = False
        print(f"Frozen: {name}")
    else:
        param.requires_grad = True   # Layers 2-31: fine-tune
        print(f"Training: {name}")

# Result:
# Frozen (2 layers + embeddings): ~500M params
# Training (30 layers): ~7.5B params   ← with LoRA: only 13M actually update

# Why keep early layers frozen?
# Layer 0-1 learn syntax ("verb + noun → question"), grammar, basic attention
# These are domain-independent and should NOT change
# Layers 20-31 learn domain concepts ("TDS", "Section 194A", "FD rates")
# These ARE what we want to update
```

---

## Summary: How Everything Connects in BankBot

```
1. 50,000 PDFs → chunked → embedded (ada-002 → text-embedding-3-large)
2. 1.5M chunk vectors stored in pgvector + metadata in PostgreSQL
3. Agent asks question → embed query → ANN search (HNSW, 15ms)
4. Hybrid BM25 + dense → RRF fusion → top 5 chunks
5. Cross-encoder re-ranks → top 3 chunks to LLM
6. GPT-4o (API) for complex, Llama-3 local for simple + privacy
7. Response streamed back (perceived latency ~420ms)
8. Thumbs up/down logged → Kafka → DPO training pairs collected
9. Every 2 weeks: fine-tune LoRA adapter, evaluate, A/B test, ship
10. All responses logged with chunk IDs + model version for audit
11. Circuit breakers: OpenAI down → Llama → cache → raw text → graceful error
12. Grafana: P99 < 2s, thumbs up > 78%, faithfulness > 0.88, GPU util < 80%
```

---

*Document version: 1.0 | Context: ML System Design Interviews | Example: BankBot (Banking AI Assistant)*
