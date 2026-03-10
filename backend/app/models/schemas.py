from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


# ── Auth ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    academic_level: str  # HIGHSCHOOL | BACHELORS | MASTERS | PHD


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    academic_level: str

    class Config:
        from_attributes = True


# ── Projects ─────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    title: str
    domain_area: str
    academic_level: str
    human_guidelines: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    domain_area: Optional[str] = None
    status: Optional[str] = None
    human_guidelines: Optional[str] = None


class ProjectOut(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    domain_area: str
    academic_level: str
    status: str
    human_guidelines: Optional[str] = None
    theoretical_alma_id: Optional[UUID] = None
    methodological_alma_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Canvas ────────────────────────────────────────────────────────────────────

class CanvasPatch(BaseModel):
    field: str
    value: Any


# ── Match ─────────────────────────────────────────────────────────────────────

class MatchRequest(BaseModel):
    raw_idea: str


class AlmaSuggestion(BaseModel):
    id: str
    name: str
    description: str
    alma_type: str
    personality_descriptor: str
    score: float


class MatchResult(BaseModel):
    theoretical: list[AlmaSuggestion]
    methodological: list[AlmaSuggestion]


class SelectAlmasRequest(BaseModel):
    theoretical_alma_id: UUID
    methodological_alma_id: UUID


# ── Chat ─────────────────────────────────────────────────────────────────────

class ChatMessageOut(BaseModel):
    id: UUID
    project_id: UUID
    role: str
    alma_name: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

# ── Admin ───────────────────────────────────────────────────────────────────

class UserAdminOut(UserOut):
    is_admin: bool
    created_at: datetime

class AlmaCreate(BaseModel):
    name: str
    description: str
    resource_type: str
    alma_type: Optional[str] = None
    system_prompt: str
    personality_descriptor: str
    llm_model: Optional[str] = None
    is_approved: bool = True

class AlmaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    personality_descriptor: Optional[str] = None
    llm_model: Optional[str] = None
    is_approved: Optional[bool] = None

class AlmaPromptUpdate(BaseModel):
    new_prompt: str
    reason: Optional[str] = None

class AlmaOut(BaseModel):
    id: UUID
    name: str
    description: str
    resource_type: str
    alma_type: Optional[str] = None
    system_prompt: str
    personality_descriptor: str
    llm_model: Optional[str] = None
    is_approved: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ResetPasswordRequest(BaseModel):
    new_password: str
