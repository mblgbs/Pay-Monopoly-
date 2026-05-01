from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .routers.auth import router as auth_router
from .routers.wallet import router as wallet_router
from .routers.webhooks import router as webhook_router
from .schemas import MessageResponse

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(wallet_router)
app.include_router(webhook_router)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/", response_model=MessageResponse)
def root() -> MessageResponse:
    return MessageResponse(message="Pay Wallet API is running")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "pay-wallet"}

