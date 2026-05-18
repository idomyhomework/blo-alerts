import logging

from backend.app.routers import notices
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(levelname)s  %(name)s  %(message)s",
)

app = FastAPI(
    title="Sistema de Avisos Municipales (Blo Alerts)",
    version="0.1.0",
)

# CORS: permite que el panel web y la app móvil llamen a la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(notices.router)


@app.get("/healthz")
async def health():
    return {"status": "ok"}
