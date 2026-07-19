/**
 * hooks/useChat.js
 *
 * Custom hook that owns all chat state and actions.
 * Components just call this hook — they don't touch the API directly.
 */

import { useState, useCallback } from 'react';
import { sendMessage } from '../services/api';

export function useChat(sessionId) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Append a message object to local state.
   * shape: { id, role: 'user'|'assistant', content, createdAt }
   */
  const appendMessage = useCallback((role, content) => {
    const msg = {
      id: Date.now() + Math.random(),
      role,
      content,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, msg]);
    return msg;
  }, []);

  /**
   * Send a user message to the backend and append both the user turn
   * and the AI response to local state.
   */
  const send = useCallback(
    async (text) => {
      if (!text.trim() || !sessionId) return;

      setError(null);
      appendMessage('user', text);
      setLoading(true);

      try {
        const data = await sendMessage(sessionId, text);
        appendMessage('assistant', data.response);
      } catch (err) {
        setError(err.message);
        appendMessage('assistant', `⚠️ ${err.message}`);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, appendMessage],
  );

  /** Seed local state with messages loaded from the API. */
  const loadHistory = useCallback((apiMessages) => {
    const mapped = apiMessages.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      createdAt: m.created_at,
    }));
    setMessages(mapped);
  }, []);

  const clearMessages = useCallback(() => setMessages([]), []);

  return { messages, loading, error, send, loadHistory, clearMessages };
}
