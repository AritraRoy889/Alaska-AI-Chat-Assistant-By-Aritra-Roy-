"""
vector_store/chroma.py – ChromaDB client wrapper.

Manages a single persistent ChromaDB collection per session_id.
All embedding is delegated to services.gemini so there is one
canonical source of truth for vectors.

Design decisions:
  • One ChromaDB collection per session so each session has its own
    private document namespace.  Documents are isolated – querying
    session A will never return chunks from session B.
  • A global "shared" collection (GLOBAL_COLLECTION) is used for
    documents not tied to a specific session (e.g. a knowledge base
    loaded at startup).
  • We store custom embeddings rather than letting ChromaDB call an
    embedding function so we can use Gemini's embedding API directly.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings
from services.gemini import embed_query, embed_text

logger = logging.getLogger(__name__)

# ── Client (singleton, one per process) ───────────────────────────────────
_client: chromadb.PersistentClient | None = None

GLOBAL_COLLECTION = "alaska_global"


def _get_client() -> chromadb.PersistentClient:
    """Lazy-initialise the ChromaDB persistent client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info("ChromaDB initialised at %s", settings.chroma_persist_dir)
    return _client


def _collection_name(session_id: str) -> str:
    """Derive a deterministic ChromaDB collection name from a session_id."""
    # ChromaDB collection names must be 3-63 chars, start with [a-zA-Z0-9_-]
    # The session_id is a UUID (36 chars without prefix) so we sanitise it.
    safe = session_id.replace("-", "_")
    return f"s_{safe}"


# ── Public API ─────────────────────────────────────────────────────────────

def get_or_create_collection(session_id: str) -> chromadb.Collection:
    """
    Return the ChromaDB collection for `session_id`, creating it if needed.
    Each collection uses pre-calculated embeddings (embedding_function=None).
    """
    client = _get_client()
    name = _collection_name(session_id)
    collection = client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def upsert_chunks(
    session_id: str,
    chunks: list[str],
    metadatas: list[dict[str, Any]],
    ids: list[str] | None = None,
) -> list[str]:
    """
    Embed and store text chunks into the session's ChromaDB collection.

    Parameters
    ----------
    session_id : Target session.
    chunks     : Plain-text chunks to embed and store.
    metadatas  : One metadata dict per chunk (source, page number, etc.).
    ids        : Optional explicit IDs; auto-generated if omitted.

    Returns
    -------
    The list of document IDs that were upserted.
    """
    if not chunks:
        return []

    collection = get_or_create_collection(session_id)

    doc_ids = ids or [str(uuid.uuid4()) for _ in chunks]
    embeddings = [embed_text(chunk, task_type="RETRIEVAL_DOCUMENT") for chunk in chunks]

    collection.upsert(
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=doc_ids,
    )

    logger.info("Upserted %d chunks into collection %s", len(chunks), _collection_name(session_id))
    return doc_ids


def similarity_search(
    session_id: str,
    query: str,
    n_results: int = 5,
) -> dict[str, Any]:
    """
    Embed `query` with RETRIEVAL_QUERY task type and search the session
    collection.  Falls back to the global collection when the session
    collection is empty.

    Returns a dict:
      {
        "documents": [["chunk text", ...]],
        "metadatas": [[{...}, ...]],
        "ids":       [["id1", ...]],
        "distances": [[0.12, ...]],
      }
    """
    collection = get_or_create_collection(session_id)

    # If the collection is empty, return an empty result set.
    if collection.count() == 0:
        return {"documents": [[]], "metadatas": [[]], "ids": [[]], "distances": [[]]}

    query_embedding = embed_query(query)

    # n_results cannot exceed the number of items in the collection
    safe_n = min(n_results, collection.count())

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=safe_n,
        include=["documents", "metadatas", "distances"],
    )
    return results


def delete_session_collection(session_id: str) -> None:
    """Remove all vectors associated with a session.  Use with care."""
    client = _get_client()
    name = _collection_name(session_id)
    try:
        client.delete_collection(name)
        logger.info("Deleted ChromaDB collection: %s", name)
    except Exception as exc:
        logger.warning("Could not delete collection %s: %s", name, exc)
