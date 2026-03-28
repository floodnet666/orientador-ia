from pydantic import BaseModel, Field
from typing import Optional, List, Any
from uuid import UUID


class CanvasState(BaseModel):
    tema: dict = Field(default_factory=lambda: {"content": "", "is_locked": False})
    problema: dict = Field(default_factory=lambda: {"content": "", "is_locked": False})
    justificativa: dict = Field(default_factory=lambda: {"content": "", "is_locked": False})
    objetivos: dict = Field(default_factory=lambda: {"geral": "", "especificos": []})
    metodologia: dict = Field(default_factory=lambda: {"tipo": "", "instrumentos": []})
    mapa_mental: dict = Field(default_factory=lambda: {"content": "", "is_locked": False})


class ChatMessageState(BaseModel):
    role: str  # 'user' | 'alma' | 'system'
    alma_name: Optional[str] = None
    content: str
    timestamp: str


class ValidationFlags(BaseModel):
    is_plagiarism_attempt: bool = False
    needs_bibliography: bool = False
    plagiarism_confidence: float = 0.0


class GraphState(BaseModel):
    project_id: str
    user_id: str
    academic_level: str  # 'HIGHSCHOOL' | 'BACHELORS' | 'MASTERS' | 'PHD'
    chat_history: List[ChatMessageState] = Field(default_factory=list)
    current_canvas: CanvasState = Field(default_factory=CanvasState)
    active_theoretical_alma: str = ""
    active_methodological_alma: str = ""
    orchestrator_directive: str = ""
    canvas_fields_to_update: dict = Field(default_factory=dict)
    validation_flags: ValidationFlags = Field(default_factory=ValidationFlags)
    human_guidelines: str = ""
    active_soul_ids: List[str] = Field(default_factory=list)

    # Documents metadata for orchestration awareness
    empirical_documents: List[Any] = Field(default_factory=list)

    # Debate mode fields
    is_debate_mode: bool = False
    debate_round_number: int = 0
    previous_debate_summary: Optional[str] = None
    debate_history: List[dict] = Field(default_factory=list)

