# 🤖 AI Engineer Sprint: Intelligence Layer Implementation

This guide focuses EXCLUSIVELY on the AI logic for the Banking & Insurance Agent. 
Infrastructure, API endpoints (FastAPI), and Database management are handled by the Backend Developer.

---

## 🏗️ 1. Logic & Agency (The Brain)
**File:** `agents/base.py`
**Goal:** Implement the "Thinking" loop using **ReAct (Reasoning and Acting)**.

- [ ] **Context Routing**: Logic to decide if a query needs **RAG** (Policy Check) or **Vision** (ID/Form Extraction).
- [ ] **State Management**: Handling conversation memory and cost-per-call metadata.
- [ ] **Temperature Optimization**: Tuning `top_p` and `temperature` (suggested: 0.2 for banking, 0.7 for creative summaries).

---

## 🔍 2. RAG Excellence (Retrieval)
**File:** `rag/retriever.py` & `rag/reranker.py`
**Goal:** Maximize precision in context retrieval.

- [ ] **Hybrid Search Config**: Combine **OData keywords** and **Vector embeddings** (text-embedding-3-small).
- [ ] **Semantic Reranking**: Integrate **Azure Search Semantic Ranker** to sort top 5 documents by conceptual relevance.
- [ ] **Context Injection**: Designing the "Context Sandwich" (Instructions + Data + Query) for the LLM.

---

## 👁️ 3. Computer Vision & OCR (Extraction)
**File:** `vision/analysis.py` & `rag/ingest.py`
**Goal:** Turn documents into structured, LLM-ready JSON.

- [ ] **Layout-Aware Ingestion**: Use **Document Intelligence** to preserve table hierarchies (crucial for bank statements).
- [ ] **Vision Validation**: Use **Azure Computer Vision 4.0** to detect key visual anchors (e.g., Signature present: True/False).
- [ ] **Multimodal Embeddings**: (Optional) Use Image Embeddings to find similar document layouts.

---

## ✍️ 4. Prompt Engineering (The Persona)
**Path:** `prompts/v1/`
**Goal:** Versioning the "Expertise" of the AI.

- [ ] **System Prompt (`system.txt`)**: Defining the Banking Agent persona, guardrails, and compliance rules.
- [ ] **Few-Shot Examples**: Providing the LLM with example Q&A pairs for complex insurance claims.
- [ ] **Chain-of-Thought (CoT)**: Forcing the AI to explain its math before approving a loan.

---

## 📈 5. AI Evaluation (Quality Control)
**File:** `evals/metrics/`
**Goal:** Measure if the AI is hallucinating or losing relevance.

- [ ] **Faithfulness Metric**: Check if the LLM's answer is supported 100% by the retrieved context.
- [ ] **Answer Relevancy**: Measuring how directly the AI answered the user's banking query.
- [ ] **Latency Monitoring**: Tracking time-to-first-token (TTFT) for Azure OpenAI calls.

---

### 🚀 Next Implementation Step: 
"I am ready to implement the `BankingAgent` ReAct logic in `agents/base.py`."
