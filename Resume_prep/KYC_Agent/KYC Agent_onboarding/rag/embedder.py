from typing import List
from core.client import azure_clients
from core.config import settings

class AzureEmbedder:
    """Wrapper for generating text embeddings using Azure OpenAI."""
    
    def __init__(self):
        self.client = azure_clients.llm
        self.deployment = settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT

    async def get_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            input=[text],
            model=self.deployment
        )
        return response.data[0].embedding

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        response = await self.client.embeddings.create(
            input=texts,
            model=self.deployment
        )
        return [item.embedding for item in response.data]

# Singleton instance
embedder = AzureEmbedder()
