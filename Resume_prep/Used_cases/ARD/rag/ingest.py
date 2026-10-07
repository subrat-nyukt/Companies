"""
ARD — rag/ingest.py
====================
One-shot ingestion script: reads a text corpus from `data/` directory,
chunks it, builds dense (OpenAI) + sparse (TF-IDF) vectors, and upserts to Pinecone.

Run once to build the research knowledge base:
    python -m rag.ingest

The corpus is mock market research notes / press releases / central bank speeches.
In production this would connect to Bloomberg, Reuters, SEC EDGAR APIs.
"""

import os
import re
import json
import math
import uuid
import hashlib
from pathlib import Path
from collections import Counter

from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

from core.config import settings

# ── Configuration ──────────────────────────────────────────────────────────────
CHUNK_SIZE = 600      # characters per chunk
CHUNK_OVERLAP = 100   # overlap between adjacent chunks
BATCH_SIZE = 50       # Pinecone upsert batch size
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SPARSE_CONFIG_PATH = Path(__file__).resolve().parent / "sparse_config.json"


# ── Step 1: Load Corpus ────────────────────────────────────────────────────────

def load_corpus(data_dir: Path) -> list[dict]:
    """
    Loads all .txt and .md files from the data directory.
    Each file becomes one document entry.
    """
    docs = []
    if not data_dir.exists():
        print(f"[Ingest] Data directory not found: {data_dir}")
        print("[Ingest] Creating sample data for demonstration...")
        data_dir.mkdir(parents=True, exist_ok=True)
        _create_sample_data(data_dir)

    for fp in sorted(data_dir.iterdir()):
        if fp.suffix in {".txt", ".md"}:
            text = fp.read_text(encoding="utf-8").strip()
            if text:
                docs.append({"source": fp.name, "text": text})
                print(f"  [Ingest] Loaded: {fp.name} ({len(text)} chars)")
    return docs


