import json
import re
from typing import Generator, Iterator
from app.models.action_token import ActionToken
from app.services.json_repair import repair_json

TOKEN_START = "`[ACTION:"
TOKEN_END   = "]`"

def parse_action_stream(
    raw_stream: Iterator[str]
) -> Generator[dict, None, None]:
    """
    Consome um iterador de chunks de texto e emite eventos.
    
    Emite:
      {"event": "text",   "data": str}
      {"event": "action", "data": ActionToken}
    
    NUNCA emite os delimitadores TOKEN_START/TOKEN_END no texto.
    NUNCA bloqueia o stream à espera de um token completo por mais de
    MAX_TOKEN_BUFFER_CHARS caracteres.
    """
    MAX_TOKEN_BUFFER_CHARS = 512  # se o buffer crescer além disto, desiste e emite como texto
    buffer = ""
    in_token = False

    for chunk in raw_stream:
        buffer += chunk

        while True:
            if not in_token:
                idx = buffer.find(TOKEN_START)
                if idx == -1:
                    # Não há início de token — emite tudo excepto o sufixo que
                    # pode ser o início de um token partido entre chunks
                    safe = buffer[: max(0, len(buffer) - len(TOKEN_START))]
                    if safe:
                        yield {"event": "text", "data": safe}
                    buffer = buffer[len(safe):]
                    break
                else:
                    # Emite tudo antes do início do token
                    if idx > 0:
                        yield {"event": "text", "data": buffer[:idx]}
                    buffer = buffer[idx:]
                    in_token = True
            else:
                # Estamos dentro de um token; procura o fim
                end_idx = buffer.find(TOKEN_END)
                if end_idx == -1:
                    # Token ainda não fechado
                    if len(buffer) > MAX_TOKEN_BUFFER_CHARS:
                        # Desiste — emite como texto e sai do modo token
                        yield {"event": "text", "data": buffer}
                        buffer = ""
                        in_token = False
                    break  # aguarda mais chunks
                else:
                    raw_token = buffer[len(TOKEN_START): end_idx]
                    buffer = buffer[end_idx + len(TOKEN_END):]
                    in_token = False
                    try:
                        repaired = repair_json(raw_token)
                        token_dict = json.loads(repaired)
                        action = ActionToken(**token_dict)
                        yield {"event": "action", "data": action}
                    except Exception:
                        # Se não conseguir parsear, emite como texto (não quebra o stream)
                        yield {"event": "text", "data": TOKEN_START + raw_token + TOKEN_END}

    # Flush do buffer restante
    if buffer:
        yield {"event": "text", "data": buffer}


from typing import AsyncGenerator, AsyncIterator

async def parse_action_stream_async(
    raw_stream: AsyncIterator[str]
) -> AsyncGenerator[dict, None]:
    """
    Versão Assíncrona do parse_action_stream para ser usada com AsyncIterators (ex: WebSocket streams).
    """
    MAX_TOKEN_BUFFER_CHARS = 512
    buffer = ""
    in_token = False

    async for chunk in raw_stream:
        buffer += chunk

        while True:
            if not in_token:
                idx = buffer.find(TOKEN_START)
                if idx == -1:
                    safe = buffer[: max(0, len(buffer) - len(TOKEN_START))]
                    if safe:
                        yield {"event": "text", "data": safe}
                    buffer = buffer[len(safe):]
                    break
                else:
                    if idx > 0:
                        yield {"event": "text", "data": buffer[:idx]}
                    buffer = buffer[idx:]
                    in_token = True
            else:
                end_idx = buffer.find(TOKEN_END)
                if end_idx == -1:
                    if len(buffer) > MAX_TOKEN_BUFFER_CHARS:
                        yield {"event": "text", "data": buffer}
                        buffer = ""
                        in_token = False
                    break
                else:
                    raw_token = buffer[len(TOKEN_START): end_idx]
                    buffer = buffer[end_idx + len(TOKEN_END):]
                    in_token = False
                    try:
                        repaired = repair_json(raw_token)
                        token_dict = json.loads(repaired)
                        action = ActionToken(**token_dict)
                        yield {"event": "action", "data": action}
                    except Exception:
                        yield {"event": "text", "data": TOKEN_START + raw_token + TOKEN_END}

    if buffer:
        yield {"event": "text", "data": buffer}
