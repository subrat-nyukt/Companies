import os
import json
from typing import Dict, List, Any
from azure.search.documents.models import VectorizedQuery
from core.client import azure_clients
from core.config import settings
from .embedder import embedder

class AzureSearchRetriever:

    async def search(self, query:str,top_k:int=5):

        query_vector= await embedder.get_embedding(query)

        vector_query=VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top_k,
            fields="content_vector"
        )

        async with azure_clients.get_search_client():
            results=await self.search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                select=["id", "content", "metadata"],
                top=top_k
            )

            hits=[]

            async for result in results:
                if result.id:
                    hits["id"].append(result.id)
                if result.content:
                    hits["content"].append(result.content)
                if result.metadata:
                    hits["metadata"].append(result.metadata)
                if result.score:
                    hits["score"].append(result.score)

            return hits
                
retriever = AzureSearchRetriever()



        
    
  