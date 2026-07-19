import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../context/SessionContext';
import { createConversation } from '../services/api';

const CreateAccount = () => {
  const navigate = useNavigate();
  const { setSessionId, setUsername } = useSession();

  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;

    setError('');
    setLoading(true);

    try {
      // Ask the backend for a fresh session_id
      const data = await createConversation();
      setSessionId(data.session_id);
      setUsername(trimmed);
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
          <h2 style={{ fontSize: '2rem', fontWeight: 600, marginBottom: '8px' }}>Join Alaska</h2>
          <p style={{ color: 'var(--text-muted)' }}>Create your account to get started</p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div>
            <label
              style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-muted)' }}
            >
              How should we call you?
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="User name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          {error && (
            <p style={{ color: '#f87171', fontSize: '14px', margin: '-8px 0' }}>{error}</p>
          )}

          <button
            type="submit"
            className="btn-primary"
            style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner" />
                Setting up…
              </>
            ) : (
              'Submit'
            )}
          </button>

          <div style={{ textAlign: 'center', marginTop: '8px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
              Already have an account?{' '}
              <span className="link-text" onClick={() => navigate('/login')}>
                Log In
              </span>
            </span>
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
          background: 'rgba(56, 189, 248, 0.1)',
          filter: 'blur(100px)',
          borderRadius: '50%',
          zIndex: 0,
        }}
      />
    </div>
  );
};

export default CreateAccount;
