from dataclasses import dataclass
from typing import Literal

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
        name="Alma Primária",
        role="primaria",
        color="#4F86C6",
        avatar_initials="AP",
        model="qwen2.5:7b",
    ),
    "complementar": AlmaIdentity(
        id="alma_complementar",
        name="Alma Complementar",
        role="complementar",
        color="#5BAD72",
        avatar_initials="AC",
        model="qwen2.5:7b",
    ),
    "antagonista": AlmaIdentity(
        id="alma_antagonista",
        name="Alma Antagonista",
        role="antagonista",
        color="#E07B54",
        avatar_initials="AN",
        model="qwen2.5:7b",
    ),
    "metodologica": AlmaIdentity(
        id="alma_metodologica",
        name="Alma Metodológica",
        role="metodologica",
        color="#9B6BB5",
        avatar_initials="AM",
        model="qwen2.5:7b",
    ),
    "synthesis": AlmaIdentity(
        id="alma_sintese",
        name="Síntese",
        role="synthesis",
        color="#7A8FA6",
        avatar_initials="SÍ",
        model="qwen2.5:7b",
    ),
}

TURN_ORDER: list[AlmaRole] = ["primaria", "complementar", "antagonista", "metodologica"]

def get_debate_manifest() -> dict:
    """Enviado via WebSocket UMA VEZ antes do primeiro turno.
    O frontend usa para montar avatares e cores antes de qualquer chunk chegar."""
    return {
        "type": "debate_manifest",
        "almas": {
            role: {
                "id": alma.id,
                "name": alma.name,
                "color": alma.color,
                "avatar_initials": alma.avatar_initials,
            }
            for role, alma in DEBATE_ALMAS.items()
        }
    }
