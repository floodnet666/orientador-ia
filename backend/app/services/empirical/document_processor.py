import os
import logging
from typing import List, Dict, Any
from uuid import UUID
import fitz  # PyMuPDF
import pandas as pd
from io import BytesIO

from qdrant_client import AsyncQdrantClient, models
from app.config import settings
from app.services.ollama_client import ollama_client

log = logging.getLogger("empirical.processor")

class EmpiricalProcessor:
    def __init__(self):
        self.qdrant = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, check_compatibility=False)
        self.collection_name = "empirical_data"

    async def ensure_collection(self):
        """Creates the collection if it doesn't exist."""
        collections = await self.qdrant.get_collections()
        exists = any(c.name == self.collection_name for c in collections.collections)
        if not exists:
            await self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE),
            )
            log.info("Created Qdrant collection: %s", self.collection_name)

    async def process_pdf(self, file_content: bytes) -> str:
        """Extracts text from PDF bytes."""
        doc = fitz.open(stream=file_content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    async def process_csv(self, file_content: bytes) -> str:
        """Converts CSV to a textual representation."""
        df = pd.read_csv(BytesIO(file_content))
        # Simple conversion for LLM consumption
        return df.to_string()

    async def index_document(self, project_id: UUID, filename: str, content: str):
        """Chunks, embeds, and stores the document in Qdrant."""
        project_id_str = str(project_id)
        await self.ensure_collection()
        
    def _chunk_text(self, text: str, max_chars: int = 800, overlap: int = 100) -> List[str]:
        """Split text into manageable chunks for embeddings."""
        # Simple recursive character splitting logic
        if len(text) <= max_chars:
            return [text.strip()] if text.strip() else []
            
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            if end < len(text):
                # Try to find a good breaking point (newline or period)
                last_newline = text.rfind("\n", start, end)
                if last_newline > start + (max_chars // 2):
                    end = last_newline
                else:
                    last_period = text.rfind(". ", start, end)
                    if last_period > start + (max_chars // 2):
                        end = last_period + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end < len(text) else end
        return chunks

    async def index_document(self, project_id: UUID, filename: str, content: str):
        """Chunks, embeds, and stores the document in Qdrant."""
        project_id_str = str(project_id)
        await self.ensure_collection()
        
        # Use robust chunking to stay within embedding context
        chunks = self._chunk_text(content)
        if not chunks:
            log.warning("No content extracted from %s", filename)
            return

        points = []
        for i, chunk in enumerate(chunks):
            embedding = await ollama_client.embed(chunk)
            points.append(models.PointStruct(
                id=str(UUID(int=abs(hash(f"{project_id}_{filename}_{i}")))),
                vector=embedding,
                payload={
                    "project_id": project_id_str,
                    "filename": filename,
                    "text": chunk,
                    "type": "empirical_evidence"
                }
            ))

        if points:
            await self.qdrant.upsert(
                collection_name=self.collection_name,
                points=points
            )
            log.info("Indexed %d chunks from %s for project %s", len(points), filename, project_id_str)

    async def search_evidence(self, project_id: UUID, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Searches for relevant evidence within a project's uploaded documents."""
        query_vector = await ollama_client.embed(query)
        
        pid_str = str(project_id)
        results = await self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(key="project_id", match=models.MatchValue(value=pid_str))
                ]
            ),
            limit=limit
        )
        
        return [
            {
                "text": hit.payload["text"],
                "filename": hit.payload["filename"],
                "score": hit.score
            }
            for hit in results
        ]

empirical_processor = EmpiricalProcessor()
