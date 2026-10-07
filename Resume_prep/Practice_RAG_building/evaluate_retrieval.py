import os
import math
import re
from collections import Counter
from dotenv import load_dotenv
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
from rich.console import Console
from rich.table import Table

# Initialize Console for beautiful output
console = Console()

# ──────────────────────────────────────────────────────────────────────
# 1. CONFIGURATION & CLIENTS
# ──────────────────────────────────────────────────────────────────────
load_dotenv()
open_api_key = os.getenv("OPENAI_API_KEY")
pdf_file = "kyc_policy.pdf"
embed_model = "text-embedding-3-small"

openai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=open_api_key
)

# ──────────────────────────────────────────────────────────────────────
# 2. DOCUMENT PARSING & CHUNKING
# ──────────────────────────────────────────────────────────────────────
def get_pdf_chunks(filepath: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """Reads PDF and splits it into chunks using RecursiveCharacterTextSplitter."""
    extracted_text = []
    try:
        with open(filepath, "rb") as f:
            reader = PdfReader(f)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    extracted_text.append({"page_number": i + 1, "text": text.strip()})
    except Exception as e:
        console.print(f"[bold red]Error reading PDF:[/bold red] {e}")
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    all_chunks = []
    global_chunk_count = 0
    for entry in extracted_text:
        page_chunks = text_splitter.split_text(entry["text"])
        for i, chunk in enumerate(page_chunks):
            all_chunks.append({
                "id": f"chunk_{global_chunk_count}",
                "text": chunk,
                "page_number": entry["page_number"]
            })
            global_chunk_count += 1
    return all_chunks

# ──────────────────────────────────────────────────────────────────────
# 3. SPARSE INDEXING (TF-IDF IMPLEMENTATION)
# ──────────────────────────────────────────────────────────────────────
def tokenize(text: str) -> list:
    """Tokenizes text into lowercase alphanumeric words."""
    return re.findall(r'\w+', text.lower())

class SparseTfidfIndex:
    """A lightweight, zero-dependency Sparse TF-IDF Vector Index."""
    def __init__(self, corpus_chunks: list):
        self.corpus = corpus_chunks
        self.num_docs = len(corpus_chunks)
        self.doc_tokenized = [tokenize(c["text"]) for c in corpus_chunks]
        
        # Calculate Document Frequency (DF)
        self.doc_freqs = Counter()
        for tokens in self.doc_tokenized:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] += 1
                
        # Calculate Inverse Document Frequency (IDF) with smoothing
        self.idfs = {}
        for token, df in self.doc_freqs.items():
            self.idfs[token] = math.log((1 + self.num_docs) / (1 + df)) + 1
            
        # Build document TF-IDF vectors (represented as sparse dictionaries)
        self.doc_vectors = []
        for tokens in self.doc_tokenized:
            tf = Counter(tokens)
            vector = {}
            for token, count in tf.items():
                vector[token] = count * self.idfs.get(token, 0.0)
            
            # L2 normalization to unit length
            norm = math.sqrt(sum(v**2 for v in vector.values()))
            if norm > 0:
                for token in vector:
                    vector[token] /= norm
            self.doc_vectors.append(vector)
            
    def get_query_vector(self, query: str) -> dict:
        """Computes sparse query vector."""
        tokens = tokenize(query)
        tf = Counter(tokens)
        vector = {}
        for token, count in tf.items():
            vector[token] = count * self.idfs.get(token, 0.0)
        
        # L2 normalization
        norm = math.sqrt(sum(v**2 for v in vector.values()))
        if norm > 0:
            for token in vector:
                vector[token] /= norm
        return vector
        
    def compute_similarity(self, query_vec: dict, doc_idx: int) -> float:
        """Computes cosine similarity between query and doc sparse vectors."""
        doc_vec = self.doc_vectors[doc_idx]
        score = 0.0
        for token, val in query_vec.items():
            if token in doc_vec:
                score += val * doc_vec[token]
        return score

# ──────────────────────────────────────────────────────────────────────
# 4. DENSE EMBEDDINGS (VIA OPENAI)
# ──────────────────────────────────────────────────────────────────────
def get_dense_embeddings(texts: list) -> list:
    """Fetches dense embeddings in batches."""
    embeddings = []
    batch_size = 50
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = openai_client.embeddings.create(
            model=embed_model,
            input=batch
        )
        for obj in response.data:
            embeddings.append(obj.embedding)
    return embeddings

# ──────────────────────────────────────────────────────────────────────
# 5. RETRIEVAL AND HYBRID COMBINATION
# ──────────────────────────────────────────────────────────────────────
def retrieve(
    query: str,
    chunks: list,
    dense_embeddings: list,
    sparse_index: SparseTfidfIndex,
    alpha: float = 0.5,
    top_k: int = 5
) -> list:
    """
    Performs hybrid retrieval.
    alpha = 1.0 -> Pure Dense (Cosine Similarity)
    alpha = 0.0 -> Pure Sparse (TF-IDF Cosine Similarity)
    0.0 < alpha < 1.0 -> Weighted Hybrid Search
    """
    # Get query vectors
    q_dense = get_dense_embeddings([query])[0]
    q_sparse = sparse_index.get_query_vector(query)

    scores = []
    for idx, chunk in enumerate(chunks):
        # Dense Cosine Similarity (Dot product because embeddings are unit vectors)
        dense_score = sum(x * y for x, y in zip(q_dense, dense_embeddings[idx]))
        
        # Sparse Similarity
        sparse_score = sparse_index.compute_similarity(q_sparse, idx)
        
        # Hybrid combination
        hybrid_score = (alpha * dense_score) + ((1 - alpha) * sparse_score)
        
        scores.append({
            "id": chunk["id"],
            "text": chunk["text"],
            "page_number": chunk["page_number"],
            "score": hybrid_score
        })
        
    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[:top_k]

