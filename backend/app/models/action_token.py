from pydantic import BaseModel
from typing import Literal, Optional, Union
from enum import Enum

class ActionType(str, Enum):
    SPOTLIGHT_PDF   = "SPOTLIGHT_PDF"    # Destaca trecho no PDF
    CANVAS_NODE     = "CANVAS_NODE"      # Cria nó no whiteboard
    CANVAS_EDGE     = "CANVAS_EDGE"      # Liga dois nós
    CANVAS_CLEAR    = "CANVAS_CLEAR"     # Limpa o whiteboard
    RAG_CITE        = "RAG_CITE"         # Cita fonte do RAG
    QUIZ_TRIGGER    = "QUIZ_TRIGGER"     # Lança quiz socrático
    CONFLICT_FLAG   = "CONFLICT_FLAG"    # Sinaliza conflito epistémico

class SpotlightPayload(BaseModel):
    section_ref: str        # ex: "§2.3"
    keyword: Optional[str] = None  # ex: "habitus"
    bbox: Optional[dict] = None    # {"page": 4, "x0": 0.1, "y0": 0.4, "x1": 0.9, "y1": 0.5}

class CanvasNodePayload(BaseModel):
    id: str
    label: str
    concept_type: str       # ex: "concept", "author", "tension"
    source_alma: str        # ex: "PB", "MF"

class CanvasEdgePayload(BaseModel):
    source_id: str
    target_id: str
    relation: str           # ex: "critica", "fundamenta", "contradiz"

class ConflictPayload(BaseModel):
    alma_a: str
    alma_b: str
    dimension: str          # ex: "onto-epistemológico"
    summary: str

ActionPayload = Union[SpotlightPayload, CanvasNodePayload, CanvasEdgePayload, ConflictPayload]

class ActionToken(BaseModel):
    type: ActionType
    payload: dict           # payload bruto (será validado pelo frontend)
