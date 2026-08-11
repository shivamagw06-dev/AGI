import { useEffect, useMemo, useState } from 'react';
import { Activity, AlertCircle, BarChart3, ChevronRight, Clock3, RefreshCw, ShieldCheck, Sparkles, X } from 'lucide-react';
import API_ORIGIN from '@/config';
import { CONVICTION_FILTERS, convictionTone, filterConvictionRows, readableConvictionLabel } from '@/lib/evidenceConvictionView';
import './liveAlphaPage.css';
import './growwResearch.css';

const STRATEGIES = [
  ['cross_sectional_momentum_v1', 'Leadership', 'Cross-Sectional Momentum'],
  ['volume_liquidity_anomaly_v1', 'Activity', 'Volume & Liquidity Anomaly'],
  ['opening_range_expansion_v1', 'Breakout', 'Opening-Range Expansion'],
  ['intraday_mean_reversion_v1', 'Dislocation', 'Intraday Mean Reversion'],
  ['derivatives_positioning_v1', 'Positioning', 'Derivatives Positioning'],
];
const SHORT = { cross_sectional_momentum_v1: 'Lead', volume_liquidity_anomaly_v1: 'Act.', opening_range_expansion_v1: 'Break', intraday_mean_reversion_v1: 'Dis.', derivatives_positioning_v1: 'Pos.' };

function signedScore(signal) {
  if (!signal || !signal.direction) return 0;
  const magnitude = Math.min(99, Math.round(Math.abs(Number(signal.alpha_z) || 0) * 28 + (Number(signal.signal_quality_score) || 0) * 0.35));
  return signal.direction === 'negative' ? -magnitude : magnitude;
}
function scoreText(value) { return `${value > 0 ? '+' : ''}${value}`; }
function confidence(score, sample = 0) { return sample >= 100 && score >= 70 ? 'VALIDATED' : score >= 80 ? 'HIGH' : score >= 60 ? 'MEDIUM' : 'LOW'; }
function formatFactor(value, suffix = '') { const number = Number(value); return Number.isFinite(number) ? `${number > 0 ? '+' : ''}${number.toFixed(2)}${suffix}` : '—'; }
function age(iso) { const mins = Math.max(0, Math.floor((Date.now() - Date.parse(iso)) / 60000)); return mins < 1 ? 'Now' : mins < 60 ? `${mins}m` : `${Math.floor(mins / 60)}h`; }

async function readApiJson(response, label) {
  const contentType = response.headers.get('content-type') || '';
  if (!response.ok) throw new Error(`${label} is unavailable (${response.status}).`);
  if (!contentType.toLowerCase().includes('application/json')) {
    throw new Error(`${label} returned the website shell instead of API data. Check the configured backend origin.`);
  }
  return response.json();
}

function buildRows(signals) {
  const latest = new Map();
  for (const signal of signals) {
    const key = `${signal.symbol}|${signal.engine}`;
    if (!latest.has(key)) latest.set(key, signal);
  }
  const symbols = new Map();
  for (const signal of latest.values()) {
    const row = symbols.get(signal.symbol) || { symbol: signal.symbol, sector: signal.sector || '—', strategies: {}, newest: signal.as_of };
    row.strategies[signal.engine] = signal;
    if (Date.parse(signal.as_of) > Date.parse(row.newest)) row.newest = signal.as_of;
    symbols.set(signal.symbol, row);
  }
  return [...symbols.values()].map((row) => {
    const active = Object.values(row.strategies).filter((signal) => signal.direction);
    const scores = active.map(signedScore);
    const composite = scores.length ? Math.round(scores.reduce((sum, value) => sum + value, 0) / Math.sqrt(scores.length)) : 0;
    const quality = active.length ? Math.round(active.reduce((sum, signal) => sum + Number(signal.empirical_confidence_score ?? signal.signal_quality_score ?? 0), 0) / active.length) : 0;
    const samples = Math.max(0, ...active.map((signal) => Number(signal.comparable_observations) || 0));
    return { ...row, active, composite: Math.max(-99, Math.min(99, composite)), quality, samples, confidence: confidence(quality, samples) };
  });
}

