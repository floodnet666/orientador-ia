from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from app.api.auth import get_current_user
from app.database import get_db
from app.models.sql_models import User
from app.services.empirical.document_processor import empirical_processor

router = APIRouter(prefix="/api/empirical", tags=["empirical"])
log = logging.getLogger("empirical.api")

@router.post("/{project_id}/upload")
async def upload_empirical_data(
    project_id: UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and process empirical data (PDF, CSV).
    Extracts text/data and indexes it into Qdrant for use in Mesa-Redonda.
    """
    content = await file.read()
    filename = file.filename.lower()
    
    try:
        if filename.endswith(".pdf"):
            text = await empirical_processor.process_pdf(content)
        elif filename.endswith(".csv"):
            text = await empirical_processor.process_csv(content)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use PDF or CSV.")
        
        # In a real app, we might want to store the metadata/file record in SQL too.
        # For MVP, we go straight to indexing in Qdrant associated with the project_id.
        await empirical_processor.index_document(project_id, file.filename, text)
        
        return {"message": f"File {file.filename} processed and indexed successfully."}
    except Exception as e:
        log.error("Error processing file %s: %s", file.filename, e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/documents")
async def list_project_documents(
    project_id: UUID,
    user: User = Depends(get_current_user)
):
    """List filenames of uploaded documents for a project."""
    try:
        from qdrant_client import models
        pid_str = str(project_id)
        
        await empirical_processor.ensure_collection()
        
        results = await empirical_processor.qdrant.scroll(
            collection_name=empirical_processor.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="project_id", match=models.MatchValue(value=pid_str)
                    )
                ]
            ),
            limit=100,
            with_payload=True
        )
        
        points = results[0]
        filenames = []
        for p in points:
            payload = getattr(p, 'payload', None)
            if payload and isinstance(payload, dict) and "filename" in payload:
                filenames.append(payload["filename"])
            elif isinstance(p, dict) and "payload" in p and isinstance(p["payload"], dict) and "filename" in p["payload"]:
                filenames.append(p["payload"]["filename"])
                
        return sorted(list(set(filenames)))
    except Exception as e:
        log.error("Error listing documents for project %s: %s", project_id, str(e), exc_info=True)
        return []

@router.get("/{project_id}/search")
async def search_project_evidence(
    project_id: UUID,
    query: str,
    user: User = Depends(get_current_user)
):
    """Search for relevant evidence within uploaded documents."""
    results = await empirical_processor.search_evidence(project_id, query)
    return results
