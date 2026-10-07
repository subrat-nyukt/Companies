"""
Production Incremental Ingestion & Chunk-Level Deduplication Pipeline
=======================================================================
Solves the problem: When a 10-page PDF changes ONLY on Page 10, how do we
avoid re-chunking and re-embedding Pages 1 to 9?

Key Mechanics:
1. Chunk-Level Content Hashing: Hash = SHA256(page_number + chunk_text)
2. Incremental Comparison: Queries Vector DB for existing chunk_hashes.
3. Selective Embedding: ONLY calls OpenAI Embedding API for new/modified chunks!
"""

import hashlib
import os
from typing import List, Dict, Tuple
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma


def compute_chunk_hash(page_number: int, chunk_text: str) -> str:
    """
    Computes a deterministic content hash for a specific chunk.
    If the text on Page 1 doesn't change, its hash remains 100% identical.
    """
    raw_key = f"page_{page_number}:{chunk_text.strip()}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class IncrementalRAGIngestionPipeline:
    def __init__(self, db_dir: str = "./incremental_chroma_db"):
        self.db_dir = db_dir
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        
        # Persistent Vector DB
        self.vectorstore = Chroma(
            collection_name="incremental_docs",
            embedding_function=self.embeddings,
            persist_directory=db_dir
        )

    def ingest_document_incrementally(self, document_id: str, pages_dict: Dict[int, str]):
        """
        Ingests a document page-by-page, skipping un-changed pages automatically.
        
        :param document_id: Unique string identifier for the document (e.g. 'doc_policy_2026.pdf')
        :param pages_dict: Dictionary mapping {page_number: page_text_content}
        """
        print(f"\n🔄 Processing Incremental Ingestion for Document: '{document_id}'...")

        # 1. Get existing chunk hashes stored in Vector DB for this document
        existing_records = self.vectorstore.get(
            where={"doc_id": document_id},
            include=["metadatas"]
        )
        existing_chunk_hashes = set()
        if existing_records and existing_records.get("metadatas"):
            for meta in existing_records["metadatas"]:
                if "chunk_hash" in meta:
                    existing_chunk_hashes.add(meta["chunk_hash"])

        print(f"📦 Existing Chunk Hashes found in Vector DB: {len(existing_chunk_hashes)}")

        new_chunks_to_embed: List[Document] = []
        new_chunk_ids: List[str] = []
        skipped_count = 0

        # 2. Iterate through pages and split into chunks
        for page_num, page_text in pages_dict.items():
            raw_chunks = self.text_splitter.split_text(page_text)
            
            for chunk_idx, c_text in enumerate(raw_chunks):
                # Calculate unique SHA-256 chunk hash
                c_hash = compute_chunk_hash(page_num, c_text)

                if c_hash in existing_chunk_hashes:
                    # 🟢 Page 1-9 match! Skip embedding!
                    skipped_count += 1
                else:
                    # 🔴 Page 10 is modified/new! Must embed!
                    doc = Document(
                        page_content=c_text,
                        metadata={
                            "doc_id": document_id,
                            "page": page_num,
                            "chunk_hash": c_hash,
                            "chunk_idx": chunk_idx
                        }
                    )
                    # Use chunk_hash as the unique Vector DB ID
                    new_chunks_to_embed.append(doc)
                    new_chunk_ids.append(c_hash)

        # 3. Embed ONLY the new/modified chunks (Page 10)
        if new_chunks_to_embed:
            print(f"🚀 Calling Embedding API for {len(new_chunks_to_embed)} NEW/MODIFIED chunks...")
            self.vectorstore.add_documents(documents=new_chunks_to_embed, ids=new_chunk_ids)
            print(f"✅ Successfully embedded {len(new_chunks_to_embed)} chunks!")
        else:
            print("✨ No changes detected in document! 0 API calls made.")

        print(f"⚡ SKIPPED (Deduplicated): {skipped_count} unchanged chunks (Saved Embedding API costs!).")


# =========================================================================
# Demonstration / Simulation Script
# =========================================================================
if __name__ == "__main__":
    pipeline = IncrementalRAGIngestionPipeline()

    # VERSION 1: 10 Pages Document
    v1_pages = {i: f"This is the static content for Page {i}." for i in range(1, 11)}
    print("--- STEP 1: Ingesting Document Version 1 (10 Pages) ---")
    pipeline.ingest_document_incrementally("policy_doc.pdf", v1_pages)

    # VERSION 2: ONLY Page 10 is changed! Pages 1 to 9 are 100% identical
    v2_pages = v1_pages.copy()
    v2_pages[10] = "MODIFIED CONTENT: Page 10 has updated legal penalties and terms."

    print("\n--- STEP 2: Ingesting Document Version 2 (Page 10 Modified) ---")
    pipeline.ingest_document_incrementally("policy_doc.pdf", v2_pages)
