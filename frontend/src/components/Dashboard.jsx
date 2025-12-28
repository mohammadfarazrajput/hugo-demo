import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  AlertTriangle, 
  Package, 
  Truck, 
  TrendingUp, 
  ShieldAlert,
  CheckCircle2,
  Clock
} from 'lucide-react';
import './Dashboard.css';

function Dashboard() {
  const [data, setData] = useState({
    alerts: [],
    inventory: null,
    stockoutRisks: [],
    suppliers: [],
    loading: true
  });

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [alertsRes, invRes, risksRes, suppRes] = await Promise.all([
          axios.get('/api/alerts'),
          axios.get('/api/inventory-summary'),
          axios.get('/api/stockout-risks'),
          axios.get('/api/supplier-performance')
        ]);

        setData({
          alerts: alertsRes.data.alerts,
          inventory: invRes.data,
          stockoutRisks: risksRes.data.risks,
          suppliers: suppRes.data.suppliers,
          loading: false
        });
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
        setData(prev => ({ ...prev, loading: false }));
      }
    };

    fetchDashboardData();
  }, []);

  if (data.loading) return <div className="loading-state">Loading Operation Data...</div>;

  return (
    <div className="dashboard">
      {/* Top Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon alert"><AlertTriangle /></div>
          <div className="stat-info">
            <label>Active Alerts</label>
            <span className="value">{data.alerts.length}</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon stock"><Package /></div>
          <div className="stat-info">
            <label>Low Stock Items</label>
            <span className="value">{data.inventory?.low_stock_count || 0}</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon value"><TrendingUp /></div>
          <div className="stat-info">
            <label>Inventory Value</label>
            <span className="value">${data.inventory?.total_stock_value?.toLocaleString()}</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon supplier"><Truck /></div>
          <div className="stat-info">
            <label>Active Suppliers</label>
            <span className="value">{data.suppliers.length}</span>
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Critical Alerts List */}
        <section className="dashboard-section alerts-list">
          <h3><ShieldAlert size={20} /> Critical Operational Alerts</h3>
          <div className="scroll-area">
            {data.alerts.map((alert, i) => (
              <div key={i} className={`alert-item ${alert.severity}`}>
                <div className="alert-header">
                  <span className="severity-badge">{alert.severity}</span>
                  <span className="alert-type">{alert.alert_type}</span>
                </div>
                <p className="alert-msg">{alert.message}</p>
                <div className="alert-action">
                  <strong>Action:</strong> {alert.action_required}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Stockout Risks */}
        <section className="dashboard-section">
          <h3><Clock size={20} /> Stockout Forecast (14 Days)</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Material</th>
                <th>Days Left</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.stockoutRisks.slice(0, 6).map((risk, i) => (
                <tr key={i}>
                  <td>{risk.description}</td>
                  <td className="risk-days">{risk.days_until_stockout}</td>
                  <td><span className={`status-pill ${risk.urgency.toLowerCase()}`}>{risk.urgency}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Supplier Performance */}
        <section className="dashboard-section full-width">
          <h3><CheckCircle2 size={20} /> Supplier Reliability Monitor</h3>
          <div className="supplier-grid">
            {data.suppliers.map((s, i) => (
              <div key={i} className="supplier-card">
                <h4>{s.Supplier_Name}</h4>
                <div className="supp-stats">
                  <div>
                    <label>On-Time Rate</label>
                    <div className="progress-bar">
                      <div className="fill" style={{width: `${s.On_Time_Rate}%`}}></div>
                    </div>
                    <span>{s.On_Time_Rate}%</span>
                  </div>
                  <div className="lead-time">
                    <label>Avg Lead Time</label>
                    <span>{s.Lead_Time_Days} Days</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

export default Dashboard;