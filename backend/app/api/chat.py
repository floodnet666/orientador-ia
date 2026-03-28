"""Chat endpoints: WebSocket streaming + message history.

Pipeline tracing is built-in: every step logs its elapsed time.
Debate mode is triggered when a canvas-development phrase is detected.
"""
import asyncio
import json
import logging
import time
from datetime import datetime
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
    canvas_data = canvas_row.canvas_json if canvas_row else {}

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

    return GraphState(
        project_id=str(project_id),
        user_id=str(user.id),
        academic_level=project.academic_level.value,
        chat_history=chat_history,
        current_canvas=CanvasState(**canvas_data) if canvas_data else CanvasState(),
        active_theoretical_alma=theo_name,
        active_methodological_alma=meth_name,
        human_guidelines=project.human_guidelines or "",
        active_soul_ids=[str(sid) for sid in (project.soul_ids or [])],
        empirical_documents=empirical_docs
    )


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

    canvas_data = dict(canvas_row.canvas_json)
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
    
    # Validação do Token ANTES do accept para evitar handshakes fantasmas
    user_id = None
    if not token:
        log.warning("[WS] REJECTED: Missing token | project=%s", project_id)
        return
    
    # Validação JWT
    from jose import jwt, JWTError
    from app.config import settings
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
    except JWTError as exc:
        log.error("[WS] AUTH FAILED: Invalid token | %s", exc)
        return

    # Agora sim, aceitamos a conexão
    await websocket.accept()
    log.info("[WS] ACCEPTED project=%s | origin=%s", project_id, origin)

    try:
        async with AsyncSessionLocal() as db:
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                await websocket.close(code=4001)
                return
            project_result = await db.execute(
                select(Project).where(Project.id == project_id, Project.user_id == user.id)
            )
            if not project_result.scalar_one_or_none():
                log.warning("[WS] PROJECT ACCESS DENIED: %s for user %s", project_id, user.email)
                await websocket.close(code=4003)
                return

        log.info("[WS] AUTH OK user=%s | %.2fs", user.email, time.perf_counter() - t_connect)
        
        # Enviar evento de conexão bem-sucedida para o frontend
        await _safe_send_json(websocket, {"type": "connected", "user": user.email})

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

            is_debate = _detect_debate_trigger(user_content)
            log.info("[PIPELINE:%s] ROUTING | debate=%s", req_id, is_debate)

            if is_debate:
                await _run_debate_pipeline(
                    websocket, project_id, user, user_content, req_id, t_msg
                )
            else:
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
    agent_config_override: dict | None = None,  # F5
):
    async with AsyncSessionLocal() as db:
        # 1. Save user message
        await _save_message(db, project_id, RoleEnum.USER, user_content)

        # 2. Guardrails
        from app.agents.guardrails import check_plagiarism, PLAGIARISM_RESPONSE
        is_violation, confidence = await check_plagiarism(str(user_content))
        log.info("[PIPELINE:%s] 2_GUARDRAILS violation=%s conf=%.2f", req_id, is_violation, confidence)
        if is_violation and confidence > 0.7:
            await _save_message(db, project_id, RoleEnum.SYSTEM, PLAGIARISM_RESPONSE)
            await _safe_send_json(websocket, {"type": "guardrail_block", "text": PLAGIARISM_RESPONSE})
            await _safe_send_json(websocket, {"type": "done"})
            return

        # 3. Build GraphState
        state = await _build_graph_state(project_id, user, db)
        state.chat_history.append(ChatMessageState(
            role="user", content=user_content,
            timestamp=datetime.utcnow().isoformat(),
        ))

        # 4. Orchestrate
        from app.agents.orchestrator import orchestrate
        
        decision = await orchestrate(state, user_content)
        intent = decision.get("intent", "DIALOG")
        state.orchestrator_directive = decision.get("directive", "")
        log.info("[PIPELINE:%s] 4_ORCHESTRATE alma=%s intent=%s", req_id, decision.get("selected_alma"), intent)

        # 5. Select Alma
        from app.agents.almas.base_alma import get_alma_by_name, ALMA_REGISTRY, StatelessAlma
        from app.models.agent_config import AgentConfig

        alma = None
        alma_name = ""

        if agent_config_override:
            try:
                config_obj = AgentConfig(**agent_config_override)
                alma = StatelessAlma(config_obj)
                alma_name = config_obj.name
                log.info("[PIPELINE:%s] Using StatelessAlma override: %s", req_id, alma_name)
            except Exception as e:
                log.error("[PIPELINE:%s] Invalid agent_config_override: %s", req_id, e)

        if not alma:
            alma_name = (
                state.active_methodological_alma
                if decision.get("selected_alma") == "METHODOLOGICAL"
                else state.active_theoretical_alma
            )
            alma = get_alma_by_name(alma_name) or (
                next(iter(ALMA_REGISTRY.values()), None) if ALMA_REGISTRY else None
            )

        # 5.1 Enforce search if intent is SEARCH
        if intent == "SEARCH" and state.orchestrator_directive:
            # We explicitly tell the Alma to use search tools
            state.orchestrator_directive += "\n[URGENTE]: Utilize obrigatoriamente a ferramenta DeepSearch para fundamentar esta resposta."

        # 6. Stream alma response with tool handling
        full_response = ""
        import json as j
        if alma:
            async for chunk in alma.stream_response(state, websocket):
                # Detect Native Tool Calls (NTC) from OllamaClient
                if chunk.startswith('{"tool_calls":'):
                    try:
                        data = j.loads(chunk)
                        tool_calls = data.get("tool_calls", [])
                        log.info("[PIPELINE:%s] NTC RAW: %s", req_id, chunk)
                        for tc in tool_calls:
                            f_name = tc.get("function", {}).get("name")
                            f_args = tc.get("function", {}).get("arguments", {})
                            
                            if f_name == "update_whiteboard":
                                field = f_args.get("field")
                                value = f_args.get("value")
                                if field and value:
                                    log.info("[PIPELINE:%s] NTC execution: update_whiteboard(%s)", req_id, field)
                                    # Update DB immediately
                                    updated = await _update_canvas(db, project_id, {field: value})
                                    # Notify UI
                                    await _safe_send_json(websocket, {
                                        "type": "canvas_update", 
                                        "canvas": updated
                                    })
                            
                            elif f_name == "add_canvas_node":
                                log.info("[PIPELINE:%s] NTC execution: add_canvas_node(%s)", req_id, f_args)
                                # Persist visual data
                                await _update_canvas(db, project_id, {"canvas_node": f_args})
                                await _safe_send_json(websocket, {
                                    "type": "action",
                                    "token": {
                                        "type": "CANVAS_NODE",
                                        "payload": f_args
                                    }
                                })
                                log.info("[PIPELINE:%s] Visual node added", req_id)
                            
                            elif f_name == "add_canvas_edge":
                                log.info("[PIPELINE:%s] NTC execution: add_canvas_edge(%s)", req_id, f_args)
                                # Persist visual data
                                await _update_canvas(db, project_id, {"canvas_edge": f_args})
                                await _safe_send_json(websocket, {
                                    "type": "action",
                                    "token": {
                                        "type": "CANVAS_EDGE",
                                        "payload": f_args
                                    }
                                })
                                log.info("[PIPELINE:%s] Visual edge added", req_id)
                    except Exception as e:
                        log.error("[PIPELINE:%s] NTC Processing Error: %s", req_id, e, exc_info=True)
                    continue

                # Standard text or legacy actions
                full_response += chunk
                await _safe_send_json(websocket, {"type": "chunk", "text": chunk})
        else:
            full_response = "Nenhuma Alma foi selecionada para este projeto ainda."
            await _safe_send_json(websocket, {"type": "chunk", "text": full_response})

        # 7. Save response
        await _save_message(db, project_id, RoleEnum.ALMA, full_response, alma_name=alma_name)

    # 8. Canvas extraction (background - fallback for 7B models)
    async def do_canvas_extraction():
        try:
            async with AsyncSessionLocal() as db2:
                state2 = await _build_graph_state(project_id, user, db2)
                from app.agents.canvas_extractor import extract_canvas_fields
                extracted = await extract_canvas_fields(state2)
                if extracted:
                    updated = await _update_canvas(db2, project_id, extracted)
                    await _safe_send_json(websocket, {"type": "canvas_update", "canvas": updated})
        except Exception as exc:
            log.error("[PIPELINE:%s] CANVAS_EXTRACT ERROR: %s", req_id, exc)

    asyncio.create_task(do_canvas_extraction())
    await _safe_send_json(websocket, {"type": "done"})
    duration_s = time.perf_counter() - t_msg
    log.info("[PIPELINE:%s] DONE total=%.2fs", req_id, duration_s)
    
    duration_ms = int(duration_s * 1000)
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


