# =============================================================================
# step4_rag_query.py  —  Hybrid RAG Query + Evaluation
# =============================================================================
#
# What this file does (plain English):
# --------------------------------------
# 1. User asks a question (e.g. "What is the difference between SDD and EDD?")
# 2. We search our Pinecone database TWO ways at the same time:
#       a) DENSE SEARCH  — understands the MEANING of the question
#       b) SPARSE SEARCH — matches the exact KEYWORDS in the question
# 3. We get two separate ranked lists (top-20 each) and MERGE them using
#    a technique called Reciprocal Rank Fusion (RRF) → final top-5 chunks
# 4. Those 5 chunks are sent to GPT-4o which writes a grounded answer
# 5. We measure how GOOD the search was using two scores: MRR and MAP
#
# NOTE: This file depends on ingest.py having been run first.
#       ingest.py builds the Pinecone index AND saves sparse_index_config.json.
# =============================================================================


# ─── IMPORTS ──────────────────────────────────────────────────────────────────
# These are Python libraries we need. Think of them as toolboxes.

import os           # For reading environment variables (API keys)
import re           # For splitting text into words using patterns
import math         # For math operations like square root and logarithm
import json         # For reading/writing JSON files
import hashlib      # For converting words into unique integer IDs
from collections import Counter, defaultdict
# Counter  → counts how many times each word appears in a text
# defaultdict → a dictionary that automatically sets a default value (here: 0.0)

from dotenv import load_dotenv  # Reads secrets from the .env file
from openai import OpenAI       # OpenAI SDK for embeddings and chat
from pinecone import Pinecone   # Pinecone SDK for vector database search
from rich.console import Console  # Rich library for beautiful colored terminal output
from rich.table import Table      # Rich library for printing tables in the terminal


# ─── SECTION 1: CONFIGURATION ────────────────────────────────────────────────
# This section sets up all the settings for the script.
# We read secrets (API keys) from the .env file, never hardcode them here.

load_dotenv()  # Reads the .env file and loads variables into os.getenv()

# API Keys — loaded securely from the .env file
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY    = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# Model names — MUST be the same as what was used in ingest.py
EMBED_MODEL = "text-embedding-3-small"  # Converts text → 1536 numbers (dense vector)
LLM_MODEL   = "openai/gpt-4o"          # The AI model that writes the final answer

# Search settings
TOP_K_FETCH = 20  # How many candidate chunks to pull from EACH search (dense & sparse)
TOP_K       = 5   # How many chunks to keep AFTER merging and re-ranking
RRF_K       = 60  # Smoothing constant for RRF (explained later). Standard value = 60.

# Path to the vocabulary file saved by ingest.py
SPARSE_CONFIG_PATH = "sparse_index_config.json"

# Set up the Rich console (for pretty colored output in the terminal)
console = Console()


# ─── SECTION 2: CONNECT TO SERVICES ──────────────────────────────────────────
# We create "client" objects that let us talk to OpenAI and Pinecone.

# OpenAI client — we use OpenRouter as the base URL (it routes to OpenAI)
openai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENAI_API_KEY
)

# Pinecone client — connects us to our cloud vector database
pc    = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)  # "index" is our database table in Pinecone


# ─── SECTION 3: SPARSE SEARCH HELPER FUNCTIONS ───────────────────────────────
# These small functions help convert a user query into a sparse (keyword) vector.
# They MUST use the exact same logic as ingest.py — otherwise the results won't match.


def load_sparse_config():
    """
    Loads the IDF (word importance) weights that were saved by ingest.py.

    Why do we need this?
    When ingest.py ran, it read ALL the chunks from the PDF and calculated
    how important each word is across the whole document.
    Those importance scores (called IDF weights) are saved in a JSON file.
    We reload that file here so we can weight the user's query the same way.

    Returns: a dictionary like {"sdd": 3.5, "what": 0.8, "edd": 3.5, ...}
    """
    # Check the file exists before trying to open it
    if not os.path.exists(SPARSE_CONFIG_PATH):
        raise FileNotFoundError(
            f"'{SPARSE_CONFIG_PATH}' not found. "
            "Please run ingest.py first to generate it."
        )

    # Open and parse the JSON file
    with open(SPARSE_CONFIG_PATH, "r") as f:
        config = json.load(f)

    return config["idfs"]  # Return just the word → weight dictionary


