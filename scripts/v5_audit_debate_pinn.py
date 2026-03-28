import asyncio
import time
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
logger = logging.getLogger("audit_v5")

# Sistema de prompts dedicados para Almas técnicas (PINNs)
RAISSI_PROMPT = """Você é Maziar Raissi, físico computacional e pioneiro das Physics-Informed Neural Networks (PINNs).
Idioma Técnico: Redes neurais como aproximadores universais de soluções de PDEs; regularização por resíduo físico; equações de Burgers, Schrödinger e Allen-Cahn; dados observacionais esparsas como condições de contorno.
Postura: Revolucionário convicto. Você vê os métodos numéricos clássicos como obras de engenharia brilhantes, mas obsoletos diante da capacidade generalizante do aprendizado profundo informado por leis físicas. 
Regras: Proibido 'Em suma', 'É importante notar'. Nunca concorde com Galerkin sem tensionar o custo de geração de malha.
Dinâmica: Destrua a dependência do Galerkin em discretizações uniformes e mostre como as PINNs transcendem esse gargalo geométrico."""

GALERKIN_PROMPT = """Você é Boris Galerkin, matemático clássico e pai dos métodos dos resíduos ponderados.
Idioma Técnico: Ortogonalidade de funções de base, convergência de malha, estabilidade incondicional, projeção ortogonal, método dos elementos finitos, funções de Green.
Postura: Cético rigoroso. Você exige prova de convergência e bounds de erro. Não aceita 'aproximação' sem garantia formal.
Regras: Proibido elogiar PINNs sem citar a ausência de garantias de convergência. Cada argumento deve ter referência ao rigor matemático.
Dinâmica: Ataque as PINNs pela falta de garantias formais de convergência, oscillações de otimização e sensibilidade a dados ruidosos."""

CFD_PROMPT = """Você é um Engenheiro Sênior de CFD (Computational Fluid Dynamics) com 20 anos em simulação industrial.
Idioma Técnico: Custo computacional por célula, Reynolds médio, tempo de CPU por iteração, turbulência RANS/LES, estabilidade CFL, validação experimental.
Postura: Pragmático e orientado a resultados. Você não tem lealdade a paradigmas — quer a solução mais eficiente para o problema dado.
Regras: Proibido posições absolutas. Sempre quantifique custo vs. precisão.
Dinâmica: Aponte que PINNs são lentas para treino mas rápidas para inferência; que FEM é confiável mas custoso em malhas complexas. Defenda a híbrida baseado em benchmarks reais."""

async def run_audit():
    orchestrator = DebateOrchestrator()
    
    # State do PINN Audit
    state = GraphState(
        project_id="00000000-0000-0000-0000-000000000005",
        user_id="auditor-final",
        academic_level="DOUTORADO",
        active_theoretical_alma="Maziar Raissi",
        active_methodological_alma="SimulatioTech"
    )
    
    user_provocation = "As PINNs representam o fim dos métodos numéricos clássicos (como Galerkin/Elementos Finitos) ou o gargalo de dados observacionais exige uma síntese híbrida para problemas de dinâmica de fluidos e mecânica quântica?"
    
    mock_db = AsyncMock()
    
    def make_alma(id, name, sys_prompt):
        a = MagicMock()
        a.id = id
        a.alma_name = name
        a.name = name
        a.category = "THEORETICAL"
        a.system_prompt = sys_prompt
        a.is_approved = True
        return a

    def make_meto(id, name, sys_prompt):
        a = MagicMock()
        a.id = id
        a.alma_name = name
        a.name = name
        a.category = "METHODOLOGICAL"
        a.system_prompt = sys_prompt
        a.is_approved = True
        return a

    almas = [
        make_alma("a1", "Maziar Raissi", RAISSI_PROMPT),
        make_alma("a2", "Boris Galerkin", GALERKIN_PROMPT),
        make_alma("a3", "CFD Engineer", CFD_PROMPT),
        make_meto("a4", "SimulatioTech", "Você é o Metodólogo. Sintetize o debate em Objetivo, Método e Instrumentos claros."),
    ]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = almas
    mock_db.execute.return_value = mock_result

    # Re-index almas para garantir busca semântica
    import app.services.qdrant_service as qs
    await qs.ensure_almas_collection()
    for a in almas:
        await qs.index_alma(a)

    report_path = "/app/debate_audit_report_v5.md"
    start_time = time.perf_counter()

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 🛡️ Relatório de Auditoria: RAG + PINNs + Robustez JSON (Teste 05)\n\n")
        f.write(f"**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Provocação**: {user_provocation}\n\n")
        f.write(f"> **Melhoria v5**: Implementação de `json-repair` no `ContextAnalyzer` e `DebateSynthesizer` para evitar falhas de parsing por ruído do LLM.\n\n")
        f.flush()

        logger.info("🚀 Iniciando Auditoria Teste 05 (com json-repair)...")
        current_turn = None
        turn_start = 0

        async for event in orchestrator.run(state, user_provocation, mock_db):
            etype = event.get("type")

            if etype == "panel_selected":
                f.write("## 👥 Painel Selecionado\n")
                panel = event.get("panel", {})
                for role, data in panel.items():
                    f.write(f"- **{role}**: {data.get('name', 'N/A')}\n")
                f.write("\n---\n\n")
                f.flush()

            elif etype == "debate_turn_start":
                current_turn = event.get("role")
                alma_name = event.get("alma_name")
                turn_start = time.perf_counter()
                f.write(f"### 🎙️ Turno {current_turn}: {alma_name}\n\n")
                logger.info(f" -> Turno {current_turn} iniciado...")
                f.flush()

            elif etype == "debate_chunk":
                content = event.get("content", "")
                if content:
                    f.write(content)
                    f.flush()

            elif etype == "debate_turn_end":
                dur = time.perf_counter() - turn_start
                f.write(f"\n\n**Métrica**: Latência = {dur:.2f}s\n\n")
                logger.info(f" <- Turno {current_turn} finalizado ({dur:.2f}s)")
                f.flush()

            elif etype == "debate_complete":
                f.write("\n\n---\n## 🏁 Síntese Final do Debate (Validada via json-repair)\n")
                summary = event.get("summary", {})
                if summary:
                    # Validar se o summary tem campos esperados
                    f.write(f"### Tensões Centrais\n")
                    for t in summary.get("core_tensions", []):
                        f.write(f"- {t}\n")
                    f.write(f"\n### Pontos de Consenso\n")
                    for c in summary.get("points_of_consensus", []):
                        f.write(f"- {c}\n")
                    f.write(f"\n### Pergunta para o Investigador\n")
                    f.write(f"> {summary.get('question_for_user', 'N/A')}\n")
                else:
                    f.write("\n**AVISO**: Sumário não gerado ou vazio.\n")
                
                logger.info(" ✅ Debate e Síntese Concluídos!")
                f.flush()

            elif etype == "error":
                logger.error(f"ERRO: {event}")
                f.write(f"\n\n**ERRO**: {event}\n")
                f.flush()
                raise RuntimeError(f"Pipeline error: {event}")

    total = time.perf_counter() - start_time
    print(f"\n✨ Relatório gerado: {report_path} ({total:.1f}s total)")

if __name__ == "__main__":
    asyncio.run(run_audit())
