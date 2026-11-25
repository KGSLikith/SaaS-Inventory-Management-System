import React, { useState } from 'react';
import api from '../api';

export default function AuthPage({ onAuthSuccess }) {
  const [isSignup, setIsSignup] = useState(false);
  const [organizationName, setOrganizationName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const endpoint = isSignup ? '/auth/signup' : '/auth/login';
      const payload = isSignup ? { organizationName, email, password } : { email, password };
      const { data } = await api.post(endpoint, payload);
      localStorage.setItem('stockflow_token', data.token);
      localStorage.setItem('stockflow_org', JSON.stringify(data.organization));
      localStorage.setItem('stockflow_user', JSON.stringify(data.user));
      onAuthSuccess(data.organization, data.user);
    } catch (err) {
      setError(err.response?.data?.error || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="card">
        <h2 style={{ marginTop: 0, color: '#0f766e' }}>
          {isSignup ? 'Create StockFlow Account' : 'Sign In to StockFlow'}
        </h2>
        {error && <div className="error-msg">{error}</div>}
        <form onSubmit={handleSubmit}>
          {isSignup && (
            <div style={{ marginBottom: 12 }}>
              <label>Organization / Store Name</label>
              <input
                type="text"
                placeholder="e.g., FreshMart Supermarket"
                value={organizationName}
                onChange={(e) => setOrganizationName(e.target.value)}
                required
              />
            </div>
          )}
          <div style={{ marginBottom: 12 }}>
            <label>Email Address</label>
            <input
              type="email"
              placeholder="owner@store.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label>Password</label>
            <input
              type="password"
              placeholder="Enter password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button className="primary" type="submit" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Please wait...' : isSignup ? 'Create Account' : 'Login'}
          </button>
        </form>
        <p style={{ marginTop: 16, textAlign: 'center', fontSize: '0.9rem' }}>
          {isSignup ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            type="button"
            className="secondary"
            onClick={() => { setIsSignup(!isSignup); setError(''); }}
          >
            {isSignup ? 'Login' : 'Sign Up'}
          </button>
        </p>
      </div>
    </div>
  );
}