import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Pause, Play, RefreshCw, Zap } from 'lucide-react';
import {
  getMieBoard,
  postMieRuntimeResume,
  postMieRuntimeRun,
  postMieRuntimeStart,
  postMieRuntimeStop,
} from '@/lib/intelligenceApi';
import './valuationPolicy.css';

function fmt(n, d = 0) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: d });
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

export default function MacroRuntime() {
  const [board, setBoard] = useState(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      setBoard(await getMieBoard());
      setError(null);
    } catch (err) {
      setError(err.message || 'mie_board_failed');
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
      setNote(`${label}: ${out?.already_running ? 'already running' : out?.ok === false ? out.error || 'failed' : 'ok'}`);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const progress = board?.progress || {};
  const runtimeStatus = board?.runtime?.status || 'idle';
  const isRunning = runtimeStatus === 'running';
  const pct = Number(progress.percent || 0);
  const cadence = board?.cadence || {};

  return (
    <div className="vp-root">
      <div className="vp-shell">
        <Link to="/admin" className="vp-back"><ArrowLeft size={16} /> Admin</Link>
        <p className="vp-kicker">Phase 9.0 · Macro Intelligence</p>
        <h1 className="vp-title">Macro Runtime</h1>
        <p className="vp-sub">
          {board?.what_this_does
            || 'Refreshes explainable macro regime, sector impact, scenarios and risks from warehouse + CMKP/HMIP/MRI/HMAI/MFI. No BUY/SELL. No GDP point predictions.'}
        </p>

        <div className="hr-actions">
          <button type="button" className="hr-btn primary" disabled={busy || isRunning} onClick={() => act('start', postMieRuntimeStart)}>
            <Play size={14} /> {isRunning ? 'Running…' : 'Start'}
          </button>
          <button type="button" className="hr-btn" disabled={busy} onClick={() => act('resume', postMieRuntimeResume)}>
            <RefreshCw size={14} /> Resume
          </button>
          <button type="button" className="hr-btn" disabled={busy} onClick={() => act('run', () => postMieRuntimeRun({ mode: 'daily', batch: 1 }))}>
            <Zap size={14} /> Refresh now
          </button>
          <button type="button" className="hr-btn ghost" disabled={busy || !isRunning} onClick={() => act('stop', postMieRuntimeStop)}>
            <Pause size={14} /> Stop
          </button>
          <button type="button" className="hr-btn ghost" disabled={busy} onClick={refresh}>Refresh</button>
        </div>

        {error ? <div className="vp-error">{error}</div> : null}
        {note ? <p className="hr-note">{note}</p> : null}

        <section className="hr-hero">
          <div className="hr-hero-top">
            <div>
              <span className={`hr-status ${isRunning ? 'on' : 'idle'}`}>{isRunning ? 'Working' : 'Idle'}</span>
              <p className="hr-plain">{board?.plain_english || 'Loading…'}</p>
            </div>
            <div className="hr-pct">
              <strong>{fmt(pct, 1)}%</strong>
              <span>complete</span>
            </div>
          </div>
          <div className="hr-bar" aria-hidden="true">
            <div className="hr-bar-fill" style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
          </div>
        </section>

        <section className="vp-stats">
          <Stat label="Universe" value={fmt(progress.universe)} />
          <Stat label="Complete" value={fmt(progress.complete)} />
          <Stat label="Pending" value={fmt(progress.pending)} />
          <Stat label="Failed" value={fmt(progress.failed)} />
          <Stat label="Runtime" value={runtimeStatus} />
          <Stat label="Last mode" value={board?.runtime?.last_mode || '—'} />
        </section>

        <section className="vp-stats" style={{ marginTop: '1rem' }}>
          <Stat label="Daily" value={cadence.daily || 'FX / yields / commodities'} />
          <Stat label="Weekly" value={cadence.weekly || 'Relationships'} />
          <Stat label="Monthly" value={cadence.monthly || 'CPI / IIP / PMI'} />
          <Stat label="Quarterly" value={cadence.quarterly || 'GDP / forecasts'} />
        </section>
      </div>
    </div>
  );
}
