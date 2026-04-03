import asyncio
import sys
import os
import json

# Sync path for app package
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

# Force Host-to-Host connectivity
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

from app.services.genesis_service import genesis_service

# --- CONFIG ---
TARGET_VARIANTS = ["V2_ORIGINAL", "V3_SYNTHESIS_ELITE", "V10_SURGICAL_Forge"]
script_dir = os.path.dirname(os.path.abspath(__file__))
SPEC_PATH = os.path.join(script_dir, "genesis_benchmark_spec.json")
VARIANTS_PATH = os.path.join(script_dir, "genesis_prompts_variants.json")
OUTPUT_PATH = os.path.join(script_dir, "genesis_almas_v15.json")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

async def prepare_souls():
    spec = load_json(SPEC_PATH)
    variants_all = load_json(VARIANTS_PATH)["variants"]
    variants = [v for v in variants_all if v["id"] in TARGET_VARIANTS]
    authors = spec["authors"]
    
    almas_dump = {}
    if os.path.exists(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                almas_dump = json.load(f)
        except:
            almas_dump = {}

    print(f"🧬 [PHASE 1: GENESIS] Preparando 15 Almas (v15.3 - Incremental)")
    
    for v in variants:
        v_id = v["id"]
        if v_id not in almas_dump:
            almas_dump[v_id] = {}
            
        print(f"\n🔬 [VARIANTE] {v_id}")
        
        for author in authors:
            a_name = author["name"]
            
            # Skip if already in dump
            if a_name in almas_dump[v_id]:
                print(f"   👨‍🏫 '{a_name}' já existe. [SKIP]")
                continue
                
            a_bio = author["bio_prompt"]
            print(f"   👨‍🏫 Criando '{a_name}'...", end="", flush=True)
            
            try:
                # Geração da Alma (Apenas uma vez!)
                alma_data = await genesis_service.generate_alma(a_bio, system_prompt=v["content"])
                sys_prompt = alma_data.get("system_prompt", "")
                
                if not sys_prompt:
                    raise ValueError("System Prompt Vazio")
                
                almas_dump[v_id][a_name] = sys_prompt
                
                # Incremental Save
                with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                    json.dump(almas_dump, f, indent=2, ensure_ascii=False)
                
                print(f" [OK]")
            except Exception as e:
                print(f" [FAIL] {repr(e)}")
        
    print(f"\n✅ Base de Almas v15.0 consolidada: {OUTPUT_PATH}")

if __name__ == "__main__":
    asyncio.run(prepare_souls())