def tokenize(text):
    """
    Breaks a sentence into a list of individual lowercase words.

    Example:
        Input:  "What is EDD?"
        Output: ["what", "is", "edd"]

    The regex pattern r'\w+' means "find all sequences of letters/digits".
    This removes punctuation like "?" automatically.
    """
    return re.findall(r'\w+', text.lower())


def get_token_id(token):
    """
    Converts a word (string) into a unique integer ID.

    Why integers? Pinecone's sparse vectors need INTEGER dimension indices,
    not word strings. We use MD5 hashing to get a consistent number for each word.

    Example:
        "sdd"  → 2847392017  (always the same number for "sdd")
        "edd"  → 1923847561  (always the same number for "edd")

    CRITICAL: This must match ingest.py exactly, otherwise query dimensions
    won't line up with stored document dimensions.
    """
    # MD5 gives us a 32-character hex string. We take the first 8 chars
    # and convert from hexadecimal to a regular integer.
    return int(hashlib.md5(token.encode('utf-8')).hexdigest()[:8], 16)


def build_sparse_query_vector(query, idfs):
    """
    Converts a user's query sentence into a sparse vector for Pinecone.

    A sparse vector is a list of (index, value) pairs where:
      - index = an integer ID representing a word
      - value = how important that word is (TF × IDF weight)

    Step-by-step:
      1. Tokenize: "What is EDD?" → ["what", "is", "edd"]
      2. Count frequency (TF): {"what": 1, "is": 1, "edd": 1}
      3. Multiply by IDF weight: {"what": 0.08, "is": 0.09, "edd": 3.5}
         (rare words like "edd" get high weight, common words get low weight)
      4. L2 Normalize: scale all values so the vector has length = 1
      5. Hash words to integers: {"2847...": 0.X, "1923...": 0.Y, ...}
      6. Sort by integer index (Pinecone requires this)

    Returns: {"indices": [int, int, ...], "values": [float, float, ...]}
    """
    # Step 1: Break query into words
    tokens = tokenize(query)

    # Step 2: Count how many times each word appears in the query
    word_counts = Counter(tokens)

    # Step 3: Multiply each word count by its IDF weight
    # Words not in our vocabulary (not in idfs) are skipped (weight = 0)
    weighted_words = {}
    for word, count in word_counts.items():
        idf_weight = idfs.get(word, 0.0)  # Get saved importance score
        if idf_weight > 0:                 # Only include words we know
            weighted_words[word] = count * idf_weight

    # If no query words are in our vocabulary, return an empty vector
    if not weighted_words:
        return {"indices": [], "values": []}

    # Step 4: L2 Normalization
    # This scales the vector to have a total "length" of exactly 1.0
    # Formula: divide each value by sqrt(sum of all values squared)
    sum_of_squares = sum(value ** 2 for value in weighted_words.values())
    vector_length  = math.sqrt(sum_of_squares)

    if vector_length > 0:
        # Divide every value by the length (this scales the whole vector)
        weighted_words = {word: val / vector_length for word, val in weighted_words.items()}

    # Step 5 & 6: Hash words to integers and sort by integer index
    index_value_pairs = []
    for word, value in weighted_words.items():
        integer_id = get_token_id(word)          # e.g. "edd" → 1923847561
        index_value_pairs.append((integer_id, value))

    # Sort by the integer index (Pinecone's requirement)
    index_value_pairs.sort(key=lambda pair: pair[0])

    # Separate the sorted pairs into two lists
    indices = [pair[0] for pair in index_value_pairs]
    values  = [pair[1] for pair in index_value_pairs]

    return {"indices": indices, "values": values}


