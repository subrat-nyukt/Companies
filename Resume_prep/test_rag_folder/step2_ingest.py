"""
=============================================================
  KYC RAG — Step 2: Ingest
  PDF -> Chunks -> Embeddings -> Pinecone
=============================================================

What this script does (in plain English):
  1. READ   — open the KYC PDF and extract all the text
  2. CHUNK  — split the text into small overlapping pieces
  3. EMBED  — convert each piece into a list of numbers (vector)
              using OpenAI's embedding model
  4. STORE  — upload those vectors into Pinecone so we can
              search them later

Run:
    python step2_ingest.py
"""

# ── Standard library ──────────────────────────────────────────────────────
import os       # read environment variables
import uuid     # generate unique IDs for each chunk
import time     # wait for Pinecone index to be ready

# ── Third-party ───────────────────────────────────────────────────────────
from dotenv import load_dotenv       # loads keys from .env file
from pypdf import PdfReader          # reads PDF files
import tiktoken                      # counts tokens (like OpenAI does)
from openai import OpenAI            # OpenAI API client
from pinecone import Pinecone, ServerlessSpec   # Pinecone vector DB client

# ─────────────────────────────────────────────────────────────────────────
# CONFIGURATION  — change these values to experiment
# ─────────────────────────────────────────────────────────────────────────
PDF_FILE      = "kyc_policy.pdf"         # the PDF we want to ingest
EMBED_MODEL   = "text-embedding-3-small" # OpenAI embedding model (1536-dim)
EMBED_DIMS    = 1536                     # number of dimensions of each vector
CHUNK_SIZE    = 400                      # how many tokens per chunk (~300 words)
CHUNK_OVERLAP = 80                       # how many tokens to repeat between chunks
BATCH_SIZE    = 50                       # how many vectors to upload at once


# ─────────────────────────────────────────────────────────────────────────
# STEP 0 — Load API keys from .env
# ─────────────────────────────────────────────────────────────────────────
load_dotenv()

OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME       = os.getenv("PINECONE_INDEX_NAME", "kyc-rag-index")

# Fail early if keys are missing — better than a cryptic error later
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing from your .env file")
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY is missing from your .env file")
if not os.path.exists(PDF_FILE):
    raise FileNotFoundError(f"PDF not found: '{PDF_FILE}'. Run step1_generate_pdf.py first.")


# ─────────────────────────────────────────────────────────────────────────
# STEP 1 — Read the PDF
# ─────────────────────────────────────────────────────────────────────────
# PdfReader opens the PDF and lets us access each page's text.

print(f"\n[1/4] Reading PDF: {PDF_FILE}")

reader = PdfReader(PDF_FILE)
all_text_chunks_raw = []   # will hold {"page_num": int, "text": str}

for page_index, page in enumerate(reader.pages):
    text = page.extract_text() or ""   # returns "" if page has no text
    text = text.strip()

    if text:   # skip blank pages
        all_text_chunks_raw.append({
            "page_num": page_index + 1,
            "text": text,
        })

print(f"    -> Extracted text from {len(all_text_chunks_raw)} pages")


# ─────────────────────────────────────────────────────────────────────────
# STEP 2 — Chunk the text
# ─────────────────────────────────────────────────────────────────────────
# WHY chunk?
#   LLMs can only read a limited amount of text at once. We break the
#   document into small pieces so we can find and send only the
#   *relevant* piece to the LLM when a question is asked.
#
# WHY overlap?
#   If a sentence falls right at the boundary between chunk 4 and chunk 5,
#   without overlap it would be cut in half. Overlap makes sure that
#   sentence appears fully in at least one chunk.
#
# WHY token-based (not character-based)?
#   OpenAI charges and limits by tokens, not characters.
#   "KYC" = 1 token. "antidisestablishmentarianism" = 7 tokens.
#   tiktoken counts exactly as OpenAI does.

print(f"\n[2/4] Chunking text (size={CHUNK_SIZE} tokens, overlap={CHUNK_OVERLAP} tokens)")

# cl100k_base is the tokeniser used by GPT-4 and text-embedding-3 models
tokenizer = tiktoken.get_encoding("cl100k_base")
chunks = []   # final list of chunk dicts

for page in all_text_chunks_raw:
    # Convert page text -> list of token IDs
    tokens = tokenizer.encode(page["text"])

    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_SIZE, len(tokens))

        # Convert token IDs back to readable text
        chunk_text = tokenizer.decode(tokens[start:end])

        chunks.append({
            "id":         str(uuid.uuid4()),  # unique ID for Pinecone
            "page_num":   page["page_num"],
            "text":       chunk_text,
            "num_tokens": end - start,
        })

        # If we've reached the last token, stop
        if end == len(tokens):
            break

        # Move forward, but step back by overlap amount
        # e.g. size=400, overlap=80 -> next chunk starts at token 320
        start += CHUNK_SIZE - CHUNK_OVERLAP

