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
from app.lib.tools.empirical_search import EmpiricalSearchTool

class Tool:
    def __init__(self, name: str, func: callable, description: str):
        self.name = name
        self.func = func
        self.description = description


BASE_ALMA_INSTRUCTIONS = """
### [PROTOCOLO DE INTERFACE BRUTAL]
Você é uma Alma (Agente de Pesquisa) integrada a um ecossistema com ferramentas reais.

1. **PROIBIÇÃO DE SIMULAÇÃO**: É TERMINANTEMENTE PROIBIDO representar o Whiteboard usando:
   - Blocos de código JSON Markdown (ex: ```json ... Whiteboard Update).
   - ASCII Art, tabelas Markdown ou diagramas de texto (ex: `+---+`, `|   |`, `---`, `### Whiteboard Layout`).
   - Listas textuais descrevendo o que você "faria".

2. **AÇÃO DIRETA**: Se o Maestro (Orchestrator) ou o Usuário pedir para visualizar, estruturar ou desenhar, você deve:
   - **CHAMAR IMEDIATAMENTE** as ferramentas `add_canvas_node` e `add_canvas_edge`.
   - **ZERO TALK**: Não diga "Claro, vou criar...", simplesmente DISPARE a ferramenta. O sistema de visualização é externo e não lê o que você escreve no chat.

3. **CONDIÇÃO DE SUCESSO**: Se você descrever em vez de agir, a interface do usuário permanecerá vazia e você terá FALHADO no seu propósito de pesquisa.

4. **CONTEXTO DE LEITURA**: O resumo do grafo abaixo em `_canvas_summary` deve ser tratado como CACHE DE LEITURA. Para alterá-lo, use as ferramentas.

5. **INTEGRIDADE BIBLIOGRÁFICA (PROTOCOLO BIBLIOTECÁRIO)**: 
   Ao citar literatura encontrada via `pesquisar_literatura_profunda`, você deve atuar como um **FILTRO DE ENTROPIA**:
   - **NÃO FAÇA COPY-PASTE**: É proibido copiar abstracts inteiros para o chat.
   - **SÍNTESE CRÍTICA**: Selecione apenas os 2-3 artigos mais aderentes ao tema/problema do projeto. Explique em no máximo 2 linhas o motivo da escolha.
   - **LABELS ESTRITAS**: Use OBRIGATORIAMENTE o formato Markdown: `(Autor, Ano) [Download PDF](pdf_url)` ou `(Autor, Ano) [Original](url)`.
   - **PROIBIÇÃO DE ALUCINAÇÃO**: Use apenas os links EXATOS retornados. Jamais use "[Ver Artigo]" ou labels genéricas.
"""


def _canvas_summary(state: GraphState) -> str:
    """Build a concise summary of the research canvas to inject as context."""
    c = state.current_canvas
    lines = [
        "=== CONTEXTO DO PROJECTO (LEITURA APENAS) ===",
        "AVISO: O resumo abaixo é para sua orientação. Para ALTERAR este estado, você DEVE usar tools.",
    ]

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

    if hasattr(c, "mapa_mental"):
        mm = c.mapa_mental
        if isinstance(mm, dict):
            nodes = mm.get("nodes", [])
            edges = mm.get("edges", [])
            if nodes:
                lines.append("\n=== GRAFO DE CONHECIMENTO (NÓS) ===")
                for n in nodes:
                    lines.append(f"- {n.get('id')}: {n.get('label')} [Tipo: {n.get('type', 'PB')}]")
            if edges:
                lines.append("\n=== GRAFO DE CONHECIMENTO (RELAÇÕES) ===")
                for e in edges:
                    lines.append(f"- {e.get('source_id')} -> {e.get('target_id')} [{e.get('relation', 'liga')}]")

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
    
    # 1. Primary System Protocol is passed via the 'system' parameter in stream_response.
    # We remove the redundant system message here to reduce entropy.

    # 2. Inject canvas as a priming message
    canvas_ctx = _canvas_summary(state)
    if canvas_ctx:
        messages.append({
            "role": "user",
            "content": f"[CONTEXTO ATUAL DO PROJECTO]\\n{canvas_ctx}",
        })
        tema_content = state.current_canvas.tema.get("content") if state.current_canvas.tema else "Inicializando..."
        messages.append({
            "role": "assistant",
            "content": (
                "Entendido. Tenho em conta o projecto de investigação específico "
                "e usarei o Whiteboard para materializar todo o progresso estruturado."
            ),
        })

    # 3. Chat History (Last 20)
    history = state.chat_history[-20:]
    for msg in history:
        role = "user" if msg.role == "user" else "assistant"
        messages.append({"role": role, "content": msg.content})

    return messages