# ─── Debate pipeline ───────────────────────────────────────────────────────────

async def _run_debate_pipeline(
    websocket: WebSocket,
    project_id: UUID,
    user: User,
    user_content: str,
    req_id: str,
    t_msg: float,
):
    from app.agents.debate.debate_orchestrator import DebateOrchestrator

    # Save user message first
    async with AsyncSessionLocal() as db:
        await _save_message(db, project_id, RoleEnum.USER, user_content)

    debate_text_parts: dict[str, str] = {}  # role -> accumulated text

    try:
        async with AsyncSessionLocal() as db:
            state = await _build_graph_state(project_id, user, db)
            state.chat_history.append(ChatMessageState(
                role="user", content=user_content,
                timestamp=datetime.utcnow().isoformat(),
            ))

            orchestrator = DebateOrchestrator()
            async for event in orchestrator.run(state, user_content, db):
                # Forward all events to frontend
                await websocket.send_text(json.dumps(event))

                # Accumulate text per role for saving to DB
                if event["type"] == "debate_chunk":
                    role = event.get("role", "")
                    alma_name = event.get("alma_name", role)
                    debate_text_parts.setdefault(alma_name, "")
                    debate_text_parts[alma_name] += event.get("content", "")

                # Update canvas in DB if event triggers it
                if event["type"] == "canvas_update":
                    updates = event.get("updates", {})
                    if updates:
                        await _update_canvas(db, project_id, updates)
                        updated_canvas = await db.execute(
                            select(ProjectCanvasState).where(
                                ProjectCanvasState.project_id == project_id
                            )
                        )
                        canvas_row = updated_canvas.scalar_one_or_none()
                        if canvas_row:
                            await websocket.send_text(json.dumps({
                                "type": "canvas_update",
                                "canvas": canvas_row.canvas_json,
                            }))

                if event["type"] == "debate_action":
                    tc = event.get("tool_call", {})
                    f_name = tc.get("function", {}).get("name")
                    f_args = tc.get("function", {}).get("arguments", {})
                    
                    if f_name == "update_whiteboard":
                        field = f_args.get("field")
                        value = f_args.get("value")
                        if field and value:
                            await _update_canvas(db, project_id, {field: value})
                            # Canvas update event is already handled by the DB refresh logic below if we wanted, 
                            # but for debates we usually send a consolidated canvas_update at the end.
                            # However, for real-time feel, we could send it now.
                    
                    elif f_name in ["add_canvas_node", "add_canvas_edge"]:
                        await websocket.send_text(json.dumps({
                            "type": "action",
                            "token": {
                                "type": "CANVAS_NODE" if f_name == "add_canvas_node" else "CANVAS_EDGE",
                                "payload": f_args
                            }
                        }))
                        log.info("[DEBATE:%s] Visual action dispatched: %s", req_id, f_name)

        # Save each Alma's debate turn as a message in DB
        async with AsyncSessionLocal() as db:
            for alma_name, content in debate_text_parts.items():
                if content.strip():
                    await _save_message(
                        db, project_id, RoleEnum.ALMA, content, alma_name=alma_name
                    )

    except Exception as exc:
        log.error("[DEBATE:%s] ERROR: %s", req_id, exc, exc_info=True)
        await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
        await websocket.send_text(json.dumps({"type": "done"}))

    duration_s = time.perf_counter() - t_msg
    log.info("[DEBATE:%s] DONE total=%.2fs", req_id, duration_s)

    duration_ms = int(duration_s * 1000)
    try:
        async with AsyncSessionLocal() as db_metrics:
            from app.models.sql_models import SystemMetric
            metric = SystemMetric(
                endpoint="/api/chat/ws/debate",
                duration_ms=duration_ms,
                status_code=200,
                user_id=user.id
            )
            db_metrics.add(metric)
            await db_metrics.commit()
            if duration_ms > 40000:
                log.warning("[DEBATE:%s] SLOW LLM DETECTED: took %dms", req_id, duration_ms)
    except Exception as e:
        log.error("Failed to log ws debate metric: %s", e)


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
