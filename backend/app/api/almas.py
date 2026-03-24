from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import logging

from app.api.auth import get_current_user
from app.database import get_db
from app.models.sql_models import User, EcosystemResource, ResourceTypeEnum, AlmaTypeEnum
from app.services.genesis_service import genesis_service
from app.services.ferramenteiro_service import ferramenteiro_service
from app.services.qdrant_service import index_alma

router = APIRouter(prefix="/api/almas", tags=["almas"])
log = logging.getLogger("almas.api")

from pydantic import BaseModel

class GenesisRequest(BaseModel):
    description: str | None = None
    prompt: str | None = None

class ExecuteRequest(BaseModel):
    code: str
    context: dict = {}

@router.post("/genesis")
async def create_alma_via_genesis(
    request: GenesisRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Agente Génesis: Creates a new Alma based on a textual description."""
    try:
        desc = request.description or request.prompt
        if not desc:
            raise HTTPException(status_code=400, detail="Missing description or prompt")
            
        alma_data = await genesis_service.generate_alma(desc)
        
        # Robustness: Se o LLM retornar system_prompt como dict, converte para string
        import json
        prompt_data = alma_data.get("system_prompt", "")
        if isinstance(prompt_data, dict):
            prompt_data = json.dumps(prompt_data, ensure_ascii=False)
            
        new_alma = EcosystemResource(
            resource_type=ResourceTypeEnum.ALMA,
            name=alma_data["name"],
            description=alma_data["description"],
            alma_type=AlmaTypeEnum(alma_data["type"]),
            system_prompt=prompt_data,
            personality_descriptor=alma_data["description"][:100],
            is_approved=True
        )
        
        db.add(new_alma)
        await db.commit()
        await db.refresh(new_alma)
        
        # Automatically index in Qdrant for Match Engine
        await index_alma(new_alma)
        
        return {
            "message": "Alma criada e indexada com sucesso!",
            "alma": {
                "id": new_alma.id,
                "name": new_alma.name,
                "description": new_alma.description
            }
        }
    except Exception as e:
        log.error("Genesis failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute")
async def execute_python_code(
    request: ExecuteRequest,
    user: User = Depends(get_current_user)
):
    """Agente Ferramenteiro: Executes Python code and returns results."""
    # Note: In a production app, this should be in a WASM sandbox or micro-container.
    result = ferramenteiro_service.execute_code(request.code)
    return result

@router.get("")
async def list_available_almas(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists all active Almas."""
    result = await db.execute(select(EcosystemResource).where(EcosystemResource.is_approved == True))
    return result.scalars().all()
