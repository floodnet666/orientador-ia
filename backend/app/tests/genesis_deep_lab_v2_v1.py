import asyncio
import sys
import os
import json
import time
import httpx

# Sync path for app package
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.config import settings

# --- CONFIG ---
TARGET_VARIANTS = ["V2_ORIGINAL", "V3_SYNTHESIS_ELITE", "V10_SURGICAL_Forge"]
SPEC_PATH = os.path.join(backend_root, "tests", "genesis_benchmark_spec.json")
VARIANTS_PATH = os.path.join(backend_root, "tests", "genesis_prompts_variants.json")
REPORT_PATH = os.path.join(backend_root, "tests", "deep_lab_audit_isolated.md")
OLLAMA_URL = f"{settings.OLLAMA_BASE_URL}/api/chat"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

async def get_alma_prompt(variant_content, author_bio):
    """Generates the system_prompt for an Alma using a fresh, isolated request."""
    # Isolated Request for Genesis
    async with httpx.AsyncClient(timeout=300.0) as client:
        payload = {
            "model": settings.OLLAMA_ORCHESTRATOR_MODEL,
            "messages": [
                {"role": "system", "content": variant_content},
                {"role": "user", "content": f"Gere a alma de: {author_bio}\nReturn JSON."}
            ],
            "stream": False,
            "options": {"num_ctx": 4096, "temperature": 0.1}
        }
        resp = await client.post(OLLAMA_URL, json=payload)
        response_text = resp.json()["message"]["content"]

    # Robust Extract (v11.2 logic)
    clean_json = response_text
    if "```json" in clean_json:
        clean_json = clean_json.split("```json")[1].split("```")[0]
    elif "```" in clean_json:
        clean_json = clean_json.split("```")[1].split("```")[0]
    
    try:
        data = json.loads(clean_json.strip())
        sys_content = data.get("system_prompt", data.get("systemPrompt", data.get("prompt", "")))
        if not sys_content and "alma" in data:
            sys_content = data["alma"]
        
        if not isinstance(sys_content, str):
            sys_content = json.dumps(sys_content, ensure_ascii=False)
        return sys_content
    except:
        return response_text # Fallback to raw if logic fails

async def run_isolated_deep_lab():
    spec = load_json(SPEC_PATH)
    variants_all = load_json(VARIANTS_PATH)["variants"]
    variants = [v for v in variants_all if v["id"] in TARGET_VARIANTS]
    authors = spec["authors"]
    
    # Header do Relatório
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# Relatório de Auditoria Isolada: Deep Lab v13\n\n")
        f.write(f"**Modo: BLINDAEM DE KV CACHE ATIVA** | **Data:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("--- \n\n")

    print(f"🚀 INICIANDO DEEP LAB ISOLADO (75 Interações) | KV Cache Purge Mode")

    for author in authors:
        a_name = author["name"]
        a_bio = author["bio_prompt"]
        print(f"\n👨‍🏫 Autor: {a_name} (Sessão Isolada)")
        
        with open(REPORT_PATH, "a", encoding="utf-8") as f:
            f.write(f"## Autor: {a_name}\n> {a_bio}\n\n")
        
        for v in variants:
            v_id = v["id"]
            print(f"  Testing Variant: {v_id}...", end="", flush=True)
            
            with open(REPORT_PATH, "a", encoding="utf-8") as f:
                f.write(f"### Variante: {v_id}\n\n")
            
            try:
                # 1. Gerar a Alma (Flush Context)
                sys_prompt = await get_alma_prompt(v["content"], a_bio)
                
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write("**System Prompt Gerado (Base de Isolamento):**\n```text\n" + sys_prompt[:300] + "...\n```\n\n")
                    f.write("| Pergunta | Resposta |\n|---|---|\n")
                
                # 2. Interrogatório Isolado
                chat_history = []
                async with httpx.AsyncClient(timeout=300.0) as client:
                    for q in author["questions"]:
                        chat_history.append({"role": "user", "content": q})
                        
                        payload = {
                            "model": settings.OLLAMA_ORCHESTRATOR_MODEL,
                            "system": sys_prompt,
                            "messages": chat_history,
                            "stream": False,
                            "options": {"num_ctx": 4096, "temperature": 0.7}
                        }
                        
                        resp = await client.post(OLLAMA_URL, json=payload)
                        answer = resp.json()["message"]["content"]
                        
                        chat_history.append({"role": "assistant", "content": answer})
                        
                        # Escrita Incremental Imediata
                        with open(REPORT_PATH, "a", encoding="utf-8") as f:
                            f.write(f"| {q} | {answer.strip().replace('|', '&#124;')} |\n")
                
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write("\n")
                print(" [OK]")
                
                await asyncio.sleep(1) # VRAM Cooling / Cache Desorption

            except Exception as e:
                print(f" [FAIL] {e}")
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write(f"> ❌ Erro na execução desta variante: {e}\n\n")

    print(f"\n✅ Deep Lab Isolado Concluído. Relatório: {REPORT_PATH}")

if __name__ == "__main__":
    asyncio.run(run_isolated_deep_lab())
