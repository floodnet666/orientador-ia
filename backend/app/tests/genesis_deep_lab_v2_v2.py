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
REPORT_PATH = os.path.join(backend_root, "tests", "deep_lab_audit_isolated_v2.md")
OLLAMA_URL = f"{settings.OLLAMA_BASE_URL}/api/chat"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

async def get_alma_prompt(client, variant_content, author_bio):
    """Generates the system_prompt for an Alma using the provided client session."""
    payload = {
        "model": settings.OLLAMA_ORCHESTRATOR_MODEL,
        "messages": [
            {"role": "system", "content": variant_content},
            {"role": "user", "content": f"Gere a alma de: {author_bio}\nReturn JSON."}
        ],
        "stream": False,
        "options": {"num_ctx": 4096, "temperature": 0.1}
    }
    resp = await client.post(OLLAMA_URL, json=payload, timeout=300.0)
    response_text = resp.json()["message"]["content"]

    # Robust Extract
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
        return response_text

async def run_optimized_deep_lab():
    spec = load_json(SPEC_PATH)
    variants_all = load_json(VARIANTS_PATH)["variants"]
    variants = [v for v in variants_all if v["id"] in TARGET_VARIANTS]
    authors = spec["authors"]
    
    # Header do Relatório
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# Relatório de Auditoria Isolada: Deep Lab v13.2 (Session-Cache)\n\n")
        f.write(f"**Modo: ISOLAMENTO ENTRE ALMAS, CACHE INTERNO ATIVO** | **Data:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("--- \n\n")

    print(f"🚀 INICIANDO DEEP LAB ISOLADO v2 (75 Interações) | Session-Level Cache")

    for v in variants:
        v_id = v["id"]
        print(f"\n🔬 Variante: {v_id}")
        
        with open(REPORT_PATH, "a", encoding="utf-8") as f:
            f.write(f"# VARIANTE: {v_id}\n\n")
            
        for author in authors:
            a_name = author["name"]
            a_bio = author["bio_prompt"]
            print(f"  👨‍🏫 Autor: {a_name}...", end="", flush=True)
            
            with open(REPORT_PATH, "a", encoding="utf-8") as f:
                f.write(f"## Autor: {a_name}\n> {a_bio}\n\n")
            
            try:
                # 1. Fresh Client for this Author/Variant Session
                async with httpx.AsyncClient(timeout=300.0) as client:
                    # 1a. Gerar a Alma (Flush context inicial)
                    sys_prompt = await get_alma_prompt(client, v["content"], a_bio)
                    
                    with open(REPORT_PATH, "a", encoding="utf-8") as f:
                        f.write("**System Prompt (Preview):**\n```text\n" + sys_prompt[:300] + "...\n```\n\n")
                        f.write("| Pergunta | Resposta |\n|---|---|\n")
                    
                    # 1b. Interrogatório Persistente (5 perguntas com cache de sessão ativo)
                    chat_history = []
                    for q in author["questions"]:
                        chat_history.append({"role": "user", "content": q})
                        
                        payload = {
                            "model": settings.OLLAMA_ORCHESTRATOR_MODEL,
                            "system": sys_prompt,
                            "messages": chat_history,
                            "stream": False,
                            "options": {"num_ctx": 4096, "temperature": 0.7}
                        }
                        
                        resp = await client.post(OLLAMA_URL, json=payload, timeout=180.0)
                        answer = resp.json()["message"]["content"]
                        
                        chat_history.append({"role": "assistant", "content": answer})
                        
                        # Append Imediato
                        with open(REPORT_PATH, "a", encoding="utf-8") as f:
                            f.write(f"| {q} | {answer.strip().replace('|', '&#124;')} |\n")
                
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write("\n")
                print(" [OK]")
                
                await asyncio.sleep(2) # Cache Desorption Delay between authors

            except Exception as e:
                print(f" [FAIL] {e}")
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write(f"> ❌ Falha na Sessão Isolada: {e}\n\n")

    print(f"\n✅ Auditoria v13.2 Concluída. Relatório: {REPORT_PATH}")

if __name__ == "__main__":
    asyncio.run(run_optimized_deep_lab())
