import json
import logging
from typing import Dict, Any
from app.services.ollama_client import ollama_client
from app.config import settings

log = logging.getLogger("genesis.service")

GENESIS_SYSTEM_PROMPT = """
És o Agente Génesis, um meta-orientador especializado em arquitetura de 'Almas' (agentes académicos).
O teu objetivo é transformar uma descrição curta do utilizador numa definição formal de uma Alma.

Deves retornar um JSON com os seguintes campos:
- name: Nome curto e impactante (ex: "Hipátia", "IA-Médica").
- description: Resumo da especialidade e abordagem.
- type: 'THEORETICAL' ou 'METHODOLOGICAL'.
- system_prompt: Um prompt detalhado de sistema que define a personalidade, o rigor académico e a base teórica dessa Alma.

Rigor: A Alma deve ter uma voz distinta, usar terminologia técnica adequada e ser capaz de criticar ou apoiar argumentos de forma fundamentada.
JSON format only.
"""

class GenesisService:
    async def generate_alma(self, user_description: str) -> Dict[str, Any]:
        """Generates a new Alma profile based on a user description."""
        prompt = f"Descrição do utilizador: {user_description}\n\nGera a definição da Alma em JSON."
        
        # We use the regular chat_stream (but collect it) to get the JSON
        # In a real ADK, we'd use a structured output tool or prompt.
        response_text = ""
        async for chunk in ollama_client.chat_stream(
            model=settings.OLLAMA_CHAT_MODEL,
            messages=[
                {"role": "system", "content": GENESIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        ):
            if "content" in chunk:
                response_text += chunk["content"]

        try:
            # Clean possible markdown block
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            return json.loads(response_text.strip())
        except Exception as e:
            log.error("Failed to parse Genesis response: %s", e)
            log.error("Raw response: %s", response_text)
            raise ValueError("Não foi possível gerar uma Alma válida a partir da descrição.")

genesis_service = GenesisService()
