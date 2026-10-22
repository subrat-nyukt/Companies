1. **"Pick one request path, such as a customer-support assistant, and describe where you would place caching, guardrails, and fallback logic, and how would you keep the components loosely coupled so a model or vector store can be swapped without rewriting the application?"**



Answer:
"I’ll use the request path of an Enterprise Customer-Support Assistant that resolves user billing and account troubleshooting queries.

Here is how I structure the request lifecycle across caching, guardrails, fallbacks, and architecture:

1. Input Guardrails (First Layer)
   Right when the user request hits our API Gateway, it passes through Input Guardrails:

PII Redaction: Masking sensitive data like credit card numbers, phone numbers, and emails.
Security & Prompt Injection Detection: Filtering out malicious system prompt extraction or jailbreak attempts before any downstream systems are touched.
2. Caching Layer (Before Retrieval & LLM)
Directly after input validation, the request queries a two-tier Redis cache:

Exact-match cache: For identical, repetitive queries.
Semantic cache: Computes an embedding of the query and checks for 95%+ cosine similarity against recently answered questions. If there's a cache hit, we return the cached response immediately—bypassing both vector search and LLM costs.
3. Retrieval with Fallback Logic
On a cache miss, the query moves to the retrieval pipeline:

Primary Search: Queries the vector database for relevant documentation.
Fallback Logic: If the vector database times out, fails, or returns relevance scores below our threshold, the system automatically falls back to a BM25 lexical keyword search or loads a verified static FAQ article to ensure the user is never left without context.
4. LLM Generation with Model Fallbacks
The context and user query are assembled into the prompt and sent to the LLM:

Model Fallback (Circuit Breaker): If the primary model experiences a rate limit (HTTP 429), timeout, or outage, a circuit breaker trips and automatically routes the request to a secondary fallback model (for instance, switching from Claude to GPT-4o-mini or a self-hosted vLLM instance). If that fails, it gracefully routes to a human agent escalation queue.
5. Output Guardrails (Pre-Response Validation)
Before streaming or returning the response to the user:

Hallucination & Faithfulness Check: Validates that factual claims in the answer are strictly supported by the retrieved context chunks.
Safety & Formatting: Ensures no sensitive internal instructions or toxicity are leaked.
6. Keeping Components Loosely Coupled
To swap models or vector databases without rewriting application code, I implement Hexagonal Architecture (Ports & Adapters) using the Strategy Pattern:




**When an LLM application produces incorrect, degraded, or failing responses in production, how would you diagnose the cause across retrieval, prompting, model, and infrastructure, and which mitigations would you apply?"**



"To systematically diagnose issues in a production AI system, I isolate the pipeline into four distinct layers using distributed tracing:

1. Retrieval Layer
   Diagnosis: I first inspect the retrieved context chunks using metrics like Context Recall and MRR (Mean Reciprocal Rank). I check if the relevant answer was actually fetched in the top-$K$, or if the vector search pulled irrelevant noise due to vocabulary mismatch or poor chunk boundaries.
   Mitigations:
   Implement Hybrid Search (combining dense vector search with BM25 sparse keyword matching) to catch exact acronyms and part numbers.
   Add a Cross-Encoder Reranker (such as Cohere or BGE) to filter down and re-order the top chunks before feeding them to the prompt.
   Switch to Parent-Child chunking so the model receives full context rather than arbitrary fragment cuts.
2. Prompting Layer
   Diagnosis: If the retrieved chunks contain the right information but the output is still incorrect, the issue is prompting. I check for the 'Lost in the Middle' phenomenon (where key facts buried in the middle of long context get ignored), prompt truncation, or conflicting system instructions.
   Mitigations:
   Reorder context so the highest-scoring chunks sit at the very beginning or end of the context window where LLM attention is strongest.
   Enforce strict grounding constraints: 'Answer strictly using the provided context. If the answer is not present, reply with: I do not know.'
   Add structured few-shot examples showing how to handle ambiguous queries.