def _create_sample_data(data_dir: Path):
    """Creates sample research corpus files for demonstration."""
    samples = {
        "ecb_speech_march_2025.txt": """European Central Bank Press Conference — March 2025
President Christine Lagarde addressed reporters following the Governing Council meeting.
The ECB held its key interest rates steady, with the deposit facility rate remaining at 3.50%.
Lagarde stated: 'We are data dependent and stand ready to adjust all instruments as appropriate.'
Inflation in the euro area fell to 2.3% in February, approaching the 2% target.
The Council noted that wage growth remains elevated but is showing signs of moderation.
Market participants interpreted the statement as mildly dovish, with rate cut expectations
for June increasing to 78% probability following the press conference.
The euro fell 0.4% against the dollar on the announcement.
10-year Bund yields declined 6 basis points to 2.41%.""",

        "fed_minutes_jan_2025.txt": """Federal Reserve FOMC Meeting Minutes — January 2025
The Federal Open Market Committee voted unanimously to hold the federal funds rate at 5.25–5.50%.
Committee members noted that inflation progress has stalled, with core PCE at 2.9%.
Several participants expressed concern about premature rate cuts reigniting price pressures.
Chair Powell emphasized: 'We need greater confidence that inflation is sustainably moving to 2%.'
The dot plot showed median expectation of three 25-basis-point cuts in 2025.
Markets sold off following the release, with 2-year Treasury yields rising 12bps.
The S&P 500 declined 1.2% on the session. Dollar index strengthened 0.6%.""",

        "ma_filing_semiconductor_2025.txt": """EC Phase II Investigation: NovaTech Semiconductor Acquisition of MicroLogic
The European Commission has opened a Phase II investigation into the proposed $28 billion
acquisition of MicroLogic Corp by NovaTech Semiconductor (NVTK).
The EC cited concerns about reduced competition in the advanced chip design tools market,
where combined entity would hold approximately 67% market share in the EEA.
NovaTech offered behavioral remedies including open licensing of key IP for 10 years.
The EC has until September 2025 to issue its final decision.
Legal experts estimate 40-60% probability of conditional approval requiring structural remedies.
The deal includes a $1.4 billion break-up fee payable by NovaTech if regulatory clearance fails.
MicroLogic shares trade at an 8.5% discount to the deal price, implying market-assessed
regulatory risk premium. CFIUS review is ongoing in parallel.""",

        "special_situations_holdco_2025.txt": """European Holding Company Discount: MediaCorp Holdings vs. Sum-of-Parts
MediaCorp Holdings (MCH LN) currently trades at a 23% discount to its net asset value (NAV),
calculated as the market cap of its three listed subsidiaries: StreamTV (55% stake),
RadioNet Europe (72% stake), and Digital Outdoor (41% stake).
The discount has widened from a 12-month average of 14% following the departure of the
CEO in Q4 2024 and uncertainty around a rumored strategic review.
Activist investor Clearwater Capital disclosed a 5.1% stake last week, demanding the board
explore a full separation of the three business units.
Historical precedent: similar European media holdco discounts closed within 18 months
following activist entry in 73% of comparable situations (2015-2024).
Catalyst: Board is scheduled to present its strategic review findings on 15 July 2025.
Implied upside to NAV: 30% if discount closes to historical average of 8%.""",

        "index_rebalancing_msci_2025.txt": """MSCI Emerging Markets Index Rebalancing — February 2025 Semi-Annual Review
MSCI announced additions and deletions to the MSCI Emerging Markets Index effective
close of business 28 February 2025.
Key additions: Adani Ports (India, estimated $2.1B inflow), Kaspi.kz (Kazakhstan, $890M inflow).
Key deletions: Petrobras preferred shares (Brazil, estimated $1.4B outflow).
The rebalancing is expected to trigger significant passive fund flows in the final 30 minutes
of trading on the effective date. Active managers typically position 3-5 days ahead.
Historical pattern shows additions outperform deletions by an average of 4.2% in the
20-day window surrounding the effective date. High short interest in deletions creates
potential for short squeeze dynamics as passive funds buy additions simultaneously.""",
    }
    for filename, content in samples.items():
        (data_dir / filename).write_text(content, encoding="utf-8")
        print(f"  [Ingest] Created sample: {filename}")


# ── Step 2: Chunking ───────────────────────────────────────────────────────────

