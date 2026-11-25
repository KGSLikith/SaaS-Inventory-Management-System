import React, { useState } from 'react';
import api from '../api';

export default function SettingsPage({ organization, defaultThreshold, onSaved }) {
  const [threshold, setThreshold] = useState(defaultThreshold);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSave = async (e) => {
    e.preventDefault();
    setMessage('');
    setError('');
    try {
      await api.put('/settings', { default_low_stock_threshold: Number(threshold) });
      setMessage('Default low-stock threshold updated successfully.');
      onSaved();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to save settings');
    }
  };

  return (
    <div className="card" style={{ maxWidth: 520 }}>
      <h3 style={{ marginTop: 0 }}>Organization Settings — {organization?.name}</h3>
      {message && <div className="success-msg">{message}</div>}
      {error && <div className="error-msg">{error}</div>}
      <form onSubmit={handleSave}>
        <div style={{ marginBottom: 14 }}>
          <label>Default Low-Stock Threshold (Units)</label>
          <input
            type="number"
            min="0"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            required
          />
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: 6 }}>
            Any product without a custom threshold whose quantity is equal to or below this value will appear as Low Stock on your Dashboard.
          </p>
        </div>
        <button className="primary" type="submit">Save Settings</button>
      </form>
    </div>
  );
}