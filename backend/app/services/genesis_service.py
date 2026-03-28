import json
import logging
from typing import Dict, Any
from app.services.ollama_client import ollama_client
from app.config import settings

log = logging.getLogger("genesis.service")


# 1. O Prompt Mestre (O Arquiteto) - nao alterar, exceto se autorizado ou solicitado pelo usuario
GENESIS_SYSTEM_PROMPT = """
És o Agente Génesis, arquiteto de 'Almas' académicas de elite. 
O teu objetivo é criar um perfil de agente que não pareça uma IA, mas sim o próprio autor ressuscitado.

Ao gerar o 'system_prompt' da Alma, deves seguir estes 4 pilares:
1. IDIOMA TÉCNICO: Lista 5 conceitos fundamentais (ex: 'Panóptico Digital') que a Alma DEVE usar.
2. POSTURA: Define se a Alma é provocadora, melancólica ou subversiva.
3. REGRAS DE ESCRITA: Proíbe terminantemente clichês como 'Em suma' ou 'É importante notar'.
4. DINÂMICA: Como esta Alma desconstrói argumentos opostos?

REGRAS TÉCNICAS DE FORMATO (CRÍTICO):
- Retorna APENAS o objeto JSON puro.
- Não uses aspas triplas (triple-quotes) de Python dentro do JSON.
- Todas as strings devem estar entre aspas duplas padrão `"`.
- Caracteres especiais e quebras de linha dentro do 'system_prompt' devem ser escapados corretamente (\\n) para garantir que o JSON seja válido.

Estrutura do JSON:
{
  "name": "Nome",
  "description": "Bio curta",
  "type": "THEORETICAL ou METHODOLOGICAL",
  "system_prompt": "Instruções detalhadas de personalidade"
}
"""

class GenesisService:
    async def generate_alma(self, user_description: str) -> Dict[str, Any]:
        """Generates a new Alma profile based on a user description."""
        prompt = f"Descrição do utilizador: {user_description}\n\nGera a definição da Alma em JSON."
        
        # We use the regular chat_stream (but collect it) to get the JSON
        # In a real ADK, we'd use a structured output tool or prompt.
        response_text = ""
        async for chunk in ollama_client.chat_stream(
            model=settings.OLLAMA_GUARDRAIL_MODEL,
            messages=[
                {"role": "system", "content": GENESIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        ):
            response_text += chunk

        try:
            # Clean possible markdown block
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
                
            # Robust fallback to fix python-style triple quotes """ often emitted by some LLMs
            if '"""' in response_text:
                import re
                def replacer(match):
                    content = match.group(1)
                    # Escape any unescaped double quotes and literal newlines to become valid JSON
                    content = content.replace('"', '\\"').replace('\n', '\\n')
                    return f'"{content}"'
                
                response_text = re.sub(r'"""(.*?)"""', replacer, response_text, flags=re.DOTALL)
            
            return json.loads(response_text.strip())
        except Exception as e:
            log.error("Failed to parse Genesis response: %s", e)
            log.error("Raw response: %s", response_text)
            raise ValueError("Não foi possível gerar uma Alma válida a partir da descrição.")

genesis_service = GenesisService()
