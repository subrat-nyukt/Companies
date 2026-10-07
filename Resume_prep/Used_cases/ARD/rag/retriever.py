"""
ARD — rag/retriever.py
=======================
Hybrid dense+sparse retrieval with Reciprocal Rank Fusion (RRF).

Algorithm:
1. Generate dense query vector (OpenAI embeddings)
2. Generate sparse query vector (TF-IDF, same IDF weights as ingest)
3. Query Pinecone with both vectors simultaneously (hybrid search)
4. Apply RRF to merge and re-rank results
5. Return top-k deduplicated chunks

This mirrors the production-grade RAG described in the use case document,
combining semantic understanding (dense) with exact keyword matching (sparse).
"""

import re
import json
import math
import hashlib
from pathlib import Path

from openai import OpenAI
from pinecone import Pinecone

from core.config import settings

SPARSE_CONFIG_PATH = Path(__file__).resolve().parent / "sparse_config.json"
RRF_K = 60    # Standard RRF smoothing constant (prevents rank-1 overweight)


# ── Sparse Vector Builder (query time) ────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    return re.findall(r'\w+', text.lower())

def _token_id(token: str) -> int:
    return int(hashlib.md5(token.encode()).hexdigest()[:8], 16)

def build_query_sparse_vector(query: str, idf: dict) -> dict:
    """
    Build a normalized TF-IDF sparse vector for the query using the same
    IDF weights computed during ingestion. This ensures score comparability.
    """
    tokens = _tokenize(query)
    tf = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1

    raw = {t: tf[t] * idf.get(t, 0.0) for t in tf}
    norm = math.sqrt(sum(v ** 2 for v in raw.values()))
    if norm > 0:
        raw = {t: v / norm for t, v in raw.items()}

    pairs = sorted((_token_id(t), v) for t, v in raw.items() if v > 0)
    if not pairs:
        return {"indices": [], "values": []}
    indices, values = zip(*pairs)
    return {"indices": list(indices), "values": list(values)}


# ── RRF Fusion ─────────────────────────────────────────────────────────────────

def reciprocal_rank_fusion(
    dense_results: list[dict],
    sparse_results: list[dict],
    k: int = RRF_K,
) -> list[dict]:
    """
    Merge dense and sparse results using Reciprocal Rank Fusion.
    
    RRF Formula: Score(d) = Σ_m 1 / (k + rank_m(d))
    
    Documents appearing high in both result lists get the highest final scores.
    The k constant (60) prevents rank-1 documents from dominating the final score.
    """
    scores: dict[str, float] = {}
    docs_by_id: dict[str, dict] = {}

    for rank, match in enumerate(dense_results):
        doc_id = match["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        docs_by_id[doc_id] = match

    for rank, match in enumerate(sparse_results):
        doc_id = match["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        docs_by_id[doc_id] = match

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [docs_by_id[doc_id] for doc_id, _ in ranked]


# ── Main Retrieval Function ────────────────────────────────────────────────────

def retrieve(query: str, top_k: int = None) -> list[dict]:
    """
    Full hybrid retrieval pipeline.
    
    Args:
        query: The natural language query or expanded search string.
        top_k: Number of final chunks to return (defaults to settings.top_k_context).
    
    Returns:
        List of chunk dicts with keys: id, text, source, score (RRF rank score).
    """
    if top_k is None:
        top_k = settings.top_k_context

    fetch_k = settings.top_k_retrieval   # Fetch more before RRF re-ranking

    openai_client = OpenAI(api_key=settings.openai_api_key)
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index = pc.Index(settings.pinecone_index_name)

    # ── 1. Dense Query Vector ──────────────────────────────────────────────────
    dense_response = openai_client.embeddings.create(
        model=settings.embed_model, input=[query]
    )
    dense_vector = dense_response.data[0].embedding

    # ── 2. Sparse Query Vector (TF-IDF) ───────────────────────────────────────
    sparse_vector = {"indices": [], "values": []}   # Graceful fallback
    if SPARSE_CONFIG_PATH.exists():
        with open(SPARSE_CONFIG_PATH) as f:
            sparse_config = json.load(f)
        idf = sparse_config.get("idf", {})
        sparse_vector = build_query_sparse_vector(query, idf)
    else:
        print("  [Retriever] WARNING: sparse_config.json not found. Run rag/ingest.py first.")

    # ── 3. Dual Pinecone Queries ───────────────────────────────────────────────
    # Dense-only results
    dense_results = index.query(
        vector=dense_vector,
        top_k=fetch_k,
        include_metadata=True,
    ).matches

    # Sparse-only results (if sparse vector is available)
    sparse_results = []
    if sparse_vector["indices"]:
        sparse_results = index.query(
            vector=[0.0] * 1536,          # Zero dense vector → purely sparse query
            sparse_vector=sparse_vector,
            top_k=fetch_k,
            include_metadata=True,
        ).matches

    # ── 4. RRF Fusion ─────────────────────────────────────────────────────────
    merged = reciprocal_rank_fusion(
        [{"id": m.id, "metadata": m.metadata, "score": m.score} for m in dense_results],
        [{"id": m.id, "metadata": m.metadata, "score": m.score} for m in sparse_results],
    )

    # ── 5. Format Output ──────────────────────────────────────────────────────
    final_chunks = []
    for match in merged[:top_k]:
        meta = match.get("metadata", {})
        final_chunks.append({
            "id": match["id"],
            "text": meta.get("text", ""),
            "source": meta.get("source", "unknown"),
            "chunk_index": meta.get("chunk_index", 0),
        })

    return final_chunks
