import sys
import os
import pytest

# Garante que o diretório atual (backend/) está no path
current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print(f"PYTHONPATH manually set to: {current_dir}")
sys.exit(pytest.main(["-v", "tests/test_pdf_section_indexer.py"]))
