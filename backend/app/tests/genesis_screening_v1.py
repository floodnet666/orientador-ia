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

# --- LOAD DATA ---

def load_variants():
    path = os.path.join(backend_root, "tests", "genesis_prompts_variants.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["variants"]

async def run_screening():
    variants = load_variants()
    # Autor base para triagem: Stephen Hawking
    author_bio = "Stephen Hawking, físico teórico focado em buracos negros e singularidades espaciais."
    
    results = []
    print(f"\n🧪 INICIANDO TRIAGEM GENESIS (10 Variantes) | Model: {settings.OLLAMA_ORCHESTRATOR_MODEL}")
    print("-" * 75)

    for v in variants:
        v_id = v["id"]
        v_content = v["content"]
        print(f"Testing {v_id}...", end="", flush=True)
        
        t0 = time.perf_counter()
        
        try:
            response_text = ""
            async for chunk in ollama_client.chat_stream(
                model=settings.OLLAMA_ORCHESTRATOR_MODEL,
                messages=[
                    {"role": "system", "content": v_content},
                    {"role": "user", "content": f"Gere a alma de: {author_bio}\nReturn JSON."}
                ]
            ):
                response_text += chunk
            
            elapsed = time.perf_counter() - t0
            
            # Clean and Parse
            clean_json = response_text
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0]
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0]
            
            data = json.loads(clean_json.strip())
            
            # Robust extraction: many variants might use different keys or nested objects
            sys_content = data.get("system_prompt", data.get("systemPrompt", data.get("prompt", "")))
            
            # If the model returned a list or dict, stringify it to count words
            if not isinstance(sys_content, str):
                sys_content = json.dumps(sys_content, ensure_ascii=False)
            
            word_count = len(sys_content.split())
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', sys_content))
            
            results.append({
                "id": v_id,
                "time": round(elapsed, 2),
                "json_ok": True,
                "words": word_count,
                "chinese": has_chinese,
                "keys": list(data.keys()),
                "preview": sys_content[:50].replace("\n", " ") + "..."
            })
            print(f" [DONE] {elapsed:.1f}s | Words: {word_count} | Keys: {list(data.keys())}")

        except Exception as e:
            print(f" [FAIL] {e}")
            results.append({
                "id": v_id,
                "time": 0,
                "json_ok": False,
                "words": 0,
                "chinese": False,
                "preview": "ERROR"
            })

    # --- PRINT FINAL TABLE ---
    print("\n" + "=" * 75)
    print(f"{'VARIANTE':<20} | {'TEMPO':<6} | {'JSON':<6} | {'WORDS':<6} | {'CHINESE'}")
    print("-" * 75)
    for r in results:
        print(f"{r['id']:<20} | {r['time']:<6} | {str(r['json_ok']):<6} | {r['words']:<6} | {str(r['chinese'])}")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(run_screening())
