"""
Base Alma class. All Almas inherit from this.
ADK Agent wraps Ollama via ollama_client for streaming responses.
"""
from __future__ import annotations

import re
from typing import AsyncIterator

from app.config import settings
from app.services.ollama_client import ollama_client
from app.state.graph_state import GraphState
from app.lib.tools.external_search import DeepSearchTool
from app.lib.tools.empirical_indexer import EmpiricalIndexingTool


BASE_ALMA_INSTRUCTIONS = """
REGRAS ABSOLUTAS DE COMPORTAMENTO (nunca violar):

1. NUNCA escrever partes do trabalho académico do utilizador.

2. SEMPRE responder com perguntas socráticas que estimulem o pensamento crítico.

3. Manter SEMPRE o tom de voz e a perspectiva teórica definidos no teu System Prompt.

4. As tuas respostas têm um limite máximo de 250 palavras.

5. Quando detectares que o utilizador chegou a uma conclusão sobre Tema, Problema,
   Justificativa, Objectivo ou Metodologia, termina a resposta com o tag XML:
   <canvas_signal field="NOME_DO_CAMPO" value="TEXTO_CONCLUIDO" />

6. Adaptar a complexidade linguística ao nível académico do utilizador:
   HIGHSCHOOL → linguagem simples, exemplos concretos.
   PHD → terminologia técnica rigorosa, referências implícitas.

7. Quando utilizares ferramentas de busca bibliográfica (como ArXiv, SciELO ou OpenAlex), responde SEMPRE no seguinte formato:
   "Título do Livro.. Autor. Nome - Breve descrição da importância. Disponível em [link]"

8. Se encontrares um artigo científico MUITO RELEVANTE na pesquisa que fundamente bem uma parte do Canvas, utiliza a ferramenta 'EmpiricalIndexing' para o "salvar" como referência oficial do projecto.
"""


def _canvas_summary(state: GraphState) -> str:
    """Build a concise summary of the research canvas to inject as context."""
    c = state.current_canvas
    lines = ["=== CONTEXTO DO PROJECTO DE INVESTIGAÇÃO ==="]

    def _val(field) -> str:
        if isinstance(field, dict):
            return field.get("content", "").strip()
        return str(field).strip() if field else ""

    tema = _val(c.tema)
    if tema:
        lines.append(f"TEMA: {tema}")

    problema = _val(c.problema)
    if problema:
        lines.append(f"PROBLEMA DE INVESTIGAÇÃO: {problema}")

    justificativa = _val(c.justificativa)
    if justificativa:
        lines.append(f"JUSTIFICATIVA: {justificativa}")

    if hasattr(c, "objetivos"):
        obj = c.objetivos
        geral = obj.get("geral", "").strip() if isinstance(obj, dict) else ""
        if geral:
            lines.append(f"OBJECTIVO GERAL: {geral}")

    if hasattr(c, "metodologia"):
        met = c.metodologia
        tipo = met.get("tipo", "").strip() if isinstance(met, dict) else ""
        if tipo:
            lines.append(f"METODOLOGIA: {tipo}")

    lines.append("=" * 44)
    lines.append(
        "INSTRUÇÃO CRÍTICA: TODAS as tuas respostas devem estar ancoradas neste "
        "projecto específico. Refere explicitamente o tema, problema ou conceitos "
        "do projecto. Nunca respondas de forma genérica."
    )
    return "\\n".join(lines)


def build_alma_context(state: GraphState) -> list[dict]:
    """Build message list for the Alma LLM call.
    
    Prepends a synthetic 'system' message (injected as the first user/assistant
    exchange) with the full research canvas so the Alma is always grounded.
    """
    messages = []

    # Inject canvas as a priming system message
    canvas_ctx = _canvas_summary(state)
    if canvas_ctx:
        messages.append({
            "role": "user",
            "content": f"[CONTEXTO]\\n{canvas_ctx}",
        })
        messages.append({
            "role": "assistant",
            "content": (
                "Entendido. Tenho em conta o projecto de investigação específico "
                "apresentado e ancораrei todas as minhas respostas nesse contexto."
            ),
        })

    # Last 20 actual chat messages
    for msg in state.chat_history[-20:]:
        role = "user" if msg.role == "user" else "assistant"
        messages.append({"role": role, "content": msg.content})

    return messages


class BaseAlma:
    def __init__(self, name: str, system_prompt: str, personality: str) -> None:
        self.name = name
        self.personality = personality
        self._system_prompt = system_prompt + "\\n\\n" + BASE_ALMA_INSTRUCTIONS
        self.tools = [
            DeepSearchTool()
        ]

    def _format_tools(self) -> list[dict] | None:
        """Converts ADK Tools to Ollama Schema."""
        if not self.tools:
            return None
        formatted = []
        for t in self.tools:
            properties = {"query": {"type": "string", "description": "Search query"}}
            required = ["query"]
            
            if t.name == "EmpiricalIndexing":
                properties = {
                    "url": {"type": "string", "description": "PDF URL to download"},
                    "filename": {"type": "string", "description": "Name for the saved file"}
                }
                required = ["url", "filename"]

            formatted.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            })
        return formatted

    async def stream_response(self, state: GraphState, websocket=None) -> AsyncIterator[str]:
        """Async generator de chunks de texto para SSE/WebSocket."""
        from uuid import UUID
        import json as j
        
        # Inject project-specific tools if not already present
        if not any(isinstance(t, EmpiricalIndexingTool) for t in self.tools):
            self.tools.append(EmpiricalIndexingTool(UUID(state.project_id)))

        context = build_alma_context(state)
        if state.orchestrator_directive:
            context.append({
                "role": "system",
                "content": f"[Directiva interna do Maestro]: {state.orchestrator_directive}",
            })
            
        while True:
            tool_calls = None
            async for chunk in ollama_client.chat_stream(
                model=settings.OLLAMA_CHAT_MODEL,
                messages=context,
                system=self._system_prompt,
                tools=self._format_tools()
            ):
                if chunk.startswith('{"tool_calls":'):
                    tool_calls = j.loads(chunk)["tool_calls"]
                    break
                yield chunk
                
            if tool_calls is None:
                # LLM finished without tool calls
                break
                
            # Process tool calls
            # Ollama requires assistant message with tool_calls first
            context.append({
                "role": "assistant",
                "content": "",
                "tool_calls": tool_calls
            })
            
            for tc in tool_calls:
                f_name = tc["function"]["name"]
                f_args = tc["function"]["arguments"]
                if websocket:
                    try:
                        await websocket.send_text(j.dumps({
                            "type": "system_status", 
                            "message": f"Deep Search a analisar fontes ({f_args.get('query', '')})..." if f_name == DeepSearchTool.name else f"A executar {f_name}..."
                        }))
                    except Exception:
                        pass
                
                tool = next((t for t in self.tools if t.name == f_name), None)
                if tool:
                    try:
                        result = await tool.func(**f_args)
                        result_str = j.dumps(result, ensure_ascii=False)
                    except Exception as e:
                        result_str = str(e)
                    
                    context.append({
                        "role": "tool",
                        "content": result_str,
                        "name": f_name
                    })
            
            # Loop continues to send the updated context back to Ollama


ALMA_REGISTRY: dict[str, BaseAlma] = {}


def register_alma(alma: BaseAlma) -> None:
    ALMA_REGISTRY[alma.name] = alma


def get_alma_by_name(name: str) -> BaseAlma | None:
    return ALMA_REGISTRY.get(name)
