import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Pause, Play, RefreshCw, Search } from 'lucide-react';
import {
  getHvieBands,
  getHvieCompany,
  getHvieCoverageDashboard,
  getHvieHealth,
  getHviePercentiles,
  getHvieRegimes,
  getHvieRerating,
  getHvieRuntimeStatus,
  postHvieRuntimeRun,
  postHvieRuntimeStart,
  postHvieRuntimeStop,
} from '@/lib/intelligenceApi';
import './valuationPolicy.css';

function Stat({ label, value, hint }) {
  return (
    <div className="vp-stat">
      <span className="label">{label}</span>
      <span className="value">{value ?? '—'}</span>
      {hint ? <span className="vp-muted" style={{ fontSize: '0.75rem' }}>{hint}</span> : null}
    </div>
  );
}

function fmt(n, d = 2) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: d });
}

export default function HistoricalValuation() {
  const [symbol, setSymbol] = useState('INFY');
  const [metric, setMetric] = useState('pe');
  const [window, setWindow] = useState('10y');
  const [pack, setPack] = useState(null);
  const [extra, setExtra] = useState({});
  const [health, setHealth] = useState(null);
  const [runtime, setRuntime] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [note, setNote] = useState(null);

  const refreshRuntime = useCallback(async () => {
    try {
      const [h, st, dash] = await Promise.all([
        getHvieHealth(),
        getHvieRuntimeStatus(),
        getHvieCoverageDashboard({ limit: 80 }),
      ]);
      setHealth(h);
      setRuntime(st);
      setDashboard(dash);
    } catch (err) {
      setError(err.message || 'runtime_status_failed');
    }
  }, []);

  useEffect(() => {
    refreshRuntime();
    const id = setInterval(refreshRuntime, 8000);
    return () => clearInterval(id);
  }, [refreshRuntime]);

  const load = useCallback(async () => {
    const sym = String(symbol || '').trim().toUpperCase();
    if (!sym) return;
    setLoading(true);
    try {
      const [company, bands, pct, regimes, rerating] = await Promise.all([
        getHvieCompany(sym, { metric, window }),
        getHvieBands(sym, { metric, window }),
        getHviePercentiles(sym, { metric }),
        getHvieRegimes(sym, { metric, window }),
        getHvieRerating(sym, { metric, window }),
      ]);
      setPack(company);
      setExtra({ bands, pct, regimes, rerating });
      setError(null);
    } catch (err) {
      setError(err.message || 'hvie_failed');
    } finally {
      setLoading(false);
    }
  }, [symbol, metric, window]);

  const runMode = async (mode) => {
    setBusy(true);
    setNote(null);
    try {
      const result = await postHvieRuntimeRun({ mode, batch: mode === 'bootstrap' ? 25 : 80 });
      setNote(`${mode}: ${result.ok === false ? result.error || 'failed' : 'ok'} · attempted ${result.attempted ?? '—'}`);
      await refreshRuntime();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const rt = runtime?.runtime || health?.runtime || {};
  const counters = rt.counters || {};

  return (
    <div className="vp-root">
      <div className="vp-shell">
        <Link to="/admin" className="vp-back">
          <ArrowLeft size={14} /> Admin
        </Link>
        <p className="vp-kicker">Phase 8.3R · HVIE Continuous Runtime</p>
        <h1 className="vp-title">Historical Valuation</h1>
        <p className="vp-sub">
          Self-maintaining historical valuation service: bootstrap once, append daily after
          close, forward-rebuild on results, corporate-action rebuild when needed.
          UI renders engine outputs only — no client-side calculations.
        </p>

        <div className="vp-stats">
          <Stat label="Runtime" value={rt.status || '—'} hint={rt.mode || 'idle'} />
          <Stat label="Universe seeded" value={`${runtime?.seeded ?? health?.seeded ?? '—'} / ${runtime?.universe ?? health?.universe ?? '—'}`} />
          <Stat label="Coverage" value={runtime?.coverage_pct != null ? `${runtime.coverage_pct}%` : (health?.coverage_pct != null ? `${health.coverage_pct}%` : '—')} />
          <Stat label="Bootstrap done" value={counters.bootstrap_done ?? 0} />
          <Stat label="Daily appends" value={counters.daily_appended ?? 0} />
          <Stat label="Research events" value={counters.research_events ?? 0} />
        </div>

        <div className="vp-filters">
          <button type="button" disabled={busy} onClick={() => runMode('bootstrap')}>Bootstrap slice</button>
          <button type="button" disabled={busy} onClick={() => runMode('daily')}>Daily append</button>
          <button type="button" disabled={busy} onClick={() => runMode('weekly')}>Weekly stats</button>
          <button type="button" disabled={busy} onClick={() => runMode('monthly')}>Monthly health</button>
          <button
            type="button"
            className="ghost"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await postHvieRuntimeStart();
                setNote('Runtime loop start requested (gather worker owns heavy drain).');
                await refreshRuntime();
              } catch (err) {
                setError(err.message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <Play size={14} style={{ marginRight: 6 }} /> Start loop
          </button>
          <button
            type="button"
            className="ghost"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await postHvieRuntimeStop();
                setNote('Runtime loop stop requested.');
                await refreshRuntime();
              } catch (err) {
                setError(err.message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <Pause size={14} style={{ marginRight: 6 }} /> Stop
          </button>
          <button type="button" className="ghost" onClick={refreshRuntime}>
            <RefreshCw size={14} style={{ marginRight: 6 }} /> Refresh
          </button>
        </div>
        {note ? <p className="vp-muted">{note}</p> : null}
        <p className="vp-muted" style={{ marginBottom: '1rem' }}>
          Schedules: 18:30 IST daily append · Sunday stats · monthly health · gather-worker bootstrap drain
        </p>

        {error ? <div className="vp-error">{error}</div> : null}

        <div className="vp-filters">
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && load()}
            placeholder="Symbol"
          />
          <select value={metric} onChange={(e) => setMetric(e.target.value)}>
            <option value="pe">PE</option>
            <option value="pb">PB</option>
            <option value="ev_ebitda">EV/EBITDA</option>
            <option value="ev_sales">EV/Sales</option>
            <option value="dividend_yield">Dividend Yield</option>
          </select>
          <select value={window} onChange={(e) => setWindow(e.target.value)}>
            {['1y', '3y', '5y', '10y', '15y', '20y', 'max'].map((w) => (
              <option key={w} value={w}>{w}</option>
            ))}
          </select>
          <button type="button" onClick={load}>
            <Search size={14} style={{ marginRight: 6 }} />
            {loading ? 'Loading…' : 'Lookup'}
          </button>
        </div>

        {pack?.ok ? (
          <div className="vp-table-wrap" style={{ padding: '1rem', marginBottom: '1rem' }}>
            <p className="vp-kicker">{pack.symbol} · {pack.metric?.toUpperCase()} · {window}</p>
            <div className="vp-stats" style={{ marginTop: '0.75rem' }}>
              <Stat label="Current" value={fmt(pack.current)} />
              <Stat label="Median" value={fmt(pack.median)} />
              <Stat label="Percentile" value={pack.historical_percentile != null ? `${fmt(pack.historical_percentile, 1)}%` : '—'} />
              <Stat label="Regime" value={pack.regime || '—'} />
              <Stat label="Confidence" value={pack.confidence || '—'} />
            </div>
            <p className="vp-muted">{pack.coverage?.coverage_label || '—'}</p>
            {extra.rerating?.ok ? <p className="vp-muted">{extra.rerating.sentence}</p> : null}
          </div>
        ) : null}

        <div className="vp-table-wrap">
          <table className="vp-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Status</th>
                <th>Primary</th>
                <th>History</th>
                <th>Obs</th>
                <th>Regime</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {(dashboard?.rows || []).map((r) => (
                <tr
                  key={r.symbol}
                  style={{ cursor: 'pointer' }}
                  onClick={() => {
                    setSymbol(r.symbol);
                    setMetric(r.primary_metric || 'pe');
                  }}
                >
                  <td><strong>{r.symbol}</strong></td>
                  <td><span className="vp-pill">{r.status || '—'}</span></td>
                  <td>{r.primary_model || r.primary_metric || '—'}</td>
                  <td className="vp-muted">{r.price_history || '—'}</td>
                  <td>{r.observations ?? '—'}</td>
                  <td>{r.regime || '—'}</td>
                  <td>{r.confidence || '—'}</td>
                </tr>
              ))}
              {!dashboard?.rows?.length ? (
                <tr>
                  <td colSpan={7} className="vp-muted">
                    No HVIE company state yet — run Bootstrap slice or wait for gather-worker drain.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
