/**
 * services/api.js
 *
 * Central API client for the Alaska backend.
 * All fetch calls live here — no component ever calls fetch() directly.
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/** Generic request helper — throws a descriptive Error on non-2xx. */
async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });

  if (!res.ok) {
    let message = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      message = body.detail || message;
    } catch (_) {}
    throw new Error(message);
  }

  if (res.status === 204) return null;
  return res.json();
}

// ─── Conversation ──────────────────────────────────────────────────────────

/** Create a brand-new conversation and get a fresh session_id. */
export async function createConversation() {
  return request('/conversation/new', { method: 'POST' });
}

/** Fetch the full message history for a session. */
export async function getConversationHistory(sessionId) {
  return request(`/conversation/${sessionId}/history`);
}

/** List all past conversations with titles. */
export async function listConversations() {
  return request('/conversation/list');
}

/** Permanently delete a conversation and all its messages. */
export async function deleteConversation(sessionId) {
  return request(`/conversation/${sessionId}`, { method: 'DELETE' });
}

// ─── Chat ──────────────────────────────────────────────────────────────────

/** Send a user message and receive the AI response via the RAG pipeline. */
export async function sendMessage(sessionId, userQuery) {
  return request('/chat', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, user_query: userQuery }),
  });
}

// ─── Search History ────────────────────────────────────────────────────────

/**
 * Get the RAG search-history log.
 * @param {string|null} sessionId  – optional filter
 * @param {string} queryFilter     – optional text filter applied client-side
 */
export async function getSearchHistory(sessionId = null, limit = 100, offset = 0) {
  const params = new URLSearchParams({ limit, offset });
  if (sessionId) params.set('session_id', sessionId);
  return request(`/search/history?${params.toString()}`);
}

// ─── File Upload ───────────────────────────────────────────────────────────

/**
 * Upload a file to the session knowledge base (documents) or Gemini
 * File API (media).  Uses FormData so Content-Type is set automatically.
 */
export async function uploadFile(sessionId, file) {
  const form = new FormData();
  form.append('session_id', sessionId);
  form.append('file', file);

  const res = await fetch(`${BASE_URL}/upload`, {
    method: 'POST',
    body: form,
    // No Content-Type header — browser sets it with the correct boundary
  });

  if (!res.ok) {
    let message = `Upload failed: ${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      message = body.detail || message;
    } catch (_) {}
    throw new Error(message);
  }

  return res.json();
}

// ─── Health ────────────────────────────────────────────────────────────────

/** Quick connectivity check — resolves true if the backend is reachable. */
export async function checkHealth() {
  try {
    await request('/health');
    return true;
  } catch (_) {
    return false;
  }
}
