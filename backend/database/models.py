"""
database/models.py – SQLAlchemy ORM models for the Alaska backend.

Three tables:
  • conversations  – one row per session_id (metadata)
  • messages       – every chat turn (user or assistant) per session
  • search_history – every RAG query with the chunks that were retrieved
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database.db import Base


def _now() -> datetime:
    """UTC-aware current timestamp."""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ── Conversations ──────────────────────────────────────────────────────────
class Conversation(Base):
    """
    One row per chat session.  The session_id is the public identifier
    that the frontend stores and passes back on every request.
    """

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True, default=_new_uuid)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at", cascade="all, delete-orphan")
    searches = relationship("SearchHistory", back_populates="conversation", order_by="SearchHistory.created_at", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Conversation session_id={self.session_id}>"


# ── Messages ───────────────────────────────────────────────────────────────
class Message(Base):
    """
    A single turn in the conversation.

    role    – 'user' | 'assistant' | 'system'
    content – the text body of the message

    For media uploads (image / audio / video) the content field stores
    the Gemini File API URI so the next /chat call can attach it to the
    multimodal prompt.
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("conversations.session_id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)        # 'user' | 'assistant'
    content = Column(Text, nullable=False)
    media_uri = Column(Text, nullable=True)          # Gemini File API URI (media uploads)
    media_mime = Column(String(100), nullable=True)  # e.g. 'image/png'
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message session={self.session_id} role={self.role}>"


# ── Search / RAG History ───────────────────────────────────────────────────
class SearchHistory(Base):
    """
    Persists every RAG query along with the chunk IDs that ChromaDB
    returned.  This gives you a full audit trail of what context the
    model actually saw when it generated a response.
    """

    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("conversations.session_id", ondelete="CASCADE"), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    retrieved_ids = Column(Text, nullable=True)       # JSON-serialised list of ChromaDB doc IDs
    retrieved_sources = Column(Text, nullable=True)   # JSON-serialised list of source metadata
    num_results = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    conversation = relationship("Conversation", back_populates="searches")

    def __repr__(self) -> str:
        return f"<SearchHistory session={self.session_id} query={self.query_text[:40]}>"
