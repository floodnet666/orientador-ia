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
REPORT_PATH = os.path.join(backend_root, "tests", "deep_lab_audit_robust.md")
OLLAMA_URL = f"{settings.OLLAMA_BASE_URL}/api/chat"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

async def get_alma_prompt(client, variant_content, author_bio):
    """Generates the system_prompt with extended timeout (900s)."""
    payload = {
        "model": settings.OLLAMA_ORCHESTRATOR_MODEL,
        "messages": [
            {"role": "system", "content": variant_content},
            {"role": "user", "content": f"Gere a alma de: {author_bio}\nReturn JSON."}
        ],
        "stream": False,
        "options": {"num_ctx": 4096, "temperature": 0.1}
    }
    # Robust Timeout for context loading (900s)
    resp = await client.post(OLLAMA_URL, json=payload, timeout=900.0)
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

async def run_robust_deep_lab():
    spec = load_json(SPEC_PATH)
    variants_all = load_json(VARIANTS_PATH)["variants"]
    variants = [v for v in variants_all if v["id"] in TARGET_VARIANTS]
    authors = spec["authors"]
    
    # Header do Relatório v13.3
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# Relatório de Auditoria Robusta: Deep Lab v13.3\n\n")
        f.write(f"**Modo: TIMEOUT ESTENDIDO (900s) | OLLAMA WINDOWS HOST** | **Data:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("--- \n\n")

    print(f"🚀 INICIANDO DEEP LAB ROBUSTO (75 Interações) | Windows Host Mode")

    for v in variants:
        v_id = v["id"]
        print(f"\n🔬 Variante: {v_id}")
        
        with open(REPORT_PATH, "a", encoding="utf-8") as f:
            f.write(f"# VARIANTE: {v_id}\n\n")
            
        for author in authors:
            a_name = author["name"]
            a_bio = author["bio_prompt"]
            print(f"  👨‍🏫 Autor: {a_name} (Sessão Robusta)...", end="", flush=True)
            
            with open(REPORT_PATH, "a", encoding="utf-8") as f:
                f.write(f"## Autor: {a_name}\n> {a_bio}\n\n")
            
            try:
                # 1. Fresh Client per Author Session (Purge between authors)
                async with httpx.AsyncClient(timeout=900.0) as client:
                    # 1a. Gerar a Alma (O momento mais pesado)
                    sys_prompt = await get_alma_prompt(client, v["content"], a_bio)
                    
                    with open(REPORT_PATH, "a", encoding="utf-8") as f:
                        f.write("**System Prompt (Extracted):**\n```text\n" + sys_prompt[:400] + "...\n```\n\n")
                        f.write("| Pergunta | Resposta |\n|---|---|\n")
                    
                    # 1b. Interrogatório (Cache de sessão ativo dentro deste loop)
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
                        
                        # Timeout de interação (300s é suficiente após o primeiro load)
                        resp = await client.post(OLLAMA_URL, json=payload, timeout=300.0)
                        answer = resp.json()["message"]["content"]
                        
                        chat_history.append({"role": "assistant", "content": answer})
                        
                        # Append Imediato
                        with open(REPORT_PATH, "a", encoding="utf-8") as f:
                            f.write(f"| {q} | {answer.strip().replace('|', '&#124;')} |\n")
                
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write("\n")
                print(" [OK]")
                
                await asyncio.sleep(3) # Delay para flushing de rede host

            except Exception as e:
                err_msg = repr(e)
                print(f" [FAIL] {err_msg}")
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write(f"> ❌ Falha Diagnóstica: {err_msg}\n\n")

    print(f"\n✅ Auditoria Robusta Concluída. Relatório: {REPORT_PATH}")

if __name__ == "__main__":
    asyncio.run(run_robust_deep_lab())
