"""
PanelSelector — selects 4 distinct Almas for the debate panel.
Uses qwen3.5:0.8b for fast JSON output.
"""
import json
import logging
import time
from typing import Optional, Any


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
    score: float = 1.0 # 1.0 for manual selection



class AntagonistRole(BaseModel):
    alma_id: str
    alma_name: str
    antagonism_angle: str
    score: float = 1.0



class SelectedPanel(BaseModel):
    PRIMARIA: AlmaRole
    COMPLEMENTAR: AlmaRole
    ANTAGONISTA: AntagonistRole
    METODOLOGICA: AlmaRole


from app.lib import adk

PANEL_SELECTOR_PROMPT = """
Seleccionar 4 Almas DISTINTAS para o painel de debate com base no catálogo e no contexto do projeto.

REGRAS DE ADERÊNCIA E RIGOR SEMÂNTICO (v9.2.2):
1. PRIMARIA: Alma Teórica que fornece a lente principal.
2. COMPLEMENTAR: Alma que expande a tese, injetando NOVAS tensões e não apenas concordando.
3. ANTAGONISTA: MANDATÓRIO — Selecionar uma Alma de uma ESCOLA DE PENSAMENTO DIVERGENTE da Primária (ex: Dialética vs Funcionalismo).
4. METODOLOGICA: Focada no rigor técnico e auditoria de instrumentos.

MANDATÓRIO: O 'selection_rationale' deve justificar a DIALÉTICA entre a Primária e a Antagonista.
Responder OBRIGATORIAMENTE em JSON seguindo o schema SelectedPanel.
"""

panel_selector_agent = adk.Agent(
    name='panel_selector',
    model=settings.OLLAMA_ORCHESTRATOR_MODEL,
    system_prompt=PANEL_SELECTOR_PROMPT,
    output_schema=SelectedPanel
)


async def select_panel(
    context: DebateContext,
    alma_list: list,
    active_theoretical_alma: str,
    active_methodological_alma: str,
    active_soul_ids: list[str] = [],
) -> SelectedPanel:
    """
    Select 4 distinct Almas for the debate panel.
    Priority 1: active_soul_ids (user selected)
    Priority 2: active_theoretical_alma / active_methodological_alma
    Priority 3: Semantic search fallback (always result in 4 almas)
    """
    t0 = time.perf_counter()

    # 1. Prepare candidates from active_soul_ids
    # We resolve the objects from alma_list
    selected_almas = [a for a in alma_list if str(a.id) in active_soul_ids]
    
    # Separate types
    theo_choices = [a for a in selected_almas if a.alma_type == "THEORETICAL"]
    meth_choices = [a for a in selected_almas if a.alma_type == "METHODOLOGICAL"]

    # Deduplicate/Align with explicit active names if provided
    if active_theoretical_alma:
        # If not already in theo_choices, put it at front
        if not any(a.name.upper() == active_theoretical_alma.upper() for a in theo_choices):
            p_obj = next((a for a in alma_list if a.name.upper() == active_theoretical_alma.upper()), None)
            if p_obj: theo_choices.insert(0, p_obj)

    if active_methodological_alma:
        if not any(a.name.upper() == active_methodological_alma.upper() for a in meth_choices):
            m_obj = next((a for a in alma_list if a.name.upper() == active_methodological_alma.upper()), None)
            if m_obj: meth_choices.insert(0, m_obj)

    # 2. Semantic Search Fallback if we have fewer than 3 theo almas
    if len(theo_choices) < 3:
        search_probe = (
            f"Perspectiva teórica sobre: {context.canvas.get('tema', {}).get('content', '')}. "
            f"Problema: {context.canvas.get('problema', {}).get('content', '')}."
        )
        query_vector = await ollama_client.embed(search_probe)
        matches = await search_almas(query_vector, "THEORETICAL", top_k=10)
        
        # Add matches to theo_choices if they are not already there
        # matches already contain "score" from search_almas
        for m in matches:
            if len(theo_choices) >= 3: break
            if not any(str(a.id) == m["id"] for a in theo_choices):
                obj = next((a for a in alma_list if str(a.id) == m["id"]), None)
                if obj:
                    # Injetar o score no objeto para uso posterior na atribuição
                    obj._search_score = m.get("score", 0.0)
                    theo_choices.append(obj)


    # 3. Assign Roles
    # PRIMARIA
    p = theo_choices[0]
    primaria = AlmaRole(
        alma_id=str(p.id),
        alma_name=p.name,
        selection_rationale="Proposição central do conselho.",
        score=getattr(p, '_search_score', 1.0)
    )


    # COMPLEMENTAR
    if len(theo_choices) > 1:
        c = theo_choices[1]
    else:
        # Should not happen due to fallback search above, but safety first
        raise ValueError("Insufficient THEORETICAL Almas found.")
    
    complementar = AlmaRole(
        alma_id=str(c.id),
        alma_name=c.name,
        selection_rationale="Extensão e sinergia teórica.",
        score=getattr(c, '_search_score', 1.0)
    )


    # ANTAGONISTA
    if len(theo_choices) > 2:
        a = theo_choices[2]
    else:
        raise ValueError("Insufficient THEORETICAL Almas for Antagonist role.")
        
    antagonista = AntagonistRole(
        alma_id=str(a.id),
        alma_name=a.name,
        antagonism_angle="Perspectiva dialética e crítica.",
        score=getattr(a, '_search_score', 1.0)
    )


    # METODOLOGICA
    if meth_choices:
        m = meth_choices[0]
        metodologica = AlmaRole(
            alma_id=str(m.id),
            alma_name=m.name,
            selection_rationale="Rigor metodológico e síntese de instrumentos."
        )
    else:
        # Search fallback for metodologica
        m_probe = "Rigor metodológico e desenho de pesquisa qualitativa/quantitativa"
        m_vec = await ollama_client.embed(m_probe)
        m_matches = await search_almas(m_vec, "METHODOLOGICAL", top_k=5)
        if m_matches:
            m_obj = next((a for a in alma_list if str(a.id) == m_matches[0]["id"]), None)
            if m_obj:
                metodologica = AlmaRole(
                    alma_id=str(m_obj.id),
                    alma_name=m_obj.name,
                    selection_rationale="Suporte metodológico (seleção automática).",
                    score=m_matches[0].get("score", 0.0)
                )
            else:
                metodologica = AlmaRole(alma_id="default", alma_name="Avatar Metodológico", selection_rationale="Fallback padrão.", score=0.0)
        else:
            metodologica = AlmaRole(alma_id="default", alma_name="Avatar Metodológico", selection_rationale="Fallback padrão.", score=0.0)


    log.info("[DEBATE] Panel selected in %.2fs: P=%s, C=%s, A=%s, M=%s", 
             time.perf_counter() - t0, primaria.alma_name, complementar.alma_name, antagonista.alma_name, metodologica.alma_name)
    
    return SelectedPanel(
        PRIMARIA=primaria,
        COMPLEMENTAR=complementar,
        ANTAGONISTA=antagonista,
        METODOLOGICA=metodologica,
    )