print(f"    -> Created {len(chunks)} chunks")


# ─────────────────────────────────────────────────────────────────────────
# STEP 3 — Embed each chunk
# ─────────────────────────────────────────────────────────────────────────
# WHY embed?
#   An embedding converts text into a list of numbers (a "vector").
#   Similar texts produce similar vectors (close in vector space).
#   This is how Pinecone finds relevant chunks for a question —
#   it finds vectors closest to the question's vector.
#
# We send ALL chunk texts in a single API call (batch) — faster and cheaper.

print(f"\n[3/4] Embedding {len(chunks)} chunks with OpenAI ({EMBED_MODEL})")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Send all chunk texts at once in one API call
embedding_response = openai_client.embeddings.create(
    model=EMBED_MODEL,
    input=[chunk["text"] for chunk in chunks],   # list of strings
)

# Attach the embedding vector back to each chunk dict
for i, embedding_object in enumerate(embedding_response.data):
    chunks[i]["embedding"] = embedding_object.embedding   # list of 1536 floats

print(f"    -> Each vector has {len(chunks[0]['embedding'])} dimensions")


# ─────────────────────────────────────────────────────────────────────────
# STEP 4 — Upload to Pinecone
# ─────────────────────────────────────────────────────────────────────────
# WHY Pinecone?
#   Pinecone is a vector database. You give it millions of vectors and
#   it can find the top-K most similar ones in milliseconds.
#   Regular databases (SQL, Mongo) can't do this efficiently.
#
# Each record we upload has 3 parts:
#   "id"       -> a unique string so we can identify this chunk
#   "values"   -> the 1536-dim embedding vector
#   "metadata" -> the original text + page number stored alongside the vector
#                 (Pinecone stores vectors, not text — metadata is our escape hatch)

print(f"\n[4/4] Uploading to Pinecone (index: '{INDEX_NAME}')")

pinecone_client = Pinecone(api_key=PINECONE_API_KEY)

# --- Create the index if it doesn't exist yet ---
existing_index_names = [idx.name for idx in pinecone_client.list_indexes()]

if INDEX_NAME not in existing_index_names:
    print(f"    -> Index '{INDEX_NAME}' not found. Creating it now...")
    pinecone_client.create_index(
        name=INDEX_NAME,
        dimension=EMBED_DIMS,       # must match the embedding model output size
        metric="cosine",            # cosine similarity is standard for text
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1",     # free tier available here
        ),
    )
    # Wait until Pinecone says the index is ready
    print("    -> Waiting for index to become ready ", end="", flush=True)
    while not pinecone_client.describe_index(INDEX_NAME).status["ready"]:
        print(".", end="", flush=True)
        time.sleep(3)
    print(" ready!")
else:
    print(f"    -> Index '{INDEX_NAME}' already exists. Skipping creation.")

# Connect to the index
index = pinecone_client.Index(INDEX_NAME)

# --- Build the list of records to upload ---
records = []
for chunk in chunks:
    records.append({
        "id":     chunk["id"],
        "values": chunk["embedding"],
        "metadata": {
            "text":       chunk["text"],       # the actual text (returned at query time)
            "page_num":   chunk["page_num"],   # useful for citing sources
            "num_tokens": chunk["num_tokens"], # for debugging
        },
    })

# --- Upload in batches (avoids hitting API size limits) ---
total_uploaded = 0
for batch_start in range(0, len(records), BATCH_SIZE):
    batch = records[batch_start : batch_start + BATCH_SIZE]
    index.upsert(vectors=batch)
    total_uploaded += len(batch)
    print(f"    -> Uploaded {total_uploaded}/{len(records)} vectors...")

# ─────────────────────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 55)
print("  INGESTION COMPLETE")
print("=" * 55)
print(f"  PDF            : {PDF_FILE}")
print(f"  Pages read     : {len(all_text_chunks_raw)}")
print(f"  Chunks created : {len(chunks)}")
print(f"  Vectors stored : {total_uploaded}")
print(f"  Pinecone index : {INDEX_NAME}")
print(f"  Embedding model: {EMBED_MODEL} ({EMBED_DIMS} dims)")
print("=" * 55)
print("\n  Next step: run  python step3_retrieve.py\n")
