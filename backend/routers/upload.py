"""
routers/upload.py – POST /upload

Accepts a file (multipart/form-data) and routes it based on MIME type:

  TEXT / DOCUMENTS (PDF, TXT, DOCX)
    → Extract text → chunk → embed → upsert into ChromaDB under session_id
    → Store a 'user' message in SQLite noting that documents were uploaded

  MEDIA (image, audio, video)
    → Upload to Gemini File API via genai.upload_file()
    → Store the returned URI and MIME type in the 'messages' table so the
      next /chat call can attach it to the multimodal prompt
"""

from __future__ import annotations

import logging
import mimetypes

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Conversation, Message
from services.document import (
    build_chunk_metadatas,
    chunk_text,
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_txt,
)
from services.gemini import upload_file_to_gemini
from vector_store.chroma import upsert_chunks

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["File Upload"])

# ── MIME type groups ───────────────────────────────────────────────────────
_TEXT_MIMES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
_MEDIA_MIMES_PREFIX = ("image/", "audio/", "video/")

# File size limit: 50 MB
MAX_FILE_SIZE = 50 * 1024 * 1024


# ── Schemas ────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    session_id: str
    filename: str
    mime_type: str
    upload_type: str          # 'document' | 'media'
    chunks_inserted: int      # non-zero only for document uploads
    gemini_file_uri: str | None  # non-None only for media uploads
    message: str


# ── Route ──────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a file to the session knowledge base or Gemini File API",
)
async def upload_file(
    session_id: str = Form(..., description="The active conversation session_id."),
    file: UploadFile = File(..., description="The file to upload."),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """
    Route a file upload based on its MIME type.

    Documents (PDF / TXT / DOCX):
      • Parse text from the file.
      • Chunk the text using the pure-Python chunker.
      • Embed each chunk and upsert into ChromaDB under the session_id.
      • Record a user message noting the upload.

    Media (image / audio / video):
      • Upload directly to the Gemini File API.
      • Store the returned URI in the message history so the next /chat
        request can include it in the multimodal prompt.
    """
    # ── Read file bytes ────────────────────────────────────────────────────
    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the 50 MB size limit.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # ── Determine MIME type ────────────────────────────────────────────────
    mime_type = file.content_type or ""
    if not mime_type or mime_type == "application/octet-stream":
        guessed, _ = mimetypes.guess_type(file.filename or "")
        mime_type = guessed or "application/octet-stream"

    filename = file.filename or "uploaded_file"

    logger.info("Upload received: filename=%s mime=%s session=%s", filename, mime_type, session_id)

    # ── Ensure session exists ──────────────────────────────────────────────
    conversation = db.query(Conversation).filter_by(session_id=session_id).first()
    if conversation is None:
        conversation = Conversation(session_id=session_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # ── Route based on MIME type ───────────────────────────────────────────

    # ─ Text / Document path ───────────────────────────────────────────────
    if mime_type in _TEXT_MIMES or filename.lower().endswith((".pdf", ".txt", ".docx", ".doc")):
        return _handle_document_upload(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
            session_id=session_id,
            db=db,
        )

    # ─ Media path ─────────────────────────────────────────────────────────
    if any(mime_type.startswith(prefix) for prefix in _MEDIA_MIMES_PREFIX):
        return _handle_media_upload(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
            session_id=session_id,
            db=db,
        )

    # ─ Unsupported ────────────────────────────────────────────────────────
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=(
            f"Unsupported file type '{mime_type}'.  "
            "Supported types: PDF, TXT, DOCX, and common image/audio/video formats."
        ),
    )


# ── Handlers ───────────────────────────────────────────────────────────────

def _handle_document_upload(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    session_id: str,
    db: Session,
) -> UploadResponse:
    """Parse, chunk, embed, and store a text document."""

    # 1. Extract raw text
    if mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
        raw_text = extract_text_from_pdf(file_bytes)
    elif mime_type == "text/plain" or filename.lower().endswith(".txt"):
        raw_text = extract_text_from_txt(file_bytes)
    else:
        # DOCX / DOC
        raw_text = extract_text_from_docx(file_bytes)

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract any readable text from the uploaded document.",
        )

    # 2. Chunk the text
    chunks = chunk_text(raw_text, max_chars=800, overlap_chars=150)

    # 3. Build metadata for each chunk
    metadatas = build_chunk_metadatas(chunks, source_name=filename, session_id=session_id)

    # 4. Embed and upsert into ChromaDB
    inserted_ids = upsert_chunks(session_id, chunks, metadatas)

    # 5. Record in conversation history
    msg = Message(
        session_id=session_id,
        role="user",
        content=f"[Uploaded document: {filename} – {len(chunks)} chunks indexed]",
    )
    db.add(msg)
    db.commit()

    logger.info(
        "Document upload complete: filename=%s chunks=%d session=%s",
        filename, len(chunks), session_id,
    )

    return UploadResponse(
        session_id=session_id,
        filename=filename,
        mime_type=mime_type,
        upload_type="document",
        chunks_inserted=len(inserted_ids),
        gemini_file_uri=None,
        message=f"Successfully indexed {len(chunks)} chunks from '{filename}' into your session knowledge base.",
    )


def _handle_media_upload(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    session_id: str,
    db: Session,
) -> UploadResponse:
    """Upload media to the Gemini File API and store the URI."""

    # 1. Upload to Gemini File API
    try:
        file_info = upload_file_to_gemini(file_bytes, filename, mime_type)
    except Exception as exc:
        logger.exception("Gemini File API upload failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload file to Gemini: {exc}",
        ) from exc

    # 2. Store the URI in the conversation history
    msg = Message(
        session_id=session_id,
        role="user",
        content=f"[Uploaded media: {filename}]",
        media_uri=file_info["uri"],
        media_mime=file_info["mime_type"],
    )
    db.add(msg)
    db.commit()

    logger.info(
        "Media upload complete: filename=%s uri=%s session=%s",
        filename, file_info["uri"], session_id,
    )

    return UploadResponse(
        session_id=session_id,
        filename=filename,
        mime_type=mime_type,
        upload_type="media",
        chunks_inserted=0,
        gemini_file_uri=file_info["uri"],
        message=(
            f"'{filename}' has been uploaded successfully.  "
            "You can now ask a question about this file in the chat."
        ),
    )
