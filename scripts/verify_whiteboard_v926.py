import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.sql_models import User, Project
from app.agents.graph_factory import backend_graph
from langchain_core.messages import HumanMessage

# Configurar logs para ver o progresso
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_whiteboard")

async def test_whiteboard_flow():
    print("\n🚀 INICIANDO TESTE DE FLUXO WHITEBOARD (v9.2.6)\n")
    
    async with AsyncSessionLocal() as db:
        project_id = "afb8417a-db10-4c82-b3bf-eff22b9d8b28"
        stmt = select(Project).filter(Project.id == project_id).options(selectinload(Project.canvas_state))
        proj_res = await db.execute(stmt)
        project = proj_res.scalar_one_or_none()
        
        if not project:
            print("❌ Erro: Projeto não encontrado.")
            return

        user_res = await db.execute(select(User).limit(1))
        user = user_res.scalar_one_or_none()

        # Forçar o Maestro a pedir um desenho
        state = {
            "messages": [HumanMessage(content="Desenha um grafo com o conceito 'Energia Escura' no whiteboard")],
            "project_id": str(project.id),
            "user_id": str(user.id),
            "canvas_summary": "Projeto sobre física",
            "rag_context": None,
            "next_node": "maestro",
            "is_debate": False
        }

        print("\n🧠 Executando Grafo... Aguardando Tool Call + Persistência...")
        
        async for event in backend_graph.astream_events(state, version="v2"):
            kind = event["event"]
            name = event.get("name")
            
            if kind == "on_tool_start":
                print(f"🛠️  TOOL START: {name} | Args: {event['data'].get('input')}")

            if kind == "on_tool_end":
                print(f"✅ TOOL END: {name}")
                # Aqui o chat.py (no fluxo real) faria a persistência. 
                # No terminal, vamos apenas verificar se a tool foi chamada.
                
    print("\n✅ TESTE DE FLUXO CONCLUÍDO.")

if __name__ == "__main__":
    asyncio.run(test_whiteboard_flow())
