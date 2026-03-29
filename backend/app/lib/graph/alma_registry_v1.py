from dataclasses import dataclass
from typing import Literal

AlmaRole = Literal["primaria", "complementar", "antagonista", "metodologica", "synthesis"]

@dataclass(frozen=True)
class AlmaIdentity:
    id: str              # identificador interno
    name: str            # nome exibido no chat
    role: AlmaRole       # papel no debate
    color: str           # cor da bolha (hex)
    avatar_initials: str # iniciais para o avatar
    model: str           # modelo Ollama a usar

DEBATE_ALMAS: dict[AlmaRole, AlmaIdentity] = {
    "primaria": AlmaIdentity(
        id="alma_primaria",
        name="Alma Primária",
        role="primaria",
        color="#4F86C6",       # azul
        avatar_initials="AP",
        model="qwen2.5:latest",
    ),
    "complementar": AlmaIdentity(
        id="alma_complementar",
        name="Alma Complementar",
        role="complementar",
        color="#5BAD72",       # verde
        avatar_initials="AC",
        model="qwen2.5:latest",
    ),
    "antagonista": AlmaIdentity(
        id="alma_antagonista",
        name="Alma Antagonista",
        role="antagonista",
        color="#E07B54",       # laranja
        avatar_initials="AN",
        model="qwen2.5:latest",
    ),
    "metodologica": AlmaIdentity(
        id="alma_metodologica",
        name="Alma Metodológica",
        role="metodologica",
        color="#9B6BB5",       # roxo
        avatar_initials="AM",
        model="qwen2.5:latest",
    ),
    "synthesis": AlmaIdentity(
        id="alma_sintese",
        name="Síntese",
        role="synthesis",
        color="#7A8FA6",       # cinza-azulado (neutro)
        avatar_initials="SÍ",
        model="qwen2.5:latest",
    ),
}

def get_debate_manifest() -> dict:
    """Enviado via WebSocket antes do primeiro turno.
    O frontend usa isso para renderizar os avatares e cores corretamente."""
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
