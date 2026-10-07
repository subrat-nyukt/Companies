import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Facial Recognition Service"
    APP_VERSION: str = "1.0.0"
    
    # Model Configuration
    DEVICE: str = "cpu"  # Change to "cuda" if GPU is available
    IMAGE_SIZE: int = 160  # FaceNet expects 160x160 images
    MARGIN: int = 0  # MTCNN cropping margin
    
    # Verification Configuration
    # Cosine distance threshold (lower means stricter). 
    # For FaceNet (vggface2), 0.6-0.7 is a good starting point for cosine distance
    SIMILARITY_THRESHOLD: float = 0.65  
    
    # Storage (For registered users)
    # In a real scenario, this would be a Vector DB like Pinecone, Milvus, or pgvector
    EMBEDDING_STORAGE_DIR: str = os.path.join(os.path.dirname(__file__), "../../data/embeddings")

settings = Settings()

# Ensure storage directory exists
os.makedirs(settings.EMBEDDING_STORAGE_DIR, exist_ok=True)