3. Model Layer
   Diagnosis: I evaluate whether the model has the reasoning capacity for the query, and verify generation hyperparameters. A high temperature often causes factual hallucinations.
   Mitigations:
   Set temperature to 0.0 or 0.1 and top_p to 0.9 for deterministic, factual outputs.
   Use Model Routing: Route simple retrieval queries to a fast 8B/mini model, but route complex, multi-hop reasoning questions to a frontier model (like Claude 3.5 Sonnet or GPT-4o).
   Run Output Guardrails (like an automated hallucination check) before returning the response to the user.
4. Infrastructure Layer
   Diagnosis: If failures are manifested as high latency, dropped requests, or timeouts, I check OpenTelemetry traces to break down latency into Time-to-First-Token (TTFT) vs. Time-Per-Output-Token (TPOT). I check GPU VRAM utilization, KV-cache thrashing, and HTTP 429 rate-limiting spikes.
   Mitigations:
   Enable Prompt/Prefix Caching and Chunked Prefill in the serving engine (like vLLM) to prevent long prompts from blocking the queue.
   Implement Circuit Breakers with automated fallbacks to secondary backup model endpoints.
   Autoscale GPU replicas using KEDA triggered by active request queue depth (num_requests_waiting) rather than standard CPU/memory metrics."



**"If an LLM has access to external tools or internal data, how would you architect it to limit the blast radius of a prompt injection or security compromise, and how would you validate those defenses before launch?"**



1. Architecting to Limit the Blast Radius
   Principle of Least Privilege for Tools: Tools should never run under an admin credential. Each tool gets short-lived, scoped API tokens restricted to row-level or tenant-level permissions. For example, a support agent has read access to order status, but zero permissions to initiate database drops or refunds over $50.
   Human-in-the-Loop (HITL) for State Changes: Read-only actions (like searching FAQs or fetching balances) execute automatically. Any high-impact state change—such as modifying user data, transferring funds, or sending external emails—requires explicit user confirmation or an admin approval webhook before execution.
   Execution Sandboxing: If the LLM generates code or SQL queries, it executes inside an isolated, ephemeral sandbox—like Firecracker microVMs or Docker containers with network egress disabled and read-only file systems.
   Dual-LLM / Privilege Separation Architecture: We separate the Untrusted LLM (which parses raw user text and web data) from the Privileged Action Executor. The untrusted model cannot invoke tools directly; it can only propose structured JSON parameters to a strictly validated deterministic validator that checks business logic rules before execution.


**"Describe your process of turning production failures into regression tests, and how do you handle privacy and compliance when storing user queries and retrieved content?"**


1. Turning Production Failures into Regression Tests
   Detection & Capture: We automatically flag failures in production via telemetry—such as user thumbs-down feedback, output guardrail violations (e.g., low faithfulness scores), or human-agent overrides. Tools like Langfuse or LangSmith trace the exact request tuple: the user query, retrieved context chunks, system prompt version, and generated response.
   Curating Ground Truth: A subject matter expert or engineer reviews the failure, identifies the root cause (retrieval miss vs. model hallucination), and labels the ideal target answer or ground-truth context.
   Adding to the Regression Suite: We convert this failure into an automated evaluation case using frameworks like DeepEval or Ragas. We assert metrics like Context Precision, Faithfulness, and Answer Relevancy.
   CI/CD Quality Gate: This test case is permanently added to our golden evaluation dataset. In GitHub Actions, anytime an engineer updates a system prompt, swaps the embedding model, or modifies chunking logic, this regression suite runs automatically. If the accuracy on previously failed edge cases regresses below a threshold, the deployment is blocked.
