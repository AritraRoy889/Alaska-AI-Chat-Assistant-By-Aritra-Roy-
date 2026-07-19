"""
services/gemini.py – Thin, stateless wrapper around the new google-genai SDK.
"""

from __future__ import annotations

import io
import logging
import mimetypes
import time
import threading
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError

from config import settings

logger = logging.getLogger(__name__)

# ── SDK initialisation ─────────────────────────────────────────────────────
# Using the new google-genai SDK
client = genai.Client(api_key=settings.gemini_api_key)


# ── Simple token-bucket rate limiter ───────────────────────────────────────
class _RateLimiter:
    """Thread-safe limiter: at most `max_calls` requests per `period` seconds."""

    def __init__(self, max_calls: int = 8, period: float = 60.0):
        self._max_calls = max_calls
        self._period = period
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block until a request slot is available."""
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._period
            self._timestamps = [t for t in self._timestamps if t > cutoff]

            if len(self._timestamps) >= self._max_calls:
                oldest_in_window = self._timestamps[0]
                sleep_for = self._period - (now - oldest_in_window) + 0.5
                if sleep_for > 0:
                    logger.info("Rate limiter: sleeping %.1fs before next API call", sleep_for)
                    time.sleep(sleep_for)

            self._timestamps.append(time.monotonic())


_limiter = _RateLimiter(max_calls=8, period=60.0)


# ── Retry helper ───────────────────────────────────────────────────────────

_MAX_RETRIES = 3
_BASE_BACKOFF = 10.0


def _call_with_retry(fn, *args, **kwargs):
    """
    Call `fn` up to _MAX_RETRIES times, backing off on 429 / 503 errors.
    """
    last_exc = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            _limiter.wait()
            return fn(*args, **kwargs)
        except APIError as exc:
            last_exc = exc
            if exc.code in (429, 503):
                wait = _BASE_BACKOFF * attempt
                logger.warning(
                    "Gemini API rate-limited or unavailable (attempt %d/%d). Retrying in %.0fs…",
                    attempt, _MAX_RETRIES, wait,
                )
                time.sleep(wait)
            else:
                raise # Re-raise immediately for 400, 404, etc.
        except Exception as exc:
            # Catchall for network errors not wrapped by APIError
            if "429" in str(exc) or "503" in str(exc):
                last_exc = exc
                wait = _BASE_BACKOFF * attempt
                time.sleep(wait)
            else:
                raise

    raise last_exc  # type: ignore[misc]


# ── Prompt truncation ─────────────────────────────────────────────────────

MAX_PROMPT_CHARS = 6_000

def _trim_prompt(prompt: str) -> str:
    """Trim prompt if it exceeds max size to save quota."""
    if len(prompt) <= MAX_PROMPT_CHARS:
        return prompt

    head_budget = MAX_PROMPT_CHARS // 3
    tail_budget = MAX_PROMPT_CHARS // 3
    head = prompt[:head_budget]
    tail = prompt[-tail_budget:]
    return head + "\n\n[… earlier conversation trimmed to save tokens …]\n\n" + tail


# ── Embedding ──────────────────────────────────────────────────────────────
def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Embed a single string and return the raw float vector."""
    result = _call_with_retry(
        client.models.embed_content,
        model=settings.gemini_embedding_model,
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return result.embeddings[0].values


def embed_query(text: str) -> list[float]:
    """Convenience wrapper for querying."""
    return embed_text(text, task_type="RETRIEVAL_QUERY")


# ── Chat generation ────────────────────────────────────────────────────────
def generate_response(
    prompt: str,
    file_uris: list[dict[str, str]] | None = None,
    temperature: float = 0.7,
) -> str:
    """Send a fully-constructed prompt to the Gemini chat model."""
    prompt = _trim_prompt(prompt)

    contents = []
    
    if file_uris:
        for f in file_uris:
            # Create a Part from URI for the new SDK
            contents.append(
                types.Part.from_uri(uri=f["uri"], mime_type=f["mime_type"])
            )

    contents.append(prompt)

    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=1024,
    )

    response = _call_with_retry(
        client.models.generate_content,
        model=settings.gemini_chat_model,
        contents=contents,
        config=config,
    )

    try:
        return response.text
    except Exception as e:
        logger.warning("Gemini response was empty or blocked: %s", e)
        return "I'm sorry, I wasn't able to generate a response for that. Could you try rephrasing?"


# ── File API upload ────────────────────────────────────────────────────────
def upload_file_to_gemini(
    file_bytes: bytes,
    filename: str,
    mime_type: str | None = None,
) -> dict[str, str]:
    """Upload raw bytes to the Gemini File API."""
    import os
    import tempfile

    if mime_type is None:
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type is None:
            mime_type = "application/octet-stream"

    suffix = os.path.splitext(filename)[-1] or ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # Using the new File API
        uploaded = _call_with_retry(
            client.files.upload,
            file=tmp_path,
            config={'display_name': filename, 'mime_type': mime_type}
        )
    finally:
        os.unlink(tmp_path)

    logger.info("Uploaded file to Gemini File API: uri=%s", uploaded.uri)
    return {"uri": uploaded.uri, "mime_type": mime_type}
