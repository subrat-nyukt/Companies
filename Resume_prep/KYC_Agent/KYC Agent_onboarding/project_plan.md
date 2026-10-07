# Azure Multi-Agent RAG Architecture Plan

## 1. Project Structure Mapping
Following the proposed high-performance template, we will map Azure-native services into each module:

- **core/**: Centralized Azure OpenAI client (GPT-4o/o1) and Vision configurations.
- **rag/**: Azure AI Search (Vector Store) + Document Intelligence (OCR/layout) + Azure AI Vision for image analysis.
- **agents/**: LangGraph/ReAct loop orchestration for loan/insurance claim processing.
- **observability/**: Azure Monitor and per-call token/cost tracking.

```text
llm-project-template/
│
├── core/
│   ├── client.py        # AzureOpenAI (Async) + AISearch Client
│   ├── router.py        # Tiered model routing (e.g. gpt-4o vs gpt-4o-mini)
│   └── config.py        # Pydantic Settings for Azure Endpoints/Keys
│
├── agents/              # Business Logic (Loan/Insurance specific)
│   ├── base.py          # State/Memory management for conversations
│   ├── loan_agent.py    # Specific logic for loan approvals
│   └── tools/
│       └── azure_tools.py # Search, Document Parsing, OCR tools
│
├── rag/                 # Data Pipeline
│   ├── ingest.py        # Azure AI Document Intelligence integration
│   ├── chunker.py       # Layout-aware chunking (tables/headers)
│   ├── embedder.py      # Azure OpenAI Embeddings (text-embedding-3-small)
│   ├── retriever.py     # Azure Search (Hybrid: Vector + Keyword)
│   └── reranker.py      # Azure Search Semantic Reranking
│
├── vision/              # Multimodal module
│   ├── analysis.py      # Azure Vision SDK for ID/Form extraction
│   └── image_embed.py   # Multi-modal embedding extraction
│
├── prompts/             # System & User prompt versioning
├── evals/               # RAGAS metrics for faithfulness/groundedness
├── tests/               # Unit and integration (Mocking Azure APIs)
└── .env                 # Azure credentials
```

---

## 2. Technology Stack (Azure Edition)
| Function | Azure Service | Python SDK |
| :--- | :--- | :--- |
| **LLM** | Azure OpenAI (GPT-4o) | `openai` (Azure variant) |
| **OCR / Layout** | Azure AI Document Intelligence | `azure-ai-formrecognizer` |
| **Vision / Image** | Azure AI Vision | `azure-ai-vision` |
| **Vector DB** | Azure AI Search | `azure-search-documents` |
| **Embeddings** | Azure OpenAI (Text/Image) | `openai` |
| **Monitoring** | Azure Application Insights | `azure-monitor-opentelemetry` |

---

## 3. Implementation Steps

### Phase 1: Core Foundation (The Skeleton)
1. Initialize the directory structure.
2. Setup `core/config.py` with environment variable validation.
3. Build `core/client.py` using `AsyncAzureOpenAI`.

### Phase 2: RAG Pipeline with OCR
1. Implement `rag/ingest.py`: Use **Document Intelligence** to parse complex banking forms/PDFs with layout awareness (preserving tables).
2. Implement `rag/retriever.py`: Integrate **Azure AI Search** with hybrid search (Vector + BM25).

### Phase 3: Vision & Multi-modal Integration
1. Implement `vision/analysis.py`: Use **Azure Vision** for OCR and image-based document validation (e.g. checking signatures, ID cards).

### Phase 4: Agent & Performance
1. Build `agents/base.py`: Implement the ReAct loop with state persistence.
2. Implement `prompts/`: Move all prompts into managed `.txt` files.
3. Setup `observability/`: Track token counts and latency for every Azure API call.

### Phase 5: Evaluation
1. Build `evals/runner.py` to test the RAG accuracy using sample banking document datasets.

---

## 4. Next Actions
1. **Directory Setup**: Create folders.
2. **Environment Configuration**: Create `.env.example` with Azure-specific keys.
3. **Requirement Setup**: Create `pyproject.toml` or `requirements.txt`.