2. Privacy & Compliance When Storing Queries & Content
   PII & PHI Redaction at Ingestion: Before any user query or retrieved document is written to long-term evaluation storage, it passes through an automated masking pipeline (using Microsoft Presidio or dedicated NER models) to scrub names, phone numbers, credit cards, and medical record numbers.
   Role-Based Access & Encryption: All logged interactions are encrypted at rest with AES-256 and in transit with TLS 1.3. Access to evaluation datasets is restricted via strict RBAC—only authorized ML engineers have access, and production audit logs track every data view.
   Data Minimization & Retention TTL: We enforce strict data retention policies (for example, a 30-to-90 day TTL). Raw logs automatically expire and are purged unless an anonymized sample is explicitly approved for long-term regression benchmarking.
   Compliance & Right to Erasure (GDPR / HIPAA / SOC2): User queries are mapped to anonymized, hashed customer identifiers so that if a customer exercises a GDPR 'Right to be Forgotten' request, we can immediately purge all their associated logs and traces across our test datasets."
3. 

**"As data volume grows and latency begins to degrade, which parts of the architecture would you scale or optimize, how would you trade recall against latency and memory, and how would you execute an embedding model upgrade without downtime?"**



1. Architectures to Scale and Optimize First
   Decouple Ingestion from Querying: Separate your write and read paths. We put heavy document processing, chunking, and embedding generation into an asynchronous message queue (like Kafka or RabbitMQ) so batch updates never impact real-time search latency.
   Vector DB Sharding & Read Replicas: Shard the vector database across nodes by tenant or time window, and deploy read-only replicas behind a load balancer to scale query throughput horizontally.
   Move from Exact to Approximate Search: If still using flat indexing, transition to graph-based ANN (Approximate Nearest Neighbors) indexing like HNSW (Hierarchical Navigable Small World).
2. Trading Recall Against Latency and Memory
   At high volumes, achieving 100% theoretical recall is cost-prohibitive. We make measured engineering trade-offs:

Vector Quantization (Scalar & Product Quantization): We apply Scalar Quantization (SQ8) or



**"What happens if the query embedding uses a different distance metric than the index was trained with, or if you forget to normalize vectors when using Inner Product for cosine similarity? How would you detect and fix this in production?"**



1. What Happens Mathematically
   The Normalization Trap: In vector databases and FAISS, Cosine Similarity is implemented as an Inner Product (Dot Product) because dot products are significantly faster to compute on GPUs and modern CPUs. However, dot product only equals cosine similarity if all vectors have unit length ($L_2$ norm = 1.0).
   Magnitude Bias: If you forget to normalize, the search is no longer measuring semantic angle—it measures vector magnitude. Long, verbose chunks with higher token counts often generate embeddings with larger magnitudes. As a result, the index returns long, irrelevant documents simply because their vector norms are large, completely corrupting search relevance.
   Metric Mismatch: If an index was trained using Euclidean distance ($L_2$) but queried using Inner Product (or vice versa), the ranking order is completely scrambled. Clusters optimized to minimize spatial distance will miscalculate nearest neighbors, degrading retrieval to near-random results.
2. How to Detect This in Production
   Anomaly Detection on Similarity Scores: In normalized cosine similarity, scores are bounded strictly between $-1.0$ and $+1.0$. If your production monitoring logs similarity scores of 15.4, 82.0, or unbounded numbers, vectors were never normalized.
   Ingestion Assertions (Unit Norm Check): We place automated validation checks in the ingestion pipeline verifying that:

   $$
   |v|_2 = \sqrt{\sum v_i^2} \approx 1.0 \pm 10^{-4}
   $$

   Any chunk failing this check throws an immediate ingestion error.
   Length Correlation Bias: If telemetry shows that the top-retrieved documents consistently correlate with document length rather than user query intent, it immediately flags a vector magnitude bug.
3. How to Fix It in Production
   Immediate In-Flight Patch (Query Side): Enforce strict normalization at the embedding client layer before any query hits the vector store:


**"In a single-model scenario with only two internal tools, what criteria and trade-offs would you evaluate to decide whether to adopt MCP (Model Context Protocol) or not?"**



1. Why Direct Function Calling Wins by Default (YAGNI)
   Operational Simplicity: Native function calling (defining tools directly in your code via Pydantic or JSON schemas) has zero extra infrastructure overhead.
   Latency & Failure Modes: Calling local Python functions or direct internal REST endpoints avoids the extra hop of running a dedicated MCP server process, handling JSON-RPC serialization, and managing inter-process communication timeouts.
   Maintainability: For just two tools, introducing a client-server protocol layer is classic premature optimization.
