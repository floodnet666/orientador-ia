import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.services.empirical.document_processor import EmpiricalProcessor

@pytest.mark.asyncio
async def test_processor_filters_redundant_chunks():
    """
    Testa se o document_processor utiliza o NoveltyFilter e ignora chunks
    que a classe julga como redundantes.
    """
    processor = EmpiricalProcessor()
    
    # Criar 2 chunks. O NoveltyFilter vai dizer que o 2º é redundante.
    mock_chunk_1 = MagicMock(text_raw="Texto original", chunk_id="chunk1", text_enriched="Texto enriquecido 1")
    mock_chunk_2 = MagicMock(text_raw="Texto muito semelhante", chunk_id="chunk2", text_enriched="Texto enriquecido 2")
    
    # Mocks para evitar chamadas pesadas dependentes
    with patch("app.services.empirical.document_processor.extract_markdown_chunks", return_value=[mock_chunk_1, mock_chunk_2]):
        with patch("app.services.empirical.document_processor.generate_global_summary", new_callable=AsyncMock):
            with patch("app.services.empirical.document_processor.enrich_chunks_with_context", new_callable=AsyncMock) as mock_enrich:
                mock_enrich.return_value = [mock_chunk_1, mock_chunk_2] # Retorna ambos enriquecidos
                
                with patch("app.services.qdrant_service.ensure_empirical_collection_v2", new_callable=AsyncMock):
                    with patch("app.services.qdrant_service.delete_project_document", new_callable=AsyncMock):
                        with patch("app.services.empirical.document_processor.ollama_client.check_model", new_callable=AsyncMock):
                            with patch("app.services.empirical.document_processor.ollama_client.embed", new_callable=AsyncMock):
                                
                                # A função chave de inserção
                                with patch("app.services.qdrant_service.upsert_empirical_chunk", new_callable=AsyncMock) as mock_upsert:
                                    
                                    # Forçar o mock do NoveltyFilter a rejeitar o chunk 2
                                    with patch("app.services.contextual_enricher.NoveltyFilter") as MockFilter:
                                        instance = MockFilter.return_value
                                        # is_redundant retorna False para chunk1, True para chunk2
                                        instance.is_redundant.side_effect = [False, True]
                                        
                                        await processor.process_pdf_v2("caminho_fake.pdf", uuid4(), "test.pdf")
                                        
                                        # Como o limitador atua, o upsert deve ser chamado APENAS 1 vez (para o chunk 1)
                                        assert mock_upsert.call_count == 1
                                        
                                        # Verificar se o chunk_1 foi o alvo
                                        call_kwargs = mock_upsert.call_args.kwargs
                                        assert call_kwargs["chunk"] == mock_chunk_1
                                        assert call_kwargs["filename"] == "test.pdf"
