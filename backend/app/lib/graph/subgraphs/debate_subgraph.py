from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from app.agents.llm import get_llm
from app.lib.graph.alma_registry import (
    DEBATE_ALMAS, TURN_ORDER, AlmaRole, AlmaIdentity
)

# ── Estado do Subgrafo ──────────────────────────────────────────────────────

class DebateTurn(TypedDict):
    alma_id: str
    alma_name: str
    alma_role: str
    content: str

class DebateState(TypedDict):
    original_user_message: str          # a provocação original — presente em TODOS os turnos
    canvas_summary: str                 # estado serializado do canvas (pode ser string vazia)
    rag_context: Optional[str]          # contexto de documentos (pode ser None)
    turns: list[DebateTurn]             # acumula os turnos já realizados
    current_turn_index: int             # índice no TURN_ORDER
    synthesis: Optional[str]            # Texto livre da síntese
    synthesis_structured: Optional[dict] # Dados estruturados para o Card (tensions, consensus, question)
    is_complete: bool

class SynthesisOutput(BaseModel):
    """Esquema para a síntese final estruturada do debate."""
    summary_text: str = Field(..., description="O resumo narrativo a ser exibido no chat.")
    points_of_consensus: list[str] = Field(..., description="Lista de pontos onde houve acordo entre as Almas.")
    core_tensions: list[str] = Field(..., description="Lista de divergências ou tensões em aberto.")
    recommendations: list[str] = Field(..., description="Sugestões práticas para o utilizador refletir.")
    question_for_user: str = Field(..., description="Pergunta provocativa final para o utilizador.")

# ── Prompts por Papel ───────────────────────────────────────────────────────

ROLE_PROMPTS: dict[AlmaRole, str] = {
    "primaria": (
        "Você é a Alma Primária num debate académico. "
        "Apresente o argumento central mais forte e fundamentado sobre o tema. "
        "Seja direto, cite bases teóricas quando relevante, e estabeleça o tom do debate. "
        "Limite: 3 a 4 parágrafos."
    ),
    "complementar": (
        "Você é a Alma Complementar num debate académico. "
        "Reaja TANTO à provocação do utilizador QUANTO ao que a Alma Primária disse. "
        "Concorde com os pontos válidos e adicione perspetivas ou exemplos que enriquecem o argumento. "
        "Não repita o que já foi dito — acrescente valor. "
        "Limite: 3 a 4 parágrafos."
    ),
    "antagonista": (
        "Você é a Alma Antagonista num debate académico. "
        "Reaja TANTO à provocação do utilizador QUANTO a tudo que as almas anteriores disseram. "
        "Questione e desafie os argumentos com rigor. Aponte limitações e perspetivas alternativas. "
        "Seja respeitoso mas incisivo. O objetivo é refinar, não destruir. "
        "Limite: 3 a 4 parágrafos."
    ),
    "metodologica": (
        "Você é a Alma Metodológica num debate académico. "
        "Reaja TANTO à provocação do utilizador QUANTO a tudo que as três almas anteriores disseram. "
        "Analise COMO os argumentos foram construídos: que evidências foram usadas, "
        "se há vieses nos raciocínios, e que metodologias validariam estas afirmações. "
        "Seja técnico e construtivo. "
        "Limite: 3 a 4 parágrafos."
    ),
}

# ── Nós ────────────────────────────────────────────────────────────────────

def _build_prior_context(turns: list[DebateTurn]) -> str:
    """Monta a transcrição acumulada de todos os turnos anteriores."""
    if not turns:
        return ""
    lines = ["## O que foi dito até agora no debate:"]
    for t in turns:
        lines.append(f"\n**{t['alma_name']}:**\n{t['content']}")
    return "\n".join(lines)


def _build_canvas_block(canvas_summary: str) -> str:
    if not canvas_summary:
        return ""
    return (
        "\n## Estado Atual do Projeto (Canvas)\n"
        f"{canvas_summary}\n"
        "⚠️ Ancore sua resposta neste contexto específico. Não responda de forma genérica.\n"
    )


def _build_rag_block(rag_context: Optional[str]) -> str:
    if not rag_context:
        return ""
    return f"\n## Documentos Relevantes\n{rag_context}\n"


