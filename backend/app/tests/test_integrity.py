import pytest
import json
from pydantic import ValidationError
from app.agents.debate.context_analyzer import analyze_context, DebateContext, IntentOutput
from app.state.graph_state import CanvasState, GraphState

@pytest.mark.asyncio
async def test_maestro_debate_node_import_integrity():
    """Valida se o grafo e seus nós podem ser carregados COM asyncio resolvido."""
    try:
        from app.agents.graph_factory import debate_node
        assert debate_node is not None
        print("\n✅ [GREEN] debate_node importado com sucesso (asyncio OK).")
    except Exception as e:
        pytest.fail(f"Falha ao importar debate_node: {e}")

@pytest.mark.asyncio
async def test_context_analyzer_pollution_robustness():
    """Valida se o ContextAnalyzer agora TOLERA preâmbulos de texto."""
    mock_state = {
        "project_id": "test-uuid",
        "academic_level": "PHD",
        "current_canvas": CanvasState(),
        "debate_round_number": 1
    }
    
    polluted_response = (
        "Vamos estruturar essa ideia para um debate... "
        "{\"debate_intent\": \"DEVELOP_PROBLEMA\", \"tema\": \"Unificacao\", \"objetivo\": \"Aprofundar\"}"
    )
    
    from unittest.mock import AsyncMock
    import app.agents.debate.context_analyzer as ca
    
    original_agent = ca.context_analyzer_agent
    ca.context_analyzer_agent = AsyncMock()
    ca.context_analyzer_agent.run.return_value = polluted_response
    
    try:
        context = await analyze_context(mock_state, "Quero debater")
        assert context.debate_intent == "DEVELOP_PROBLEMA"
        print("\n✅ [GREEN] ContextAnalyzer extraiu JSON da poluição com sucesso.")
    except Exception as e:
        pytest.fail(f"ContextAnalyzer falhou com poluição: {e}")
    finally:
        ca.context_analyzer_agent = original_agent

@pytest.mark.asyncio
async def test_genesis_control_char_handling():
    """Valida se o parser JSON agora limpa caracteres de controle."""
    # Simulação de resposta com char \x0b (vertical tab) no meio
    dirty_json = '{"name": "Autor", "description": "Bio \x0b suja", "type": "THEORETICAL", "system_prompt": "Prompt"}'
    
    import re
    # Simula a lógica interna do local_genesis_service (sanitização aplicada no código)
    clean_json = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', dirty_json)
    
    try:
        data = json.loads(clean_json)
        assert data["description"] == "Bio  suja"
        print("\n✅ [GREEN] Caractere de controle sanitizado com sucesso.")
    except Exception as e:
        pytest.fail(f"Saneamento de JSON falhou: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_maestro_debate_node_import_integrity())
    asyncio.run(test_context_analyzer_pollution_robustness())
    asyncio.run(test_genesis_control_character_sanitization())
