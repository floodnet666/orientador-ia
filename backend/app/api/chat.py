"""Chat endpoints: WebSocket streaming + message history.

Pipeline tracing is built-in: every step logs its elapsed time.
Debate mode is triggered when a canvas-development phrase is detected.
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import AsyncSessionLocal, get_db
from app.models.schemas import ChatMessageOut
from app.models.sql_models import (
    ChatMessage,
    EcosystemResource,
    Project,
    ProjectCanvasState,
    RoleEnum,
    User,
)
from app.state.graph_state import CanvasState, ChatMessageState, GraphState, ValidationFlags
from app.agents.state import BackendState
from app.agents.graph_factory import backend_graph
from app.lib.graph.alma_registry import DEBATE_ALMAS, get_debate_manifest
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage, ToolMessage, AIMessageChunk

router = APIRouter(prefix="/api/chat", tags=["chat"])
log = logging.getLogger("chat.pipeline")


import re

# ─── Debate trigger detection ──────────────────────────────────────────────────

_DEBATE_PATTERN = re.compile(
    r"(debate|debater|debatam|discutir|discutam|posicionamento|perspectiva|o que pensam|analisem)\s+(sobre|acerca|os|as|o|a)?",
    re.IGNORECASE
)

def _detect_debate_trigger(message: str) -> bool:
    msg = message.lower()
    # Verifica gatilhos específicos de desenvolvimento do canvas
    canvas_triggers = [
        "desenvolver a justificativa", "desenvolver o problema",
        "formular os objetivos", "definir a metodologia", "ajude com o problema"
    ]
    if any(t in msg for t in canvas_triggers):
        return True
        
    # Verifica intenção genérica de debate teórica usando Regex
    return bool(_DEBATE_PATTERN.search(msg))


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _elapsed(t0: float) -> str:
    return f"{time.perf_counter() - t0:.2f}s"


async def _safe_send_json(websocket: WebSocket, data: dict):
    """Envia JSON apenas se o WebSocket ainda estiver conectado."""
    if websocket.client_state == WebSocketState.CONNECTED:
        try:
            await websocket.send_text(json.dumps(data))
        except Exception as e:
            log.debug(f"[WS] Failed to send message: {e}")


async def _build_graph_state(project_id: UUID, user: User, db: AsyncSession) -> GraphState:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError("Project not found")

    canvas_result = await db.execute(
        select(ProjectCanvasState).where(ProjectCanvasState.project_id == project_id)
    )
    canvas_row = canvas_result.scalar_one_or_none()
    
    # Safe initialization of canvas_data
    raw_canvas = canvas_row.canvas_json if canvas_row else {}
    canvas_data = dict(raw_canvas) if isinstance(raw_canvas, dict) else {}

    theo_name, meth_name = "", ""
    if project.theoretical_alma_id:
        r = await db.execute(
            select(EcosystemResource).where(EcosystemResource.id == project.theoretical_alma_id)
        )
        a = r.scalar_one_or_none()
        if a:
            theo_name = a.name
    if project.methodological_alma_id:
        r = await db.execute(
            select(EcosystemResource).where(
                EcosystemResource.id == project.methodological_alma_id
            )
        )
        a = r.scalar_one_or_none()
        if a:
            meth_name = a.name

    msgs_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(50)
    )
    messages = list(reversed(msgs_result.scalars().all()))
    chat_history = [
        ChatMessageState(
            role=msg.role.value.lower(),
            alma_name=msg.alma_name,
            content=msg.content,
            timestamp=msg.created_at.isoformat(),
        )
        for msg in messages
    ]

    for key in ["tema", "problema", "justificativa"]:
        if key in canvas_data and isinstance(canvas_data[key], str):
            canvas_data[key] = {"content": canvas_data[key], "is_locked": False}

    # Buscar documentos empíricos do Qdrant (RAG v2.2.0)
    from app.api.empirical import list_project_documents
    doc_names = await list_project_documents(project_id, user)
    empirical_docs = [type('Doc', (), {'filename': name, 'id': name}) for name in doc_names]
    messages_as_langchain = await _build_messages_list(project_id, db)
    return BackendState(
        messages=messages_as_langchain,
        project_id=str(project_id),
        user_id=str(user.id),
        academic_level=project.academic_level.value,
        active_theoretical_alma=theo_name,
        active_methodological_alma=meth_name,
        active_soul_ids=[str(sid) for sid in (project.soul_ids or [])],
        orchestrator_directive="",
        human_guidelines=project.human_guidelines or "",
        current_canvas=CanvasState(**canvas_data) if canvas_data else CanvasState(),
        canvas_fields_to_update={},
        validation_flags=ValidationFlags(),
        empirical_documents=empirical_docs,
        is_debate_mode=False,
        debate_round_number=0,
        previous_debate_summary=None,
        debate_history=[]
    )


async def _build_messages_list(project_id: UUID, db: AsyncSession) -> List[BaseMessage]:
    """Auxiliar para carregar histórico como BaseMessages do LangChain."""
    msgs_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(50)
    )
    history = msgs_result.scalars().all()
    
    ls_messages = []
    for m in history:
        if m.role == RoleEnum.USER:
            ls_messages.append(HumanMessage(content=m.content))
        elif m.role == RoleEnum.ALMA:
            # TODO: Restaurar tool_calls se necessário para o estado
            ls_messages.append(AIMessage(content=m.content, name=m.alma_name))
        elif m.role == RoleEnum.SYSTEM:
            ls_messages.append(SystemMessage(content=m.content))
            
    return ls_messages


async def _save_message(
    db: AsyncSession,
    project_id: UUID,
    role: RoleEnum,
    content: str,
    alma_name: str | None = None,
) -> ChatMessage:
    msg = ChatMessage(
        project_id=project_id,
        role=role,
        content=content,
        alma_name=alma_name,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def _update_canvas(db: AsyncSession, project_id: UUID, fields: dict) -> dict:
    log.info("[CANVAS] Attempting update for project=%s fields=%s", project_id, fields.keys())
    result = await db.execute(
        select(ProjectCanvasState).where(ProjectCanvasState.project_id == project_id)
    )
    canvas_row = result.scalar_one_or_none()
    if not canvas_row:
        log.warning("[CANVAS] ProjectCanvasState not found for project=%s", project_id)
        return {}

    # Deep copy/dict conversion to avoid mutation issues and clarify types
    raw_json = canvas_row.canvas_json
    canvas_data = dict(raw_json) if isinstance(raw_json, dict) else {}
    for key, value in fields.items():
        if value is None:
            continue
        log.debug("[CANVAS] Updating field '%s'", key)
        if key == "tema":
            canvas_data.setdefault("tema", {})["content"] = value
        elif key == "problema":
            canvas_data.setdefault("problema", {})["content"] = value
        elif key == "justificativa":
            canvas_data.setdefault("justificativa", {})["content"] = value
        elif key == "objetivos_geral":
            canvas_data.setdefault("objetivos", {})["geral"] = value
        elif key == "objetivos_especificos" and isinstance(value, list):
            canvas_data.setdefault("objetivos", {})["especificos"] = value
        elif key == "metodologia_tipo":
            canvas_data.setdefault("metodologia", {})["tipo"] = value
        elif key == "metodologia_instrumentos" and isinstance(value, list):
            canvas_data.setdefault("metodologia", {})["instrumentos"] = value
        elif key == "mapa_mental":
            canvas_data.setdefault("mapa_mental", {})["content"] = value
        elif key == "canvas_node":
            mm = canvas_data.setdefault("mapa_mental", {})
            nodes = mm.setdefault("nodes", [])
            # Evita duplicados por ID
            node_id = value.get("id")
            if not any(n.get("id") == node_id for n in nodes):
                nodes.append(value)
        elif key == "canvas_edge":
            mm = canvas_data.setdefault("mapa_mental", {})
            edges = mm.setdefault("edges", [])
            edges.append(value)

    canvas_row.canvas_json = canvas_data
    await db.commit()
    log.info("[CANVAS] Update success project=%s", project_id)
    return canvas_data


# ─── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/{project_id}/ws")
async def chat_websocket(websocket: WebSocket, project_id: UUID):
    t_connect = time.perf_counter()
    headers = dict(websocket.headers)
    origin = headers.get("origin")
    host = headers.get("host")
    ws_version = headers.get("sec-websocket-version")
    
    token = websocket.query_params.get("token")
    log.info(
        "[WS] HANDSHAKE START: project=%s | origin=%s | host=%s | version=%s | token=%s", 
        project_id, origin, host, ws_version, "PRESENT" if token else "MISSING"
    )
    
    # Agora sim, aceitamos a conexão IMEDIATAMENTE para estabilizar o handshake
    await websocket.accept()
    log.info("[WS] ACCEPTED project=%s | origin=%s", project_id, origin)

    # Validação do Token e User
    if not token:
        log.warning("[WS] REJECTED: Missing token | project=%s", project_id)
        await _safe_send_json(websocket, {"type": "error", "message": "Missing authentication token"})
        await websocket.close(code=4001)
        return
    
    # Validação JWT
    from jose import jwt, JWTError
    from app.config import settings
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
    except JWTError as exc:
        log.error("[WS] AUTH FAILED: Invalid token | %s", exc)
        await _safe_send_json(websocket, {"type": "error", "message": "Invalid or expired token"})
        await websocket.close(code=4001)
        return

    try:
        async with AsyncSessionLocal() as db:
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                await _safe_send_json(websocket, {"type": "error", "message": "User not found"})
                await websocket.close(code=4001)
                return
            project_result = await db.execute(
                select(Project).where(Project.id == project_id, Project.user_id == user.id)
            )
            if not project_result.scalar_one_or_none():
                log.warning("[WS] PROJECT ACCESS DENIED: %s for user %s", project_id, user.email)
                await _safe_send_json(websocket, {"type": "error", "message": "Access denied to this project"})
                await websocket.close(code=4003)
                return

        log.info("[WS] AUTH OK user=%s | %.2fs", user.email, time.perf_counter() - t_connect)
        
        # Enviar evento de conexão bem-sucedida para o frontend
        await _safe_send_json(websocket, {"type": "connected", "user": user.email})

        # Verificar se a conexão ainda está aberta antes de entrar no loop
        if websocket.client_state != WebSocketState.CONNECTED:
            log.warning("[WS] Connection lost after handshake/auth for project %s", project_id)
            return

        while True:
            data = await websocket.receive_text()
            t_msg = time.perf_counter()
            msg_data = json.loads(data)
            
            if msg_data.get("type") == "ping":
                log.debug("[WS] PING received project=%s -> Sending PONG", project_id)
                await _safe_send_json(websocket, {"type": "pong"})
                continue

            if msg_data.get("type") != "message":
                log.debug("[WS] Non-message payload project=%s type=%s", project_id, msg_data.get("type"))
                continue

            user_content = msg_data.get("content", "").strip()
            if not user_content:
                continue

            # Suporte para F5 Orquestração Stateless
            agent_config_override = msg_data.get("agent_config_override")

            req_id = f"{str(project_id)[:8]}@{int(t_msg)}"
            log.info("[PIPELINE:%s] START | len=%d", req_id, len(user_content))

            # Sempre executa o pipeline padrão (o Maestro decide se é debate ou diálogo)
            await _run_standard_pipeline(
                websocket, project_id, user, user_content, req_id, t_msg, agent_config_override
            )

    except WebSocketDisconnect:
        log.info("[WS] DISCONNECTED project=%s | %.1fs", project_id, time.perf_counter() - t_connect)
    except Exception as exc:
        log.error("[WS] UNHANDLED project=%s | %s", project_id, exc, exc_info=True)
        await _safe_send_json(websocket, {"type": "error", "message": str(exc)})


# ─── Standard pipeline ─────────────────────────────────────────────────────────

async def _run_standard_pipeline(
    websocket: WebSocket,
    project_id: UUID,
    user: User,
    user_content: str,
    req_id: str,
    t_msg: float,
    agent_config_override: dict | None = None,
):
    async with AsyncSessionLocal() as db:
        # 1. Salvar mensagem do usuário
        await _save_message(db, project_id, RoleEnum.USER, user_content)

        # 2. Guardrails ELIMINADOS conforme solicitação do usuário.
        # Nenhuma filtragem de plágio ou bloqueio será aplicada aqui.

        # 3. Preparar o Estado Inicial do Grafo
        ls_messages = await _build_messages_list(project_id, db)
        # Adiciona a mensagem atual se ainda não estiver no histórico do BD
        ls_messages.append(HumanMessage(content=user_content))
        
        # Carregar metadados do projeto
        initial_state = await _build_graph_state(project_id, user, db)
        initial_state["messages"] = ls_messages

        # 4. Executar o Grafo via stream
        log.info("[PIPELINE:%s] LangGraph Executing (astream_events)...", req_id)
        
        full_response_text: str = ""
        debate_responses: dict[str, str] = {}
        last_alma_name = initial_state.get("active_theoretical_alma", "Orientador")

        try:
            # Configuração do Grafo
            config = {"configurable": {"thread_id": str(project_id)}}

            async for event in backend_graph.astream_events(
                initial_state, 
                config=config,
                version="v2"
            ):
                kind = event["event"]
                data = event.get("data", {})
                metadata = event.get("metadata", {})
                node_name = metadata.get("langgraph_node")

                # [A] Eventos de DEBATE (Manifesto e Turnos)
                if kind == "on_chain_start" and event.get("name") == "debate":
                    await _safe_send_json(websocket, get_debate_manifest())
                    log.info("[PIPELINE:%s] Debate manifest sent.", req_id)

                elif kind == "on_chat_model_start":
                    if node_name in DEBATE_ALMAS:
                        alma = DEBATE_ALMAS[node_name]
                        await _safe_send_json(websocket, {
                            "type": "debate_turn_start",
                            "alma_id": alma.id,
                            "role": node_name,
                            "alma_name": alma.name
                        })
                    elif node_name == "alma":
                        await _safe_send_json(websocket, {"type": "start"})

                # [B] Streaming de Chunks (Normal ou Debate)
                elif kind == "on_chat_model_stream":
                    if node_name == "maestro":
                        # Ocultar lógica do maestro do utilizador
                        continue

                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, 'content') and chunk.content:
                        content = str(chunk.content)
                        if node_name in DEBATE_ALMAS:
                            await _safe_send_json(websocket, {
                                "type": "debate_chunk",
                                "content": content,
                                "role": node_name,
                                "alma_name": DEBATE_ALMAS[node_name].name
                            })
                            debate_responses[node_name] = debate_responses.get(node_name, "") + content
                        else:
                            await _safe_send_json(websocket, {
                                "type": "chunk",
                                "text": content
                            })
                            full_response_text = (full_response_text or "") + content

                # [C] Tool Calls e Atualizações Visuais
                elif kind == "on_tool_end":
                    t_name = event.get("name")
                    if t_name in ["update_whiteboard", "add_canvas_node", "add_canvas_edge"]:
                        async with AsyncSessionLocal() as db_sync:
                            res = await db_sync.execute(
                                select(ProjectCanvasState).where(ProjectCanvasState.project_id == project_id)
                            )
                            canvas_row = res.scalar_one_or_none()
                            if canvas_row:
                                await _safe_send_json(websocket, {
                                    "type": "canvas_update",
                                    "canvas": canvas_row.canvas_json
                                })

                elif kind == "on_chain_end" and event.get("name") == "debate":
                    output = data.get("output", {})
                    summary = output.get("previous_debate_summary")
                    if summary:
                        await _safe_send_json(websocket, {
                            "type": "debate_question",
                            "data": summary
                        })

            # 5. Salvar respostas (Normal ou Debate)
            if debate_responses:
                # Salvar cada interlocutor do debate
                for node_name, text in debate_responses.items():
                    if text.strip() and node_name in DEBATE_ALMAS:
                        alma = DEBATE_ALMAS[node_name]
                        await _save_message(db, project_id, RoleEnum.ALMA, text, alma_name=alma.name)
                log.info("[PIPELINE:%s] SAVED %d debate turns", req_id, len(debate_responses))
            
            if full_response_text.strip():
                await _save_message(db, project_id, RoleEnum.ALMA, full_response_text, alma_name=last_alma_name)
                log.info("[PIPELINE:%s] SAVED final response", req_id)

        except Exception as e:
            log.error("[PIPELINE:%s] Graph Execution Error: %s", req_id, e, exc_info=True)
            await _safe_send_json(websocket, {"type": "error", "message": f"Erro na orquestração: {str(e)}"})

        # 6. Extração de Canvas em background (opcional, já que ferramentas agora fazem isso)
        # Mantido como segurança para modelos que não usam ferramentas mas descrevem no texto
        async def do_canvas_extraction():
            try:
                async with AsyncSessionLocal() as db2:
                    # Construir um estado fake/leve para extração
                    state2 = await _build_graph_state(project_id, user, db2)
                    
                    # Se for modo DEBATE, pulamos a extração automática (pedido do usuário)
                    if state2.get("intent") == "DEBATE" or state2.get("selected_alma") == "DEBATE":
                        log.info("[PIPELINE:%s] Skipping extraction in DEBATE mode", req_id)
                        return

                    from app.agents.canvas_extractor import extract_canvas_fields
                    extracted = await extract_canvas_fields(state2)
                    if extracted:
                        updated = await _update_canvas(db2, project_id, extracted)
                        await _safe_send_json(websocket, {"type": "canvas_update", "canvas": updated})
            except Exception as exc:
                log.error("[PIPELINE:%s] BACKGROUND EXTRACTION ERROR: %s", req_id, exc)

        asyncio.create_task(do_canvas_extraction())
        await _safe_send_json(websocket, {"type": "done"})
        log.info("[PIPELINE:%s] DONE total=%.2fs", req_id, time.perf_counter() - t_msg)
    
    duration_ms = int((time.perf_counter() - t_msg) * 1000)
    try:
        async with AsyncSessionLocal() as db_metrics:
            from app.models.sql_models import SystemMetric
            metric = SystemMetric(
                endpoint="/api/chat/ws/standard",
                duration_ms=duration_ms,
                status_code=200,
                user_id=user.id
            )
            db_metrics.add(metric)
            await db_metrics.commit()
            if duration_ms > 40000:
                log.warning("[PIPELINE:%s] SLOW LLM DETECTED: took %dms", req_id, duration_ms)
    except Exception as e:
        log.error("Failed to log ws standard metric: %s", e)


    # Finalizado
    pass


# ─── REST: message history ──────────────────────────────────────────────────────

@router.get("/{project_id}/history", response_model=list[ChatMessageOut])
async def get_history(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at)
    )
    return result.scalars().all()
