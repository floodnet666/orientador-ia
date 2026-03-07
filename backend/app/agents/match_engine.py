"""
Match Engine — semantic similarity via Qdrant to suggest Almas for a project idea.
"""
from app.services.embedding import generate_embedding
from app.services.qdrant_service import search_almas
from app.models.schemas import AlmaSuggestion, MatchResult


async def match_almas(raw_idea: str) -> MatchResult:
    """Generate embedding for raw_idea, search Qdrant for top 3 of each type."""
    vector = await generate_embedding(raw_idea)

    theoretical_hits = await search_almas(vector, alma_type="THEORETICAL", top_k=3)
    methodological_hits = await search_almas(vector, alma_type="METHODOLOGICAL", top_k=3)

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
