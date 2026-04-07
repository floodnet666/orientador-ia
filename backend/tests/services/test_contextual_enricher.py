import pytest
from app.services.contextual_enricher import NoveltyFilter


from unittest.mock import AsyncMock, patch
import numpy as np

@pytest.fixture
def mock_embed():
    with patch("app.services.ollama_client.ollama_client.embed", new_callable=AsyncMock) as m:
        yield m

class TestNoveltyFilter:
    """
    Suite TDD para NoveltyFilter.
    Threshold de referência da spec: 0.85 (Embeddings / Cosine Similarity).
    """

    @pytest.mark.asyncio
    async def test_rejects_redundant_input(self, mock_embed):
        """
        Input semanticamente idêntico ao histórico deve ser marcado como redundante.
        O threshold padrão é 0.85 para similaridade de cosseno.
        """
        # Vectores paralelos perfeitamente idênticos -> cos_sim = 1.0 > 0.85
        mock_embed.side_effect = [
            [0.1, 0.2, 0.3], # new_text embedding
            [0.1, 0.2, 0.3], # history[0] embedding
        ]
        nf = NoveltyFilter(threshold=0.85)
        history = ["Texto histórico."]
        new_input = "Texto muito parecido."
        result = await nf.is_redundant(new_input, history)
        assert result is True

    @pytest.mark.asyncio
    async def test_accepts_novel_input(self, mock_embed):
        """Input semanticamente diferente deve ser aceite (cosine similarity baixo)."""
        # Vectores ortogonais -> cos_sim = 0.0 < 0.85
        mock_embed.side_effect = [
            [1.0, 0.0, 0.0], # new_text embedding
            [0.0, 1.0, 0.0], # history[0] embedding
        ]
        nf = NoveltyFilter(threshold=0.85)
        history = ["Texto de uma coisa."]
        new_input = "Texto de outra coisa completamente diferente."
        result = await nf.is_redundant(new_input, history)
        assert result is False

    @pytest.mark.asyncio
    async def test_empty_history_never_redundant(self, mock_embed):
        """Com histórico vazio, qualquer input é aceite e não chama embeddings do histórico."""
        nf = NoveltyFilter(threshold=0.85)
        result = await nf.is_redundant("Qualquer texto.", [])
        assert result is False
        # Para histórico vazio, nem precisamos calcular o embedding do new_text
        mock_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_cosine_similarity_math(self, mock_embed):
        """Testar a matemática interna da similaridade de cosseno."""
        nf = NoveltyFilter(threshold=0.85)
        v1 = [1.0, 2.0, 3.0]
        v2 = [1.0, 2.0, 3.0]
        v3 = [-1.0, -2.0, -3.0]
        
        sim_1_2 = nf._cosine_similarity(v1, v2)
        sim_1_3 = nf._cosine_similarity(v1, v3)
        assert np.isclose(sim_1_2, 1.0)
        assert np.isclose(sim_1_3, -1.0)

