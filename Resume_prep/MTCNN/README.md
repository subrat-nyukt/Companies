# Facial Recognition & Identity Verification System

This repository demonstrates a production-ready, real-time facial recognition and identity verification pipeline. It was developed to ensure secure user onboarding and real-time authentication by leveraging state-of-the-art Computer Vision models.

## 🧠 Architecture Overview

The system operates in a two-stage pipeline:

1. **Face Detection & Alignment (MTCNN)**
   * **Multi-task Cascaded Convolutional Networks (MTCNN)** is used to accurately detect faces in raw images, even under varying lighting conditions or slight occlusions.
   * Crucially, MTCNN extracts facial landmarks (eyes, nose, mouth) and aligns the face. This spatial normalization step is critical for ensuring the downstream feature extractor receives standardized inputs, maximizing accuracy.
2. **Feature Extraction & Verification (FaceNet)**
   * The aligned face is passed to **FaceNet (InceptionResnetV1)**, pretrained on the `vggface2` dataset.
   * FaceNet strips away background/lighting noise and projects the face into a **512-dimensional embedding space** using a Triplet Loss optimization strategy during its training phase. In this space, embeddings of the same identity are clustered closely together, while differing identities are pushed apart.
   * Identity verification is executed by calculating the **Cosine Distance** between a stored baseline embedding and a real-time live embedding.

## 🛠️ Tech Stack
* **Deep Learning Framework:** PyTorch (`facenet-pytorch` implementation)
* **Model Serving:** FastAPI / Uvicorn (ensuring asynchronous, low-latency API handling)
* **Image Processing:** OpenCV, Pillow, Numpy
* **Vector Storage:** Local File System (Numpy binaries) - *Note: In a high-scale production environment, this is seamlessly swapped for a Vector DB like Pinecone, Milvus, or pgvector.*

## 📂 Project Structure

```text
MTCNN/
├── data/
│   └── embeddings/          # Storage for registered user feature vectors (.npy)
├── src/
│   ├── core/
│   │   └── config.py        # Centralized configurations (Thresholds, Image Sizes, Device config)
│   ├── models/
│   │   ├── detector.py      # MTCNN wrapper logic
│   │   └── recognizer.py    # FaceNet wrapper logic
│   └── services/
│       └── verification.py  # Business logic combining models for registration and verification
├── main.py                  # FastAPI application exposing the REST API
├── requirements.txt         # Dependencies
└── README.md                # Documentation
```

## 🚀 How to Run (Local Development)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the FastAPI server:**
   ```bash
   python main.py
   # Or using uvicorn directly: uvicorn main:app --reload
   ```

3. **API Endpoints (Test via Swagger UI at `http://localhost:8000/docs`):**
   * `POST /api/v1/register`: Accepts a `user_id` and an image file. Generates and stores the 512D embedding.
   * `POST /api/v1/verify`: Accepts a `user_id` and a real-time capture image file. Compares the real-time embedding to the stored embedding using Cosine Similarity.

## 💡 Key Design Decisions & Interview Talking Points

* **Why MTCNN over Haar Cascades or Dlib?** MTCNN uses a cascade of three deep convolutional networks (P-Net, R-Net, O-Net), which provides far superior robustness to varying face scales, angles, and lighting compared to traditional machine learning methods. The built-in alignment (O-Net) directly boosts FaceNet's accuracy.
* **Why Cosine Distance over Euclidean?** Cosine distance measures the angle between vectors, ignoring magnitude. In high-dimensional spaces (512D), feature vectors can suffer from the "curse of dimensionality." Cosine distance is generally more robust for normalized embeddings compared to strict spatial Euclidean distance.
* **Production Optimization Strategies:**
  * Currently configured for `CPU` by default for accessibility, but `src/core/config.py` can be flipped to `cuda` for immediate GPU acceleration.
  * For handling millions of users, the local `.npy` storage should be replaced with an Approximate Nearest Neighbor (ANN) index (e.g., HNSW in Milvus/Pinecone) to achieve sub-millisecond retrieval.
  * In a real banking/fintech scenario, this pipeline would be preceded by an **Active or Passive Liveness Detection** module to prevent spoofing via photos or screens.
