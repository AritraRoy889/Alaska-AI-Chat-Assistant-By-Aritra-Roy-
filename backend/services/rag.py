"""
services/rag.py – The core RAG pipeline, hand-rolled without any orchestrator.

This is the brain of the backend.  It does everything LangChain would do,
but written explicitly so every step is visible and tunable:

  1. retrieve_context()
       • Embeds the user query with RETRIEVAL_QUERY task type.
       • Queries ChromaDB for the k most similar chunks.
       • Returns the raw chunk texts and their metadata.

  2. build_prompt()
       • Constructs a single string from:
           – A system preamble that defines the assistant's behaviour.
           – Retrieved context chunks (if any).
           – Recent conversation history (last N turns).
           – The current user message.
       • No template engine is used – just f-strings.

  3. run_rag_pipeline()
       • Orchestrates the full request: retrieve → build prompt → generate.
       • Saves the user message, assistant reply, and search-history row
         to SQLite via the supplied DB session.
       • Returns the assistant's text response.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from database.models import Conversation, Message, SearchHistory
from services.gemini import generate_response
from vector_store.chroma import similarity_search

logger = logging.getLogger(__name__)

# How many recent conversation turns to include in the prompt
# (kept small to stay within free-tier per-minute token quota)
HISTORY_WINDOW = 6

# How many ChromaDB chunks to retrieve
TOP_K = 3

# ── System prompt ──────────────────────────────────────────────────────────
SYSTEM_PREAMBLE = """You are Alaska, a friendly, knowledgeable, and thoughtful AI assistant.
Your goal is to give accurate, helpful, and concise answers.

When answering:
- Use the provided context to ground your answer whenever it is relevant.
- If the context does not cover the question, say so honestly and answer from your own knowledge.
- Maintain a warm, conversational tone.
- Avoid repeating yourself or padding your response with filler phrases.
- If the user attaches an image, audio, or video, analyse it carefully before responding.
"""


# ── Step 1: Retrieval ──────────────────────────────────────────────────────

def retrieve_context(session_id: str, query: str) -> dict[str, Any]:
    """
    Query ChromaDB and return a structured result.

    Returns
    -------
    {
        "chunks":    ["chunk text", ...],
        "metadatas": [{...}, ...],
        "ids":       ["id1", ...],
        "distances": [0.12, ...],
    }
    """
    raw = similarity_search(session_id, query, n_results=TOP_K)

    # ChromaDB returns nested lists (one list per query), so flatten them
    chunks    = raw["documents"][0]    if raw["documents"]    else []
    metadatas = raw["metadatas"][0]    if raw["metadatas"]    else []
    ids       = raw["ids"][0]          if raw["ids"]          else []
    distances = raw["distances"][0]    if raw["distances"]    else []

    return {
        "chunks":    chunks,
        "metadatas": metadatas,
        "ids":       ids,
        "distances": distances,
    }


# ── Step 2: Prompt construction ────────────────────────────────────────────

def build_prompt(
    query: str,
    context_chunks: list[str],
    history: list[Message],
) -> str:
    """
    Assemble the full text prompt that will be sent to Gemini.

    Layout
    ------
    [SYSTEM]
    [CONTEXT – retrieved chunks, if any]
    [CONVERSATION HISTORY – last N turns]
    [CURRENT USER MESSAGE]
    """
    parts: list[str] = []

    # System preamble
    parts.append(SYSTEM_PREAMBLE.strip())

    # Retrieved context
    if context_chunks:
        parts.append("\n\n--- Relevant Context ---")
        for idx, chunk in enumerate(context_chunks, start=1):
            parts.append(f"\n[{idx}] {chunk.strip()}")
        parts.append("\n--- End of Context ---")
    else:
        parts.append("\n\n[No relevant context was found in the uploaded documents.]")

    # Conversation history
    if history:
        parts.append("\n\n--- Conversation History ---")
        for msg in history:
            speaker = "User" if msg.role == "user" else "Alaska"
            parts.append(f"\n{speaker}: {msg.content}")
        parts.append("\n--- End of History ---")

    # Current turn
    parts.append(f"\n\nUser: {query}\nAlaska:")

    return "".join(parts)


# ── Step 3: Full pipeline ──────────────────────────────────────────────────

def run_rag_pipeline(
    session_id: str,
    user_query: str,
    db: Session,
) -> str:
    """
    Execute the complete RAG pipeline for one user turn.

    Steps
    -----
    1. Ensure the session exists in SQLite.
    2. Retrieve similar chunks from ChromaDB.
    3. Load recent conversation history from SQLite.
    4. Build the full prompt.
    5. Check for any media URIs from the most recent user message.
    6. Call the Gemini API.
    7. Persist the new user message, AI response, and search-history row.
    8. Return the assistant text.
    """

    # 1. Get or create the conversation row
    conversation = db.query(Conversation).filter_by(session_id=session_id).first()
    if conversation is None:
        conversation = Conversation(session_id=session_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 2. Retrieve context from ChromaDB
    ctx = retrieve_context(session_id, user_query)
    context_chunks = ctx["chunks"]
    retrieved_ids   = ctx["ids"]
    retrieved_metas = ctx["metadatas"]

    # 3. Load conversation history (most recent HISTORY_WINDOW turns)
    history: list[Message] = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_WINDOW)
        .all()[::-1]   # reverse to chronological order
    )

    # 4. Build the prompt string
    prompt = build_prompt(user_query, context_chunks, history)

    # 5. Collect any Gemini File API URIs stored in recent messages
    file_uris: list[dict[str, str]] = []
    for msg in history:
        if msg.media_uri and msg.media_mime:
            file_uris.append({"uri": msg.media_uri, "mime_type": msg.media_mime})

    # 6. Generate the response
    assistant_text = generate_response(prompt, file_uris=file_uris or None)

    # 7a. Persist the user message
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=user_query,
    )
    db.add(user_msg)

    # 7b. Persist the assistant response
    assistant_msg = Message(
        session_id=session_id,
        role="assistant",
        content=assistant_text,
    )
    db.add(assistant_msg)

    # 7c. Persist search history
    search_row = SearchHistory(
        session_id=session_id,
        query_text=user_query,
        retrieved_ids=json.dumps(retrieved_ids),
        retrieved_sources=json.dumps(
            [m.get("source", "") for m in retrieved_metas]
        ),
        num_results=len(retrieved_ids),
    )
    db.add(search_row)

    # 7d. Update conversation timestamp
    conversation.updated_at = datetime.now(timezone.utc)

    db.commit()

    logger.info(
        "RAG pipeline complete for session=%s | context_chunks=%d | response_len=%d",
        session_id,
        len(context_chunks),
        len(assistant_text),
    )

    return assistant_text
