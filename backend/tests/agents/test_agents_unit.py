import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from app.agents.orchestrator import orchestrate, OrchestratorOutput
from app.state.graph_state import GraphState, CanvasState

@pytest.fixture
def base_state():
    return GraphState(
        project_id=str(uuid4()),
        user_id=str(uuid4()),
        academic_level="MESTRADO",
        active_theoretical_alma="FOUCAULT",
        active_methodological_alma="ETNOGRAFA"
    )

@pytest.mark.asyncio
async def test_maestro_orchestrate_basic(base_state):
    """Tests the main orchestrator decision logic with mocked ADK agent."""
    # Mock the ADK agent run
    with patch("app.agents.orchestrator.maestro_agent.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = OrchestratorOutput(
            selected_alma="THEORETICAL",
            is_plagiarism=False,
            directive="Teste diretiva"
        )
        
        result = await orchestrate(base_state, "Olá")
        
        assert result["selected_alma"] == "THEORETICAL"
        assert result["is_plagiarism"] is False
        assert "Teste diretiva" in result["directive"]
        mock_run.assert_called_once()

@pytest.mark.asyncio
async def test_maestro_orchestrate_error_fallback(base_state):
    """Tests error fallback in orchestrator."""
    with patch("app.agents.orchestrator.maestro_agent.run", side_effect=Exception("LLM Fail")):
        result = await orchestrate(base_state, "Olá")
        # Should return default fallback
        assert result["selected_alma"] == "THEORETICAL"
        assert "socrática" in result["directive"]

from app.agents.debate.debate_orchestrator import DebateOrchestrator

@pytest.mark.asyncio
async def test_debate_orchestrator_not_enough_almas(base_state):
    """Tests debate fails if not enough almas are available."""
    orch = DebateOrchestrator()
    mock_db = AsyncMock()
    
    # Mock db.execute to return only 2 almas
    mock_result = MagicMock()
    mock_item = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_item, mock_item]
    mock_db.execute.return_value = mock_result
    
    events = []
    async for event in orch.run(base_state, "Debate agora", mock_db):
        events.append(event)
        
    assert any(e["type"] == "error" for e in events)
    assert "pelo menos 4 Almas" in events[-1]["message"]
