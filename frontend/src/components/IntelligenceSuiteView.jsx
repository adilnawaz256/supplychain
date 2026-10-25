import React, { useCallback, useEffect, useState } from 'react';
import { API_BASE_URL } from '../config/api';
import { INTELLIGENCES } from './intelligence/config';
import IntelligencePage, { PageHeader, PageSkeleton } from './intelligence/IntelligencePage';
import './intelligence/intelligence.css';

const STORAGE_KEY = 'intelligence_active_tab';

function initialTab() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (INTELLIGENCES.some((i) => i.id === saved)) return saved;
  } catch (e) { /* storage unavailable */ }
  return INTELLIGENCES[0].id;
}

export default function IntelligenceSuiteView() {
  const [active, setActive] = useState(initialTab);
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState({});

  const load = useCallback(async (id, refresh = false) => {
    setLoading((s) => ({ ...s, [id]: true }));
    try {
      const res = await fetch(`${API_BASE_URL}/api/intelligences/${id}${refresh ? '?refresh=true' : ''}`);
      const body = await res.json();
      if (!res.ok) throw new Error(body?.detail || `HTTP ${res.status}`);
      setResults((s) => ({ ...s, [id]: body }));
    } catch (e) {
      setResults((s) => ({ ...s, [id]: { status: 'error', message: `Could not load results from the backend: ${e.message}` } }));
    } finally {
      setLoading((s) => ({ ...s, [id]: false }));
    }
  }, []);

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, active); } catch (e) { /* storage unavailable */ }
    if (!results[active] && !loading[active]) load(active);
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  const meta = INTELLIGENCES.find((i) => i.id === active);
  const data = results[active];
  const busy = Boolean(loading[active]);

  return (
    <div className="iq-root">
      <nav className="iq-tabs" aria-label="Intelligences">
        {INTELLIGENCES.map((i) => {
          const Icon = i.icon;
          return (
            <button key={i.id} type="button" className={`iq-tab ${i.id === active ? 'active' : ''}`} onClick={() => setActive(i.id)}>
              <span className="iq-tab-num">{i.number}</span>
              <Icon size={16} />
              <span className="iq-tab-name">{i.name}</span>
            </button>
          );
        })}
      </nav>

      <PageHeader meta={meta} data={data} loading={busy} onRefresh={() => load(active, true)} />

      <div className="iq-subtabs">
        <span className="iq-subtab active">Overview</span>
      </div>

      {!data || (busy && !data.pipeline) ? <PageSkeleton /> : <IntelligencePage meta={meta} data={data} />}
    </div>
  );
}
