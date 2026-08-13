import { useEffect, useMemo, useState } from 'react';
import { Activity, AlertCircle, BarChart3, ChevronRight, Clock3, RefreshCw, ShieldCheck, Sparkles, X } from 'lucide-react';
import API_ORIGIN from '@/config';
import { CONVICTION_FILTERS, convictionTone, filterConvictionRows, readableConvictionLabel } from '@/lib/evidenceConvictionView';
import { buildCanonicalSignals, LIVE_ALPHA_STRATEGIES, reconcileLiveAlpha, signedSignalScore } from '@/lib/liveAlphaSignalModel';
import './liveAlphaPage.css';
import './growwResearch.css';

const STRATEGIES = LIVE_ALPHA_STRATEGIES;
const SHORT = { cross_sectional_momentum_v1: 'Lead', volume_liquidity_anomaly_v1: 'Act.', opening_range_expansion_v1: 'Break', intraday_mean_reversion_v1: 'Dis.', derivatives_positioning_v1: 'Pos.' };

const signedScore = signedSignalScore;
function scoreText(value) { return `${value > 0 ? '+' : ''}${value}`; }
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

function buildRows(signals, strategyHealth) { return buildCanonicalSignals(signals, strategyHealth); }

function signalReason(row) {
  const interpretation = row.interpretation;
  const scored = (signal) => `${STRATEGIES.find(([key]) => key === signal?.engine)?.[1] || signal?.engine} ${scoreText(signedScore(signal))}`;
  return {
    primary_driver: interpretation.primary_driver ? scored(interpretation.primary_driver) : interpretation.structure === 'CONFLICTING' ? `${scored(interpretation.dominant_positive)} versus ${scored(interpretation.dominant_negative)}` : 'No directional component',
    supporting_factors: interpretation.supporting_components.map(scored),
    negative_factors: interpretation.contradicting_components.map(scored),
    data_quality: row.active.every((signal) => signal.liquidity_ok) ? 'Required live inputs passed liquidity checks' : 'One or more inputs failed liquidity checks',
    confidence_reason: row.samples >= 100 ? 'Supported by comparable completed outcomes' : `${row.confidence} model-state confidence from signal strength, agreement and available inputs; not calibrated to future returns`,
    strategy_sources: interpretation.active_components.map((signal) => STRATEGIES.find(([key]) => key === signal.engine)?.[1] || signal.engine),
  };
}

