import asyncio
import logging
import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch

from app.agents.debate.panel_selector import select_panel
from app.agents.debate.context_analyzer import DebateContext

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("test.panel_selector")

@pytest.mark.asyncio
async def test_select_panel_success():
    """Verifica se o select_panel funciona com mocks de busca semântica."""
    context = DebateContext(
        debate_intent="DISCUTIR_METODOLOGIA",
        canvas={"tema": {"content": "IA na Saúde"}},
        critical_tension="Ética vs Performance"
    )
    
    # Mocking alma_list
    alma1 = MagicMock(id=uuid4(), name="Alma1", personality_descriptor="P1", description="D1")
    alma1.alma_type.value = "THEORETICAL"
    alma2 = MagicMock(id=uuid4(), name="Alma2", personality_descriptor="P2", description="D2")
    alma2.alma_type.value = "THEORETICAL"
    alma3 = MagicMock(id=uuid4(), name="Alma3", personality_descriptor="P3", description="D3")
    alma3.alma_type.value = "THEORETICAL"
    alma4 = MagicMock(id=uuid4(), name="Alma4", personality_descriptor="P4", description="D4")
    alma4.alma_type.value = "METHODOLOGICAL"
    
    alma_list = [alma1, alma2, alma3, alma4]

    # Mocking semantic search
    with patch("app.agents.debate.panel_selector.ollama_client.embed", new_callable=AsyncMock) as mock_embed, \
         patch("app.agents.debate.panel_selector.search_almas", new_callable=AsyncMock) as mock_search:
        
        mock_embed.return_value = [0.1] * 1536
        mock_search.side_effect = [
            # theoretical_matches
            [
                {"id": str(alma1.id), "name": "Alma1", "score": 0.9},
                {"id": str(alma2.id), "name": "Alma2", "score": 0.8},
            ],
            # antagonist_matches
            [
                {"id": str(alma3.id), "name": "Alma3", "score": 0.7},
            ]
        ]

        panel = await select_panel(
            context, alma_list, "Alma1", "Alma4"
        )
        
        assert panel.PRIMARIA.alma_name == "Alma1"
        assert panel.COMPLEMENTAR.alma_name == "Alma2"
        assert panel.ANTAGONISTA.alma_name == "Alma3"
        assert panel.METODOLOGICA.alma_name == "Alma4"
        log.info("Success selection test passed.")

@pytest.mark.asyncio
async def test_select_panel_fallback():
    """Verifica se o fallback funciona quando a busca semântica falha."""
    context = DebateContext(
        debate_intent="DISCUTIR_METODOLOGIA",
        canvas={"tema": {"content": "IA na Saúde"}},
        critical_tension="Ética vs Performance"
    )
    
    alma1 = MagicMock(id=uuid4(), name="Alma1")
    alma1.alma_type = "THEORETICAL"
    alma2 = MagicMock(id=uuid4(), name="Alma2")
    alma2.alma_type = "THEORETICAL"
    alma3 = MagicMock(id=uuid4(), name="Alma3")
    alma3.alma_type = "THEORETICAL"
    alma4 = MagicMock(id=uuid4(), name="Alma4")
    alma4.alma_type = "METHODOLOGICAL"
    
    alma_list = [alma1, alma2, alma3, alma4]

    # Forçar erro para testar o fallback
    with patch("app.agents.debate.panel_selector.ollama_client.embed", side_effect=Exception("Ollama Down")):
        panel = await select_panel(
            context, alma_list, "Alma1", "Alma4"
        )
        
        # O fallback deve selecionar as almas sequencialmente com base no tipo
        assert panel.PRIMARIA.alma_name == "Alma1"
        assert panel.COMPLEMENTAR.alma_name == "Alma2"
        assert panel.ANTAGONISTA.alma_name == "Alma3"
        assert panel.METODOLOGICA.alma_name == "Alma4"
        log.info("Fallback selection test passed.")

class AsyncMock(AsyncMock):
    pass

if __name__ == "__main__":
    asyncio.run(test_select_panel_success())
    asyncio.run(test_select_panel_fallback())
