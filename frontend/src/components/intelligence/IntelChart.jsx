import React, { useState } from 'react';
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Cell,
  PieChart, Pie, ScatterChart, Scatter, ZAxis, ComposedChart, RadarChart, Radar, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, LabelList, ReferenceLine,
} from 'recharts';
import { PALETTE } from './config';
import { formatShort, formatValue } from './format';

const AXIS = { fontSize: 11, fill: '#64748b' };
const HEIGHT = 250;

function Empty({ text }) {
  return <div className="iq-chart-empty">{text || 'Not enough data for this chart yet.'}</div>;
}

const tooltipStyle = {
  contentStyle: { borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 12, boxShadow: '0 8px 20px rgba(15,23,42,0.08)' },
  labelStyle: { fontWeight: 700, color: '#0f172a' },
};

function colorFor(chart, name, i) {
  return (chart.colors && chart.colors[name]) || chart.color || (chart.multicolor ? PALETTE[i % PALETTE.length] : PALETTE[0]);
}

function LineView({ chart }) {
  const [idx, setIdx] = useState(0);
  const variants = chart.variants || [];
  if (!variants.length) return <Empty text={chart.empty} />;
  const v = variants[Math.min(idx, variants.length - 1)];
  return (
    <>
      {variants.length > 1 && (
        <select className="iq-chart-select" value={idx} onChange={(e) => setIdx(Number(e.target.value))}>
          {variants.map((x, i) => <option key={x.label} value={i}>{x.label}</option>)}
        </select>
      )}
      <ResponsiveContainer width="100%" height={HEIGHT}>
        <LineChart data={v.data} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
          <XAxis dataKey="label" tick={AXIS} interval="preserveStartEnd" minTickGap={18} />
          <YAxis tick={AXIS} tickFormatter={(x) => formatShort(x, chart.valueFormat)} />
          <Tooltip {...tooltipStyle} formatter={(x) => formatValue(x, chart.valueFormat)} />
          <Legend iconType="plainline" wrapperStyle={{ fontSize: 11 }} />
          {v.split && <ReferenceLine x={v.split} stroke="#94a3b8" strokeDasharray="4 4" />}
          {chart.series.map((s) => (
            <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} dot={false}
              strokeWidth={s.dashed ? 1.5 : 2.2} strokeDasharray={s.dashed ? '5 4' : undefined} connectNulls={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </>
  );
}

function BarView({ chart }) {
  if (!chart.data?.length) return <Empty text={chart.empty} />;
  const fmt = chart.valueFormat;
  if (chart.series) {
    return (
      <ResponsiveContainer width="100%" height={HEIGHT}>
        <BarChart data={chart.data} margin={{ top: 18, right: 8, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
          <XAxis dataKey="name" tick={AXIS} interval={0} tickFormatter={(x) => (x.length > 12 ? `${x.slice(0, 11)}…` : x)} />
          <YAxis tick={AXIS} tickFormatter={(x) => formatShort(x, fmt)} />
          <Tooltip {...tooltipStyle} formatter={(x) => formatValue(x, fmt === 'pct0' ? 'pct' : fmt)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {chart.series.map((s, i) => (
            <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} maxBarSize={chart.stacked ? 40 : 28}
              stackId={chart.stacked ? 'stack' : undefined}
              radius={!chart.stacked ? [4, 4, 0, 0] : i === chart.series.length - 1 ? [4, 4, 0, 0] : 0}>
              {!chart.stacked && (
                <LabelList dataKey={s.key} position="top" formatter={(x) => formatShort(x, fmt)} style={{ fontSize: 10, fill: '#334155' }} />
              )}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={HEIGHT}>
      <BarChart data={chart.data} margin={{ top: 20, right: 8, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
        <XAxis dataKey="name" tick={AXIS} interval={0}
          tickFormatter={(x) => { const n = chart.data.length > 4 ? 10 : 14; return x.length > n ? `${x.slice(0, n - 1)}…` : x; }} />
        <YAxis tick={AXIS} tickFormatter={(x) => formatShort(x, fmt)} />
        <Tooltip {...tooltipStyle} formatter={(x) => [formatValue(x, fmt === 'pct0' ? 'pct' : fmt), chart.title]} />
        <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={56}>
          {chart.data.map((d, i) => <Cell key={d.name} fill={colorFor(chart, d.name, i)} />)}
          <LabelList dataKey="value" position="top" formatter={(x) => formatShort(x, fmt)} style={{ fontSize: 11, fill: '#334155', fontWeight: 600 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function HBarView({ chart }) {
  if (!chart.data?.length) return <Empty text={chart.empty} />;
  const fmt = chart.valueFormat;
  const width = chart.wideLabels ? 190 : 84;
  return (
    <ResponsiveContainer width="100%" height={Math.max(HEIGHT, chart.data.length * 24 + 20)}>
      <BarChart data={chart.data} layout="vertical" margin={{ top: 0, right: 52, left: 0, bottom: 0 }}>
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="name" tick={{ ...AXIS, fontSize: 10.5 }} width={width}
          tickFormatter={(x) => (x.length > (chart.wideLabels ? 34 : 12) ? `${x.slice(0, chart.wideLabels ? 33 : 11)}…` : x)} />
        <Tooltip {...tooltipStyle} formatter={(x) => [formatValue(x, fmt), 'Value']}
          labelFormatter={(l, p) => p?.[0]?.payload?.label || l} />
        <Bar dataKey="value" fill={chart.color || '#7c6cf0'} radius={[0, 4, 4, 0]} barSize={13}>
          <LabelList dataKey="value" position="right" formatter={(x) => formatShort(x, fmt)} style={{ fontSize: 10.5, fill: '#334155' }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function DonutView({ chart }) {
  const data = (chart.data || []).filter((d) => d.value > 0);
  if (!data.length) return <Empty text={chart.empty} />;
  const total = data.reduce((s, d) => s + d.value, 0);
  return (
    <div className="iq-donut">
      <div className="iq-donut-chart">
        <ResponsiveContainer width="100%" height={210}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="92%" paddingAngle={1} stroke="none">
              {data.map((d, i) => <Cell key={d.name} fill={colorFor({ ...chart, multicolor: true }, d.name, i)} />)}
            </Pie>
            <Tooltip {...tooltipStyle} formatter={(x) => formatValue(x, chart.valueFormat)} />
          </PieChart>
        </ResponsiveContainer>
        <div className="iq-donut-center">
          <strong>{chart.centerValue}</strong>
          <span>{chart.centerLabel}</span>
        </div>
      </div>
      <ul className="iq-legend">
        {data.map((d, i) => (
          <li key={d.name}>
            <span className="iq-dot" style={{ background: colorFor({ ...chart, multicolor: true }, d.name, i) }} />
            <span className="iq-legend-name" title={d.name}>{d.name}</span>
            <span className="iq-legend-val">{chart.showPercent ? `${((d.value / total) * 100).toFixed(0)}%` : formatShort(d.value, chart.valueFormat)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ScatterView({ chart }) {
  const groups = (chart.groups || []).filter((g) => g.points?.length);
  if (!groups.length) return <Empty text={chart.empty} />;
  const pos = (g) => g.points.filter((p) => (!chart.xLog || p.x > 0) && (!chart.yLog || p.y > 0));
  return (
    <ResponsiveContainer width="100%" height={HEIGHT}>
      <ScatterChart margin={{ top: 8, right: 12, left: -4, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
        <XAxis type="number" dataKey="x" name={chart.xLabel} scale={chart.xLog ? 'log' : 'auto'} domain={['auto', 'auto']}
          tick={AXIS} tickFormatter={(x) => formatShort(x, chart.xFormat)} allowDataOverflow />
        <YAxis type="number" dataKey="y" name={chart.yLabel} scale={chart.yLog ? 'log' : 'auto'} domain={['auto', 'auto']}
          tick={AXIS} tickFormatter={(x) => formatShort(x, chart.yFormat)} allowDataOverflow />
        {chart.sized && <ZAxis type="number" dataKey="z" range={[30, 300]} name="Lift" />}
        <Tooltip {...tooltipStyle} cursor={{ strokeDasharray: '3 3' }}
          content={({ payload }) => {
            const p = payload?.[0]?.payload;
            if (!p) return null;
            return (
              <div className="iq-tip">
                {p.label && <strong>{p.label}</strong>}
                <div>{chart.xLabel}: {formatValue(p.x, chart.xFormat || 'num')}</div>
                <div>{chart.yLabel}: {formatValue(p.y, chart.yFormat || 'num')}</div>
                {chart.sized && <div>Lift: {formatValue(p.z, 'num2')}</div>}
              </div>
            );
          }} />
        <Legend verticalAlign="top" wrapperStyle={{ fontSize: 11, paddingBottom: 6 }} />
        {groups.map((g, i) => (
          <Scatter key={g.name} name={g.name} data={pos(g)} fill={colorFor({ ...chart, multicolor: true }, g.name, i)} fillOpacity={0.75} />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

function CurveView({ chart }) {
  if (!chart.curve?.length) return <Empty text={chart.empty} />;
  return (
    <ResponsiveContainer width="100%" height={HEIGHT}>
      <ComposedChart margin={{ top: 8, right: 12, left: -8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
        <XAxis type="number" dataKey="x" domain={['auto', 'auto']} tick={AXIS} tickFormatter={(x) => formatShort(x, 'money')} />
        <YAxis type="number" dataKey="y" tick={AXIS} tickFormatter={(x) => formatShort(x, 'num')} />
        <Tooltip {...tooltipStyle} formatter={(x, n) => [formatValue(x, n === 'Price' ? 'money' : 'num'), n]}
          labelFormatter={(l) => `Price ${formatValue(l, 'money')}`} />
        <Legend verticalAlign="top" wrapperStyle={{ fontSize: 11, paddingBottom: 6 }} />
        <Scatter name="Actual Demand" data={chart.points} fill="#3b82f6" />
        <Line name="Model Demand" data={chart.curve} dataKey="y" stroke="#8b5cf6" strokeWidth={2.2} dot={{ r: 2.5 }} type="monotone" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function CompareView({ chart }) {
  if (!chart.rows?.length) return <Empty text={chart.empty} />;
  return (
    <table className="iq-compare">
      <thead>
        <tr>{chart.columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr>
      </thead>
      <tbody>
        {chart.rows.map((r) => (
          <tr key={r.metric}>
            {chart.columns.map((c) => {
              const val = r[c.key];
              const cls = c.key === 'change' ? (String(val).startsWith('-') ? 'neg' : 'pos') : c.key === 'optimal' ? 'opt' : '';
              return <td key={c.key} className={cls}>{val}</td>;
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RadarView({ chart }) {
  if (!chart.data?.length || !chart.series?.length) return <Empty text={chart.empty} />;
  return (
    <ResponsiveContainer width="100%" height={HEIGHT}>
      <RadarChart data={chart.data} outerRadius="72%">
        <PolarGrid stroke="#e2e8f0" />
        <PolarAngleAxis dataKey="axis" tick={{ fontSize: 10.5, fill: '#475569' }} />
        <PolarRadiusAxis domain={[0, 1]} tick={false} axisLine={false} />
        {chart.series.map((s, i) => (
          <Radar key={s} name={s} dataKey={s} stroke={colorFor({ ...chart, multicolor: true }, s, i)}
            fill={colorFor({ ...chart, multicolor: true }, s, i)} fillOpacity={0.08} strokeWidth={2} />
        ))}
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Tooltip {...tooltipStyle} formatter={(x) => x.toFixed(2)} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

function ComboView({ chart }) {
  if (!chart.data?.length) return <Empty text={chart.empty} />;
  const many = chart.data.length > 5;
  return (
    <ResponsiveContainer width="100%" height={HEIGHT}>
      <ComposedChart data={chart.data} margin={{ top: 18, right: 0, left: -6, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
        <XAxis dataKey="name" tick={many ? { ...AXIS, fontSize: 10, angle: -30, textAnchor: 'end' } : AXIS} interval={0}
          height={many ? 56 : 30} tickFormatter={(x) => (x.length > 14 ? `${x.slice(0, 13)}…` : x)} />
        <YAxis yAxisId="l" tick={AXIS} tickFormatter={(x) => formatShort(x, chart.barFormat)} />
        <YAxis yAxisId="r" orientation="right" tick={AXIS} tickFormatter={(x) => formatShort(x, chart.lineFormat)} />
        <Tooltip {...tooltipStyle} formatter={(x, n) => formatValue(x, n === chart.lineLabel ? 'pct_signed' : chart.barFormat)} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Bar yAxisId="l" dataKey="bar" name={chart.barLabel} fill="#3b82f6" radius={[6, 6, 0, 0]} maxBarSize={48}>
          {!many && <LabelList dataKey="bar" position="top" formatter={(x) => formatShort(x, chart.barFormat)} style={{ fontSize: 10, fill: '#334155' }} />}
        </Bar>
        <Line yAxisId="r" dataKey="line" name={chart.lineLabel} stroke="#8b5cf6" strokeWidth={2.2} type="monotone" dot={{ r: 3 }} connectNulls />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

const VIEWS = {
  line: LineView, bar: BarView, hbar: HBarView, donut: DonutView, scatter: ScatterView, curve: CurveView,
  compare: CompareView, radar: RadarView, combo: ComboView,
};

export default function IntelChart({ chart }) {
  const View = VIEWS[chart.type];
  const axes = ['scatter', 'curve'].includes(chart.type) && chart.xLabel ? `X: ${chart.xLabel} · Y: ${chart.yLabel}` : null;
  return (
    <div className="iq-card iq-chart-card">
      <div className="iq-chart-head">
        <h4>{chart.title}</h4>
        {(chart.subtitle || axes) && <span>{chart.subtitle || axes}</span>}
      </div>
      {View ? <View chart={chart} /> : <Empty text={`Unknown chart type: ${chart.type}`} />}
    </div>
  );
}
