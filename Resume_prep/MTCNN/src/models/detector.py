import torch
from facenet_pytorch import MTCNN
from PIL import Image
import numpy as np
import io

from src.core.config import settings

class FaceDetector:
    def __init__(self):
        """
        Initialize the MTCNN detector for face detection and alignment.
        MTCNN: Multi-task Cascaded Convolutional Networks
        It performs face detection, bounding box regression, and facial landmark localization.
        """
        self.device = torch.device(settings.DEVICE)
        
        # Initialize MTCNN
        # keep_all=False means it only returns the most prominent face
        self.mtcnn = MTCNN(
            image_size=settings.IMAGE_SIZE,
            margin=settings.MARGIN,
            keep_all=False,
            device=self.device,
            post_process=False # Don't normalize here, FaceNet will handle it
        )

    def detect_and_align(self, image_bytes: bytes) -> torch.Tensor:
        """
        Detects a face in the image and returns the aligned, cropped face tensor.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            torch.Tensor: Cropped face tensor, or None if no face is detected
        """
        try:
            # Load image using PIL
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            # mtcnn returns the cropped and aligned face as a tensor directly
            # because we specified image_size and margin in initialization
            face_tensor = self.mtcnn(image)
            
            return face_tensor
        except Exception as e:
            print(f"Error during face detection: {str(e)}")
            return None

    def detect_boxes(self, image_bytes: bytes) -> np.ndarray:
        """
        Returns just the bounding boxes and probabilities (useful for visualization or liveness checks).
        """
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            boxes, probs = self.mtcnn.detect(image)
            return boxes, probs
        except Exception as e:
            print(f"Error detecting boxes: {str(e)}")
            return None, None