function OpportunitySummary({ rows, signals, freshness, runtime, onSelect }) {
  const directional = rows.filter((row) => row.active.length);
  const clean = directional.filter((row) => row.signal_structure !== 'CONFLICTING');
  const positive = clean.filter((row) => row.composite > 0).sort((a, b) => b.composite - a.composite);
  const negative = clean.filter((row) => row.composite < 0).sort((a, b) => a.composite - b.composite);
  const conflicting = directional.filter((row) => row.signal_structure === 'CONFLICTING').sort((a, b) => Math.abs(b.composite) - Math.abs(a.composite));
  const liveUniverse = runtime?.universe?.members || new Set(signals.map((signal) => signal.symbol)).size;
  const coreRuns = (runtime?.last_successful_evaluation?.persistence || []).filter((row) => !['derivatives_positioning_v1', 'opening_range_expansion_v1'].includes(row.engine));
  const eligible = Math.max(0, ...coreRuns.map((row) => Number(row.signals) || 0)) || new Set(signals.filter((signal) => signal.engine !== 'derivatives_positioning_v1').map((signal) => signal.symbol)).size;
  const derivativeUniverse = signals.filter((signal) => signal.engine === 'derivatives_positioning_v1').length;
  const strategySignalCount = rows.reduce((sum, row) => sum + row.active.length, 0);
  const reconciliation = reconcileLiveAlpha({ liveUniverse, canonicalSignals: rows, strategySignalCount });
  const confidenceCounts = directional.reduce((counts, row) => ({ ...counts, [row.confidence]: (counts[row.confidence] || 0) + 1 }), {});
  const renderOpportunity = (row) => <button key={row.symbol} onClick={() => onSelect(row.symbol)}><div><strong>{row.symbol}</strong><span>{row.sector}</span></div><Score value={row.composite} /><span className={`la-confidence ${row.confidence.toLowerCase()}`}>{row.confidence}</span><p><b>{row.signal_structure}</b> · {row.interpretation.summary}</p></button>;
  return <section className="la-opportunity-summary">
    <header><div><span className="la-section-kicker">Current research state</span><h2>Opportunity Summary</h2></div><div><strong>{reconciliation.uniqueActiveNames}</strong><span>unique active names<br />Data age {freshness?.age_seconds == null ? 'unavailable' : `${Math.floor(freshness.age_seconds / 60)} min`}</span></div></header>
    <div className="la-universe-stats"><div><span>Live equity universe</span><strong>{liveUniverse}</strong></div><div><span>Core strategy-eligible</span><strong>{eligible}</strong></div><div><span>Derivatives universe</span><strong>{derivativeUniverse}</strong></div><div><span>Strategy-level signals</span><strong>{strategySignalCount}</strong></div></div>
    <div className="la-summary-stats"><div><span>Positive names</span><strong className="positive">{reconciliation.positive}</strong></div><div><span>Negative names</span><strong className="negative">{reconciliation.negative}</strong></div><div><span>Neutral</span><strong>{reconciliation.neutral}</strong></div><div><span>High confidence</span><strong>{(confidenceCounts.HIGH || 0) + (confidenceCounts.VALIDATED || 0)}</strong></div><div><span>Medium confidence</span><strong>{confidenceCounts.MEDIUM || 0}</strong></div><div><span>Low confidence</span><strong>{confidenceCounts.LOW || 0}</strong></div></div>
    {!reconciliation.valid ? <div className="la-integrity-warning">DATA INTEGRITY WARNING — live-universe or active-signal counts do not reconcile.</div> : null}
    <div className="la-summary-lists"><article><h3>Strongest positive research signals</h3>{positive.slice(0, 5).map(renderOpportunity)}{!positive.length ? <p>No positive signal currently passes the configured rules.</p> : null}</article><article><h3>Negative / weakening signals</h3>{negative.slice(0, 5).map(renderOpportunity)}{!negative.length ? <p>No negative signal currently passes the configured rules.</p> : null}</article>{conflicting.length ? <article className="la-conflicting"><h3>Conflicting / mixed signals</h3>{conflicting.slice(0, 5).map(renderOpportunity)}</article> : null}</div>
    <footer><b>Research Signal — validation pending.</b> Rankings prioritize current signal strength, then component agreement and data completeness. These are not recommendations or demonstrated predictive alpha.</footer>
  </section>;
}

function StrategyHealth({ payload, runtime }) {
  const signals = payload.signals || [];
  const rows = STRATEGIES.map(([key, label, name]) => {
    const engineRows = signals.filter((signal) => signal.engine === key);
    const classes = Object.fromEntries([...new Set(engineRows.map((row) => row.classification))].map((value) => [value, engineRows.filter((row) => row.classification === value).length]));
    const active = engineRows.filter((row) => row.direction).length;
    const health = payload.strategy_health?.[key];
    const unavailable = key === 'opening_range_expansion_v1' && runtime?.last_successful_evaluation?.opening_range_status === 'opening_range_not_restored';
    const rejection = unavailable ? 'Opening window unavailable' : key === 'intraday_mean_reversion_v1' ? `${classes.trend_filtered || 0} trend, ${classes.event_volume_filtered || 0} event volume` : key === 'derivatives_positioning_v1' ? `${classes.neutral || 0} thresholds not jointly met` : '—';
    return { key, label, name, evaluated: engineRows.length || null, active, health, unavailable, rejection, accounted: key !== 'intraday_mean_reversion_v1' || engineRows.length === active + Object.entries(classes).filter(([classification]) => !classification.includes('candidate')).reduce((sum, [, count]) => sum + count, 0) };
  });
  const degraded = rows.some((row) => row.unavailable || ['persistence_failed', 'stale'].includes(row.health?.status));
  return <section className="la-panel la-health"><header><div><span className="la-section-kicker">Independent pipeline status</span><h2>Strategy Health</h2></div><span className={degraded ? 'degraded' : 'ready'}>{degraded ? 'Operational with degraded strategy' : 'Operational'}</span></header><div className="la-table-wrap"><table><thead><tr><th>Strategy</th><th>Status</th><th>Evaluated</th><th>Signals</th><th>Rejections</th><th>Data state</th></tr></thead><tbody>{rows.map((row) => <tr key={row.key}><td><strong>{row.label}</strong><span>{row.name}</span></td><td>{row.unavailable ? 'Degraded' : row.health?.status === 'ready' ? row.active ? 'Operational' : 'Operational / No signal' : row.health?.status || 'Not run'}</td><td>{row.evaluated ?? '—'}</td><td>{row.evaluated == null ? '—' : row.active}</td><td>{row.rejection}{row.key === 'intraday_mean_reversion_v1' ? <small className={row.accounted ? 'ok' : 'warning'}>{row.accounted ? 'All instruments accounted for' : 'Data integrity warning'}</small> : null}</td><td>{row.unavailable ? 'Recovery next session' : row.health?.status === 'ready' ? 'Ready' : 'Unavailable'}</td></tr>)}</tbody></table></div></section>;
}

