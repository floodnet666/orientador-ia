import asyncio
import sys
import os
import json
import time
import re

# Sync path for app package
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.services.ollama_client import ollama_client
from app.config import settings

# --- CONFIG ---
TARGET_VARIANTS = ["V2_ORIGINAL", "V3_SYNTHESIS_ELITE", "V10_SURGICAL_Forge"]
SPEC_PATH = os.path.join(backend_root, "tests", "genesis_benchmark_spec.json")
VARIANTS_PATH = os.path.join(backend_root, "tests", "genesis_prompts_variants.json")
REPORT_PATH = os.path.join(backend_root, "tests", "deep_lab_audit.md")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

async def get_alma_prompt(variant_content, author_bio):
    """Generates the system_prompt for an Alma using a specific variant."""
    response_text = ""
    async for chunk in ollama_client.chat_stream(
        model=settings.OLLAMA_ORCHESTRATOR_MODEL,
        messages=[
            {"role": "system", "content": variant_content},
            {"role": "user", "content": f"Gere a alma de: {author_bio}\nReturn JSON."}
        ]
    ):
        response_text += chunk
    
    # Robust Extract (v11.2 logic)
    clean_json = response_text
    if "```json" in clean_json:
        clean_json = clean_json.split("```json")[1].split("```")[0]
    elif "```" in clean_json:
        clean_json = clean_json.split("```")[1].split("```")[0]
    
    data = json.loads(clean_json.strip())
    # Try all known keys
    sys_content = data.get("system_prompt", data.get("systemPrompt", data.get("prompt", "")))
    if not sys_content and "alma" in data:
        sys_content = data["alma"]
    
    # If it's still an object/list, stringify it
    if not isinstance(sys_content, str):
        sys_content = json.dumps(sys_content, ensure_ascii=False)
        
    return sys_content

async def run_deep_lab():
    spec = load_json(SPEC_PATH)
    variants_all = load_json(VARIANTS_PATH)["variants"]
    variants = [v for v in variants_all if v["id"] in TARGET_VARIANTS]
    authors = spec["authors"]
    
    report_md = "# Relatório de Auditoria Genesis: Deep Lab v12\n\n"
    report_md += f"**Modelo:** {settings.OLLAMA_ORCHESTRATOR_MODEL} | **Data:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report_md += "--- \n\n"

    print(f"🚀 INICIANDO DEEP LAB (75 Interações) | 3 Variantes x 5 Autores")

    for author in authors:
        a_name = author["name"]
        a_bio = author["bio_prompt"]
        print(f"\n👨‍🏫 Autor: {a_name}")
        report_md += f"## Autor: {a_name}\n> {a_bio}\n\n"
        
        for v in variants:
            v_id = v["id"]
            print(f"  Testing Variant: {v_id}...", end="", flush=True)
            report_md += f"### Variante: {v_id}\n\n"
            
            try:
                # 1. Gerar a Alma
                sys_prompt = await get_alma_prompt(v["content"], a_bio)
                report_md += "**System Prompt Gerado (Preview):**\n```text\n" + sys_prompt[:250] + "...\n```\n\n"
                
                # 2. Interrogatório (5 perguntas)
                chat_history = []
                report_md += "| No. | Pergunta | Resposta |\n|---|---|---|\n"
                
                for idx, q in enumerate(author["questions"], 1):
                    chat_history.append({"role": "user", "content": q})
                    
                    answer = ""
                    async for chunk in ollama_client.chat_stream(
                        model=settings.OLLAMA_ORCHESTRATOR_MODEL,
                        messages=chat_history,
                        system=sys_prompt
                    ):
                        answer += chunk
                    
                    chat_history.append({"role": "assistant", "content": answer})
                    report_md += f"| {idx} | {q} | {answer.strip().replace('|', '&#124;')} |\n"
                
                report_md += "\n"
                print(" [OK]")
                
            except Exception as e:
                print(f" [FAIL] {e}")
                report_md += f"> ❌ Erro na execução desta variante: {e}\n\n"

    # Save Report
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)
    
    print(f"\n✅ Deep Lab Concluído. Relatório disponível em: {REPORT_PATH}")

if __name__ == "__main__":
    asyncio.run(run_deep_lab())
