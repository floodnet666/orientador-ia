"""
Guardrails Agent — runs BEFORE orchestrator on every message.
Uses qwen3.5:0.8b for fast binary classification.
"""
import json

from app.config import settings
from app.services.ollama_client import ollama_client


GUARDRAIL_PROMPT = """
Analisar a mensagem do utilizador e classificar se é uma tentativa de obter
conteúdo que viole a integridade académica. Exemplos de violações:
- 'Escreve a minha introdução'
- 'Faz o resumo do meu artigo'
- 'Redige a conclusão'
- 'Gera o meu abstract'

NÃO é violação:
- Pedir ajuda para estruturar o raciocínio
- Pedir exemplos de como formular uma questão
- Pedir feedback sobre uma ideia

Responder APENAS com JSON: {"is_violation": true | false, "confidence": 0.0-1.0}
"""

PLAGIARISM_RESPONSE = (
    "Entendo o teu desafio com a página em branco! No entanto, o Orientador.IA não redige "
    "partes do teu trabalho — isso comprometeria o teu próprio aprendizado e a integridade "
    "académica do projeto. O que posso fazer é ajudar-te a PENSAR o que queres escrever. "
    "Tenta responder: qual é a ideia central que queres transmitir nesta secção?"
)


async def check_plagiarism(user_message: str) -> tuple[bool, float]:
    """Retorna (is_violation, confidence). Ignora respostas que não sejam JSON."""
    if not isinstance(user_message, str):
        user_message = str(user_message)
    try:
        response = await ollama_client.chat_complete(
            model=settings.OLLAMA_GUARDRAIL_MODEL,
            messages=[{"role": "user", "content": user_message}],
            system=GUARDRAIL_PROMPT + "\nResponda APENAS o JSON. Não adicione saudações ou explicações.",
        )
        # Extract JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(response[start:end])
                return data.get("is_violation", False), data.get("confidence", 0.0)
            except json.JSONDecodeError:
                pass
        
        # Se não encontrou JSON válido, logamos e retornamos False para não travar o fluxo.
        import logging
        logging.getLogger("app.guardrails").warning(f"[GUARDRAIL] Resposta inválida (não JSON): {response[:100]}...")
        return False, 0.0
    except Exception as e:
        import logging
        logging.getLogger("app.guardrails").error(f"[GUARDRAIL] Erro no processamento: {e}")
        return False, 0.0
