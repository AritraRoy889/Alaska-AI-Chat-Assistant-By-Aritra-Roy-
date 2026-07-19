import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../context/SessionContext';
import { useChat } from '../hooks/useChat';
import {
  getConversationHistory,
  listConversations,
  createConversation,
  uploadFile,
  getSearchHistory,
  deleteConversation,
} from '../services/api';
import TypewriterText from '../components/TypewriterText';

// ── Spinner ────────────────────────────────────────────────────────────────
const Spinner = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ animation: 'spin 0.8s linear infinite' }}>
    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round" />
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
  </svg>
);

// ── MessageBubble ──────────────────────────────────────────────────────────
const MessageBubble = ({ msg }) => {
  const isUser = msg.role === 'user';
  return (
    <div style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', marginBottom: '16px', padding: '0 24px', animation: 'fadeIn 0.3s ease-out' }}>
      {!isUser && (
        <div style={{ width: '34px', height: '34px', borderRadius: '50%', background: 'linear-gradient(135deg, #7c3aed, #38bdf8)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', fontWeight: 700, flexShrink: 0, marginRight: '12px', marginTop: '4px' }}>
          A
        </div>
      )}
      <div style={{ maxWidth: '72%', padding: '12px 16px', borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px', background: isUser ? 'linear-gradient(135deg, #7c3aed, #5b21b6)' : 'rgba(255,255,255,0.05)', border: isUser ? 'none' : '1px solid rgba(255,255,255,0.08)', color: 'var(--text-main)', fontSize: '15px', lineHeight: '1.6', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
        {msg.content}
      </div>
    </div>
  );
};

// ── TypingIndicator ────────────────────────────────────────────────────────
const TypingIndicator = () => (
  <div style={{ display: 'flex', padding: '0 24px 16px', gap: '12px', alignItems: 'center' }}>
    <div style={{ width: '34px', height: '34px', borderRadius: '50%', background: 'linear-gradient(135deg, #7c3aed, #38bdf8)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', fontWeight: 700, flexShrink: 0 }}>A</div>
    <div style={{ padding: '12px 18px', borderRadius: '18px 18px 18px 4px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', display: 'flex', gap: '6px', alignItems: 'center' }}>
      {[0, 1, 2].map((i) => (
        <span key={i} style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#a78bfa', animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite` }} />
      ))}
      <style>{`@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-6px); opacity: 1; } }`}</style>
    </div>
  </div>
);

// ── Main Component ─────────────────────────────────────────────────────────
const ChatInterface = () => {
  const navigate = useNavigate();
  const { sessionId, setSessionId, username, clearSession } = useSession();
  const { messages, loading, send, loadHistory, clearMessages } = useChat(sessionId);

  const [input, setInput] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [showGreeting, setShowGreeting] = useState(true);

  // Sidebar panel: null | 'history' | 'search'
  const [sidebarPanel, setSidebarPanel] = useState(null);

  // Conversation history list
  const [convList, setConvList] = useState([]);
  const [convListLoading, setConvListLoading] = useState(false);

  // Search history
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [allSearchHistory, setAllSearchHistory] = useState([]);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const searchInputRef = useRef(null);

  // Redirect to landing if no session
  useEffect(() => {
    if (!sessionId) navigate('/');
  }, [sessionId, navigate]);

  // Load existing history on mount
  useEffect(() => {
    if (!sessionId) return;
    (async () => {
      try {
        const data = await getConversationHistory(sessionId);
        if (data.total_messages > 0) {
          loadHistory(data.messages);
          setShowGreeting(false);
        }
      } catch (_) {}
    })();
  }, [sessionId]);

  // Hide greeting once first message arrives
  useEffect(() => {
    if (messages.length > 0) setShowGreeting(false);
  }, [messages.length]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Focus search input when panel opens
  useEffect(() => {
    if (sidebarPanel === 'search') {
      setTimeout(() => searchInputRef.current?.focus(), 100);
    }
  }, [sidebarPanel]);

  // ── Load conversation list ─────────────────────────────────────────────
  const openHistoryPanel = useCallback(async () => {
    setSidebarPanel('history');
    setConvListLoading(true);
    try {
      const data = await listConversations();
      setConvList(data.conversations || []);
    } catch (_) {
      setConvList([]);
    }
    setConvListLoading(false);
  }, []);

  // ── Delete a conversation ─────────────────────────────────────────────
  const handleDeleteConversation = useCallback(async (e, convSessionId) => {
    // Stop the click from also triggering switchConversation
    e.stopPropagation();
    if (!window.confirm('Delete this conversation? This cannot be undone.')) return;

    try {
      await deleteConversation(convSessionId);
      // Remove from the local list immediately
      setConvList(prev => prev.filter(c => c.session_id !== convSessionId));

      // If user deleted the active session, start a fresh one
      if (convSessionId === sessionId) {
        const data = await createConversation();
        setSessionId(data.session_id);
        clearMessages();
        setShowGreeting(true);
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  }, [sessionId, setSessionId, clearMessages]);

  // ── Load search history ────────────────────────────────────────────────
  const openSearchPanel = useCallback(async () => {
    setSidebarPanel('search');
    setSearchLoading(true);
    try {
      const data = await getSearchHistory(null, 200);
      setAllSearchHistory(data.items || []);
      setSearchResults(data.items || []);
    } catch (_) {
      setAllSearchHistory([]);
      setSearchResults([]);
    }
    setSearchLoading(false);
  }, []);

  // Filter search results on query change
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults(allSearchHistory);
    } else {
      const q = searchQuery.toLowerCase();
      setSearchResults(allSearchHistory.filter(item =>
        item.query_text.toLowerCase().includes(q)
      ));
    }
  }, [searchQuery, allSearchHistory]);

  // ── Switch to a past conversation ────────────────────────────────────
  const switchConversation = useCallback(async (convSessionId) => {
    try {
      const data = await getConversationHistory(convSessionId);
      setSessionId(convSessionId);
      clearMessages();
      loadHistory(data.messages);
      setShowGreeting(false);
      setSidebarPanel(null);
      setSidebarOpen(false);
    } catch (err) {
      console.error('Failed to load conversation:', err);
    }
  }, [setSessionId, clearMessages, loadHistory]);

  // ── Send message ─────────────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    await send(text);
    inputRef.current?.focus();
  }, [input, loading, send]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ── New conversation ──────────────────────────────────────────────────
  const handleNewConversation = async () => {
    try {
      const data = await createConversation();
      setSessionId(data.session_id);
      clearMessages();
      setShowGreeting(true);
      setSidebarPanel(null);
      setSidebarOpen(false);
    } catch (err) {
      console.error('Failed to create new conversation:', err);
    }
  };

  // ── File upload ───────────────────────────────────────────────────────
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !sessionId) return;
    // Reset the input so the same file can be re-selected
    e.target.value = '';

    setUploadStatus(`Uploading "${file.name}"…`);
    try {
      const res = await uploadFile(sessionId, file);
      setUploadStatus(`✓ ${res.message}`);
      setTimeout(() => setUploadStatus(''), 4000);
    } catch (err) {
      setUploadStatus(`⚠️ ${err.message}`);
      setTimeout(() => setUploadStatus(''), 5000);
    }
  };

  // ── Sidebar nav items ─────────────────────────────────────────────────
  const sidebarNavItems = [
    {
      id: 'new',
      label: 'New conversation',
      icon: <path d="M12 5v14M5 12h14" strokeLinecap="round" strokeLinejoin="round" />,
      style: { background: 'var(--primary)', color: 'white', borderRadius: '12px' },
      onClick: handleNewConversation,
    },
    {
      id: 'history',
      label: 'Conversation history',
      icon: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10z" strokeLinecap="round" strokeLinejoin="round" />,
      style: sidebarPanel === 'history' ? { background: 'rgba(124,58,237,0.2)', borderRadius: '12px' } : {},
      onClick: openHistoryPanel,
    },
    {
      id: 'search',
      label: 'Search history',
      icon: <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeLinejoin="round" />,
      style: sidebarPanel === 'search' ? { background: 'rgba(124,58,237,0.2)', borderRadius: '12px' } : {},
      onClick: openSearchPanel,
    },
  ];

  // ── Sidebar panel content ─────────────────────────────────────────────
  const renderSidebarPanel = () => {
    if (sidebarPanel === 'history') {
      return (
        <div style={{ flex: 1, overflowY: 'auto', marginTop: '8px' }}>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', padding: '0 8px 8px' }}>Past conversations</p>
          {convListLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '20px' }}><Spinner size={22} /></div>
          ) : convList.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '8px' }}>No conversations yet.</p>
          ) : (
            convList.map((conv) => (
              <div
                key={conv.session_id}
                style={{
                  position: 'relative', display: 'flex', alignItems: 'center',
                  background: conv.session_id === sessionId ? 'rgba(124,58,237,0.25)' : 'transparent',
                  borderRadius: '10px', marginBottom: '4px', transition: 'background 0.2s',
                  cursor: 'pointer',
                }}
                onMouseEnter={e => {
                  if (conv.session_id !== sessionId) e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                  e.currentTarget.querySelector('.del-btn').style.opacity = '1';
                }}
                onMouseLeave={e => {
                  if (conv.session_id !== sessionId) e.currentTarget.style.background = 'transparent';
                  e.currentTarget.querySelector('.del-btn').style.opacity = '0';
                }}
                onClick={() => switchConversation(conv.session_id)}
              >
                {/* Text content */}
                <div style={{ flex: 1, padding: '10px 8px 10px 12px', minWidth: 0 }}>
                  <div style={{ fontSize: '13px', color: 'var(--text-main)', fontWeight: 500, marginBottom: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {conv.title}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {conv.message_count} messages · {new Date(conv.updated_at).toLocaleDateString()}
                  </div>
                </div>

                {/* Delete button — always rendered, hidden until hover */}
                <button
                  className="del-btn"
                  title="Delete conversation"
                  onClick={(e) => handleDeleteConversation(e, conv.session_id)}
                  style={{
                    opacity: 0, transition: 'opacity 0.15s, color 0.15s',
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--text-muted)', padding: '8px 10px 8px 4px',
                    flexShrink: 0, display: 'flex', alignItems: 'center',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.color = '#f87171'; }}
                  onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M10 11v6M14 11v6" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </div>
            ))
          )}
        </div>
      );
    }

    if (sidebarPanel === 'search') {
      return (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', marginTop: '8px', minHeight: 0 }}>
          {/* Search input */}
          <div style={{ position: 'relative', marginBottom: '10px' }}>
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search your history…"
              style={{
                width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: '10px', padding: '9px 36px 9px 12px', color: 'var(--text-main)',
                fontSize: '13px', outline: 'none', boxSizing: 'border-box',
              }}
            />
            <svg style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', opacity: 0.4 }} width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>

          {/* Results */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px' }}>
              {searchResults.length} result{searchResults.length !== 1 ? 's' : ''}
            </p>
            {searchLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '20px' }}><Spinner size={22} /></div>
            ) : searchResults.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No matching history found.</p>
            ) : (
              searchResults.map((item) => (
                <div
                  key={item.id}
                  style={{
                    background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)',
                    borderRadius: '10px', padding: '10px 12px', marginBottom: '6px',
                  }}
                >
                  <div style={{ fontSize: '13px', color: 'var(--text-main)', marginBottom: '4px', lineHeight: '1.4' }}>
                    {item.query_text}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {new Date(item.created_at).toLocaleString()} · {item.num_results} chunks retrieved
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      );
    }

    return null;
  };

  // ── Render ────────────────────────────────────────────────────────────
  return (
    <div className="chat-layout">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <div
        className={`sidebar ${sidebarOpen ? 'open' : ''}`}
        style={{ justifyContent: 'space-between', display: 'flex', flexDirection: 'column' }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          {/* Logo */}
          <div style={{ padding: '4px 16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
            <h2 style={{ color: 'var(--text-main)', fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.5px' }}>Alaska</h2>
            <button className="icon-btn" onClick={() => { setSidebarOpen(false); setSidebarPanel(null); }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>

          {/* Nav items */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flexShrink: 0 }}>
            {sidebarNavItems.map(item => (
              <div
                key={item.id}
                className="sidebar-item"
                style={item.style}
                onClick={item.onClick}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  {item.icon}
                </svg>
                {item.label}
              </div>
            ))}
          </div>

          {/* Panel content (history / search) */}
          {sidebarPanel && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, marginTop: '16px', padding: '0 4px' }}>
              {renderSidebarPanel()}
            </div>
          )}
        </div>

        {/* Session info + logout */}
        <div style={{ padding: '16px', borderTop: '1px solid var(--glass-border)', flexShrink: 0 }}>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '12px' }}>
            Session: <span style={{ color: 'var(--text-main)', fontFamily: 'monospace' }}>{sessionId?.slice(0, 8)}…</span>
          </p>
          <button
            className="btn-secondary"
            style={{ width: '100%', fontSize: '14px', padding: '10px' }}
            onClick={() => { clearSession(); navigate('/'); }}
          >
            Log out
          </button>
        </div>
      </div>

      {/* Sidebar overlay (mobile) */}
      {sidebarOpen && (
        <div
          onClick={() => { setSidebarOpen(false); setSidebarPanel(null); }}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 99, backdropFilter: 'blur(2px)' }}
        />
      )}

      {/* ── Main chat area ─────────────────────────────────────────────────── */}
      <div className="chat-main">
        {/* Top bar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 24px', borderBottom: '1px solid var(--glass-border)', backdropFilter: 'blur(12px)', background: 'rgba(11,15,25,0.6)', position: 'sticky', top: 0, zIndex: 10 }}>
          <button className="icon-btn" onClick={() => setSidebarOpen(true)} title="Menu">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 12h18M3 6h18M3 18h18" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <span style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-main)' }}>Alaska</span>
          <div style={{ width: '36px' }} />
        </div>

        {/* Messages / Greeting */}
        <div
          className="chat-content"
          style={{
            flexDirection: 'column',
            justifyContent: showGreeting && messages.length === 0 ? 'center' : 'flex-start',
            overflowY: 'auto',
            padding: showGreeting && messages.length === 0 ? '40px' : '24px 0 0',
          }}
        >
          {showGreeting && messages.length === 0 ? (
            <h1 style={{ fontSize: 'clamp(1.6rem, 4vw, 3rem)', fontWeight: 700, textAlign: 'center', background: 'linear-gradient(to right, #fff, #a78bfa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              <TypewriterText text={`Let's start our conversation ${username}`} delay={55} />
            </h1>
          ) : (
            <>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} msg={msg} />
              ))}
              {loading && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Upload status banner */}
        {uploadStatus && (
          <div style={{ padding: '10px 24px', background: 'rgba(124, 58, 237, 0.15)', borderTop: '1px solid rgba(124, 58, 237, 0.3)', fontSize: '13px', color: '#c4b5fd', textAlign: 'center' }}>
            {uploadStatus}
          </div>
        )}

        {/* ── Input bar ─────────────────────────────────────────────────────── */}
        <div className="chat-input-container">
          <div className="chat-input-wrapper">
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              id="file-upload-input"
              style={{ display: 'none' }}
              accept=".pdf,.txt,.docx,.doc,image/*,audio/*,video/*"
              onChange={handleFileUpload}
            />
            {/* Attach button — triggers the hidden file input */}
            <button
              className="icon-btn"
              type="button"
              title="Attach a file or image"
              disabled={loading}
              onClick={() => fileInputRef.current?.click()}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>

            <textarea
              ref={inputRef}
              className="chat-input"
              placeholder="Ask me"
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
              }}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={loading}
              style={{ resize: 'none', lineHeight: '1.5', maxHeight: '160px', overflowY: 'auto' }}
            />

            <button
              className="send-btn"
              onClick={handleSend}
              disabled={loading || !input.trim()}
              title="Send message"
              style={{ opacity: loading || !input.trim() ? 0.5 : 1 }}
            >
              {loading ? (
                <Spinner size={18} />
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ transform: 'translateX(1px)' }}>
                  <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </button>
          </div>

          <p style={{ textAlign: 'center', fontSize: '12px', color: 'var(--text-muted)', marginTop: '10px' }}>
            Alaska can make mistakes — verify important information.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
