"""Projects endpoints: CRUD, match, select-almas, canvas."""
import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models.schemas import (
    CanvasPatch,
    MatchRequest,
    MatchResult,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    SelectAlmasRequest,
)
from app.models.sql_models import (
    EcosystemResource,
    Project,
    ProjectCanvasState,
    User,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _get_project_or_404(project_id: UUID, user_id, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.user_id == current_user.id))
    return result.scalars().all()


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.sql_models import AcademicLevelEnum

    try:
        level = AcademicLevelEnum(body.academic_level)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid academic_level")

    project = Project(
        user_id=current_user.id,
        title=body.title,
        domain_area=body.domain_area,
        academic_level=level,
        human_guidelines=body.human_guidelines,
    )
    db.add(project)
    await db.flush()
    canvas = ProjectCanvasState(project_id=project.id)
    db.add(canvas)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_project_or_404(project_id, current_user.id, db)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, current_user.id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, current_user.id, db)
    await db.delete(project)
    await db.commit()
    return {"success": True}


@router.post("/{project_id}/match", response_model=MatchResult)
async def match_almas_endpoint(
    project_id: UUID,
    body: MatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.match_engine import match_almas

    await _get_project_or_404(project_id, current_user.id, db)
    return await match_almas(body.raw_idea)


@router.post("/{project_id}/select-almas", response_model=ProjectOut)
async def select_almas(
    project_id: UUID,
    body: SelectAlmasRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, current_user.id, db)
    project.theoretical_alma_id = body.theoretical_alma_id
    project.methodological_alma_id = body.methodological_alma_id
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}/canvas")
async def get_canvas(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_project_or_404(project_id, current_user.id, db)
    result = await db.execute(
        select(ProjectCanvasState).where(ProjectCanvasState.project_id == project_id)
    )
    canvas = result.scalar_one_or_none()
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    return canvas.canvas_json


@router.patch("/{project_id}/canvas")
async def patch_canvas(
    project_id: UUID,
    body: CanvasPatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_project_or_404(project_id, current_user.id, db)
    result = await db.execute(
        select(ProjectCanvasState).where(ProjectCanvasState.project_id == project_id)
    )
    canvas = result.scalar_one_or_none()
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")

    canvas_data = dict(canvas.canvas_json)
    canvas_data[body.field] = body.value
    canvas.canvas_json = canvas_data
    await db.commit()
    return canvas.canvas_json
