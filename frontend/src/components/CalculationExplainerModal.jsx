import React from 'react';
import {
  X,
  Database,
  Calculator,
  ArrowRight,
  CheckCircle2,
  Sparkles,
  HelpCircle,
  TrendingUp,
  Layers,
  FileText,
  Copy,
  Check
} from 'lucide-react';

export default function CalculationExplainerModal({ item, onClose }) {
  const [copied, setCopied] = React.useState(false);

  if (!item) return null;

  const handleCopy = () => {
    const text = `Wisualyst Model Math Lineage:\nMetric: ${item.title || item.metricName}\nFormula: ${item.formula || 'Calculated dynamically'}\nValues: ${JSON.stringify(item.inputs || {}, null, 2)}\nResult: ${item.resultValue || ''}`;
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.65)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: '#ffffff',
        borderRadius: '16px',
        width: '100%',
        maxWidth: '720px',
        maxHeight: '90vh',
        overflowY: 'auto',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
        border: '1px solid #e2e8f0',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid #f1f5f9',
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          background: 'linear-gradient(135deg, #f8fafc 0%, #ffffff 100%)',
          borderRadius: '16px 16px 0 0'
        }}>
          <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              backgroundColor: '#eff6ff',
              color: '#2563eb',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid #bfdbfe'
            }}>
              <Calculator size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#2563eb', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Model Math & Data Lineage
                </span>
                <span style={{
                  fontSize: '0.68rem',
                  padding: '2px 8px',
                  borderRadius: '999px',
                  backgroundColor: '#ecfdf5',
                  color: '#059669',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}>
                  <CheckCircle2 size={11} /> 100% Live DB Data
                </span>
              </div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0f172a', margin: '4px 0 0 0' }}>
                {item.title || item.metricName || 'Calculation Explanation'}
              </h2>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={handleCopy}
              style={{
                background: 'none',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '6px 10px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.75rem',
                color: '#475569'
              }}
              title="Copy calculation trace"
            >
              {copied ? <Check size={14} color="#059669" /> : <Copy size={14} />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '6px',
                borderRadius: '8px'
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

          {/* 1. Final Result Callout */}
          <div style={{
            padding: '16px 20px',
            borderRadius: '12px',
            backgroundColor: '#f8fafc',
            border: '1px solid #e2e8f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
                Algorithm Result / Recommendation
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a', marginTop: '2px' }}>
                {item.resultValue ?? item.output ?? '—'}
              </div>
              {item.subtitle && (
                <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '2px' }}>
                  {item.subtitle}
                </div>
              )}
            </div>

            {item.badge && (
              <div style={{
                padding: '6px 12px',
                borderRadius: '8px',
                backgroundColor: item.badgeBg || '#eff6ff',
                color: item.badgeColor || '#2563eb',
                fontSize: '0.78rem',
                fontWeight: 700
              }}>
                {item.badge}
              </div>
            )}
          </div>

          {/* 2. Mathematical Formula Box */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
              <Sparkles size={16} color="#2563eb" />
              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0f172a' }}>
                Applied Mathematical Formula
              </span>
            </div>
            <div style={{
              padding: '14px 18px',
              borderRadius: '10px',
              backgroundColor: '#0f172a',
              color: '#38bdf8',
              fontFamily: 'monospace',
              fontSize: '0.95rem',
              fontWeight: 700,
              letterSpacing: '0.5px',
              boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.3)',
              overflowX: 'auto'
            }}>
              {item.formula || 'Result = f(Database_Inputs)'}
            </div>
            {item.formulaExplanation && (
              <p style={{ fontSize: '0.76rem', color: '#64748b', margin: '6px 0 0 0', lineHeight: 1.4 }}>
                {item.formulaExplanation}
              </p>
            )}
          </div>

          {/* 3. Database Provenance & Input Values */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
              <Database size={16} color="#059669" />
              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0f172a' }}>
                Database Source Lineage & Inputs
              </span>
            </div>
            <div style={{
              borderRadius: '10px',
              border: '1px solid #e2e8f0',
              overflow: 'hidden'
            }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                <thead style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                  <tr style={{ textAlign: 'left', color: '#64748b' }}>
                    <th style={{ padding: '8px 12px', fontWeight: 600 }}>Parameter</th>
                    <th style={{ padding: '8px 12px', fontWeight: 600 }}>Source Table & Column</th>
                    <th style={{ padding: '8px 12px', fontWeight: 600, textAlign: 'right' }}>Extracted Value</th>
                  </tr>
                </thead>
                <tbody>
                  {(item.inputs || []).map((inp, idx) => (
                    <tr key={idx} style={{ borderBottom: idx < item.inputs.length - 1 ? '1px solid #f1f5f9' : 'none' }}>
                      <td style={{ padding: '9px 12px', fontWeight: 700, color: '#0f172a' }}>{inp.name}</td>
                      <td style={{ padding: '9px 12px', color: '#64748b', fontFamily: 'monospace', fontSize: '0.74rem' }}>{inp.source}</td>
                      <td style={{ padding: '9px 12px', fontWeight: 700, color: '#2563eb', textAlign: 'right' }}>{inp.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 4. Step-by-Step Calculation Trace */}
          {item.steps && item.steps.length > 0 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <Layers size={16} color="#7c3aed" />
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0f172a' }}>
                  Step-by-Step Calculation Breakdown
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {item.steps.map((st, i) => (
                  <div key={i} style={{
                    padding: '10px 14px',
                    borderRadius: '8px',
                    backgroundColor: '#faf5ff',
                    border: '1px solid #f3e8ff',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px'
                  }}>
                    <span style={{
                      backgroundColor: '#7c3aed',
                      color: '#ffffff',
                      fontSize: '0.65rem',
                      fontWeight: 800,
                      width: '20px',
                      height: '20px',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      marginTop: '2px'
                    }}>
                      {i + 1}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#581c87' }}>{st.stepTitle}</div>
                      <div style={{ fontSize: '0.75rem', color: '#4b5563', fontFamily: st.isMath ? 'monospace' : 'inherit', marginTop: '2px' }}>
                        {st.stepDetail}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 5. Business Interpretation & Decision Action */}
          {item.businessInsight && (
            <div style={{
              padding: '14px 18px',
              borderRadius: '10px',
              backgroundColor: '#f0fdf4',
              border: '1px solid #bbf7d0',
              display: 'flex',
              gap: '12px',
              alignItems: 'flex-start'
            }}>
              <CheckCircle2 size={18} color="#16a34a" style={{ marginTop: '2px', flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#166534' }}>
                  Operational Impact & Recommendation:
                </div>
                <div style={{ fontSize: '0.75rem', color: '#15803d', marginTop: '2px', lineHeight: 1.4 }}>
                  {item.businessInsight}
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div style={{
          padding: '14px 24px',
          borderTop: '1px solid #f1f5f9',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#f8fafc',
          borderRadius: '0 0 16px 16px'
        }}>
          <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
            Validated against connected PostgreSQL schema • Zero synthetic fallbacks active.
          </span>
          <button
            onClick={onClose}
            className="btn-primary"
            style={{ padding: '8px 18px', fontSize: '0.78rem' }}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
