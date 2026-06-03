from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.ws.manager import manager

router = APIRouter(tags=["ws"])


def _resolve_tenant_id(token: str | None) -> int | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    if payload.get("type") != "access":
        return None
    return int(payload["tid"])


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str | None = Query(default=None)):
    tenant_id = _resolve_tenant_id(token)
    if tenant_id is None:
        await websocket.close(code=4401)
        return
    await manager.connect(tenant_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(tenant_id, websocket)
