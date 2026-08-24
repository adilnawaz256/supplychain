import React from 'react';
import { Package, AlertTriangle, ShoppingCart, DollarSign, TrendingUp, Warehouse } from 'lucide-react';

export default function KPICards({ summary }) {
  if (!summary) return null;

  return (
    <div className="kpi-grid">
      <div className="glass-panel kpi-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Total Inventory Value
            </span>
            <h2 style={{ fontSize: '1.75rem', fontWeight: 800, margin: '0.3rem 0', fontFamily: 'var(--font-mono)' }}>
              ${summary.total_inventory_value?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              {summary.total_inventory_items} Active SKU Locations across {summary.total_warehouses} Hubs
            </p>
          </div>
          <div style={{ padding: '0.6rem', borderRadius: '12px', background: 'rgba(99, 102, 241, 0.15)', color: 'var(--primary-indigo)' }}>
            <DollarSign size={22} />
          </div>
        </div>
      </div>

      <div className="glass-panel kpi-card critical">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-critical)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Stockout Risk Alerts
            </span>
            <h2 style={{ fontSize: '1.75rem', fontWeight: 800, margin: '0.3rem 0', color: 'var(--color-critical)', fontFamily: 'var(--font-mono)' }}>
              {summary.stockout_critical_count} Critical / {summary.stockout_high_count} High
            </h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              SKUs below Safety Stock & Lead Time window
            </p>
          </div>
          <div style={{ padding: '0.6rem', borderRadius: '12px', background: 'rgba(244, 63, 94, 0.15)', color: 'var(--color-critical)' }}>
            <AlertTriangle size={22} />
          </div>
        </div>
      </div>

      <div className="glass-panel kpi-card high">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-high)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Open Replenishment POs
            </span>
            <h2 style={{ fontSize: '1.75rem', fontWeight: 800, margin: '0.3rem 0', fontFamily: 'var(--font-mono)' }}>
              {summary.open_purchase_orders} Pending POs
            </h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              {summary.excess_inventory_count} SKUs identified with Excess Stock
            </p>
          </div>
          <div style={{ padding: '0.6rem', borderRadius: '12px', background: 'rgba(245, 158, 11, 0.15)', color: 'var(--color-high)' }}>
            <ShoppingCart size={22} />
          </div>
        </div>
      </div>

      <div className="glass-panel kpi-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              30-Day Sales Demand
            </span>
            <h2 style={{ fontSize: '1.75rem', fontWeight: 800, margin: '0.3rem 0', fontFamily: 'var(--font-mono)' }}>
              ${summary.recent_sales_30d_revenue?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </h2>
            <p style={{ fontSize: '0.75rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
              <TrendingUp size={12} /> Active historical velocity tracking
            </p>
          </div>
          <div style={{ padding: '0.6rem', borderRadius: '12px', background: 'rgba(6, 182, 212, 0.15)', color: 'var(--primary-cyan)' }}>
            <TrendingUp size={22} />
          </div>
        </div>
      </div>
    </div>
  );
}
