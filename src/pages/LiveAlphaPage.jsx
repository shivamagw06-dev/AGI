import { useEffect, useMemo, useState } from 'react';
import { Activity, AlertCircle, BarChart3, ChevronRight, Clock3, RefreshCw, ShieldCheck, Sparkles, X } from 'lucide-react';
import './liveAlphaPage.css';

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

  const load = async () => {
    setLoading(true); setError('');
    try {
      const [workspaceResponse, statusResponse] = await Promise.all([fetch('/api/market/live-alpha/workspace'), fetch('/api/market/live-alpha/status')]);
      if (!workspaceResponse.ok) throw new Error('Live Alpha research store is unavailable.');
      setPayload(await workspaceResponse.json());
      setRuntime(statusResponse.ok ? await statusResponse.json() : null);
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { document.title = 'Live Alpha | Agarwal Global Investments'; load(); const timer = setInterval(load, 60000); return () => clearInterval(timer); }, []);

  const allRows = useMemo(() => buildRows(payload.signals || []), [payload.signals]);
  const rows = useMemo(() => allRows.filter((row) => strategy === 'all' || row.strategies[strategy]).sort((a, b) => sort === 'confidence' ? b.quality - a.quality : sort === 'age' ? Date.parse(b.newest) - Date.parse(a.newest) : sort === 'sector' ? a.sector.localeCompare(b.sector) : Math.abs(b.composite) - Math.abs(a.composite)), [allRows, strategy, sort]);
  const strategyStats = useMemo(() => Object.fromEntries(STRATEGIES.map(([key]) => {
    const signals = allRows.map((row) => row.strategies[key]).filter((signal) => signal?.direction);
    return [key, { active: signals.length, high: signals.filter((signal) => Number(signal.signal_quality_score) >= 80).length, strongest: signals.sort((a, b) => Math.abs(signedScore(b)) - Math.abs(signedScore(a)))[0] }];
  })), [allRows]);
  const highConfidence = allRows.filter((row) => row.confidence === 'HIGH' || row.confidence === 'VALIDATED').length;
  const selectedRow = selected ? allRows.find((row) => row.symbol === selected) : null;
  const confluence = [...allRows].filter((row) => row.active.length >= 2).sort((a, b) => b.active.length - a.active.length || Math.abs(b.composite) - Math.abs(a.composite)).slice(0, 3);
  const lastUpdate = payload.generated_at ? new Date(payload.generated_at).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—';

  return <div className="la-page">
    <section className="la-command">
      <div className="la-title-row">
        <div><span className="la-eyebrow"><Sparkles size={13} /> AGI research system</span><h1>Live Alpha</h1><p>Independent market behaviours, unified into one institutional signal workspace.</p></div>
        <div className="la-live-meta"><span className={`la-live-dot ${runtime?.status === 'running' ? 'on' : ''}`} />{runtime?.status === 'running' ? 'Live feed' : 'Research standby'}<button onClick={load} aria-label="Refresh"><RefreshCw size={15} className={loading ? 'spin' : ''} /></button></div>
      </div>
      <div className="la-regime">
        <div><small>Market regime</small><strong>{runtime?.last_evaluation?.regime || 'Awaiting classification'}</strong></div>
        <div><small>Nifty bias</small><strong>Not yet classified</strong></div>
        <div><small>Active signals</small><strong>{allRows.filter((row) => row.active.length).length}</strong></div>
        <div><small>High confidence</small><strong>{highConfidence}</strong></div>
        <div><small>Last update</small><strong>{lastUpdate} IST</strong></div>
      </div>
      <div className="la-strategy-grid">
        {STRATEGIES.map(([key, label, technical]) => { const stat = strategyStats[key]; const score = stat?.strongest ? signedScore(stat.strongest) : 0; return <button key={key} onClick={() => setStrategy(strategy === key ? 'all' : key)} className={`la-strategy-card ${strategy === key ? 'active' : ''}`}>
          <span className="la-card-status"><i className={stat?.active ? 'ready' : ''} />{key === 'derivatives_positioning_v1' && runtime?.last_evaluation?.derivatives_status === 'insufficient_derivative_coverage' ? 'Awaiting futures' : stat?.active ? 'Live' : 'Standby'}</span>
          <h2>{label}</h2><p>{technical}</p><div className="la-card-count"><strong>{stat?.active || 0}</strong><span>active<br />{stat?.high || 0} high confidence</span></div>
          <footer><span>Strongest</span><b>{stat?.strongest ? `${stat.strongest.symbol} ${scoreText(score)}` : 'No signal'}</b></footer>
        </button>; })}
      </div>
    </section>

    <main className="la-main">
      <section className="la-panel la-scanner">
        <header><div><span className="la-section-kicker">Opportunity map</span><h2>Live Alpha Scanner</h2></div><div className="la-controls"><select value={sort} onChange={(event) => setSort(event.target.value)} aria-label="Sort scanner"><option value="alpha">Alpha score</option><option value="confidence">Confidence</option><option value="sector">Sector</option><option value="age">Signal age</option></select><span>{rows.length} names</span></div></header>
        {error ? <div className="la-notice error"><AlertCircle size={18} /><div><strong>Workspace unavailable</strong><p>{error}</p></div></div> : null}
        {!loading && !error && !rows.length ? <div className="la-empty"><Activity size={28} /><h3>No live research signals yet</h3><p>The workspace is connected, but AGI has not stored a qualifying signal. Apply the migrations, complete volume baselines, verify the universe, and enable shadow collection when ready.</p></div> : null}
        {rows.length ? <div className="la-table-wrap"><table><thead><tr><th>Stock</th><th>Alpha</th>{STRATEGIES.map(([key]) => <th key={key}>{SHORT[key]}</th>)}<th>Confidence</th><th>Age</th><th /></tr></thead><tbody>{rows.map((row) => <tr key={row.symbol} onClick={() => setSelected(row.symbol)}><td><strong>{row.symbol}</strong><span>{row.sector}</span></td><td><Score value={row.composite} /></td>{STRATEGIES.map(([key]) => <td key={key}><MiniScore signal={row.strategies[key]} /></td>)}<td><span className={`la-confidence ${row.confidence.toLowerCase()}`}>{row.confidence}</span></td><td>{age(row.newest)}</td><td><ChevronRight size={15} /></td></tr>)}</tbody></table></div> : null}
      </section>

      <section className="la-lower-grid">
        <div className="la-panel la-confluence"><header><div><span className="la-section-kicker">Independent confirmation</span><h2>High-Conviction Confluence</h2></div></header>{confluence.length ? confluence.map((row) => <button key={row.symbol} onClick={() => setSelected(row.symbol)}><div><strong>{row.symbol}</strong><span>{row.sector}</span></div><div className="la-model-dots">{STRATEGIES.map(([key]) => <i key={key} className={row.strategies[key]?.direction ? 'on' : ''} title={SHORT[key]} />)}</div><div><b>{row.active.length}/5</b><span>models confirm</span></div><Score value={row.composite} /></button>) : <p className="la-muted-copy">Confluence appears when two or more independent engines flag the same stock.</p>}</div>
        <div className="la-panel la-events"><header><div><span className="la-section-kicker">Signal lifecycle</span><h2>Recent Events</h2></div></header>{(payload.signals || []).filter((signal) => signal.direction).slice(0, 6).map((signal) => <button key={signal.id} onClick={() => setSelected(signal.symbol)}><Clock3 size={14} /><time>{new Date(signal.as_of).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' })}</time><span><b>{signal.symbol}</b> · {String(signal.classification).replaceAll('_', ' ')}</span></button>)}{!(payload.signals || []).some((signal) => signal.direction) ? <p className="la-muted-copy">No signal lifecycle events have been recorded.</p> : null}</div>
      </section>
      <p className="la-disclosure"><ShieldCheck size={14} /> Research signals only. AGI does not generate orders, position sizes, targets, or execution instructions.</p>
    </main>
    {selectedRow ? <ResearchDrawer row={selectedRow} onClose={() => setSelected(null)} /> : null}
  </div>;
}

function Score({ value }) { return <span className={`la-score ${value >= 80 ? 'exceptional up' : value <= -80 ? 'exceptional down' : value > 0 ? 'up' : value < 0 ? 'down' : ''}`}>{scoreText(value)}</span>; }
function MiniScore({ signal }) { const value = signedScore(signal); return signal?.direction ? <span className={`la-mini-score ${value > 0 ? 'up' : 'down'}`}>{scoreText(value)}</span> : <span className="la-dash">—</span>; }

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
