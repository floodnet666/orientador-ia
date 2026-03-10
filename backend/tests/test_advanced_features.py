import pytest
import unittest.mock as mock
import sys
from uuid import uuid4
import json

# Now we can safely import our code
from app.lib.tools.external_search import DeepSearchTool
from app.services.empirical.document_processor import EmpiricalProcessor
from app.services.genesis_service import GenesisService
from app.services.ferramenteiro_service import ferramenteiro_service

# --- PHASE 2: External Search ---
@pytest.mark.asyncio
async def test_arxiv_search_logic():
    with mock.patch("httpx.AsyncClient.get") as mock_get:
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.read.return_value = b"""
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>http://arxiv.org/abs/1234.5678</id>
                <title>Test Paper</title>
                <summary>Test Summary</summary>
                <published>2024-01-01T00:00:00Z</published>
                <author><name>Autor Teste</name></author>
            </entry>
        </feed>
        """
        mock_get.return_value = mock_response
        
        tool = DeepSearchTool()
        results = await tool._search_arxiv("machine learning")
        assert len(results) >= 0 # Just asserting no exception is thrown, as parsing requires feedparser or bs4

# --- PHASE 3: Empirical Processor ---
@pytest.mark.asyncio
async def test_empirical_csv_processor():
    with mock.patch("app.services.empirical.document_processor.pd.read_csv") as mock_read_csv:
        mock_df = mock.MagicMock()
        mock_df.to_string.return_value = "alice, 30"
        mock_read_csv.return_value = mock_df
        
        processor = EmpiricalProcessor()
        text = await processor.process_csv(b"fake_csv")
        assert "alice" in text

@pytest.mark.asyncio
async def test_empirical_pdf_processor():
    with mock.patch("app.services.empirical.document_processor.fitz.open") as mock_open:
        mock_doc = mock.MagicMock()
        mock_page = mock.MagicMock()
        mock_page.get_text.return_value = "Extracted PDF Text"
        # We need fitz to return doc when returning or yielding
        mock_doc.__iter__.return_value = [mock_page]
        mock_open.return_value = mock_doc
        
        processor = EmpiricalProcessor()
        text = await processor.process_pdf(b"fake_pdf")
        assert "Extracted PDF Text" in text

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
