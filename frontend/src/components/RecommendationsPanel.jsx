import React from 'react';
import { ShoppingBag, ArrowRight, Truck, CheckCircle } from 'lucide-react';

export default function RecommendationsPanel({ recommendations }) {
  return (
    <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.25rem' }}>
        <ShoppingBag size={20} color="var(--primary-violet)" />
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Smart Replenishment & Procurement Recommendations</h3>
      </div>

      {recommendations.length === 0 ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          <CheckCircle size={32} color="#10b981" style={{ marginBottom: '0.5rem' }} />
          <div>All inventory items are currently at optimal levels. No replenishment action required.</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          {recommendations.map((rec, idx) => (
            <div 
              key={idx} 
              style={{ 
                background: 'rgba(14, 21, 38, 0.8)', 
                border: '1px solid var(--border-glass)', 
                borderRadius: '12px', 
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                justify: 'space-between'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.6rem' }}>
                  <div>
                    <span className="badge badge-critical" style={{ fontSize: '0.65rem' }}>{rec.risk_level} RISK</span>
                    <h4 style={{ fontSize: '1rem', fontWeight: 700, marginTop: '0.4rem' }}>{rec.product_name}</h4>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>{rec.sku} — {rec.warehouse}</span>
                  </div>
                </div>

                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.8rem', lineHeight: '1.4' }}>
                  Current Stock: <strong style={{ color: '#ffffff' }}>{rec.current_stock} units</strong> | Days of Supply: <strong style={{ color: 'var(--color-critical)' }}>{rec.days_of_inventory} days</strong>
                </div>
              </div>

              <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '0.8rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <Truck size={12} /> Supplier: {rec.supplier} ({rec.lead_time_days}d Lead Time)
                  </div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--primary-cyan)', marginTop: '2px' }}>
                    Order {rec.recommended_reorder_qty} units
                  </div>
                </div>

                <button 
                  onClick={() => alert(`Purchase Order draft initiated for ${rec.recommended_reorder_qty} units of ${rec.sku} with ${rec.supplier}.`)}
                  className="btn-primary" 
                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}
                >
                  Create PO <ArrowRight size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
