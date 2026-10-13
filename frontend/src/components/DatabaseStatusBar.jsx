import React from 'react';
import {
  Database,
  CheckCircle2,
  RefreshCw,
  Zap,
  Calculator,
  Server,
  Layers,
  Sparkles,
  AlertCircle
} from 'lucide-react';

export default function DatabaseStatusBar({
  connectorStatus,
  onRefresh,
  onOpenGlobalExplainer,
  isLoading,
  totalProducts = 0,
  totalSales = 0
}) {
  const isConnected = !!connectorStatus?.is_connected;
  const dbName = connectorStatus?.connector?.database || '—';
  const dbHost = connectorStatus?.connector?.host || 'no source connected';

  return (
    <div style={{
      padding: '14px 20px',
      borderRadius: '12px',
      backgroundColor: '#ffffff',
      border: '1px solid #e2e8f0',
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexWrap: 'wrap',
      gap: '14px'
    }}>
      {/* Left: DB Connection Pill and Live Stats */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 12px',
          borderRadius: '8px',
          backgroundColor: isConnected ? '#ecfdf5' : '#fff1f2',
          border: `1px solid ${isConnected ? '#a7f3d0' : '#fecdd3'}`
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: isConnected ? '#10b981' : '#f43f5e',
            boxShadow: isConnected ? '0 0 8px #10b981' : 'none'
          }} />
          <Database size={15} color={isConnected ? '#059669' : '#e11d48'} />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 800, color: isConnected ? '#065f46' : '#9f1239' }}>
              {isConnected ? 'Live Database Connected' : 'Database Offline'}
            </span>
            <span style={{ fontSize: '0.66rem', color: isConnected ? '#047857' : '#be123c', fontFamily: 'monospace' }}>
              {dbName} ({dbHost.length > 28 ? dbHost.substring(0, 25) + '...' : dbHost})
            </span>
          </div>
        </div>

        {/* Live records counters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.76rem', color: '#475569' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ fontWeight: 800, color: '#0f172a' }}>{Number(totalProducts || 0).toLocaleString()}</span>
            <span style={{ color: '#64748b' }}>Live Products</span>
          </div>
          <span style={{ color: '#cbd5e1' }}>•</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ fontWeight: 800, color: '#0f172a' }}>{Number(totalSales || 0).toLocaleString()}</span>
            <span style={{ color: '#64748b' }}>Sales rows</span>
          </div>
          <span style={{ color: '#cbd5e1' }}>•</span>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '2px 8px',
            borderRadius: '6px',
            backgroundColor: '#eff6ff',
            color: '#2563eb',
            fontWeight: 700,
            fontSize: '0.7rem'
          }}>
            <CheckCircle2 size={12} /> Computed from database tables
          </div>
        </div>
      </div>

      {/* Right: Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <button
          onClick={onOpenGlobalExplainer}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '7px 12px',
            borderRadius: '8px',
            backgroundColor: '#f5f3ff',
            border: '1px solid #ddd6fe',
            color: '#6d28d9',
            fontSize: '0.76rem',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
          title="See complete mathematical equations and data lineage for all 10 intelligence engines"
        >
          <Calculator size={14} color="#7c3aed" />
          <span>Inspect Model Math & Lineage</span>
        </button>

        <button
          onClick={onRefresh}
          disabled={isLoading}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '7px 12px',
            borderRadius: '8px',
            backgroundColor: '#f8fafc',
            border: '1px solid #e2e8f0',
            color: '#334155',
            fontSize: '0.76rem',
            fontWeight: 600,
            cursor: isLoading ? 'not-allowed' : 'pointer'
          }}
          title="Refresh calculations directly from database"
        >
          <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
          <span>{isLoading ? 'Updating...' : 'Refresh'}</span>
        </button>
      </div>
    </div>
  );
}