2. The Specific Criteria That WOULD Justify Adopting MCP
   I would flip the decision and adopt MCP only if one of these three conditions is met:

Multi-Client Reusability: If these two tools are not just for this one application, but need to be consumed by other agents, team members using Claude Desktop, Cursor, or different internal microservices, MCP acts as a universal API contract so you write the tool once and share it everywhere.
Security & Process Isolation: If the tools execute sensitive or high-risk tasks (like running SQL or system scripts), MCP enforces a strict client-server boundary. The tools can run in an isolated subprocess or container with sandboxed privileges, completely separated from the core application process.
Imminent Roadmap Expansion: If these two tools are just the first step in a roadmap that will quickly expand to dozens of enterprise data sources (like GitHub, Jira, PostgreSQL, or Slack), adopting MCP now establishes a plug-and-play architecture where we can leverage existing open-source MCP servers without writing custom wrappers.
Conclusion
In summary: If this is a self-contained, low-complexity service, we avoid the overhead and stick to native function calling. If we foresee multi-client consumption or rapid expansion to external systems, MCP provides immediate standardization and process-level security."



**"Walk through how an MCP tool ends up being called by a model. Where does function calling sit in that flow, and what does the MCP layer give you that a hardcoded tool list in your app would not?"**



1. The Step-by-Step Execution Flow
   Discovery (Handshake): At startup, the MCP Client (our host application) connects to an external MCP Server via stdio or HTTP/SSE, sending a tools/list JSON-RPC request. The MCP Server responds with available tools and their JSON schemas.
   Schema Translation to LLM: The MCP Client takes those schemas and passes them into the standard tools parameter of the model's API call (e.g., Anthropic or OpenAI format).
   Model Function Calling: The user asks a question. The LLM decides it needs a tool, producing a structured function call output (e.g., tool_use with the tool name and arguments).
   Execution via MCP: The MCP Client catches this function call and dispatches a tools/call JSON-RPC request to the external MCP Server. The server executes the tool (querying a database or running an API call) and returns the tool output.
   Final Synthesis: The MCP Client feeds the tool result back to the model as a tool_result message, and the model generates the final human-readable response.


**"In LoRA, walk through why matrix $B$ is initialized to zero and matrix $A$ randomly, what the scaling factor $\alpha$ (alpha) does, and what merging the adapter into the base weights buys you versus serving multiple dynamic adapters?"**


1. Why $B$ is Initialized to Zero and $A$ Randomly
   Preserving Pre-trained Knowledge at Step 0:
   At the very start of training, we want $\Delta W = 0$. Because $B$ is initialized entirely to zeros, the product $B \times A$ is strictly zero. This guarantees that before gradient descent begins, the model’s outputs are 100% identical to the original pre-trained base model—no random noise is introduced to disrupt pre-existing capabilities.
   Symmetry Breaking:
   If we initialized both $A$ and $B$ to zero, the gradients would remain symmetric and the network couldn't learn effectively. Initializing $A$ with a random Gaussian distribution breaks mathematical symmetry while $B=0$ keeps the initial update at zero.
2. What the Scaling Factor $\alpha$ (Alpha) Does
   In the update formula $\Delta W = \frac{\alpha}{r}(B \times A)$, $\alpha$ acts as a scaling and stabilization constant.
   Its primary purpose is to decouple the learning rate from the rank $r$. When you experiment with different ranks—say scaling up from $r=8$ to $r=64$—the scale of the weights naturally shifts. By dividing by $r$ and scaling by constant $\alpha$, the magnitude of the adapter's gradient updates remains stable, meaning you don't have to re-tune your learning rate every time you change the rank.
