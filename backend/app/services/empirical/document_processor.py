import os
import logging
from typing import List, Dict, Any
from uuid import UUID
import pandas as pd
from io import BytesIO

from qdrant_client import AsyncQdrantClient, models
from app.config import settings
from app.services.ollama_client import ollama_client
from app.services.qdrant_service import (
    get_qdrant, 
    EMPIRICAL_COLLECTION, 
    ensure_empirical_collection,
    compute_bm25_sparse_vector
)
from app.services.pdf_markdown_extractor import extract_markdown_chunks
from app.services.contextual_enricher import enrich_chunks_with_context, generate_global_summary
from app.services.hybrid_search import hybrid_search_evidence

log = logging.getLogger("empirical.processor")

class EmpiricalProcessor:
    def __init__(self):
        self.qdrant = AsyncQdrantClient(host="localhost", port=6333, check_compatibility=False)
        self.collection_name = EMPIRICAL_COLLECTION

    async def ensure_collection(self):
        """Creates the collection if it doesn't exist."""
        await ensure_empirical_collection()

    async def process_pdf_v2(self, file_path: str, project_id: UUID, filename: str):
        """
        New RAG v2.1.0 Pipeline:
        1. Extract Markdown (M1)
        2. Enrich with Context (M2)
        3. Index with Hybrid Vector (M3)
        """
        pid_str = str(project_id)
        doc_id = f"{pid_str}_{filename}"
        
        # 1. Extração M1
        log.info("M1: Extraindo Markdown de %s", filename)
        chunks = extract_markdown_chunks(file_path, doc_id)
        title_sample = "".join([c.text_raw for c in chunks[:3]])
        if not title_sample:
             log.warning("PDF vazio: %s", filename)
             return


        # 2. Resumo Global e Enriquecimento M2
        log.info("M2: Gerando contexto situacional via Ollama")
        global_summary = await generate_global_summary(title_sample)
        enriched_chunks = await enrich_chunks_with_context(chunks, global_summary)

        # 3. Preparação BM25 (Corpus de tokens)
        import re
        corpus_tokens = [
            re.findall(r'\b[a-záàâãéêíóôõúç]+\b', c.text_raw.lower())
            for c in enriched_chunks
        ]

        # 4. Indexação Qdrant M3
        log.info("M3: Indexando %d chunks enriquecidos no Qdrant", len(enriched_chunks))
        points = []
        for i, chunk in enumerate(enriched_chunks):
            # Vetor Denso do texto enriquecido
            dense_vec = await ollama_client.embed(chunk.text_enriched)
            # Vetor Esparso (BM25) do texto original
            sparse_vec = compute_bm25_sparse_vector(chunk.text_raw, corpus_tokens)
            
            points.append(models.PointStruct(
                id=str(UUID(int=abs(hash(chunk.chunk_id)))),
                vector={
                    "dense": dense_vec,
                    "sparse": models.SparseVector(
                        indices=sparse_vec["indices"],
                        values=sparse_vec["values"]
                    )
                },
                payload={
                    "project_id": pid_str,
                    "filename": filename,
                    "text": chunk.text_enriched, # para RAG (contextualizado)
                    "text_raw": chunk.text_raw,   # para display
                    "section_title": chunk.section_title,
                    "page_number": chunk.page_number,
                    "type": "empirical_evidence_v2"
                }
            ))

        await self.ensure_collection()
        await self.qdrant.upsert(
            collection_name=self.collection_name,
            points=points
        )
        log.info("RAG v2.1.0: Concluída indexação de %s", filename)

    async def search_evidence(self, project_id: UUID, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Usa a nova busca híbrida."""
        return await hybrid_search_evidence(project_id, query, limit)

    # Legado para CSV (mantido por agora)
    async def process_pdf(self, file_content: bytes) -> str:
        # Pass-through para manter compatibilidade com a API raw se necessário
        # Mas recomendável usar process_pdf_v2 com path
        import fitz
        doc = fitz.open(stream=file_content, filetype="pdf")
        return "".join([page.get_text() for page in doc])

    async def process_csv(self, file_content: bytes) -> str:
        df = pd.read_csv(BytesIO(file_content))
        return df.to_string()

    async def index_document(self, project_id: UUID, filename: str, content: str):
        # Fallback legado
        log.info("Usando indexação legada para %s", filename)
        # TODO: Migrar CSV para o novo pipeline se necessário
        pass

empirical_processor = EmpiricalProcessor()

