import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.routers import (
    ai_chat,
    auth,
    automation,
    invoices,
    products,
    purchase_orders,
    suppliers,
    ws,
)
from app.services.scheduler import build_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    sched = build_scheduler()
    sched.start()
    app.state.scheduler = sched
    logging.getLogger("smartstore").info("scheduler started")
    try:
        yield
    finally:
        sched.shutdown(wait=False)


app = FastAPI(title="SmartStore AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(suppliers.router)
app.include_router(purchase_orders.router)
app.include_router(ai_chat.router)
app.include_router(invoices.router)
app.include_router(automation.router)
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
