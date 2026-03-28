"""
PanelSelector — selects 4 distinct Almas for the debate panel.
Uses qwen3.5:0.8b for fast JSON output.
"""
import json
import logging
import time
from typing import Optional

from pydantic import BaseModel

from app.services.ollama_client import ollama_client
from app.config import settings
from app.agents.debate.context_analyzer import DebateContext
from app.services.qdrant_service import search_almas

log = logging.getLogger("debate.panel_selector")


class AlmaRole(BaseModel):
    alma_id: str
    alma_name: str
    selection_rationale: str


class AntagonistRole(BaseModel):
    alma_id: str
    alma_name: str
    antagonism_angle: str


class SelectedPanel(BaseModel):
    PRIMARIA: AlmaRole
    COMPLEMENTAR: AlmaRole
    ANTAGONISTA: AntagonistRole
    METODOLOGICA: AlmaRole


from app.lib import adk

PANEL_SELECTOR_PROMPT = """
Seleccionar 4 Almas DISTINTAS para o painel de debate com base no catálogo fornecido.

REGRAS:
- PRIMARIA: Alma Teórica mais alinhada. Se active_theoretical_alma está definida, DEVE ser a PRIMARIA.
- COMPLEMENTAR: Alma Teórica que SOMAS à PRIMARIA. Escolher com sinergia clara.
- ANTAGONISTA: Alma com perspectiva crítica. Especificar antagonism_angle.
- METODOLOGICA: SEMPRE o Avatar Metodológico activo.

Responder OBRIGATORIAMENTE em JSON seguindo o schema SelectedPanel.
"""

panel_selector_agent = adk.Agent(
    name='panel_selector',
    model=f'ollama/{settings.OLLAMA_GUARDRAIL_MODEL}',
    system_prompt=PANEL_SELECTOR_PROMPT,
    output_schema=SelectedPanel
)


async def select_panel(
    context: DebateContext,
    alma_list: list,
    active_theoretical_alma: str,
    active_methodological_alma: str,
) -> SelectedPanel:
    """Select 4 debate Almas from the available registry."""
    t0 = time.perf_counter()

    # Prepare semantic search probe from context
    search_probe = (
        f"Perspectiva teórica sobre: {context.canvas.get('tema', {}).get('content', '')}. "
        f"Problema: {context.canvas.get('problema', {}).get('content', '')}. "
        f"Objetivo do debate: {context.debate_intent}"
    )
    
    # 1. Generate embedding for the search probe
    query_vector = await ollama_client.embed(search_probe)
    
    # 2. Search for theoretical almas
    theoretical_matches = await search_almas(query_vector, "THEORETICAL", top_k=10)
    if not theoretical_matches:
        raise ValueError("No THEORETICAL Almas found in semantic search. Ensure Almas are indexed.")
    
    # 3. Search for a critical/antagonist perspective
    antagonist_probe = f"Crítica ou perspectiva divergente sobre: {context.canvas.get('tema', {}).get('content', '')}"
    antagonist_vector = await ollama_client.embed(antagonist_probe)
    antagonist_matches = await search_almas(antagonist_vector, "THEORETICAL", top_k=10)
    
    # Filter out primary if already set
    available_theo = [m for m in theoretical_matches if m["name"].upper() != active_theoretical_alma.upper()]
    
    # Selection Logic:
    # PRIMARIA
    if active_theoretical_alma:
        # Attempt 1: exact case-insensitive match
        primary_alma_match = next(
            (m for m in theoretical_matches if m["name"].upper() == active_theoretical_alma.upper()),
            None
        )
        # Attempt 2: substring match (e.g., "Raissi" matches "Maziar Raissi")
        if not primary_alma_match:
            primary_alma_match = next(
                (m for m in theoretical_matches if active_theoretical_alma.upper() in m["name"].upper()),
                None
            )
        # Attempt 3: alma_list local search (substring)
        if not primary_alma_match:
            p_obj = next(
                (a for a in alma_list if
                 active_theoretical_alma.upper() in a.name.upper() or
                 a.name.upper() in active_theoretical_alma.upper()),
                None
            )
            if p_obj:
                primary_alma_match = {"id": str(p_obj.id), "name": p_obj.name, "score": 1.0}

        if primary_alma_match:
            primaria = AlmaRole(alma_id=primary_alma_match["id"], alma_name=primary_alma_match["name"], selection_rationale="Alma Teórica ativa do projeto.")
        elif context.debate_intent == "FREE_DEBATE" and theoretical_matches:
            p = theoretical_matches[0]
            primaria = AlmaRole(alma_id=p["id"], alma_name=p["name"], selection_rationale=f"Alma ativa '{active_theoretical_alma}' não encontrada, usando melhor afinidade (score: {p['score']:.2f}).")
            log.warning("[DEBATE] Active alma '%s' not found. Using best match: %s", active_theoretical_alma, p["name"])
        else:
            raise ValueError(f"Active theoretical alma '{active_theoretical_alma}' not found in registry.")
    else:
        p = theoretical_matches[0]
        primaria = AlmaRole(alma_id=p["id"], alma_name=p["name"], selection_rationale=f"Maior afinidade semântica (score: {p['score']:.2f})")

    # COMPLEMENTAR — must be different from PRIMARIA
    available_theo = [m for m in theoretical_matches if m["name"] != primaria.alma_name]
    if not available_theo:
        if len(theoretical_matches) > 1:
            c = next(m for m in theoretical_matches if m["name"] != primaria.alma_name)
        else:
            raise ValueError("Insufficient THEORETICAL Almas for a full panel (need at least 2 distinct).")
    else:
        c = available_theo[0]

    complementar = AlmaRole(alma_id=c["id"], alma_name=c["name"], selection_rationale=f"Sinergia temática (score: {c['score']:.2f})")

    # ANTAGONISTA
    # Pick someone different from P and C
    a_matches = [m for m in antagonist_matches if m["name"] not in [primaria.alma_name, complementar.alma_name]]
    if not a_matches:
        # Try picking from the general theoretical matches if antagonist-specific failed
        a_matches = [m for m in theoretical_matches if m["name"] not in [primaria.alma_name, complementar.alma_name]]
    
    if not a_matches:
        raise ValueError("Could not find a distinct ANTAGONISTA alma.")
        
    a = a_matches[0]
    antagonista = AntagonistRole(alma_id=a["id"], alma_name=a["name"], antagonism_angle=f"Tensão crítica detectada (score: {a['score']:.2f})")

    # METODOLOGICA
    m_alma = active_methodological_alma or "Avatar Metodológico"
    metodologica = AlmaRole(
        alma_id=m_alma,
        alma_name=m_alma,
        selection_rationale="Suporte metodológico e desenho de instrumentos."
    )

    log.info("[DEBATE] Panel selected in %.2fs: P=%s, C=%s, A=%s", time.perf_counter() - t0, primaria.alma_name, complementar.alma_name, antagonista.alma_name)
    
    return SelectedPanel(
        PRIMARIA=primaria,
        COMPLEMENTAR=complementar,
        ANTAGONISTA=antagonista,
        METODOLOGICA=metodologica,
    )
