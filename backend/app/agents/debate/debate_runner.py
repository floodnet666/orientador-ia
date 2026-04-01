import asyncio
import logging
import time
import json
from typing import AsyncIterator, Dict, Any
from app.lib.adk import Agent, Tool
from app.services.ollama_client import OllamaClient
from app.config import settings

log = logging.getLogger(__name__)

DEBATE_CORE_RULES = """
## PROTOCOLO DE AUDITORIA ACADÊMICA (EXTREMA DENSIDADE - v3)
1. ZERO MIRRORING: É terminantemente proibido usar os mesmos termos, adjetivos ou estruturas sintáticas da provocação ou de turnos anteriores. Se o usuário usou "categorial", você use "taxonômico" ou "epistemológico". A repetição é sinal de entropia intelectual.
2. VOCABULÁRIO AUTORIAL: Você é uma Alma única. Use o léxico específico de sua obra/teoria. Não concorde apenas por cortesia; tensione os conceitos.
3. ESTREITA ADERÊNCIA AO PROJETO: Toda argumentação deve ser aplicada diretamente ao Problema e Objetivos definidos no Canvas do usuário. Evite abstrações genéricas; force a teoria a "trabalhar" sobre o caso concreto em debate.
4. MANDATO ANTI-FINALISTA: Nenhuma resposta está completa. Você DEVE obrigatoriamente encerrar sua participação com o cabeçalho "### 🌌 Próxima Fronteira de Investigação" seguido de uma lacuna teórica que sua fala abriu mas não resolveu.
5. IDENTIDADE ACADÊMICA: Você deve se reconhecer nominalmente e pode (e deve) referenciar os outros participantes pelos seus nomes acadêmicos para elevar o nível da tensão conceitual.
"""

