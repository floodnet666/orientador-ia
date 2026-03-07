import unittest
import unittest.mock as mock
import sys
import os
from uuid import uuid4
import json
import asyncio

# 1. MOCK THE ENTIRE ECOSYSTEM BEFORE ANY IMPORTS
# This prevents the app from trying to load real libraries
mock_modules = [
    "arxiv",
    "fitz",
    "pandas",
    "qdrant_client",
    "qdrant_client.models",
    "sqlalchemy",
    "sqlalchemy.ext.asyncio",
    "sqlalchemy.orm",
    "fastapi",
    "passlib",
    "passlib.context",
    "jose",
    "jwt",
]

for mod in mock_modules:
    sys.modules[mod] = mock.MagicMock()

# Mock specific attributes needed for imports to not fail
sys.modules["qdrant_client.models"] = mock.MagicMock()
sys.modules["sqlalchemy.ext.asyncio"].AsyncSession = mock.MagicMock()

# 2. IMPORT SERVICES
# Adding backend path to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Mocking settings and ollama_client to avoid network calls
with mock.patch("app.config.settings") as mock_settings, \
     mock.patch("app.services.ollama_client.ollama_client") as mock_ollama:
    
    from app.lib.tools.external_search import arxiv_search
    from app.services.empirical.document_processor import EmpiricalProcessor
    from app.services.genesis_service import genesis_service
    from app.services.ferramenteiro_service import ferramenteiro_service

    class TestAdvancedFeatures(unittest.IsolatedAsyncioTestCase):
        
        # --- PHASE 2: External Search ---
        async def test_arxiv_search_logic(self):
            mock_result = mock.MagicMock()
            mock_result.title = "Test Paper"
            mock_result.summary = "Test Summary"
            mock_result.entry_id = "http://arxiv.org/abs/1234.5678"
            mock_result.published.strftime.return_value = "2024-01-01"
            
            # Patch the library at the module level
            import arxiv
            with mock.patch("arxiv.Search") as mock_search_class:
                mock_search_instance = mock_search_class.return_value
                mock_search_instance.results.return_value = [mock_result]
                
                results = arxiv_search("machine learning")
                self.assertEqual(len(results), 1)
                self.assertIn("Test Paper", results[0]["title"])

        # --- PHASE 3: Empirical Processor ---
        async def test_empirical_csv_processor(self):
            import pandas as pd
            mock_df = mock.MagicMock()
            mock_df.to_string.return_value = "alice, 30"
            pd.read_csv.return_value = mock_df
            
            processor = EmpiricalProcessor()
            text = await processor.process_csv(b"fake_csv")
            self.assertIn("alice", text)

        async def test_empirical_pdf_processor(self):
            import fitz
            mock_doc = mock.MagicMock()
            mock_page = mock.MagicMock()
            mock_page.get_text.return_value = "Extracted PDF Text"
            mock_doc.__iter__.return_value = [mock_page]
            fitz.open.return_value = mock_doc
            
            processor = EmpiricalProcessor()
            text = await processor.process_pdf(b"fake_pdf")
            self.assertEqual(text, "Extracted PDF Text")

        # --- PHASE 4: Genesis Service ---
        async def test_genesis_service_parsing(self):
            # Mocking the generator response
            async def mock_gen(*args, **kwargs):
                yield {"content": "```json\n{\"name\": \"Tesla\", \"description\": \"Engenheiro\", \"type\": \"THEORETICAL\", \"system_prompt\": \"Prompt de teste\"}\n```"}
            
            mock_ollama.chat_stream.side_effect = mock_gen
            
            alma = await genesis_service.generate_alma("Crie um engenheiro")
            self.assertEqual(alma["name"], "Tesla")
            self.assertEqual(alma["type"], "THEORETICAL")

        # --- PHASE 4: Ferramenteiro Service ---
        def test_ferramenteiro_sandbox_success(self):
            code = "x = 10 + 5\nprint(f'Result: {x}')"
            result = ferramenteiro_service.execute_code(code)
            self.assertTrue(result["success"])
            self.assertIn("Result: 15", result["stdout"])
            self.assertEqual(result["context"]["x"], 15)

        def test_ferramenteiro_sandbox_error(self):
            code = "y = 10 / 0"
            result = ferramenteiro_service.execute_code(code)
            self.assertFalse(result["success"])
            self.assertIn("ZeroDivisionError", result["stderr"])

if __name__ == "__main__":
    unittest.main()
