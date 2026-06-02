import asyncio
from collections import defaultdict

from fastapi import WebSocket


class WSManager:
    def __init__(self) -> None:
        self._conns: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, tenant_id: int, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._conns[tenant_id].add(ws)

    async def disconnect(self, tenant_id: int, ws: WebSocket) -> None:
        async with self._lock:
            self._conns[tenant_id].discard(ws)

    async def broadcast(self, tenant_id: int, message: dict) -> None:
        dead: list[WebSocket] = []
        async with self._lock:
            conns = list(self._conns.get(tenant_id, ()))
        for c in conns:
            try:
                await c.send_json(message)
            except Exception:
                dead.append(c)
        if dead:
            async with self._lock:
                for d in dead:
                    self._conns[tenant_id].discard(d)


manager = WSManager()


async def broadcast_stock_update(tenant_id: int, product_id: int, new_stock: int) -> None:
    await manager.broadcast(tenant_id, {
        "type": "stock_update",
        "product_id": product_id,
        "new_stock": new_stock,
    })
