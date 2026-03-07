import pytest
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from app.lib.tools.empirical_indexer import EmpiricalIndexingTool

@pytest.mark.asyncio
async def test_empirical_indexing_tool_success():
    project_id = uuid4()
    tool = EmpiricalIndexingTool(project_id)
    
    mock_content = b"Mock PDF content"
    mock_text = "Extracted text from PDF"
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = mock_content
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response
        
        with patch("app.services.empirical.document_processor.empirical_processor.process_pdf", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = mock_text
            
            with patch("app.services.empirical.document_processor.empirical_processor.index_document", new_callable=AsyncMock) as mock_index:
                
                result = await tool.run("https://example.com/test.pdf", "test.pdf")
                
                assert result["success"] is True
                assert result["filename"] == "test.pdf"
                mock_get.assert_called_once_with("https://example.com/test.pdf")
                mock_process.assert_called_once_with(mock_content)
                mock_index.assert_called_once_with(project_id, "test.pdf", mock_text)

@pytest.mark.asyncio
async def test_empirical_indexing_tool_failure():
    project_id = uuid4()
    tool = EmpiricalIndexingTool(project_id)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = Exception("Empty error")
        
        result = await tool.run("https://example.com/fail.pdf", "fail.pdf")
        
        assert result["success"] is False
        assert "Falha ao processar documento" in result["error"]
