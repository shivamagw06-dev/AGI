import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Pause, Play, RefreshCw, Search, Zap } from 'lucide-react';
import {
  getCompanyFinancialCoverage,
  getFinancialAudit,
  getUpstoxFillBoard,
  getYahooFillBoard,
  postYahooFillStop,
} from '@/lib/warehouseApi';
import {
  getUpstoxEmptyFillStatus,
  runUpstoxEmptyFill,
  startUpstoxEmptyFill,
  stopUpstoxEmptyFill,
} from '@/lib/uifiApi';
import './valuationPolicy.css';

function fmt(n, d = 0) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: d });
}

function Stat({ label, value, hint, tone }) {
  return (
    <div className={`vp-stat ${tone || ''}`}>
      <span className="label">{label}</span>
      <span className="value">{value ?? '—'}</span>
      {hint ? <span className="vp-muted" style={{ fontSize: '0.75rem' }}>{hint}</span> : null}
    </div>
  );
}

function Histogram({ rows, valueKey = 'companies', labelKey }) {
  const max = Math.max(1, ...(rows || []).map((r) => Number(r[valueKey] || 0)));
  return (
    <div style={{ display: 'grid', gap: '0.45rem' }}>
      {(rows || []).map((row) => {
        const label = row[labelKey] ?? row.years ?? row.bucket;
        const value = Number(row[valueKey] || 0);
        return (
          <div key={String(label)} style={{ display: 'grid', gridTemplateColumns: '4.5rem 1fr 3.5rem', gap: '0.5rem', alignItems: 'center' }}>
            <span className="vp-muted" style={{ fontSize: '0.8rem' }}>{label}</span>
            <div style={{ height: 10, background: 'var(--vp-line)', borderRadius: 2, overflow: 'hidden' }}>
              <div style={{ width: `${(value / max) * 100}%`, height: '100%', background: 'var(--vp-accent)' }} />
            </div>
            <span style={{ fontSize: '0.8rem', textAlign: 'right' }}>{fmt(value)}</span>
          </div>
        );
      })}
    </div>
  );
}

const CLASS_TONE = {
  COMPLETE_10Y: 'ok',
  GOOD: '',
  PARTIAL: 'warn',
  MINIMAL: 'warn',
  EMPTY: 'bad',
};

