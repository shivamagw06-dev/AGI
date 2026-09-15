import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Pause, Play, RefreshCw, Zap } from 'lucide-react';
import {
  getHvieUniverseBoard,
  postHvieUniverseResume,
  postHvieUniverseRun,
  postHvieUniverseStart,
  postHvieUniverseStop,
} from '@/lib/intelligenceApi';
import './valuationPolicy.css';

function fmt(n, d = 0) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: d });
}

function friendlyError(err) {
  const msg = String(err?.message || err || '');
  if (/502|503|504|Bad Gateway|Service Unavailable|HTML/i.test(msg)) {
    return 'The intelligence engine is busy or restarting. Wait a minute, then press Refresh — your progress is saved.';
  }
  if (/timeout|aborted|Failed to fetch|NetworkError/i.test(msg)) {
    return 'Could not reach the engine. Check that the service is up, then try again.';
  }
  return msg || 'Something went wrong loading HVIE Runtime.';
}

function Stat({ label, value, hint }) {
  return (
    <div className="vp-stat">
      <span className="label">{label}</span>
      <span className="value">{value ?? '—'}</span>
      {hint ? <span className="vp-muted" style={{ fontSize: '0.75rem' }}>{hint}</span> : null}
    </div>
  );
}

export default function HvieRuntime() {
  const [board, setBoard] = useState(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const data = await getHvieUniverseBoard();
      setBoard(data);
      setError(null);
    } catch (err) {
      setError(friendlyError(err));
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 15000);
    return () => clearInterval(id);
  }, [refresh]);

  const act = async (label, fn) => {
    setBusy(true);
    setNote(null);
    try {
      const out = await fn();
      if (out?.already_running) {
        setNote('Worker is already running — progress continues in the background.');
      } else if (out?.ok === false) {
        setNote(`${label} failed: ${out.error || 'unknown error'}`);
      } else {
        setNote(
          label === 'start' || label === 'resume'
            ? 'Worker started. It will keep going until the list is finished — you can leave this page.'
            : label === 'stop'
              ? 'Worker paused. Finished companies stay finished.'
              : `${label}: ok`,
        );
      }
      await refresh();
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setBusy(false);
    }
  };

  const progress = board?.progress || {};
  const thr = board?.throughput || {};
  const runtimeStatus = board?.runtime?.status || 'idle';
  const isRunning = runtimeStatus === 'running';
  const pct = Number(progress.percent || 0);
  const stages = board?.stages || [];

  return (
    <div className="vp-root">
      <div className="vp-shell">
        <Link to="/admin" className="vp-back"><ArrowLeft size={16} /> Admin</Link>

        <p className="vp-kicker">Historical Valuation · Universe build</p>
        <h1 className="vp-title">HVIE Runtime</h1>
        <p className="vp-sub">
          {board?.what_this_does
            || 'Builds historical PE, PB and EV for every company from warehouse data. Press Start and leave it running.'}
        </p>

        <div className="hr-actions">
          <button
            type="button"
            className="hr-btn primary"
            disabled={busy || isRunning}
            onClick={() => act('start', postHvieUniverseStart)}
            title={board?.buttons?.start}
          >
            <Play size={14} /> {isRunning ? 'Running…' : 'Start'}
          </button>
          <button
            type="button"
            className="hr-btn"
            disabled={busy}
            onClick={() => act('resume', postHvieUniverseResume)}
            title={board?.buttons?.resume}
          >
            <RefreshCw size={14} /> Resume / reload
          </button>
          <button
            type="button"
            className="hr-btn"
            disabled={busy}
            onClick={() => act('run', () => postHvieUniverseRun({ batch: 3 }))}
            title={board?.buttons?.run_batch}
          >
            <Zap size={14} /> Run 3 now
          </button>
          <button
            type="button"
            className="hr-btn ghost"
            disabled={busy || !isRunning}
            onClick={() => act('stop', postHvieUniverseStop)}
            title={board?.buttons?.stop}
          >
            <Pause size={14} /> Stop
          </button>
          <button type="button" className="hr-btn ghost" disabled={busy} onClick={refresh}>
            Refresh
          </button>
        </div>

        {error ? <div className="vp-error">{error}</div> : null}
        {note ? <p className="hr-note">{note}</p> : null}

        <section className="hr-hero">
          <div className="hr-hero-top">
            <div>
              <span className={`hr-status ${isRunning ? 'on' : runtimeStatus === 'stopped' ? 'off' : 'idle'}`}>
                {isRunning ? 'Working' : runtimeStatus === 'stopped' ? 'Paused' : 'Idle'}
              </span>
              <p className="hr-plain">{board?.plain_english || 'Loading progress…'}</p>
            </div>
            <div className="hr-pct">
              <strong>{fmt(pct, 1)}%</strong>
              <span>complete</span>
            </div>
          </div>
          <div className="hr-bar" aria-hidden="true">
            <div className="hr-bar-fill" style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
          </div>
          <p className="vp-muted hr-bar-caption">
            {fmt(progress.complete)} finished · {fmt(progress.pending)} waiting · {fmt(progress.running)} in progress
            {progress.skipped ? ` · ${fmt(progress.skipped)} missing data` : ''}
            {progress.failed ? ` · ${fmt(progress.failed)} failed` : ''}
          </p>
        </section>

        <section className="vp-stats">
          <Stat label="Companies" value={fmt(progress.universe)} hint="On the work list" />
          <Stat label="Finished" value={fmt(progress.complete)} hint={`${fmt(pct, 1)}%`} />
          <Stat label="Ready / pending" value={fmt(progress.pending)} hint="Queued to build" />
          <Stat label="Waiting prices" value={fmt(progress.waiting_prices)} hint="Need market history" />
          <Stat label="Waiting statements" value={fmt(progress.waiting_statements)} hint="Need financials" />
          <Stat label="Waiting share count" value={fmt(progress.waiting_share_count)} hint="Need shares outstanding" />
          <Stat label="Failed" value={fmt(progress.failed)} hint="Need attention" />
          <Stat
            label="Speed"
            value={thr.speed_per_hour != null ? `${fmt(thr.speed_per_hour, 1)}/h` : '—'}
            hint={thr.eta_hours != null ? `~${fmt(thr.eta_hours, 1)} h left` : 'ETA after Start'}
          />
        </section>

        <section className="hr-panel">
          <h2>What each stage means</h2>
          <p className="vp-muted">
            These are counts of companies that reached each step — not separate jobs.
            “Finished” is what Coverage Health uses for historical intelligence.
          </p>
          <ul className="hr-stages">
            {stages.map((s) => (
              <li key={s.name}>
                <div>
                  <strong>{s.name}</strong>
                  <span className="vp-muted">{s.hint}</span>
                </div>
                <em>{fmt(s.count)}</em>
              </li>
            ))}
          </ul>
        </section>

        <div className="hr-grid">
          <section className="hr-panel">
            <h2>Next up</h2>
            <p className="vp-muted">Companies the worker will pick next.</p>
            <div className="vp-table-wrap">
              <table className="vp-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Sector</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(board?.next_up || []).length === 0 ? (
                    <tr><td colSpan={3} className="vp-muted">Nothing waiting — queue may be done or still loading.</td></tr>
                  ) : (board?.next_up || []).map((r) => (
                    <tr key={`n-${r.symbol}`}>
                      <td>{r.symbol}</td>
                      <td>{r.sector || '—'}</td>
                      <td>{r.queue_status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="hr-panel">
            <h2>Needs attention</h2>
            <p className="vp-muted">Failed, retrying, or waiting on prices/statements.</p>
            <div className="vp-table-wrap">
              <table className="vp-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>State</th>
                    <th>Why</th>
                  </tr>
                </thead>
                <tbody>
                  {(board?.failures || []).length === 0 ? (
                    <tr><td colSpan={3} className="vp-muted">No failures right now.</td></tr>
                  ) : (board?.failures || []).map((r) => (
                    <tr key={`f-${r.symbol}-${r.queue_status}`}>
                      <td>{r.symbol}</td>
                      <td>
                        <span className={`vp-pill ${r.queue_status === 'FAILED' ? 'bad' : 'warn'}`}>
                          {r.queue_status}
                        </span>
                      </td>
                      <td className="vp-reason">{r.last_error || r.reason || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <section className="hr-panel">
          <h2>Recently finished</h2>
          <ul className="hr-chips">
            {(board?.recent_complete || []).length === 0 ? (
              <li className="vp-muted">None yet this view.</li>
            ) : (board?.recent_complete || []).map((r) => (
              <li key={`c-${r.symbol}`}>{r.symbol}</li>
            ))}
          </ul>
        </section>

        {board?.runtime?.last_error ? (
          <p className="vp-muted">Last worker error: {board.runtime.last_error}</p>
        ) : null}
      </div>
    </div>
  );
}
