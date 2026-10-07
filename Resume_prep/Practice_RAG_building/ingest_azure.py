"""
ingest_azure.py
===============
Azure AI Search equivalent of ingest.py.

PIPELINE (identical logic, different services):
  PDF → Chunks → Azure OpenAI Embeddings → Azure AI Search Index

REQUIRED ENV VARS (.env):
  AZURE_OPENAI_ENDPOINT       = https://<your-resource>.openai.azure.com/
  AZURE_OPENAI_API_KEY        = <your azure openai key>
  AZURE_OPENAI_EMBED_DEPLOYMENT = text-embedding-3-small  (your deployment name)

  AZURE_SEARCH_ENDPOINT       = https://<your-resource>.search.windows.net
  AZURE_SEARCH_API_KEY        = <your azure search admin key>
  AZURE_SEARCH_INDEX_NAME     = kyc-policy-index

INSTALL:
  pip install azure-search-documents azure-identity openai pypdf python-dotenv langchain
"""

import os
import uuid
from dotenv import load_dotenv
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Azure SDKs
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)


# ─────────────────────────────────────────────
# 1. CONFIGURATION
# ─────────────────────────────────────────────
load_dotenv()

# Azure OpenAI — for embeddings
AZURE_OPENAI_ENDPOINT         = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY          = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_EMBED_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-small")

# Azure AI Search — for vector storage and retrieval
AZURE_SEARCH_ENDPOINT    = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY     = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME  = os.getenv("AZURE_SEARCH_INDEX_NAME", "kyc-policy-index")

# Chunking config (same as ingest.py)
PDF_FILE   = "kyc_policy.pdf"
CHUNK_SIZE = 1000
OVERLAP    = 50
BATCH_SIZE = 50

# Vector dimension of text-embedding-3-small
VECTOR_DIMENSIONS = 1536


# ─────────────────────────────────────────────
# 2. CLIENTS
# ─────────────────────────────────────────────
# Azure OpenAI client (replaces openrouter-based OpenAI client in ingest.py)
azure_openai_client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-02-01"
)

# Azure AI Search admin client — used to CREATE the index schema
credential     = AzureKeyCredential(AZURE_SEARCH_API_KEY)
index_client   = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=credential)

# Azure AI Search document client — used to UPLOAD documents
search_client  = SearchClient(
    endpoint=AZURE_SEARCH_ENDPOINT,
    index_name=AZURE_SEARCH_INDEX_NAME,
    credential=credential
)


# ─────────────────────────────────────────────
# 3. STEP 1 — READ PDF  (identical to ingest.py)
# ─────────────────────────────────────────────
print("Step 1: Reading PDF...")
extracted_text = []
try:
    with open(PDF_FILE, "rb") as f:
        reader = PdfReader(f)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            extracted_text.append({"page_number": i, "text": text.strip()})
    print(f"  -> Extracted {len(extracted_text)} pages.")
except FileNotFoundError:
    print(f"Error: {PDF_FILE} not found.")
    exit(1)


# ─────────────────────────────────────────────
# 4. STEP 2 — CHUNK TEXT  (identical to ingest.py)
# ─────────────────────────────────────────────
print("Step 2: Chunking text...")

def get_chunks(extracted_text: list) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    all_chunks = []
    global_chunk_count = 0
    for entry in extracted_text:
        page_chunks = splitter.split_text(entry["text"])
        for chunk in page_chunks:
            all_chunks.append({
                "id":          str(uuid.uuid4()),   # Azure Search requires a unique string "id" field
                "text":        chunk,
                "source":      PDF_FILE,
                "page_number": str(entry["page_number"]),  # Azure Search fields are typed; store as string
                "chunk_index": str(global_chunk_count)
            })
            global_chunk_count += 1
    return all_chunks

chunks = get_chunks(extracted_text)
print(f"  -> Generated {len(chunks)} chunks.")


