from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.security import decode_token
from app.database import AsyncSessionLocal
from app.models.user import User
from app.ws.manager import manager

router = APIRouter(tags=["ws"])


async def _resolve_tenant_id(token: str | None) -> int | None:
    if token:
        try:
            payload = decode_token(token)
            if payload.get("type") == "access":
                return int(payload["tid"])
        except ValueError:
            pass
    # Auth is disabled — fall back to the first seeded admin's tenant.
    async with AsyncSessionLocal() as db:
        u = (await db.execute(
            select(User).where(User.role == "admin", User.is_active.is_(True)).order_by(User.id).limit(1)
        )).scalar_one_or_none()
        return u.tenant_id if u else None


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str | None = Query(default=None)):
    tenant_id = await _resolve_tenant_id(token)
    if tenant_id is None:
        await websocket.close(code=4401)
        return
    await manager.connect(tenant_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(tenant_id, websocket)
