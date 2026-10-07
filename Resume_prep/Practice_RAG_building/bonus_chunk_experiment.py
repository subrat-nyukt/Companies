import os
import time
from dotenv import load_dotenv
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI

# Load environment variables
load_dotenv()
open_api_key = os.getenv("OPENAI_API_KEY")

# Configuration
pdf_file = "kyc_policy.pdf"
embed_model = "text-embedding-3-small"

# Set up OpenAI client (using OpenRouter as per ingest.py)
openai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=open_api_key
)

# Questions from the README to test retrieval on
test_questions = [
    "What is the difference between SDD and EDD?",
    "Who qualifies as a PEP and what extra steps are required?",
    "What are SAR filing thresholds in the US and UK?"
]

def get_text():
    """Extract all text from the PDF."""
    extracted = ""
    try:
        with open(pdf_file, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                extracted += page.extract_text() + " "
        return extracted
    except FileNotFoundError:
        print(f"Error: {pdf_file} not found. Make sure it is in the same directory.")
        exit(1)

def cosine_similarity(a, b):
    """
    OpenAI embeddings are unit vectors (normalized to length 1).
    Therefore, the dot product is exactly equal to cosine similarity.
    """
    return sum(x * y for x, y in zip(a, b))

def run_experiment():
    print("Reading PDF...")
    text = get_text()
    
    # Pre-embed the questions to save time and API calls
    print("Embedding test questions...")
    q_embeddings = []
    for q in test_questions:
        resp = openai_client.embeddings.create(model=embed_model, input=[q])
        q_embeddings.append(resp.data[0].embedding)
    
    # The different chunk sizes we want to test
    chunk_sizes = [250, 500, 1000]
    overlap_ratio = 0.1 # 10% overlap
    
    for size in chunk_sizes:
        overlap = int(size * overlap_ratio)
        print(f"\n{'='*60}")
        print(f"EXPERIMENT: Chunk Size = {size} | Overlap = {overlap}")
        print(f"{'='*60}")
        
        # 1. Chunk the text
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=size,
            chunk_overlap=overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_text(text)
        print(f"-> Generated {len(chunks)} chunks.")
        
        # 2. Embed all chunks (in batches to avoid rate limits)
        print("-> Embedding chunks...")
        chunk_embeddings = []
        batch_size = 50
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            resp = openai_client.embeddings.create(model=embed_model, input=batch)
            for data in resp.data:
                chunk_embeddings.append(data.embedding)
        
        # 3. Evaluate retrieval for each test question
        print("\n--- RETRIEVAL RESULTS ---")
        for q_idx, q in enumerate(test_questions):
            q_emb = q_embeddings[q_idx]
            
            # Calculate similarity score for all chunks
            scores = []
            for i, c_emb in enumerate(chunk_embeddings):
                score = cosine_similarity(q_emb, c_emb)
                scores.append((score, chunks[i]))
            
            # Sort by highest similarity score
            scores.sort(key=lambda x: x[0], reverse=True)
            best_score, best_chunk = scores[0]
            
            # Print the top hit
            print(f"\nQ: {q}")
            print(f"Top Match Score: {best_score:.4f}")
            
            # Clean up the text for printing (remove newlines)
            clean_chunk = best_chunk.replace('\n', ' ')
            print(f"Top Chunk Preview: {clean_chunk[:150]}...")

if __name__ == "__main__":
    run_experiment()