async def _execute_turn(state: DebateState, role: AlmaRole) -> dict:
    """Executa um único turno para a alma do papel especificado."""
    alma: AlmaIdentity = DEBATE_ALMAS[role]

    system = (
        f"{ROLE_PROMPTS[role]}"
        f"{_build_canvas_block(state['canvas_summary'])}"
        f"{_build_rag_block(state.get('rag_context'))}"
    )

    prior_context = _build_prior_context(state["turns"])

    human = (
        f"O utilizador disse:\n\"{state['original_user_message']}\"\n\n"
        f"{prior_context}\n\n"
        f"Apresente sua contribuição como {alma.name}:"
    )

    llm = get_llm(model=alma.model, temperature=0.7)
    # Turn execution will be picked up by astream_events in the main pipeline
    # We update the state with the metadata, and the actual content will be filled
    # by the LLM invocation which is now handled at a higher level or via streaming.
    # Note: For langgraph astream_events to capture the model, we need to invoke it inside the node.
    
    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=human),
    ])

    new_turn = DebateTurn(
        alma_id=alma.id,
        alma_name=alma.name,
        alma_role=role,
        content=response.content,
    )

    return {
        "turns": state["turns"] + [new_turn],
        "current_turn_index": state["current_turn_index"] + 1,
    }


async def primaria_node(state: DebateState) -> dict:
    return await _execute_turn(state, "primaria")

async def complementar_node(state: DebateState) -> dict:
    return await _execute_turn(state, "complementar")

async def antagonista_node(state: DebateState) -> dict:
    return await _execute_turn(state, "antagonista")

async def metodologica_node(state: DebateState) -> dict:
    return await _execute_turn(state, "metodologica")

async def synthesis_node(state: DebateState) -> dict:
    alma = DEBATE_ALMAS["synthesis"]

    all_turns = "\n\n".join([
        f"**{t['alma_name']}:**\n{t['content']}"
        for t in state["turns"]
    ])

    canvas_block = _build_canvas_block(state["canvas_summary"])

    system = (
        "Você é um mediador académico neutral e rigoroso.\n"
        "O seu objetivo é sintetizar o debate ocorrido entre as Almas e propor o próximo passo da investigação.\n"
        f"{canvas_block}"
    )

    human = (
        f"Tema Central: \"{state['original_user_message']}\"\n\n"
        f"Transcrição do Debate:\n{all_turns}\n\n"
        "Gere a síntese estruturada agora:"
    )

    llm = get_llm(model=alma.model)
    structured_llm = llm.with_structured_output(SynthesisOutput)
    
    try:
        res = await structured_llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=human),
        ])
        
        return {
            "synthesis": res.summary_text,
            "synthesis_structured": {
                "consensus": res.points_of_consensus,
                "tensions": res.core_tensions,
                "question": res.question_for_user,
                "recommendations": res.recommendations
            },
            "is_complete": True,
        }
    except Exception as e:
        # Fallback para texto simples se o estruturado falhar
        resp = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=human)])
        return {
            "synthesis": resp.content,
            "is_complete": True,
        }

# ── Roteamento ─────────────────────────────────────────────────────────────

def route_debate(state: DebateState) -> str:
    idx = state["current_turn_index"]
    if idx < len(TURN_ORDER):
        return TURN_ORDER[idx]
    return "synthesis"

# ── Montagem do Subgrafo ───────────────────────────────────────────────────

def build_debate_subgraph():
    g = StateGraph(DebateState)

    g.add_node("primaria",     primaria_node)
    g.add_node("complementar", complementar_node)
    g.add_node("antagonista",  antagonista_node)
    g.add_node("metodologica", metodologica_node)
    g.add_node("synthesis",    synthesis_node)

    async def router_node(state: DebateState) -> dict:
        return {}

    g.add_node("router", router_node)
    g.set_entry_point("router")

    g.add_conditional_edges("router", route_debate, {
        "primaria":     "primaria",
        "complementar": "complementar",
        "antagonista":  "antagonista",
        "metodologica": "metodologica",
        "synthesis":    "synthesis",
    })

    for role in TURN_ORDER:
        g.add_edge(role, "router")

    g.add_edge("synthesis", END)

    return g.compile()


debate_subgraph = build_debate_subgraph()