export default function FinancialCoverage() {
  const [board, setBoard] = useState(null);
  const [yahoo, setYahoo] = useState(null);
  const [upstox, setUpstox] = useState(null);
  const [upstoxBoard, setUpstoxBoard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('');
  const [classFilter, setClassFilter] = useState('ALL');
  const [probe, setProbe] = useState('');
  const [probeResult, setProbeResult] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [data, yb, ub, us] = await Promise.all([
        getFinancialAudit(),
        getYahooFillBoard().catch(() => null),
        getUpstoxFillBoard().catch(() => null),
        getUpstoxEmptyFillStatus().catch(() => null),
      ]);
      setBoard(data);
      setYahoo(yb);
      setUpstoxBoard(ub);
      setUpstox(us);
      setError(null);
    } catch (err) {
      setError(String(err?.message || err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(() => {
      getUpstoxEmptyFillStatus().then(setUpstox).catch(() => {});
      getYahooFillBoard().then(setYahoo).catch(() => {});
    }, 15000);
    return () => clearInterval(id);
  }, [refresh]);

  const upstoxAct = async (label, fn) => {
    setBusy(true);
    setNote(null);
    try {
      // Pause Yahoo worker if still spinning — Upstox is the Render path.
      await postYahooFillStop().catch(() => null);
      const out = await fn();
      if (out?.already_running) {
        setNote('AGI statement fill already running — EMPTY INE* equities are being written.');
      } else if (out?.ok === false) {
        setNote(`${label} failed: ${out.error || 'unknown'}`);
      } else if (label === 'run') {
        const b = out?.batch || {};
        setNote(`AGI batch: ${b.filled ?? 0} filled, ${b.failed ?? 0} failed, ${b.ingest_rows ?? 0} rows.`);
      } else {
        setNote(
          label === 'start'
            ? 'AGI statement fill started for eligible annual and quarterly records.'
            : 'AGI statement fill paused.',
        );
      }
      setUpstox(await getUpstoxEmptyFillStatus().catch(() => out));
      setUpstoxBoard(await getUpstoxFillBoard().catch(() => null));
    } catch (err) {
      setError(String(err?.message || err));
    } finally {
      setBusy(false);
    }
  };

  const summary = board?.summary || {};
  const annual = summary.annual || {};
  const quarterly = summary.quarterly || {};
  const classification = summary.classification || {};

  const importRows = useMemo(() => {
    let rows = board?.companies_requiring_import || [];
    if (classFilter !== 'ALL') {
      rows = rows.filter((r) => r.classification === classFilter);
    }
    const q = filter.trim().toUpperCase();
    if (q) {
      rows = rows.filter((r) =>
        String(r.symbol || '').includes(q)
        || String(r.company_name || '').toUpperCase().includes(q)
        || String(r.sector || '').toUpperCase().includes(q));
    }
    return rows;
  }, [board, filter, classFilter]);

  const inspect = async (event) => {
    event.preventDefault();
    const symbol = probe.trim().toUpperCase();
    if (!symbol) return;
    try {
      const cov = await getCompanyFinancialCoverage(symbol);
      setProbeResult(cov);
      setError(null);
    } catch (err) {
      setError(String(err?.message || err));
    }
  };

  return (
    <div className="vp-root">
      <div className="vp-shell">
        <Link to="/admin" className="vp-back"><ArrowLeft size={16} /> Admin</Link>

        <p className="vp-kicker">AGI coverage audit and statement fill</p>
        <h1 className="vp-title">Financial Coverage Audit</h1>
        <p className="vp-sub">
          Measures warehouse depth, then fills EMPTY / thin equities from{' '}
          <strong>AGI fundamentals</strong> by ISIN
          (<code>/fundamentals/&#123;isin&#125;/income-statement</code> + balance-sheet + cash-flow).
          AGI automatically selects the available production feed.
          AGI long-history records provide complete depth.
        </p>

        <div className="hr-actions">
          <button
            type="button"
            className="hr-btn primary"
            disabled={busy || upstox?.runtime?.status === 'running'}
            onClick={() => upstoxAct('start', () => startUpstoxEmptyFill({ batch: 10, concurrency: 2, include_thin: true }))}
          >
            <Play size={14} /> Start AGI fill
          </button>
          <button
            type="button"
            className="hr-btn"
            disabled={busy || upstox?.runtime?.status !== 'running'}
            onClick={() => upstoxAct('stop', () => stopUpstoxEmptyFill())}
          >
            <Pause size={14} /> Pause
          </button>
          <button
            type="button"
            className="hr-btn"
            disabled={busy}
            onClick={() => upstoxAct('run', () => runUpstoxEmptyFill({ batch: 5 }))}
          >
            <Zap size={14} /> Run 5 now
          </button>
          <button type="button" className="hr-btn" disabled={loading} onClick={refresh}>
            <RefreshCw size={14} /> {loading ? 'Scanning…' : 'Re-run audit'}
          </button>
          <Link to="/admin/upstox-fundamentals" className="hr-btn">AGI Fundamentals →</Link>
          <Link to="/admin/financial-warehouse" className="hr-btn">Import runtime →</Link>
        </div>

        {note ? <p className="hr-note">{note}</p> : null}
        {error ? <p className="vp-error">{error}</p> : null}
        {yahoo?.diagnosis ? (
          <p className="vp-error" style={{ marginTop: '0.75rem' }}>
            Yahoo note: {yahoo.diagnosis} Use <strong>Start AGI fill</strong> instead.
          </p>
        ) : null}
        {upstox?.plain_english || upstoxBoard?.plain_english ? (
          <p className="vp-sub" style={{ marginTop: '0.75rem' }}>
            AGI worker: <strong>{upstox?.runtime?.status || 'idle'}</strong>
            {' · '}filled {fmt(upstox?.runtime?.filled)} / processed {fmt(upstox?.runtime?.processed)}
            {' · '}failed {fmt(upstox?.runtime?.failed)}
            {' · '}EMPTY+INE waiting {fmt(upstoxBoard?.progress?.empty)}
            {' · '}{upstoxBoard?.plain_english || upstox?.plain_english}
          </p>
        ) : null}
        {(upstox?.recent || []).length ? (
          <div className="vp-panel" style={{ marginTop: '0.75rem' }}>
            <h2 className="vp-h2">Recent AGI fill batches</h2>
            <ul className="vp-muted" style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.8rem' }}>
              {upstox.recent.slice(0, 8).map((e) => (
                <li key={`${e.at}-${e.event}`}>
                  {e.event}: filled {e.filled ?? '—'} / failed {e.failed ?? '—'}
                  {e.error ? ` — ${e.error}` : ''}
                  {Array.isArray(e.symbols) ? ` [${e.symbols.slice(0, 5).join(', ')}]` : ''}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {board?.plain_english ? (
          <p className="vp-sub" style={{ marginTop: '0.5rem' }}>{board.plain_english}</p>
        ) : null}

        <div className="vp-stats">
          <Stat label="Universe" value={fmt(summary.universe)} hint={`ISIN ${fmt(summary.isin_pct, 1)}%`} />
          <Stat
            label="≥10y annual"
            value={`${fmt(annual.ge10_years)} (${fmt(annual.ge10_pct, 1)}%)`}
            tone={annual.ge10_pct >= 80 ? 'ok' : annual.ge10_pct >= 40 ? 'warn' : 'bad'}
          />
          <Stat
            label="≥8y annual"
            value={`${fmt(annual.ge8_years)} (${fmt(annual.ge8_pct, 1)}%)`}
          />
          <Stat
            label="≥40 quarters"
            value={`${fmt(quarterly.ge40_quarters)} (${fmt(quarterly.ge40_pct, 1)}%)`}
            tone={quarterly.ge40_pct >= 80 ? 'ok' : quarterly.ge40_pct >= 40 ? 'warn' : 'bad'}
          />
          <Stat
            label="<5y annual"
            value={`${fmt(annual.lt5_years)} (${fmt(annual.lt5_pct, 1)}%)`}
            tone="warn"
          />
          <Stat
            label="No statements"
            value={`${fmt(summary.no_statements)} (${fmt(summary.no_statements_pct, 1)}%)`}
            tone="bad"
          />
          <Stat
            label="Need backfill"
            value={`${fmt(summary.need_backfill)} (${fmt(summary.need_backfill_pct, 1)}%)`}
            hint={`Bottleneck: ${summary.bottleneck || '—'}`}
          />
          <Stat
            label="Share count"
            value={`${fmt(summary.share_count?.companies_with_any)} (${fmt(summary.share_count?.pct, 1)}%)`}
          />
        </div>

        <div className="vp-stats" style={{ marginTop: 0 }}>
          {['COMPLETE_10Y', 'GOOD', 'PARTIAL', 'MINIMAL', 'EMPTY'].map((klass) => (
            <Stat
              key={klass}
              label={klass.replace('_', ' ')}
              value={fmt(classification[klass])}
              hint={`${fmt(summary.classification_pct?.[klass], 1)}%`}
              tone={CLASS_TONE[klass]}
            />
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', margin: '1.5rem 0' }}>
          <section className="vp-panel">
            <h2 className="vp-h2">Annual years histogram</h2>
            <Histogram rows={board?.annual_histogram} labelKey="years" />
          </section>
          <section className="vp-panel">
            <h2 className="vp-h2">Quarterly histogram</h2>
            <Histogram rows={board?.quarterly_histogram} labelKey="bucket" />
          </section>
        </div>

        <section className="vp-panel" style={{ marginBottom: '1.5rem' }}>
          <h2 className="vp-h2">Missing fields (companies with zero presence on annuals)</h2>
          <div className="vp-table-wrap">
            <table className="vp-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Missing entirely</th>
                  <th>% of universe</th>
                  <th>Sparse (&lt;50% rows)</th>
                </tr>
              </thead>
              <tbody>
                {(board?.missing_fields || []).map((row) => (
                  <tr key={row.field}>
                    <td>{row.field}</td>
                    <td>{fmt(row.companies_missing_entirely)}</td>
                    <td>{fmt(row.missing_entirely_pct, 1)}%</td>
                    <td>{fmt(row.companies_sparse)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="vp-panel" style={{ marginBottom: '1.5rem' }}>
          <h2 className="vp-h2">Coverage by sector</h2>
          <div className="vp-table-wrap">
            <table className="vp-table">
              <thead>
                <tr>
                  <th>Sector</th>
                  <th>Companies</th>
                  <th>10Y Complete</th>
                  <th>Good</th>
                  <th>Partial+</th>
                  <th>Empty</th>
                  <th>≥10y %</th>
                  <th>≥40q %</th>
                </tr>
              </thead>
              <tbody>
                {(board?.by_sector || []).slice(0, 40).map((row) => (
                  <tr key={row.sector}>
                    <td>{row.sector}</td>
                    <td>{fmt(row.companies)}</td>
                    <td>{fmt(row.complete_10y)}</td>
                    <td>{fmt(row.good)}</td>
                    <td>{fmt((row.partial || 0) + (row.minimal || 0))}</td>
                    <td>{fmt(row.empty)}</td>
                    <td>{fmt(row.ge10_annual_pct, 1)}%</td>
                    <td>{fmt(row.ge40_quarters_pct, 1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="vp-panel" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'end', marginBottom: '0.75rem' }}>
            <h2 className="vp-h2" style={{ margin: 0, flex: 1 }}>Companies requiring import</h2>
            <label className="vp-muted" style={{ fontSize: '0.8rem' }}>
              Class{' '}
              <select value={classFilter} onChange={(e) => setClassFilter(e.target.value)}>
                <option value="ALL">All needing backfill</option>
                <option value="EMPTY">EMPTY</option>
                <option value="MINIMAL">MINIMAL</option>
                <option value="PARTIAL">PARTIAL</option>
                <option value="GOOD">GOOD</option>
              </select>
            </label>
            <label className="vp-muted" style={{ fontSize: '0.8rem', display: 'flex', gap: 6, alignItems: 'center' }}>
              <Search size={14} />
              <input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Symbol / sector"
                style={{ minWidth: 160 }}
              />
            </label>
          </div>
          <div className="vp-table-wrap">
            <table className="vp-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Name</th>
                  <th>Sector</th>
                  <th>Class</th>
                  <th>Annual</th>
                  <th>Range</th>
                  <th>Quarters</th>
                  <th>Shares</th>
                  <th>Missing fields</th>
                </tr>
              </thead>
              <tbody>
                {importRows.slice(0, 200).map((row) => (
                  <tr key={row.symbol}>
                    <td>{row.symbol}</td>
                    <td>{row.company_name || '—'}</td>
                    <td>{row.sector}</td>
                    <td>{row.classification}</td>
                    <td>{fmt(row.annual_years)}</td>
                    <td>
                      {row.annual_earliest && row.annual_latest
                        ? `${row.annual_earliest}–${row.annual_latest}`
                        : '—'}
                    </td>
                    <td>{fmt(row.quarters)}</td>
                    <td>{row.has_share_count ? 'yes' : 'no'}</td>
                    <td className="vp-muted" style={{ fontSize: '0.75rem' }}>
                      {(row.missing_fields || []).slice(0, 5).join(', ') || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="vp-muted" style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
            Showing {Math.min(importRows.length, 200)} of {importRows.length} filtered
            (API returns top 500 by backfill priority).
          </p>
        </section>

        <section className="vp-panel">
          <h2 className="vp-h2">Company probe</h2>
          <form onSubmit={inspect} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <input
              value={probe}
              onChange={(e) => setProbe(e.target.value)}
              placeholder="RELIANCE"
              style={{ minWidth: 160 }}
            />
            <button type="submit" className="hr-btn">Inspect</button>
          </form>
          {probeResult ? (
            <pre className="vp-pre" style={{ fontSize: '0.75rem', overflow: 'auto', maxHeight: 360 }}>
              {JSON.stringify(probeResult.audit || probeResult, null, 2)}
            </pre>
          ) : null}
        </section>

        {board?.checked_at ? (
          <p className="vp-muted" style={{ marginTop: '1.5rem', fontSize: '0.75rem' }}>
            Checked at {board.checked_at} · read-only · modifies_data={String(board.modifies_data)}
          </p>
        ) : null}
      </div>
    </div>
  );
}
