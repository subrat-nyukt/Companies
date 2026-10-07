# AI System Design: Real-Time E-Commerce Recommendation

This is a classic **Machine Learning System Design** question (Question 3 of 3 from the Aivar Innovations screenshots). Since the prompt explicitly specifies an *e-commerce client*, we will pivot slightly from KYC to focus purely on high-scale personalization, while still leveraging your AI engineering expertise.

Here is the exact notepad/whiteboard structure you should use during the interview.

---

## 1. High-Level Architecture (The Two-Stage Funnel)
To hit a strict < 100ms p99 latency at 50K RPS, we cannot run a heavy neural network on 10 million products. We must split the problem:


before

In a simple academic notebook, you might run model.encode("user data") right there in the Python code. You cannot do that in production. Running an embedding model inside the web request takes too long.

Here is exactly how that user_embedding list (e.g., [0.1, -0.4, 0.8, ...]) gets injected into the Python code in the real world:

The "Streaming" Pipeline (Happens in the background)
The User Clicks: John clicks on a pair of "Red Nike Running Shoes".
Kafka catches it: That click event is instantly sent to an Apache Kafka message stream.
Apache Flink calculates the math: An Apache Flink streaming job is listening to Kafka. It looks at the "Red Nike Shoes", grabs the pre-computed mathematical embedding for those shoes, and mathematically combines it with John's historical embedding.
Saved to Redis: Flink takes that final string of numbers (the brand new user_embedding list) and saves it into Redis under the key user_123.







1.  **Candidate Generation (Retrieval):** 
    *   *Goal:* Quickly filter 50M SKUs down to ~500 highly relevant candidates.
    *   *Tech:* Vector Database (e.g., Milvus, Pinecone) using Approximate Nearest Neighbors (ANN). We take the user's real-time session embedding and do a fast cosine similarity search.

Step 1: What is an Embedding?
An embedding is just an array of floating-point numbers mapping an item’s "meaning" in a multi-dimensional space. For example, an item embedding for a Red Nike Running Shoe might be a 384-dimensional vector: [0.91, -0.22, 0.54, 0.11, ..., 0.88].

The user also has an embedding representing their history/preferences, which is generated to exist in that self-same 384-dimensional space.

Step 2: How ANN Works (The HNSW Algorithm)
If you do an exact math calculation (like Cosine Similarity) between your user array and all 50 Million product arrays, it would take several seconds. That is too slow.

Instead, Pinecone uses **HNSW** (Hierarchical Navigable Small World) graphs, which is the most popular ANN algorithm.

**Relationship between Algorithm & Metric:**
*   **Metric (Cosine Similarity):** This defines "Closeness". It measures the angle between vectors to see how similar the user's intent is to the product.
*   **Algorithm (HNSW):** This is the search strategy. It creates a multi-layered graph where items with high similarity are connected, allowing us to "jump" through the database instead of scanning it sequentially.

Imagine a map of the world:

The Top Layer (Highway): Instead of checking every address, Pinecone first jumps to the "continent" the user vector is closest to (e.g., "The Sports Apparel cluster").
The Middle Layer (City Roads): It drops down a level and navigates to the closest "City" (e.g., "Running Shoes").
The Bottom Layer (Street Level): It drops down to the bottom layer and only calculates the exact distance for products nearby (e.g., specific "Red Nike Shoes").
Because it skips 99.9% of the products that are "on the wrong continent," it returns answers in ~20 milliseconds. It is "Approximate", meaning it might miss the literal #1 best mathematical match, but the Top 500 it brings back are good enough for the next stage (the Ranker Model) to sort out.




2.  **Ranking (Scoring / Re-ranking):**
    *   *Goal:* Take the ~500 "raw" candidates and find the precise `Top-20`.
    *   *Why we need it:* To "Confirm" the results. Vector search is fast but "blind" to real-time facts like stock, price, or specific user size preferences.
    *   *Tech:* Triton Inference Server running a **Cross-Encoder** model (XGBoost, DeepFM, or LightGBM).

**How the Re-ranker "Confirms":**
*   **Stage 1 (Pinecone):** "Here are 500 items that look like things this user usually buys." (Bi-Encoder approach).
*   **Stage 2 (Re-ranker):** "Out of these 500, which ones are in-stock, have 4+ star reviews, and match the user's current budget *right now*?" (Cross-Encoder approach).
*   **Outcome:** The Re-ranker often completely reshuffles the order. An item that was #400 in Pinecone might jump to #1 because it's on a 50% flash sale.

---

## 2. Latency Budget (< 100ms p99)
*Interviewers love when you explicitly budget the latency milliseconds.* Write this down:

*   **API Gateway & Auth:** `5ms`
*   **Feature Retrieval (Redis):** `15ms` (Grab the user's real-time session data and history).
*   **Candidate Generation (Vector DB):** `20ms` (Fetch top 500 candidate IDs).
*   **Item Feature Fetch (Redis):** `15ms` (Fetch price, inventory, brand for the 500 candidates).
*   **Ranking Model (ONNX/Triton):** `35ms` (Calculate probability of click/buy for all 500).
*   **Sorting & Response formatting:** `5ms`
*   **Total:** `95ms` (Safely under the 100ms limit).

---

## 3. Data & Feature Pipelines (Offline vs. Online)
You need to explain how "clicks" impact the model in seconds.

*   **Streaming (Real-Time Session Context):** 
    User clicks/add-to-carts are blasted to a **Kafka** topic. **Apache Flink** consumes this stream, calculates sliding real-time features (e.g., "count of shoes viewed in last 3 minutes"), and updates a fast **Redis Feature Store** in sub-seconds.
*   **Batch (Offline Training):**
    **Apache Spark** jobs run nightly over data lakes (S3/Snowflake) to generate heavy embeddings for new products and retrain the ranking models on the last 30 days of purchases.

---

## 4. Reliability & Fallback Paths (Targeting 99.9%)
How do you survive when traffic spikes or the AI model crashes?
*   **Circuit Breakers:** If the Triton Ranking server takes longer than 45ms, the circuit breaker opens and immediately kills the request.
*   **Degraded Mode 1 (Ranker Down):** If the Ranker is down, just return the 20 items straight from the Candidate Generator.
*   **Degraded Mode 2 (Vector DB Down):** If everything AI-related fails, fall back to a dumb Redis Cache of "Global Top Trending Items in [User's Category]." It's not personalized, but it ensures the webpage still loads instantly with *some* products.

---

## 5. Explicit Trade-offs You Must Mention
Interviewers don't want you to just name tools; they want to know *why*.

1.  **Why Vector DB over Database Search?**
    *   *Trade-off:* Relational databases (Postgres) can't do rapid semantic search over millions of dense vectors in 20ms. Vector DBs trade absolute accuracy for speed via ANN indexes (like HNSW).
2.  **Why Flink into Redis instead of directly updating the Database?**
    *   *Trade-off:* Hitting a primary SQL database at 50,000 writes/sec will cause locking and timeouts. Kafka+Flink streaming into an in-memory Redis cluster handles insane throughput with microsecond read times.
3.  **Why ONNX over Native PyTorch/TensorFlow?**
    *   *Trade-off:* Python models carry huge overhead. Serializing the model to `ONNX` and running it via C++ backends (Triton) cuts inference latency in half, allowing us to hit the 100ms SLO.
