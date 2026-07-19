"""
routers/conversation.py

POST   /conversation/new                 – create a fresh session
GET    /conversation/list                – list all conversations with titles
GET    /conversation/{session_id}/history – retrieve full chat history
DELETE /conversation/{session_id}        – delete a conversation permanently
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Conversation, Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversation", tags=["Conversation"])


# ── Schemas ────────────────────────────────────────────────────────────────

class NewConversationResponse(BaseModel):
    session_id: str
    created_at: datetime


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    media_uri: str | None
    media_mime: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationHistoryResponse(BaseModel):
    session_id: str
    total_messages: int
    messages: list[MessageOut]


class ConversationSummary(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    total: int
    conversations: list[ConversationSummary]


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post(
    "/new",
    response_model=NewConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new conversation and get a fresh session_id",
)
def new_conversation(db: Session = Depends(get_db)) -> NewConversationResponse:
    """
    Generate a new UUID-based session_id, persist it to the conversations
    table, and return it to the frontend.
    """
    session_id = str(uuid.uuid4())
    conversation = Conversation(session_id=session_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    logger.info("New conversation created: session_id=%s", session_id)

    return NewConversationResponse(
        session_id=conversation.session_id,
        created_at=conversation.created_at,
    )


@router.get(
    "/list",
    response_model=ConversationListResponse,
    summary="List all past conversations with their first message as title",
)
def list_conversations(db: Session = Depends(get_db)) -> ConversationListResponse:
    """
    Returns all conversations ordered by most recently updated.
    Uses the first user message as the conversation title.
    """
    conversations = (
        db.query(Conversation)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    summaries: list[ConversationSummary] = []
    for conv in conversations:
        first_msg = (
            db.query(Message)
            .filter(
                Message.session_id == conv.session_id,
                Message.role == "user",
            )
            .order_by(Message.created_at.asc())
            .first()
        )

        if first_msg:
            raw = first_msg.content.strip()
            if raw.startswith("[Uploaded"):
                raw = "File upload session"
            title = raw[:60] + ("…" if len(raw) > 60 else "")
        else:
            title = "New conversation"

        msg_count = (
            db.query(Message)
            .filter(Message.session_id == conv.session_id)
            .count()
        )

        summaries.append(
            ConversationSummary(
                session_id=conv.session_id,
                title=title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=msg_count,
            )
        )

    return ConversationListResponse(
        total=len(summaries),
        conversations=summaries,
    )


@router.get(
    "/{session_id}/history",
    response_model=ConversationHistoryResponse,
    summary="Get the full chat history for a session",
)
def get_history(session_id: str, db: Session = Depends(get_db)) -> ConversationHistoryResponse:
    """
    Retrieve every message in chronological order for the given session_id.
    Returns a 404 if the session does not exist.
    """
    conversation = db.query(Conversation).filter_by(session_id=session_id).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No conversation found with session_id '{session_id}'.",
        )

    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return ConversationHistoryResponse(
        session_id=session_id,
        total_messages=len(messages),
        messages=messages,
    )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a conversation and all its messages",
)
def delete_conversation(session_id: str, db: Session = Depends(get_db)) -> None:
    """
    Delete a conversation row along with all its messages and search-history
    entries (CASCADE handles child rows automatically).
    Returns 204 No Content on success, 404 if not found.
    """
    conversation = db.query(Conversation).filter_by(session_id=session_id).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No conversation found with session_id '{session_id}'.",
        )

    db.delete(conversation)
    db.commit()
    logger.info("Conversation deleted: session_id=%s", session_id)