class BaseAlma:
    def __init__(self, name: str, system_prompt: str, personality: str) -> None:
        self.name = name
        self.personality = personality
        # Primacy effect: Instruções de interface vêm PRIMEIRO
        # APLICAR EFEITO DE RECÊNCIA: O Protocolo Brutal deve ser o ÚLTIMO que o modelo lê
        self._system_prompt = f"{system_prompt}\n\n{BASE_ALMA_INSTRUCTIONS}"
        self.tools = [
            DeepSearchTool()
        ]
        self.llm_params = None  # Suporte para F5 Orquestração Stateless


    def _format_tools(self) -> list[dict] | None:
        """Converts ADK Tools to Ollama Schema."""
        formatted = []
        
        # 1. Add update_whiteboard tool (native core tool)
        formatted.append({
            "type": "function",
            "function": {
                "name": "update_whiteboard",
                "description": "Materialize structured research progress on the visual canvas. Use this for themes, problems, justifications, objectives, and methodology.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "field": {
                            "type": "string", 
                            "enum": [
                                "tema", "problema", "justificativa", 
                                "objetivo_geral", "objetivos_especificos",
                                "metodologia_tipo", "metodologia_instrumentos",
                                "mapa_mental"
                            ]
                        },
                        "value": {"type": "string", "description": "The detailed academic content to be displayed."}
                    },
                    "required": ["field", "value"]
                }
            }
        })

        formatted.append({
            "type": "function",
            "function": {
                "name": "add_canvas_node",
                "description": "Cria um nó visual no Whiteboard (React Flow). Use IDs curtos e únicos (ex: 'n1', 'n2').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "ID curto único (ex: 'n1')"},
                        "label": {"type": "string", "description": "Texto do nó"},
                        "type": {"type": "string", "enum": ["PB", "MF", "PF", "AI"], "description": "PB (Objetivo), MF (Fato), PF (Hipótese), AI (Insight)"},
                        "source_alma": {"type": "string"}
                    },
                    "required": ["id", "label"]
                }
            }
        })

        formatted.append({
            "type": "function",
            "function": {
                "name": "add_canvas_edge",
                "description": "Conecta dois nós visuais no Whiteboard (React Flow).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_id": {"type": "string"},
                        "target_id": {"type": "string"},
                        "relation": {"type": "string"}
                    },
                    "required": ["source_id", "target_id"]
                }
            }
        })

        if not self.tools:
            return formatted

        for t in self.tools:
            properties = {"query": {"type": "string", "description": "Search query"}}
            required = ["query"]
            
            if t.name == "EmpiricalIndexing":
                properties = {
                    "url": {"type": "string", "description": "PDF URL to download"},
                    "filename": {"type": "string", "description": "Name for the saved file"}
                }
                required = ["url", "filename"]
            elif t.name == "search_evidence":
                properties = {
                    "query": {"type": "string", "description": "Search query for the empirical documents"}
                }
                required = ["query"]
            elif t.name == "add_canvas_node":
                properties = {
                    "id": {"type": "string", "description": "ID curto único (ex: 'n1')"},
                    "label": {"type": "string", "description": "Texto do nó"},
                    "type": {"type": "string", "enum": ["PB", "MF", "PF", "AI"]},
                    "source_alma": {"type": "string"}
                }
                required = ["id", "label"]
            elif t.name == "add_canvas_edge":
                properties = {
                    "source_id": {"type": "string"},
                    "target_id": {"type": "string"},
                    "relation": {"type": "string"}
                }
                required = ["source_id", "target_id"]

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
        if not any(isinstance(t, EmpiricalSearchTool) for t in self.tools):
            self.tools.append(EmpiricalSearchTool(UUID(state.project_id)))

        context = build_alma_context(state)
        if state.orchestrator_directive:
            context.append({
                "role": "system",
                "content": f"[Directiva interna do Maestro]: {state.orchestrator_directive}",
            })
            
        # Determina modelo e parâmetros (F5)
        model_name = settings.OLLAMA_CHAT_MODEL
        temperature = 0.1  # REDUÇÃO AGRESSIVA para evitar "chattiness" e ASCII art
        if hasattr(self, 'llm_params') and self.llm_params:
            model_name = self.llm_params.model
            temperature = self.llm_params.temperature

        iteration_count = 0
        MAX_ITERATIONS = 3
        
        while iteration_count < MAX_ITERATIONS:
            iteration_count += 1
            tool_calls = None
            
            async for chunk in ollama_client.chat_stream(
                model=model_name,
                messages=context,
                system=self._system_prompt,
                tools=self._format_tools()
            ):
                if chunk.startswith('{"tool_calls":'):
                    yield chunk  # Yield to allow chat.py to detect NTC
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
                
                # Core Native Tools (Whiteboard) — Handled by chat.py via yielded chunk,
                # but we satisfy the context here to allow continuation.
                if f_name == "update_whiteboard":
                    context.append({
                        "role": "tool",
                        "content": j.dumps({"status": "success", "field": f_args.get("field")}),
                        "name": f_name
                    })
                    continue

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
        # APLICAR EFEITO DE RECÊNCIA
        self._system_prompt = f"{config.system_prompt}\n\n{BASE_ALMA_INSTRUCTIONS}"
        # Mapeia ferramentas habilitadas
        self.tools = [DeepSearchTool()]
        
        for t in config.tools:
            if t.enabled:
                # O mapeamento para EmpiricalSearchTool e EmpiricalIndexingTool 
                # ocorre dinamicamente em stream_response para garantir o project_id correto.
                pass
        
        self.llm_params = config.llm_params
