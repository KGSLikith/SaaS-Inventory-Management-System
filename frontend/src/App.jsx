import React, { useState, useEffect, useCallback } from 'react';
import api from './api';
import AuthPage from './components/AuthPage';
import Dashboard from './components/Dashboard';
import ProductManager from './components/ProductManager';
import SettingsPage from './components/SettingsPage';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('stockflow_token'));
  const [organization, setOrganization] = useState(() => {
    const saved = localStorage.getItem('stockflow_org');
    return saved ? JSON.parse(saved) : null;
  });
  const [activeTab, setActiveTab] = useState('dashboard');
  const [products, setProducts] = useState([]);
  const [defaultThreshold, setDefaultThreshold] = useState(5);

  const loadInventory = useCallback(async () => {
    if (!token) return;
    try {
      const { data } = await api.get('/products');
      setProducts(data.products);
      setDefaultThreshold(data.defaultThreshold);
    } catch (err) {
      if (err.response?.status === 401 || err.response?.status === 403) {
        handleLogout();
      }
    }
  }, [token]);

  useEffect(() => {
    loadInventory();
  }, [loadInventory]);

  const handleAuthSuccess = (org) => {
    setOrganization(org);
    setToken(localStorage.getItem('stockflow_token'));
  };

  const handleLogout = () => {
    localStorage.removeItem('stockflow_token');
    localStorage.removeItem('stockflow_org');
    localStorage.removeItem('stockflow_user');
    setToken(null);
    setOrganization(null);
    setProducts([]);
  };

  if (!token) {
    return <AuthPage onAuthSuccess={handleAuthSuccess} />;
  }

  return (
    <div>
      <header className="navbar">
        <h1>StockFlow <span style={{ fontWeight: 400, fontSize: '0.95rem' }}>| {organization?.name}</span></h1>
        <nav className="nav-links">
          <button className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            Dashboard
            </button>
          <button className={`nav-btn ${activeTab === 'products' ? 'active' : ''}`} onClick={() => setActiveTab('products')}>
            Products
          </button>
          <button className={`nav-btn ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
            Settings
          </button>
          <button className="nav-btn logout" onClick={handleLogout}>Logout</button>
        </nav>
      </header>

      <main className="container">
        {activeTab === 'dashboard' && (
          <Dashboard
            products={products}
            defaultThreshold={defaultThreshold}
            onNavigateProducts={() => setActiveTab('products')}
          />
        )}
        {activeTab === 'products' && (
          <ProductManager
            products={products}
            defaultThreshold={defaultThreshold}
            onRefresh={loadInventory}
          />
        )}
        {activeTab === 'settings' && (
          <SettingsPage
            organization={organization}
            defaultThreshold={defaultThreshold}
            onSaved={loadInventory}
          />
        )}
      </main>
    </div>
  );
}