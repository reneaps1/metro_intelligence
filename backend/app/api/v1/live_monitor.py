"""LM.1/LM.3 (docs/tasks/LM1-live-monitor-mvp.md, docs/tasks/
LM3-live-monitor-presenter-controls.md): WebSocket endpoint streaming the
deterministic replay (`app.services.live_replay_service`) of already-seeded
measurement history for one or more characteristics, plus (LM.3) presenter
control over an in-flight session and a REST lookup for scenario-matched
candidate characteristics.

Path deviation from docs/design/live-monitor-panel.md: that brainstorm doc
sketches the path as top-level `/ws/live-monitor`. This task's own "Archivos
esperados" section says to register this router in
`app.api.v1.router.api_router` (the shared `/api/v1` mount point) alongside
every other endpoint, which this module follows -- so the actual path is
`/api/v1/ws/live-monitor`. Flagged explicitly here (same convention as
`app.api.v1.measurements`'s RBAC deviation note) rather than silently picking
one interpretation.

Auth: a WebSocket handshake from a browser can't easily carry a custom
`Authorization` header, so the already-issued access token is passed as a
query param (`?token=...`) and validated with the same `decode_token` +
revocation-check logic `get_current_user` uses for REST calls -- it just
can't be expressed as the same `Depends(oauth2_scheme)` chain since there's
no header to read it from. Authorization reuses the same RBAC tables via the
`live_monitor.stream` permission token (migration 0006) for watching, and the
separate `live_monitor.update` token (migration 0007, LM.3) for presenter
control -- no exception for WebSockets (CLAUDE.md §5).

LM.3 control protocol: pause/resume/set_speed are sent as JSON control
messages *on the same open WebSocket* (client -> server), mutating a shared
`PlaybackControl` (`live_replay_service.py`) that every characteristic's
replay task already reads from -- chosen over a separate REST endpoint
because the session only exists as this one open connection; there's no
session id to look a REST call up by. `set_scenario`, by contrast, is *not*
a WS control message: changing scenario means watching a different set of
characteristics, and LM.1's frontend hook already reconnects cleanly
whenever its requested characteristic_ids change -- so the frontend just
fetches new candidate ids from `GET /characteristics/scenario-candidates`
and opens a new connection with them. Reusing the existing reconnect path
for that satisfies "no mixing points from two scenarios" for free, without
inventing a second, redundant restart mechanism.

Connection/session manager: in-memory, single process -- one `asyncio.Task`
(and its own DB session) per requested characteristic, fanned into one queue
per client connection. This is demo-grade in the exact same sense as
`app.core.security`'s revocation store: it does not survive a restart and
does not fan out across multiple worker processes. A production deployment
would need a shared pub/sub (e.g. Redis) instead of the in-process queue.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import asdict
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import decode_token, is_token_revoked, require_permission
from app.models.security import Permission, RolePermission, User, UserRole
from app.schemas.live_monitor import ScenarioCandidatesResponse
from app.services.live_replay_service import (
    DEFAULT_SECONDS_PER_REPLAY_DAY,
    PlaybackControl,
    PointEvent,
    ReplayEvent,
    ReplayNotAvailable,
    stream_replay,
)
from app.services.scenario_classifier import SCENARIO_NAMES, load_candidate_profiles, rank_by_scenario

router = APIRouter(tags=["live-monitor"])

STREAM_PERMISSION_TOKEN = "live_monitor.stream"
CONTROL_PERMISSION_TOKEN = "live_monitor.update"

MIN_SPEED_MULTIPLIER = 0.01
MAX_SPEED_MULTIPLIER = 100.0


def _authenticate(token: str, db: Session) -> User | None:
    """Mirrors `app.core.security.get_current_user`'s checks, adapted for a
    query-param token instead of a bearer header -- same failure modes
    (invalid/expired token, revoked jti, unknown/inactive user) all collapse
    to "reject the connection", since a WebSocket has no per-check status
    code to distinguish 401 from 403 before the handshake completes."""
    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        return None

    jti = payload.get("jti")
    if not jti or is_token_revoked(jti):
        return None

    subject = payload.get("sub")
    if not subject:
        return None

    try:
        user = db.get(User, uuid.UUID(subject))
    except (ValueError, TypeError):
        return None

    if user is None or not user.is_active:
        return None
    return user


def _user_has_permission(db: Session, user: User, token: str) -> bool:
    stmt = (
        select(Permission.token)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user.id, Permission.token == token)
    )
    return db.execute(stmt).first() is not None


def _parse_characteristic_ids(raw: str) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.append(uuid.UUID(chunk))
        except ValueError:
            continue
    return ids


def _serialize_event(event: ReplayEvent) -> dict[str, Any]:
    """Decimal/UUID/datetime fields must be stringified -- the stdlib `json`
    encoder `websocket.send_json` uses underneath has no default codec for
    any of them."""
    payload = asdict(event)
    payload["characteristic_id"] = str(payload["characteristic_id"])
    if isinstance(event, PointEvent):
        payload["type"] = "point"
        payload["value"] = str(payload["value"])
        payload["deviation"] = str(payload["deviation"])
        payload["measured_at"] = payload["measured_at"].isoformat()
    else:
        payload["type"] = "control_limits_updated"
        payload["cpk"] = str(payload["cpk"]) if payload["cpk"] is not None else None
        payload["center_line"] = str(payload["center_line"])
        payload["ucl"] = str(payload["ucl"])
        payload["lcl"] = str(payload["lcl"])
    return payload


async def _control_listener(websocket: WebSocket, control: PlaybackControl, can_control: bool) -> None:
    """LM.3: listens for `{"type": "control", "action": ...}` messages on the
    same connection and mutates the shared `PlaybackControl` in place. A
    connected client without `live_monitor.update` can still watch (the
    stream itself doesn't depend on this task) -- its control messages are
    just silently ignored, fail-closed rather than erroring the connection."""
    try:
        while True:
            raw = await websocket.receive_text()
            if not can_control:
                continue
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(message, dict) or message.get("type") != "control":
                continue

            action = message.get("action")
            if action == "pause":
                control.running.clear()
            elif action == "resume":
                control.running.set()
            elif action == "set_speed":
                multiplier = message.get("speed_multiplier")
                if (
                    isinstance(multiplier, int | float)
                    and not isinstance(multiplier, bool)
                    and MIN_SPEED_MULTIPLIER <= multiplier <= MAX_SPEED_MULTIPLIER
                ):
                    control.speed_multiplier = float(multiplier)
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/live-monitor")
async def live_monitor_stream(
    websocket: WebSocket,
    token: str = Query(...),
    characteristic_ids: str = Query(...),
    seconds_per_replay_day: float = Query(default=DEFAULT_SECONDS_PER_REPLAY_DAY, ge=0),
    speed_multiplier: float = Query(default=1.0, gt=0),
    db: Session = Depends(get_db),
) -> None:
    user = _authenticate(token, db)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if not _user_has_permission(db, user, STREAM_PERMISSION_TOKEN):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    can_control = _user_has_permission(db, user, CONTROL_PERMISSION_TOKEN)

    ids = _parse_characteristic_ids(characteristic_ids)
    if not ids:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    control = PlaybackControl(
        seconds_per_replay_day=seconds_per_replay_day, speed_multiplier=speed_multiplier
    )
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def _run_one(characteristic_id: uuid.UUID) -> None:
        session = SessionLocal()
        try:
            async for event in stream_replay(session, characteristic_id, control=control):
                await queue.put(_serialize_event(event))
        except ReplayNotAvailable:
            # One bad/empty id in a multi-characteristic request shouldn't
            # kill the streams for the rest of the requested set.
            pass
        finally:
            session.close()

    tasks = [asyncio.create_task(_run_one(characteristic_id)) for characteristic_id in ids]

    async def _signal_completion() -> None:
        await asyncio.gather(*tasks)
        await queue.put(None)

    completion_watcher = asyncio.create_task(_signal_completion())
    control_listener = asyncio.create_task(_control_listener(websocket, control, can_control))

    try:
        while True:
            message = await queue.get()
            if message is None:
                # Every requested characteristic's replay is exhausted --
                # explicitly close rather than just returning: relying on an
                # ASGI transport to infer a close from the handler returning
                # is not reliable (observed hanging under Starlette's
                # TestClient, which needs an explicit "websocket.close").
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                break
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    finally:
        completion_watcher.cancel()
        control_listener.cancel()
        for task in tasks:
            task.cancel()


@router.get("/characteristics/scenario-candidates", response_model=ScenarioCandidatesResponse)
def get_scenario_candidates(
    scenario: str = Query(...),
    limit: int = Query(default=8, ge=1, le=50),
    db: Session = Depends(get_db),
    # Gated behind the same `live_monitor.update` (control) permission as the
    # WS control messages, not the broader `live_monitor.stream` (read) one --
    # picking which scenario to demo is part of steering the session, not
    # just watching it.
    _user: User = Depends(require_permission("live_monitor", "update")),
) -> ScenarioCandidatesResponse:
    if scenario not in SCENARIO_NAMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown scenario '{scenario}'. Valid values: {', '.join(SCENARIO_NAMES)}.",
        )
    profiles = load_candidate_profiles(db)
    characteristic_ids = rank_by_scenario(profiles, scenario, limit)
    return ScenarioCandidatesResponse(
        scenario=scenario,
        candidate_pool_size=len(profiles),
        characteristic_ids=characteristic_ids,
    )
