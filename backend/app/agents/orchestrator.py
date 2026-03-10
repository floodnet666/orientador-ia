from typing import Literal
from pydantic import BaseModel, Field
from app.lib import adk
from app.state.graph_state import GraphState
from app.config import settings

class OrchestratorOutput(BaseModel):
    """Schema for Maestro Orchestrator output."""
    selected_alma: Literal["THEORETICAL", "METHODOLOGICAL"] = Field(..., description="A Alma que deve responder")
    intent: Literal["DIALOG", "SEARCH", "EXTRACTION"] = Field(default="DIALOG", description="A intenção principal detectada")
    is_plagiarism: bool = Field(..., description="Se a mensagem é um pedido de plágio")
    directive: str = Field(..., description="Diretiva interna para a Alma")

ORCHESTRATOR_SYSTEM_PROMPT = """
Você é o Maestro (O Maestro), o orquestrador central do Orientador.IA. 
O seu único papel é analisar a mensagem do utilizador e o GraphState atual para decidir a próxima ação.

CLASSIFICAÇÃO DE INTENÇÃO (intent):
- SEARCH: O utilizador quer novos papers, fontes, bibliografia ou fazer pesquisas no ArXiv/internet.
- EXTRACTION: O utilizador chegou a uma conclusão e queres que os campos do Canvas sejam atualizados.
- DIALOG: Conversa teórica ou metodológica padrão sobre o trabalho.

REGRAS DE OURO:
1. SEMPRE a Alma Teórica responde PRIMEIRO no início de um projeto.
2. Alterne com o Alma Metodológica (METHODOLOGICAL) quando o utilizador perguntar sobre "como fazer", "método", "amostragem" ou "técnica".
3. Se o utilizador pedir para "procurar", "pesquisar", "encontrar papers", "adicionar documentos" ou "verificar bibliografia", marque intent="SEARCH" e selected_alma="THEORETICAL".
4. Detete pedidos de plágio: se o utilizador pedir para "escrever o trabalho", marque is_plagiarism=true.
5. Quando intent="SEARCH", emita uma diretiva clara: "EXECUTE_SEARCH: Pesquisar papers sobre [tema] no ArXiv".

Responda OBRIGATORIAMENTE em JSON seguindo o schema OrchestratorOutput.
"""

# Define the ADK Agent
maestro_agent = adk.Agent(
    name='maestro_orchestrator',
    model=f'ollama/{settings.OLLAMA_ORCHESTRATOR_MODEL}',
    system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    tools=[],  # O Maestro NÃO usa ferramentas externas
    output_schema=OrchestratorOutput
)

async def orchestrate(state: GraphState, user_message: str) -> dict:
    """Returns orchestrator decision using ADK Agent."""
    def _val(field) -> str:
        if isinstance(field, dict):
            return field.get("content", "").strip()
        return str(field).strip() if field else ""

    canvas_info = (
        f"TEMA: {_val(state.current_canvas.tema) or '(não definido)'}\n"
        f"PROBLEMA: {_val(state.current_canvas.problema) or '(não definido)'}"
    )
    
    context = {
        "academic_level": state.academic_level,
        "theoretical_alma": state.active_theoretical_alma,
        "methodological_alma": state.active_methodological_alma,
        "last_alma_spoke": 'THEORETICAL' if state.chat_history and state.chat_history[-1].alma_name == state.active_theoretical_alma else 'METHODOLOGICAL',
        "project_canvas": canvas_info
    }

    try:
        result = await maestro_agent.run(user_message, context=context)
        if isinstance(result, OrchestratorOutput):
            return result.model_dump()
        
        # Heuristic fallback if parsing fails but message contains search keywords
        is_search = any(k in user_message.lower() for k in ["pesquise", "busque", "papers", "artigos", "bibliografia"])
        return {
            "selected_alma": "THEORETICAL",
            "intent": "SEARCH" if is_search else "DIALOG",
            "is_plagiarism": False,
            "directive": f"EXECUTE_SEARCH: Pesquisar sobre {user_message}" if is_search else f"Responde ao utilizador: {user_message}"
        }
    except Exception as e:
        log.error(f"Error in ADK Orchestrate: {e}")
        return {
            "selected_alma": "THEORETICAL",
            "intent": "DIALOG",
            "is_plagiarism": False,
            "directive": "Responde com uma pergunta socrática sobre o tema da investigação."
        }
