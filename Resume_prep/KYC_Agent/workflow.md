graph TD
    A([User Uploads KYC Payload]) --> B{Supervisor Agent}
    
    B -->|Routes Visuals| C[Image Parsing Agent]
    B -->|Routes Docs/Text| D[Document Parsing Agent]
    
    C -.->|Azure Vision| E(Structured JSON Data)
    D -.->|Form Recognizer| E(Structured JSON Data)
    
    E --> F[Validation Agent]
    
    F -.->|External API Call| G[(AML/Watchlist Screening)]
    G -.-> F
    
    F --> H{Confidence Check Node}
    
    H -->|Confidence HIGH| I[Update Database / Auto-Approve]
    H -->|Confidence LOW| J[Pause Graph State / HITL]
    
    J --> K([Manual Human Review])
    K -->|Human Decision| I
    K -->|Human Decision| L[Reject User]



    1. The Entry Point & The Supervisor (The Brain)
"The system is built on LangGraph using a multi-agent Supervisor pattern. When a user uploads a KYC payload (like an ID card photo and a selfie), it hits the Supervisor Agent first. The Supervisor acts as a traffic controller—it doesn't process the data itself, but it looks at the payload and decides which specialized 'worker' agent needs to handle which piece of data."


2. The Extraction Phase (Parallel Processing)
"The Supervisor spawns two specialized sub-agents based on the file types:

It sends visual assets (like the selfie for face-matching) to the Image Parsing Agent, which is powered under the hood by Azure Vision.

steps:
If OpenCV spots a poor-quality image, the Agent's state gracefully fails early and instantly prompts the user: 'Your ID is too blurry, please retake'—all without incurring any cloud compute costs. Once OpenCV approves the visual quality, it hands the payload over to the Azure Document Intelligence node for heavy-lifting data extraction."


1. The Core Concept
The Laplacian operator is a derivative operator used to find edges in an image.
Edges = High Change: In a sharp image, the transition from one pixel to the next at an edge is sudden (e.g., black to white).
Blur = Low Change: In a blurry image, edges are smeared, and transitions are gradual.
The Variance part simply measures the "spread" of these edge values.
High Variance: Lots of sharp edges (Sharp Image).
Low Variance: Very few edges or very soft edges (Blurry Image).

2. The Mathematical Logic
The Laplacian operator ($\nabla^2$) calculates the second-order derivative of the image intensity. In two dimensions (for an image $f$), it is defined as:
$$\nabla^2 f = \frac{\partial^2 f}{\partial x^2} + \frac{\partial^2 f}{\partial y^2}$$
Once you apply this operator to every pixel, you get a new "map" of the image highlighting the edges. You then calculate the Variance ($\sigma^2$) of all the pixels in this edge map.



3. A Real-World Example
Imagine you are building a document-scanning feature for the Kulu mobile money platform in Africa to verify user IDs.
The Scenario:
A user takes a photo of their National ID. Your pipeline needs to decide: Is this photo clear enough for OCR (Optical Character Recognition) to read the name?
Step 1: You convert the ID photo to grayscale.
Step 2: You convolve the image with a Laplacian kernel (usually a $3 \times 3$ matrix).
Step 3: You calculate the variance of the resulting pixels.
The Comparison:
Sharp Photo: The text on the ID has crisp edges. The Laplacian variance might be 1500.
Blurry Photo: The user moved their hand. The text is a grey smudge. The Laplacian variance might be 80.
The Automated Decision:
You set a Threshold (e.g., 500).
If Variance $> 500 \rightarrow$ Accept and send to the Data Warehouse.
If Variance $< 500 \rightarrow$ Reject and tell the user, "Please retake the photo; it's too blurry."
  



It sends the physical ID card to the Document Parsing Agent, which uses Azure Form Recognizer to extract text like Name, DOB, and ID number.


Both agents convert unstructured images and PDFs into a clean, structured JSON object and return it to the central graph."



3. The Validation Phase (External APIs)
"Once we have the clean JSON text, the state is passed to the Validation Agent. This agent's sole job is cross-referencing. It takes the extracted Name and ID and fires off external API calls to third-party AML (Anti-Money Laundering) and global watchlist databases. It compiles the API responses and calculates an overall 'Confidence Score' for the user."


"This is where the automation pays off. We programmed a conditional edge in LangGraph. If the Validation Agent calculates a High Confidence score (e.g., the face matches the ID, the text is clear, and the AML check passes), the agent triggers an SQL task to automatically update the company database and instantly approve the user. Pure zero-touch automation."


"However, if the photo is blurry or the AML check returns a partial match, the Confidence is Low. Instead of blindly failing the user, LangGraph uses its built-in memory capability to Pause the graph's state. It routes the specific ticket to a Human-In-The-Loop (HITL) queue. A human compliance officer reviews the paused ticket, clicks approve or deny, and LangGraph resumes the final step of updating the database."