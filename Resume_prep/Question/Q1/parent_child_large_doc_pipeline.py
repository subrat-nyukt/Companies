"""
Production-Grade Parent-Child Semantic Chunking Pipeline for Large Documents
=============================================================================
Handles 100+ page PDFs/Documents without running out of RAM or hitting API limits.

Key Production Design Features:
1. Memory-efficient streaming/batching (Page-by-Page PDF parsing).
2. Persistent K-V DocStore (SQLite/Disk) for Parent Chunks (No RAM crashes).
3. Batched Vector Embedding into Vector DB (Avoids OpenAI rate limits).
4. Parent-Child retrieval mapping.
"""

import os
import uuid
import time
from typing import List, Dict, Generator
import pypdf
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.storage import LocalFileStore, create_kv_docstore


class LargeDocumentParentChildPipeline:
    def __init__(
        self,
        parent_chunk_size: int = 1200,
        parent_overlap: int = 150,
        child_chunk_size: int = 200,
        child_overlap: int = 30,
        db_dir: str = "./parent_child_db",
    ):
        """
        Initialize the Parent-Child Pipeline for large scale document ingestion.
        """
        self.db_dir = db_dir
        os.makedirs(db_dir, exist_ok=True)
        
        # 1. Text Splitters
        self.parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_chunk_size,
            chunk_overlap=parent_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_chunk_size,
            chunk_overlap=child_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )

        # 2. Embedding Model
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        # 3. Persistent Storage (Disk-based Store for Parent Chunks to save RAM)
        parent_store_path = os.path.join(self.db_dir, "parent_chunks_store")
        fs = LocalFileStore(parent_store_path)
        self.docstore = create_kv_docstore(fs)

        # 4. Persistent Vector DB for Child Chunk Vectors
        vector_db_path = os.path.join(self.db_dir, "child_vectors_chroma")
        self.vectorstore = Chroma(
            collection_name="child_chunks",
            embedding_function=self.embeddings,
            persist_directory=vector_db_path
        )

    def stream_pdf_pages(self, pdf_path: str, pages_per_batch: int = 10) -> Generator[List[Document], None, None]:
        """
        Memory-Efficient Generator: Streams PDF pages in batches to prevent RAM exhaustion.
        """
        reader = pypdf.PdfReader(pdf_path)
        total_pages = len(reader.pages)
        print(f"📖 Total Pages in Document: {total_pages}")

        batch = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                doc = Document(
                    page_content=text,
                    metadata={"source": os.path.basename(pdf_path), "page": i + 1}
                )
                batch.append(doc)

            if len(batch) >= pages_per_batch or i == total_pages - 1:
                yield batch
                batch = []

    def ingest_large_pdf(self, pdf_path: str, embedding_batch_size: int = 100):
        """
        Executes Parent-Child ingestion for large PDFs in memory-safe batches.
        """
        print(f"\n🚀 Starting Ingestion for Large Document: {pdf_path}")
        start_time = time.time()
        
        total_parents_created = 0
        total_children_created = 0

        # Stream pages in batches of 20 to keep RAM low
        for page_batch in self.stream_pdf_pages(pdf_path, pages_per_batch=20):
            # Combine pages into large text blocks to form Parent Chunks
            combined_text = "\n\n".join([d.page_content for d in page_batch])
            base_metadata = page_batch[0].metadata

            # A. Generate Parent Chunks
            raw_parents = self.parent_splitter.split_text(combined_text)
            
            parent_docs_to_save = []
            child_docs_to_embed = []

            for p_text in raw_parents:
                parent_id = str(uuid.uuid4())
                parent_doc = Document(
                    page_content=p_text,
                    metadata={**base_metadata, "parent_id": parent_id}
                )
                parent_docs_to_save.append((parent_id, parent_doc))
                total_parents_created += 1

                # B. Generate Child Chunks from THIS Parent Chunk
                raw_children = self.child_splitter.split_text(p_text)
                for c_text in raw_children:
                    child_doc = Document(
                        page_content=c_text,
                        metadata={
                            **base_metadata,
                            "parent_id": parent_id  # Critical: Link Child to Parent ID
                        }
                    )
                    child_docs_to_embed.append(child_doc)
                    total_children_created += 1

            # C. Save Parent Chunks to Disk K-V Store (Low RAM)
            self.docstore.mset(parent_docs_to_save)

            # D. Batch Insert Child Vectors into Vector DB (Prevents API Timeouts)
            for i in range(0, len(child_docs_to_embed), embedding_batch_size):
                chunk_batch = child_docs_to_embed[i : i + embedding_batch_size]
                self.vectorstore.add_documents(chunk_batch)

        elapsed = time.time() - start_time
        print(f"✅ Ingestion Complete in {elapsed:.2f} seconds!")
        print(f"   - Total Parent Chunks (1200t): {total_parents_created}")
        print(f"   - Total Child Chunks (200t):  {total_children_created}")

    def search_parent_context(self, query: str, top_k_children: int = 3) -> List[Document]:
        """
        Executes Parent-Child Retrieval:
        1. Searches small Child Chunk vectors.
        2. Fetches matching large Parent Chunks from disk.
        3. Deduplicates parent chunks so LLM receives clean context.
        """
        print(f"\n🔍 Searching for: '{query}'")
        
        # Step 1: Perform Vector Search on Child Chunks
        child_results = self.vectorstore.similarity_search(query, k=top_k_children)
        
        # Step 2: Extract Parent IDs and deduplicate
        parent_ids = []
        for child in child_results:
            p_id = child.metadata.get("parent_id")
            if p_id and p_id not in parent_ids:
                parent_ids.append(p_id)

        # Step 3: Fetch Full Parent Chunks from Disk Store
        parent_docs = self.docstore.mget(parent_ids)
        
        # Filter out any missing values
        final_parents = [doc for doc in parent_docs if doc is not None]
        return final_parents


# ==========================================
# Example Execution Demo
# ==========================================
if __name__ == "__main__":
    # Ensure OPENAI_API_KEY is set in your environment
    # os.environ["OPENAI_API_KEY"] = "your-openai-key"

    pipeline = LargeDocumentParentChildPipeline()

    # To run on your large document:
    # pipeline.ingest_large_pdf("sample_large_compliance_book.pdf")
    
    # To query parent context:
    # results = pipeline.search_parent_context("What are the default penalties under Section 4?")
    # for i, doc in enumerate(results):
    #     print(f"\n--- PARENT CONTEXT {i+1} (Page {doc.metadata.get('page')}) ---")
    #     print(doc.page_content[:300] + "...")
    pass
