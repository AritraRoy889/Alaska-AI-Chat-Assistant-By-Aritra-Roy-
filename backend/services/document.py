"""
services/document.py – Pure-Python document parsing and chunking.

Handles three document types:
  • PDF  – via pdfplumber (more accurate layout) with PyPDF2 as fallback
  • TXT  – decoded directly
  • DOCX – via python-docx

After extracting text, the chunker splits it into overlapping windows
using a simple sentence-boundary-aware algorithm.  No external NLP
library is required.

Chunking strategy
─────────────────
  1. Split on double newlines (paragraph boundaries).
  2. If a paragraph is still longer than `max_chars`, split further at
     sentence endings ('. ', '! ', '? ').
  3. Merge small fragments together so every chunk is close to `max_chars`
     in size.
  4. Maintain a sliding overlap of roughly `overlap_chars` characters
     from the previous chunk so context is not lost at boundaries.
"""

from __future__ import annotations

import io
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ── Text extraction ────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF binary blob."""
    text_parts: list[str] = []

    # pdfplumber – preferred because it preserves table structure better
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except Exception as exc:
        logger.warning("pdfplumber failed (%s), falling back to PyPDF2", exc)

    # PyPDF2 fallback
    try:
        import PyPDF2

        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except Exception as exc:
        logger.error("PyPDF2 also failed: %s", exc)
        return ""


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Decode raw bytes as UTF-8 text, falling back to latin-1."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1", errors="replace")


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract paragraph text from a .docx file."""
    try:
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as exc:
        logger.error("python-docx extraction failed: %s", exc)
        return ""


# ── Chunking ───────────────────────────────────────────────────────────────

def _split_into_sentences(text: str) -> list[str]:
    """Rough sentence splitter – no NLTK or spaCy required."""
    # Split on typical sentence-ending punctuation followed by whitespace
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(
    text: str,
    max_chars: int = 800,
    overlap_chars: int = 150,
) -> list[str]:
    """
    Split `text` into chunks of at most `max_chars` characters with an
    overlap of roughly `overlap_chars` characters between consecutive chunks.

    Returns a list of non-empty strings.
    """
    if not text.strip():
        return []

    # Step 1: coarse split on blank lines (paragraphs)
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    # Step 2: if any paragraph still exceeds max_chars, break on sentences
    segments: list[str] = []
    for para in paragraphs:
        if len(para) <= max_chars:
            segments.append(para)
        else:
            sentences = _split_into_sentences(para)
            segments.extend(sentences)

    # Step 3: merge small segments and honour max_chars
    chunks: list[str] = []
    buffer = ""

    for seg in segments:
        candidate = (buffer + " " + seg).strip() if buffer else seg

        if len(candidate) <= max_chars:
            buffer = candidate
        else:
            if buffer:
                chunks.append(buffer)
            # If the segment itself is too long, hard-split it
            if len(seg) > max_chars:
                for start in range(0, len(seg), max_chars - overlap_chars):
                    chunks.append(seg[start : start + max_chars])
                buffer = ""
            else:
                buffer = seg

    if buffer:
        chunks.append(buffer)

    # Step 4: add overlap by prepending the tail of the previous chunk
    overlapping: list[str] = []
    for i, chunk in enumerate(chunks):
        if i == 0:
            overlapping.append(chunk)
        else:
            tail = chunks[i - 1][-overlap_chars:]
            overlapping.append((tail + " " + chunk).strip())

    return [c for c in overlapping if c]


# ── Metadata helpers ───────────────────────────────────────────────────────

def build_chunk_metadatas(
    chunks: list[str],
    source_name: str,
    session_id: str,
    extra: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Build a ChromaDB-compatible metadata dict for each chunk.

    Parameters
    ----------
    chunks      : The chunked text strings.
    source_name : Original filename or URL.
    session_id  : Owner session.
    extra       : Any additional metadata key-value pairs.
    """
    base: dict[str, Any] = {"source": source_name, "session_id": session_id}
    if extra:
        base.update(extra)

    return [
        {**base, "chunk_index": idx, "char_count": len(chunk)}
        for idx, chunk in enumerate(chunks)
    ]
