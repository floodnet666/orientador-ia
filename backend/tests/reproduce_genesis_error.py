import sys
import os

# Adiciona o diretório backend ao sys.path para importação do app
sys.path.append(os.path.join(os.getcwd(), "app"))

try:
    from app.config import settings
    print(f"DEBUG: OLLAMA_CHAT_MODEL={settings.OLLAMA_CHAT_MODEL}")
    # Esta linha deve falhar se a regra de TDD for seguida (RED)
    print(f"DEBUG: OLLAMA_GUARDRAIL_MODEL={settings.OLLAMA_GUARDRAIL_MODEL}")
except AttributeError as e:
    print(f"SUCCESS (RED): Erro reproduzido conforme esperado: {e}")
    sys.exit(0)  # Reproduzido
except Exception as e:
    print(f"ERROR: Erro inesperado: {type(e).__name__}: {e}")
    sys.exit(1)

print("FAILURE: O atributo OLLAMA_GUARDRAIL_MODEL ainda existe ou não falhou como esperado.")
sys.exit(1)
