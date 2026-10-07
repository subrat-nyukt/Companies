from openai import AsyncAzureOpenAI
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from .config import settings


class AzureClientManager:
    """Centralized lazy-init manager for all Azure SDK clients."""

    def __init__(self):
        self._llm_client = None

    @property
    def llm(self) -> AsyncAzureOpenAI:
        if self._llm_client is None:
            self._llm_client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
        return self._llm_client

    def get_search_client(self, index_name: str = None) -> SearchClient:
        """Returns a new SearchClient — use as async context manager."""
        index = index_name or settings.azure_search_index
        return SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=index,
            credential=AzureKeyCredential(settings.azure_search_key),
        )


# Singleton — import this everywhere
azure_clients = AzureClientManager()
