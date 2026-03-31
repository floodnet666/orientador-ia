from typing import Annotated, TypedDict, List, Optional, Any, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from app.state.graph_state import CanvasState, ValidationFlags


class DebateTurn(TypedDict):
    """Representa um turno individual de uma Alma no debate."""
    alma_id: str
    alma_name: str
    alma_role: str  # 'primaria' | 'complementar' | 'antagonista' | 'metodologica'
    content: str

class DebateState(TypedDict):
    """Estado interno do Subgrafo de Debate."""
    topic: str
    canvas_summary: str          # Grounding do Whiteboard
    rag_context: Optional[str]   # Contexto de documentos (RAG)
    
    # Histórico de turnos (Annotated garante append)
    turns: Annotated[List[DebateTurn], lambda x, y: x + y]
    
    # Controle de Fluxo
    current_role: str
    turn_order: List[str]
    current_turn_index: int
    
    # Resultado
    synthesis: Optional[str]
    is_complete: bool

class BackendState(TypedDict):
    """
    Estado central do Grafo de Decisão do Orientador.IA.
    Utiliza typing.Annotated com add_messages para gerenciar o histórico de chat de forma imutável.
    """
    # Histórico de mensagens primordial para o LangGraph
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Metadados de contexto
    project_id: str
    user_id: str
    academic_level: str  # 'HIGHSCHOOL' | 'BACHELORS' | 'MASTERS' | 'PHD'
    
    # Estado de ativação de Almas
    active_theoretical_alma: str
    active_methodological_alma: str
    active_soul_ids: List[str]
    
    # Diretrizes de Orquestração
    orchestrator_directive: str
    human_guidelines: str
    
    # Integração com o Canvas
    current_canvas: CanvasState
    canvas_nodes: List[dict] # Nós brutos para o serializador
    canvas_fields_to_update: dict
    
    # Flags de validação e documentos
    validation_flags: ValidationFlags
    empirical_documents: List[Any]
    
    # Estado de Debate e Roteamento
    is_debate_mode: bool
    debate_topic: Optional[str]
    debate_round_number: int
    previous_debate_summary: Optional[dict]
    debate_history: List[dict]
    
    # Roteamento interno
    selected_alma: Optional[str]
    intent: Optional[str]
    is_plagiarism: bool
