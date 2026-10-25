import React from 'react';
import { ArrowRight, CheckCircle2, AlertCircle, Database, Cog, FileText, RefreshCw, Info } from 'lucide-react';
import { KPI_ICONS, TONES } from './config';
import IntelChart from './IntelChart';
import IntelTable from './IntelTable';

const SCOPE_TONES = ['info', 'good', 'warn'];

function Kpi({ k }) {
  const Icon = KPI_ICONS[k.icon] || KPI_ICONS.box;
  const tone = TONES[k.tone] || TONES.neutral;
  const colored = k.trend || ['bad', 'warn'].includes(k.tone);
  return (
    <div className="iq-card iq-kpi">
      <div className="iq-kpi-top">
        <span className="iq-kpi-label">{k.label}</span>
        <span className="iq-kpi-icon" style={{ color: tone.fg, background: tone.bg }}><Icon size={18} /></span>
      </div>
      <div className={`iq-kpi-value ${k.value.length > 14 ? 'long' : ''}`} title={k.value}>{k.value}</div>
      <div className="iq-kpi-sub" style={{ color: colored ? tone.fg : undefined }}>
        {k.trend === 'up' && '↑ '}{k.trend === 'down' && '↓ '}{k.sub}
      </div>
    </div>
  );
}

function PipelineBox({ kind, icon: Icon, title, lines }) {
  return (
    <div className={`iq-pipe iq-pipe-${kind}`}>
      <span className="iq-pipe-icon"><Icon size={22} /></span>
      <div>
        <div className="iq-pipe-kind">{kind.toUpperCase()}</div>
        <div className="iq-pipe-title">{title}</div>
        {lines.filter(Boolean).map((l) => <div key={l} className="iq-pipe-line">{l}</div>)}
      </div>
    </div>
  );
}

export function PageHeader({ meta, data, loading, onRefresh }) {
  const Icon = meta.icon;
  const status = loading ? 'loading' : data?.status;
  return (
    <div className="iq-header">
      <span className="iq-header-icon"><Icon size={30} /></span>
      <div className="iq-header-text">
        <h2>{meta.number}. {data?.name || meta.name}</h2>
        <div className="iq-header-sub">
          <span>{data?.question || ''}</span>
          {(data?.scopes || []).map((s, i) => {
            const t = TONES[SCOPE_TONES[i % SCOPE_TONES.length]];
            return <span key={s} className="iq-scope" style={{ color: t.fg, background: t.bg, borderColor: t.border }}>{s}</span>;
          })}
        </div>
      </div>
      <div className="iq-header-right">
        {status === 'ready' && <span className="iq-status ready"><CheckCircle2 size={16} /> Results ready</span>}
        {status === 'needs_data' && <span className="iq-status warn"><AlertCircle size={16} /> Needs data</span>}
        {status === 'error' && <span className="iq-status bad"><AlertCircle size={16} /> Calculation failed</span>}
        {status === 'loading' && <span className="iq-status"><RefreshCw size={16} className="iq-spin" /> Calculating…</span>}
        <button type="button" className="iq-btn" onClick={onRefresh} disabled={loading} title="Recalculate from the current data">
          <RefreshCw size={14} /> Recalculate
        </button>
        {data?.computed_at && (
          <span className="iq-muted iq-small">Updated {new Date(data.computed_at + (data.computed_at.endsWith('Z') ? '' : 'Z')).toLocaleString()}</span>
        )}
      </div>
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="iq-body">
      <div className="iq-skel" style={{ height: 104 }} />
      <div className="iq-kpis">{[0, 1, 2, 3, 4].map((i) => <div key={i} className="iq-skel" style={{ height: 112 }} />)}</div>
      <div className="iq-charts">{[0, 1, 2].map((i) => <div key={i} className="iq-skel" style={{ height: 300 }} />)}</div>
      <div className="iq-skel" style={{ height: 360 }} />
    </div>
  );
}

export default function IntelligencePage({ meta, data }) {
  if (data.status !== 'ready') {
    return (
      <div className="iq-card iq-message">
        <AlertCircle size={28} />
        <div>
          <h4>{data.status === 'needs_data' ? 'This intelligence needs more data' : 'Something went wrong'}</h4>
          <p>{data.message}</p>
        </div>
      </div>
    );
  }
  const { pipeline } = data;
  return (
    <div className="iq-body">
      <div className="iq-card iq-pipeline">
        <PipelineBox kind="input" icon={Database} title={pipeline.input.title}
          lines={[`Scope: ${pipeline.input.scope}`, `Key columns: ${pipeline.input.columns}`]} />
        <ArrowRight className="iq-pipe-arrow" size={20} />
        <PipelineBox kind="algorithm" icon={Cog} title={pipeline.algorithm.title} lines={[pipeline.algorithm.description]} />
        <ArrowRight className="iq-pipe-arrow" size={20} />
        <PipelineBox kind="output" icon={FileText} title={pipeline.output.title} lines={[pipeline.output.description]} />
      </div>

      <div className="iq-kpis">
        {data.kpis.map((k) => <Kpi key={k.label} k={k} />)}
      </div>

      <div className="iq-charts">
        {data.charts.map((c) => <IntelChart key={c.title} chart={c} />)}
      </div>

      <IntelTable key={meta.id} table={data.table} fileName={data.pipeline.output.title || meta.id} />

      {data.notes?.length > 0 && (
        <div className="iq-notes">
          {data.notes.map((n) => <div key={n}><Info size={14} /> {n}</div>)}
        </div>
      )}
    </div>
  );
}
