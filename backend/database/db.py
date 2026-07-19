"""
database/db.py – SQLAlchemy engine, session factory, and base class.

The engine uses SQLite with check_same_thread=False so FastAPI's
async request handlers (which may hop between threads in the
threadpool) can safely share one database file.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings


# ── Engine ─────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,          # flip to True while debugging SQL
)

# ── Session factory ────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Declarative base ───────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency ─────────────────────────────────────────────────────────────
def get_db():
    """
    FastAPI dependency that opens a DB session per request and guarantees
    it is closed even when an exception is raised mid-handler.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
