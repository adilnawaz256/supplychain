import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Search, ChevronDown, ChevronsUpDown, ChevronUp, Columns3, Download, MoreHorizontal, X,
  ArrowUpRight, ArrowDownRight, ArrowRight, Check, Inbox,
} from 'lucide-react';
import { TONES, autoTone } from './config';
import { downloadText, formatValue, toCsv } from './format';

const TREND_ICON = { up: ArrowUpRight, down: ArrowDownRight, right: ArrowRight, ok: Check };
const TREND_TONE = { up: 'good', down: 'bad', right: 'warn', ok: 'info', none: 'neutral' };
const DEFAULT_TRENDS = { Growing: 'up', Declining: 'down', Stable: 'right' };

function Pill({ value, tone }) {
  const t = TONES[tone] || TONES.neutral;
  return <span className="iq-pill" style={{ color: t.fg, background: t.bg }}>{value}</span>;
}

function Cell({ col, value }) {
  if (value === null || value === undefined || value === '') return <span className="iq-muted">—</span>;
  if (col.format === 'pill') {
    return <Pill value={value} tone={col.pills?.[value] || autoTone(value)} />;
  }
  if (col.format === 'trend') {
    const dir = col.trends?.[value] || DEFAULT_TRENDS[value] || 'right';
    const Icon = TREND_ICON[dir];
    const t = TONES[TREND_TONE[dir]] || TONES.neutral;
    return (
      <span className="iq-trend" style={{ color: t.fg }}>
        {Icon && <Icon size={14} />} {value}
      </span>
    );
  }
  const text = formatValue(value, col.format);
  if (col.format === 'pct_signed' || col.format === 'pp') {
    return <span style={{ color: value > 0 ? '#059669' : value < 0 ? '#dc2626' : undefined, fontWeight: 600 }}>{text}</span>;
  }
  if (col.format === 'bold_int') return <strong>{text}</strong>;
  return text;
}

const isNumericCol = (c) => !['text', 'pill', 'trend'].includes(c.format || 'text');

function FilterMenu({ label, options, value, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const close = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);
  return (
    <div className="iq-menu" ref={ref}>
      <button type="button" className={`iq-btn ${value ? 'active' : ''}`} onClick={() => setOpen((o) => !o)}>
        {value ? `${label}: ${value}` : label} <ChevronDown size={14} />
      </button>
      {open && (
        <div className="iq-menu-pop">
          <button type="button" className={!value ? 'sel' : ''} onClick={() => { onChange(''); setOpen(false); }}>All</button>
          {options.map((o) => (
            <button type="button" key={o} className={value === o ? 'sel' : ''} onClick={() => { onChange(o); setOpen(false); }}>{o}</button>
          ))}
        </div>
      )}
    </div>
  );
}