3. Merging into Base Weights vs. Serving Multiple Dynamic Adapters
   What Merging Buys You (merge_and_unload()):
   Merging mathematically adds $\Delta W$ directly into the base weights: $W_{new} = W_0 + \frac{\alpha}{r}(BA)$.
   Zero Inference Latency Overhead: During inference, the GPU performs a single matrix multiplication instead of two parallel branches ($xW_0 + xBA$). You eliminate kernel-launch switching and memory-bandwidth overhead.
   Simpler Serving: The merged model exports as standard SafeTensors, plug-and-play into high-performance engines like vLLM or TensorRT-LLM without custom LoRA kernels.



**"Suppose a product team wants personalized recommendations under 200 ms, but traffic is highly spiky and GPU costs are a concern. How would you architect the serving layer: what you would precompute versus compute on demand, how you would use caching, dynamic batching, and what failure modes you expect (cold starts, stale features, queue buildup) and how to degrade gracefully?"**



2. Caching & Dynamic Batching
   Tiered Caching:
   Redis Tier: Cache the final top-10 recommended item IDs for active users with a 15-minute sliding TTL. If a user revisits the page without new interactions, Redis returns the result in under 5 milliseconds with zero GPU cost.
   Dynamic Batching:
   We serve the reranker using Triton Inference Server. We configure dynamic batching with a max_queue_delay_microseconds of 10 to 15 ms. This groups bursty incoming queries into efficient matrix operations, maximizing GPU utilization without blowing our 200ms latency budget.
3. Expected Failure Modes & Graceful Degradation
   To handle spikes and cost limits, we plan for three failure modes:

Queue Buildup Under Traffic Spikes:
Degradation: If traffic bursts overwhelm the GPUs and queue wait times exceed 100ms, a circuit breaker trips: the system skips the neural reranker entirely and directly returns the unranked top candidates from the vector store or Redis. Latency drops back to 20ms immediately.
Cold Starts During Autoscaling:
Degradation: Spinning up new GPU nodes takes minutes. While new GPU pods initialize, autoscalers route overflow traffic to a fallback CPU pool running precomputed segment-level recommendations (e.g., 'Trending in Category').


**"How would the prefill/decode difference affect your choices around chunked prefill, or even disaggregating prefill and decode onto separate GPUs or nodes? What workload patterns would make those choices worthwhile?"**


2. Chunked Prefill (When & Why to Use It)
   How it works: Instead of evaluating a 4,000-token prompt in one massive burst, Chunked Prefill (native in vLLM) slices the prompt into smaller chunks (e.g., 512 tokens) and batches them alongside ongoing decode steps.
   Workload Fit: It is ideal for moderate-concurrency RAG and customer support chatbots running on single-node GPU setups. It smooths out decode latency spikes without requiring specialized inter-node network infrastructure.


* **How it works:** We physically separate the infrastructure into a **Prefill GPU pool** and a  **Decode GPU pool** , transferring the computed KV cache over high-speed networks (RDMA or NVLink).
  * Prefill nodes are configured with high Tensor Parallelism to maximize raw compute FLOPs.
  * Decode nodes maximize KV cache capacity and memory bandwidth.
* 

* **Workload Patterns That Make Disaggregation Worthwhile:**
  1. **Asymmetric Long-Context RAG (High Input, Short Output):** For workloads with 8,000+ input tokens (like legal document search or codebase QA) and short 200-token answers. In colocated serving, prefill dominates and starves decode. Disaggregating unlocks up to  **2x to 4x higher throughput** .
  2. **Real-Time Streaming & Voice Agents:** Conversational voice AI requires ultra-smooth, jitter-free streaming ($TPOT < 30\text{ ms}$). Disaggregation guarantees that new incoming callers never interrupt the audio streaming cadence of active callers.
  3. **Large-Scale Enterprise Fleets:** At massive scale, disaggregation allows heterogeneous hardware optimization—using compute-dense GPUs (like H100 SXM) for prefill, and cost-effective, high-memory GPUs (like L40S) for decode."


**"How would you diagnose whether a bad answer is caused by retrieval versus generation, and how would you structure the system so these two stages can be evaluated and improved independently?"**


