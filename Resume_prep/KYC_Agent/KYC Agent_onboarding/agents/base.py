import os 
import json
from typing import TypedDict, Dict, List, Any
from core.client import azure_clients
from core.config import settings
from prompts.v1.agent_prompt import SYSTEM_PROMPT
from rag.ingest import DocumentIngestor
from rag.retriever import retriever
from vision.analysis import VisionAnalyzer



class BaseAgent:
    def __init__(self):

        self.client=azure_clients.llm
        self.deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME
        self.messages=[]
        self.system_prompt=SYSTEM_PROMPT
        self.ingestor=DocumentIngestor()
        self.analyzer=VisionAnalyzer()


    

    async def process_document(self, user_query:str, document_path:str=None):

        try:
            with open (file_path, "rb") as f:

                filename=f.name.lower()

                if filename.endswith(".pdf"):

                    extracted_data=await self.ingestor.parse_document(document_path)

                elif filename.endswith(".jpg") or filename.endswith(".png"):

                    extracted_data=await self.analyzer.process_documents(document_path)

                else:
                    raise ValueError("Unsupported file type")

        except Exception as e:
            print(f"error while processing the file")



        final_prompt=f"""
            user question:{user_query}\n\n
            extracted_data:{extracted_data}

            
            """


        self.messages.append([
                {
                    "role":"system", "content": SYSTEM_PROMPT,
            
                }
                ])

        self.messages.append({
                "role":"user", "content": final_prompt
            })

        response=await.self.client,chat.compeltions.create(

            model=self.deployment,
            messages=self.messages,
            temperature=0.3


        )

        result=response.choices[0].message.content

        self.message.append({
            "role":"assistant", "content": result
        })

        return result

        except Exception as e:
            print(f"error while processing the file")
            return str(e)





        

        


                    



                    

            
             

        