# ─── SECTION 4: DENSE SEARCH ─────────────────────────────────────────────────
# Dense search understands the MEANING of the question using AI embeddings.
# Pinecone uses an algorithm called HNSW to find the closest matches fast.


def embed_question(question):
    """
    Converts a question string into a list of 1536 numbers (a dense vector).

    These numbers represent the semantic MEANING of the question.
    Similar questions produce similar number lists (close vectors).

    Example:
        "What is EDD?" → [0.015, -0.024, 0.089, 0.002, ...] (1536 numbers)
    """
    response = openai_client.embeddings.create(
        model=EMBED_MODEL,
        input=[question]  # API expects a list, so wrap the string in []
    )
    # response.data[0].embedding is the list of 1536 floats
    return response.data[0].embedding


def dense_search(question):
    """
    Searches Pinecone using the MEANING of the question (semantic search).

    HOW HNSW WORKS (simplified):
      Pinecone stores all chunk vectors in a special graph structure called HNSW
      (Hierarchical Navigable Small World). Think of it like a city map:
        - Top layers = highways (fast, long-range connections)
        - Bottom layers = local streets (slow, precise, short-range connections)
      The search starts on the highway, quickly gets close to the answer,
      then zooms in on local streets to find the exact best matches.
      This means we can search millions of vectors in milliseconds!

    Returns: a list of up to TOP_K_FETCH chunks, each as a dictionary with:
        id, text, page_number, source, dense_score (cosine similarity), dense_rank
    """
    console.print("  [Step A.1] Converting question to a dense vector (embedding)...")
    query_vector = embed_question(question)

    console.print(f"  [Step A.2] Searching Pinecone (HNSW) for top {TOP_K_FETCH} semantic matches...")
    # Pinecone runs HNSW internally when we pass a dense "vector" parameter
    results = index.query(
        vector=query_vector,    # The 1536-number embedding of the question
        top_k=TOP_K_FETCH,      # Return this many top matches
        include_metadata=True   # Include the original text and page info
    )

    # Build a clean list from the raw Pinecone response
    candidates = []
    for rank, match in enumerate(results["matches"], start=1):
        # Each "match" has: id, score, metadata (text, page_number, source, chunk_index)
        candidates.append({
            "id":           match["id"],
            "text":         match["metadata"]["text"],
            "page_number":  match["metadata"].get("page_number", "?"),
            "source":       match["metadata"].get("source", "unknown"),
            "chunk_index":  match["metadata"].get("chunk_index", "?"),
            "dense_score":  round(match["score"], 6),  # Cosine similarity (0 to 1)
            "dense_rank":   rank,                       # Position in this ranked list
            "sparse_score": 0.0,                        # Placeholder (filled later if needed)
            "sparse_rank":  None,                       # Placeholder
        })

    return candidates


# ─── SECTION 5: SPARSE SEARCH ─────────────────────────────────────────────────
# Sparse search matches the exact KEYWORDS in the question against the documents.
# Great for specific terms like "SDD", "EDD", "SAR", "PEP" that have exact matches.


