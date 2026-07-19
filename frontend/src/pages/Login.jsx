import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../context/SessionContext';
import { createConversation } from '../services/api';

const Login = () => {
  const navigate = useNavigate();
  const { setSessionId, setUsername } = useSession();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // NOTE: Full auth (password hashing, JWT) is a future backend feature.
  // For now we use the entered username as the display name and obtain
  // a real session_id from the backend.
  const handleLogin = async (e) => {
    e.preventDefault();
    if (!identifier.trim()) return;

    setError('');
    setLoading(true);

    try {
      const data = await createConversation();
      setSessionId(data.session_id);
      setUsername(identifier.split('@')[0]); // use the part before @ as name
      navigate('/chat');
    } catch (err) {
      setError(err.message || 'Could not reach the server. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container animate-fade-in">
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '420px',
          padding: '40px',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
          position: 'relative',
          zIndex: 10,
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '8px' }}>
          <h2 style={{ fontSize: '2rem', fontWeight: 600, marginBottom: '8px' }}>Welcome Back</h2>
          <p style={{ color: 'var(--text-muted)' }}>Sign in to continue to Alaska</p>
        </div>

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <input
            type="text"
            className="input-field"
            placeholder="Username or e-mail"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            required
            disabled={loading}
          />

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <input
              type="password"
              className="input-field"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
            <div style={{ textAlign: 'right' }}>
              <span className="link-text">Forgot password?</span>
            </div>
          </div>

          {error && (
            <p style={{ color: '#f87171', fontSize: '14px', margin: '-4px 0' }}>{error}</p>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
            <button
              type="submit"
              className="btn-primary"
              style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner" />
                  Signing in…
                </>
              ) : (
                'Log In'
              )}
            </button>

            <button
              type="button"
              className="btn-secondary"
              style={{ width: '100%' }}
              onClick={() => navigate('/create-account')}
              disabled={loading}
            >
              Create Account
            </button>
          </div>
        </form>
      </div>

      {/* Background glow */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '500px',
          height: '500px',
          background: 'rgba(124, 58, 237, 0.1)',
          filter: 'blur(100px)',
          borderRadius: '50%',
          zIndex: 0,
        }}
      />
    </div>
  );
};

export default Login;
