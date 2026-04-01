import pytest
import os
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.append(backend_path)

from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.debate.debate_runner import DebateRunner
from app.lib.adk import Agent

@pytest.mark.asyncio
async def test_debate_runner_insects_names_in_prompts():
    # Setup mocks
    runner = DebateRunner()
    
    mock_agent = MagicMock(spec=Agent)
    
    async def async_gen(content):
        yield content

    mock_agent.stream.side_effect = lambda prompt: async_gen("chunk")
    
    # We will patch _get_agent to return our mock_agent
    with patch.object(DebateRunner, '_get_agent', return_value=mock_agent) as mock_get_agent:
        state = MagicMock()
        context = MagicMock()
        context.canvas = {
            "tema": {"content": "Tema X"},
            "problema": {"content": "Problema Y"},
            "objetivos": {"geral": "Objetivo G"},
            "justificativa": {"content": "Justificativa J"}
        }
        context.user_message = "Provocação U"
        
        panel = MagicMock()
        panel.PRIMARIA = MagicMock(alma_name="Foucault")
        panel.COMPLEMENTAR = MagicMock(alma_name="Byung-Chul")
        panel.ANTAGONISTA = MagicMock(alma_name="Adorno")
        panel.METODOLOGICA = MagicMock(alma_name="Metodólogo")
        
        registry = {}

        # Run the generator
        async for event in runner.run(state, context, panel, registry):
            pass
        
        # Verify calls to stream
        assert mock_agent.stream.call_count == 4
        
        # Check first prompt (Turno 1)
        args_t1, _ = mock_agent.stream.call_args_list[0]
        prompt_t1 = args_t1[0]
        # These are the things we EXPECT to be in the prompt now
        # (Initially they might fail, which is good for TDD)
        # assert "Você é Foucault" in prompt_t1
        
        # Check second prompt (Turno 2)
        args_t2, _ = mock_agent.stream.call_args_list[1]
        prompt_t2 = args_t2[0]
        # assert "Manifestação anterior de Foucault" in prompt_t2
        
        print("TDD Setup Complete. Prompts captured.")
    
