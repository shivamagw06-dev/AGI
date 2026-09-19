import { useCallback, useEffect, useState } from 'react';
import { Download, FileSpreadsheet, RefreshCw } from 'lucide-react';
import { API_ORIGIN } from '@/config';
import './valuationRatiosWorkbook.css';

const BASE = `${API_ORIGIN || ''}/api/intelligence/valuation-ratios/workbook`;

const TABS = [
  ['P-E', 'Price to earnings'],
  ['P-B', 'Price to book'],
  ['ROA', 'Return on assets'],
  ['ROE', 'Return on equity'],
  ['ROCE', 'Return on capital employed'],
  ['EV-EBITDA', 'Enterprise value to EBITDA'],
  ['Coverage', 'Ratios collected per company per day'],
];

const RANGES = [
  [30, '30 days'],
  [120, '120 days'],
  [250, '1 year'],
  [500, 'Max'],
];

function fmt(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return Number(value).toLocaleString();
}

function Stat({ label, value, hint }) {
  return (
    <div className="vrw-stat">
      <span className="vrw-stat-label">{label}</span>
      <span className="vrw-stat-value">{value}</span>
      {hint ? <span className="vrw-stat-hint">{hint}</span> : null}
    </div>
  );
}

export default function ValuationRatiosWorkbook() {
  const [days, setDays] = useState(120);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${BASE}/summary?days=${days}`, { credentials: 'include' });
      const data = await resp.json();
      if (!resp.ok || data?.ok === false) {
        throw new Error(data?.detail || data?.error || `HTTP ${resp.status}`);
      }
      setSummary(data);
    } catch (err) {
      setError(err?.message || 'Could not reach the intelligence engine.');
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    load();
  }, [load]);

  // The file is fetched rather than linked so a failure surfaces as a message
  // on the page. A plain <a href> to a route that returns JSON on error hands
  // the browser a file called "workbook.xlsx" containing an error object,
  // which Excel then refuses to open with no explanation.
  const download = useCallback(async () => {
    setDownloading(true);
    setError(null);
    try {
      const resp = await fetch(`${BASE}?days=${days}`, { credentials: 'include' });
      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}));
        throw new Error(detail?.detail || detail?.error || `HTTP ${resp.status}`);
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `agi_valuation_ratios_${summary?.latest_date || 'latest'}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err?.message || 'Download failed.');
    } finally {
      setDownloading(false);
    }
  }, [days, summary]);

  return (
    <div className="vrw">
      <header className="vrw-head">
        <div>
          <h1>
            <FileSpreadsheet size={20} /> Valuation Ratios Workbook
          </h1>
          <p className="vrw-sub">
            Six ratios from Upstox plus a coverage sheet. Companies down column A, collection
            dates across, newest first. Built from the warehouse on request, so it is never
            stale.
          </p>
        </div>
        <button type="button" className="vrw-ghost" onClick={load} disabled={loading}>
          <RefreshCw size={15} className={loading ? 'vrw-spin' : undefined} /> Refresh
        </button>
      </header>

      {error ? <div className="vrw-error">{error}</div> : null}

      <div className="vrw-range">
        {RANGES.map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={value === days ? 'vrw-chip vrw-chip-on' : 'vrw-chip'}
            onClick={() => setDays(value)}
          >
            {label}
          </button>
        ))}
      </div>

      <section className="vrw-stats">
        <Stat label="Companies" value={fmt(summary?.companies)} hint="every eligible equity" />
        <Stat label="Collection dates" value={fmt(summary?.dates)} hint="from the data, not a calendar" />
        <Stat label="Latest date" value={summary?.latest_date || '—'} />
        <Stat
          label="Collected that day"
          value={fmt(summary?.companies_on_latest_date)}
          hint="companies with at least one ratio"
        />
        <Stat label="Values" value={fmt(summary?.values)} />
        <Stat
          label="File size"
          value={summary?.bytes ? `${(summary.bytes / 1e6).toFixed(1)} MB` : '—'}
        />
      </section>

      <button type="button" className="vrw-download" onClick={download} disabled={downloading || !summary}>
        <Download size={16} />
        {downloading ? 'Building the workbook…' : 'Download .xlsx'}
      </button>

      <section className="vrw-tabs">
        <h2>Seven tabs</h2>
        <ol>
          {TABS.map(([name, meaning]) => (
            <li key={name}>
              <code>{name}</code>
              <span>{meaning}</span>
            </li>
          ))}
        </ol>
        <p className="vrw-note">
          Six ratio tabs because six is what the provider returns. On the Coverage tab a cell is
          how many ratios landed that day: <strong>0</strong> means the sweep missed the company,
          and <strong>4</strong> against a bank is correct rather than short, since ROCE and
          EV/EBITDA do not exist for a lender.
        </p>
      </section>
    </div>
  );
}
