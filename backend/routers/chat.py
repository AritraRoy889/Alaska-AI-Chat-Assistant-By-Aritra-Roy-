"""
routers/chat.py – POST /chat

Accepts a session_id and a user_query, runs the full RAG pipeline,
and returns the assistant's response.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Conversation
from services.rag import run_rag_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Request / response schemas ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="UUID of the active conversation session.")
    user_query: str = Field(..., min_length=1, description="The user's message / question.")


class ChatResponse(BaseModel):
    session_id: str
    user_query: str
    response: str


# ── Route ──────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ChatResponse,
    summary="Send a message and get an AI response via RAG",
)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """
    The main chat endpoint.

    1. Validates that the session exists (or auto-creates it through the
       RAG pipeline).
    2. Runs the full RAG pipeline:
         retrieve context → build prompt → call Gemini → save history.
    3. Returns the assistant's text response.
    """
    if not payload.session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id must not be empty.",
        )

    try:
        assistant_text = run_rag_pipeline(
            session_id=payload.session_id,
            user_query=payload.user_query,
            db=db,
        )
    except Exception as exc:
        logger.exception("RAG pipeline error for session=%s", payload.session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Something went wrong while generating the response: {exc}",
        ) from exc

    return ChatResponse(
        session_id=payload.session_id,
        user_query=payload.user_query,
        response=assistant_text,
    )