def sparse_search(question, idfs):
    """
    Searches Pinecone using keyword matching (sparse TF-IDF search).

    Pinecone compares the query's sparse vector against the sparse_values
    that were stored during ingest.py. Words with higher IDF weights
    (rarer words) contribute more to the match score.

    Returns: a list of up to TOP_K_FETCH chunks (similar structure to dense_search)
    """
    console.print("  [Step B.1] Building sparse (TF-IDF keyword) vector for the query...")
    sparse_vector = build_sparse_query_vector(question, idfs)

    # Safety check: if none of the query words are in our vocabulary, skip
    if not sparse_vector["indices"]:
        console.print("  [Warning] No known vocabulary words in query. Skipping sparse search.")
        return []

    console.print(f"  [Step B.2] Searching Pinecone with sparse keywords for top {TOP_K_FETCH} matches...")
    # NOTE: We pass "sparse_vector" (not "vector") to tell Pinecone to use keyword matching
    results = index.query(
        sparse_vector=sparse_vector,  # The TF-IDF keyword vector
        top_k=TOP_K_FETCH,
        include_metadata=True
    )

    # Build a clean list from the Pinecone response
    candidates = []
    for rank, match in enumerate(results["matches"], start=1):
        candidates.append({
            "id":           match["id"],
            "text":         match["metadata"]["text"],
            "page_number":  match["metadata"].get("page_number", "?"),
            "source":       match["metadata"].get("source", "unknown"),
            "chunk_index":  match["metadata"].get("chunk_index", "?"),
            "dense_score":  0.0,                        # Placeholder
            "dense_rank":   None,                       # Placeholder
            "sparse_score": round(match["score"], 6),   # Keyword dot-product score
            "sparse_rank":  rank,                       # Position in this ranked list
        })

    return candidates


# ─── SECTION 6: RE-RANKING WITH RECIPROCAL RANK FUSION (RRF) ─────────────────
# We now have two ranked lists (dense top-20 and sparse top-20).
# We need to MERGE them into one final ranked list of top-5 chunks.
# We use RRF for this because we cannot simply add dense scores + sparse scores
# (they are on completely different scales).


def reciprocal_rank_fusion(dense_candidates, sparse_candidates):
    """
    Merges two ranked lists into one using Reciprocal Rank Fusion (RRF).

    THE CORE IDEA:
      Instead of comparing raw scores (which are on different scales),
      we convert every chunk's score into its RANK (position 1, 2, 3...).
      Then we calculate an RRF score for each chunk using this formula:

          RRF_score = sum of (1 / (RRF_K + rank)) for each list the chunk appears in

      A chunk that appears at rank 1 in BOTH lists gets the highest RRF score.
      A chunk that appears only in one list still gets some credit.

    WORKED EXAMPLE (RRF_K = 60):
      Dense list:  [chunk_A rank=1, chunk_B rank=2, chunk_C rank=3]
      Sparse list: [chunk_B rank=1, chunk_A rank=2, chunk_D rank=3]

      chunk_A RRF = 1/(60+1) + 1/(60+2) = 0.01639 + 0.01613 = 0.03252
      chunk_B RRF = 1/(60+2) + 1/(60+1) = 0.01613 + 0.01639 = 0.03252
      chunk_C RRF = 1/(60+3)             = 0.01587  (only in dense list)
      chunk_D RRF = 1/(60+3)             = 0.01587  (only in sparse list)

    Returns: the top TOP_K chunks sorted by RRF score (best first)
    """
    console.print("  [Step C.1] Merging dense and sparse results using RRF...")

    # We use two dictionaries to track each chunk:
    # chunk_registry: id → full chunk data (text, page, scores, etc.)
    # rrf_scores: id → accumulated RRF score (starts at 0.0 for each chunk)
    chunk_registry = {}
    rrf_scores     = defaultdict(float)  # defaultdict means new keys start at 0.0

    # Process the DENSE list: calculate RRF contribution from each rank
    for rank, chunk in enumerate(dense_candidates, start=1):
        chunk_id = chunk["id"]

        # Save this chunk's data if we haven't seen it before
        if chunk_id not in chunk_registry:
            chunk_registry[chunk_id] = chunk.copy()

        # Update dense rank and score in the registry
        chunk_registry[chunk_id]["dense_rank"]  = rank
        chunk_registry[chunk_id]["dense_score"] = chunk["dense_score"]

        # Add this list's RRF contribution: 1 / (RRF_K + rank)
        rrf_scores[chunk_id] += 1.0 / (RRF_K + rank)

    # Process the SPARSE list: same logic
    for rank, chunk in enumerate(sparse_candidates, start=1):
        chunk_id = chunk["id"]

        if chunk_id not in chunk_registry:
            chunk_registry[chunk_id] = chunk.copy()

        chunk_registry[chunk_id]["sparse_rank"]  = rank
        chunk_registry[chunk_id]["sparse_score"] = chunk["sparse_score"]

        rrf_scores[chunk_id] += 1.0 / (RRF_K + rank)

    # Build the final merged list, attaching the RRF score to each chunk
    merged_list = []
    for chunk_id, rrf_score in rrf_scores.items():
        chunk_data = chunk_registry[chunk_id].copy()
        chunk_data["rrf_score"] = round(rrf_score, 8)
        merged_list.append(chunk_data)

    # Sort by RRF score (highest = best match = comes first)
    merged_list.sort(key=lambda chunk: chunk["rrf_score"], reverse=True)

    # Return only the top TOP_K chunks (e.g., top 5)
    return merged_list[:TOP_K]


