import asyncio
import logging
import os
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.sql_models import User, Project, ProjectCanvasState
from app.agents.graph_factory import backend_graph
from langchain_core.messages import HumanMessage

# Configurar logs para ver o progresso
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_real_debate")

async def run_real_debate():
    print("\n🚀 INICIANDO TESTE REAL DE DEBATE (BACKEND v9.2.4)\n")
    
    async with AsyncSessionLocal() as db:
        # Puxar o projeto de teste específico com o canvas carregado
        project_id = "afb8417a-db10-4c82-b3bf-eff22b9d8b28"
        try:
            stmt = select(Project).filter(Project.id == project_id).options(selectinload(Project.canvas_state))
            proj_res = await db.execute(stmt)
            project = proj_res.scalar_one_or_none()
        except Exception:
            project = None
        
        if not project:
            print(f"⚠️  Aviso: Projeto {project_id} não encontrado. Tentando pegar o primeiro disponível.")
            stmt = select(Project).limit(1).options(selectinload(Project.canvas_state))
            proj_res = await db.execute(stmt)
            project = proj_res.scalar_one_or_none()

        if not project:
            print("❌ Erro Fatal: Nenhum projeto encontrado no banco de dados.")
            return

        user_res = await db.execute(select(User).limit(1))
        user = user_res.scalar_one_or_none()

        print(f"🔹 Projeto: {project.id} ({project.title})")
        print(f"🔹 User: {user.email}")
        
        # 1. Preparar o estado
        canvas_data = project.canvas_state.canvas_json if project.canvas_state else {}
        state = {
            "messages": [HumanMessage(content="/debate Vamos analisar o rigor metodológico das medições")],
            "project_id": str(project.id),
            "user_id": str(user.id),
            "canvas_summary": str(canvas_data.get("problema", {}).get("content", "Sem problema definido")),
            "rag_context": None,
            "next_node": "maestro",
            "is_debate": False
        }

        print("\n🧠 Executando Grafo Maestro -> Subgrafo Debate...")
        
        # 2. Iterar sobre todos os eventos do gráfico
        async for event in backend_graph.astream_events(state, version="v2"):
            kind = event["event"]
            name = event.get("name")
            
            # Capturar o início do debate
            if kind == "on_chain_start" and name == "debate":
                 print("\n🔥 [DEBATE] Subgrafo Ativado!")

            # Capturar o final de cada turno das almas
            if kind == "on_chain_end" and name == "_execute_turn":
                output = event.get("data", {}).get("output", {})
                new_turns = output.get("turns", [])
                if new_turns:
                    latest = new_turns[-1]
                    print(f"\n🗣️  RESPOSTA DE {latest['alma_name']} ({latest['alma_role'].upper()}):")
                    print("-" * 60)
                    print(latest["content"])
                    print("-" * 60)

            # Capturar a síntese final
            if kind == "on_chain_end" and name == "synthesis_node":
                output = event.get("data", {}).get("output", {})
                print("\n📝 SÍNTESE FINAL DO DEBATE:")
                print("=" * 60)
                print(output.get("synthesis", "Sem síntese gerada"))
                print("=" * 60)
                
    print("\n✅ TESTE REAL CONCLUÍDO COM SUCESSO.")

if __name__ == "__main__":
    asyncio.run(run_real_debate())