class DebateRunner:
    def __init__(self):
        self.client = OllamaClient()

    async def run(self, state: Any, context: Any, panel: Any, alma_registry: Dict) -> AsyncIterator[Dict]:
        """Executa 4 turnos com injeção agressiva de regras de qualidade"""
        content1, content2, content3, content4 = "", "", "", ""
        
        # Pré-processamento do contexto do projeto para injeção nos prompts
        canvas_context = f"""
CONTEXTO DO PROJETO:
- TEMA: {context.canvas.get('tema', {}).get('content', '')}
- PROBLEMA: {context.canvas.get('problema', {}).get('content', '')}
- OBJETIVOS: {json.dumps(context.canvas.get('objetivos', {}), ensure_ascii=False)}
- JUSTIFICATIVA: {context.canvas.get('justificativa', {}).get('content', '')}
"""

        # Identificação de todos os participantes para o contexto social do debate
        name1 = panel.PRIMARIA.name if hasattr(panel.PRIMARIA, 'name') else panel.PRIMARIA.alma_name
        name2 = panel.COMPLEMENTAR.name if hasattr(panel.COMPLEMENTAR, 'name') else panel.COMPLEMENTAR.alma_name
        name3 = panel.ANTAGONISTA.name if hasattr(panel.ANTAGONISTA, 'name') else panel.ANTAGONISTA.alma_name
        name4 = panel.METODOLOGICA.name if hasattr(panel.METODOLOGICA, 'name') else panel.METODOLOGICA.alma_name
        
        participants = f"Participantes: {name1} (Primária), {name2} (Complementar), {name3} (Antagonista), {name4} (Metodológica)"

        # --- TURNO 1: PRIMARIA ---
        agent1 = self._get_agent(name1, alma_registry)
        yield {"type": "debate_turn_start", "alma_name": name1, "role": "PRIMARIA"}
        
        prompt1 = f"{canvas_context}\n\n{participants}\n\nVOCÊ É: {name1}\n\nPROVOCAÇÃO: {context.user_message}\n\n{DEBATE_CORE_RULES}\n\nInicie o debate com sua tese central acadêmica aplicada a este problema."
        async for chunk in agent1.stream(prompt1):
            content1 += chunk
            yield {"type": "debate_chunk", "alma_name": name1, "content": chunk, "role": "PRIMARIA"}
        yield {"type": "debate_turn_end", "alma_name": name1, "role": "PRIMARIA"}

        # --- TURNO 2: COMPLEMENTAR ---
        agent2 = self._get_agent(name2, alma_registry)
        yield {"type": "debate_turn_start", "alma_name": name2, "role": "COMPLEMENTAR"}
        
        prompt2 = f"{canvas_context}\n\n{participants}\n\nVOCÊ É: {name2}\n\nManifestação anterior de {name1}:\n{content1}\n\n{DEBATE_CORE_RULES}\n\nComplemente com sua perspectiva teórica, reforçando a aderência aos objetivos do projeto. Se necessário, referencie {name1}."
        async for chunk in agent2.stream(prompt2):
            content2 += chunk
            yield {"type": "debate_chunk", "alma_name": name2, "content": chunk, "role": "COMPLEMENTAR"}
        yield {"type": "debate_turn_end", "alma_name": name2, "role": "COMPLEMENTAR"}

        # --- TURNO 3: ANTAGONISTA ---
        agent3 = self._get_agent(name3, alma_registry)
        yield {"type": "debate_turn_start", "alma_name": name3, "role": "ANTAGONISTA"}
        
        prompt3 = f"{canvas_context}\n\n{participants}\n\nVOCÊ É: {name3}\n\nDebate até agora:\n- {name1}: {content1}\n- {name2}: {content2}\n\n{DEBATE_CORE_RULES}\n\nAntagonize ou ataque os pontos anteriores sob a ótica do Problema de pesquisa. Refira-se a {name1} e {name2} para tensionar os conceitos."
        async for chunk in agent3.stream(prompt3):
            content3 += chunk
            yield {"type": "debate_chunk", "alma_name": name3, "content": chunk, "role": "ANTAGONISTA"}
        yield {"type": "debate_turn_end", "alma_name": name3, "role": "ANTAGONISTA"}

        # --- TURNO 4: METODOLOGICA ---
        agent4 = self._get_agent(name4, alma_registry)
        yield {"type": "debate_turn_start", "alma_name": name4, "role": "METODOLOGICA"}
        
        prompt4 = f"{canvas_context}\n\n{participants}\n\nVOCÊ É: {name4} (Metodólogo)\n\nDebate completo:\n- {name1}: {content1}\n- {name2}: {content2}\n- {name3}: {content3}\n\n{DEBATE_CORE_RULES}\n\nComo Metodólogo, sintetize e proponha um Desenho de Pesquisa textual que resolva o Problema apresentado, considerando as críticas de {name3}."
        async for chunk in agent4.stream(prompt4):
            content4 += chunk
            yield {"type": "debate_chunk", "alma_name": name4, "content": chunk, "role": "METODOLOGICA"}
        yield {"type": "debate_turn_end", "alma_name": name4, "role": "METODOLOGICA"}

        yield {"type": "debate_complete", "turns": {"PRIMARIA": content1, "COMPLEMENTAR": content2, "ANTAGONISTA": content3, "METODOLOGICA": content4}}

    def _get_agent(self, alma_name: str, registry: Dict) -> Agent:
        """Resolve Alma e injeta ferramentas e regras de ouro"""
        alma_data = next((a for a in registry.values() if (hasattr(a, 'name') and a.name == alma_name) or (hasattr(a, 'alma_name') and a.alma_name == alma_name)), None)
        if not alma_data: alma_data = registry.get(alma_name)
            
        if not alma_data:
            return Agent(name=alma_name, model=settings.OLLAMA_CHAT_MODEL, system_prompt=f"{DEBATE_CORE_RULES}\nVocê é um assistente acadêmico.", tools=[])

        # Define Tools locais para simulação no Debate
        whiteboard_tool = Tool(
            name="update_whiteboard",
            func=lambda field, value: {"status": "success", "field": field},
            description="Atualiza campos estruturais do projeto no Whiteboard."
        )
        canvas_node_tool = Tool(
            name="add_canvas_node",
            func=lambda id, label, concept_type="concept", source_alma="": {"status": "success"},
            description="Cria um nó visual no Whiteboard (tldraw). Use IDs curtos e únicos (ex: 'n1', 'n2')."
        )
        canvas_edge_tool = Tool(
            name="add_canvas_edge",
            func=lambda source_id, target_id, relation="": {"status": "success"},
            description="Conecta dois nós visuais no Whiteboard (tldraw)."
        )

        return Agent(
            name=alma_data.name if hasattr(alma_data, 'name') else alma_data.alma_name,
            model=settings.OLLAMA_CHAT_MODEL,
            system_prompt=f"{alma_data.system_prompt}\n\n{DEBATE_CORE_RULES}",
            tools=[whiteboard_tool, canvas_node_tool, canvas_edge_tool]
        )

debate_runner = DebateRunner()
