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

from app.config import settings
from app.services.genesis_service import genesis_service
from app.agents.state import BackendState
from app.agents.llm import get_llm
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver

# --- CONFIG ---
TARGET_VARIANTS = ["V2_ORIGINAL", "V3_SYNTHESIS_ELITE", "V10_SURGICAL_Forge"]
# Local paths relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
SPEC_PATH = os.path.join(script_dir, "genesis_benchmark_spec.json")
VARIANTS_PATH = os.path.join(script_dir, "genesis_prompts_variants.json")
REPORT_PATH = os.path.join(script_dir, "deep_lab_audit_langgraph_v1.md")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- 1. Definindo o Grafo de Benchmark ---
# Um grafo simplificado que apenas recebe a alma e responde.
async def identity_node(state: BackendState) -> dict:
    """Nó que simula a resposta da Alma."""
    # O LLM é instanciado aqui com as configurações da Alma
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

async def run_langgraph_deep_lab():
    spec = load_json(SPEC_PATH)
    variants_all = load_json(VARIANTS_PATH)["variants"]
    variants = [v for v in variants_all if v["id"] in TARGET_VARIANTS]
    authors = spec["authors"]
    
    # Header do Relatório v14.1
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# Relatório de Auditoria LangGraph v14.1 (Nativo Host)\n\n")
        f.write(f"**Modo: LANGGRAPH STATE ISOLATION | OLLAMA WINDOWS HOST** | **Data:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("--- \n\n")

    print(f"🚀 INICIANDO DEEP LAB LANGGRAPH (75 Interações) | Host-to-Host Mode")

    for v in variants:
        v_id = v["id"]
        print(f"\n🔬 Variante: {v_id}")
        
        with open(REPORT_PATH, "a", encoding="utf-8") as f:
            f.write(f"# VARIANTE: {v_id}\n\n")
            
        for author in authors:
            a_name = author["name"]
            a_bio = author["bio_prompt"]
            print(f"  👨‍🏫 Autor: {a_name} (LangGraph Session)...", end="", flush=True)
            
            with open(REPORT_PATH, "a", encoding="utf-8") as f:
                f.write(f"## Autor: {a_name}\n> {a_bio}\n\n")
            
            try:
                # 1. Geração da Alma (Saber qual o System Prompt) com suporte a variante externa
                alma_data = await genesis_service.generate_alma(a_bio, system_prompt=v["content"])
                sys_prompt = alma_data.get("system_prompt", "")
                
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write("**System Prompt (Real Genesis Output):**\n```text\n" + sys_prompt[:400] + "...\n```\n\n")
                    f.write("| Pergunta | Resposta |\n|---|---|\n")

                # 2. Configuração de Thread Única para este Autor (Purge entre autores)
                config = {"configurable": {"thread_id": f"{v_id}_{a_name.replace(' ', '_')}"}}
                
                # 3. Interrogatório no Grafo
                for q in author["questions"]:
                    # Inicializamos o estado com a diretiva da alma
                    input_state = {
                        "messages": [HumanMessage(content=q)],
                        "orchestrator_directive": sys_prompt
                    }
                    
                    # Invocação do Grafo (LangGraph gerencia o histórico via checkpoint)
                    result = await app_graph.ainvoke(input_state, config)
                    
                    # Extrair a última resposta
                    last_msg = result["messages"][-1].content
                    
                    # Append Imediato ao Relatório
                    with open(REPORT_PATH, "a", encoding="utf-8") as f:
                        f.write(f"| {q} | {last_msg.strip().replace('|', '&#124;')} |\n")
                
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write("\n")
                print(" [OK]")

            except Exception as e:
                err_msg = repr(e)
                print(f" [FAIL] {err_msg}")
                with open(REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write(f"> ❌ Falha no Grafo: {err_msg}\n\n")

    print(f"\n✅ Auditoria LangGraph Concluída. Relatório: {REPORT_PATH}")

if __name__ == "__main__":
    asyncio.run(run_langgraph_deep_lab())
