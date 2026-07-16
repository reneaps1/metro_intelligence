"""LM.1 (docs/tasks/LM1-live-monitor-mvp.md): WebSocket endpoint streaming the
deterministic replay (`app.services.live_replay_service`) of already-seeded
measurement history for one or more characteristics, for the Live Monitor
demo panel.

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
new `live_monitor.stream` permission token (migration 0006) -- no exception
for WebSockets (CLAUDE.md §5).

Connection/session manager: in-memory, single process -- one `asyncio.Task`
(and its own DB session) per requested characteristic, fanned into one queue
per client connection. This is demo-grade in the exact same sense as
`app.core.security`'s revocation store: it does not survive a restart and
does not fan out across multiple worker processes. A production deployment
would need a shared pub/sub (e.g. Redis) instead of the in-process queue.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict
from typing import Any

import jwt
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import decode_token, is_token_revoked
from app.models.security import Permission, RolePermission, User, UserRole
from app.services.live_replay_service import (
    DEFAULT_SECONDS_PER_REPLAY_DAY,
    PointEvent,
    ReplayEvent,
    ReplayNotAvailable,
    stream_replay,
)

router = APIRouter(tags=["live-monitor"])

PERMISSION_TOKEN = "live_monitor.stream"


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


def _user_has_stream_permission(db: Session, user: User) -> bool:
    stmt = (
        select(Permission.token)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user.id, Permission.token == PERMISSION_TOKEN)
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
    if not _user_has_stream_permission(db, user):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    ids = _parse_characteristic_ids(characteristic_ids)
    if not ids:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def _run_one(characteristic_id: uuid.UUID) -> None:
        session = SessionLocal()
        try:
            async for event in stream_replay(
                session,
                characteristic_id,
                seconds_per_replay_day=seconds_per_replay_day,
                speed_multiplier=speed_multiplier,
            ):
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
        for task in tasks:
            task.cancel()
