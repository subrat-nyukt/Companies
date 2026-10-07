import os
import uuid
import time
import re
import math
import hashlib
import json
from collections import Counter

from dotenv import load_dotenv
from pypdf import PdfReader
import tiktoken
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec


#File Configuration

pdf_file="kyc_policy.pdf"


#Chunking config
chunk_size= 500

Overlap = 50

Batch_size= 50

#model Config

load=load_dotenv()

open_api_key=os.getenv("OPENAI_API_KEY")
pinecone_api_key=os.getenv("PINECONE_API_KEY")
pinecone_index_name=os.getenv("PINECONE_INDEX_NAME")

embed_model="text-embedding-3-small"

#Step 1 Read PDF

extracted_text=[]
try:

    with open(pdf_file, "rb") as f:
        reader = PdfReader(f)

        for i,page in enumerate(reader.pages):
            text = page.extract_text()
            extracted_text.append({"page_number":i, "text":text.strip()})
    

except Exception as e:
    print(f"An error occurred: {e}")


# Step 2 Chunking

from langchain.text_splitter import RecursiveCharacterTextSplitter

def get_chunks(Extracted_text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=50,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    all_chunks = []
    global_chunk_count = 0
    for entry in Extracted_text:
        page_chunks = text_splitter.split_text(entry["text"])
        actual_page = entry["page_number"]
        
        for i, chunk in enumerate(page_chunks):
            all_chunks.append({
                "id": str(uuid.uuid4()),
                "Text": chunk,
                "Metadta": {
                    "Source": pdf_file,
                    "Page_number": actual_page,
                    "chunk_index": global_chunk_count
                }
            })
            global_chunk_count += 1
    return all_chunks


chunks = get_chunks(extracted_text)

# Step 3 — Embeddings

openai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=open_api_key
)

response = openai_client.embeddings.create(
    model=embed_model,
    input=[chunk["Text"] for chunk in chunks]
)

for i, embedding_object in enumerate(response.data):
    chunks[i]["embedding"] = embedding_object.embedding 

print(f"-> Each vector has {len(chunks[0]['embedding'])} dimensions")


# ─────────────────────────────────────────────
# Step 3.5 — Sparse Indexing (TF-IDF)
# ─────────────────────────────────────────────
print("\nStep 3.5: Generating Sparse TF-IDF Vectors...")

def tokenize(text: str) -> list:
    """Tokenizes text into lowercase alphanumeric words."""
    return re.findall(r'\w+', text.lower())

def get_token_id(token: str) -> int:
    """Deterministic hash mapping a word to a 32-bit unsigned integer index."""
    return int(hashlib.md5(token.encode('utf-8')).hexdigest()[:8], 16)

num_docs = len(chunks)
doc_tokenized = [tokenize(c["Text"]) for c in chunks]

# Calculate Document Frequency (DF)
doc_freqs = Counter()
doc_freqs={}
for tokens in doc_tokenized:
    unique_tokens = set(tokens)
    for token in unique_tokens:
        doc_freqs[token] += 1

# Calculate Inverse Document Frequency (IDF) with smoothing
idfs = {}
for token, df in doc_freqs.items():
    idfs[token] = math.log((1 + num_docs) / (1 + df)) + 1

# Save IDFs to local config so they can be reused during search/queries
sparse_config = {
    "num_docs": num_docs,
    "idfs": idfs
}
with open("sparse_index_config.json", "w") as f:
    json.dump(sparse_config, f, indent=4)
print("-> Saved sparse index configuration to sparse_index_config.json")

# Build and normalize TF-IDF sparse vector for each chunk
for i, chunk in enumerate(chunks):
    tokens = doc_tokenized[i]
    tf = Counter(tokens)
    vector = {}
    for token, count in tf.items():
        vector[token] = count * idfs.get(token, 0.0)
    
    # L2 normalization to unit length
    norm = math.sqrt(sum(v**2 for v in vector.values()))
    if norm > 0:
        for token in vector:
            vector[token] /= norm
            
    # Format for Pinecone: dictionary of indices (sorted) and values
    indices = []
    values = []
    for token, val in vector.items():
        if val > 0:
            indices.append(get_token_id(token))
            values.append(val)
            
    # Pinecone requires sparse indices to be sorted in ascending order
    sorted_pairs = sorted(zip(indices, values))
    if sorted_pairs:
        sorted_indices, sorted_values = zip(*sorted_pairs)
    else:
        sorted_indices, sorted_values = [], []
        
    chunk["sparse_values"] = {
        "indices": list(sorted_indices),
        "values": list(sorted_values)
    }

print("-> Generated sparse vectors for all chunks.")


"""

# Preview the results
print("\n--- Embedding Preview (First 2 Chunks) ---")
for i, chunk in enumerate(chunks[:2]):
    print(f"\nChunk #{i}")
    print(f"Text: {chunk['Text'][:80]}...")
    print(f"Vector (first 5 values): {chunk['embedding'][:5]}")

"""

#Step 4 uplaod to pine cone

pc = Pinecone(api_key=pinecone_api_key)
index = pc.Index(pinecone_index_name)

# 2. Format the payload for Pinecone
pinecone_payload = []
for chunk in chunks:
    pinecone_payload.append({
        "id": chunk["id"],
        "values": chunk["embedding"],
        "sparse_values": chunk["sparse_values"],
        "metadata": {
            # CRITICAL: We must store the raw text in the metadata. 
            # A vector database only searches math; the LLM needs this text to read later.
            "text": chunk["Text"], 
            "source": chunk["Metadta"]["Source"],
            "page_number": chunk["Metadta"]["Page_number"],
            "chunk_index": chunk["Metadta"]["chunk_index"]
        }
    })


total_batches = (len(pinecone_payload) + Batch_size - 1) // Batch_size

for i in range(0, len(pinecone_payload), Batch_size):
    batch = pinecone_payload[i : i + Batch_size]
    
    try:
        # The actual database write operation
        index.upsert(vectors=batch)
        print(f"Successfully upserted batch {i//Batch_size + 1} of {total_batches} ({len(batch)} vectors)")
    except Exception as e:
        print(f"Failed to upsert batch {i//Batch_size + 1}: {e}")

print("\nIngestion Complete! Your KYC policy is now searchable in Pinecone.")