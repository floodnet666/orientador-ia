import asyncio
import sys
import os

# Adiciona o diretório backend ao sys.path para importação do pacote 'app'
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_root)

async def test_genesis():
    try:
        from app.services.genesis_service import genesis_service
        from app.config import settings
        
        print(f"DEBUG: Usando modelo {settings.OLLAMA_ORCHESTRATOR_MODEL} para o teste.")
        
        test_prompt = "Uma Alma que analisa políticas públicas sob a ótica de Hannah Arendt, focada na banalidade do mal e espaço público."
        print(f"PROMPT: {test_prompt}")
        print("--- Gerando Alma (isto pode demorar alguns segundos) ---")
        
        alma = await genesis_service.generate_alma(test_prompt)
        
        print("\nSUCCESS: Alma gerada com sucesso:")
        print(f"NOME: {alma.get('name')}")
        print(f"DESCRIÇÃO: {alma.get('description')}")
        print(f"TIPO: {alma.get('type')}")
        print(f"SYSTEM PROMPT (Primeiros 100 caracteres): {alma.get('system_prompt')[:100]}...")
        
        # Validação básica de campos
        required_fields = ["name", "description", "type", "system_prompt"]
        for field in required_fields:
            if field not in alma:
                print(f"ERROR: Campo '{field}' ausente no JSON gerado.")
                sys.exit(1)
        
        sys.exit(0)
        
    except Exception as e:
        print(f"ERROR: Falha catastrófica no teste funcional: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_genesis())
