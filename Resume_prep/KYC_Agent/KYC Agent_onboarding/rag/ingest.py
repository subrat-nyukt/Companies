import logging
from typing import Dict, Any, Optional
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from core.config import settings

logger = logging.getLogger(__name__)


class DocumentIngestor:
    """
    Wraps Azure Form Recognizer (Document Intelligence) to parse
    PDFs and structured documents into text + table data.
    Used by the Document Parsing Agent node in the LangGraph pipeline.
    """

    def __init__(self):
        self.client = DocumentAnalysisClient(
            endpoint=settings.azure_doc_intel_endpoint,
            credential=AzureKeyCredential(settings.azure_doc_intel_key),
        )

    async def parse_document(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Read a PDF/document and extract structured text and tables.
        Returns dict with keys: text, tables, page_count.
        Returns None on failure.
        """
        try:
            with open(file_path, "rb") as f:
                poller = self.client.begin_analyze_document(
                    "prebuilt-layout", document=f
                )
                result = poller.result()

            extracted: Dict[str, Any] = {
                "text": "",
                "tables": [],
                "page_count": len(result.pages) if result.pages else 0,
            }

            # Concatenate all page content
            if result.content:
                extracted["text"] = result.content

            # Extract tables as list of row-col-content dicts
            if result.tables:
                for table in result.tables:
                    table_rows = [
                        {
                            "row": cell.row_index,
                            "col": cell.column_index,
                            "content": cell.content,
                        }
                        for cell in table.cells
                    ]
                    extracted["tables"].append(table_rows)

            logger.info(f"Document extraction complete for {file_path}")
            return extracted

        except Exception as e:
            logger.error(f"DocumentIngestor failed for {file_path}: {e}")
            return None


# Singleton used by the agent
document_ingestor = DocumentIngestor()