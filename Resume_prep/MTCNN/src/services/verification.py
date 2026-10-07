import os
import numpy as np
from typing import Tuple, Optional, Dict

from src.models.detector import FaceDetector
from src.models.recognizer import FaceRecognizer
from src.core.config import settings

class VerificationService:
    def __init__(self):
        self.detector = FaceDetector()
        self.recognizer = FaceRecognizer()
        self.storage_dir = settings.EMBEDDING_STORAGE_DIR

    def _get_embedding_path(self, user_id: str) -> str:
        return os.path.join(self.storage_dir, f"{user_id}.npy")

    def register_user(self, user_id: str, image_bytes: bytes) -> Dict[str, any]:
        """
        Process an image, extract facial features, and save the embedding.
        This represents the "secure onboarding" phase.
        """
        # 1. Detect and align face
        face_tensor = self.detector.detect_and_align(image_bytes)
        
        if face_tensor is None:
            return {"status": "error", "message": "No face detected in the image. Please ensure good lighting and look directly at the camera."}

        # 2. Generate embedding
        embedding = self.recognizer.get_embedding(face_tensor)
        
        # 3. Store embedding (Simulating a Vector DB)
        save_path = self._get_embedding_path(user_id)
        np.save(save_path, embedding)
        
        return {
            "status": "success", 
            "message": f"User {user_id} registered successfully.",
            "embedding_shape": embedding.shape
        }

    def verify_user(self, user_id: str, image_bytes: bytes) -> Dict[str, any]:
        """
        Process a real-time capture and compare against stored identity.
        This represents the "real-time detection and high-accuracy identity verification" phase.
        """
        # 1. Check if user exists
        stored_path = self._get_embedding_path(user_id)
        if not os.path.exists(stored_path):
            return {"status": "error", "message": "User not found in the system."}

        # 2. Detect and align incoming face
        face_tensor = self.detector.detect_and_align(image_bytes)
        if face_tensor is None:
            return {"status": "error", "message": "No face detected in the live image."}

        # 3. Generate live embedding
        live_embedding = self.recognizer.get_embedding(face_tensor)
        
        # 4. Load stored embedding
        stored_embedding = np.load(stored_path)
        
        # 5. Compute distance
        distance = self.recognizer.compute_distance(live_embedding, stored_embedding, metric='cosine')
        
        # 6. Verification decision
        is_verified = bool(distance < settings.SIMILARITY_THRESHOLD)
        
        return {
            "status": "success",
            "is_verified": is_verified,
            "distance": float(distance),
            "threshold": settings.SIMILARITY_THRESHOLD,
            "message": "Identity verified successfully." if is_verified else "Identity verification failed. Faces do not match."
        }
