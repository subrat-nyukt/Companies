# Interview Preparation: Facial Recognition (MTCNN + FaceNet)

This project is a high-signal topic for a Lead ML Engineer role because it combines **Deep Learning**, **Real-time Engineering**, and **Security (Biometrics)**.

---

## 1. Architectural & Pipeline Questions
*   **"Walk us through the end-to-end pipeline."**
    *   *Answer Flow*: Image Capture -> MTCNN (Detection/Alignment) -> FaceNet (Embedding Generation) -> Vector Database (L2/Cosine Similarity Search) -> Thresholding -> Identity Result.
*   **"Why MTCNN for detection instead of YOLO or SSD?"**
    *   *Lead Answer*: MTCNN is specifically optimized for faces; it provides **facial landmarks** (eyes, nose, mouth corners) which are critical for **alignment** (warping the face to a standard frontal view) before feeding it to FaceNet.
*   **"How do you handle the 'Cold Start' problem for new users?"**
    *   *Answer*: During onboarding, we capture 3-5 images, generate embeddings, and store them in a vector index (like Faiss or Pinecone). Identity verification is then a 1-to-1 or 1-to-N search against this index.

---

## 2. Deep Learning Specifics (FaceNet)
*   **"Explain the Triplet Loss function used in FaceNet."**
    *   *Lead Answer*: It minimizes the distance between an **Anchor** and a **Positive** (same person) while maximizing the distance between the Anchor and a **Negative** (different person). $L = [||f(x^a) - f(x^p)||^2 - ||f(x^a) - f(x^n)||^2 + \alpha]_+$.
*   **"What is the dimensionality of the embeddings you used, and why?"**
    *   *Answer*: Typically 128 or 512 dimensions. Higher dimensions capture more detail but increase search latency and storage.

---

## 3. Real-Time & Lead Engineering
*   **"How did you achieve 'Real-Time' performance? MTCNN can be slow."**
    *   *Optimization Techniques*: 
        1.  **Resolution Downscaling**: Detection on a lower-res version of the frame.
        2.  **Tracking vs. Detection**: Detect every 5th frame; use KCF or MOSSE tracking in between.
        3.  **Quantization**: Converting the FaceNet model to INT8/FP16 for mobile/edge deployment.
*   **"How do you handle varying lighting conditions or occlusions (masks/glasses)?"**
    *   *Answer*: Data augmentation during training (if fine-tuning) and using **Pre-processing (Histogram Equalization)** to normalize lighting.

---

## 4. Security & Biometric Integrity (CRITICAL)
*   **"How do you prevent 'Presentation Attacks' (someone holding up a photo or video)?"**
    *   *Key Concept*: **Liveness Detection**.
    *   *Techniques*: 
        1.  **Challenge-Response**: "Blink your eyes" or "Turn your head."
        2.  **Texture Analysis**: Using a secondary CNN to detect "moiré patterns" or "screen edges" that indicate a photo of a screen.
        3.  **Depth Sensing**: Using IR or Structured Light (if hardware allows).
*   **"What threshold did you choose for identity verification? How did you balance FAR vs. FRR?"**
    *   *Definitions*: 
        - **FAR (False Acceptance Rate)**: A stranger gets in (Security risk).
        - **FRR (False Rejection Rate)**: A valid user is blocked (UX friction).
    *   *Lead Answer*: "In fintech onboarding, we prioritize a **low FAR**. We used an ROC curve to pick a threshold where FAR < 0.001%, accepting a slightly higher FRR which we mitigated with a manual review fallback."

---

## 5. Production & Scaling
*   **"How would you scale this to 1 Million users? You can't compare embeddings linearly."**
    *   *Answer*: Use **Approximate Nearest Neighbors (ANN)** like HNSW or IVF-PQ (indexing libraries like **Faiss**). This reduces search time from $O(N)$ to $O(\log N)$.
*   **"How do you monitor for 'Model Bias' across different ethnicities?"**
    *   *Answer*: We perform **Slicing Analysis**. We evaluate FRR/FAR across different demographic slices to ensure the model performs equitably, which is a key part of **Responsible AI**.

---

## 💡 Lead Narratives to Use:
*   *"I didn't just build the model; I designed the **liveness detection** layer to ensure we weren't vulnerable to simple photo-spoofing attacks."*
*   *"I implemented **embedding versioning**. When we upgraded from FaceNet to a newer architecture, I managed the re-indexing of our 100k+ user database without downtime."*
