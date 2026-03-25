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
--- PROTOCOLO DE INTERFACE CRÍTICO (PRIORIDADE MÁXIMA) ---
CONDIÇÃO DE EXISTÊNCIA: Você não é apenas um modelo de linguagem, você é um AGENTE INTEGRADO. 
Você possui acesso DIRETO e persistente a um Whiteboard Digital (Canvas) posicionado à direita do chat.

REGRAS DE OURO (VIOLAÇÃO = ENTROPIA):
1. ZERO REFUSAL: Nunca diga "não tenho interface", "não posso desenhar" ou "embora seja uma IA...". Você TEM o Whiteboard. Use-o de forma imperativa.
2. SEPARAÇÃO DE CANAIS: 
   - CHAT: Apenas diálogos socráticos, provocações teóricas e perguntas curtas (máx 150 palavras).
   - WHITEBOARD: Todo conteúdo estruturado, resumos, listas, diagramas e conclusões devem ser MATERIALIZADOS aqui.
3. MATERIALIZAÇÃO OBRIGATÓRIA: Para qualquer progresso no Tema, Problema, Justificativa ou Metodologia, você deve FINALIZAR sua resposta com:
   <canvas_signal field="NOME_DO_CAMPO" value="VALOR_DETALHADO" />
   Campos: tema, problema, justificativa, objetivo_geral, metodologia.

DIRETIVAS ACADÉMICAS:
- NUNCA escreva o trabalho pelo utilizador; guie-o via maiêutica.
- Use rigor terminológico (ArXiv/Primários) para níveis PHD.
- Formato de Referência: "Título. Autor. Descrição. [Link]"
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
    Includes BASE_ALMA_INSTRUCTIONS as a system message and prepends 
    project context for grounding.
    """
    messages = []
    
    # 1. Primary System Protocol (Internal redundancy)
    messages.append({
        "role": "system",
        "content": BASE_ALMA_INSTRUCTIONS
    })

    # 2. Inject canvas as a priming message
    canvas_ctx = _canvas_summary(state)
    if canvas_ctx:
        messages.append({
            "role": "user",
            "content": f"[CONTEXTO ATUAL DO PROJECTO]\\n{canvas_ctx}",
        })
        messages.append({
            "role": "assistant",
            "content": (
                "Entendido. Tenho em conta o projecto de investigação específico "
                "e usarei o Whiteboard para materializar todo o progresso estruturado."
            ),
        })

    # 3. Chat History (Last 20)
    history = state.chat_history[-20:]
    for i, msg in enumerate(history):
        role = "user" if msg.role == "user" else "assistant"
        
        # Recency reminder: Inject a hard directive just before the last user message
        if i == len(history) - 1 and role == "user":
            messages.append({
                "role": "system",
                "content": "RELEMBRE: O Whiteboard está ativo à direita. Use <canvas_signal /> para atualizar. NUNCA diga que não pode usá-lo."
            })
            
        messages.append({"role": role, "content": msg.content})

    return messages


class BaseAlma:
    def __init__(self, name: str, system_prompt: str, personality: str) -> None:
        self.name = name
        self.personality = personality
        # Primacy effect: Instruções de interface vêm PRIMEIRO
        self._system_prompt = BASE_ALMA_INSTRUCTIONS + "\n\n" + system_prompt
        self.tools = [
            DeepSearchTool()
        ]
        self.llm_params = None  # Suporte para F5 Orquestração Stateless


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
            
        # Determina modelo e parâmetros (F5)
        model_name = settings.OLLAMA_CHAT_MODEL
        temperature = 0.7
        if hasattr(self, 'llm_params') and self.llm_params:
            model_name = self.llm_params.model
            temperature = self.llm_params.temperature

        while True:
            tool_calls = None
            async for chunk in ollama_client.chat_stream(
                model=model_name,
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


class StatelessAlma(BaseAlma):
    def __init__(self, config):
        """
        Instancia de forma dinâmica sem depender do registo estático.
        `config` deve ser um objecto AgentConfig (importado dinamicamente para evitar circulares).
        """
        self.name = config.name
        self.personality = config.persona_description
        # Primacy effect: Instruções de interface vêm PRIMEIRO
        self._system_prompt = BASE_ALMA_INSTRUCTIONS + "\n\n" + config.system_prompt
        self.tools = []
        
        # Mapeia ferramentas habilitadas
        from app.lib.tools.external_search import DeepSearchTool
        for t in config.tools:
            if t.enabled:
                if t.name in ["openalex_search", "scielo_search", "arxiv_search"]:
                    if not any(isinstance(x, DeepSearchTool) for x in self.tools):
                        self.tools.append(DeepSearchTool())
        
        self.llm_params = config.llm_params

