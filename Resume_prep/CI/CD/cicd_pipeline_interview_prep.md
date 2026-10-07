# CI/CD Pipeline — Interview Preparation Guide

This guide breaks down the Continuous Integration and Continuous Deployment (CI/CD) pipeline. It is specifically framed to answer questions from the perspective of a technical leader or CTO (like Mukesh Soni), who cares deeply about business metrics: **Auditability, Scale (400k users), Consistency, Speed-to-Market, and Revenue Protection ($8M MRR).**

---

## 🏗️ The Pipeline Stages at a Glance

| Stage | Developer Action | Technical Mechanism | Why Leadership Cares |
|-------|-----------------|---------------------|----------------------|
| **1. Commit** | Developer saves code | Git / GitHub Version Control | **Auditability:** Complete version history. We know exactly who changed what and when. |
| **2. Test** | Push triggers automation | CI Server (GitHub Actions/Jenkins) runs 100+ automated tests | **Quality Control:** Prevents regressions and bugs from reaching our 400k active users. |
| **3. Build** | Code passes tests | Code is packaged into a Docker Container image | **Consistency:** Eliminates "it works on my machine." It runs identically on every server. |
| **4. Deploy** | Image is distributed | Kubernetes / Cloud orchestration deploys to UAE/Africa servers | **Speed-to-Market:** Allows us to ship new features to global markets safely and rapidly. |
| **5. Monitor** | Code is live | APM tools (Datadog/New Relic) track crashes and latency | **Revenue Protection:** Detects anomalies instantly to protect the $8M MRR from downtime. |

---

## 🎯 Strategic Interview Questions & Answers

### Q1: "Explain our code deployment process. How do we ensure that a single developer's mistake doesn't bring down the platform for our 400k users?"
**How to Answer (Focus on Commit & Test):**
> "We rely on a strict CI/CD philosophy. When a developer **Commits** code, it isn't deployed right away. It's pushed to a version control branch which triggers our **Test** stage. Our CI server automatically runs hundreds of unit and integration tests against that specific commit. 
> 
> By keeping a strict version history, we maintain 100% auditability. More importantly, this automated testing barrier is our primary shield—it catches bugs in an isolated environment before they ever have the chance to impact our 400,000 users in production."

### Q2: "We're expanding into new markets (UAE, Africa) and need to move fast. But historically, deployments have been messy with environmental differences. How does your pipeline fix this?"
**How to Answer (Focus on Build & Deploy):**
> "The solution to environmental deployment issues is our **Build** stage. Once code passes testing, the pipeline automatically packages the application and its exact dependencies into a standalone Docker Container. 
> 
> This guarantees perfect consistency. The container behaves exactly the same on a developer's laptop as it does on our production servers in the UAE or Africa. During the **Deploy** stage, our orchestrator simply spins up these identical containers across our global regions. This eliminates 'it worked on my machine' errors and drastically increases our speed-to-market for new features globally."

### Q3: "Our platform generates $8M MRR. Downtime is incredibly expensive. Post-deployment, how are we protecting that revenue?"
**How to Answer (Focus on Monitor):**
> "Deploying the code isn't the final step; the **Monitor** stage is. The moment a new container goes live, our Application Performance Monitoring (APM) tools begin tracking it for high latency, memory leaks, or crash loops.
> 
> If the deployment negatively impacts backend performance, our observability stack triggers immediate alerts. Because our deployment pipeline is containerized and version-controlled, we can trigger an automated rollback to the previous stable state within minutes. This rapid detection and remediation process is specifically designed to protect our $8M MRR from extended downtime."

---

## 🔬 Deep Dive: The Test Stage (Real-World KYC Example)

If the interviewer asks: **"Explain exactly how the automated Test stage works in reality. What happens under the hood when a developer pushes code?"**

Here is exactly how you map this to your **KYC Agent Architecture**:

### The Scenario
Imagine your team wants to update the `VALIDATION_PROMPT` in `agent_prompt.py` to better handle reflections on plastic ID sleeves. A Data Scientist makes the prompt change and **Commits/Pushes** the code to GitHub.

### Step-by-Step Execution (The CI Server)
The moment the code hits the remote repository, **GitHub Actions** (the CI Server) detects the push and automatically spins up a clean, temporary, headless Virtual Machine (a "Runner"). 

This Runner pulls your new code and executes your **Automated Test Suite**. For an AI engineering pipeline like your KYC Agent, these tests fall into three categories:

1. **Unit Tests (Core Code Logic):**
   * *Example:* The CI server runs a fake payload through `kyc_graph.py`'s `supervisor` node to ensure it still correctly routes an image to the `image_parser` and a PDF to the `doc_parser`. It proves the basic Python state definitions (`KYCState`) haven't been broken.

2. **Integration Tests (System Connections):**
   * *Example:* The CI server tests the connection between the `validator` node and the `tools/aml_screening.py` function. It sends a mock name ("Osama Bin Laden") and asserts that the system correctly forces the confidence score to `0.0` and flags `HITL_REVIEW` before finishing the graph execution.

3. **LLM Evaluations (The "Golden Set" Validation):**
   * *Example:* You have a stored dataset of 50 difficult ID images (expired, extreme glare, foreign languages). The CI pipeline runs your *new* prompt against these 50 images using Azure's GPT-4o API. It asserts that the new prompt doesn't accidentally drop the confidence threshold below `0.72` for acceptable IDs, or falsely approve bad ones.

### The Mechanism of Protection (Why it matters to Mukesh)
* **If it PASSES:** The CI server reports a "Green" status. The code is confidently merged and handed off to the **Build** stage (Dockerization).
* **If it FAILS:** If your new prompt accidentally causes the model to ignore the AML tool, the Integration Test fails. The CI server triggers a "Red" alert, automatically **blocking the deployment.** 

**The Business Pitch:** *"By automating these tests—specifically our LLM evaluations against edge-case IDs—our pipeline acts as an impermeable shield. It entirely removes human error from the release process, ensuring that a bad prompt update can't accidentally fast-track fraudulent users or cause a compliance breach for our 400k user base."*

---

## 🔑 Key Vocabulary to Use in the Interview
* **Immutable Artifacts:** (Referring to Docker containers) — "We don't change code on live servers; we replace the whole container. It's immutable."
* **Shift-Left Testing:** "We catch bugs early in the pipeline during the automated 'Test' phase, rather than fixing them in production."
* **Zero-Downtime Deployment:** "Using our deployment pipeline, we can route traffic to the new containers gradually, meaning users never experience a maintenance outage."
