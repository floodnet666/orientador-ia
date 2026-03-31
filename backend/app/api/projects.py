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


async def _hydrate_active_almas(project: Project, db: AsyncSession):
    """Popula a lista de objetos Alma (EcosystemResource) baseada no soul_ids."""
    if not project.soul_ids:
        project.active_almas = []
        return project
    
    # Converte para strings se necessário (dependendo do driver JSON)
    ids = [str(uid) for uid in project.soul_ids]
    result = await db.execute(
        select(EcosystemResource).where(EcosystemResource.id.in_(ids))
    )
    project.active_almas = result.scalars().all()
    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.user_id == current_user.id))
    projects = result.scalars().all()
    for p in projects:
        await _hydrate_active_almas(p, db)
    return projects


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
    return await _hydrate_active_almas(project, db)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, current_user.id, db)
    return await _hydrate_active_almas(project, db)


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
    return await _hydrate_active_almas(project, db)


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, current_user.id, db)
    
    pid_str = str(project_id)
    
    # 1. Clean up RAG data in Qdrant (Mesa-Redonda evidence)
    try:
        from app.services.qdrant_service import delete_project_data
        await delete_project_data(pid_str)
    except Exception as e:
        # Log error but continue to ensure DB cleanup
        import logging
        logging.getLogger("projects").error(f"Failed to delete Qdrant data for project {pid_str}: {e}")

    # 2. Clean up Redis ingestion status keys
    try:
        from app.api.empirical import redis_client
        keys = await redis_client.keys(f"ingest:{pid_str}:*")
        if keys:
            await redis_client.delete(*keys)
    except Exception as e:
        import logging
        logging.getLogger("projects").error(f"Failed to clean up Redis keys for project {pid_str}: {e}")

    # 3. DB delete (Cascades automatically handle ChatMessage and ProjectCanvasState)
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
    return await match_almas(body.raw_idea, db)


@router.post("/{project_id}/select-almas", response_model=ProjectOut)
async def select_almas(
    project_id: UUID,
    body: SelectAlmasRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, current_user.id, db)
    
    # Atualiza campos legados
    if body.theoretical_alma_id:
        project.theoretical_alma_id = body.theoretical_alma_id
    if body.methodological_alma_id:
        project.methodological_alma_id = body.methodological_alma_id
        
    # Atualiza lista de múltiplas Almas (v2)
    if body.alma_ids:
        # Armazenamos como lista de strings para compatibilidade JSON
        project.soul_ids = [str(aid) for aid in body.alma_ids]
    elif body.theoretical_alma_id or body.methodological_alma_id:
        # Fallback: se apenas os legados forem enviados, popula a lista
        ids = []
        if body.theoretical_alma_id: ids.append(str(body.theoretical_alma_id))
        if body.methodological_alma_id: ids.append(str(body.methodological_alma_id))
        project.soul_ids = ids

    await db.commit()
    await db.refresh(project)
    return await _hydrate_active_almas(project, db)


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
