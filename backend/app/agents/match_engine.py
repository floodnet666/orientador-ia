"""
Match Engine — semantic similarity via Qdrant to suggest Almas for a project idea.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.embedding import generate_embedding
from app.services.qdrant_service import search_almas, index_alma
from app.models.schemas import AlmaSuggestion, MatchResult
from app.services.genesis_service import genesis_service
from app.models.sql_models import EcosystemResource, ResourceTypeEnum, AlmaTypeEnum
import logging

log = logging.getLogger("match_engine")

async def match_almas(raw_idea: str, db: AsyncSession) -> MatchResult:
    """Generate embedding for raw_idea, search Qdrant for top 3 of each type."""
    vector = await generate_embedding(raw_idea)

    theoretical_hits = await search_almas(vector, alma_type="THEORETICAL", top_k=3)
    methodological_hits = await search_almas(vector, alma_type="METHODOLOGICAL", top_k=3)

    # Verificação de Aderência (Threshold) para Almas Teóricas
    max_score = max([hit.get("score", 0.0) for hit in theoretical_hits]) if theoretical_hits else 0.0
    
    if max_score < 0.65:
        log.info(f"Low match score ({max_score:.2f}) for theoretical almas. Auto-generating custom Alma for: {raw_idea[:30]}...")
        try:
            alma_data = await genesis_service.generate_alma(raw_idea)
            
            # Robustness: Se o LLM retornar system_prompt como dict, converte para string
            import json
            prompt_data = alma_data.get("system_prompt", "")
            if isinstance(prompt_data, dict):
                prompt_data = json.dumps(prompt_data, ensure_ascii=False)
                
            new_alma = EcosystemResource(
                resource_type=ResourceTypeEnum.ALMA,
                name=f"{alma_data['name']} (Sintética)",
                description=alma_data["description"],
                alma_type=AlmaTypeEnum.THEORETICAL,
                system_prompt=prompt_data,
                personality_descriptor=alma_data["description"][:100],
                is_approved=True
            )
            db.add(new_alma)
            await db.commit()
            await db.refresh(new_alma)
            
            # Indexar em Qdrant
            await index_alma(new_alma)
            
            # Inserir como sugestão principal
            new_hit = {
                "id": str(new_alma.id),
                "name": new_alma.name,
                "description": new_alma.description,
                "alma_type": "THEORETICAL",
                "personality_descriptor": new_alma.personality_descriptor,
                "score": 0.9999, # Pontuação alta para destaque
            }
            theoretical_hits.insert(0, new_hit)
            log.info(f"Auto-generated Alma {new_alma.name} added to match result.")
        except Exception as e:
            log.error(f"Auto-genesis failed during match fallback: {e}")

    def to_suggestion(hit: dict) -> AlmaSuggestion:
        return AlmaSuggestion(
            id=hit.get("id", ""),
            name=hit.get("name", ""),
            description=hit.get("description", ""),
            alma_type=hit.get("alma_type", ""),
            personality_descriptor=hit.get("personality_descriptor", ""),
            score=round(hit.get("score", 0.0), 4),
        )

    return MatchResult(
        theoretical=[to_suggestion(h) for h in theoretical_hits],
        methodological=[to_suggestion(h) for h in methodological_hits],
    )
