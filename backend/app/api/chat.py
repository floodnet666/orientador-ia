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


# ─── Debate trigger detection ──────────────────────────────────────────────────

_DEBATE_TRIGGERS = [
    "desenvolver a justificativa",
    "desenvolver o problema",
    "formular os objectivos",
    "formular os objetivos",
    "definir a metodologia",
    "me ajude a desenvolver",
    "como posso fundamentar",
    "debatam sobre",
    "discutam sobre",
    "analisem o",
    "o que pensam sobre",
    "qual a perspectiva de",
    "ajude com a justificativa",
    "ajude com o problema",
    "ajude com os objectivos",
    "ajude com os objetivos",
    "ajude com a metodologia",
]


def _detect_debate_trigger(message: str) -> bool:
    msg = message.lower()
    return any(t in msg for t in _DEBATE_TRIGGERS)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _elapsed(t0: float) -> str:
    return f"{time.perf_counter() - t0:.2f}s"


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

    return GraphState(
        project_id=str(project_id),
        user_id=str(user.id),
        academic_level=project.academic_level.value,
        chat_history=chat_history,
        current_canvas=CanvasState(**canvas_data) if canvas_data else CanvasState(),
        active_theoretical_alma=theo_name,
        active_methodological_alma=meth_name,
        human_guidelines=project.human_guidelines or "",
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
    result = await db.execute(
        select(ProjectCanvasState).where(ProjectCanvasState.project_id == project_id)
    )
    canvas_row = result.scalar_one_or_none()
    if not canvas_row:
        return {}

    canvas_data = dict(canvas_row.canvas_json)
    for key, value in fields.items():
        if value is None:
            continue
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

    canvas_row.canvas_json = canvas_data
    await db.commit()
    return canvas_data


# ─── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/{project_id}/ws")
async def chat_websocket(websocket: WebSocket, project_id: UUID):
    t_connect = time.perf_counter()
    await websocket.accept()
    log.info("[WS] CONNECTED project=%s", project_id)

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return

    from jose import jwt, JWTError
    from app.config import settings

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
    except JWTError as exc:
        log.warning("[WS] INVALID TOKEN | %s", exc)
        await websocket.close(code=4001)
        return

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
                await websocket.close(code=4003)
                return

        log.info("[WS] AUTH OK user=%s | %.2fs", user.email, time.perf_counter() - t_connect)

        while True:
            data = await websocket.receive_text()
            t_msg = time.perf_counter()
            msg_data = json.loads(data)
            if msg_data.get("type") != "message":
                continue

            user_content = msg_data.get("content", "").strip()
            if not user_content:
                continue

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
                    websocket, project_id, user, user_content, req_id, t_msg
                )

    except WebSocketDisconnect:
        log.info("[WS] DISCONNECTED project=%s | %.1fs", project_id, time.perf_counter() - t_connect)
    except Exception as exc:
        log.error("[WS] UNHANDLED project=%s | %s", project_id, exc, exc_info=True)
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
        except Exception:
            pass


# ─── Standard pipeline ─────────────────────────────────────────────────────────

async def _run_standard_pipeline(
    websocket: WebSocket,
    project_id: UUID,
    user: User,
    user_content: str,
    req_id: str,
    t_msg: float,
):
    async with AsyncSessionLocal() as db:
        # 1. Save user message
        await _save_message(db, project_id, RoleEnum.USER, user_content)

        # 2. Guardrails
        from app.agents.guardrails import check_plagiarism, PLAGIARISM_RESPONSE
        is_violation, confidence = await check_plagiarism(user_content)
        log.info("[PIPELINE:%s] 2_GUARDRAILS violation=%s conf=%.2f", req_id, is_violation, confidence)
        if is_violation and confidence > 0.7:
            await _save_message(db, project_id, RoleEnum.SYSTEM, PLAGIARISM_RESPONSE)
            await websocket.send_text(json.dumps({"type": "guardrail_block", "text": PLAGIARISM_RESPONSE}))
            await websocket.send_text(json.dumps({"type": "done"}))
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
        state.orchestrator_directive = decision.get("directive", "")
        log.info("[PIPELINE:%s] 4_ORCHESTRATE alma=%s", req_id, decision.get("selected_alma"))

        # 5. Select Alma
        from app.agents.almas.base_alma import get_alma_by_name, ALMA_REGISTRY
        alma_name = (
            state.active_methodological_alma
            if decision.get("selected_alma") == "METHODOLOGICAL"
            else state.active_theoretical_alma
        )
        alma = get_alma_by_name(alma_name) or (
            next(iter(ALMA_REGISTRY.values()), None) if ALMA_REGISTRY else None
        )

        # 6. Stream alma response with tool handling
        full_response = ""
        if alma:
            async for chunk in alma.stream_response(state, websocket):
                full_response += chunk
                await websocket.send_text(json.dumps({"type": "chunk", "text": chunk}))
        else:
            full_response = "Nenhuma Alma foi selecionada para este projeto ainda."
            await websocket.send_text(json.dumps({"type": "chunk", "text": full_response}))

        # 7. Save response
        await _save_message(db, project_id, RoleEnum.ALMA, full_response, alma_name=alma_name)

    # 8. Canvas extraction (background)
    async def do_canvas_extraction():
        try:
            async with AsyncSessionLocal() as db2:
                state2 = await _build_graph_state(project_id, user, db2)
                from app.agents.canvas_extractor import extract_canvas_fields
                extracted = await extract_canvas_fields(state2)
                if extracted:
                    updated = await _update_canvas(db2, project_id, extracted)
                    await websocket.send_text(json.dumps({"type": "canvas_update", "canvas": updated}))
        except Exception as exc:
            log.error("[PIPELINE:%s] CANVAS_EXTRACT ERROR: %s", req_id, exc)

    asyncio.create_task(do_canvas_extraction())
    await websocket.send_text(json.dumps({"type": "done"}))
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
