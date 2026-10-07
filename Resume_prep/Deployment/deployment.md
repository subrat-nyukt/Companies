When you configured Azure OpenAl for production, how did you manage the tokens-per-minute or requests-
per-minute quota to ensure the system could handle peak load without hitting throttling limits?




### 1. Edge Pre-Filtering & Local Quality Gates (OpenCV)

Before calling any cloud APIs (Azure Document Intelligence or Azure OpenAI), we implemented a local quality gate using **OpenCV** to check for image blur (via Laplacian variance) and over/underexposure.

* **Why this saves quota:** If a user uploads a blurry or dark ID photo, the OpenCV pre-processor fails it *locally* at the server edge and immediately requests a retake from the user.
* **Impact:** This prevents forwarding bad images to the downstream Azure Vision or GPT-4o Vision fallback nodes, saving valuable TPM/RPM capacity and cloud compute costs on requests that are doomed to fail anyway.

### 2. Multi-Region Active-Active Load Balancing (Azure API Management - APIM)

Since a single Azure OpenAI resource is bound by strict regional TPM/RPM quotas, we deployed Azure OpenAI service instances across multiple geographic regions (e.g., East US, West US 2, North Europe).

* **Load Balancing Layer:** We placed these deployments behind **Azure API Management (APIM)** acting as an API gateway.
* **Smart Failover:** APIM was configured with a custom policy to track rate-limiting response headers (`x-ratelimit-remaining-tokens`, `x-ratelimit-remaining-requests`) and intercept `HTTP 429` (Too Many Requests) errors. If a region got throttled during a peak load event, APIM automatically rerouted the request to the next available region instance in milliseconds.

### 3. Queue-Based Backpressure Control (Decoupling)

KYC onboarding is asynchronous by design. We decoupled the document submission endpoint from the processing engine using a message queue (e.g., Celery/Redis).

* **Controlled Consumption:** Workers pull documents from the queue at a throttled rate that matches our global Azure OpenAI rate limits.
* **Peak Load Smoothing:** During a registration burst, the queue absorbs the shock wave and processes user documents in a steady stream rather than flooding Azure OpenAI simultaneously, ensuring we stay within our RPM envelope.

### 4. Exponential Backoff with Random Jitter

At the code level (e.g., when initializing the `AsyncAzureOpenAI` client), we wrapped LLM calls with retry logic using **exponential backoff with randomized jitter** (configured via libraries like `tenacity`).

* **Implementation:** If a `429` error is received despite the APIM load balancer, the worker pauses and retries (e.g., waiting $2s \rightarrow 4s \rightarrow 8s$) with a small random time delta added.
* **Why Jitter matters:** Adding random jitter prevents all throttled workers from hitting the API again at the exact same sub-second interval (the "thundering herd" problem), which would cause immediate re-throttling.

### 5. Circuit Breakers and Human-in-the-Loop (HITL) Fallback

As designed in ![](vscode-file://vscode-app/c:/Users/DELL/AppData/Local/Programs/Antigravity/resources/app/extensions/theme-symbols/src/icons/files/python.svg)

kyc_graph_A2A.py, the image/document parser and validation nodes are protected by **Circuit Breakers** wrapped in timeouts (e.g., `asyncio.wait_for(..., timeout=15.0)`).

* **Graceful Degradation:** If the Azure APIs are completely overloaded and exhaust their retries, the circuit breaker trips.
* **State Preservation:** Instead of crashing the onboarding process and losing state, LangGraph pauses the execution and transitions the transaction payload to an **Operator Queue** for human compliance officers (HITL) to review.

### 6. Token Footprint Optimization

We minimized the tokens processed per request to stretch our TPM quota further:

* **JSON Extraction Fallback:** Clean documents go through Azure Form Recognizer first, and only the structured JSON text is sent to GPT-4o for validation (approx. 1,370 input tokens per user). We only route to the highly expensive GPT-4o Vision model (approx. 2,170 input tokens) as a fallback if document extraction confidence falls below 0.50 (historically ~10% of users).
* **System Prompt Layout:** We structured the `SYSTEM_PROMPT` to support  **Azure OpenAI Prompt Caching** , ensuring that static system prompts and schema definitions are cached, resulting in significantly lower latency and reduced active token consumption.