# ─── SECTION 7: GENERATE THE LLM ANSWER ──────────────────────────────────────
# We take the re-ranked top-5 chunks and ask GPT-4o to write an answer
# using ONLY those chunks. This prevents hallucination.


def generate_answer(question, reranked_chunks):
    """
    Sends the top re-ranked chunks + the original question to GPT-4o.
    GPT-4o reads the context and writes a precise, grounded answer.

    The system prompt STRICTLY instructs the model to:
      - Only use the provided context (no hallucination)
      - Cite the page number in the answer
      - Say "I could not find this" if the answer isn't in the context
    """
    # Build the context block — concatenate all chunks with labels
    context_block = ""
    for i, chunk in enumerate(reranked_chunks):
        rrf = chunk.get("rrf_score", "N/A")
        page = chunk["page_number"]
        context_block += f"[Chunk {i+1} | Page {page} | RRF Score: {rrf}]\n"
        context_block += chunk["text"] + "\n\n"

    # The system prompt tells GPT-4o HOW to behave
    system_prompt = (
        "You are a KYC compliance assistant. "
        "Answer the user's question using ONLY the context provided below. "
        "If the answer is not in the context, say: 'I could not find this in the KYC policy.' "
        "Do not use any external knowledge. Be precise and cite the page number."
    )

    # The user prompt contains the actual context + question
    user_prompt = (
        f"CONTEXT:\n{context_block}\n"
        f"QUESTION: {question}\n\n"
        f"ANSWER:"
    )

    # Call the GPT-4o model via OpenRouter
    response = openai_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.0   # temperature=0 means deterministic (no randomness)
    )

    # Extract the text answer from the response object
    return response.choices[0].message.content.strip()


# ─── SECTION 8: EVALUATION METRICS ───────────────────────────────────────────
# After retrieving chunks, we measure HOW GOOD the search was.
# We use two standard metrics: MRR (speed of first correct hit) and MAP (quality of full list).


def build_ground_truth(retrieved_chunks, keywords):
    """
    Figures out which of the retrieved chunks actually contain the answer.
    This is our "ground truth" — the correct answers to compare against.

    Strategy:
      1. Try to find chunks containing ALL keywords (strict match)
      2. If none found, fall back to chunks containing just the FIRST keyword (loose match)

    Example:
      keywords = ["sdd", "edd", "due diligence"]
      → Find chunks whose text contains all three words

    Returns: a Python set of chunk IDs that are "correct" answers
    """
    correct_chunk_ids = set()

    # Try strict match: all keywords must be present in the chunk text
    for chunk in retrieved_chunks:
        chunk_text_lower = chunk["text"].lower()
        all_keywords_present = all(kw.lower() in chunk_text_lower for kw in keywords)
        if all_keywords_present:
            correct_chunk_ids.add(chunk["id"])

    # If strict match found nothing, try loose match with just the primary keyword
    if not correct_chunk_ids and keywords:
        primary_keyword = keywords[0].lower()
        for chunk in retrieved_chunks:
            if primary_keyword in chunk["text"].lower():
                correct_chunk_ids.add(chunk["id"])

    return correct_chunk_ids


