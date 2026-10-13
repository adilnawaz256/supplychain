import React, { useState, useEffect, useCallback } from 'react';
import {
  Database,
  Table,
  Cpu,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { API_BASE_URL } from '../config/api';

const COUNT_LABELS = [
  ['products', 'Products'],
  ['inventory', 'Stock lines'],
  ['sales_history', 'Sales rows'],
  ['warehouses', 'Warehouses'],
  ['suppliers', 'Suppliers'],
  ['customers', 'Customers'],
  ['orders', 'Orders'],
  ['retail_spaces', 'Shelf spaces']
];

const STATUS_STYLE = {
  ready: { label: 'Running', color: '#047857', bg: '#ecfdf5', border: '#a7f3d0' },
  needs_data: { label: 'Needs data', color: '#92400e', bg: '#fffbeb', border: '#fde68a' },
  error: { label: 'Error', color: '#b91c1c', bg: '#fef2f2', border: '#fecaca' }
};

const TRUST_STYLE = {
  real: { label: 'Real data', color: '#047857', bg: '#ecfdf5' },
  partly_assumed: { label: 'Partly assumed', color: '#92400e', bg: '#fffbeb' },
  estimated: { label: 'Mostly estimated', color: '#b91c1c', bg: '#fef2f2' }
};

const formatDateTime = (iso) => {
  if (!iso) return null;
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`);
  return isNaN(d) ? iso : d.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};

const isActive = (job) => job && (job.status === 'QUEUED' || job.status === 'RUNNING');

const formatDate = (iso) => {
  if (!iso) return null;
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`);
  return isNaN(d) ? iso : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
};

