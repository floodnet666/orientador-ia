import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    String, Text, Integer, JSON
)
from sqlalchemy.types import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AcademicLevelEnum(str, enum.Enum):
    HIGHSCHOOL = "HIGHSCHOOL"
    BACHELORS = "BACHELORS"
    MASTERS = "MASTERS"
    PHD = "PHD"


class ProjectStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    ANALYSIS = "ANALYSIS"
    COMPLETE = "COMPLETE"


class ResourceTypeEnum(str, enum.Enum):
    ALMA = "ALMA"
    SKILL = "SKILL"
    TOOL = "TOOL"


class AlmaTypeEnum(str, enum.Enum):
    THEORETICAL = "THEORETICAL"
    METHODOLOGICAL = "METHODOLOGICAL"


class ScopeEnum(str, enum.Enum):
    LOCAL = "LOCAL"
    GLOBAL = "GLOBAL"


class RoleEnum(str, enum.Enum):
    USER = "USER"
    ALMA = "ALMA"
    SYSTEM = "SYSTEM"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    academic_level = Column(
        Enum(AcademicLevelEnum, name="academic_level_enum"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    projects = relationship("Project", back_populates="owner")


class EcosystemResource(Base):
    __tablename__ = "ecosystem_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_type = Column(
        Enum(ResourceTypeEnum, name="resource_type_enum"), nullable=False
    )
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    alma_type = Column(
        Enum(AlmaTypeEnum, name="alma_type_enum"), nullable=True
    )
    scope = Column(Enum(ScopeEnum, name="scope_enum"), default=ScopeEnum.GLOBAL)
    origin_project_id = Column(UUID(as_uuid=True), nullable=True)
    system_prompt = Column(Text, nullable=False)
    personality_descriptor = Column(String, nullable=False)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    domain_area = Column(String, nullable=False)
    academic_level = Column(
        Enum(AcademicLevelEnum, name="academic_level_enum"), nullable=False
    )
    status = Column(
        Enum(ProjectStatusEnum, name="project_status_enum"), default=ProjectStatusEnum.DRAFT
    )
    human_guidelines = Column(Text, nullable=True)
    theoretical_alma_id = Column(
        UUID(as_uuid=True), ForeignKey("ecosystem_resources.id"), nullable=True
    )
    methodological_alma_id = Column(
        UUID(as_uuid=True), ForeignKey("ecosystem_resources.id"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="projects")
    canvas_state = relationship("ProjectCanvasState", uselist=False, back_populates="project")
    messages = relationship("ChatMessage", back_populates="project")


class ProjectCanvasState(Base):
    __tablename__ = "project_canvas_state"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True)
    canvas_json = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "tema": {"content": "", "is_locked": False},
            "problema": {"content": "", "is_locked": False},
            "justificativa": {"content": "", "is_locked": False},
            "objetivos": {"geral": "", "especificos": []},
            "metodologia": {"tipo": "", "instrumentos": []},
        },
    )
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="canvas_state")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    role = Column(Enum(RoleEnum, name="role_enum"), nullable=False)
    alma_id = Column(UUID(as_uuid=True), nullable=True)
    alma_name = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="messages")
