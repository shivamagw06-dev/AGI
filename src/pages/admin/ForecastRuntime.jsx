import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, Pause, Play, RefreshCw, Zap } from 'lucide-react';
import { API_ORIGIN } from '@/config';
import {
  getFieBoard,
  postFieRuntimeResume,
  postFieRuntimeRun,
  postFieRuntimeStart,
  postFieRuntimeStop,
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

async function marketJson(path, timeoutMs = 15000) {
  const response = await fetch(`${API_ORIGIN}/api/market${path}`, {
    credentials: 'include',
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(timeoutMs),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.error || `Forecast output unavailable (${response.status})`);
  return data;
}

function pct(value, digits = 2) {
  return value == null ? '—' : `${Number(value).toFixed(digits)}%`;
}

export default function ForecastRuntime() {
  const [board, setBoard] = useState(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);
  const [error, setError] = useState(null);
  const [outputError, setOutputError] = useState(null);
  const [horizon, setHorizon] = useState('5d');
  const [rankings, setRankings] = useState([]);
  const [validation, setValidation] = useState(null);
  const [rankHealth, setRankHealth] = useState(null);
  const [outputUpdatedAt, setOutputUpdatedAt] = useState(null);

  const refresh = useCallback(async () => {
    try {
      setBoard(await getFieBoard());
      setError(null);
    } catch (err) {
      setError(err.message || 'fie_board_failed');
    }
  }, []);

  const refreshOutput = useCallback(async () => {
    try {
      const query = `horizon=${encodeURIComponent(horizon)}`;
      const [rankingPayload, validationPayload, rankPayload] = await Promise.all([
        marketJson(`/forecasts/rankings?${query}&limit=200`),
        marketJson(`/forecasts/validation?${query}`),
        marketJson(`/forecasts/rank-ic?${query}&limit=252`),
      ]);
      setRankings(rankingPayload.rows || []);
      setValidation(validationPayload);
      setRankHealth(rankPayload);
      setOutputUpdatedAt(new Date());
      setOutputError(null);
    } catch (err) {
      setOutputError(err?.name === 'TimeoutError' ? 'Forecast output timed out after 15 seconds.' : err.message || 'forecast_output_failed');
    }
  }, [horizon]);

  useEffect(() => {
    refresh();
    refreshOutput();
    const runtimeId = setInterval(refresh, 60000);
    const outputId = setInterval(refreshOutput, 30000);
    return () => { clearInterval(runtimeId); clearInterval(outputId); };
  }, [refresh, refreshOutput]);

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
  const progressPct = Number(progress.percent || 0);

  return (
    <div className="vp-root">
      <div className="vp-shell">
        <Link to="/admin" className="vp-back"><ArrowLeft size={16} /> Admin</Link>
        <p className="vp-kicker">Phase 8.5 · Forecast Intelligence</p>
        <h1 className="vp-title">Forecast Runtime</h1>
        <p className="vp-sub">
          {board?.what_this_does
            || 'Builds explainable business, growth, profitability and valuation outlooks from warehouse + UVE/HVIE/VARIE/RIE. No target prices. No BUY/SELL.'}
        </p>

        <div className="hr-actions">
          <button type="button" className="hr-btn primary" disabled={busy || isRunning} onClick={() => act('start', postFieRuntimeStart)}>
            <Play size={14} /> {isRunning ? 'Running…' : 'Start'}
          </button>
          <button type="button" className="hr-btn" disabled={busy} onClick={() => act('resume', postFieRuntimeResume)}>
            <RefreshCw size={14} /> Resume
          </button>
          <button type="button" className="hr-btn" disabled={busy} onClick={() => act('run', () => postFieRuntimeRun({ batch: 3 }))}>
            <Zap size={14} /> Run 3 now
          </button>
          <button type="button" className="hr-btn ghost" disabled={busy || !isRunning} onClick={() => act('stop', postFieRuntimeStop)}>
            <Pause size={14} /> Stop
          </button>
          <button type="button" className="hr-btn ghost" disabled={busy} onClick={() => { refresh(); refreshOutput(); }}>Refresh</button>
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
              <strong>{fmt(progressPct, 1)}%</strong>
              <span>complete</span>
            </div>
          </div>
          <div className="hr-bar" aria-hidden="true">
            <div className="hr-bar-fill" style={{ width: `${Math.min(100, Math.max(0, progressPct))}%` }} />
          </div>
        </section>

        <section className="vp-stats">
          <Stat label="Universe" value={fmt(progress.universe)} />
          <Stat label="Complete" value={fmt(progress.complete)} />
          <Stat label="Pending" value={fmt(progress.pending)} />
          <Stat label="Waiting statements" value={fmt(progress.waiting_statements)} />
          <Stat label="Waiting HVIE" value={fmt(progress.waiting_hvie)} />
          <Stat label="Waiting RIE" value={fmt(progress.waiting_rie)} />
          <Stat label="Failed" value={fmt(progress.failed)} />
          <Stat label="Runtime" value={runtimeStatus} />
        </section>

        <section className="mt-8 rounded-xl border border-slate-200 bg-white overflow-hidden">
          <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 bg-slate-950 px-6 py-5 text-white">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-400">Stored probabilistic output</p>
              <h2 className="mt-1 text-xl font-semibold">Latest Forecast Rankings</h2>
              <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-400">One latest forecast per stock. Refreshes every 30 seconds independently of the Forecast Intelligence Engine runtime.</p>
            </div>
            <div className="flex items-center gap-2">
              {['1d', '5d', '20d'].map((value) => <button key={value} type="button" onClick={() => setHorizon(value)} className={`rounded-md px-3 py-2 text-xs font-semibold ${horizon === value ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800 text-slate-300'}`}>{value}</button>)}
            </div>
          </header>

          {outputError ? <div className="m-5 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><AlertTriangle size={17} className="mt-0.5 shrink-0" /><span>{outputError} Previously loaded output remains visible.</span></div> : null}

          <div className="grid grid-cols-2 gap-px border-b border-slate-200 bg-slate-200 md:grid-cols-5">
            <div className="bg-white p-4"><span className="block text-[10px] uppercase tracking-wide text-slate-500">Unique stocks</span><strong className="mt-1 block text-2xl text-slate-900">{rankings.length}</strong></div>
            <div className="bg-white p-4"><span className="block text-[10px] uppercase tracking-wide text-slate-500">Accuracy</span><strong className="mt-1 block text-2xl text-slate-900">{pct(validation?.directional_accuracy)}</strong></div>
            <div className="bg-white p-4"><span className="block text-[10px] uppercase tracking-wide text-slate-500">Validated outcomes</span><strong className="mt-1 block text-2xl text-slate-900">{fmt(validation?.observations)}</strong></div>
            <div className="bg-white p-4"><span className="block text-[10px] uppercase tracking-wide text-slate-500">Mean rank IC</span><strong className="mt-1 block text-2xl text-slate-900">{rankHealth?.mean_rank_ic == null ? 'Unproven' : Number(rankHealth.mean_rank_ic).toFixed(3)}</strong></div>
            <div className="bg-white p-4"><span className="block text-[10px] uppercase tracking-wide text-slate-500">Last refreshed</span><strong className="mt-1 block text-sm text-slate-900">{outputUpdatedAt ? outputUpdatedAt.toLocaleTimeString('en-IN') : 'Loading…'}</strong></div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-[900px] w-full text-left text-xs">
              <thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3">Rank</th><th className="px-5 py-3">Stock</th><th className="px-5 py-3">Expected alpha</th><th className="px-5 py-3">Positive probability</th><th className="px-5 py-3">Range (P10–P90)</th><th className="px-5 py-3">Confidence</th><th className="px-5 py-3">Forecast time</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {rankings.map((row) => { const forecast = row.forecast || {}; return <tr key={row.forecast_id} className="hover:bg-slate-50"><td className="px-5 py-3 font-mono text-slate-500">#{row.forecast_rank}</td><td className="px-5 py-3 font-semibold text-slate-900">{row.symbol}</td><td className={`px-5 py-3 font-semibold ${Number(forecast.expected_alpha_pct) >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>{pct(forecast.expected_alpha_pct)}</td><td className="px-5 py-3 text-slate-700">{forecast.probability_positive == null ? '—' : pct(Number(forecast.probability_positive) * 100, 1)}</td><td className="px-5 py-3 text-slate-600">{forecast.p10 == null ? '—' : `${pct(forecast.p10)} – ${pct(forecast.p90)}`}</td><td className="px-5 py-3 text-slate-700">{forecast.confidence == null ? '—' : pct(forecast.confidence, 1)}</td><td className="px-5 py-3 text-slate-500">{forecast.forecast_time ? new Date(forecast.forecast_time).toLocaleString('en-IN') : '—'}</td></tr>; })}
                {!rankings.length && !outputError ? <tr><td colSpan="7" className="px-5 py-10 text-center text-slate-500">No {horizon} forecasts are stored for today.</td></tr> : null}
              </tbody>
            </table>
          </div>
          <footer className="flex flex-wrap justify-between gap-2 border-t border-slate-200 bg-slate-50 px-5 py-3 text-[10px] text-slate-500"><span>Research only · no orders, target prices or position sizing</span><span>{rankHealth?.periods || 0} completed rank-IC periods · {validation?.calibrated ? 'direction model calibrated' : 'calibration pending'}</span></footer>
        </section>
      </div>
    </div>
  );
}