# ─────────────────────────────────────────────
# 5. STEP 3 — CREATE INDEX SCHEMA IN AZURE AI SEARCH
# ─────────────────────────────────────────────
# KEY DIFFERENCE FROM PINECONE:
# Pinecone requires zero schema setup — you just upsert vectors.
# Azure AI Search requires you to define every field explicitly:
#   - SimpleField:    stored but not searchable text (metadata)
#   - SearchableField: full-text searchable (BM25 keyword search)
#   - SearchField:    the actual vector field (for cosine similarity search)
#
# This extra step is what ENABLES hybrid retrieval — both vector AND keyword
# search on the same index, which Pinecone cannot do natively.
# ─────────────────────────────────────────────
print("Step 3: Creating Azure AI Search index schema...")

fields = [
    # "id" is the required unique key field in Azure AI Search
    SimpleField(name="id",          type=SearchFieldDataType.String, key=True, filterable=True),

    # "text" is both STORED and KEYWORD-SEARCHABLE (enables BM25 / hybrid search)
    SearchableField(name="text",    type=SearchFieldDataType.String),

    # Metadata fields — stored for display, filterable for role-based access
    SimpleField(name="source",       type=SearchFieldDataType.String,  filterable=True),
    SimpleField(name="page_number",  type=SearchFieldDataType.String,  filterable=True),
    SimpleField(name="chunk_index",  type=SearchFieldDataType.String,  filterable=True),

    # The VECTOR field — this is where cosine similarity search happens
    # dimensions must exactly match the embedding model output (1536 for text-embedding-3-small)
    SearchField(
        name="content_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=VECTOR_DIMENSIONS,
        vector_search_profile_name="myHnswProfile"   # Links to the HNSW algorithm config below
    )
]

# HNSW = Hierarchical Navigable Small World — the algorithm Azure uses for
# approximate nearest neighbour (ANN) vector search. It is fast and memory-efficient.
vector_search = VectorSearch(
    algorithms=[
        HnswAlgorithmConfiguration(name="myHnswAlgo")  # HNSW with cosine similarity
    ],
    profiles=[
        VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnswAlgo")
    ]
)

index_def = SearchIndex(
    name=AZURE_SEARCH_INDEX_NAME,
    fields=fields,
    vector_search=vector_search
)

# Create or overwrite the index
index_client.create_or_update_index(index_def)
print(f"  -> Index '{AZURE_SEARCH_INDEX_NAME}' created/updated in Azure AI Search.")


# ─────────────────────────────────────────────
# 6. STEP 4 — EMBED CHUNKS (using Azure OpenAI instead of OpenRouter)
# ─────────────────────────────────────────────
print("Step 4: Embedding chunks with Azure OpenAI...")

# Embed in batches to avoid rate limits
for i in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[i : i + BATCH_SIZE]
    batch_texts = [c["text"] for c in batch]

    response = azure_openai_client.embeddings.create(
        model=AZURE_OPENAI_EMBED_DEPLOYMENT,  # This is your Azure deployment name
        input=batch_texts
    )

    for j, embedding_object in enumerate(response.data):
        chunks[i + j]["content_vector"] = embedding_object.embedding

print(f"  -> Embedded all {len(chunks)} chunks. Each vector: {len(chunks[0]['content_vector'])} dimensions.")


# ─────────────────────────────────────────────
# 7. STEP 5 — UPLOAD TO AZURE AI SEARCH
# (replaces index.upsert() from Pinecone)
# ─────────────────────────────────────────────
print("Step 5: Uploading documents to Azure AI Search...")

total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

for i in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[i : i + BATCH_SIZE]
    batch_num = i // BATCH_SIZE + 1

    try:
        # upload_documents is the Azure equivalent of Pinecone's index.upsert()
        # It also "upserts" — creates new or updates existing documents by id.
        result = search_client.upload_documents(documents=batch)
        print(f"  -> Uploaded batch {batch_num} of {total_batches} ({len(batch)} docs). "
              f"Succeeded: {sum(1 for r in result if r.succeeded)}")
    except Exception as e:
        print(f"  -> Failed to upload batch {batch_num}: {e}")

print("\nIngestion Complete! Your KYC policy is now searchable in Azure AI Search.")
print(f"Index name: {AZURE_SEARCH_INDEX_NAME}")
print(f"Total documents indexed: {len(chunks)}")
