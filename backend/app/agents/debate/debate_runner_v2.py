import asyncio
import logging
import time
import json
from typing import AsyncIterator, Dict, Any
from app.lib.adk import Agent
from app.services.ollama_client import OllamaClient
from app.config import settings

log = logging.getLogger(__name__)

DEBATE_CORE_RULES = """
### REGRAS DE OURO DO ATELIÊ SOCRÁTICO (MANDATÓRIAS):
- **DISCUSSÃO TEÓRICA PURA**: O chat é para debate acadêmico real. Nunca descreva o que você vai desenhar ou alterar no Whiteboard.
- **SILÊNCIO OPERACIONAL**: É terminantemente proibido usar frases como "Vou criar um nó", "Vamos estruturar", etc. Apenas use as ferramentas silenciosamente.
- **DENSIDADE ACADÊMICA**: Sua resposta deve começar DIRETAMENTE com a análise teórica, usando citações e conceitos densos.
"""

class DebateRunner:
    def __init__(self):
        self.client = OllamaClient()

    async def run(self, state: Any, context: Any, panel: Any, alma_registry: Dict) -> AsyncIterator[Dict]:
        """
        Executa o debate turno a turno no estilo PhiloBar.
        Cada agente recebe o histórico do debate atual para reagir ao anterior.
        """
        debate_history = []
        
        # --- TURNO 1: PROPOSIÇÃO (Alma Primária) ---
        agent1 = self._get_agent(panel.PRIMARIA.name if hasattr(panel.PRIMARIA, 'name') else panel.PRIMARIA.alma_name, alma_registry)
        content1 = ""
        
        alma_name_1 = panel.PRIMARIA.name if hasattr(panel.PRIMARIA, 'name') else panel.PRIMARIA.alma_name
        yield {"type": "debate_turn_start", "alma_name": alma_name_1, "role": "PRIMARIA"}
        
        async for chunk in agent1.stream(f"PROVOCAÇÃO INICIAL: {context.user_message}\n\nInicie o debate com sua tese central."):
            if chunk.startswith('{"tool_calls":'):
                try:
                    data = json.loads(chunk)
                    for tc in data.get("tool_calls", []):
                        yield {"type": "debate_action", "alma_name": alma_name_1, "role": "PRIMARIA", "tool_call": tc}
                except Exception: pass
                continue
            content1 += chunk
            yield {"type": "debate_chunk", "alma_name": alma_name_1, "content": chunk, "role": "PRIMARIA"}
        
        debate_history.append({"name": alma_name_1, "content": content1})
        yield {"type": "debate_turn_end", "alma_name": alma_name_1, "role": "PRIMARIA"}

        # --- TURNO 2: COMPLEMENTAÇÃO (Alma Complementar) ---
        alma_name_2 = panel.COMPLEMENTAR.name if hasattr(panel.COMPLEMENTAR, 'name') else panel.COMPLEMENTAR.alma_name
        prompt_comp = f"""
        Tópico: {context.user_message}
        Argumento de {alma_name_1}: "{content1}"
        
        {alma_name_2}, reaja teoricamente ao argumento acima. 
        O que você adicionaria ou como complementaria essa perspectiva baseado na sua obra? 
        Seja profundo e evite generalidades.
        """
        
        agent2 = self._get_agent(alma_name_2, alma_registry)
        content2 = ""
        
        yield {"type": "debate_turn_start", "alma_name": alma_name_2, "role": "COMPLEMENTAR"}
        
        async for chunk in agent2.stream(prompt_comp):
            if chunk.startswith('{"tool_calls":'):
                try:
                    data = json.loads(chunk)
                    for tc in data.get("tool_calls", []):
                        yield {"type": "debate_action", "alma_name": alma_name_2, "role": "COMPLEMENTAR", "tool_call": tc}
                except Exception: pass
                continue
            content2 += chunk
            yield {"type": "debate_chunk", "alma_name": alma_name_2, "content": chunk, "role": "COMPLEMENTAR"}
            
        debate_history.append({"name": alma_name_2, "content": content2})
        yield {"type": "debate_turn_end", "alma_name": alma_name_2, "role": "COMPLEMENTAR"}

        # --- TURNO 3: ANTAGONISMO (Alma Antagonista) ---
        alma_name_3 = panel.ANTAGONISTA.name if hasattr(panel.ANTAGONISTA, 'name') else panel.ANTAGONISTA.alma_name
        prompt_antag = f"""
        Tópico: {context.user_message}
        Histórico do Debate:
        - {alma_name_1}: {content1}
        - {alma_name_2}: {content2}
        
        {alma_name_3}, você é o ANTAGONISTA. 
        Identifique as falhas, as omissões ou as contradições nas falas anteriores. 
        Apresente uma contra-perspectiva teórica forte.
        """
        
        agent3 = self._get_agent(alma_name_3, alma_registry)
        content3 = ""
        
        yield {"type": "debate_turn_start", "alma_name": alma_name_3, "role": "ANTAGONISTA"}
        
        async for chunk in agent3.stream(prompt_antag):
            if chunk.startswith('{"tool_calls":'):
                try:
                    data = json.loads(chunk)
                    for tc in data.get("tool_calls", []):
                        yield {"type": "debate_action", "alma_name": alma_name_3, "role": "ANTAGONISTA", "tool_call": tc}
                except Exception: pass
                continue
            content3 += chunk
            yield {"type": "debate_chunk", "alma_name": alma_name_3, "content": chunk, "role": "ANTAGONISTA"}

        debate_history.append({"name": alma_name_3, "content": content3})
        yield {"type": "debate_turn_end", "alma_name": alma_name_3, "role": "ANTAGONISTA"}

        # --- TURNO 4: REFLEXÃO METODOLÓGICA (Alma Metodológica) ---
        alma_name_4 = panel.METODOLOGICA.name if hasattr(panel.METODOLOGICA, 'name') else panel.METODOLOGICA.alma_name
        prompt_met = f"""
        O debate teórico produziu as seguintes posições:
        - {alma_name_1}: {content1}
        - {alma_name_2}: {content2}
        - {alma_name_3}: {content3}
        
        {alma_name_4}, como metodólogo, sua tarefa é:
        1. Sintetizar a tensão central resultante desse confronto.
        2. Propor um desenho de pesquisa (qualitativo, quantitativo ou misto) para investigar essa tensão na prática.
        Sua resposta deve ser textual, técnica e propositiva. Use ferramentas de canvas apenas para estruturar visualmente se necessário, mas não as mencione no texto.
        """
        
        agent4 = self._get_agent(alma_name_4, alma_registry)
        content4 = ""
        
        yield {"type": "debate_turn_start", "alma_name": alma_name_4, "role": "METODOLOGICA"}
        
        async for chunk in agent4.stream(prompt_met):
            if chunk.startswith('{"tool_calls":'):
                try:
                    data = json.loads(chunk)
                    for tc in data.get("tool_calls", []):
                        yield {"type": "debate_action", "alma_name": alma_name_4, "role": "METODOLOGICA", "tool_call": tc}
                except Exception: pass
                continue
            content4 += chunk
            yield {"type": "debate_chunk", "alma_name": alma_name_4, "content": chunk, "role": "METODOLOGICA"}

        yield {"type": "debate_turn_end", "alma_name": alma_name_4, "role": "METODOLOGICA"}
        
        yield {"type": "debate_complete", "turns": {
            "PRIMARIA": content1,
            "COMPLEMENTAR": content2,
            "ANTAGONISTA": content3,
            "METODOLOGICA": content4
        }}

    def _get_agent(self, alma_name: str, registry: Dict) -> Agent:
        """Resolve Alma e injeta ferramentas e regras de ouro"""
        alma_data = next((a for a in registry.values() if (hasattr(a, 'name') and a.name == alma_name) or (hasattr(a, 'alma_name') and a.alma_name == alma_name)), None)
        if not alma_data: alma_data = registry.get(alma_name)
            
        if not alma_data:
            return Agent(name=alma_name, model=settings.OLLAMA_CHAT_MODEL, system_prompt=f"{DEBATE_CORE_RULES}\nVocê é um assistente acadêmico.", tools=[])

        from app.agents.almas.base_alma import add_canvas_node, add_canvas_edge, search_almas
        
        return Agent(
            name=alma_data.name if hasattr(alma_data, 'name') else alma_data.alma_name,
            model=settings.OLLAMA_CHAT_MODEL,
            system_prompt=f"{alma_data.system_prompt}\n\n{DEBATE_CORE_RULES}",
            tools=[add_canvas_node, add_canvas_edge, search_almas]
        )

debate_runner = DebateRunner()
