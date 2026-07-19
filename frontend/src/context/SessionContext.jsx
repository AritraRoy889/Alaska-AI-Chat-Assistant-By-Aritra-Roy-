/**
 * context/SessionContext.jsx
 *
 * Global React context that holds the active session_id and
 * the username in memory so every page can read them without
 * prop-drilling.
 *
 * The session_id is also persisted to sessionStorage so it
 * survives a hard refresh within the same browser tab.
 */

import React, { createContext, useContext, useState, useEffect } from 'react';

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [sessionId, setSessionIdState] = useState(
    () => sessionStorage.getItem('alaska_session_id') || null,
  );
  const [username, setUsernameState] = useState(
    () => sessionStorage.getItem('alaska_username') || 'Guest',
  );

  const setSessionId = (id) => {
    setSessionIdState(id);
    if (id) sessionStorage.setItem('alaska_session_id', id);
    else sessionStorage.removeItem('alaska_session_id');
  };

  const setUsername = (name) => {
    setUsernameState(name);
    sessionStorage.setItem('alaska_username', name);
  };

  const clearSession = () => {
    setSessionId(null);
    setUsernameState('Guest');
    sessionStorage.clear();
  };

  return (
    <SessionContext.Provider value={{ sessionId, setSessionId, username, setUsername, clearSession }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used inside <SessionProvider>');
  return ctx;
}
