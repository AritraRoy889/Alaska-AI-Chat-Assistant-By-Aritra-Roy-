"""
main.py – FastAPI application entry point for the Alaska backend.

Responsibilities:
  • Create and configure the FastAPI app (title, version, CORS).
  • Create all SQLAlchemy tables on startup (idempotent).
  • Register all routers.
  • Expose a lightweight health-check endpoint.

Run locally:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database.db import engine
from database.models import Base  # noqa: F401  – triggers model registration
from routers import chat, conversation, search, upload

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Database initialisation ────────────────────────────────────────────────
# Creates all tables that do not yet exist.  Safe to call on every startup.
Base.metadata.create_all(bind=engine)
logger.info("SQLite tables created / verified.")

# ── FastAPI app ────────────────────────────────────────────────────────────
app = FastAPI(
    title="Alaska AI Assistant – Backend API",
    description=(
        "A Retrieval-Augmented Generation (RAG) backend built with FastAPI, "
        "ChromaDB, and the Google Gemini API.  No LangChain or LlamaIndex – "
        "every step of the RAG pipeline is written from scratch."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(conversation.router)
app.include_router(search.router)
app.include_router(upload.router)


# ── Health check ───────────────────────────────────────────────────────────
@app.get("/", tags=["Health"], summary="Health check")
def root() -> dict[str, str]:
    """
    Returns a simple OK response so load-balancers and monitoring tools
    can verify the service is alive.
    """
    return {"status": "ok", "service": "Alaska Backend", "version": "1.0.0"}


@app.get("/health", tags=["Health"], summary="Detailed health check")
def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "database": "sqlite",
        "vector_store": "chromadb",
        "llm": settings.gemini_chat_model,
        "embedding_model": settings.gemini_embedding_model,
    }
