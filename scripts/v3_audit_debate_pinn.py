import asyncio
import time
import json
import logging
import os
import sys
from datetime import datetime
from uuid import UUID

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.debate.debate_orchestrator import DebateOrchestrator
from app.state.graph_state import GraphState
from unittest.mock import AsyncMock, MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("audit_v3")

async def run_audit():
    orchestrator = DebateOrchestrator()
    
    project_uuid = "00000000-0000-0000-0000-000000000003"
    
    # --- MOCK STATE & CONTEXT ---
    state = GraphState(
        project_id=project_uuid,
        user_id="auditor-final",
        academic_level="DOUTORADO",
        active_theoretical_alma="Raissi", # Will be chosen or ignored by auto
        active_methodological_alma="METODOLOGO"
    )
    
    user_provocation = "As PINNs representam o fim dos métodos numéricos clássicos (como Galerkin/Elementos Finitos) ou o gargalo de dados observacionais exige uma síntese híbrida para problemas de dinâmica de fluidos e mecânica quântica?"
    
    # --- MOCK DB (Realistic Almas created in previous script) ---
    mock_db = AsyncMock()
    
    def create_mock_alma(id, name, type, system_prompt):
        alma = MagicMock()
        alma.id = id
        alma.alma_name = name
        alma.name = name
        alma.category = type
        alma.system_prompt = system_prompt
        alma.is_approved = True
        return alma

    almas = [
        create_mock_alma("6246766e-5ff0-510e-eb83-c64b173c7956", "Maziar Raissi", "THEORETICAL", 
            'És o Agente Génesis, arquiteto de Almas académicas de elite.\n\nIdiomas Técnicos: PINN, aproximação universal, equações diferenciais parciais (PDEs), descoberta de dados e aprendizado profundo informado pela física.\nPostura: Inovador incansável e subversivo.\nRegras de Escrita: Proibidas frases prontas como "É importante notar" ou "Em suma".\nDinâmica: Desconstróis métodos clássicos (Galerkin) por sua dependência a malhas e promoves PINNs por sua independência estatística. Foca-se em leis físicas e dados.'),
        create_mock_alma("e0e75-0f91-f6bb-6811-e47e7e9ed93", "Boris Galerkin", "THEORETICAL", 
            'Idiomas Técnicos: método dos resíduos ponderados, continuidade e ortogonalidade das funções de base, convergência de malha finita, projeção ortogonal, estabilidade incondicional.\nPostura: O cético conservador, focado na solidez matemática e em métodos rigorosos clássicos.\nRegras de Escrita: Nenhuma frase pronta ou linguagem moderna sem base teórica.\nDinâmica: Ataque as PINNs como algoritmos probabilísticos não convergentes.'),
        create_mock_alma("a3", "CFD Engineer", "THEORETICAL", 
            'Idiomas Técnicos: malha, custo computacional, convergência, tempo real, dinâmica dos fluidos computacional (CFD).\nPostura: Pragmático e industrial.\nRegras de Escrita: Proibido "Em suma", "É importante notar".\nDinâmica: Aponta gargalos de dados nas PINNs e custo de geração de mesh em Galerkin, defendendo abordagens híbridas.'),
        create_mock_alma("a4", "SimulatioTech", "METHODOLOGICAL", 
            "Você é o Metodólogo e Engenheiro de Software. Foque na viabilidade da pesquisa para software escalável.")
    ]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = almas
    mock_db.execute.return_value = mock_result
    
    # Enable Qdrant check
    import app.services.qdrant_service as qs
    await qs.ensure_almas_collection()
    
    # Re-index to ensure consistency
    for a in almas:
        await qs.index_alma(a)
    
    # --- AUDIT LOG INITIALIZATION ---
    report_path = "/app/debate_audit_report_v3.md"
    start_time = time.perf_counter()
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 🛡️ Relatório de Auditoria: RAG + PINNs (Teste 03)\n\n")
        f.write(f"**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Provocação**: {user_provocation}\n")
        f.write(f"**Projeto de RAG**: {project_uuid}\n\n")
        f.flush()
        
        logger.info(f"🚀 Iniciando Auditoria de Debate Complexo...")
        
        current_turn = None
        turn_start_time = 0
        
        async for event in orchestrator.run(state, user_provocation, mock_db):
            event_type = event.get("type")
            
            if event_type == "panel_selected":
                f.write(f"## 👥 Painel Selecionado\n")
                for role, data in event["panel"].items():
                    f.write(f"- **{role}**: {data.get('name', '')}\n")
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
                
            elif event_type == "error":
                logger.error(f"ERRO: {event}")
                f.write(f"\n\n**ERRO no Pipeline**: {event}\n")
                f.flush()

    print(f"\n✨ Relatório gerado: {report_path}")

if __name__ == "__main__":
    asyncio.run(run_audit())
