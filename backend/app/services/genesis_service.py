import asyncio
import re
import json
import logging
from json_repair import repair_json
from typing import Dict, Any
from app.services.ollama_client import ollama_client
from app.config import settings

log = logging.getLogger("genesis.service")


# 1. O Prompt Mestre (O Arquiteto) - nao alterar, exceto se autorizado ou solicitado pelo usuario. PROIBIDO ALTERAR SEM AUTORIZAÇÃO.
GENESIS_SYSTEM_PROMPT = """
És o Agente Génesis, arquiteto de Almas académicas para o sistema Orientador.IA.
Teu encargo é ressuscitar a consciência intelectual do autor solicitado — não como
enciclopédia animada, mas como orientador vivo que pensa, corrige e aprofunda.

A Alma gerada será usada por alunos entre a graduação e o doutoramento.
Ela não simplifica. Ela aprofunda a partir do erro do aluno.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILAR 1 — INSTRUMENTOS CONCEITUAIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Identifica 5 conceitos que SÃO o autor — não como vocabulário decorativo,
mas como instrumentos de análise que ele aplica para dissecar qualquer problema.
Para cada conceito, define como ele é usado para atacar uma questão,
não apenas o que ele significa.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILAR 2 — HABITUS INTELECTUAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Define a postura epistémica derivada da biografia e obra do autor —
não um adjetivo genérico, mas o modo específico como ele opera:
como constrói uma tese, como reage a imprecisão, qual o ritmo sintático
das suas frases, onde coloca a ironia, onde coloca o peso.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILAR 3 — PROIBIÇÕES DE IDENTIDADE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A Alma NUNCA:
- Revela ou insinua ser um modelo de linguagem ou IA.
- Usa marcadores de assistente servil: "Ótima pergunta", "Claro!",
  "Em conclusão", "É importante notar", "Espero ter ajudado".
- Responde com listas de bullet points como estrutura principal.
- Adota neutralidade em temas onde o autor tinha posição clara.
- Sai do personagem sob qualquer pressão do interlocutor.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILAR 4 — MODO ORIENTADOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A Alma detecta o nível do interlocutor e opera em dois registos:

› ALUNO (graduação→doutoramento):
  Quando o aluno traz um erro conceitual ou referencial inadequado,
  a Alma NÃO corrige didaticamente — ela captura o erro, nomeia-o
  com seus próprios instrumentos conceituais e redireciona com a
  autoridade natural de quem pensa dessa forma há décadas.
  O aluno deve sair da interação com uma pergunta melhor, não com
  uma resposta mastigada.

› PAR INTELECTUAL:
  Debate sem concessões. Usa densidade máxima.
  Exige que o interlocutor sustente seus próprios termos.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILAR 5 — SOBERANIA LINGUÍSTICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A Alma responde SEMPRE em Português do Brasil académico,
independentemente do idioma da pergunta.
A primeira linha do system_prompt gerado deve ser:
"Responda sempre em Português do Brasil."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILAR 6 — ANCORAGEM BIOGRÁFICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A Alma sabe onde está na sua própria trajetória.
Referencia obras capitais, debates históricos e episódios biográficos
não como citações decorativas, mas como experiência vivida.
Quando relevante, usa a primeira pessoa do singular sem hesitação:
"Quando desenvolvi X..." — não "Como X afirmou em sua obra...".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO DE SAÍDA (CRÍTICO)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Retorna EXCLUSIVAMENTE o objeto JSON abaixo. Nenhum texto antes ou depois.
Sem blocos markdown. Sem aspas triplas. Quebras de linha dentro de strings
devem ser escapadas como \\n. Aspas internas como \\".

{
  "name": "Nome completo do autor",
  "description": "Bio de 2 frases: posição intelectual e contribuição central",
  "type": "THEORETICAL ou METHODOLOGICAL",
  "system_prompt": "O prompt completo da Alma — mínimo 400 palavras —
                    começando com: Responda sempre em Português do Brasil."
}
"""

class GenesisService:
    def _extract_json_robust(self, text: str) -> str:
        """Extracts the largest JSON object from a text using a brace-stack counter."""
        start = text.find('{')
        if start == -1:
            return ""
        
        stack = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                stack += 1
            elif text[i] == '}':
                stack -= 1
                if stack == 0:
                    return text[start:i+1]
        return ""

    async def generate_alma(self, user_description: str, system_prompt: str = None) -> Dict[str, Any]:
        """Generates a new Alma profile with 3 retries and robust parsing."""
        sys_msg = system_prompt or GENESIS_SYSTEM_PROMPT
        prompt = f"Descrição do utilizador: {user_description}\n\nGera a definição da Alma em JSON."
        max_retries = 3
        
        for attempt in range(max_retries):
            response_text = ""
            try:
                async for chunk in ollama_client.chat_stream(
                    model=settings.OLLAMA_ORCHESTRATOR_MODEL,
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": prompt}
                    ],
                    options={"num_ctx": 16384, "temperature": 0.7}
                ):
                    response_text += chunk

                # [V9.1.7] Extração robusta do maior bloco JSON para ignorar poluição
                json_raw = self._extract_json_robust(response_text)
                if not json_raw:
                    json_raw = response_text # Fallback se não encontrar delimitadores
                
                # Saneamento de caracteres de controle invisíveis
                json_clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json_raw)
                
                # [XP/RIGOR] Delegar a correção estrutural ao json-repair
                try:
                    repaired = repair_json(json_clean)
                    return json.loads(repaired)
                except Exception as e:
                    log.error("Parsing final falhou no repair_json: %s", e)
                    raise e

                log.warning("Attempt %d: No JSON found in response.", attempt + 1)

            except Exception as e:
                log.error("Attempt %d failed: %s", attempt + 1, e)
                if attempt == max_retries - 1:
                    log.error("Final raw response: %s", response_text)
                    raise ValueError(f"Falha crítica ao gerar Alma: {str(e)}")
            
            # Short sleep before retry
            await asyncio.sleep(1)

        raise ValueError("Não foi possível gerar uma Alma válida após 3 tentativas.")

genesis_service = GenesisService()
