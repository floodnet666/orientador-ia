import pytest
import sys
import os

# Adiciona o diretório /app ao sys.path para permitir importações do pacote 'app'
# No Docker, o código está em /app/app, então o root para o pacote 'app' é /app
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

try:
    from app.agents.graph_factory import backend_graph
except ImportError as e:
    print(f"[FAILED] Erro de importação: {e}")
    sys.exit(1)
from app.services.genesis_service import GENESIS_SYSTEM_PROMPT

def test_graph_import_integrity():
    """
    XP/TDD: Valida se a correção do import de AsyncSessionLocal surtiu efeito.
    Se falhar, significa que o ModuleNotFoundError: 'app.db' ainda persiste.
    """
    assert backend_graph is not None
    print("\n[PASSED] Grafo de Backend instanciado com sucesso (Integridade de Importação: OK)")

def test_genesis_language_guardrails():
    """
    XP/TDD: Valida se as correções de idioma foram aplicadas ao prompt mestre.
    """
    assert "SOBERANIA LINGUÍSTICA" in GENESIS_SYSTEM_PROMPT
    assert "Português do Brasil" in GENESIS_SYSTEM_PROMPT
    assert "Responda sempre em Português do Brasil" in GENESIS_SYSTEM_PROMPT
    print("[PASSED] Guardrails de Soberania Linguística detectados no Genesis (Idioma: OK)")

if __name__ == "__main__":
    # Permite execução direta para debug rápido se necessário
    test_graph_import_integrity()
    test_genesis_language_guardrails()