def chunk_text(text: str, source: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Sliding window chunker with overlap. Each chunk gets a deterministic SHA-256 ID."""
    chunks = []
    start = 0
    chunk_index = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()
        if len(chunk_text) > 50:   # Skip tiny trailing fragments
            chunk_id = hashlib.sha256(f"{source}_{chunk_index}_{chunk_text[:30]}".encode()).hexdigest()[:16]
            chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "metadata": {"source": source, "chunk_index": chunk_index},
            })
            chunk_index += 1
        start += chunk_size - overlap
    return chunks


# ── Step 3: Dense Embeddings ───────────────────────────────────────────────────

def embed_chunks(chunks: list[dict], openai_client: OpenAI) -> list[dict]:
    """Generate dense embeddings using OpenAI text-embedding-3-small."""
    texts = [c["text"] for c in chunks]
    response = openai_client.embeddings.create(model=settings.embed_model, input=texts)
    for i, emb_obj in enumerate(response.data):
        chunks[i]["embedding"] = emb_obj.embedding
    print(f"  [Ingest] Generated {len(chunks)} dense embeddings (dim={len(chunks[0]['embedding'])})")
    return chunks


# ── Step 4: Sparse TF-IDF Vectors ─────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    return re.findall(r'\w+', text.lower())

def _token_id(token: str) -> int:
    return int(hashlib.md5(token.encode()).hexdigest()[:8], 16)

def build_sparse_vectors(chunks: list[dict]) -> tuple[list[dict], dict]:
    """
    Builds TF-IDF sparse vectors for all chunks.
    Returns updated chunks and the IDF config (needed at query time for matching).
    """
    tokenized = [_tokenize(c["text"]) for c in chunks]
    num_docs = len(chunks)

    # Document Frequency
    df = Counter()
    for tokens in tokenized:
        df.update(set(tokens))

    # Inverse Document Frequency (smoothed)
    idf = {t: math.log((1 + num_docs) / (1 + df[t])) + 1 for t in df}

    # TF-IDF + L2 normalization per chunk
    for i, chunk in enumerate(chunks):
        tf = Counter(tokenized[i])
        raw_vector = {t: tf[t] * idf.get(t, 0.0) for t in tf}
        norm = math.sqrt(sum(v**2 for v in raw_vector.values()))
        if norm > 0:
            raw_vector = {t: v / norm for t, v in raw_vector.items()}

        # Convert to sorted Pinecone sparse format
        pairs = sorted((_token_id(t), v) for t, v in raw_vector.items() if v > 0)
        indices, values = zip(*pairs) if pairs else ([], [])
        chunk["sparse_values"] = {"indices": list(indices), "values": list(values)}

    sparse_config = {"num_docs": num_docs, "idf": idf}
    print(f"  [Ingest] Generated sparse TF-IDF vectors for {num_docs} chunks")
    return chunks, sparse_config


# ── Step 5: Upsert to Pinecone ─────────────────────────────────────────────────

def upsert_to_pinecone(chunks: list[dict], pc: Pinecone):
    """Create index if needed, then upsert all chunks in batches."""
    index_name = settings.pinecone_index_name
    existing = [i.name for i in pc.list_indexes()]

    if index_name not in existing:
        print(f"  [Ingest] Creating Pinecone index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=1536,   # text-embedding-3-small dimension
            metric="dotproduct",  # Required for hybrid (sparse+dense) search
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    index = pc.Index(index_name)
    payload = [
        {
            "id": c["id"],
            "values": c["embedding"],
            "sparse_values": c["sparse_values"],
            "metadata": {**c["metadata"], "text": c["text"]},
        }
        for c in chunks
    ]

    total_batches = math.ceil(len(payload) / BATCH_SIZE)
    for i in range(0, len(payload), BATCH_SIZE):
        batch = payload[i: i + BATCH_SIZE]
        index.upsert(vectors=batch)
        print(f"  [Ingest] Upserted batch {i // BATCH_SIZE + 1}/{total_batches} ({len(batch)} vectors)")


# ── Main ───────────────────────────────────────────────────────────────────────

def run_ingestion():
    print("\n" + "=" * 60)
    print("ARD RESEARCH DATABASE INGESTION")
    print("=" * 60)

    openai_client = OpenAI(api_key=settings.openai_api_key)
    pc = Pinecone(api_key=settings.pinecone_api_key)

    # 1. Load
    print("\n[Step 1] Loading corpus...")
    docs = load_corpus(DATA_DIR)
    if not docs:
        print("[Ingest] No documents found. Exiting.")
        return

    # 2. Chunk
    print("\n[Step 2] Chunking documents...")
    all_chunks = []
    for doc in docs:
        chunks = chunk_text(doc["text"], doc["source"])
        all_chunks.extend(chunks)
        print(f"  [Ingest] {doc['source']} → {len(chunks)} chunks")

    # 3. Dense Embeddings
    print(f"\n[Step 3] Generating dense embeddings for {len(all_chunks)} chunks...")
    all_chunks = embed_chunks(all_chunks, openai_client)

    # 4. Sparse Vectors
    print("\n[Step 4] Building sparse TF-IDF vectors...")
    all_chunks, sparse_config = build_sparse_vectors(all_chunks)

    # Save sparse config for retriever
    with open(SPARSE_CONFIG_PATH, "w") as f:
        json.dump(sparse_config, f, indent=2)
    print(f"  [Ingest] Saved sparse config → {SPARSE_CONFIG_PATH}")

    # 5. Upload
    print("\n[Step 5] Upserting to Pinecone...")
    upsert_to_pinecone(all_chunks, pc)

    print("\n" + "=" * 60)
    print(f"✅ INGESTION COMPLETE — {len(all_chunks)} vectors indexed in '{settings.pinecone_index_name}'")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_ingestion()