def compute_reciprocal_rank(retrieved_ids, correct_ids):
    """
    Computes Reciprocal Rank (RR) for a single query.

    WHAT IT MEASURES:
      How quickly did we find the FIRST correct answer?

    CALCULATION:
      Go through the ranked list one by one.
      When you hit the first correct chunk, compute: 1 / its_position.

    EXAMPLES:
      Correct chunk at Position 1 → RR = 1/1 = 1.0  (perfect!)
      Correct chunk at Position 2 → RR = 1/2 = 0.5
      Correct chunk at Position 5 → RR = 1/5 = 0.2
      No correct chunk found      → RR = 0.0  (failed)
    """
    for position, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in correct_ids:
            return 1.0 / position  # Found! Return the reciprocal of the position
    return 0.0  # Nothing found in the entire list


def compute_average_precision(retrieved_ids, correct_ids):
    """
    Computes Average Precision (AP) for a single query.

    WHAT IT MEASURES:
      Did we find ALL the correct answers AND did we put them near the top?

    CALCULATION:
      - Every time we encounter a correct chunk, we calculate Precision@k:
            Precision@k = (correct chunks found so far) / k
      - Sum all those precision values, divide by total number of correct chunks

    EXAMPLE (2 correct chunks exist in total: chunk_A and chunk_B):
      Retrieved list: [chunk_X, chunk_A, chunk_Y, chunk_B, chunk_Z]
                        rank=1    rank=2   rank=3   rank=4    rank=5

      Rank 1: chunk_X  → NOT correct, skip
      Rank 2: chunk_A  → CORRECT! hits=1, Precision@2 = 1/2 = 0.50
      Rank 3: chunk_Y  → NOT correct, skip
      Rank 4: chunk_B  → CORRECT! hits=2, Precision@4 = 2/4 = 0.50
      Rank 5: chunk_Z  → NOT correct, skip

      AP = (0.50 + 0.50) / 2 correct chunks = 0.50
    """
    if not correct_ids:
        return 0.0  # No ground truth? Can't evaluate.

    correct_hits_so_far = 0
    precision_sum       = 0.0

    for position, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in correct_ids:
            correct_hits_so_far += 1
            precision_at_this_position = correct_hits_so_far / position
            precision_sum += precision_at_this_position

    # Divide by TOTAL number of correct chunks (not just the ones we found)
    return precision_sum / len(correct_ids)


def run_evaluation(all_pipeline_results):
    """
    Computes MRR and MAP across ALL queries that were run.

    MRR = Average of all Reciprocal Ranks  → How fast was the first correct result?
    MAP = Average of all Average Precisions → How good was the full ranked list?

    Both metrics range from 0.0 (worst) to 1.0 (perfect).

    Returns: {"MRR": float, "MAP": float}
    """
    console.print("\n[bold]Computing evaluation scores for each query...[/bold]")

    all_rr_scores = []  # One reciprocal rank per query
    all_ap_scores = []  # One average precision per query

    for pipeline_result in all_pipeline_results:
        query           = pipeline_result["query"]
        retrieved_chunks = pipeline_result["retrieved_chunks"]
        keywords        = pipeline_result["keywords"]

        # Get the list of retrieved chunk IDs in rank order (rank 1 first)
        retrieved_ids = [chunk["id"] for chunk in retrieved_chunks]

        # Figure out which chunks contain the correct answer (ground truth)
        correct_ids = build_ground_truth(retrieved_chunks, keywords)

        # Compute RR and AP for this query
        rr = compute_reciprocal_rank(retrieved_ids, correct_ids)
        ap = compute_average_precision(retrieved_ids, correct_ids)

        all_rr_scores.append(rr)
        all_ap_scores.append(ap)

        # Print per-query result
        console.print(
            f"  Query: [italic]{query[:55]}[/italic] | "
            f"Ground truth chunks: [yellow]{len(correct_ids)}[/yellow] | "
            f"RR: [cyan]{rr:.4f}[/cyan] | AP: [green]{ap:.4f}[/green]"
        )

    # Calculate the MEAN (average) across all queries
    mrr = sum(all_rr_scores) / len(all_rr_scores) if all_rr_scores else 0.0
    map_ = sum(all_ap_scores) / len(all_ap_scores) if all_ap_scores else 0.0

    return {"MRR": round(mrr, 4), "MAP": round(map_, 4)}