function Observability({ rows, signals, runtime }) {
  const scores = rows.filter((row) => row.active.length).map((row) => row.composite);
  const sorted = [...scores].sort((a, b) => a - b);
  const average = scores.length ? scores.reduce((sum, value) => sum + value, 0) / scores.length : 0;
  const median = sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0;
  const deviation = scores.length ? Math.sqrt(scores.reduce((sum, value) => sum + ((value - average) ** 2), 0) / scores.length) : 0;
  const extremes = scores.filter((value) => Math.abs(value) === 99).length;
  const concentrationWarning = scores.length >= 10 && extremes / scores.length >= 0.2;
  const feed = runtime?.feed || {};
  const observed = new Set(signals.map((signal) => signal.instrument_key).filter(Boolean)).size;
  const expected = runtime?.universe?.subscribed_instruments || feed.subscribed_instruments || null;
  const missing = expected == null ? null : Math.max(0, expected - observed);
  const coverageStatus = missing === 0 ? 'Complete' : missing == null ? 'Unavailable' : 'Partial / Review required';
  return <section className="la-observability">
    <article className="la-panel"><header><div><span className="la-section-kicker">Transport is not data quality</span><h2>Upstox Feed Health</h2></div><span className={feed.status === 'connected' ? 'ready' : 'degraded'}>Transport {feed.status || 'Unavailable'}</span></header><div className="la-observe-grid"><div><small>Messages received</small><strong>{Number(feed.messages || 0).toLocaleString('en-IN')}</strong></div><div><small>Reconnects</small><strong>{feed.reconnects ?? '—'}</strong></div><div><small>Decode errors</small><strong>{feed.decode_errors ?? '—'}</strong></div><div><small>Expected subscriptions</small><strong>{expected ?? '—'}</strong></div><div><small>Observed latest runs</small><strong>{observed}</strong></div><div><small>Unexpectedly missing</small><strong>{missing ?? '—'}</strong></div><div><small>Input coverage</small><strong>{coverageStatus}</strong></div><div><small>Last heartbeat</small><strong>{feed.last_message_at ? age(feed.last_message_at) : '—'}</strong></div><div><small>Tick-order checks</small><strong>Not instrumented</strong></div></div><footer>Connected transport does not independently establish complete inputs or strategy correctness. Intentional exclusions are not currently reported separately, so missing coverage remains review-required.</footer></article>
    <article className="la-panel"><header><div><span className="la-section-kicker">Distribution monitor</span><h2>Signal Diagnostics</h2></div><span className={concentrationWarning ? 'degraded' : 'ready'}>{concentrationWarning ? 'Concentration warning' : 'Observed'}</span></header><div className="la-observe-grid"><div><small>Directional names</small><strong>{scores.length}</strong></div><div><small>+99 / -99 scores</small><strong>{extremes}</strong></div><div><small>Average score</small><strong>{average.toFixed(1)}</strong></div><div><small>Median score</small><strong>{median.toFixed(1)}</strong></div><div><small>Standard deviation</small><strong>{deviation.toFixed(1)}</strong></div><div><small>20-day signal median</small><strong>Collecting</strong></div></div><footer>{concentrationWarning ? 'An unusually large share of current research signals is at the score boundary.' : 'No configured score-concentration threshold is currently breached.'} Signal-count anomaly comparison begins after sufficient daily history accumulates.</footer></article>
  </section>;
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

  const allRows = useMemo(() => buildRows(payload.signals || [], payload.strategy_health || {}), [payload.signals, payload.strategy_health]);
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
          <footer><span>{isFresh ? 'Strongest' : 'Last stored'}<small>{health?.stored_signals ? `${health.stored_signals} evaluated` : key === 'opening_range_expansion_v1' ? 'Execution unavailable' : 'Not evaluated'}</small></span><b>{stat?.strongest ? `${stat.strongest.symbol} ${scoreText(score)}` : 'No signal'}</b></footer>
        </button>; })}
      </div>
    </section>

    <main className="la-main">
      <nav className="la-view-tabs" aria-label="Live Alpha views">
        <button className={view === 'signals' ? 'active' : ''} onClick={() => setView('signals')}><Activity size={15} /> Strategy signals</button>
        <button className={view === 'conviction' ? 'active' : ''} onClick={() => setView('conviction')}><ShieldCheck size={15} /> Conviction</button>
      </nav>
      {view === 'signals' ? <>
      <OpportunitySummary rows={allRows} signals={payload.signals || []} freshness={payload.freshness} runtime={runtime} onSelect={setSelected} />
      <StrategyHealth payload={payload} runtime={runtime} />
      <Observability rows={allRows} signals={payload.signals || []} runtime={runtime} />
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
  const reason = signalReason(row);
  const interpretation = row.interpretation;
  const roleFor = (signal) => !signal?.direction ? row.component_states[signal?.engine] || 'Inactive' : interpretation.structure === 'CONFLICTING' ? signal.direction === 'positive' ? 'Dominant positive' : 'Dominant negative' : signal === interpretation.primary_driver ? 'Primary' : signal.direction === interpretation.primary_driver?.direction ? 'Supporting' : 'Contradicting';
  return <div className="la-drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><aside className="la-drawer">
    <header><div><span>{row.sector}</span><h2>{row.symbol}</h2></div><button onClick={onClose} aria-label="Close research drawer"><X size={20} /></button></header>
    <section className="la-drawer-score"><div><small>Research Signal Score</small><Score value={row.composite} /></div><div><small>Confidence</small><strong>{row.confidence}</strong></div><div><small>Agreement</small><strong>{row.agreement}</strong></div><div><small>Signal age</small><strong>{age(row.newest)}</strong></div></section>
    <section className="la-what"><h3>Research summary</h3><p>{interpretation.summary} The signal is operational and fresh, but predictive validity has not yet been established.</p></section>
    <section><h3>Why flagged</h3><ol className="la-why-list">{interpretation.why_flagged.map((item) => <li key={item}>{item}</li>)}</ol></section>
    <section><h3>Signal components</h3><div className="la-component-table"><div><b>Component</b><b>Score</b><b>State</b><b>Role</b></div>{STRATEGIES.map(([key, label]) => { const signal = row.strategies[key]; return <div key={key}><span>{label}</span><MiniScore signal={signal} /><span>{row.component_states[key]}</span><span>{roleFor(signal || { engine: key })}</span></div>; })}</div><p className="la-confidence-copy">Composite score follows the existing scoring framework. Component scores are contributing signals and are not necessarily additive.</p></section>
    <section><h3>Live evidence</h3><div className="la-evidence"><div><span>15m residual</span><b>{formatFactor(factors.residual_15m ?? lead?.residual_15m, '%')}</b></div><div><span>Volume vs expected</span><b>{Number(lead?.volume_ratio || factors.volume_surprise || 0) ? `${Number(lead?.volume_ratio || factors.volume_surprise).toFixed(2)}×` : '—'}</b></div><div><span>Opening range</span><b>{factors.breakout_pct != null ? `${formatFactor(factors.breakout_pct, '%')} break` : '—'}</b></div><div><span>OI change</span><b>{formatFactor(factors.oi_change_15m ?? lead?.oi_change, '%')}</b></div></div></section>
    <section className="la-what"><h3>Why {row.symbol} surfaced</h3><p>{explain(row)}</p><ul>{reason.supporting_factors.map((factor) => <li key={factor}>{factor}</li>)}{reason.negative_factors.map((factor) => <li key={factor}>Opposing: {factor}</li>)}</ul></section>
    <section><h3>Data quality</h3><div className="la-evidence"><div><span>Price data</span><b>{lead?.price_at_signal ? 'READY' : 'UNAVAILABLE'}</b></div><div><span>Volume data</span><b>{lead?.volume_ratio != null || factors.volume_surprise != null ? 'READY' : 'NOT REQUIRED'}</b></div><div><span>Derivative data</span><b>{row.strategies.derivatives_positioning_v1 ? 'READY' : 'NOT REQUIRED'}</b></div><div><span>Liquidity checks</span><b>{reason.data_quality}</b></div><div><span>Timestamp</span><b>{new Date(row.newest).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST</b></div></div></section>
    <section><h3>Confidence basis</h3><p className="la-confidence-copy">{reason.confidence_reason}. Confidence is model-state confidence, not probability of positive future return.</p></section>
    <section><h3>Historical validation</h3>{row.samples ? <div className="la-validation"><div><span>Comparable signals</span><b>{row.samples.toLocaleString('en-IN')}</b></div><div><span>Empirical confidence</span><b>{row.quality}%</b></div></div> : <div className="la-notice"><BarChart3 size={18} /><div><strong>Collecting evidence</strong><p>Signal quality is live, but empirical confidence remains unvalidated until enough forward outcomes are complete.</p></div></div>}</section>
    <section><h3>Research status</h3><div className="la-evidence"><div><span>Lifecycle</span><b>Operational</b></div><div><span>Validation</span><b>Research Signal — validation pending</b></div><div><span>Permitted use</span><b>Research prioritisation</b></div><div><span>Execution</span><b>Blocked</b></div><div><span>Signal ID</span><b>{lead?.id || 'Unavailable'}</b></div><div><span>Data cutoff</span><b>{row.newest}</b></div></div></section>
    <section className="la-condition-grid"><div><h3>What would strengthen</h3><ul>{interpretation.strengthening_conditions.map((item) => <li key={item}>{item}</li>)}</ul></div><div><h3>What could weaken</h3><ul>{interpretation.weakening_conditions.map((item) => <li key={item}>{item}</li>)}</ul></div></section>
    <section><h3>Research caveats</h3><ul className="la-caveats">{interpretation.caveats.map((item) => <li key={item}>{item}</li>)}<li>This is a research signal, not an investment recommendation.</li><li>Transport health does not independently establish input completeness.</li></ul></section>
    <details className="la-lineage"><summary>Data lineage</summary><p>Market feed → Instrument mapping → Normalization → Timestamp validation → Liquidity checks → Strategy input → Component score → Composite score → Signal interpretation → Confidence → Immutable research snapshot.</p><dl><dt>Data cutoff</dt><dd>{row.data_cutoff}</dd><dt>Strategy version</dt><dd>{row.strategy_version}</dd><dt>Model version</dt><dd>{row.model_version}</dd><dt>Input fingerprint</dt><dd>{row.data_fingerprint || 'Unavailable'}</dd></dl></details>
    <section className="la-what"><h3>Research interpretation</h3><p>{explain(row)}</p></section>
  </aside></div>;
}

function explain(row) {
  const reason = signalReason(row);
  const names = reason.strategy_sources;
  const direction = row.composite >= 0 ? 'positive' : 'negative';
  if (!names.length) return 'No active directional research classification is present.';
  return `${row.symbol} has a ${direction} research signal score of ${scoreText(row.composite)}. The primary measurable driver is ${reason.primary_driver}. ${names.join(', ')} ${names.length === 1 ? 'is' : 'are'} contributing evidence and component agreement is ${row.agreement.toLowerCase()}. ${row.samples ? 'Comparable completed outcomes are available.' : 'The signal is operational but has not accumulated enough outcomes for empirical validation.'}`;
}
