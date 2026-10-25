export const CURRENCY = '$';

const isNum = (v) => typeof v === 'number' && Number.isFinite(v);

export function money(v) {
  if (!isNum(v)) return '—';
  const a = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (a >= 1e9) return `${sign}${CURRENCY}${(a / 1e9).toFixed(1)}B`;
  if (a >= 1e6) return `${sign}${CURRENCY}${(a / 1e6).toFixed(2)}M`;
  if (a >= 1e4) return `${sign}${CURRENCY}${(a / 1e3).toFixed(1)}K`;
  if (a >= 100) return `${sign}${CURRENCY}${a.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  return `${sign}${CURRENCY}${a.toFixed(2)}`;
}

export function moneyFull(v) {
  if (!isNum(v)) return '—';
  const dp = Math.abs(v) < 100 ? 2 : 0;
  return `${v < 0 ? '-' : ''}${CURRENCY}${Math.abs(v).toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp })}`;
}

export function num(v, dp = 0) {
  if (!isNum(v)) return '—';
  return v.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
}

export function compact(v) {
  if (!isNum(v)) return '—';
  const a = Math.abs(v);
  if (a >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (a >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `${(v / 1e3).toFixed(a >= 1e4 ? 0 : 1)}K`;
  return num(v, a < 10 && a % 1 ? 1 : 0);
}

export const pct = (v, dp = 1) => (isNum(v) ? `${v.toFixed(dp)}%` : '—');
export const pctSigned = (v, dp = 1) => (isNum(v) ? `${v > 0 ? '+' : ''}${v.toFixed(dp)}%` : '—');

/** Format a value by a format key sent from the backend (charts and table columns). */
export function formatValue(v, fmt) {
  switch (fmt) {
    case 'money': return moneyFull(v);
    case 'money_short': return money(v);
    case 'int': case 'bold_int': return num(v, 0);
    case 'num': return num(v, 1);
    case 'num2': return num(v, 2);
    case 'pct': return pct(v, 1);
    case 'pct0': return pct(v, 0);
    case 'pct2': return pct(v, 2);
    case 'pct_signed': return pctSigned(v, 1);
    case 'days': return isNum(v) ? `${num(v, 0)} days` : '—';
    default: return v === null || v === undefined || v === '' ? '—' : String(v);
  }
}

/** Short axis / bar-label formatter. */
export function formatShort(v, fmt) {
  if (!isNum(v)) return '';
  if (fmt === 'money') return money(v);
  if (fmt === 'pct' || fmt === 'pct0') return `${v.toFixed(v >= 10 || fmt === 'pct0' ? 0 : 1)}%`;
  if (fmt === 'pct_signed') return pctSigned(v, 0);
  if (fmt === 'num2') return v.toFixed(2);
  return compact(v);
}

export function toCsv(columns, rows) {
  const esc = (v) => {
    const s = v === null || v === undefined ? '' : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const head = columns.map((c) => esc(c.label)).join(',');
  const body = rows.map((r) => columns.map((c) => esc(r[c.key])).join(',')).join('\n');
  return `${head}\n${body}`;
}

export function downloadText(filename, text) {
  const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
