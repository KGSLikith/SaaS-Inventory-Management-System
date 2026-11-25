import React from 'react';

export default function Dashboard({ products, defaultThreshold, onNavigateProducts }) {
  const totalProducts = products.length;
  const totalUnits = products.reduce((sum, p) => sum + Number(p.quantity), 0);
  const lowStockItems = products.filter((p) => p.is_low_stock);

  return (
    <div>
      <div className="kpi-grid">
        <div className="kpi-card">
          <div style={{ color: '#475569', fontWeight: 600 }}>Total Products</div>
          <div className="kpi-value">{totalProducts}</div>
        </div>
        <div className="kpi-card">
          <div style={{ color: '#475569', fontWeight: 600 }}>Total Available Stock (Units)</div>
          <div className="kpi-value">{totalUnits}</div>
        </div>
        <div className="kpi-card alert">
          <div style={{ color: '#475569', fontWeight: 600 }}>Low-Stock Alerts</div>
          <div className="kpi-value" style={{ color: '#dc2626' }}>{lowStockItems.length}</div>
        </div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>
            Products Running Low on Stock (Default Threshold: &le; {defaultThreshold})
          </h3>
          <button className="primary" onClick={onNavigateProducts}>Manage Inventory</button>
        </div>

        {lowStockItems.length === 0 ? (
          <p style={{ color: '#15803d', marginTop: 12 }}>
            All products are adequately stocked above their low-stock thresholds.
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Product Name</th>
                <th>SKU</th>
                <th>Remaining Qty</th>
                <th>Applied Threshold</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {lowStockItems.map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.name}</strong></td>
                  <td>{item.sku}</td>
                  <td style={{ color: '#dc2626', fontWeight: 700 }}>{item.quantity}</td>
                  <td>{item.effective_threshold}</td>
                  <td><span className="badge-low">Restock Needed</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}