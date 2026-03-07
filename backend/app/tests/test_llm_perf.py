import asyncio
import time
import json
import httpx
from typing import Dict, Any, List

# Configuração baseada no .env
OLLAMA_URL = "http://ollama:11434"
MODELS_TO_TEST = ["qwen3.5:4b", "qwen3.5:0.8b"]
TEST_PROMPTS = [
    "Explique o conceito de biopoder em Foucault.",
    "Como a educação libertadora de Paulo Freire se aplica ao ensino superior?",
    "Quais são os principais instrumentos de coleta de dados em uma pesquisa etnográfica?"
]

async def test_model_performance(model: str, prompt: str) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    
    start_time = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=300.0, base_url=OLLAMA_URL) as client:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            end_time = time.perf_counter()
            
            duration = end_time - start_time
            content = data["message"]["content"]
            # Estimativa simples de tokens (1 token approx 4 chars para PT)
            token_count = len(content) / 4 
            tpm = (token_count / duration) * 60
            
            return {
                "success": True,
                "model": model,
                "duration": round(duration, 2),
                "tokens": int(token_count),
                "tpm": round(tpm, 2),
                "error": None
            }
    except Exception as e:
        return {
            "success": False,
            "model": model,
            "duration": 0,
            "tokens": 0,
            "tpm": 0,
            "error": str(e)
        }

async def run_full_suite():
    print(f"=======================================================")
    print(f"🚀 Iniciando Testes de Performance de LLMs")
    print(f"=======================================================\n")
    
    all_results = []
    for model in MODELS_TO_TEST:
        print(f"Testando Modelo: {model}")
        for prompt in TEST_PROMPTS:
            print(f"  > Prompt: {prompt[:50]}...")
            result = await test_model_performance(model, prompt)
            all_results.append(result)
            if result["success"]:
                print(f"    ✅ Sucesso | Tempo: {result['duration']}s | TPM: {result['tpm']}")
            else:
                print(f"    ❌ Falha   | Erro: {result['error']}")
        print()

    # Métricas Agregadas
    total_tests = len(all_results)
    success_count = sum(1 for r in all_results if r["success"])
    success_rate = (success_count / total_tests) * 100
    avg_duration = sum(r["duration"] for r in all_results if r["success"]) / success_count if success_count > 0 else 0
    avg_tpm = sum(r["tpm"] for r in all_results if r["success"]) / success_count if success_count > 0 else 0

    print(f"=======================================================")
    print(f"📊 Relatório Final")
    print(f"=======================================================")
    print(f"Total de Testes: {total_tests}")
    print(f"Taxa de Sucesso: {success_rate}%")
    print(f"Tempo Médio de Resposta: {round(avg_duration, 2)}s")
    print(f"TPM Médio: {round(avg_tpm, 2)}")
    
    if success_rate < 100:
        print(f"\n[FALHA] A meta de 100% de sucesso não foi atingida.")
        exit(1)
    else:
        print(f"\n[PASSOU] Testes realizados com 100% de sucesso.")
        exit(0)

if __name__ == "__main__":
    asyncio.run(run_full_suite())
