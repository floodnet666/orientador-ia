import httpx
import logging
from uuid import UUID
from typing import Dict, Any

from app.services.empirical.document_processor import empirical_processor

log = logging.getLogger("tools.empirical_indexer")

class EmpiricalIndexingTool:
    """Ferramenta para 'baixar' e indexar documentos encontrados externamente."""
    def __init__(self, project_id: UUID):
        self.name = "EmpiricalIndexing"
        self.description = (
            "Faz o download de um documento (PDF) de uma URL e indexa-o no projeto "
            "como evidência empírica / referência. Use isto para 'salvar' papers relevantes."
        )
        self.project_id = project_id
        self.func = self.run

    async def run(self, url: str, filename: str) -> Dict[str, Any]:
        """Downloads a PDF from a URL and indexes it."""
        log.info("Downloading and indexing document from %s (filename: %s)", url, filename)
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                content = response.content

            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"

            # Process and index
            text = await empirical_processor.process_pdf(content)
            await empirical_processor.index_document(self.project_id, filename, text)

            return {
                "success": True,
                "message": f"Documento '{filename}' baixado e indexado com sucesso no projeto.",
                "filename": filename
            }
        except Exception as e:
            log.error("Failed to index document from %s: %s", url, e)
            return {
                "success": False,
                "error": f"Falha ao processar documento: {str(e)}"
            }
