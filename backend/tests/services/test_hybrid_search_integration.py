import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

# Importar da app real
from app.services.hybrid_search import hybrid_search_evidence

@pytest.mark.asyncio
async def test_hybrid_search_evidence_uses_sum_instead_of_rrf():
    """
    Testa se a função de alto nível hybrid_search_evidence agora faz DUAS queries
    separadas (ao invés de usar o FusionQuery RRF nativo do Qdrant) e invoca _set_union_merge.
    """
    project_id = uuid4()
    
    # Mocks para o Qdrant Client e Ollama
    mock_qdrant = MagicMock()
    # Retorno fake de query_points: 2 hits falsos
    mock_query_points = AsyncMock()
    mock_query_points.return_value.points = [
        MagicMock(id="1", score=0.9, payload={"text_raw": "t1", "filename": "f1.pdf"}),
        MagicMock(id="2", score=0.8, payload={"text_raw": "t2", "filename": "f1.pdf"})
    ]
    mock_qdrant.query_points = mock_query_points

    with patch("app.services.hybrid_search.get_qdrant", return_value=mock_qdrant):
        with patch("app.services.hybrid_search.ollama_client.embed", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 768
            
            with patch("app.services.hybrid_search._set_union_merge") as mock_sum:
                # Simular o comportamento do SUM
                mock_sum.return_value = [{"score": 0.9, "payload": {"text_raw": "t1", "filename": "f1.pdf", "is_anchor": False}}]
                
                await hybrid_search_evidence(project_id, "teste query", limit=5)
                
                # Afirmações cruciais do TDD:
                # 1. query_points deve ter sido chamado 2 vezes (uma para denso, uma para esparso)
                assert mock_query_points.call_count == 2
                
                # 2. _set_union_merge deve ser a função de união oficial agora (e não o prefetch do Qdrant)
                mock_sum.assert_called_once()
