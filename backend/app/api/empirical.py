from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging
import os
import json
import redis.asyncio as redis

from app.api.auth import get_current_user
from app.database import get_db
from app.models.sql_models import User
from app.services.empirical.document_processor import empirical_processor
from app.config import settings

# Redis client for job tracking
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

router = APIRouter(prefix="/api/empirical", tags=["empirical"])
log = logging.getLogger("empirical.api")

@router.post("/{project_id}/upload")
async def upload_empirical_data(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    Upload and process empirical data (PDF, CSV) in background.
    Uses Redis to track state.
    """
    content = await file.read()
    filename = file.filename
    pid_str = str(project_id)
    job_id = f"ingest:{pid_str}:{filename}"
    
    # 1. Check if already processing
    status = await redis_client.get(job_id)
    if status == "processing":
        raise HTTPException(status_code=400, detail="Document already being processed.")

    # 2. Save file temporarily
    import tempfile
    suffix = ".pdf" if filename.lower().endswith(".pdf") else ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    # 3. Define background task
    async def run_ingestion():
        try:
            await redis_client.set(job_id, "processing", ex=3600)
            if filename.lower().endswith(".pdf"):
                await empirical_processor.process_pdf_v2(tmp_path, project_id, filename)
            # Add CSV/other logic as needed
            await redis_client.set(job_id, "completed", ex=86400)
        except Exception as e:
            log.error("Background ingestion failed for %s: %s", filename, e)
            await redis_client.set(job_id, f"error: {str(e)}", ex=3600)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    background_tasks.add_task(run_ingestion)
    
    return {
        "message": f"Upload received. Processing {filename} in background.",
        "job_id": job_id
    }

@router.get("/{project_id}/status/{filename}")
async def get_ingestion_status(project_id: UUID, filename: str):
    job_id = f"ingest:{str(project_id)}:{filename}"
    status = await redis_client.get(job_id)
    return {"filename": filename, "status": status or "unknown"}

@router.get("/{project_id}/documents")
async def list_project_documents(
    project_id: UUID,
    user: User = Depends(get_current_user)
):
    """List filenames of uploaded documents for a project."""
    try:
        from qdrant_client import models
        pid_str = str(project_id)
        collection_name = "empirical_data_v2" # RAG v2.2.0
        
        results = await empirical_processor.qdrant.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="project_id", match=models.MatchValue(value=pid_str)
                    )
                ]
            ),
            limit=1000,
            with_payload=True
        )
        
        points = results[0]
        filenames = []
        for p in points:
            payload = p.payload if hasattr(p, 'payload') else p.get('payload', {})
            if payload and "filename" in payload:
                filenames.append(payload["filename"])
                
        return sorted(list(set(filenames)))
    except Exception as e:
        log.error("Error listing documents for project %s: %s", project_id, str(e), exc_info=True)
        return []

@router.delete("/{project_id}/documents/{filename}")
async def delete_project_document(
    project_id: UUID,
    filename: str,
    user: User = Depends(get_current_user)
):
    """Remove a document from the project library (Gargalo C Fix)."""
    try:
        from app.services.qdrant_service import delete_project_document as qdrant_delete
        await qdrant_delete(str(project_id), filename)
        # Clear redis status too
        job_id = f"ingest:{str(project_id)}:{filename}"
        await redis_client.delete(job_id)
        return {"message": f"Document {filename} removed successfully."}
    except Exception as e:
        log.error("Error deleting document %s: %s", filename, e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/search")
async def search_project_evidence(
    project_id: UUID,
    query: str,
    user: User = Depends(get_current_user)
):
    """Search for relevant evidence within uploaded documents."""
    results = await empirical_processor.search_evidence(project_id, query)
    return results
