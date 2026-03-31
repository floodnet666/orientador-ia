import logging
from typing import Literal, Dict, Any, List, Annotated, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from app.agents.state import BackendState
from app.agents.llm import llm
from app.agents.tools import CORE_TOOLS
from app.agents.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from app.agents.almas.base_alma import BASE_ALMA_INSTRUCTIONS
from app.lib.graph.canvas_serializer import serialize_canvas_for_prompt
from app.lib.graph.subgraphs.debate_subgraph import debate_subgraph, DebateState

log = logging.getLogger("app.agents.graph")

# --- 1. Modelos de Saída Estruturada ---

class OrchestratorOutput(BaseModel):
    """Esquema de decisão do Maestro."""
    selected_alma: Literal["THEORETICAL", "METHODOLOGICAL", "DEBATE"] = Field(..., description="A Alma que deve responder ou DEBATE.")
    intent: Literal["DIALOG", "SEARCH", "EXTRACTION", "DEBATE"] = Field(default="DIALOG", description="A intenção principal detectada.")
    is_plagiarism: bool = Field(False, description="Se a mensagem é um pedido de plágio.")
    directive: str = Field(..., description="Diretiva interna clara para a Alma selecionada.")
    debate_topic: Optional[str] = Field(None, description="Se for DEBATE, qual o tema central?")

# --- 2. Nós do Grafo (Nodes) ---

async def maestro_node(state: BackendState) -> Dict[str, Any]:
    """
    Nó Orquestrador: Analisa a entrada e decide o roteamento e a persona ativa.
    """
    log.info("--- ENTRANDO NO MAESTRO ---")
    
    # Grounding do Canvas
    canvas_nodes = state.get("canvas_nodes", [])
    canvas_summary = serialize_canvas_for_prompt(canvas_nodes)
    
    full_prompt = ORCHESTRATOR_SYSTEM_PROMPT
    if canvas_summary:
        full_prompt += f"\n\n[CONTEXTO VISUAL DO WHITEBOARD (GROUNDING)]:\n{canvas_summary}"

    system_msg = SystemMessage(content=full_prompt)
    
    decision_messages = [system_msg] + state["messages"][-5:]
    
    try:
        structured_llm = llm.with_structured_output(OrchestratorOutput)
        decision = await structured_llm.ainvoke(decision_messages)
        
        log.info(f"Maestro Decision: Alma={decision.selected_alma}, Intent={decision.intent}")
        
        return {
            "selected_alma": decision.selected_alma,
            "intent": decision.intent,
            "is_plagiarism": decision.is_plagiarism,
            "orchestrator_directive": decision.directive,
            "debate_topic": decision.debate_topic,
            "is_debate_mode": decision.selected_alma == "DEBATE"
        }
    except Exception as e:
        log.error(f"Erro no Maestro: {e}. Usando fallback THEORETICAL.")
        return {
            "selected_alma": "THEORETICAL",
            "intent": "DIALOG",
            "orchestrator_directive": "Continue a orientação teórica normalmente."
        }

async def debate_node(state: BackendState) -> Dict[str, Any]:
    """Ponte entre o grafo principal e o subgrafo de debate."""

    # Extrai a última mensagem do utilizador como provocação original
    original_message = ""
    for msg in reversed(state["messages"]):
        if hasattr(msg, "type") and msg.type == "human":
            original_message = msg.content
            break

    debate_input = DebateState(
        original_user_message=original_message,
        canvas_summary=serialize_canvas_for_prompt(state.get("canvas_nodes", [])),
        rag_context=state.get("rag_context"),
        turns=[],
        current_turn_index=0,
        synthesis=None,
        is_complete=False,
    )

    result = await debate_subgraph.ainvoke(debate_input)

    return {
        "messages": [AIMessage(content=result["synthesis"])],
        "debate_history": result["turns"],
        "previous_debate_summary": result.get("synthesis_structured"),
        "is_debate_mode": False
    }

async def alma_node(state: BackendState) -> Dict[str, Any]:
    """
    Nó de Persona: Executa o pensamento da Alma selecionada e gera respostas/chamadas de ferramenta.
    """
    selected = state.get("selected_alma", "THEORETICAL")
    log.info(f"--- ENTRANDO NA ALMA: {selected} ---")
    
    # 1. Recupera o prompt específico da persona do estado ou usa um padrão
    if selected == "METHODOLOGICAL":
        persona_content = state.get("methodological_system_prompt") or "És um Orientador de Metodologia Científica rigoroso."
    else:
        persona_content = state.get("theoretical_system_prompt") or "És um Orientador de Teoria Social profunda."
        
    # 2. Constrói o System Prompt completo (Instruções de Base + Persona + Grounding + Directiva)
    canvas_summary = serialize_canvas_for_prompt(state.get("canvas_nodes", []))
    
    full_system = f"{BASE_ALMA_INSTRUCTIONS}\n\n{persona_content}"
    
    if canvas_summary:
        full_system += f"\n\n[CONTEXTO VISUAL DO WHITEBOARD (GROUNDING)]:\n{canvas_summary}"
        
    directive = state.get("orchestrator_directive")
    if directive:
        full_system += f"\n\n[DIRECTIVA DO MAESTRO PARA ESTE TURNO]: {directive}"
        
    # 3. Prepara a chamada ao LLM com as ferramentas vinculadas
    llm_with_tools = llm.bind_tools(CORE_TOOLS)
    
    # 4. Invocação (histórico completo preservado no state['messages'])
    messages = [SystemMessage(content=full_system)] + state["messages"]
    
    response = await llm_with_tools.ainvoke(messages)
    
    return {"messages": [response]}

# --- 3. Lógica de Roteamento (Conditional Edges) ---

def should_continue(state: BackendState) -> Literal["tools", "__end__"]:
    """Decide se o fluxo vai para execução de ferramentas ou finaliza."""
    messages = state["messages"]
    last_message = messages[-1]
    
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        log.info(f"Tool calls detectadas: {len(last_message.tool_calls)}")
        return "tools"
    
    return END

# --- 4. Construção da Fábrica do Grafo ---

def create_backend_graph():
    """Compila o grafo de estados do Orientador IA."""
    workflow = StateGraph(BackendState)
    
    # Adiciona os nós
    workflow.add_node("maestro", maestro_node)
    workflow.add_node("alma", alma_node)
    workflow.add_node("debate", debate_node)
    workflow.add_node("tools", ToolNode(CORE_TOOLS))
    
    # Define as conexões
    workflow.add_edge(START, "maestro")
    
    # Roteamento condicional do Maestro
    def route_maestro(state: BackendState):
        if state.get("selected_alma") == "DEBATE":
            return "debate"
        return "alma"
        
    workflow.add_conditional_edges("maestro", route_maestro)
    
    # Roteamento condicional para ferramentas (Loop da Alma)
    workflow.add_conditional_edges(
        "alma",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    
    # Após o debate ou ferramentas, encerra o turno atual
    workflow.add_edge("debate", END)
    workflow.add_edge("tools", "alma")
    
    # Compilação
    return workflow.compile()

# Instância Singleton do Grafo
backend_graph = create_backend_graph()
