import logging
from uuid import UUID
from typing import Dict, Any

from app.services.empirical.document_processor import empirical_processor

log = logging.getLogger("tools.empirical_search")

class EmpiricalSearchTool:
    """Ferramenta para pesquisar evidências nos documentos empíricos do projeto."""
    def __init__(self, project_id: UUID):
        self.name = "search_evidence"
        self.description = (
            "Pesquisa trechos relevantes nos documentos (PDFs, CSVs) que o utilizador enviou para o projeto. "
            "Use esta ferramenta para fundamentar suas respostas nos textos enviados pelo autor."
        )
        self.project_id = project_id
        self.func = self.run

    async def run(self, query: str) -> Dict[str, Any]:
        """Searches empirical data using hybrid search."""
        log.info("Searching empirical data for project %s with query: '%s'", self.project_id, query)
        try:
            results = await empirical_processor.search_evidence(self.project_id, query, limit=5)
            
            if not results:
                return {
                    "success": True,
                    "message": "A pesquisa não encontrou trechos relevantes nos documentos do projeto para esta query.",
                    "results": []
                }
                
            return {
                "success": True,
                "message": f"Encontrados {len(results)} trechos relevantes nos documentos do projeto.",
                "results": results
            }
        except Exception as e:
            log.error("Failed to search empirical data: %s", e)
            return {
                "success": False,
                "error": f"Falha ao pesquisar documentos: {str(e)}"
            }
