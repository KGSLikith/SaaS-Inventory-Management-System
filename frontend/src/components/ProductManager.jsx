import React, { useState } from 'react';
import api from '../api';

const emptyForm = {
  name: '',
  sku: '',
  description: '',
  quantity: 0,
  cost_price: '',
  selling_price: '',
  low_stock_threshold: '',
};

export default function ProductManager({ products, defaultThreshold, onRefresh }) {
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      if (editingId) {
        await api.put(`/products/${editingId}`, form);
      } else {
        await api.post('/products', form);
      }
      setForm(emptyForm);
      setEditingId(null);
      onRefresh();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to save product');
    }
  };

  const startEdit = (product) => {
    setEditingId(product.id);
    setForm({
      name: product.name,
      sku: product.sku,
      description: product.description || '',
      quantity: product.quantity,
      cost_price: product.cost_price,
      selling_price: product.selling_price,
      low_stock_threshold: product.low_stock_threshold ?? '',
    });
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this product permanently?')) return;
    try {
      await api.delete(`/products/${id}`);
      onRefresh();
    } catch (err) {
      setError('Failed to delete product');
    }
  };
  const adjustQuantity = async (product, delta) => {
    const newQty = Math.max(0, Number(product.quantity) + delta);
    try {
      await api.patch(`/products/${product.id}/quantity`, { quantity: newQty });
      onRefresh();
    } catch (err) {
      setError('Failed to update quantity');
    }
  };

  return (
    <div>
      <div className="card">
        <h3 style={{ marginTop: 0 }}>{editingId ? 'Edit Product' : 'Add New Product'}</h3>
        {error && <div className="error-msg">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div>
              <label>Product Name *</label>
              <input name="name" placeholder="Basmati Rice" value={form.name} onChange={handleChange} required />
            </div>
            <div>
              <label>SKU *</label>
              <input name="sku" placeholder="RICE001" value={form.sku} onChange={handleChange} required />
            </div>
            <div>
              <label>Description</label>
              <input name="description" placeholder="5 kg rice bag" value={form.description} onChange={handleChange} />
            </div>
            <div>
              <label>Quantity *</label>
              <input type="number" min="0" name="quantity" value={form.quantity} onChange={handleChange} required />
            </div>
            <div>
              <label>Cost Price (₹) *</label>
              <input type="number" step="0.01" min="0" name="cost_price" placeholder="400" value={form.cost_price} onChange={handleChange} required />
            </div>
            <div>
              <label>Selling Price (₹) *</label>
              <input type="number" step="0.01" min="0" name="selling_price" placeholder="500" value={form.selling_price} onChange={handleChange} required />
            </div>
            <div>
              <label>Low Stock Threshold (Default: {defaultThreshold})</label>
              <input type="number" min="0" name="low_stock_threshold" placeholder={`Leave blank for ${defaultThreshold}`} value={form.low_stock_threshold} onChange={handleChange} />
            </div>
          </div>
          <div style={{ marginTop: 14, display: 'flex', gap: 10 }}>
            <button className="primary" type="submit">
              {editingId ? 'Update Product' : 'Add Product'}
            </button>
            {editingId && (
              <button type="button" className="secondary" onClick={() => { setEditingId(null);
                setForm(emptyForm); }}>
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>All Products ({products.length})</h3>
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>SKU</th>
              <th>Quantity</th>
              <th>Cost / Sell</th>
              <th>Threshold</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id}>
                <td>
                  <strong>{p.name}</strong>
                  <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{p.description}</div>
                </td>
                <td>{p.sku}</td>
                <td>
                  <button className="secondary" onClick={() => adjustQuantity(p, -1)}>-</button>
                  <strong style={{ margin: '0 8px' }}>{p.quantity}</strong>
                  <button className="secondary" onClick={() => adjustQuantity(p, 1)}>+</button>
                </td>
                <td>₹{p.cost_price} / ₹{p.selling_price}</td>
                <td>{p.effective_threshold}</td>
                <td>
                  {p.is_low_stock
                    ? <span className="badge-low">Low Stock</span>
                    : <span className="badge-ok">Normal</span>}
                </td>
                <td style={{ display: 'flex', gap: 6 }}>
                  <button className="secondary" onClick={() => startEdit(p)}>Edit</button>
                  <button className="danger" onClick={() => handleDelete(p.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}