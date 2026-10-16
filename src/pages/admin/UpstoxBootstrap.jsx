import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
} from 'lucide-react';
import {
  getUpstoxBootstrapFailures,
  getUpstoxBootstrapMissingIsin,
  getUpstoxBootstrapStatus,
  resetUpstoxBootstrap,
  startUpstoxBootstrap,
  stopUpstoxBootstrap,
} from '@/lib/upstoxBootstrapApi';
import './upstoxBootstrap.css';

function fmt(n, digits = 0) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits > 0 ? Math.min(digits, 1) : 0,
  });
}

function Stat({ label, value, hint }) {
  return (
    <div className="ub-stat">
      <span className="label">{label}</span>
      <span className="value">{value}</span>
      {hint ? <span className="ub-muted">{hint}</span> : null}
    </div>
  );
}

export default function UpstoxBootstrap() {
  const [status, setStatus] = useState(null);
  const [missing, setMissing] = useState([]);
  const [failures, setFailures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [note, setNote] = useState(null);

  const load = useCallback(async () => {
    try {
      const [st, miss, fail] = await Promise.all([
        getUpstoxBootstrapStatus(),
        getUpstoxBootstrapMissingIsin(80),
        getUpstoxBootstrapFailures(80),
      ]);
      setStatus(st);
      setMissing(miss?.rows || []);
      setFailures(fail?.rows || []);
      setError(null);
    } catch (err) {
      setError(err.message || 'status_failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 4000);
    return () => clearInterval(id);
  }, [load]);

  const running = status?.status === 'running';

  const onStart = async ({ reset = false } = {}) => {
    setBusy(true);
    setNote(null);
    try {
      const result = await startUpstoxBootstrap({
        reset,
        batchSize: 40,
        concurrency: 3,
        pauseMs: 2000,
      });
      setNote(result.ok ? 'Bootstrap started — draining ISIN queue in batches of 40.' : result.error);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onStop = async () => {
    setBusy(true);
    try {
      await stopUpstoxBootstrap();
      setNote('Bootstrap stop requested.');
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onReset = async () => {
    if (!window.confirm('Reset bootstrap queue state? Completed progress will be cleared.')) return;
    setBusy(true);
    try {
      await resetUpstoxBootstrap();
      setNote('Bootstrap state reset.');
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const summary = status?.summary || {};
  const queue = status?.queue || {};
  const api = status?.apiHealth || {};
  const thr = status?.throughput || {};
  const coverage = Number(summary.coverage || 0);
  const logs = status?.recentLog || [];

  return (
    <div className="ub-root">
      <div className="ub-shell">
        <header className="ub-header">
          <div>
            <Link to="/admin/data-warehouse" className="ub-back">
              <ArrowLeft size={14} /> Data Warehouse
            </Link>
            <p className="ub-kicker">Phase 7.4d · Admin only</p>
            <h1 className="ub-title">AGI Valuation Bootstrap</h1>
            <p className="ub-sub">
              One-shot full-universe ISIN → AGI key ratios → quality validation → warehouse → Unified Valuation Engine.
              Nightly 18:15 IST stays incremental; this bootstrap is not a permanent scheduler.
            </p>
          </div>
          <div className="ub-actions">
            <button type="button" className="ub-btn ghost" onClick={load} disabled={busy}>
              <RefreshCw size={14} /> Refresh
            </button>
            {!running ? (
              <button type="button" className="ub-btn primary" onClick={() => onStart({ reset: false })} disabled={busy}>
                <Play size={14} /> Start / Resume
              </button>
            ) : (
              <button type="button" className="ub-btn danger" onClick={onStop} disabled={busy}>
                <Pause size={14} /> Stop
              </button>
            )}
            <button type="button" className="ub-btn" onClick={() => onStart({ reset: true })} disabled={busy || running}>
              <RotateCcw size={14} /> Restart fresh
            </button>
            <button type="button" className="ub-btn" onClick={onReset} disabled={busy || running}>
              Reset state
            </button>
          </div>
        </header>

        {error ? <div className="ub-error">{error}</div> : null}
        {note ? <p className="ub-muted">{note}</p> : null}
        {loading && !status ? <p className="ub-muted">Loading bootstrap status…</p> : null}

        {status ? (
          <>
            <div className="ub-stats">
              <Stat label="Status" value={<span className={`ub-badge ${status.status || 'idle'}`}>{status.status || 'idle'}</span>} />
              <Stat label="Companies" value={fmt(summary.companies)} />
              <Stat label="ISIN available" value={fmt(summary.isinAvailable)} />
              <Stat label="Completed" value={fmt(summary.completed)} />
              <Stat label="Running" value={fmt(summary.running)} />
              <Stat label="Remaining" value={fmt(summary.remaining)} />
              <Stat label="Coverage" value={`${fmt(coverage, 1)}%`} />
              <Stat label="ETA" value={`${fmt(summary.etaMinutes, 1)} min`} />
              <Stat label="Missing ISIN" value={fmt(summary.missingIsin)} />
            </div>

            <div className="ub-progress" title={`${coverage}%`}>
              <i style={{ width: `${Math.min(100, coverage)}%` }} />
            </div>

            <div className="ub-grid">
              <section className="ub-panel">
                <h2><Activity size={12} /> Queue status</h2>
                <div className="ub-kv">
                  {['PENDING', 'RUNNING', 'SUCCESS', 'RETRY', 'FAILED', 'SKIPPED'].flatMap((k) => ([
                    <span key={`${k}-l`}>{k}</span>,
                    <span key={`${k}-v`}>{fmt(queue[k] || 0)}</span>,
                  ]))}
                </div>
              </section>

              <section className="ub-panel">
                <h2><Activity size={12} /> API health</h2>
                <div className="ub-kv">
                  <span>Successful calls</span><span>{fmt(api.successfulCalls)}</span>
                  <span>Failures</span><span>{fmt(api.failures)}</span>
                  <span>429 count</span><span>{fmt(api.http429)}</span>
                  <span>Retry count</span><span>{fmt(api.retryCount)}</span>
                  <span>Avg latency</span><span>{fmt(api.averageLatencyMs)} ms</span>
                  <span>Success %</span><span>{fmt(api.successPct, 1)}%</span>
                  <span>Batch size</span><span>{fmt(api.currentBatchSize)}</span>
                  <span>Last success batch</span><span>{api.lastSuccessfulBatchAt ? new Date(api.lastSuccessfulBatchAt).toLocaleTimeString() : '—'}</span>
                </div>
              </section>

              <section className="ub-panel">
                <h2><Activity size={12} /> Throughput</h2>
                <div className="ub-kv">
                  <span>Companies / min</span><span>{fmt(thr.companiesPerMinute, 1)}</span>
                  <span>Rows / min</span><span>{fmt(thr.rowsPerMinute, 1)}</span>
                  <span>Warehouse writes</span><span>{fmt(thr.warehouseWrites)}</span>
                  <span>Batches done</span><span>{fmt(thr.batchesCompleted)}</span>
                  <span>Pause</span><span>{fmt(thr.pauseMs)} ms</span>
                  <span>Concurrency</span><span>{fmt(thr.concurrency)}</span>
                </div>
              </section>
            </div>

            <section className="ub-panel">
              <h2>Recent activity</h2>
              <div className="ub-table-wrap">
                <table className="ub-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Symbol</th>
                      <th>State</th>
                      <th>Detail</th>
                      <th>Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.length ? logs.slice(0, 25).map((row, idx) => (
                      <tr key={`${row.at}-${row.symbol}-${idx}`}>
                        <td>{row.at ? new Date(row.at).toLocaleTimeString() : '—'}</td>
                        <td>{row.symbol || '—'}</td>
                        <td>{row.state || '—'}</td>
                        <td>{row.reason || row.dqiv || row.isin || '—'}</td>
                        <td>{row.latencyMs != null ? `${row.latencyMs} ms` : '—'}</td>
                      </tr>
                    )) : (
                      <tr><td colSpan={5} className="ub-muted">No activity yet — start bootstrap to begin.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            <div className="ub-grid">
              <section className="ub-panel">
                <h2><AlertTriangle size={12} /> Missing ISIN ({summary.missingIsin || missing.length})</h2>
                <div className="ub-table-wrap">
                  <table className="ub-table">
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>Company</th>
                        <th>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {missing.length ? missing.slice(0, 40).map((row) => (
                        <tr key={row.symbol}>
                          <td>{row.symbol}</td>
                          <td>{row.company}</td>
                          <td>{row.reason}</td>
                        </tr>
                      )) : (
                        <tr><td colSpan={3} className="ub-muted">Start bootstrap once to load missing-ISIN inventory.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="ub-panel">
                <h2><AlertTriangle size={12} /> Retry / Failed</h2>
                <div className="ub-table-wrap">
                  <table className="ub-table">
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>State</th>
                        <th>Attempts</th>
                        <th>Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {failures.length ? failures.slice(0, 40).map((row) => (
                        <tr key={row.symbol}>
                          <td>{row.symbol}</td>
                          <td>{row.state}</td>
                          <td>{row.attempts}</td>
                          <td>{row.lastError || '—'}</td>
                        </tr>
                      )) : (
                        <tr><td colSpan={4} className="ub-muted">No retries or failures.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