# ──────────────────────────────────────────────────────────────────────
# 6. EVALUATION METRICS (MRR & MAP)
# ──────────────────────────────────────────────────────────────────────
def calculate_reciprocal_rank(retrieved_ids: list, ground_truth_ids: set) -> float:
    """Computes Reciprocal Rank (RR) for a single query."""
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in ground_truth_ids:
            return 1.0 / rank
    return 0.0

def calculate_average_precision(retrieved_ids: list, ground_truth_ids: set) -> float:
    """Computes Average Precision (AP) for a single query."""
    if not ground_truth_ids:
        return 0.0
    
    hits = 0
    sum_precisions = 0.0
    
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in ground_truth_ids:
            hits += 1
            precision_at_k = hits / rank
            sum_precisions += precision_at_k
            
    return sum_precisions / len(ground_truth_ids)

# ──────────────────────────────────────────────────────────────────────
# 7. EXPERIMENTAL RUN
# ──────────────────────────────────────────────────────────────────────
def run_evaluation_suite():
    console.print("[bold cyan]=== Initializing Retrieval Evaluation Suite ===[/bold cyan]")
    
    # Load and chunk PDF
    console.print(f"Reading [green]{pdf_file}[/green]...")
    chunks = get_pdf_chunks(pdf_file, chunk_size=500, overlap=50)
    console.print(f"Generated [yellow]{len(chunks)}[/yellow] chunks.")
    
    # Build Indices
    console.print("Generating Dense Embeddings via OpenAI/OpenRouter...")
    dense_embeddings = get_dense_embeddings([c["text"] for c in chunks])
    
    console.print("Building Local Sparse (TF-IDF) Index...")
    sparse_index = SparseTfidfIndex(chunks)
    
    # Define Ground Truth dynamically by identifying chunks containing key topic phrases.
    # This prevents indexing misalignment if chunk sizes change.
    test_suite = [
        {
            "query": "What is the difference between SDD and EDD?",
            "keywords": ["sdd", "edd", "due diligence"]
        },
        {
            "query": "Who qualifies as a PEP and what extra steps are required?",
            "keywords": ["pep", "politically exposed person"]
        },
        {
            "query": "What are SAR filing thresholds in the US and UK?",
            "keywords": ["sar", "threshold", "filing"]
        }
    ]
    
    # Establish Ground Truth sets based on keyword presence in chunks
    evaluation_dataset = []
    for item in test_suite:
        relevant_chunks = set()
        for chunk in chunks:
            # Check if all keywords are present in the chunk text (case-insensitive)
            if all(k in chunk["text"].lower() for k in item["keywords"]):
                relevant_chunks.add(chunk["id"])
                
        # If no chunk matches all, fall back to matching at least one strong keyword
        if not relevant_chunks:
            primary_keyword = item["keywords"][0]
            for chunk in chunks:
                if primary_keyword in chunk["text"].lower():
                    relevant_chunks.add(chunk["id"])
                    
        evaluation_dataset.append({
            "query": item["query"],
            "relevant_chunks": relevant_chunks
        })
        console.print(f"Query: '[bold italic]{item['query']}[/bold italic]' has [yellow]{len(relevant_chunks)}[/yellow] ground-truth chunks.")

    # Evaluate across different Alpha weights (Dense vs Sparse vs Hybrid)
    # alpha = 1.0 (Dense-only)
    # alpha = 0.0 (Sparse-only)
    # alpha = 0.5 (Balanced Hybrid)
    alphas = [1.0, 0.0, 0.5, 0.7]
    top_k = 5
    
    table = Table(title="Retrieval Performance Evaluation (Top-5)", header_style="bold magenta")
    table.add_column("Retrieval Mode (Alpha Weight)", justify="left", style="cyan")
    table.add_column("Mean Reciprocal Rank (MRR)", justify="right", style="green")
    table.add_column("Mean Average Precision (MAP)", justify="right", style="green")
    
    for alpha in alphas:
        rr_scores = []
        ap_scores = []
        
        for eval_item in evaluation_dataset:
            query = eval_item["query"]
            ground_truth = eval_item["relevant_chunks"]
            
            # Retrieve top-k
            retrieved = retrieve(query, chunks, dense_embeddings, sparse_index, alpha=alpha, top_k=top_k)
            retrieved_ids = [r["id"] for r in retrieved]
            
            # Compute scores
            rr = calculate_reciprocal_rank(retrieved_ids, ground_truth)
            ap = calculate_average_precision(retrieved_ids, ground_truth)
            
            rr_scores.append(rr)
            ap_scores.append(ap)
            
        mean_mrr = sum(rr_scores) / len(rr_scores)
        mean_map = sum(ap_scores) / len(ap_scores)
        
        mode_label = f"Dense-Only (alpha={alpha})" if alpha == 1.0 else \
                     f"Sparse-Only (alpha={alpha})" if alpha == 0.0 else \
                     f"Hybrid (alpha={alpha})"
        
        table.add_row(mode_label, f"{mean_mrr:.4f}", f"{mean_map:.4f}")
        
    console.print("\n")
    console.print(table)
    console.print("\n[bold green]Evaluation Suite Complete![/bold green]")

if __name__ == "__main__":
    run_evaluation_suite()
