import torch
from facenet_pytorch import InceptionResnetV1
import numpy as np

from src.core.config import settings

class FaceRecognizer:
    def __init__(self):
        """
        Initialize the FaceNet model (InceptionResnetV1) for generating facial embeddings.
        Pre-trained on VGGFace2 dataset, which performs well for identity verification.
        """
        self.device = torch.device(settings.DEVICE)
        
        # Initialize FaceNet
        # classify=False means we want the raw 512D embeddings, not classification logits
        self.model = InceptionResnetV1(pretrained='vggface2', classify=False).eval().to(self.device)

    @torch.no_grad()
    def get_embedding(self, face_tensor: torch.Tensor) -> np.ndarray:
        """
        Generates a 512-dimensional embedding vector for a given aligned face tensor.
        
        Args:
            face_tensor: Cropped and aligned face tensor from MTCNN
            
        Returns:
            np.ndarray: 512D embedding vector
        """
        # Add batch dimension if necessary (C, H, W) -> (1, C, H, W)
        if face_tensor.dim() == 3:
            face_tensor = face_tensor.unsqueeze(0)
            
        # Standardize pixel values (facenet-pytorch standardizes internally if post_process=True in MTCNN,
        # but since we set it to False, we ensure values are scaled to [-1, 1] range)
        # Note: InceptionResnetV1 in facenet_pytorch expects inputs to be standardized.
        # Alternatively, we just use the model's forward pass.
        face_tensor = face_tensor.to(self.device)
        face_tensor = (face_tensor - 127.5) / 128.0 # Normalization for FaceNet
        
        # Get embedding
        embedding = self.model(face_tensor)
        
        # Convert to numpy and flatten
        return embedding.cpu().numpy().flatten()

    @staticmethod
    def compute_distance(emb1: np.ndarray, emb2: np.ndarray, metric: str = 'cosine') -> float:
        """
        Compute the distance between two embedding vectors.
        Lower distance means higher similarity.
        """
        if metric == 'cosine':
            # Cosine distance = 1 - Cosine similarity
            dot_product = np.dot(emb1, emb2)
            norm_emb1 = np.linalg.norm(emb1)
            norm_emb2 = np.linalg.norm(emb2)
            similarity = dot_product / (norm_emb1 * norm_emb2)
            return 1.0 - similarity
        elif metric == 'euclidean':
            return np.linalg.norm(emb1 - emb2)
        else:
            raise ValueError(f"Unknown metric: {metric}")
