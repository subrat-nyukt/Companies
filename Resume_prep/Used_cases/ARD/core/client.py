"""
ARD — core/client.py
====================
Lazy singleton wrappers for external service clients.
Import and call once; reused across all agents.
"""

from openai import OpenAI
from pinecone import Pinecone
from core.config import settings


class Clients:
    """Lazy-initialized singletons for external APIs."""

    _openai: OpenAI | None = None
    _pinecone: Pinecone | None = None
    _pinecone_index = None

    @property
    def openai(self) -> OpenAI:
        if self._openai is None:
            self._openai = OpenAI(api_key=settings.openai_api_key)
        return self._openai

    @property
    def pinecone_index(self):
        if self._pinecone_index is None:
            self._pinecone = Pinecone(api_key=settings.pinecone_api_key)
            self._pinecone_index = self._pinecone.Index(settings.pinecone_index_name)
        return self._pinecone_index


# Singleton: `from core.client import clients`
clients = Clients()
