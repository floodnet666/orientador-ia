import sys
import os

# Adiciona o diretório backend ao sys.path para importação do app
sys.path.append(os.path.join(os.getcwd(), "app"))

try:
    from app.services.genesis_service import genesis_service
    from app.agents.orchestrator import orchestrate
    from app.agents.debate.panel_selector import panel_selector_agent
    from app.agents.debate.context_analyzer import context_analyzer_agent
    
    print("SUCCESS (GREEN): Todos os serviços importados com sucesso sem referências a 'OLLAMA_GUARDRAIL_MODEL'.")
    sys.exit(0)
except AttributeError as e:
    print(f"FAILURE: Atributo ausente detectado em runtime: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Erro inesperado na verificação: {type(e).__name__}: {e}")
    sys.exit(1)