function ColumnsMenu({ columns, hidden, onToggle }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const close = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);
  return (
    <div className="iq-menu" ref={ref}>
      <button type="button" className="iq-btn" onClick={() => setOpen((o) => !o)}>
        <Columns3 size={14} /> Columns <ChevronDown size={14} />
      </button>
      {open && (
        <div className="iq-menu-pop right">
          {columns.map((c) => (
            <label key={c.key} className="iq-check">
              <input type="checkbox" checked={!hidden.has(c.key)} onChange={() => onToggle(c.key)} /> {c.label}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

export default function IntelTable({ table, fileName }) {
  const { columns, rows } = table;
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState({});
  const [sort, setSort] = useState(table.sort || null);
  const [hidden, setHidden] = useState(() => new Set(columns.filter((c) => c.hidden).map((c) => c.key)));
  const [compact, setCompact] = useState(false);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [detail, setDetail] = useState(null);

  const labelOf = useMemo(() => Object.fromEntries(columns.map((c) => [c.key, c.label])), [columns]);
  const filterOptions = useMemo(() => (table.filters || []).map((key) => ({
    key,
    label: labelOf[key] || key,
    options: [...new Set(rows.map((r) => r[key]).filter((v) => v !== null && v !== undefined && v !== ''))].sort(),
  })).filter((f) => f.options.length > 1), [table.filters, rows, labelOf]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const textKeys = columns.filter((c) => !isNumericCol(c)).map((c) => c.key);
    let out = rows.filter((r) => Object.entries(filters).every(([k, v]) => !v || r[k] === v));
    if (q) out = out.filter((r) => textKeys.some((k) => String(r[k] ?? '').toLowerCase().includes(q)));
    if (sort) {
      const dir = sort.dir === 'asc' ? 1 : -1;
      out = [...out].sort((a, b) => {
        const x = a[sort.key];
        const y = b[sort.key];
        if (x === null || x === undefined) return 1;
        if (y === null || y === undefined) return -1;
        if (typeof x === 'number' && typeof y === 'number') return (x - y) * dir;
        return String(x).localeCompare(String(y)) * dir;
      });
    }
    return out;
  }, [rows, columns, filters, query, sort]);

  useEffect(() => setPage(0), [query, filters, sort, pageSize]);

  const visible = columns.filter((c) => !hidden.has(c.key));
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const start = page * pageSize;
  const shown = filtered.slice(start, start + pageSize);

  const toggleSort = (key) => setSort((s) => (s?.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'desc' }));
  const toggleCol = (key) => setHidden((h) => {
    const n = new Set(h);
    if (n.has(key)) n.delete(key); else n.add(key);
    return n;
  });

  return (
    <div className="iq-card iq-table-card">
      <div className="iq-table-head">
        <h3>{table.title}</h3>
        <span className="iq-muted">{filtered.length.toLocaleString()} of {rows.length.toLocaleString()} rows</span>
      </div>
      <div className="iq-toolbar">
        <div className="iq-search">
          <Search size={15} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={table.searchPlaceholder || 'Search...'} />
        </div>
        {filterOptions.map((f) => (
          <FilterMenu key={f.key} label={f.label} options={f.options} value={filters[f.key] || ''}
            onChange={(v) => setFilters((s) => ({ ...s, [f.key]: v }))} />
        ))}
        <div className="iq-toolbar-right">
          <ColumnsMenu columns={columns} hidden={hidden} onToggle={toggleCol} />
          <label className="iq-switch">
            <input type="checkbox" checked={compact} onChange={(e) => setCompact(e.target.checked)} />
            <span className="iq-switch-track" /> Compact
          </label>
          <button type="button" className="iq-btn strong" onClick={() => downloadText(`${fileName}.csv`, toCsv(visible, filtered))}>
            <Download size={14} /> Download CSV
          </button>
        </div>
      </div>

      <div className="iq-table-scroll">
        <table className={`iq-table ${compact ? 'compact' : ''}`}>
          <thead>
            <tr>
              {visible.map((c) => {
                const active = sort?.key === c.key;
                const Icon = !active ? ChevronsUpDown : sort.dir === 'asc' ? ChevronUp : ChevronDown;
                return (
                  <th key={c.key} className={isNumericCol(c) ? 'num' : ''} onClick={() => toggleSort(c.key)} title={c.info || c.label}>
                    <span>{c.label} <Icon size={12} className={active ? 'on' : ''} /></span>
                  </th>
                );
              })}
              <th className="iq-actions-col" />
            </tr>
          </thead>
          <tbody>
            {shown.map((r, i) => (
              <tr key={start + i} onClick={() => setDetail(r)}>
                {visible.map((c) => (
                  <td key={c.key} className={isNumericCol(c) ? 'num' : ''}><Cell col={c} value={r[c.key]} /></td>
                ))}
                <td className="iq-actions-col"><MoreHorizontal size={16} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!shown.length && (
          <div className="iq-empty"><Inbox size={28} /><span>No rows match the search or filters.</span></div>
        )}
      </div>

      <div className="iq-pager">
        <span>
          Showing {filtered.length ? start + 1 : 0}–{Math.min(start + pageSize, filtered.length)} of {filtered.length.toLocaleString()}
        </span>
        <div className="iq-pager-right">
          <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
            {[20, 50, 100].map((n) => <option key={n} value={n}>{n} / page</option>)}
          </select>
          <button type="button" className="iq-btn" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Prev</button>
          <span>{page + 1} / {pages}</span>
          <button type="button" className="iq-btn" disabled={page >= pages - 1} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      </div>

      {detail && (
        <div className="iq-drawer-backdrop" onClick={() => setDetail(null)}>
          <aside className="iq-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="iq-drawer-head">
              <h4>{detail[columns[1]?.key] || detail[columns[0]?.key]}</h4>
              <button type="button" className="iq-icon-btn" onClick={() => setDetail(null)}><X size={18} /></button>
            </div>
            <dl>
              {columns.map((c) => (
                <React.Fragment key={c.key}>
                  <dt>{c.label}</dt>
                  <dd><Cell col={c} value={detail[c.key]} /></dd>
                </React.Fragment>
              ))}
            </dl>
          </aside>
        </div>
      )}
    </div>
  );
}
