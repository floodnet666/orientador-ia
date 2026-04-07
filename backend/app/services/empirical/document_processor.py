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
    ensure_empirical_collection_v2
)
from app.services.pdf_markdown_extractor import extract_markdown_chunks
from app.services.contextual_enricher import enrich_chunks_with_context, generate_global_summary

log = logging.getLogger("empirical.processor")

class EmpiricalProcessor:
    def __init__(self):
        self.qdrant = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.collection_name = EMPIRICAL_COLLECTION

    async def ensure_collection(self):
        """Creates the collection if it doesn't exist."""
        await ensure_empirical_collection_v2()

    async def process_pdf_v2(self, file_path: str, project_id: UUID, filename: str):
        """
        RAG v2.2.0 Industrial Pipeline:
        1. Extract Markdown (M1)
        2. Enrich with Context (M2)
        3. Index with SPLADE Sparse + Dense Hybrid (M3)
        4. Multi-document persistence (No destructive recreate)
        """
        pid_str = str(project_id)
        doc_id = f"{pid_str}_{filename}"
        
        # 1. Extração M1
        log.info("M1: Extraindo Markdown de %s", filename)
        chunks = extract_markdown_chunks(file_path, doc_id)
        if not chunks:
             log.warning("PDF vazio: %s", filename)
             return
        
        title_sample = "".join([c.text_raw for c in chunks[:3]])

        # 2. Resumo Global e Enriquecimento M2
        log.info("M2: Gerando contexto situacional via Ollama")
        global_summary = await generate_global_summary(title_sample)
        enriched_chunks = await enrich_chunks_with_context(chunks, global_summary)

        # 3. Preparação BM25 (Removida em v2.2.0 a favor do SPLADE-style hashing)
        # O SPLADE não requer corpus prévio, calculamos chunk a chunk

        # 4. Ingestão Híbrida v2.2.0
        from app.services.contextual_enricher import NoveltyFilter
        from app.services.qdrant_service import (
            ensure_empirical_collection_v2,
            delete_project_document,
            upsert_empirical_chunk,
            compute_sparse_vector_splade
        )

        col_name = await ensure_empirical_collection_v2()
        
        # Limpa chunks antigos deste documento ANTES de inserir novos (Gargalo C)
        log.info("Limpando indexação anterior para %s", filename)
        await delete_project_document(pid_str, filename)

        log.info("M3: Indexando %d chunks híbridos (SPLADE + Dense) no Qdrant", len(enriched_chunks))
        
        # OLLAMA Pre-warming (Gargalo A refinement)
        await ollama_client.check_model(settings.OLLAMA_CHAT_MODEL) # Cold start guard

        novelty_filter = NoveltyFilter(threshold=0.65)
        history_texts = []

        for chunk in enriched_chunks:
            # Aplica o Filtro de Novidade (Jaccard)
            if novelty_filter.is_redundant(chunk.text_raw, history_texts):
                log.info("Chunk redundante ignorado (Jaccard): %s", chunk.chunk_id)
                continue

            # Vetor Denso (Contextualizado)
            dense_vec = await ollama_client.embed(chunk.text_enriched)
            
            # Vetor Esparso SPLADE com Normalização (Gargalo D)
            sparse_data = compute_sparse_vector_splade(chunk.text_raw)
            
            await upsert_empirical_chunk(
                collection_name=col_name,
                chunk=chunk,
                dense_vector=dense_vec,
                sparse_data=sparse_data,
                project_id=pid_str,
                filename=filename
            )
            
            history_texts.append(chunk.text_raw)

        log.info("RAG v2.2.0: Concluída indexação industrial de %s", filename)

    async def search_evidence(self, project_id: UUID, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Usa a nova busca híbrida."""
        from app.services.hybrid_search import hybrid_search_evidence
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