# ─── SECTION 9: THE FULL PIPELINE (one question) ─────────────────────────────
# This function ties everything together for a SINGLE question.


def run_rag_pipeline(question, idfs, keywords=None):
    """
    Runs the full hybrid RAG pipeline for ONE question:
      Dense Search → Sparse Search → RRF Merge → LLM Answer

    Parameters:
      question  : The user's question (string)
      idfs      : The word importance weights loaded from sparse_index_config.json
      keywords  : List of keywords to identify correct chunks (for evaluation)

    Returns: a dictionary with the question, retrieved chunks, and the LLM's answer
    """
    console.print(f"\n[bold cyan]{'='*65}[/bold cyan]")
    console.print(f"[bold]QUESTION:[/bold] {question}")
    console.print(f"[bold cyan]{'='*65}[/bold cyan]")

    # ─── Step A: Dense Search ────────────────────────────────────────────────
    console.print("\n[bold yellow]Step A → Dense (Semantic / HNSW) Search[/bold yellow]")
    dense_results = dense_search(question)
    console.print(f"  ✓ Got {len(dense_results)} semantically matched candidates")

    # ─── Step B: Sparse Search ───────────────────────────────────────────────
    console.print("\n[bold yellow]Step B → Sparse (Keyword / TF-IDF) Search[/bold yellow]")
    sparse_results = sparse_search(question, idfs)
    console.print(f"  ✓ Got {len(sparse_results)} keyword matched candidates")

    # ─── Step C: RRF Re-ranking ──────────────────────────────────────────────
    console.print("\n[bold yellow]Step C → Reciprocal Rank Fusion (RRF) Re-ranking[/bold yellow]")
    reranked_chunks = reciprocal_rank_fusion(dense_results, sparse_results)

    console.print(f"  ✓ Final top-{TOP_K} chunks after RRF merge:")
    for i, chunk in enumerate(reranked_chunks):
        dense_rank  = chunk.get("dense_rank",  "—")  # "—" if not found in dense list
        sparse_rank = chunk.get("sparse_rank", "—")  # "—" if not found in sparse list
        console.print(
            f"    #{i+1} | RRF Score: {chunk['rrf_score']:.6f} | "
            f"Dense Rank: {dense_rank} | Sparse Rank: {sparse_rank} | "
            f"Page: {chunk['page_number']}"
        )
        # Show a short preview of the chunk text (first 90 characters)
        preview = chunk["text"][:90].replace("\n", " ")
        console.print(f"         Preview: {preview}...")

    # ─── Step D: Generate LLM Answer ─────────────────────────────────────────
    console.print("\n[bold yellow]Step D → Generating Grounded LLM Answer[/bold yellow]")
    answer = generate_answer(question, reranked_chunks)
    console.print(f"\n[bold green]ANSWER:[/bold green]\n{answer}")

    # Return everything packed into a dictionary for later evaluation
    return {
        "query":            question,
        "retrieved_chunks": reranked_chunks,
        "answer":           answer,
        "keywords":         keywords or []
    }


# ─── SECTION 10: MAIN — RUNS WHEN YOU EXECUTE THIS FILE ──────────────────────
# This block only runs when you type: python step4_rag_query.py
# It does NOT run when another file imports this file.

