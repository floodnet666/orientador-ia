from typing import Literal, Optional
from pydantic import BaseModel, Field
from app.lib import adk
from app.state.graph_state import GraphState
import re
import json
import logging
from app.config import settings

log = logging.getLogger("orchestrator")

ORCHESTRATOR_SYSTEM_PROMPT = """
Você é o Maestro (O Maestro), o orquestrador central do Orientador.IA. 
O seu único papel é analisar a mensagem do utilizador e o GraphState atual para decidir a próxima ação.

CLASSIFICAÇÃO DE INTENÇÃO (intent):
- SEARCH: O utilizador quer novos papers, fontes, bibliografia ou fazer pesquisas no ArXiv/internet.
- EXTRACTION: O utilizador chegou a uma conclusão e queres que os campos do Canvas sejam atualizados.
- DEBATE: O utilizador pede EXPLÍCITAMENTE um debate, discussão ou confronto entre as Almas (ex: "debate entre vocês", "discutam", "confrontem ideias").
- DIALOG: Conversa teórica ou metodológica padrão sobre o trabalho.

REGRAS DE OURO:
1. SEMPRE a Alma Teórica responde PRIMEIRO no início de um projeto.
2. Alterne com o Alma Metodológica (METHODOLOGICAL) quando o utilizador perguntar sobre "how-to", "mecanismo", "técnica" ou "metodologia".
3. Se o utilizador pedir EXPLÍCITAMENTE um "debate", "discussão" ou "confronto" entre as almas, marque selected_alma="DEBATE" e intent="DEBATE".
4. Se o utilizador pedir para "procurar", "pesquisar", "encontrar papers", "adicionar documentos" ou "verificar bibliografia", marque intent="SEARCH" e selected_alma="THEORETICAL".
5. Quando intent="SEARCH", emita uma diretiva clara: "EXECUTE_SEARCH: Pesquisar papers sobre [tema] no ArXiv".
6. No modo DEBATE, defina o debate_topic com o tema solicitado.

RESPOSTA OBRIGATÓRIA:
Apenas um objeto JSON seguindo o schema OrchestratorOutput. 
PROIBIDO saudações, explicações ou texto conversacional.
"""

class OrchestratorOutput(BaseModel):
    """Schema for Maestro Orchestrator output."""
    selected_alma: Literal["THEORETICAL", "METHODOLOGICAL", "DEBATE"] = Field(..., description="A Alma que deve responder ou DEBATE")
    intent: Literal["DIALOG", "SEARCH", "EXTRACTION", "DEBATE"] = Field(default="DIALOG", description="A intenção principal detectada")
    debate_topic: Optional[str] = Field(None, description="Se for DEBATE, o tema do debate")
    directive: str = Field(..., description="Diretiva interna para a Alma")

async def orchestrate(state: GraphState, user_message: str) -> dict:
    """Returns orchestrator decision using ADK Agent."""
    # Inicialização preguiçosa do agente para evitar erros de importação global
    maestro_agent = adk.Agent(
        "Maestro",
        settings.OLLAMA_ORCHESTRATOR_MODEL,
        ORCHESTRATOR_SYSTEM_PROMPT
    )

    def _val(field) -> str:
        if isinstance(field, dict):
            return field.get("content", "").strip()
        return str(field).strip() if field else ""

    canvas_info = (
        f"TEMA: {_val(state.current_canvas.tema) or '(não definido)'}\n"
        f"PROBLEMA: {_val(state.current_canvas.problema) or '(não definido)'}"
    )
    
    empirical_docs = getattr(state, "empirical_documents", [])
    docs_info = "\n".join([f"- {doc.filename} (ID: {doc.id})" for doc in empirical_docs]) if empirical_docs else "Nenhum arquivo anexado."

    # Detecção de intenção de visualização
    visualize_keywords = ["grafo", "mapa", "nó", "desenha", "whiteboard", "visualiz", "esquema"]
    wants_visualize = any(k in user_message.lower() for k in visualize_keywords)

    context = {
        "academic_level": state.academic_level,
        "theoretical_alma": state.active_theoretical_alma,
        "methodological_alma": state.active_methodological_alma,
        "last_alma_spoke": 'THEORETICAL' if state.chat_history and state.chat_history[-1].alma_name == state.active_theoretical_alma else 'METHODOLOGICAL',
        "project_canvas": canvas_info,
        "empirical_documents": docs_info,
        "forced_directive": (
            "VISUALIZE_WHITEBOARD: O usuário deseja uma visualização. "
            "USE a ferramenta add_canvas_node ou add_canvas_edge AGORA. "
            "NÃO escreva JSON no chat. NÃO descreva o que vai fazer, APENAS execute a tool."
        ) if wants_visualize else ""
    }

    try:
        raw_result = await maestro_agent.run(user_message, context=context)
        
        if isinstance(raw_result, OrchestratorOutput):
            res = raw_result.model_dump()
            if context.get("forced_directive"):
                res["directive"] = f"{res['directive']} | {context['forced_directive']}"
            return res
        
        if isinstance(raw_result, str):
            json_match = re.search(r'\{.*\}', raw_result, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                    res = OrchestratorOutput(**data).model_dump()
                    if context.get("forced_directive"):
                        res["directive"] = f"{res['directive']} | {context['forced_directive']}"
                    return res
                except Exception:
                    pass

        # Fallback se houver falha de parsing
        is_search = any(k in user_message.lower() for k in ["pesquise", "busque", "papers", "artigos", "bibliografia", "documento"])
        return {
            "selected_alma": "THEORETICAL",
            "intent": "SEARCH" if is_search else "DIALOG",
            "directive": f"EXECUTE_SEARCH: Pesquisar sobre {user_message}" if is_search else f"Responde ao utilizador: {user_message}"
        }
    except Exception as e:
        log.error(f"Error in ADK Orchestrate: {e}")
        # Segundo fallback de segurança
        return {
            "selected_alma": "THEORETICAL",
            "intent": "DIALOG",
            "directive": "Peça ao utilizador para esclarecer o ponto da investigação."
        }
