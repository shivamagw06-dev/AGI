import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CalendarRange,
  Database,
  Layers,
  Play,
  RefreshCw,
  Search,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  getBackfillJobs,
  getBackfillStatus,
  getHistoricalCoverage,
  getSeries,
  getSymbolCoverage,
  runBackfill,
  setWarehouseActor,
} from '@/lib/warehouseApi';
import './dataWarehouse.css';
import './historicalCoverage.css';

const STAGES = [
  { id: 'nse_archive', label: 'NSE archive' },
  { id: 'yahoo_prices', label: 'Yahoo prices' },
  { id: 'yahoo_statements', label: 'Statements' },
  { id: 'valuation_history', label: 'Valuation history' },
];

const TIER_ORDER = ['20y+', '10-20y', '5-10y', '1-5y', '<1y'];

function Sparkline({ points, height = 40 }) {
  const path = useMemo(() => {
    const values = (points || []).map((p) => p.value).filter((v) => v != null);
    if (values.length < 2) return null;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const step = 100 / (values.length - 1);
    return values
      .map((v, i) => `${i === 0 ? 'M' : 'L'} ${(i * step).toFixed(2)} ${(100 - ((v - min) / span) * 100).toFixed(2)}`)
      .join(' ');
  }, [points]);

  if (!path) return <span className="hc-muted">not enough history</span>;
  return (
    <svg className="hc-spark" viewBox="0 0 100 100" preserveAspectRatio="none" style={{ height }}>
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export default function HistoricalCoverage() {
  const { user } = useAuth() || {};
  const [board, setBoard] = useState(null);
  const [status, setStatus] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [note, setNote] = useState(null);
  const [stages, setStages] = useState(STAGES.map((s) => s.id));
  const [companies, setCompanies] = useState(25);
  const [days, setDays] = useState(60);
  const [probe, setProbe] = useState('');
  const [probeResult, setProbeResult] = useState(null);

  useEffect(() => {
    setWarehouseActor(user?.email || user?.id || 'admin');
  }, [user]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [coverage, engineStatus, jobList] = await Promise.all([
        getHistoricalCoverage(20),
        getBackfillStatus(),
        getBackfillJobs(8),
      ]);
      setBoard(coverage);
      setStatus(engineStatus);
      setJobs(jobList?.jobs || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const start = async () => {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const result = await runBackfill({ stages, companies: Number(companies), days: Number(days) });
      if (result?.error === 'worker_only') {
        setNote('Backfill runs on the gather worker. This environment refused it deliberately.');
      } else if (result?.ok === false) {
        setNote(`Finished with errors: ${(result.errors || []).map((e) => e.stage).join(', ')}`);
      } else {
        setNote('Backfill slice complete. Progress is checkpointed — run again to continue.');
      }
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const inspect = async (event) => {
    event.preventDefault();
    const symbol = probe.trim().toUpperCase();
    if (!symbol) return;
    try {
      const [cov, series] = await Promise.all([
        getSymbolCoverage(symbol),
        getSeries(symbol, 'price', { window: 'max', limit: 400 }),
      ]);
      setProbeResult({ symbol, coverage: cov, series });
    } catch (err) {
      setError(err.message);
    }
  };

  const summary = board?.summary;
  const tiers = summary?.tiers || {};

  return (
    <div className="wh-root hc-root">
      <header className="wh-top">
        <div className="wh-top-left">
          <Link to="/admin/data-warehouse" className="wh-back">
            <ArrowLeft size={13} /> Warehouse
          </Link>
          <h1>
            <CalendarRange size={16} /> Historical Coverage
          </h1>
          <span className="wh-sub">
            {summary
              ? `${summary.companies_with_history?.toLocaleString()} of ${summary.universe?.toLocaleString()} companies · ${summary.avg_years}y average`
              : 'loading…'}
          </span>
        </div>
        <div className="wh-top-actions">
          <button type="button" className="wh-btn" onClick={load} disabled={loading}>
            <RefreshCw size={13} /> Reload
          </button>
        </div>
      </header>

      {error ? <div className="wh-error wh-error-bar">{error}</div> : null}
      {note ? <div className="wh-status-bar">{note}</div> : null}

      <div className="hc-body">
        <section className="hc-stats">
          {[
            ['Companies with history', summary?.companies_with_history],
            ['Deep (10y+)', summary?.companies_deep_10y],
            ['Coverage', summary ? `${summary.coverage_pct}%` : null],
            ['Deep coverage', summary ? `${summary.deep_coverage_pct}%` : null],
            ['Average years', summary?.avg_years],
            ['Deepest', summary ? `${summary.max_years}y` : null],
            ['Oldest date', summary?.oldest],
            ['Total rows', summary?.rows_total?.toLocaleString?.()],
          ].map(([label, value]) => (
            <div key={label} className="hc-stat">
              <span className="label">{label}</span>
              <span className="value">{value ?? '—'}</span>
            </div>
          ))}
        </section>

        <section className="hc-panel">
          <h2>
            <Play size={13} /> Run a backfill slice
          </h2>
          <p className="wh-muted">
            Each run does a bounded slice and checkpoints it. Stop it whenever you like — the next
            run continues from the same place rather than starting again.
          </p>
          <div className="hc-controls">
            <div className="hc-stage-picker">
              {STAGES.map((stage) => (
                <label key={stage.id} className={stages.includes(stage.id) ? 'is-on' : ''}>
                  <input
                    type="checkbox"
                    checked={stages.includes(stage.id)}
                    onChange={(event) =>
                      setStages((prev) =>
                        event.target.checked
                          ? [...prev, stage.id]
                          : prev.filter((id) => id !== stage.id),
                      )
                    }
                  />
                  {stage.label}
                </label>
              ))}
            </div>
            <label className="hc-num">
              Companies
              <input type="number" min="1" max="500" value={companies}
                     onChange={(e) => setCompanies(e.target.value)} />
            </label>
            <label className="hc-num">
              Trading days
              <input type="number" min="1" max="2000" value={days}
                     onChange={(e) => setDays(e.target.value)} />
            </label>
            <button type="button" className="wh-btn wh-btn-primary" disabled={busy} onClick={start}>
              {busy ? 'Running…' : 'Run slice'}
            </button>
          </div>
          {status?.worker_gate && status.worker_gate.ok === false ? (
            <p className="hc-gate">
              <AlertTriangle size={12} /> {status.worker_gate.detail}
            </p>
          ) : null}
        </section>

        {board?.inputs ? (
          <section className="hc-panel">
            <h2>
              <AlertTriangle size={13} /> What the reconstruction could build
            </h2>
            <p className="wh-muted">{board.inputs.note}</p>
            <div className="hc-inputs">
              {[
                ['Observations', board.inputs.observations?.toLocaleString()],
                ['With P/E', `${board.inputs.with_pe_pct}%`],
                ['With P/B', `${board.inputs.with_pb_pct}%`],
                ['With market cap', `${board.inputs.with_market_cap_pct}%`],
                ['With EV/EBITDA', `${board.inputs.with_ev_ebitda_pct}%`],
                [
                  'Share count on file',
                  `${board.inputs.companies_with_share_count} of ${board.inputs.companies_with_statements}`,
                ],
              ].map(([label, value]) => (
                <div key={label} className="hc-input-stat">
                  <span className="label">{label}</span>
                  <span className="value">{value ?? '—'}</span>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        <div className="hc-grid">
          <section className="hc-panel">
            <h2>
              <Layers size={13} /> Depth distribution
            </h2>
            <div className="hc-tiers">
              {TIER_ORDER.map((tier) => {
                const count = tiers[tier] || 0;
                const total = Object.values(tiers).reduce((a, b) => a + b, 0) || 1;
                return (
                  <div key={tier} className="hc-tier">
                    <span className="tier">{tier}</span>
                    <div className="bar">
                      <span style={{ width: `${(100 * count) / total}%` }} />
                    </div>
                    <span className="count">{count}</span>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="hc-panel">
            <h2>
              <Database size={13} /> By table
            </h2>
            <table className="wh-ops-table">
              <thead>
                <tr>
                  <th>Table</th>
                  <th>Rows</th>
                  <th>Companies</th>
                  <th>Periods</th>
                  <th>Span</th>
                </tr>
              </thead>
              <tbody>
                {(board?.tables || []).map((row) => (
                  <tr key={row.table}>
                    <td>{row.table}</td>
                    <td className="is-num">{row.rows?.toLocaleString()}</td>
                    <td className="is-num">{row.companies?.toLocaleString()}</td>
                    <td className="is-num">{row.periods?.toLocaleString()}</td>
                    <td>{row.first ? `${row.first} → ${row.last}` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>

        <div className="hc-grid">
          <section className="hc-panel">
            <h2>Deepest histories</h2>
            <table className="wh-ops-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Years</th>
                  <th>Points</th>
                  <th>From</th>
                </tr>
              </thead>
              <tbody>
                {(board?.deepest || []).slice(0, 12).map((row) => (
                  <tr key={row.symbol}>
                    <td>{row.symbol}</td>
                    <td className="is-num">{row.years}</td>
                    <td className="is-num">{row.points?.toLocaleString()}</td>
                    <td>{row.first}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="hc-panel">
            <h2>By sector</h2>
            <table className="wh-ops-table">
              <thead>
                <tr>
                  <th>Sector</th>
                  <th>Companies</th>
                  <th>Avg years</th>
                  <th>10y+</th>
                </tr>
              </thead>
              <tbody>
                {(board?.sectors || []).slice(0, 12).map((row) => (
                  <tr key={row.sector}>
                    <td>{row.sector}</td>
                    <td className="is-num">{row.companies}</td>
                    <td className="is-num">{row.avg_years}</td>
                    <td className="is-num">{row.deep_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>

        <section className="hc-panel">
          <h2>
            <Search size={13} /> Inspect a company
          </h2>
          <form className="hc-probe" onSubmit={inspect}>
            <input
              value={probe}
              placeholder="Symbol, for example RELIANCE"
              onChange={(event) => setProbe(event.target.value)}
            />
            <button type="submit" className="wh-btn">
              Inspect
            </button>
          </form>
          {probeResult ? (
            <div className="hc-probe-result">
              <div className="hc-probe-head">
                <strong>{probeResult.symbol}</strong>
                <span className="wh-muted">
                  {probeResult.coverage?.price_years ?? 0} years of price history
                </span>
              </div>
              <Sparkline points={probeResult.series?.points} />
              {probeResult.series?.stats ? (
                <div className="hc-probe-stats">
                  <span>first {probeResult.series.stats.first}</span>
                  <span>last {probeResult.series.stats.last}</span>
                  <span>CAGR {probeResult.series.stats.cagr_pct ?? '—'}%</span>
                  <span>low {probeResult.series.stats.min}</span>
                  <span>high {probeResult.series.stats.max}</span>
                </div>
              ) : null}
              <table className="wh-ops-table">
                <tbody>
                  {Object.entries(probeResult.coverage?.tabs || {}).map(([tab, entry]) => (
                    <tr key={tab}>
                      <td>{tab}</td>
                      <td className="is-num">{entry.rows}</td>
                      <td>{entry.first ? `${entry.first} → ${entry.last}` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>

        <section className="hc-panel">
          <h2>
            <Activity size={13} /> Recent jobs
          </h2>
          <ul className="wh-run-list">
            {jobs.map((job) => (
              <li key={job.id} className={job.status === 'done' ? 'is-ok' : 'is-bad'}>
                <div className="wh-run-head">
                  <strong>{job.status}</strong>
                  <span>{new Date(job.created_at).toLocaleString()}</span>
                </div>
                <div className="wh-muted">
                  {job.actor} · {(job.params?.stages || []).join(' → ')}
                </div>
                {job.error ? <div className="hc-job-error">{job.error}</div> : null}
              </li>
            ))}
            {!jobs.length ? <li className="wh-muted">No backfill has run yet.</li> : null}
          </ul>
        </section>

        {status?.failures?.length ? (
          <section className="hc-panel">
            <h2>
              <AlertTriangle size={13} /> Failures worth attention
            </h2>
            <table className="wh-ops-table">
              <thead>
                <tr>
                  <th>Stage</th>
                  <th>Symbol</th>
                  <th>Attempts</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {status.failures.slice(0, 15).map((row) => (
                  <tr key={`${row.kind}-${row.entity}`}>
                    <td>{row.kind}</td>
                    <td>{row.entity}</td>
                    <td className="is-num">{row.attempts}</td>
                    <td className="hc-err">{row.last_error}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : null}
      </div>
    </div>
  );
}