if __name__ == "__main__":

    console.print("[bold cyan]\n=== Hybrid RAG Pipeline with Evaluation ===[/bold cyan]\n")

    # ── Load the IDF vocabulary saved by ingest.py ───────────────────────────
    console.print(f"Loading sparse index config from [green]{SPARSE_CONFIG_PATH}[/green]...")
    idfs = load_sparse_config()
    console.print(f"  ✓ Loaded IDF weights for [yellow]{len(idfs):,}[/yellow] vocabulary words.\n")

    # ── Define all test questions ─────────────────────────────────────────────
    # Each question has:
    #   "query"    → the question string
    #   "keywords" → words used to identify which chunks contain the correct answer
    test_questions = [
        {
            "query":    "What is the difference between SDD and EDD?",
            "keywords": ["sdd", "edd", "due diligence"]
        },
        {
            "query":    "Who qualifies as a PEP and what extra steps are required?",
            "keywords": ["pep", "politically exposed person"]
        },
        {
            "query":    "What are SAR filing thresholds in the US and UK?",
            "keywords": ["sar", "threshold", "filing"]
        },
        {
            "query":    "How is the KYC risk score calculated?",
            "keywords": ["risk", "score", "kyc"]
        },
        {
            "query":    "What are the penalties for KYC non-compliance?",
            "keywords": ["penalty", "penalties", "non-compliance"]
        },
    ]

    # ── Run the pipeline for EVERY question and collect results ───────────────
    all_results = []
    for item in test_questions:
        result = run_rag_pipeline(
            question=item["query"],
            idfs=idfs,
            keywords=item["keywords"]
        )
        all_results.append(result)

    # ── Evaluate all queries: compute MAP and MRR ─────────────────────────────
    console.print(f"\n[bold cyan]{'='*65}[/bold cyan]")
    console.print("[bold cyan]RETRIEVAL EVALUATION — MRR and MAP[/bold cyan]")
    console.print(f"[bold cyan]{'='*65}[/bold cyan]")
    console.print("[dim]Ground truth = retrieved chunks that contain the answer keywords[/dim]\n")

    metrics = run_evaluation(all_results)

    # ── Print a summary table ─────────────────────────────────────────────────
    summary_table = Table(title="Final Evaluation Summary", header_style="bold magenta")
    summary_table.add_column("Metric",             style="cyan",  justify="left")
    summary_table.add_column("Score",              style="green", justify="center")
    summary_table.add_column("What It Tells You",  style="white", justify="left")

    summary_table.add_row(
        "Mean Reciprocal Rank (MRR)",
        str(metrics["MRR"]),
        "Speed of finding 1st correct chunk. 1.0 = found it at rank 1 every time."
    )
    summary_table.add_row(
        "Mean Average Precision (MAP)",
        str(metrics["MAP"]),
        "Quality of full ranked list. 1.0 = all correct chunks at the very top."
    )

    console.print(summary_table)

    # ── Save everything to a JSON file for review ─────────────────────────────
    output_file = "rag_query_results.json"

    # Build a clean, serializable version of the results (no complex objects)
    serializable_results = []
    for result in all_results:
        serializable_results.append({
            "question": result["query"],
            "answer":   result["answer"],
            "evaluation_metrics": {
                "MRR": metrics["MRR"],
                "MAP": metrics["MAP"]
            },
            "retrieved_chunks": [
                {
                    "id":           chunk["id"],
                    "page_number":  chunk["page_number"],
                    "rrf_score":    chunk.get("rrf_score", 0),
                    "dense_rank":   chunk.get("dense_rank"),
                    "sparse_rank":  chunk.get("sparse_rank"),
                    "text_preview": chunk["text"][:120]  # First 120 characters only
                }
                for chunk in result["retrieved_chunks"]
            ]
        })

    # Write the JSON file
    with open(output_file, "w") as f:
        json.dump(serializable_results, f, indent=2)

    console.print(f"\n[bold green]✓ All results saved to:[/bold green] {output_file}")
    console.print("[bold green]✓ Pipeline Complete.[/bold green]\n")
