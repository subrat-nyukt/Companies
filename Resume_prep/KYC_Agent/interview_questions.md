# KYC Agent Interview Questions & Prep Guide

Based on the resume bullet point:

> *"Designed and deployed an AI-driven KYC agent using LangGraph (Chain-of-Thought) and Azure Document Intelligence with Computer Vision(OpenCV), automating user onboarding and reducing manual processing time by 60% & maintaining regulatory compliance."*

Interviewers will be extremely interested in this point because it touches on **Agentic AI, Cloud Vision APIs, localized computer vision, and high-stakes compliance**. Expect questions categorized into these four buckets:

---

## 1. System Architecture & Agent Design (LangGraph)

**Q: Walk me through the architecture of the KYC agent. Why did you choose LangGraph instead of a simpler sequential pipeline?**

* **What they want to know:** Do you understand stateful, cyclic graphs vs simple DAGs?
* **How to answer:** Explain that KYC is inherently cyclic. A user uploads an ID; it might be blurry. A simple pipeline fails and stops. LangGraph allows you to build a state machine with a "Human-in-the-loop" or "Feedback-loop" state. *Example: If Azure says "Confidence Score < 80%", the LangGraph state loops back to the user asking for a clearer photo before proceeding to the Face Match step.*

**Q: How did you implement "Chain-of-Thought" in this specific agent?**

* **What they want to know:** CoT is often a buzzword. How did it practically help the KYC logic?
* **How to answer:** CoT was used for the "Decision Engine" node. Instead of just outputting "Approved/Rejected", the LLM was prompted to explicitly reason: *"Step 1: Does the Azure extracted name match the database name? Yes. Step 2: Does the OpenCV blur-detection pass? Yes. Step 3: Is the document expired? Document expires in 2028, so No. Conclusion: Approve."* This chain is logged for regulatory auditing.

**Q: How did you manage the "State" in LangGraph as the onboarding process progressed?**

* **What they want to know:** Technical depth on LangGraph's `StateGraph`.
* **How to answer:** Mention that you defined a Pydantic state object containing memory (uploaded file references, extracted text payload, error messages, and a retry counter). State was updated as the payload passed between the Extraction Node, Verification Node, and Decision Node.

---

## 2. OCR and Vision (Azure Document Intelligence & OpenCV)

**Q: You mentioned both Azure Document Intelligence and OpenCV. Why did you need both? What did OpenCV do that Azure couldn't?**

* **What they want to know:** Did you just call an API, or do you understand image processing pipelines?
* **How to answer:** Azure Document Intelligence was used as the heavy lifter for OCR (Optical Character Recognition) and extracting structured key-value pairs (Name: X, DOB: Y) from Driver's Licenses/Passports. **OpenCV** was used as a *pre-processing gatekeeper local to your server*. Before paying for the Azure API call, OpenCV checks if the image is too blurry (Laplacian variance) or completely dark/overexposed. If OpenCV fails the image, the agent instantly asks the user for a new photo, saving API costs and latency.

**Q: How did you handle edge cases, like glare on the ID card or rotated images?**

* **What they want to know:** Real-world computer vision troubleshooting.
* **How to answer:** Azure usually handles rotation internally, but OpenCV can be used for glare detection (checking for severe light spikes in the greyscale histogram mask) or edge detection to crop the document out of a messy background before sending it to Azure.

---

## 3. Business Impact & Optimization

**Q: You stated you reduced manual processing time by 60%. How did you measure this, and why wasn't it 100%?**

* **What they want to know:** Do you understand the real-world limitation of AI in finance?
* **How to answer:** Say that in KYC/Compliance, AI should never operate at 100% autonomy due to FATF (Financial Action Task Force) or local banking regulations. You configured the agent to "Auto-Approve" only if confidence scores were > 95% across all checks. The remaining 40% (edge cases, blurry photos, mismatched names like "Mike" vs "Michael") were routed to a human dashboard with the LangGraph *reasoning trace* attached, so the human only took 1 minute to review instead of 5 minutes.

**Q: If your Azure API went down, how did your system handle it?**

* **What they want to know:** Reliability and fault tolerance.
* **How to answer:** LangGraph supports fallbacks. If Azure throws a 503 error, the node tries an exponential backoff. If it still fails, the state transitions to an "Operator Queue" rather than failing the user onboarding process completely.

---

## 4. Security & Compliance

**Q: Handling passports and IDs means handling PII (Personally Identifiable Information). How did you ensure data privacy in this architecture?**

* **What they want to know:** Security maturity.
* **How to answer:**
  1. Images were never logged in the LLM prompts directly; only the extracted text.
  2. The LLM used was an isolated, private Azure OpenAI instance (no data used for retraining).
  3. Azure Document Intelligence was configured to not store data at rest.
  4. Images processed by OpenCV locally were processed strictly in-memory (bytes buffer) and not written to disk.

**Q: How do you prove to an auditor why your AI rejected a specific user?**

* **What they want to know:** Explainability in AI (XAI).
* **How to answer:** This is exactly why the Chain-of-Thought architecture was implemented. Every decision node outputs a JSON schema detailing the exact Boolean gates that failed (e.g., `fail_reason: "DOB delta > 0"`). These LangGraph traces are stored persistently in a database for audit logs.



### Part 2: How Image Tagging in Azure Increases Performance

"Performance" in a KYC visual pipeline translates to **OCR accuracy (reducing incorrect rejections)** and  **classification speed (reducing downstream API costs)** . In Azure, there are two distinct workflows for tagging/labeling images to train specialized models that outperform generic APIs.

---

#### Workflow A: Azure Document Intelligence Custom Extraction (Form Recognizer)

If your KYC pipeline must handle non-standard documents (like local utility bills, rent agreements, or regional ID cards) where the pre-built models fail, you train a  **Custom Extraction Model** . You tag bounding boxes around specific fields on sample images.

##### **Step-by-Step Process in Azure:**

1. **Set Up Azure Resources** :

* Create an **Azure AI Document Intelligence** resource in the Azure Portal.
* Create an **Azure Storage Account (Blob Storage)** and upload a container containing 10–50 sample images of the target document type. Enable CORS (Cross-Origin Resource Sharing) on the storage account.

1. **Open Document Intelligence Studio** :

* Go to [Document Intelligence Studio](https://documentintelligence.ai.azure.com/).
* Select **Custom extraction model** and click  **Create a project** .
* Link it to your Azure subscription and your blob storage container.

1. **Define the Schema (Fields)** :

* Create the tags representing target fields you want to extract: e.g., `FullName`, `DocumentID`, `Address`, `IssueDate`.

1. **Label/Tag the Document Images** :

* Open the uploaded documents in the Studio interface.
* Draw bounding boxes around the text in the document image or select the recognized OCR lines.
* Assign each selection to a schema tag (e.g., highlight the user's address on a utility bill and tag it as `Address`).
* *Tip:* For best performance, label at least 5 documents per distinct layout.

1. **Train the Model** :

* Click  **Train** .
* Select **Custom Neural** (deep-learning based, highly recommended for varying layouts and unstructured documents) or **Custom Template** (for static forms).

1. **Evaluate and Integrate** :

* Check the resulting training metrics (Precision, Recall, F1-Score).
* Publish the model and capture the `model_id`.
* Call the model from your ![](vscode-file://vscode-app/c:/Users/DELL/AppData/Local/Programs/Antigravity/resources/app/extensions/theme-symbols/src/icons/files/python.svg)

  vision/analysis.py client SDK:

