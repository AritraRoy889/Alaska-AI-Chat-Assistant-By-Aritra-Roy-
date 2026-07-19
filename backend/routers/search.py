"""
routers/search.py – GET /search/history

Returns the global log of every RAG query made across all sessions,
or optionally filtered to a single session.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import SearchHistory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["Search History"])


# ── Schemas ────────────────────────────────────────────────────────────────

class SearchHistoryItem(BaseModel):
    id: int
    session_id: str
    query_text: str
    retrieved_ids: list[str]
    retrieved_sources: list[str]
    num_results: int
    created_at: datetime

    class Config:
        from_attributes = True


class SearchHistoryResponse(BaseModel):
    total: int
    items: list[SearchHistoryItem]


# ── Route ──────────────────────────────────────────────────────────────────

@router.get(
    "/history",
    response_model=SearchHistoryResponse,
    summary="Get a log of all past RAG queries",
)
def search_history(
    session_id: str | None = Query(
        default=None,
        description="Filter results to a specific session.  Omit to get all sessions.",
    ),
    limit: int = Query(default=50, ge=1, le=500, description="Max number of records to return."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    db: Session = Depends(get_db),
) -> SearchHistoryResponse:
    """
    Retrieves the RAG search-history log.

    Each item includes:
      • The raw query text.
      • The IDs of the ChromaDB chunks that were retrieved.
      • The source file names of those chunks.
      • The number of results and the timestamp.

    You can filter by session_id and paginate using limit/offset.
    """
    query = db.query(SearchHistory)

    if session_id:
        query = query.filter(SearchHistory.session_id == session_id)

    total = query.count()
    rows = query.order_by(SearchHistory.created_at.desc()).offset(offset).limit(limit).all()

    items: list[SearchHistoryItem] = []
    for row in rows:
        items.append(
            SearchHistoryItem(
                id=row.id,
                session_id=row.session_id,
                query_text=row.query_text,
                retrieved_ids=_safe_json_load(row.retrieved_ids),
                retrieved_sources=_safe_json_load(row.retrieved_sources),
                num_results=row.num_results,
                created_at=row.created_at,
            )
        )

    return SearchHistoryResponse(total=total, items=items)


# ── Helpers ────────────────────────────────────────────────────────────────

def _safe_json_load(value: str | None) -> list[str]:
    """Safely deserialise a JSON string stored in the DB."""
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []
