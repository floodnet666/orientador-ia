import pytest
from app.agents.almas.base_alma import BaseAlma
from app.state.graph_state import GraphState
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_state():
    state = MagicMock(spec=GraphState)
    state.chat_history = []
    state.orchestrator_directive = None
    return state

@pytest.mark.asyncio
async def test_base_alma_stream_response(mocker, mock_state):
    # Mock ollama_client
    mock_chat_stream = mocker.patch("app.agents.almas.base_alma.ollama_client.chat_stream")
    
    async def mock_stream_gen(*args, **kwargs):
        yield "Hello"
        yield " world"
        
    mock_chat_stream.return_value = mock_stream_gen()
    
    alma = BaseAlma(name="TestAlma", system_prompt="Be a test.", personality="Helpful")
    
    chunks = []
    async for chunk in alma.stream_response(mock_state):
        chunks.append(chunk)
        
    assert "".join(chunks) == "Hello world"
    mock_chat_stream.assert_called_once()