export default function LiveAlphaPage() {
  const [payload, setPayload] = useState({ signals: [], runs: [] });
  const [runtime, setRuntime] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);
  const [strategy, setStrategy] = useState('all');
  const [sort, setSort] = useState('alpha');
  const [view, setView] = useState('signals');
  const [conviction, setConviction] = useState({ run: null, rows: [] });
  const [convictionFilter, setConvictionFilter] = useState('shortlist');
  const [convictionError, setConvictionError] = useState('');

  const load = async () => {
    setLoading(true); setError('');
    try {
      if (!API_ORIGIN) throw new Error('AGI backend origin is not configured.');
      const [workspaceResponse, statusResponse] = await Promise.all([
        fetch(`${API_ORIGIN}/api/market/live-alpha/workspace`, { headers: { Accept: 'application/json' } }),
        fetch(`${API_ORIGIN}/api/market/live-alpha/status`, { headers: { Accept: 'application/json' } }),
      ]);
      setPayload(await readApiJson(workspaceResponse, 'Live Alpha research store'));
      setRuntime(await readApiJson(statusResponse, 'Live Alpha runtime'));
      try {
        const convictionResponse = await fetch(`${API_ORIGIN}/api/market/evidence-conviction?limit=200`, { headers: { Accept: 'application/json' } });
        setConviction(await readApiJson(convictionResponse, 'Conviction ranking')); setConvictionError('');
      }
      catch (convictionRequestError) { setConvictionError(convictionRequestError.message); }
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { document.title = 'Live Alpha | Agarwal Global Investments'; load(); const timer = setInterval(load, 60000); return () => clearInterval(timer); }, []);

  const allRows = useMemo(() => buildRows(payload.signals || []), [payload.signals]);
  const rows = useMemo(() => allRows.filter((row) => strategy === 'all' || row.strategies[strategy]?.direction).sort((a, b) => sort === 'confidence' ? b.quality - a.quality : sort === 'age' ? Date.parse(b.newest) - Date.parse(a.newest) : sort === 'sector' ? a.sector.localeCompare(b.sector) : Math.abs(b.composite) - Math.abs(a.composite)), [allRows, strategy, sort]);
  const strategyStats = useMemo(() => Object.fromEntries(STRATEGIES.map(([key]) => {
    const signals = allRows.map((row) => row.strategies[key]).filter((signal) => signal?.direction);
    return [key, { active: signals.length, high: signals.filter((signal) => Number(signal.signal_quality_score) >= 80).length, strongest: signals.sort((a, b) => Math.abs(signedScore(b)) - Math.abs(signedScore(a)))[0] }];
  })), [allRows]);
  const isFresh = payload.freshness?.stale === false;
  const evaluationStatus = runtime?.evaluation_status || (runtime?.status === 'running' ? 'warming_up' : 'stopped');
  const displayStatus = payload.readiness?.status === 'persistence_degraded'
    ? 'Storage issue'
    : evaluationStatus === 'warming_up'
      ? 'Warming up'
      : evaluationStatus === 'degraded' || evaluationStatus === 'blocked'
        ? 'Research degraded'
        : !isFresh
          ? 'Stale signals'
          : evaluationStatus === 'live'
            ? 'Live research'
            : 'Research standby';
  const liveNow = displayStatus === 'Live research';
  const highConfidence = isFresh ? allRows.filter((row) => row.confidence === 'HIGH' || row.confidence === 'VALIDATED').length : 0;
  const selectedRow = selected ? allRows.find((row) => row.symbol === selected) : null;
  const confluence = [...allRows].filter((row) => row.active.length >= 2).sort((a, b) => b.active.length - a.active.length || Math.abs(b.composite) - Math.abs(a.composite)).slice(0, 3);
  const lastUpdate = payload.freshness?.latest_successful_at
    ? new Date(payload.freshness.latest_successful_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
    : 'No completed run';

  return <div className="la-page">
    <section className="la-command">
      <div className="la-title-row">
        <div><span className="la-eyebrow"><Sparkles size={13} /> AGI research system</span><h1>Live Alpha</h1><p>Independent market behaviours, unified into one institutional signal workspace.</p></div>
        <div className="la-live-meta"><span className={`la-live-dot ${liveNow ? 'on' : ''}`} />{displayStatus}<button onClick={load} aria-label="Refresh"><RefreshCw size={15} className={loading ? 'spin' : ''} /></button></div>
      </div>
      <div className="la-regime">
        <div><small>Market regime</small><strong>{runtime?.last_evaluation?.regime || 'Awaiting classification'}</strong></div>
        <div><small>Nifty bias</small><strong>Not yet classified</strong></div>
        <div><small>Active signals</small><strong>{isFresh ? allRows.filter((row) => row.active.length).length : 0}</strong></div>
        <div><small>High confidence</small><strong>{highConfidence}</strong></div>
        <div><small>Last completed run</small><strong>{lastUpdate}</strong></div>
      </div>
      <div className="la-strategy-grid">
        {STRATEGIES.map(([key, label, technical]) => { const stat = strategyStats[key]; const health = payload.strategy_health?.[key]; const effectiveActive = isFresh ? stat?.active || 0 : 0; const score = stat?.strongest ? signedScore(stat.strongest) : 0; const cardStatus = health?.status === 'persistence_failed' ? 'Storage error' : health?.status === 'stale' ? 'Stale' : health?.status === 'never_run' ? 'Not run' : key === 'derivatives_positioning_v1' && runtime?.last_evaluation?.derivatives_status === 'insufficient_derivative_coverage' ? 'Awaiting futures' : liveNow && effectiveActive ? 'Live' : evaluationStatus === 'warming_up' ? 'Warming up' : 'Standby'; return <button key={key} onClick={() => setStrategy(strategy === key ? 'all' : key)} className={`la-strategy-card ${strategy === key ? 'active' : ''}`}>
          <span className="la-card-status"><i className={cardStatus === 'Live' ? 'ready' : ''} />{cardStatus}</span>
          <h2>{label}</h2><p>{technical}</p><div className="la-card-count"><strong>{effectiveActive}</strong><span>active<br />{isFresh ? stat?.high || 0 : 0} high confidence</span></div>
          <footer><span>{isFresh ? 'Strongest' : 'Last stored'}</span><b>{stat?.strongest ? `${stat.strongest.symbol} ${scoreText(score)}` : 'No signal'}</b></footer>
        </button>; })}
      </div>
    </section>

    <main className="la-main">
      <nav className="la-view-tabs" aria-label="Live Alpha views">
        <button className={view === 'signals' ? 'active' : ''} onClick={() => setView('signals')}><Activity size={15} /> Strategy signals</button>
        <button className={view === 'conviction' ? 'active' : ''} onClick={() => setView('conviction')}><ShieldCheck size={15} /> Conviction</button>
      </nav>
      {view === 'signals' ? <>
      <GrowwResearch groww={payload.groww} />
      <section className="la-panel la-scanner">
        <header><div><span className="la-section-kicker">Opportunity map</span><h2>Live Alpha Scanner</h2></div><div className="la-controls"><select value={sort} onChange={(event) => setSort(event.target.value)} aria-label="Sort scanner"><option value="alpha">Alpha score</option><option value="confidence">Confidence</option><option value="sector">Sector</option><option value="age">Signal age</option></select><span>{rows.length} names</span></div></header>
        {error ? <div className="la-notice error"><AlertCircle size={18} /><div><strong>Workspace unavailable</strong><p>{error}</p></div></div> : null}
        {!error && !liveNow ? <div className="la-notice"><AlertCircle size={18} /><div><strong>{displayStatus}</strong><p>{payload.readiness?.status === 'persistence_degraded' ? `Signal storage failed for: ${(payload.readiness.degraded_engines || []).map((key) => SHORT[key] || key).join(', ')}.` : evaluationStatus === 'warming_up' ? 'The market feed is connected, but the strategies are collecting enough benchmark history before evaluation.' : payload.freshness?.latest_successful_at ? `Displayed observations are historical. Last completed run: ${lastUpdate}.` : 'No completed strategy run is available yet.'}</p></div></div> : null}
        {!loading && !error && !rows.length ? <div className="la-empty"><Activity size={28} /><h3>{payload.readiness?.status === 'database_setup_required' ? 'Alpha database setup required' : 'No live research signals yet'}</h3><p>{payload.readiness?.status === 'database_setup_required' ? 'Apply the five Live Alpha Supabase migrations. The workspace will remain safely in standby until its research tables exist.' : 'The workspace is connected, but AGI has not stored a qualifying signal. Complete volume baselines, verify the universe, and enable shadow collection when ready.'}</p></div> : null}
        {rows.length ? <div className="la-table-wrap"><table><thead><tr><th>Stock</th><th>Alpha</th>{STRATEGIES.map(([key]) => <th key={key}>{SHORT[key]}</th>)}<th>Confidence</th><th>Age</th><th /></tr></thead><tbody>{rows.map((row) => <tr key={row.symbol} onClick={() => setSelected(row.symbol)}><td><strong>{row.symbol}</strong><span>{row.sector}</span></td><td><Score value={row.composite} /></td>{STRATEGIES.map(([key]) => <td key={key}><MiniScore signal={row.strategies[key]} /></td>)}<td><span className={`la-confidence ${row.confidence.toLowerCase()}`}>{row.confidence}</span></td><td>{age(row.newest)}</td><td><ChevronRight size={15} /></td></tr>)}</tbody></table></div> : null}
      </section>

      <section className="la-lower-grid">
        <div className="la-panel la-confluence"><header><div><span className="la-section-kicker">Independent confirmation</span><h2>High-Conviction Confluence</h2></div></header>{confluence.length ? confluence.map((row) => <button key={row.symbol} onClick={() => setSelected(row.symbol)}><div><strong>{row.symbol}</strong><span>{row.sector}</span></div><div className="la-model-dots">{STRATEGIES.map(([key]) => <i key={key} className={row.strategies[key]?.direction ? 'on' : ''} title={SHORT[key]} />)}</div><div><b>{row.active.length}/5</b><span>models confirm</span></div><Score value={row.composite} /></button>) : <p className="la-muted-copy">Confluence appears when two or more independent engines flag the same stock.</p>}</div>
        <div className="la-panel la-events"><header><div><span className="la-section-kicker">Signal lifecycle</span><h2>Recent Events</h2></div></header>{(payload.signals || []).filter((signal) => signal.direction).slice(0, 6).map((signal) => <button key={signal.id} onClick={() => setSelected(signal.symbol)}><Clock3 size={14} /><time>{new Date(signal.as_of).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' })}</time><span><b>{signal.symbol}</b> · {String(signal.classification).replaceAll('_', ' ')}</span></button>)}{!(payload.signals || []).some((signal) => signal.direction) ? <p className="la-muted-copy">No signal lifecycle events have been recorded.</p> : null}</div>
      </section>
      </> : <ConvictionPanel payload={conviction} error={convictionError} filter={convictionFilter} onFilter={setConvictionFilter} />}
      <p className="la-disclosure"><ShieldCheck size={14} /> Research signals only. AGI does not generate orders, position sizes, targets, or execution instructions.</p>
    </main>
    {selectedRow ? <ResearchDrawer row={selectedRow} onClose={() => setSelected(null)} /> : null}
  </div>;
}

function ConvictionPanel({ payload, error, filter, onFilter }) {
  const rows = filterConvictionRows(payload?.rows || [], filter);
  const counts = payload?.run?.counts || {};
  const generated = payload?.run?.generated_at ? new Date(payload.run.generated_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : 'Awaiting first run';
  return <section className="la-conviction-view">
    <header className="la-conviction-hero"><div><span className="la-section-kicker">Evidence-confirmed decision layer</span><h2>Conviction Ranking</h2><p>Groww leadership, Upstox confirmation and available research evidence—ranked without turning incomplete signals into investment theses.</p></div><div className="la-conviction-meta"><strong>{payload?.run?.universe_size || 0}</strong><span>ranked names<br />Updated {generated}</span></div></header>
    <div className="la-conviction-summary">
      <div><small>High conviction</small><strong>{counts.HIGH_CONVICTION || 0}</strong></div>
      <div><small>Confirmed</small><strong>{counts.CONFIRMED || 0}</strong></div>
      <div><small>Watch</small><strong>{counts.WATCH || 0}</strong></div>
      <div><small>Needs evidence</small><strong>{counts.INCOMPLETE || 0}</strong></div>
    </div>
    <div className="la-conviction-toolbar"><div>{CONVICTION_FILTERS.map(([key, label]) => <button key={key} className={filter === key ? 'active' : ''} onClick={() => onFilter(key)}>{label}</button>)}</div><span>Showing {rows.length} names</span></div>
    {error ? <div className="la-notice error"><AlertCircle size={18} /><div><strong>Conviction ranking unavailable</strong><p>{error}</p></div></div> : null}
    {!error && !payload?.run ? <div className="la-empty"><ShieldCheck size={28} /><h3>Awaiting the first conviction cycle</h3><p>The ranking will appear after the finance backend combines stored Groww, Upstox and research evidence.</p></div> : null}
    {!error && payload?.run && !rows.length ? <div className="la-empty"><ShieldCheck size={28} /><h3>{filter === 'shortlist' ? 'No evidence-confirmed shortlist yet' : 'No names in this category'}</h3><p>{filter === 'shortlist' ? 'AGI is correctly withholding conviction while fundamental, valuation or live confirmation is incomplete.' : 'Choose another filter to inspect the current ranking.'}</p>{filter === 'shortlist' ? <button className="la-empty-action" onClick={() => onFilter('incomplete')}>View names needing evidence</button> : null}</div> : null}
    {rows.length ? <div className="la-conviction-list">{rows.slice(0, filter === 'shortlist' ? 10 : 200).map((row) => <details key={row.symbol} className="la-conviction-card">
      <summary><span className="la-conviction-rank">#{row.rank}</span><div className="la-conviction-name"><strong>{row.symbol}</strong><span>{row.sector || 'Sector unavailable'}</span></div><div className="la-conviction-score"><strong>{Number(row.conviction_score).toFixed(1)}</strong><span>conviction</span></div><span className={`la-conviction-label ${convictionTone(row.conviction_label)}`}>{readableConvictionLabel(row.conviction_label)}</span><div className="la-evidence-meter"><i style={{ width: `${Math.round(Number(row.evidence_coverage || 0) * 100)}%` }} /><span>{Math.round(Number(row.evidence_coverage || 0) * 100)}% evidence</span></div><ChevronRight className="la-conviction-chevron" size={16} /></summary>
      <div className="la-conviction-detail"><article><small>AGI thesis</small><p>{row.thesis}</p></article><article><small>Risk and contradiction check</small><p>{row.risk_note}</p></article><div className="la-component-grid">{Object.entries(row.component_scores || {}).map(([key, value]) => <div key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{value == null ? '—' : Number(value).toFixed(0)}</strong></div>)}</div></div>
    </details>)}</div> : null}
  </section>;
}

function Score({ value }) { return <span className={`la-score ${value >= 80 ? 'exceptional up' : value <= -80 ? 'exceptional down' : value > 0 ? 'up' : value < 0 ? 'down' : ''}`}>{scoreText(value)}</span>; }
function MiniScore({ signal }) { const value = signedScore(signal); return signal?.direction ? <span className={`la-mini-score ${value > 0 ? 'up' : 'down'}`}>{scoreText(value)}</span> : <span className="la-dash">—</span>; }

function GrowwResearch({ groww }) {
  const runs = new Map((groww?.runs || []).map((run) => [run.strategy, run]));
  const sectorRun = runs.get('agi_sector_rotation_v1');
  const equityRun = runs.get('agi_equity_opportunity_v1');
  const sectors = (groww?.sectors || []).slice(0, 6);
  const equities = (groww?.equities || []).slice(0, 6);
  return <section className="la-groww"><header><div><span className="la-section-kicker">Groww Cloud · end-of-day research</span><h2>Groww Research</h2><p>Independent scheduled research inputs, excluded from the five-model live composite until comparably validated.</p></div><span className="la-groww-badge">Research only</span></header><div className="la-groww-grid">
    <article className="la-panel"><div className="la-groww-head"><div><small>AGI Sector</small><h3>Sector Rotation</h3></div><RunState run={sectorRun} /></div>{sectors.length ? <table><thead><tr><th>#</th><th>Sector</th><th>Score</th><th>Rotation</th><th>20d relative</th></tr></thead><tbody>{sectors.map((row) => <tr key={row.sector}><td>{row.rank}</td><td><strong>{row.sector}</strong></td><td>{Number(row.score).toFixed(0)}</td><td><span className={`la-rotation ${row.rotation}`}>{row.rotation}</span></td><td className={Number(row.relative_20d) >= 0 ? 'positive' : 'negative'}>{formatFactor(row.relative_20d, '%')}</td></tr>)}</tbody></table> : <GrowwEmpty label="No sector rotation run has been received." />}</article>
    <article className="la-panel"><div className="la-groww-head"><div><small>Opportunity</small><h3>Equity Opportunities</h3></div><RunState run={equityRun} /></div>{equities.length ? <table><thead><tr><th>#</th><th>Stock</th><th>Score</th><th>Signal</th><th>Volume</th></tr></thead><tbody>{equities.map((row) => <tr key={`${row.symbol}-${row.signal}`}><td>{row.rank || '—'}</td><td><strong>{row.symbol}</strong></td><td>{Number(row.score).toFixed(0)}</td><td><span className={`la-groww-signal ${row.signal}`}>{String(row.signal).replaceAll('_', ' ')}</span></td><td>{Number(row.volume_ratio) ? `${Number(row.volume_ratio).toFixed(2)}×` : '—'}</td></tr>)}</tbody></table> : <GrowwEmpty label="No equity opportunity run has been received." />}</article>
  </div></section>;
}

function RunState({ run }) { return <div className="la-run-state"><i className={run ? 'ready' : ''} /><span>{run ? run.status || 'received' : 'standby'}</span>{run ? <time>{age(run.as_of)}</time> : null}</div>; }
function GrowwEmpty({ label }) { return <div className="la-groww-empty"><Clock3 size={17} /><span>{label}</span></div>; }

function ResearchDrawer({ row, onClose }) {
  const lead = row.active.sort((a, b) => Math.abs(signedScore(b)) - Math.abs(signedScore(a)))[0];
  const factors = lead?.factor_values || {};
  return <div className="la-drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><aside className="la-drawer">
    <header><div><span>{row.sector}</span><h2>{row.symbol}</h2></div><button onClick={onClose} aria-label="Close research drawer"><X size={20} /></button></header>
    <section className="la-drawer-score"><div><small>Composite Alpha</small><Score value={row.composite} /></div><div><small>Confidence</small><strong>{row.confidence}</strong></div><div><small>Models</small><strong>{row.active.length}/5</strong></div><div><small>Signal age</small><strong>{age(row.newest)}</strong></div></section>
    <section><h3>Why flagged</h3><div className="la-factor-list">{STRATEGIES.map(([key, label]) => <div key={key}><span>{label}</span><MiniScore signal={row.strategies[key]} /></div>)}</div></section>
    <section><h3>Live evidence</h3><div className="la-evidence"><div><span>15m residual</span><b>{formatFactor(factors.residual_15m ?? lead?.residual_15m, '%')}</b></div><div><span>Volume vs expected</span><b>{Number(lead?.volume_ratio || factors.volume_surprise || 0) ? `${Number(lead?.volume_ratio || factors.volume_surprise).toFixed(2)}×` : '—'}</b></div><div><span>Opening range</span><b>{factors.breakout_pct != null ? `${formatFactor(factors.breakout_pct, '%')} break` : '—'}</b></div><div><span>OI change</span><b>{formatFactor(factors.oi_change_15m ?? lead?.oi_change, '%')}</b></div></div></section>
    <section className="la-what"><h3>What AGI sees</h3><p>{explain(row)}</p></section>
    <section><h3>Historical validation</h3>{row.samples ? <div className="la-validation"><div><span>Comparable signals</span><b>{row.samples.toLocaleString('en-IN')}</b></div><div><span>Empirical confidence</span><b>{row.quality}%</b></div></div> : <div className="la-notice"><BarChart3 size={18} /><div><strong>Collecting evidence</strong><p>Signal quality is live, but empirical confidence remains unvalidated until enough forward outcomes are complete.</p></div></div>}</section>
  </aside></div>;
}

function explain(row) {
  const names = STRATEGIES.filter(([key]) => row.strategies[key]?.direction).map(([, label]) => label);
  const direction = row.composite >= 0 ? 'positive' : 'negative';
  if (!names.length) return 'No active directional research classification is present.';
  return `${row.symbol} has a ${direction} composite research signal. ${names.join(', ')} ${names.length === 1 ? 'is' : 'are'} contributing independent evidence. ${row.samples ? 'Historical confidence is based on completed comparable outcomes.' : 'The live reading has not yet accumulated enough comparable outcomes for empirical validation.'}`;
}
