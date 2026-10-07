# KYC Agent with Model Context Protocol (MCP)

This folder demonstrates a modern architectural approach to building the KYC platform using the **Model Context Protocol (MCP)**. 

## Traditional vs. MCP Architecture

In a standard LangGraph/LangChain application, your agent logic (prompts, state graph) and your tool logic (API calls, python scripts, DB connections) live inside the exact same codebase and execute in the same runtime.

**With MCP**, you split the system into two components:
1. **The MCP Server (`mcp_server.py`)**: Exposes your KYC capabilities (OCR, Sanction APIs, Face matching) as secure, standardized tools over `stdio` or `SSE`.
2. **The Client/Agent (`client.py`)**: An LLM agent (which can be a LangGraph agent, an OpenAI swarm agent, or simply the Claude Desktop App) that connects to the server, queries what tools exist, and uses them.

### Why use MCP for the KYC Pipeline?

In an enterprise interview context, transitioning to MCP provides massive design architecture benefits:

1. **Security & Data Isolation**: The tools that touch sensitive PII or securely route to databases (AML/PEP hits) live strictly inside the Server. The client agent never sees API keys, database credentials, or complex execution logic.
2. **Framework Agnostic**: If you write your KYC Agent in LangGraph today, but your company pivots to AutoGen or plain OpenAI Agents tomorrow, you don't rewrite your tools. Any MCP-compliant client can instantly attach to the server.
3. **Bring Your Own UI**: You could configure Claude Desktop or a Cursor AI editor to connect to your local `KYC MCP Server` and test your KYC tools via pure natural language chatting without writing any front-end.
4. **Independent Scaling**: The KYC MCP Server can be hosted independently, load-balanced, and version-controlled completely separately from the LLM routing logic.

## Files
* `kyc_logic.py`: The underlying enterprise functions (OCR, AML checks).
* `mcp_server.py`: Wraps standard logic using `FastMCP` to serve tools.
* `client.py`: An example of how an Agent requests tools to be run.
* `requirements.txt`: Python package dependencies.

## Standard Setup
```bash
pip install -r requirements.txt
python client.py
```



## Why MCP is Important (REST API vs. MCP Server)

In enterprise AI integration, understanding the boundary between traditional **REST APIs** and **MCP Servers** is a critical design pattern.

```
┌────────────────────────────────────────────────────────┐
│                      Client Agent                      │
│             (LangGraph, Claude Desktop, etc.)          │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ (Model Context Protocol)
                            ▼
┌────────────────────────────────────────────────────────┐
│                   KYC MCP Server                       │
│    - Defines Tool Schemas                              │
│    - Handles Security & Permission Checks              │
│    - Standardizes Request/Response Protocol            │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ (Internal Network/Secure SDKs)
                            ▼
┌────────────────────────────────────────────────────────┐
│             REST APIs & Core Business Logic            │
│       (OCR Engines, AML Databases, Liveness Check)     │
└────────────────────────────────────────────────────────┘
```

---

## 💼 Recruiter Interview Q&A: REST APIs vs. MCP

Based on industry transition trends from conventional web applications to AI-powered systems, here are key architectural questions you may be asked in interviews, paired with professional responses.

### ❓ Q1: "Why do we need MCP servers or tools? Can't we just directly integrate our REST APIs with the LLM?"

**Answer:**
Direct LLM-to-API integration (where the model creates direct HTTP requests or generates raw backend payload parameters) works fine for quick Proof of Concepts (POCs), but fails in enterprise production. 

* **REST APIs are your business backbone:** They are designed for machine-to-machine communication, expecting strict schemas, raw tokens, and handling direct business actions.
* **MCP is the controlled, LLM-friendly layer:** It acts as a secure, structured mediator. Instead of exposing raw database queries or REST endpoints directly to the LLM, MCP abstracts the capability into a safe interface that standardizes how the AI queries, reads, and writes data.
* **The Analogy:** Direct API integration is like letting a new employee walk straight into the operations room and touch production systems just because they can "talk well." MCP is like giving them a **supervised service desk** containing:
  * Defined request forms
  * Permission checks
  * Execution rules
  * Controlled access to underlying systems

*Same business systems underneath. Safer interface on top.*

---

### ❓ Q2: "What specific guardrails does MCP provide that direct REST API calling lacks?"

**Answer:**
Direct API calling requires the agent's runtime environment to hold credentials, construct raw JSON payloads, and manage raw server responses. MCP mitigates this with three main guardrails:

1. **Secret & Credential Isolation:** The client agent (`client.py`) never sees database strings, AWS credentials, or API keys. Those are held securely inside the MCP Server (`mcp_server.py`). The client only requests a tool; the server performs the request securely.
2. **Validation & Sandboxing:** The MCP server acts as an API gatekeeper. If the LLM generates a tool payload with unexpected or unsafe parameters (e.g., trying to run an AML search for an invalid entity or trying to access another customer's ID document path), the server validates and rejects the arguments before hitting the downstream production database.
3. **Execution Control:** In direct integrations, an LLM in a planning loop can hallucinate recursive network calls, causing massive API bills or rate-limiting bans. An MCP server can throttle, audit, and intercept requests before they affect external APIs.

---

### ❓ Q3: "How does MCP simplify API evolution and versioning in AI systems?"

**Answer:**
If an LLM is directly integrated with a REST API, any changes to the API schema (such as changing `first_name` to `given_name` or updating the auth header format) require updating prompt templates, system instructions, and tool calling schemas.

With MCP, we achieve **separation of concerns**:
* The LLM agent only interacts with stable, high-level tools (e.g., `screen_user_aml`).
* If the underlying PEP/Sanction screening provider is changed or their REST API upgrades from v1 to v2, you only update the server implementation (`kyc_logic.py`). The tool schema exposed to the LLM client remains completely unchanged. The system continues to function without retraining or reprompting the agent.

---

### ❓ Q4: "In our KYC pipeline (ID extraction, AML checks, liveness checks), why is this architecture critical?"

**Answer:**
KYC handles highly sensitive PII (Personally Identifiable Information) subject to strict regulatory compliance (GDPR, HIPAA, CCPA).
* **Data Minimization:** Instead of dumping raw database rows or full API response payloads to the LLM, the MCP server parses the API response and returns a cleaned, structured summary containing only what the LLM needs to make its next decision.
* **Audit Trails:** Because all tool executions route through the MCP layer, you get a clean, standardized log of every action the AI took, the exact parameters it passed, and the outputs it received—critical for audit compliance.