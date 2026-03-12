import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.debate.debate_runner import DebateRunner

@pytest.mark.asyncio
async def test_debate_runner_sequential_logic():
    # Mock dependencies
    state = MagicMock()
    context = MagicMock()
    context.user_message = "Test message"
    
    alma_registry = {
        "Alma1": MagicMock(alma_name="Alma1", system_prompt="Prompt1"),
        "Alma2": MagicMock(alma_name="Alma2", system_prompt="Prompt2"),
        "Alma3": MagicMock(alma_name="Alma3", system_prompt="Prompt3"),
    }
    for mock in alma_registry.values():
        mock.name = mock.alma_name

    panel = MagicMock()
    panel.PRIMARIA = alma_registry["Alma1"]
    panel.COMPLEMENTAR = alma_registry["Alma2"]
    panel.ANTAGONISTA = alma_registry["Alma3"]
    
    runner = DebateRunner()
    
    # Mock Agent.stream
    async def mock_stream(prompt):
        yield f"Response to: {prompt[:20]}..."

    with patch("app.agents.debate.debate_runner.Agent") as MockAgent:
        mock_agent_instance = MockAgent.return_value
        mock_agent_instance.stream.side_effect = mock_stream
        mock_agent_instance.name = "Mocked Agent"
        
        events = []
        async for event in runner.run(state, context, panel, alma_registry):
            events.append(event)
            
        # Verify sequence of events
        types = [e["type"] for e in events]
        assert "debate_turn_start" in types
        assert "debate_chunk" in types
        assert "debate_turn_end" in types
        assert "debate_complete" in types
        
        # Verify turns
        chunks = [e for e in events if e["type"] == "debate_chunk"]
        assert len(chunks) == 3
        assert chunks[0]["alma_name"] == "Alma1"
        assert chunks[1]["alma_name"] == "Alma2"
        assert chunks[2]["alma_name"] == "Alma3"
        
        # Verify complete data
        complete_event = next(e for e in events if e["type"] == "debate_complete")
        assert "PRIMARIA" in complete_event["turns"]
        assert "COMPLEMENTAR" in complete_event["turns"]
        assert "ANTAGONISTA" in complete_event["turns"]