#### . How to Diagnose: The 2-Step Inspection

We isolate the root cause by evaluating the retrieved context before looking at the generated text:

* **Retrieval Failure (Garbage In):**
  We inspect whether the ground-truth answer was actually present in the retrieved chunks. If the necessary facts are missing from the top-$K$ chunks, the retriever failed.
  * *Metrics to check:* Low **Context Recall** and low  **MRR (Mean Reciprocal Rank)** . The generator never had a chance because the context wasn't retrieved.
* **Generation Failure (Good In, Bad Out):**
  If the ground-truth answer **is** present in the retrieved chunks, but the model hallucinates, ignores the facts, or misinterprets them, the failure belongs strictly to generation.
  * *Metrics to check:* High Context Recall, but low **Faithfulness / Groundedness** (facts in the answer are not supported by the context) or low  **Answer Relevancy** .


**"What are the limitations of LLM-as-a-judge evaluation for RAG, how would you mitigate them, and how would you build and maintain a golden dataset when you have little to no labeled data at the start?"**



#### . Limitations of LLM-as-a-Judge

* **Verbosity Bias:** LLM judges consistently score longer, wordy answers higher than concise, accurate answers.
* **Position Bias:** In pairwise evaluations (comparing model A vs. model B), judges heavily favor whichever response is presented first.
* **Self-Enhancement Bias:** A model family (like GPT-4) tends to rate outputs generated by itself higher than outputs from Claude or open-source models.
* **Non-Determinism & Hallucination:** Without rigid constraints, judges hallucinate reasoning or give fluctuating numerical scores for the same input.


* **Strict Scoring Rubrics & CoT:** Never ask the judge to simply  *'Rate 1 to 5'* . Instead, define explicit criteria for each score (e.g.,  *'Score 5 = all facts present; Score 3 = 1 minor hallucination'* ). Force the judge to output **Chain-of-Thought reasoning first** before emitting the final score.
* **Position Swapping:** For pairwise comparisons, run the evaluation twice, swapping the order of Response A and Response B. If the judge contradicts itself, flag it as a tie or discard it.
* **Reference-Based Evaluation:** Rather than having the judge evaluate freely, feed it the  **ground-truth context and expected key facts** . This turns the task into objective fact-verification rather than subjective grading.


**"Two models have nearly identical ROC-AUC of 0.97 but very different PR-AUC on an imbalanced dataset. Explain why this can happen and how you would decide which model to deploy?"**



. Why This Happens Mathematically
The True Negative Dilution in ROC-AUC:
The ROC curve plots True Positive Rate against False Positive Rate.

$$
\text{FPR} = \frac{\text{False Positives}}{\text{False Positives} + \text{True Negatives}}$$ In a highly imbalanced dataset (like fraud detection or rare cancer screening where 99% of data is negative), the True Negatives ($TN$) count is massive. Even if a model makes thousands of False Positives, the enormous $TN$ denominator keeps the False Positive Rate deceptively tiny (e.g., $\text{FPR} < 0.02$). This causes the ROC curve to hug the top-left corner, giving both models an inflated ROC-AUC of 0.97.
Why PR-AUC Exposes the Difference:
$$\text{Precision} = \frac{\text{True Positives}}{\text{True Positives} + \text{False Positives}}$$ Precision does not include True Negatives at all—it directly punishes False Positives. If Model A produces 50 False Positives, its Precision might be 80%. If Model B produces 1,000 False Positives, its Precision collapses to 10%. Model A will have a high PR-AUC, while Model B will have a terrible PR-AUC, despite identical ROC-AUCs.
2. How to Decide Which Model to Deploy
In production, we never deploy an 'area under a curve'—we deploy a single operating threshold. Here is my decision framework:

Prioritize PR-AUC over ROC-AUC: On any imbalanced dataset, PR-AUC is the true north metric because it directly measures positive class accuracy.
Apply the Business Cost Matrix (Cost of FP vs. FN):
If a False Negative is catastrophic (e.g., missing fraudulent transactions or missed medical diagnosis), we set a high fixed recall target (say, 95% Recall) and pick whichever model achieves higher Precision at that specific operating point.
If a False Positive is expensive (e.g., manual fraud investigator review costs $20/case), we select the model with the higher PR-AUC to minimize investigator fatigue.
$$



