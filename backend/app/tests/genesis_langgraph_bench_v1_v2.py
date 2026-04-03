import asyncio
import sys
import os
import json
import time

# Sync path for app package: tests -> app -> backend
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

# Force Host-to-Host connectivity for Ollama on Windows
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

from app.services.genesis_service import genesis_service
from app.agents.state import BackendState
from app.agents.llm import get_llm
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver

# --- CONFIG ---
TARGET_VARIANTS = ["V2_ORIGINAL", "V3_SYNTHESIS_ELITE", "V10_SURGICAL_Forge"]
script_dir = os.path.dirname(os.path.abspath(__file__))
SPEC_PATH = os.path.join(script_dir, "genesis_benchmark_spec.json")
VARIANTS_PATH = os.path.join(script_dir, "genesis_prompts_variants.json")
REPORT_PATH = os.path.join(script_dir, "deep_lab_audit_langgraph_v1.md")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- 1. Definindo o Grafo de Benchmark ---
async def identity_node(state: BackendState) -> dict:
    """Nó que simula a resposta da Alma."""
    # O system_prompt da alma está no estado
    sys_prompt = state.get("orchestrator_directive", "")
    
    # Invocamos o LLM com o histórico
    llm = get_llm(temperature=0.7)
    messages = [SystemMessage(content=sys_prompt)] + state["messages"]
    
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

# Construção do Grafo
workflow = StateGraph(BackendState)
workflow.add_node("identity", identity_node)
workflow.add_edge(START, "identity")
workflow.add_edge("identity", END)
memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)

async def run_visible_bench():
    spec = load_json(SPEC_PATH)
    variants_all = load_json(VARIANTS_PATH)["variants"]
    variants = [v for v in variants_all if v["id"] in TARGET_VARIANTS]
    authors = spec["authors"]
    
    print(f"\n" + "="*80)
    print(f"🚀 INICIANDO DEEP LAB VISIBLE (75 Interações) | v14.2 | Host Mode")
    print(f"="*80 + "\n")

    for v in variants:
        v_id = v["id"]
        print(f"\n🔬 [VARIANTE] {v_id}")
        print("-" * 50)
        
        with open(REPORT_PATH, "a", encoding="utf-8") as f:
            f.write(f"# VARIANTE: {v_id}\n\n")
            
        for author in authors:
            a_name = author["name"]
            a_bio = author["bio_prompt"]
            print(f"\n👨‍🏫 [AUTOR] {a_name}")
            print(f"   Bio: {a_bio}")
            
            with open(REPORT_PATH, "a", encoding="utf-8") as f:
                f.write(f"## Autor: {a_name}\n> {a_bio}\n\n")
            
            try:
                # 1. Geração da Alma
                t0 = time.perf_counter()
                print(f"   [GENESIS] Criando Alma...", end="", flush=True)
                alma_data = await genesis_service.generate_alma(a_bio, system_prompt=v["content"])
                sys_prompt = alma_data.get("system_prompt", "")
                t_alma = time.perf_counter() - t0
                print(f" DONE (%.2fs)" % t_alma)
                
                print(f"   [SYSTEM_PROMPT] Preview: {sys_prompt[:250]}...")
                
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write("**System Prompt (Real Genesis Output):**\n```text\n" + sys_prompt + "\n```\n\n")
                    f.write("| Pergunta | Resposta |\n|---|---|\n")

                # 2. Configuraçao de Thread (Isolation)
                config = {"configurable": {"thread_id": f"{v_id}_{a_name.replace(' ', '_')}"}}
                
                # 3. Interrogatório no Grafo
                for idx, q in enumerate(author["questions"], 1):
                    print(f"   [QUESTION {idx}/5]: {q}")
                    tq0 = time.perf_counter()
                    
                    input_state = {
                        "messages": [HumanMessage(content=q)],
                        "orchestrator_directive": sys_prompt
                    }
                    
                    print(f"   [LANGGRAPH] Procesando...", end="", flush=True)
                    result = await app_graph.ainvoke(input_state, config)
                    last_msg = result["messages"][-1].content
                    tq_end = time.perf_counter() - tq0
                    
                    print(f" DONE (%.2fs)" % tq_end)
                    print(f"   [ANSWER]: {last_msg[:150].strip()}...")
                    
                    # Persistência
                    with open(REPORT_PATH, "a", encoding="utf-8") as f:
                        f.write(f"| {q} | {last_msg.strip().replace('|', '&#124;')} |\n")
                
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write("\n")

            except Exception as e:
                err_msg = repr(e)
                print(f"\n   ❌ [FAIL] {err_msg}")
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write(f"> ❌ Falha no Grafo: {err_msg}\n\n")

    print(f"\n" + "="*80)
    print(f"✅ Auditoria Robusta Concluída v14.2. Relatório: {REPORT_PATH}")
    print(f"="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(run_visible_bench())