function FlowBox({ icon: Icon, step, title, children, accent }) {
  return (
    <div style={{ flex: '1 1 220px', minWidth: 0, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '14px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <div style={{ width: 28, height: 28, borderRadius: 8, background: accent.bg, color: accent.color, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Icon size={16} />
        </div>
        <div>
          <div style={{ fontSize: '0.68rem', color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Step {step}</div>
          <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#0f172a' }}>{title}</div>
        </div>
      </div>
      {children}
    </div>
  );
}

function EngineCard({ engine, onNavigate }) {
  const [open, setOpen] = useState(false);
  const st = STATUS_STYLE[engine.status] || STATUS_STYLE.error;
  const ready = engine.status === 'ready';

  return (
    <div className="ui-card" style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: '8px', opacity: ready ? 1 : 0.92 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0f172a' }}>{engine.name}</div>
          <div style={{ fontSize: '0.76rem', color: '#64748b' }}>{engine.question}</div>
        </div>
        <span style={{ fontSize: '0.68rem', fontWeight: 700, color: st.color, background: st.bg, border: `1px solid ${st.border}`, padding: '2px 8px', borderRadius: 999, whiteSpace: 'nowrap' }}>
          {st.label}
        </span>
      </div>

      {ready && (
        <div>
          <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#0f172a', lineHeight: 1.2, overflowWrap: 'anywhere' }}>{engine.headline}</div>
          <div style={{ fontSize: '0.74rem', color: '#64748b' }}>{engine.metric_label}</div>
          {engine.secondary && (
            <div style={{ fontSize: '0.76rem', color: '#2563eb', fontWeight: 600, marginTop: 2 }}>{engine.secondary}</div>
          )}
        </div>
      )}

      <div style={{ fontSize: '0.8rem', color: '#334155', lineHeight: 1.45 }}>{engine.answer}</div>

      {ready && engine.trust && (
        <div style={{ fontSize: '0.72rem', color: TRUST_STYLE[engine.trust].color, background: TRUST_STYLE[engine.trust].bg, borderRadius: 6, padding: '4px 8px', display: 'flex', gap: 5, alignItems: 'flex-start' }}>
          {engine.trust === 'real' ? <CheckCircle2 size={12} style={{ flexShrink: 0, marginTop: 2 }} /> : <AlertTriangle size={12} style={{ flexShrink: 0, marginTop: 2 }} />}
          <span><strong>{TRUST_STYLE[engine.trust].label}</strong>{engine.assumption_note ? ` — ${engine.assumption_note}` : ' — calculated only from your tables.'}</span>
        </div>
      )}

      <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        {ready && engine.steps?.length > 0 ? (
          <button
            onClick={() => setOpen(o => !o)}
            style={{ background: 'none', border: 'none', padding: 0, color: '#7c3aed', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
          >
            {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            How was this calculated?
          </button>
        ) : !ready ? (
          <button
            onClick={() => onNavigate && onNavigate('datasources')}
            style={{ background: 'none', border: 'none', padding: 0, color: '#2563eb', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
          >
            Import data <ArrowRight size={13} />
          </button>
        ) : <span />}
        <span style={{ fontSize: '0.68rem', color: '#94a3b8' }} title="Database tables this engine reads">
          reads: {engine.tables.join(', ')}
        </span>
      </div>

      {open && (
        <ol style={{ margin: '4px 0 0 0', padding: '12px 14px 12px 30px', background: '#faf5ff', border: '1px solid #ede9fe', borderRadius: 10, fontSize: '0.78rem', color: '#334155', lineHeight: 1.5, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {engine.steps.map((s, i) => <li key={i}>{s}</li>)}
        </ol>
      )}
    </div>
  );
}

export default function HomeInsightsPanel({ onNavigate, onLoaded }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/insights/home`);
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const json = await res.json();
      setData(json);
      onLoaded && onLoaded(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [onLoaded]);

  useEffect(() => { load(); }, [load]);

  // While an import or ML recalculation runs in the background, poll its progress,
  // then reload the saved answers once it finishes.
  const runningJob = isActive(data?.import_job) ? data.import_job : isActive(data?.ml_job) ? data.ml_job : null;
  const [liveJob, setLiveJob] = useState(null);
  useEffect(() => {
    if (!runningJob) { setLiveJob(null); return; }
    let stop = false;
    const tick = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/jobs/${runningJob.id}`);
        const job = await res.json();
        if (stop) return;
        setLiveJob(job);
        if (isActive(job)) setTimeout(tick, 1500);
        else load();
      } catch (e) {
        if (!stop) setTimeout(tick, 3000);
      }
    };
    tick();
    return () => { stop = true; };
  }, [runningJob?.id, load]);

  const recalculate = async () => {
    try {
      await fetch(`${API_BASE_URL}/api/insights/recalculate`, { method: 'POST' });
    } catch (e) {}
    load();
  };

  if (error) {
    return (
      <div className="ui-card" style={{ padding: '16px 20px', color: '#b91c1c', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <AlertTriangle size={16} /> Could not load ML insights: {error}
        <button onClick={load} className="btn-secondary" style={{ marginLeft: 'auto' }}>Retry</button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="ui-card" style={{ padding: '20px', fontSize: '0.85rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: 8 }}>
        <RefreshCw size={14} className="animate-spin" /> Running the ML engines on your data...
      </div>
    );
  }

  const { pipeline, data: stored, engines, ready_count } = data;
  const counts = stored.counts || {};
  const lastImport = pipeline.imports?.[0];

  return (
    <div className="ui-card" style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '1rem', fontWeight: 800, color: '#0f172a' }}>From your data to answers</div>
          <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
            Every number below is calculated live from the tables imported out of your database. Click "How was this calculated?" on any card.
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          {data.computed_at && !liveJob && (
            <span style={{ fontSize: '0.74rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Clock size={12} /> Calculated {formatDateTime(data.computed_at)}
            </span>
          )}
          <button onClick={recalculate} disabled={loading || !!liveJob} className="btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <RefreshCw size={13} className={liveJob ? 'animate-spin' : ''} /> {liveJob ? 'Working...' : 'Recalculate'}
          </button>
        </div>
      </div>

      {liveJob && (
        <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 10, padding: '10px 14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, fontSize: '0.8rem', color: '#1e40af', fontWeight: 600, flexWrap: 'wrap' }}>
            <span>{liveJob.kind === 'import' ? 'Importing data in batches' : 'Recalculating ML results in the background'}: {liveJob.message}</span>
            {liveJob.progress_pct != null && <span>{liveJob.progress_pct}%</span>}
          </div>
          <div style={{ marginTop: 6, height: 6, background: '#dbeafe', borderRadius: 999, overflow: 'hidden' }}>
            <div style={{ width: `${liveJob.progress_pct ?? 5}%`, height: '100%', background: '#2563eb', transition: 'width 0.4s ease' }} />
          </div>
          <div style={{ marginTop: 6, fontSize: '0.72rem', color: '#475569' }}>
            The answers below are from the last finished calculation. They update by themselves when this finishes.
          </div>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'stretch', gap: 10, flexWrap: 'wrap' }}>
        <FlowBox icon={Database} step={1} title="Your database" accent={{ bg: pipeline.is_connected ? '#ecfdf5' : '#fef2f2', color: pipeline.is_connected ? '#059669' : '#dc2626' }}>
          <div style={{ fontSize: '0.78rem', color: pipeline.is_connected ? '#047857' : '#b91c1c', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 4 }}>
            {pipeline.is_connected ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
            {pipeline.is_connected ? 'Connected' : 'Not connected'}
          </div>
          {pipeline.source?.host && (
            <div style={{ fontSize: '0.72rem', color: '#64748b', fontFamily: 'monospace', overflowWrap: 'anywhere' }}>
              {pipeline.source.database} @ {pipeline.source.host}
            </div>
          )}
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
            <Clock size={11} />
            {lastImport ? `Last import: ${lastImport.source_table} (${formatDate(lastImport.at)})` : 'No tables imported yet'}
          </div>
          <button onClick={() => onNavigate && onNavigate('datasources')} style={{ marginTop: 6, background: 'none', border: 'none', padding: 0, color: '#2563eb', fontSize: '0.76rem', fontWeight: 700, cursor: 'pointer' }}>
            {pipeline.is_connected ? 'Import more tables →' : 'Connect a database →'}
          </button>
        </FlowBox>

        <div style={{ display: 'flex', alignItems: 'center', color: '#cbd5e1' }}><ArrowRight size={18} /></div>

        <FlowBox icon={Table} step={2} title="Stored in our tables" accent={{ bg: '#eff6ff', color: '#2563eb' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {COUNT_LABELS.map(([key, label]) => (
              <span key={key} style={{ fontSize: '0.7rem', padding: '2px 7px', borderRadius: 6, background: counts[key] ? '#ffffff' : 'transparent', border: `1px solid ${counts[key] ? '#e2e8f0' : '#f1f5f9'}`, color: counts[key] ? '#0f172a' : '#94a3b8' }}>
                <strong>{(counts[key] || 0).toLocaleString()}</strong> {label}
              </span>
            ))}
          </div>
          {stored.sales_from && (
            <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: 6 }}>
              Sales from {formatDate(stored.sales_from)} to {formatDate(stored.sales_to)}
            </div>
          )}
        </FlowBox>

        <div style={{ display: 'flex', alignItems: 'center', color: '#cbd5e1' }}><ArrowRight size={18} /></div>

        <FlowBox icon={Cpu} step={3} title="Machine learning engines" accent={{ bg: '#f5f3ff', color: '#7c3aed' }}>
          <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#0f172a' }}>
            {ready_count} <span style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: 600 }}>of {engines.length} running</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b' }}>
            {ready_count < engines.length
              ? 'Engines marked "Needs data" switch on as soon as you import the tables they read.'
              : 'All engines have the data they need.'}
          </div>
        </FlowBox>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 270px), 1fr))', gap: 12 }}>
        {engines.map(e => <EngineCard key={e.id} engine={e} onNavigate={onNavigate} />)}
      </div>
    </div>
  );
}
