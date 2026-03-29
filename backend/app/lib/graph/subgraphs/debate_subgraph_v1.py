import logging
from typing import List, Optional, Annotated
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from app.agents.state import DebateState, DebateTurn
from app.lib.graph.alma_registry import DEBATE_ALMAS, AlmaRole

log = logging.getLogger("app.debate.subgraph")

ROLE_SYSTEM_PROMPTS = {
    "primaria": """Você é a Alma Primária neste debate académico.
Seu papel é apresentar o argumento central mais forte e fundamentado sobre o tema.
Seja direto, cite fontes quando relevante, e estabeleça o tom do debate.
Limite: 3-4 parágrafos.""",

    "complementar": """Você é a Alma Complementar neste debate académico.
Seu papel é CONCORDAR com os pontos válidos da Alma Primária E adicionar
perspetivas, nuances ou exemplos que enriquecem o argumento.
Não repita o que já foi dito — adicione valor.
Limite: 3-4 parágrafos.""",

    "antagonista": """Você é a Alma Antagonista neste debate académico.
Seu papel é QUESTIONAR e DESAFIAR os argumentos anteriores com rigor.
Aponte limitações, contra-exemplos e perspetivas alternativas.
Seja respeitoso mas incisivo. Não destrua — refine.
Limite: 3-4 parágrafos.""",

    "metodologica": """Você é a Alma Metodológica neste debate académico.
Seu papel é analisar COMO os argumentos foram construídos:
- Quais evidências foram usadas? São suficientes?
- Há vieses nos raciocínios?
- Que metodologias validariam estas afirmações?
Seja técnico e construtivo.
Limite: 3-4 parágrafos.""",
}

def build_turn_node(role: str):
    """Cria um nó de turno para uma alma específica."""
    async def turn_node(state: DebateState) -> dict:
        alma = DEBATE_ALMAS[role]
        
        # Contexto dos turnos anteriores
        prior_context = ""
        if state["turns"]:
            prior_context = "\n\n".join([
                f"**{t['alma_name']} ({t['alma_role']}):**\n{t['content']}"
                for t in state["turns"]
            ])
            prior_context = f"\n\n## O que foi dito até agora no debate:\n{prior_context}"

        # Grounding do Canvas
        canvas_block = ""
        if state.get("canvas_summary"):
            canvas_block = f"\n## Estado Atual do Projeto (Whiteboard)\n{state['canvas_summary']}\n\n⚠️ Ancore sua resposta neste contexto. Não seja genérico."

        # Contexto RAG
        rag_block = ""
        if state.get("rag_context"):
            rag_block = f"\n## Documentos de Apoio\n{state['rag_context']}"

        system_prompt = f"{ROLE_SYSTEM_PROMPTS[role]}\n{canvas_block}\n{rag_block}"
        
        human_msg = f"Tema do debate: \"{state['topic']}\"{prior_context}\n\nApresente sua contribuição como {alma.name}:"
        
        llm = ChatOllama(model=alma.model, temperature=0.7)
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_msg)
        ])
        
        new_turn = DebateTurn(
            alma_id=alma.id,
            alma_name=alma.name,
            alma_role=role,
            content=response.content
        )
        
        return {
            "turns": [new_turn],
            "current_turn_index": state["current_turn_index"] + 1
        }
    return turn_node

async def synthesis_node(state: DebateState) -> dict:
    """Nó de síntese final do debate."""
    alma = DEBATE_ALMAS["synthesis"]
    
    all_turns = "\n\n".join([
        f"**{t['alma_name']}:**\n{t['content']}"
        for t in state["turns"]
    ])
    
    system_prompt = f"""Você é um mediador académico neutro. 
Sua função é sintetizar este debate de forma estruturada.

Organize sua síntese em:
1. **Pontos de Convergência** — onde as almas concordam.
2. **Tensões Produtivas** — onde divergem de forma útil.
3. **Recomendações** — o que o estudante deve considerar a seguir."""

    human_msg = f"Debate sobre: \"{state['topic']}\"\n\n{all_turns}\n\nProduza a síntese final contemplando o contexto do projeto se fornecido."
    
    llm = ChatOllama(model=alma.model, temperature=0.3)
    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_msg)
    ])
    
    return {"synthesis": response.content, "is_complete": True}

def route_debate(state: DebateState):
    """Define o próximo passo no debate baseado no index."""
    order = ["primaria", "complementar", "antagonista", "metodologica"]
    idx = state["current_turn_index"]
    if idx < len(order):
        return order[idx]
    return "synthesis"

def create_debate_subgraph():
    """Monta o StateGraph do debate."""
    workflow = StateGraph(DebateState)
    
    # Adiciona nós
    workflow.add_node("primaria", build_turn_node("primaria"))
    workflow.add_node("complementar", build_turn_node("complementar"))
    workflow.add_node("antagonista", build_turn_node("antagonista"))
    workflow.add_node("metodologica", build_turn_node("metodologica"))
    workflow.add_node("synthesis", synthesis_node)
    
    # Caminho linear facilitado pelo roteador ou edges diretas
    workflow.set_entry_point("primaria")
    
    workflow.add_edge("primaria", "complementar")
    workflow.add_edge("complementar", "antagonista")
    workflow.add_edge("antagonista", "metodologica")
    workflow.add_edge("metodologica", "synthesis")
    workflow.add_edge("synthesis", END)
    
    return workflow.compile()

debate_subgraph = create_debate_subgraph()
