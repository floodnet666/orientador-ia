import pytest
import unittest.mock as mock
import sys
from uuid import uuid4
import json

# --- MOCKING EXTERNAL LIBRARIES ---
# We mock these BEFORE importing our services to avoid ImportErrors 
# in the environment where uv sync is failing.
mock_arxiv = mock.MagicMock()
sys.modules["arxiv"] = mock_arxiv

mock_fitz = mock.MagicMock()
sys.modules["fitz"] = mock_fitz

mock_pd = mock.MagicMock()
sys.modules["pandas"] = mock_pd

mock_qdrant = mock.MagicMock()
sys.modules["qdrant_client"] = mock_qdrant
sys.modules["qdrant_client.models"] = mock.MagicMock()

# Now we can safely import our code
from app.lib.tools.external_search import arxiv_search
from app.services.empirical.document_processor import EmpiricalProcessor
from app.services.genesis_service import GenesisService
from app.services.ferramenteiro_service import ferramenteiro_service

# --- PHASE 2: External Search ---
@pytest.mark.asyncio
async def test_arxiv_search_logic():
    mock_result = mock.MagicMock()
    mock_result.title = "Test Paper"
    mock_result.summary = "Test Summary"
    mock_result.entry_id = "http://arxiv.org/abs/1234.5678"
    mock_result.published.strftime.return_value = "2024-01-01"
    
    mock_arxiv.Client.return_value.results.return_value = [mock_result]
    
    results = await arxiv_search("machine learning")
    assert len(results) == 1
    assert "Test Paper" in results[0]["title"]

# --- PHASE 3: Empirical Processor ---
@pytest.mark.asyncio
async def test_empirical_csv_processor():
    # Mocking pandas read_csv behavior
    mock_df = mock.MagicMock()
    mock_df.to_string.return_value = "alice, 30"
    mock_pd.read_csv.return_value = mock_df
    
    processor = EmpiricalProcessor()
    text = await processor.process_csv(b"fake_csv")
    assert "alice" in text

@pytest.mark.asyncio
async def test_empirical_pdf_processor():
    mock_doc = mock.MagicMock()
    mock_page = mock.MagicMock()
    mock_page.get_text.return_value = "Extracted PDF Text"
    mock_doc.__iter__.return_value = [mock_page]
    mock_fitz.open.return_value = mock_doc
    
    processor = EmpiricalProcessor()
    text = await processor.process_pdf(b"fake_pdf")
    assert text == "Extracted PDF Text"

# --- PHASE 4: Genesis Service ---
@pytest.mark.asyncio
async def test_genesis_service_parsing():
    with mock.patch("app.services.ollama_client.ollama_client.chat_stream") as mock_chat:
        async def mock_gen(*args, **kwargs):
            yield {"content": "```json\n{\"name\": \"Tesla\", \"description\": \"Engenheiro\", \"type\": \"THEORETICAL\", \"system_prompt\": \"Prompt de teste\"}\n```"}
        mock_chat.side_effect = mock_gen
        
        service = GenesisService()
        alma = await service.generate_alma("Crie um engenheiro")
        assert alma["name"] == "Tesla"
        assert alma["type"] == "THEORETICAL"

# --- PHASE 4: Ferramenteiro Service ---
def test_ferramenteiro_sandbox_success():
    code = "x = 10 + 5\nprint(f'Result: {x}')"
    result = ferramenteiro_service.execute_code(code)
    assert result["success"] is True
    assert "Result: 15" in result["stdout"]
    assert result["context"]["x"] == 15

def test_ferramenteiro_sandbox_error():
    code = "y = 10 / 0"
    result = ferramenteiro_service.execute_code(code)
    assert result["success"] is False
    assert "ZeroDivisionError" in result["stderr"]
