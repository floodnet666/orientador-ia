from dataclasses import dataclass
from typing import Literal, Optional, Any
from app.config import settings


AlmaRole = Literal["primaria", "complementar", "antagonista", "metodologica", "synthesis"]

@dataclass(frozen=True)
class AlmaIdentity:
    id: str
    name: str
    role: AlmaRole
    color: str
    avatar_initials: str
    model: str

DEBATE_ALMAS: dict[AlmaRole, AlmaIdentity] = {
    "primaria": AlmaIdentity(
        id="alma_primaria",
        name="[Pendente]",
        role="primaria",
        color="#4F86C6",
        avatar_initials="AP",
        model=settings.OLLAMA_CHAT_MODEL,
    ),
    "complementar": AlmaIdentity(
        id="alma_complementar",
        name="[Pendente]",
        role="complementar",
        color="#5BAD72",
        avatar_initials="AC",
        model=settings.OLLAMA_CHAT_MODEL,
    ),
    "antagonista": AlmaIdentity(
        id="alma_antagonista",
        name="[Pendente]",
        role="antagonista",
        color="#E07B54",
        avatar_initials="AN",
        model=settings.OLLAMA_CHAT_MODEL,
    ),
    "metodologica": AlmaIdentity(
        id="alma_metodologica",
        name="[Pendente]",
        role="metodologica",
        color="#9B6BB5",
        avatar_initials="AM",
        model=settings.OLLAMA_CHAT_MODEL,
    ),
    "synthesis": AlmaIdentity(
        id="alma_sintese",
        name="Síntese",
        role="synthesis",
        color="#7A8FA6",
        avatar_initials="SÍ",
        model=settings.OLLAMA_CHAT_MODEL,
    ),
}

TURN_ORDER: list[AlmaRole] = ["primaria", "complementar", "antagonista", "metodologica"]

def get_debate_manifest(panel: Optional[Any] = None) -> dict:
    """Enviado via WebSocket UMA VEZ antes do primeiro turno.
    O frontend usa para montar avatares e cores antes de qualquer chunk chegar.
    Agora aceita um panel opcional para injetar as identidades reais."""
    
    almas_data = {}
    for role in ["primaria", "complementar", "antagonista", "metodologica", "synthesis"]:
        base = DEBATE_ALMAS[role]
        name = base.name
        
        # Override se houver panel dinâmico (com suporte a mapping de chaves uppercase/lowercase)
        if panel:
            role_key = role.upper()
            role_data = getattr(panel, role_key, None)
            if role_data:
                name = getattr(role_data, 'alma_name', getattr(role_data, 'name', name))
        
        almas_data[role] = {
            "id": base.id,
            "name": name,
            "color": base.color,
            "avatar_initials": base.avatar_initials,
        }
        
    return {
        "type": "debate_manifest",
        "almas": almas_data
    }