> **"Using a concrete example such as spam filtering or disease detection, define the confusion matrix and show how a change in the decision threshold moves precision and recall in opposite directions. Why is it not enough to look at accuracy alone?"**




Spoken Answer (90–120 seconds, ready to speak orally):
"I’ll use the concrete example of Cancer Screening in healthcare:

1. Defining the Confusion Matrix
   In this scenario, a 'positive' test means the model predicts disease:

True Positive (TP): A sick patient correctly diagnosed as sick.
False Positive (FP): A healthy patient incorrectly flagged as sick (a false alarm).
True Negative (TN): A healthy patient correctly identified as healthy.
False Negative (FN): A sick patient incorrectly told they are healthy (a missed diagnosis—the most dangerous outcome).
2. How the Decision Threshold Moves Precision and Recall in Opposite Directions
A classification model outputs a probability from 0 to 1. Where we place the decision threshold directly forces a trade-off between Precision and Recall:

Lowering the Threshold (e.g., from 0.5 down to 0.2):
We make the model more aggressive. If there is even a 20% suspicion of cancer, we flag the patient.
We catch almost every sick person ($FN$ drops near zero), so Recall increases dramatically ($\uparrow$).
However, many healthy people get falsely flagged ($FP$ increases), so Precision decreases ($\downarrow$).
Raising the Threshold (e.g., from 0.5 up to 0.8):
The model must be 80% confident before flagging someone.
When it does flag cancer, it is almost certainly correct ($FP$ drops), so Precision increases ($\uparrow$).
But early-stage or borderline cases are missed ($FN$ increases), so Recall drops ($\downarrow$).



**"If a model's online accuracy suddenly drops while offline evaluation remains high, how would you investigate whether the architecture of the feature pipeline is at fault (training-serving skew), and what architectural changes would you make to prevent it from happening again?"**



1. Parity Check (Diffing Online vs. Offline Features):
   I take a sample of recent production requests, log the exact feature vectors generated at inference time, and pass those same raw requests through our offline training feature extraction pipeline. I run an automated vector diff. Any discrepancy in values, rounding, or null handling reveals a logic mismatch.
2. Statistical Drift Analysis (PSI & KL-Divergence):
   I compute the Population Stability Index (PSI) and Wasserstein Distance between the training feature distributions and the live production feature distributions. A PSI score greater than 0.25 immediately flags which specific features have diverged.
3. Auditing for Future Data Leakage:
   I check if the offline training query inadvertently used future information—such as computing a 30-day user spend average that included transactions occurring after the prediction timestamp.
4. Feature Staleness & Pipeline Lag:
   I verify the latency of our streaming pipeline (e.g., Kafka or Flink). If real-time feature updates are lagging behind, the online model is making predictions using stale or default-zero values while offline training had access to fully aggregated historical data.


**"How would you build a cost-optimized infrastructure plan for a team that has bursty experimentation workloads and a steady production inference workload? What capacity commitments would you make and what would you leave on-demand or spot?"**



* **Strategy:** For steady production inference, uptime and predictable latency are non-negotiable. We cannot risk node evictions.
* **Commitment Choice:** I analyze our minimum baseline traffic (the bottom 70–80% of our daily load) and purchase **1-year or 3-year Compute Savings Plans or Reserved Instances (RIs)** (AWS Savings Plans or GCP Committed Use Discounts).
* **Cost Impact:** This guarantees capacity during GPU shortages and slashes compute costs by **40% to 65%** compared to on-demand rates.
* **Hardware Rightsizing:** We avoid overpaying for top-tier training GPUs for inference. We reserve cost-effective, inference-optimized GPUs—like **NVIDIA L4 or A10G** instances (or 2x A100s for large 27B models)—running quantized models on vLLM.
