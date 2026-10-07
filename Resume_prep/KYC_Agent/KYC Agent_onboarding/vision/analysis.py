import logging
from typing import Dict, Any, Optional
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
from core.config import settings

logger = logging.getLogger(__name__)


class VisionAnalyzer:
    """
    Wraps Azure AI Vision to extract text, tags, captions, and
    detected objects from an image file (JPG / PNG).
    Used by the Image Parsing Agent node in the LangGraph pipeline.
    """

    def __init__(self):
        self.client = ImageAnalysisClient(
            endpoint=settings.azure_vision_endpoint,
            credential=AzureKeyCredential(settings.azure_vision_key),
        )

    async def process_document(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Read an image from disk and extract structured information.
        Returns a dict with keys: caption, tags, read (OCR text), objects.
        Returns None on failure so callers can handle gracefully.
        """
        try:
            with open(file_path, "rb") as f:
                image_data = f.read()

            # Azure Vision is synchronous; wrap in executor in real async apps
            result = self.client.analyze(
                image_data=image_data,
                visual_features=[
                    VisualFeatures.CAPTION,
                    VisualFeatures.READ,
                    VisualFeatures.TAGS,
                    VisualFeatures.OBJECTS,
                ],
            )

            extracted: Dict[str, Any] = {
                "caption": "",
                "tags": [],
                "read": [],   # OCR lines — most important for ID cards
                "objects": [],
            }

            if result.caption:
                extracted["caption"] = result.caption.text

            if result.tags:
                extracted["tags"] = [tag.name for tag in result.tags.list]

            if result.read:
                for block in result.read.blocks:
                    for line in block.lines:
                        extracted["read"].append(line.text)

            if result.objects:
                extracted["objects"] = [
                    {"name": obj.tags[0].name, "confidence": obj.tags[0].confidence}
                    for obj in result.objects.list
                ]

            logger.info(f"Vision extraction complete for {file_path}")
            return extracted

        except Exception as e:
            logger.error(f"VisionAnalyzer failed for {file_path}: {e}")
            return None


# Singleton used by the agent
vision_analyzer = VisionAnalyzer()
