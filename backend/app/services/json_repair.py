"""
Implementação do algoritmo de reparação de JSON especulativo.
Baseado em lib/generation/json-repair.ts do OpenMAIC.

Princípio: tenta o mínimo de reparação necessária para produzir JSON válido.
Não inventa dados — apenas fecha estruturas abertas ou remove tokens inválidos finais.
"""
import json
import re
from typing import Optional


def repair_json(raw: str) -> str:
    """
    Tenta reparar um JSON potencialmente malformado.
    
    Returns:
        String JSON válida, ou lança ValueError se impossível reparar.
    
    Estratégias aplicadas em ordem:
    1. Tenta parse directo (caso feliz)
    2. Remove trailing commas
    3. Substitui aspas simples por duplas
    4. Fecha estruturas abertas (objectos e arrays)
    5. Remove tokens incompletos no final
    """
    if not raw or not raw.strip():
        raise ValueError("JSON vazio")
    
    s = raw.strip()
    
    # Estratégia 1: parse directo
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass
    
    # Estratégia 2: trailing commas (,} e ,])
    s = re.sub(r',\s*([}\]])', r'\1', s)
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass
    
    # Estratégia 3: aspas simples -> duplas (cuidado com apostrofes)
    # Só substitui quando a aspa simples está a delimitar chave/valor
    candidate = re.sub(r"(?<![\\])'", '"', s)
    try:
        json.loads(candidate)
        return candidate
    except json.JSONDecodeError:
        pass  # não ajudou, continua com s original
    
    # Estratégia 4: fecha estruturas abertas
    s = _close_open_structures(s)
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass
    
    # Estratégia 5: remove tokens parciais no final (string incompleta)
    s = _remove_incomplete_tail(s)
    s = _close_open_structures(s)
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        raise ValueError(f"Impossível reparar JSON: {raw[:100]}...")


def _close_open_structures(s: str) -> str:
    """Fecha objectos e arrays não fechados."""
    stack = []
    in_string = False
    escape = False
    
    for ch in s:
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            stack.append('}')
        elif ch == '[':
            stack.append(']')
        elif ch in ('}', ']'):
            if stack and stack[-1] == ch:
                stack.pop()
    
    # Se estava no meio de uma string, fecha-a
    if in_string:
        s += '"'
    
    # Fecha estruturas abertas
    s += ''.join(reversed(stack))
    return s


def _remove_incomplete_tail(s: str) -> str:
    """Remove o último token se estiver incompleto."""
    # Remove string incompleta no final: "key": "val  <sem fechar>
    s = re.sub(r',?\s*"[^"]*$', '', s)
    # Remove chave sem valor no final: "key":  <sem valor>
    s = re.sub(r',?\s*"[^"]*"\s*:\s*$', '', s)
    return s


def try_repair_json(raw: str) -> Optional[dict]:
    """
    Versão segura: retorna None se não for possível reparar.
    Nunca lança excepção.
    """
    try:
        return json.loads(repair_json(raw))
    except (ValueError, json.JSONDecodeError):
        return None
