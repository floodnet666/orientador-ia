import asyncio
import time
import json
import logging
import os
import sys
from datetime import datetime

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.debate.debate_orchestrator import DebateOrchestrator
from app.state.graph_state import GraphState
from unittest.mock import AsyncMock, MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("audit")

async def run_audit():
    orchestrator = DebateOrchestrator()
    
    # --- MOCK STATE & CONTEXT ---
    state = GraphState(
        project_id="audit-theoretical-quality",
        user_id="auditor-final",
        academic_level="DOUTORADO",
        active_theoretical_alma="FOUCAULT",
        active_methodological_alma="METODOLOGO"
    )
    
    user_provocation = "O conceito de biopoder em Foucault ainda é aplicável às redes sociais contemporâneas, ou precisamos de uma nova categoria metodológica para analisar o algoritmo como agente regulador?"
    
    # --- MOCK DB (Realistic Almas) ---
    mock_db = AsyncMock()
    
    class SimpleAlma:
        def __init__(self, id, name, type, system_prompt):
            self.id = id
            self.name = name
            self.alma_name = name
            self.alma_type = type
            self.system_prompt = system_prompt
            self.is_approved = True
            self.description = system_prompt[:200]

    def create_mock_alma(id, name, type, system_prompt):
        return SimpleAlma(id, name, type, system_prompt)

    almas = [
        create_mock_alma("a1", "FOUCAULT", "THEORETICAL", "Você é Michel Foucault. Analise o poder como uma rede de relações, focando em biopoder e vigilância."),
        create_mock_alma("a2", "Byung-Chul Han", "THEORETICAL", "Você é Byung-Chul Han. Analise a sociedade do cansaço, a transparência e a psicopolítica digital."),
        create_mock_alma("a3", "Deleuze", "THEORETICAL", "Você é Gilles Deleuze. Analise as sociedades de controle que substituem as sociedades disciplinares."),
        create_mock_alma("a4", "METODOLOGO", "METHODOLOGICAL", "Você é um Metodólogo de Pesquisa. Ajude a operacionalizar tensões teóricas em desenhos de pesquisa empíricos.")
    ]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = almas
    mock_db.execute.return_value = mock_result
    
    # --- INDEX ALMAS IN QDRANT (To avoid 400 error) ---
    from app.services.qdrant_service import index_alma, get_qdrant, ALMAS_COLLECTION
    logger.info("📡 Limpando e Indexando Almas no Qdrant para teste semântico...")
    q_client = get_qdrant()
    try:
        await q_client.delete_collection(ALMAS_COLLECTION)
    except Exception:
        pass
    
    for alma in almas:
        await index_alma(alma)
    
    # Wait for Qdrant and verify count
    await asyncio.sleep(2)
    coll_info = await q_client.get_collection(ALMAS_COLLECTION)
    logger.info(f"✅ Qdrant: {coll_info.points_count} pontos indexados.")
    
    # --- AUDIT LOG INITIALIZATION ---
    report_path = "/app/debate_audit_report.md"
    start_time = time.perf_counter()
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 🛡️ Relatório de Auditoria: Qualidade Teórica (Padrão Ouro)\n\n")
        f.write(f"**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Provocação**: {user_provocation}\n\n")
        f.flush()
        
        logger.info(f"🚀 Iniciando Auditoria de Qualidade...")
        
        current_turn = None
        turn_start_time = 0
        
        async for event in orchestrator.run(state, user_provocation, mock_db):
            event_type = event.get("type")
            # Logger debug
            # logger.info(f" -> EVENT: {event_type}")
            
            if event_type == "panel_selected":
                f.write(f"## 👥 Painel Selecionado\n")
                for role, data in event["panel"].items():
                    f.write(f"- **{role}**: {data['name']}\n")
                f.write("\n---\n\n")
                f.flush()
                
            elif event_type == "debate_turn_start":
                current_turn = event.get("role")
                alma_name = event.get("alma_name")
                turn_start_time = time.perf_counter()
                f.write(f"### 🎙️ Turno {current_turn}: {alma_name}\n\n")
                logger.info(f" -> Turno {current_turn} iniciado...")
                f.flush()
                
            elif event_type == "debate_chunk":
                content = event.get("content", "")
                if content:
                    f.write(content)
                    f.flush()
                
            elif event_type == "debate_turn_end":
                duration = time.perf_counter() - turn_start_time
                f.write(f"\n\n**Métrica**: Latência = {duration:.2f}s\n\n")
                logger.info(f" <- Turno {current_turn} finalizado ({duration:.2f}s)")
                f.flush()
                
            elif event_type == "debate_complete":
                f.write("\n\n---\n## 🏁 Fim do Debate\n")
                logger.info(" ✅ Auditoria Concluída!")
                f.flush()

    print(f"\n✨ Relatório gerado: {report_path}")

if __name__ == "__main__":
    asyncio.run(run_audit())
