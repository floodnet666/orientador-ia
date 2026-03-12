import asyncio
import logging
import time
import json
from typing import AsyncIterator, Dict, Any
from app.lib.adk import Agent
from app.services.ollama_client import OllamaClient
from app.config import settings

log = logging.getLogger(__name__)

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
        
        async for chunk in agent1.stream(context.user_message):
            content1 += chunk
            yield {"type": "debate_chunk", "alma_name": alma_name_1, "content": chunk, "role": "PRIMARIA"}
        
        debate_history.append({"name": alma_name_1, "content": content1})
        yield {"type": "debate_turn_end", "alma_name": alma_name_1, "role": "PRIMARIA"}

        # --- TURNO 2: COMPLEMENTAÇÃO (Alma Complementar) ---
        alma_name_2 = panel.COMPLEMENTAR.name if hasattr(panel.COMPLEMENTAR, 'name') else panel.COMPLEMENTAR.alma_name
        prompt_comp = f"""
        Contexto do Debate: {context.user_message}
        {alma_name_1} argumentou: "{content1}"
        
        Agora é sua vez, {alma_name_2}. 
        Reaja à fala acima. Você concorda? O que você adicionaria à tese de {alma_name_1} 
        baseado no seu referencial teórico? Seja direto e interativo.
        """
        
        agent2 = self._get_agent(alma_name_2, alma_registry)
        content2 = ""
        
        yield {"type": "debate_turn_start", "alma_name": alma_name_2, "role": "COMPLEMENTAR"}
        
        async for chunk in agent2.stream(prompt_comp):
            content2 += chunk
            yield {"type": "debate_chunk", "alma_name": alma_name_2, "content": chunk, "role": "COMPLEMENTAR"}
            
        debate_history.append({"name": alma_name_2, "content": content2})
        yield {"type": "debate_turn_end", "alma_name": alma_name_2, "role": "COMPLEMENTAR"}

        # --- TURNO 3: ANTAGONISMO (Alma Antagonista) ---
        alma_name_3 = panel.ANTAGONISTA.name if hasattr(panel.ANTAGONISTA, 'name') else panel.ANTAGONISTA.alma_name
        prompt_antag = f"""
        Estamos debatendo: {context.user_message}
        Histórico:
        - {alma_name_1}: {content1}
        - {alma_name_2}: {content2}
        
        Você é o ANTAGONISTA, {alma_name_3}. 
        Sua missão é encontrar as falhas, contradições ou pontos cegos nos argumentos de {alma_name_1} 
        e {alma_name_2}. Desafie-os teoricamente.
        """
        
        agent3 = self._get_agent(alma_name_3, alma_registry)
        content3 = ""
        
        yield {"type": "debate_turn_start", "alma_name": alma_name_3, "role": "ANTAGONISTA"}
        
        async for chunk in agent3.stream(prompt_antag):
            content3 += chunk
            yield {"type": "debate_chunk", "alma_name": alma_name_3, "content": chunk, "role": "ANTAGONISTA"}

        yield {"type": "debate_turn_end", "alma_name": alma_name_3, "role": "ANTAGONISTA"}
        
        yield {"type": "debate_complete", "turns": {
            "PRIMARIA": content1,
            "COMPLEMENTAR": content2,
            "ANTAGONISTA": content3
        }}

    def _get_agent(self, alma_name: str, registry: Dict) -> Agent:
        # Resolve alma from registry by name or ID
        alma_data = next((a for a in registry.values() if a.name == alma_name), None)
        if not alma_data:
            # Fallback for ID lookup
            alma_data = registry.get(alma_name)
            
        if not alma_data:
            log.warning(f"Alma {alma_name} not found in registry. Using default.")
            return Agent(
                name=alma_name,
                model=settings.OLLAMA_CHAT_MODEL,
                system_prompt="Você é um assistente acadêmico.",
                tools=[]
            )

        return Agent(
            name=alma_data.name,
            model=settings.OLLAMA_CHAT_MODEL,
            system_prompt=alma_data.system_prompt,
            tools=[]
        )

debate_runner = DebateRunner()
