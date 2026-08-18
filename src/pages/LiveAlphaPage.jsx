import { useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertCircle, ChevronRight, HelpCircle, Info, RefreshCw, Search, ShieldCheck, X,
} from 'lucide-react';
import API_ORIGIN from '@/config';
import { CONVICTION_FILTERS, convictionTone, filterConvictionRows, readableConvictionLabel } from '@/lib/evidenceConvictionView';
import {
  buildLiveBrief,
  buildMarketBehaviorRows,
  buildMarketMap,
  ENGINE_PLAIN,
  evidenceStrengthLabel,
  filterRadarRows,
  marketStateFromBrief,
  plainSignalDirection,
  radarReason,
  sortRadarRows,
} from '@/lib/liveAlphaDashboardModel';
import { buildCanonicalSignals, LIVE_ALPHA_STRATEGIES, signedSignalScore } from '@/lib/liveAlphaSignalModel';
import './liveAlphaPage.css';

const STRATEGIES = LIVE_ALPHA_STRATEGIES;
const SHORT = {
  cross_sectional_momentum_v1: 'Lead',
  volume_liquidity_anomaly_v1: 'Act.',
  opening_range_expansion_v1: 'Break',
  intraday_mean_reversion_v1: 'Dis.',
  derivatives_positioning_v1: 'Pos.',
};

function scoreText(value) { return `${value > 0 ? '+' : ''}${value}`; }
function formatFactor(value, suffix = '') {
  const number = Number(value);
  return Number.isFinite(number) ? `${number > 0 ? '+' : ''}${number.toFixed(2)}${suffix}` : '—';
}
function age(iso) {
  const mins = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000));
  if (!Number.isFinite(mins)) return '—';
  if (mins < 1) return 'Now';
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h`;
}
function ageSecondsLabel(seconds) {
  if (seconds == null || !Number.isFinite(Number(seconds))) return '—';
  const s = Math.max(0, Math.floor(Number(seconds)));
  if (s < 60) return `${s} sec ago`;
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

async function readApiJson(response, label) {
  const contentType = response.headers.get('content-type') || '';
  if (!response.ok) throw new Error(`${label} is unavailable (${response.status}).`);
  if (!contentType.toLowerCase().includes('application/json')) {
    throw new Error(`${label} returned the website shell instead of API data. Check the configured backend origin.`);
  }
  return response.json();
}

function StrengthBar({ value, max = 99 }) {
  const pct = Math.min(100, Math.round((Math.abs(Number(value) || 0) / max) * 100));
  const tone = value > 0 ? 'up' : value < 0 ? 'down' : '';
  return (
    <span className={`la-strength ${tone}`}>
      <span className="la-strength-track"><i style={{ width: `${pct}%` }} /></span>
      <b>{Math.abs(Number(value) || 0)}</b>
    </span>
  );
}

function BehaviorMeter({ bars = 0 }) {
  return (
    <span className="la-meter" aria-hidden>
      {Array.from({ length: 5 }).map((_, i) => <i key={i} className={i < bars ? 'on' : ''} />)}
    </span>
  );
}

function UnavailableCard({ title, reason }) {
  return (
    <div className="la-card la-unavailable">
      <header><span className="la-kicker">Unavailable</span><h2>{title}</h2></header>
      <p>{reason}</p>
    </div>
  );
}

export default function LiveAlphaPage() {
  const [payload, setPayload] = useState({ signals: [], runs: [] });
  const [runtime, setRuntime] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);
  const [strategy, setStrategy] = useState('all');
  const [filter, setFilter] = useState('all');
  const [sort, setSort] = useState('strength');
  const [search, setSearch] = useState('');
  const [sector, setSector] = useState('');
  const [view, setView] = useState('live');
  const [healthOpen, setHealthOpen] = useState(false);
  const [behaviorHelp, setBehaviorHelp] = useState(false);
  const [conviction, setConviction] = useState({ run: null, rows: [] });
  const [convictionFilter, setConvictionFilter] = useState('shortlist');
  const [convictionError, setConvictionError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      if (!API_ORIGIN) throw new Error('AGI backend origin is not configured.');
      const [workspaceResponse, statusResponse] = await Promise.all([
        fetch(`${API_ORIGIN}/api/market/live-alpha/workspace`, { headers: { Accept: 'application/json' } }),
        fetch(`${API_ORIGIN}/api/market/live-alpha/status`, { headers: { Accept: 'application/json' } }),
      ]);
      setPayload(await readApiJson(workspaceResponse, 'Live Alpha research store'));
      setRuntime(await readApiJson(statusResponse, 'Live Alpha runtime'));
      try {
        const convictionResponse = await fetch(`${API_ORIGIN}/api/market/evidence-conviction?limit=500`, { headers: { Accept: 'application/json' } });
        setConviction(await readApiJson(convictionResponse, 'Conviction ranking'));
        setConvictionError('');
      } catch (convictionRequestError) {
        setConvictionError(convictionRequestError.message);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    document.title = 'Live Alpha | Agarwal Global Investments';
    load();
    const timer = setInterval(load, 60000);
    return () => clearInterval(timer);
  }, []);

  const allRows = useMemo(
    () => buildCanonicalSignals(payload.signals || [], payload.strategy_health || {}),
    [payload.signals, payload.strategy_health],
  );
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

  const brief = useMemo(() => buildLiveBrief(allRows, { isFresh }), [allRows, isFresh]);
  const marketState = useMemo(() => marketStateFromBrief(brief), [brief]);
  const behaviorRows = useMemo(
    () => buildMarketBehaviorRows(allRows, payload.strategy_health || {}, isFresh),
    [allRows, payload.strategy_health, isFresh],
  );
  const marketMap = useMemo(() => buildMarketMap(allRows, { isFresh }), [allRows, isFresh]);

  const activeFilter = strategy !== 'all' ? strategy : filter;
  const radarRows = useMemo(() => {
    const filtered = filterRadarRows(allRows, activeFilter, { search, sector });
    return sortRadarRows(filtered, sort === 'strength' ? 'strength' : sort);
  }, [allRows, activeFilter, search, sector, sort]);

  const confluence = useMemo(
    () => [...allRows]
      .filter((row) => row.active.length >= 2)
      .sort((a, b) => b.active.length - a.active.length || Math.abs(b.composite) - Math.abs(a.composite)),
    [allRows],
  );
  const topConfirmation = confluence[0] || null;
  const selectedRow = selected ? allRows.find((row) => row.symbol === selected) : null;
  const lastUpdate = payload.freshness?.latest_successful_at
    ? new Date(payload.freshness.latest_successful_at).toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
    })
    : 'No completed run';

  const onStrategySelect = (engine) => {
    setStrategy((current) => (current === engine ? 'all' : engine));
    setFilter('all');
  };

  return (
    <div className="la-page">
      <header className="la-command">
        <div className="la-command-left">
          <h1>AGI Live Alpha</h1>
          <p>Live market intelligence · Research only</p>
        </div>
        <div className="la-command-right">
          <span className={`la-status-pill ${liveNow ? 'live' : ''}`}>
            <i />
            {liveNow ? 'LIVE' : displayStatus}
          </span>
          <span className="la-updated">{ageSecondsLabel(payload.freshness?.age_seconds)}</span>
          <button type="button" className="la-icon-btn" onClick={load} aria-label="Refresh">
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
          </button>
          <button type="button" className="la-ghost-btn" onClick={() => setHealthOpen(true)}>
            System Health
          </button>
        </div>
      </header>

      <main className="la-shell">
        <nav className="la-tabs" aria-label="Live Alpha views">
          <button type="button" className={view === 'live' ? 'active' : ''} onClick={() => setView('live')}>
            <Activity size={14} /> Live Intelligence
          </button>
          <button type="button" className={view === 'conviction' ? 'active' : ''} onClick={() => setView('conviction')}>
            <ShieldCheck size={14} /> Conviction
          </button>
        </nav>

        {view === 'live' ? (
          <>
            <section className="la-glance" aria-label="Market at a glance">
              <GlanceCard label="Market state" value={marketState.label} detail={marketState.detail} tone={marketState.tone} />
              <GlanceCard label="Nifty bias" value="Awaiting model" detail="Not yet classified" tone="neutral" />
              <GlanceCard
                label="Signals"
                value={isFresh ? String(brief.breadth.active) : '0'}
                detail={`${isFresh ? brief.breadth.high_evidence : 0} high evidence`}
                tone="info"
              />
              <GlanceCard
                label="Confluence"
                value={isFresh ? String(brief.breadth.multi) : '0'}
                detail={`${isFresh ? brief.breadth.conflicts : 0} conflicts`}
                tone="info"
              />
              <GlanceCard
                label="Evidence"
                value={brief.evidence_strength}
                detail={liveNow ? 'Fresh session' : displayStatus}
                tone={brief.evidence_strength === 'HIGH' ? 'positive' : brief.evidence_strength === 'LOW' ? 'warning' : 'neutral'}
              />
            </section>

            <section className="la-row-brief">
              <LiveBriefCard brief={brief} />
              <MarketBehaviorCard
                rows={behaviorRows}
                active={strategy}
                onSelect={onStrategySelect}
                helpOpen={behaviorHelp}
                onToggleHelp={() => setBehaviorHelp((v) => !v)}
              />
            </section>

            <section className="la-row-main">
              <MarketMapCard map={marketMap} />
              <UnavailableCard
                title="Emerging Now"
                reason="Biggest changes need historical Live Alpha score snapshots. That history is not exposed by the current workspace API, so change tracking stays unavailable rather than estimated."
              />
              <OpportunityRadar
                rows={radarRows}
                error={error}
                displayStatus={displayStatus}
                liveNow={liveNow}
                loading={loading}
                payload={payload}
                lastUpdate={lastUpdate}
                filter={filter}
                strategy={strategy}
                sort={sort}
                search={search}
                sector={sector}
                onFilter={(next) => { setFilter(next); setStrategy('all'); }}
                onSort={setSort}
                onSearch={setSearch}
                onSector={setSector}
                onSelect={setSelected}
                onClearStrategy={() => setStrategy('all')}
              />
            </section>

            <section className="la-row-lower">
              <ConfirmationCard row={isFresh ? topConfirmation : null} onOpen={setSelected} />
              <UnavailableCard
                title="Signal Evolution"
                reason="Not enough intraday history is available from the workspace API to plot composite and engine scores over time."
              />
              <UnavailableCard
                title="What Changed"
                reason="Since/delta comparisons require prior snapshots. Implement snapshot history on the backend before enabling this card."
              />
              <EodResearchCard groww={payload.groww} />
            </section>
          </>
        ) : (
          <ConvictionPanel
            payload={conviction}
            error={convictionError}
            filter={convictionFilter}
            onFilter={setConvictionFilter}
          />
        )}

        <p className="la-disclosure">
          <ShieldCheck size={13} />
          Research only. Not investment advice. AGI does not generate orders, position sizes, targets, or execution instructions.
        </p>
      </main>

      {selectedRow ? <ResearchDrawer row={selectedRow} onClose={() => setSelected(null)} /> : null}
      {healthOpen ? (
        <SystemHealthDrawer
          payload={payload}
          runtime={runtime}
          displayStatus={displayStatus}
          onClose={() => setHealthOpen(false)}
        />
      ) : null}
    </div>
  );
}

function GlanceCard({ label, value, detail, tone = 'neutral' }) {
  return (
    <article className={`la-glance-card tone-${tone}`}>
      <small>{label}</small>
      <strong>{value}</strong>
      <span>{detail}</span>
    </article>
  );
}

function LiveBriefCard({ brief }) {
  return (
    <article className="la-card la-brief">
      <header>
        <div>
          <span className="la-kicker">AGI intelligence</span>
          <h2>AGI Live Brief</h2>
        </div>
        <time>{brief.time_label}</time>
      </header>
      <p className="la-brief-headline">{brief.headline}</p>
      {brief.sector_line ? <p className="la-brief-sector">{brief.sector_line}</p> : null}
      {brief.notable?.length ? (
        <div className="la-notable">
          <small>Notable now</small>
          <ul>
            {brief.notable.map((item) => (
              <li key={`${item.symbol}-${item.direction}`}>
                <span className={item.direction === 'up' ? 'up' : 'down'}>{item.direction === 'up' ? '↑' : '↓'} {item.symbol}</span>
                <em>{item.line}</em>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <footer>
        Evidence strength
        <b className={`la-pill ${String(brief.evidence_strength).toLowerCase()}`}>{brief.evidence_strength}</b>
      </footer>
    </article>
  );
}

function MarketBehaviorCard({ rows, active, onSelect, helpOpen, onToggleHelp }) {
  return (
    <article className="la-card la-behavior">
      <header>
        <div>
          <span className="la-kicker">Behaviours</span>
          <h2>Market Behavior Today</h2>
        </div>
        <button type="button" className="la-text-btn" onClick={onToggleHelp}>
          <HelpCircle size={13} /> What do these mean?
        </button>
      </header>
      {helpOpen ? (
        <div className="la-help">
          {rows.map((row) => (
            <div key={row.engine}>
              <strong>{row.label}</strong>
              <p>{row.plain}</p>
              <small>{row.technical}</small>
            </div>
          ))}
        </div>
      ) : null}
      <div className="la-behavior-list">
        {rows.map((row) => (
          <button
            key={row.engine}
            type="button"
            className={active === row.engine ? 'active' : ''}
            onClick={() => onSelect(row.engine)}
          >
            <span className="la-behavior-name">{row.label}</span>
            <BehaviorMeter bars={row.intensity.bars} />
            <span className={`la-intensity ${row.intensity.key}`}>{row.intensity.label}</span>
            <strong>{row.active}</strong>
          </button>
        ))}
      </div>
    </article>
  );
}

function MarketMapCard({ map }) {
  if (!map.available) {
    return <UnavailableCard title="Market Map" reason={map.reason} />;
  }
  return (
    <article className="la-card la-map">
      <header>
        <div>
          <span className="la-kicker">Where activity is happening</span>
          <h2>Market Map</h2>
        </div>
      </header>
      <div className="la-map-wrap">
        <table>
          <thead>
            <tr>
              <th>Sector</th>
              {map.engines.map((engine) => <th key={engine}>{ENGINE_PLAIN[engine].label}</th>)}
            </tr>
          </thead>
          <tbody>
            {map.sectors.map((row) => (
              <tr key={row.sector}>
                <td>{row.sector}</td>
                {map.engines.map((engine) => {
                  const cell = row.cells[engine];
                  return <td key={engine} className={`cell-${cell.tone}`} title={cell.label}>{cell.mark}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <footer className="la-map-legend">
        <span>+++ Strong</span><span>++ Above normal</span><span>+ Supportive</span><span>− Below normal</span><span>−− Weak</span>
      </footer>
    </article>
  );
}

function OpportunityRadar({
  rows, error, displayStatus, liveNow, loading, payload, lastUpdate,
  filter, strategy, sort, search, sector,
  onFilter, onSort, onSearch, onSector, onSelect, onClearStrategy,
}) {
  const chips = [
    ['all', 'All'], ['positive', 'Positive'], ['negative', 'Negative'], ['high', 'High Evidence'],
    ['multi', 'Multi-Factor'], ['conflicting', 'Conflicting'],
    ...STRATEGIES.map(([engine, label]) => [engine, label]),
  ];
  return (
    <article className="la-card la-radar">
      <header>
        <div>
          <span className="la-kicker">Opportunity map</span>
          <h2>Live Opportunity Radar</h2>
          <p>Research prioritisation — not trade recommendations.</p>
        </div>
        <span className="la-count">{rows.length} names</span>
      </header>

      <div className="la-radar-filters">
        <div className="la-chips">
          {chips.map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={(strategy !== 'all' ? strategy : filter) === key ? 'active' : ''}
              onClick={() => onFilter(key)}
            >
              {label}
            </button>
          ))}
          {strategy !== 'all' ? (
            <button type="button" className="la-clear" onClick={onClearStrategy}>Clear behaviour</button>
          ) : null}
        </div>
        <div className="la-radar-controls">
          <label className="la-search">
            <Search size={13} />
            <input value={search} onChange={(e) => onSearch(e.target.value)} placeholder="Search company" />
          </label>
          <input className="la-sector-input" value={sector} onChange={(e) => onSector(e.target.value)} placeholder="Sector" />
          <select value={sort} onChange={(e) => onSort(e.target.value)} aria-label="Sort radar">
            <option value="strength">Strength</option>
            <option value="change">Biggest change</option>
            <option value="newest">Newest</option>
            <option value="confirmed">Most confirmed</option>
          </select>
        </div>
      </div>

      {error ? (
        <div className="la-notice error"><AlertCircle size={16} /><div><strong>Workspace unavailable</strong><p>{error}</p></div></div>
      ) : null}
      {!error && !liveNow ? (
        <div className="la-notice">
          <AlertCircle size={16} />
          <div>
            <strong>{displayStatus}</strong>
            <p>
              {payload.readiness?.status === 'persistence_degraded'
                ? `Signal storage failed for: ${(payload.readiness.degraded_engines || []).map((key) => SHORT[key] || key).join(', ')}.`
                : evaluationCopy(displayStatus, lastUpdate, payload)}
            </p>
          </div>
        </div>
      ) : null}
      {!loading && !error && !rows.length ? (
        <div className="la-empty">
          <Activity size={24} />
          <h3>{payload.readiness?.status === 'database_setup_required' ? 'Alpha database setup required' : 'No live research signals yet'}</h3>
          <p>
            {payload.readiness?.status === 'database_setup_required'
              ? 'Apply the Live Alpha Supabase migrations. The workspace stays in standby until research tables exist.'
              : 'The workspace is connected, but AGI has not stored a qualifying directional signal for the current filters.'}
          </p>
        </div>
      ) : null}

      {rows.length ? (
        <div className="la-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Signal</th>
                <th>Strength</th>
                <th>Confirmed by</th>
                <th>Change</th>
                <th>Main reason</th>
                <th>Age</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const direction = plainSignalDirection(row);
                return (
                  <tr key={row.symbol} onClick={() => onSelect(row.symbol)}>
                    <td>
                      <strong>{row.symbol}</strong>
                      <span>{row.sector}</span>
                    </td>
                    <td><span className={`la-dir ${direction.key}`}>{direction.key === 'positive' ? '▲' : direction.key === 'negative' ? '▼' : '◆'} {direction.label}</span></td>
                    <td><StrengthBar value={row.composite} /></td>
                    <td>{row.active.length} engine{row.active.length === 1 ? '' : 's'}</td>
                    <td className="la-muted">Unavailable</td>
                    <td>{radarReason(row)}</td>
                    <td>{age(row.newest)}</td>
                    <td><ChevronRight size={14} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
      <footer className="la-radar-foot">
        Strength is a research score on a ±99 scale — not a probability and never shown as a percent.
      </footer>
    </article>
  );
}

function evaluationCopy(displayStatus, lastUpdate, payload) {
  if (displayStatus === 'Warming up') {
    return 'The market feed is connected, but strategies are collecting enough benchmark history before evaluation.';
  }
  if (payload.freshness?.latest_successful_at) {
    return `Displayed observations are historical. Last completed run: ${lastUpdate}.`;
  }
  return 'No completed strategy run is available yet.';
}

function ConfirmationCard({ row, onOpen }) {
  if (!row) {
    return (
      <UnavailableCard
        title="Multi-Engine Confirmation"
        reason="Confirmation appears when two or more independent Live Alpha engines flag the same company in fresh evidence."
      />
    );
  }
  const direction = plainSignalDirection(row);
  return (
    <article className="la-card la-confirm">
      <header>
        <div>
          <span className="la-kicker">Evidence confirmation</span>
          <h2>Multi-Engine Confirmation</h2>
          <p>Multiple independent Live Alpha models are seeing the same company.</p>
        </div>
      </header>
      <button type="button" className="la-confirm-hero" onClick={() => onOpen(row.symbol)}>
        <div>
          <strong>{row.symbol}</strong>
          <span className={`la-dir ${direction.key}`}>{direction.label} structure</span>
        </div>
        <div className="la-confirm-score">
          <b>{Math.abs(row.composite)}</b>
          <small>/ 99</small>
        </div>
      </button>
      <p className="la-confirm-meta">{row.active.length} of 5 engines supportive · Evidence {evidenceStrengthLabel(row.confidence)} · Age {age(row.newest)}</p>
      <div className="la-confirm-bars">
        {STRATEGIES.map(([engine, label]) => {
          const signal = row.strategies[engine];
          const score = signedSignalScore(signal);
          const pct = Math.min(100, Math.abs(score));
          return (
            <div key={engine}>
              <span>{label}</span>
              <i><b style={{ width: `${pct}%` }} className={score > 0 ? 'up' : score < 0 ? 'down' : ''} /></i>
              <em>{signal?.direction ? scoreText(score) : 'Neutral'}</em>
            </div>
          );
        })}
      </div>
      <footer>Structure · {row.signal_structure}</footer>
    </article>
  );
}

function EodResearchCard({ groww }) {
  const runs = new Map((groww?.runs || []).map((run) => [run.strategy, run]));
  const sectorRun = runs.get('agi_sector_rotation_v1');
  const equityRun = runs.get('agi_equity_opportunity_v1');
  return (
    <article className="la-card la-eod">
      <header>
        <div>
          <span className="la-kicker">Scheduled</span>
          <h2>Scheduled / EOD Research</h2>
        </div>
        <span className="la-tip" title="Groww scheduled research is excluded from the five-model Live Alpha composite until comparably validated.">
          <Info size={12} /> Not in composite
        </span>
      </header>
      <div className="la-eod-grid">
        <div>
          <small>Sector Rotation</small>
          <strong>EOD research</strong>
          <span>{sectorRun ? `Last update ${age(sectorRun.as_of)}` : 'Awaiting run'}</span>
        </div>
        <div>
          <small>Equity Opportunities</small>
          <strong>EOD research</strong>
          <span>{equityRun ? `Last update ${age(equityRun.as_of)}` : 'Awaiting run'}</span>
        </div>
      </div>
      {(groww?.sectors || []).length || (groww?.equities || []).length ? (
        <div className="la-eod-preview">
          {(groww?.sectors || []).slice(0, 3).map((row) => (
            <span key={row.sector}>{row.sector} · {Number(row.score).toFixed(0)}</span>
          ))}
          {(groww?.equities || []).slice(0, 3).map((row) => (
            <span key={row.symbol}>{row.symbol} · {Number(row.score).toFixed(0)}</span>
          ))}
        </div>
      ) : (
        <p className="la-muted-copy">No scheduled research run has been received yet.</p>
      )}
    </article>
  );
}

function SystemHealthDrawer({ payload, runtime, displayStatus, onClose }) {
  const feed = runtime?.feed || {};
  const health = payload.strategy_health || {};
  return (
    <div className="la-drawer-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <aside className="la-drawer la-health-drawer">
        <header>
          <div>
            <span>Operations</span>
            <h2>System Health</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </header>
        <section>
          <h3>Overall</h3>
          <div className="la-health-row"><span>Page status</span><b>{displayStatus}</b></div>
          <div className="la-health-row"><span>Runtime</span><b>{runtime?.status || 'Unavailable'}</b></div>
          <div className="la-health-row"><span>Evaluation</span><b>{runtime?.evaluation_status || 'Unavailable'}</b></div>
          <div className="la-health-row"><span>Readiness</span><b>{payload.readiness?.status || 'Unavailable'}</b></div>
        </section>
        <section>
          <h3>Market feed</h3>
          <div className="la-health-row"><span>Transport</span><b>{feed.status || 'Unavailable'}</b></div>
          <div className="la-health-row"><span>Messages</span><b>{Number(feed.messages || 0).toLocaleString('en-IN')}</b></div>
          <div className="la-health-row"><span>Reconnects</span><b>{feed.reconnects ?? '—'}</b></div>
          <div className="la-health-row"><span>Decode errors</span><b>{feed.decode_errors ?? '—'}</b></div>
          <div className="la-health-row"><span>Last heartbeat</span><b>{feed.last_message_at ? age(feed.last_message_at) : '—'}</b></div>
          <div className="la-health-row"><span>Universe</span><b>{runtime?.universe ? `${runtime.universe.members} / ${runtime.universe.expected_members}` : '—'}</b></div>
        </section>
        <section>
          <h3>Engines</h3>
          {STRATEGIES.map(([engine, label]) => {
            const row = health[engine] || {};
            return (
              <div className="la-health-row" key={engine}>
                <span>{label}</span>
                <b>{row.status || 'never_run'} · {row.stored_signals || 0} stored</b>
              </div>
            );
          })}
        </section>
        <section>
          <h3>Storage & diagnostics</h3>
          <div className="la-health-row"><span>Degraded engines</span><b>{(payload.readiness?.degraded_engines || []).join(', ') || 'None'}</b></div>
          <div className="la-health-row"><span>Last successful run</span><b>{payload.freshness?.latest_successful_at || '—'}</b></div>
          <div className="la-health-row"><span>Last evaluation skip</span><b>{runtime?.last_evaluation?.reason || '—'}</b></div>
          <div className="la-health-row"><span>Baselines</span><b>{runtime?.baseline_bootstrap?.status || '—'}</b></div>
          <div className="la-health-row"><span>Rejected out-of-order</span><b>{Number(feed.snapshot_quality?.rejected_out_of_order || 0).toLocaleString('en-IN')}</b></div>
        </section>
      </aside>
    </div>
  );
}

function ResearchDrawer({ row, onClose }) {
  const direction = plainSignalDirection(row);
  const lead = [...row.active].sort((a, b) => Math.abs(signedSignalScore(b)) - Math.abs(signedSignalScore(a)))[0];
  const factors = lead?.factor_values || {};
  const interpretation = row.interpretation;
  return (
    <div className="la-drawer-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <aside className="la-drawer">
        <header>
          <div>
            <span>{row.sector}</span>
            <h2>{row.symbol}</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </header>

        <section className="la-drawer-score">
          <div><small>Structure</small><strong className={`la-dir ${direction.key}`}>{direction.label}</strong></div>
          <div><small>Strength</small><strong>{Math.abs(row.composite)} / 99</strong></div>
          <div><small>Evidence</small><strong>{evidenceStrengthLabel(row.confidence)}</strong></div>
          <div><small>Age</small><strong>{age(row.newest)}</strong></div>
        </section>

        <section className="la-what">
          <h3>Why AGI flagged it</h3>
          <p>{interpretation.summary} Predictive validity has not yet been established.</p>
        </section>

        <section>
          <h3>Evidence</h3>
          <div className="la-component-table">
            <div><b>Component</b><b>Score</b><b>State</b><b>Role</b></div>
            {STRATEGIES.map(([engine, label]) => {
              const signal = row.strategies[engine];
              const score = signedSignalScore(signal);
              const role = !signal?.direction
                ? row.component_states[engine]
                : interpretation.structure === 'CONFLICTING'
                  ? (signal.direction === 'positive' ? 'Dominant positive' : 'Dominant negative')
                  : signal === interpretation.primary_driver
                    ? 'Primary'
                    : signal.direction === interpretation.primary_driver?.direction
                      ? 'Supporting'
                      : 'Contradicting';
              return (
                <div key={engine}>
                  <span>{label}</span>
                  <span className={score > 0 ? 'up' : score < 0 ? 'down' : ''}>{signal?.direction ? scoreText(score) : '—'}</span>
                  <span>{row.component_states[engine]}</span>
                  <span>{role}</span>
                </div>
              );
            })}
          </div>
        </section>

        <section>
          <h3>What changed</h3>
          <p className="la-muted-copy">Intraday change history is unavailable until Live Alpha exposes prior score snapshots.</p>
        </section>

        <section>
          <h3>Conflicting evidence</h3>
          {interpretation.structure === 'CONFLICTING' ? (
            <ul className="la-caveats">
              {interpretation.contradicting_components.map((signal) => (
                <li key={signal.engine}>{ENGINE_PLAIN[signal.engine]?.label || signal.engine} · {scoreText(signedSignalScore(signal))}</li>
              ))}
            </ul>
          ) : (
            <p className="la-muted-copy">No material conflicting engine currently detected.</p>
          )}
        </section>

        <section>
          <h3>What could weaken this signal?</h3>
          <ul className="la-caveats">
            {interpretation.weakening_conditions.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>

        <section>
          <h3>Data quality</h3>
          <div className="la-evidence">
            <div><span>Liquidity checks</span><b>{row.active.every((s) => s.liquidity_ok) ? 'Passed' : 'Review required'}</b></div>
            <div><span>Freshness</span><b>{age(row.newest)}</b></div>
            <div><span>Comparable obs.</span><b>{row.samples || 0}</b></div>
            <div><span>15m residual</span><b>{formatFactor(factors.residual_15m ?? lead?.residual_15m, '%')}</b></div>
            <div><span>Volume vs expected</span><b>{Number(lead?.volume_ratio || factors.volume_surprise || 0) ? `${Number(lead?.volume_ratio || factors.volume_surprise).toFixed(2)}×` : '—'}</b></div>
            <div><span>OI change</span><b>{formatFactor(factors.oi_change_15m ?? lead?.oi_change, '%')}</b></div>
          </div>
        </section>

        <details className="la-lineage">
          <summary>Model lineage</summary>
          <p>Market feed → Instrument mapping → Normalization → Timestamp validation → Liquidity checks → Strategy input → Component score → Composite score → Signal interpretation → Confidence → Immutable research snapshot.</p>
          <dl>
            <dt>Data cutoff</dt><dd>{row.data_cutoff}</dd>
            <dt>Strategy version</dt><dd>{row.strategy_version}</dd>
            <dt>Model version</dt><dd>{row.model_version}</dd>
            <dt>Lead signal id</dt><dd>{lead?.id || 'Unavailable'}</dd>
            <dt>Input fingerprint</dt><dd>{row.data_fingerprint || 'Unavailable'}</dd>
            <dt>Agreement</dt><dd>{row.agreement}</dd>
          </dl>
        </details>

        <section>
          <h3>Research caveats</h3>
          <ul className="la-caveats">
            {interpretation.caveats.map((item) => <li key={item}>{item}</li>)}
            <li>This is a research signal, not an investment recommendation.</li>
          </ul>
        </section>
      </aside>
    </div>
  );
}

function ConvictionPanel({ payload, error, filter, onFilter }) {
  const rows = filterConvictionRows(payload?.rows || [], filter);
  const counts = payload?.run?.counts || {};
  const generated = payload?.run?.generated_at
    ? new Date(payload.run.generated_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
    : 'Awaiting first run';
  return (
    <section className="la-conviction-view">
      <header className="la-conviction-hero">
        <div>
          <span className="la-kicker">Evidence-confirmed decision layer</span>
          <h2>Conviction Ranking</h2>
          <p>Separate from Live Alpha composite. Combines leadership, live confirmation and research evidence without inventing theses from incomplete signals.</p>
        </div>
        <div className="la-conviction-meta">
          <strong>{payload?.run?.universe_size || 0}</strong>
          <span>ranked names<br />Updated {generated}</span>
        </div>
      </header>
      <div className="la-conviction-summary">
        <div><small>High conviction</small><strong>{counts.HIGH_CONVICTION || 0}</strong></div>
        <div><small>Confirmed</small><strong>{counts.CONFIRMED || 0}</strong></div>
        <div><small>Watch</small><strong>{counts.WATCH || 0}</strong></div>
        <div><small>Needs evidence</small><strong>{counts.INCOMPLETE || 0}</strong></div>
      </div>
      <div className="la-conviction-toolbar">
        <div>{CONVICTION_FILTERS.map(([key, label]) => (
          <button key={key} type="button" className={filter === key ? 'active' : ''} onClick={() => onFilter(key)}>{label}</button>
        ))}</div>
        <span>Showing {rows.length} names</span>
      </div>
      {error ? <div className="la-notice error"><AlertCircle size={16} /><div><strong>Conviction ranking unavailable</strong><p>{error}</p></div></div> : null}
      {!error && !payload?.run ? (
        <div className="la-empty"><ShieldCheck size={24} /><h3>Awaiting the first conviction cycle</h3><p>The ranking appears after AGI combines stored market and research evidence.</p></div>
      ) : null}
      {rows.length ? (
        <div className="la-conviction-list">
          {rows.slice(0, filter === 'shortlist' ? 10 : 200).map((row) => (
            <details key={row.symbol} className="la-conviction-card">
              <summary>
                <span className="la-conviction-rank">#{row.rank}</span>
                <div className="la-conviction-name"><strong>{row.symbol}</strong><span>{row.sector || 'Sector unavailable'}</span></div>
                <div className="la-conviction-score"><strong>{Number(row.conviction_score).toFixed(1)}</strong><span>conviction</span></div>
                <span className={`la-conviction-label ${convictionTone(row.conviction_label)}`}>{readableConvictionLabel(row.conviction_label)}</span>
                <div className="la-evidence-meter"><i style={{ width: `${Math.round(Number(row.evidence_coverage || 0) * 100)}%` }} /><span>{Math.round(Number(row.evidence_coverage || 0) * 100)}% evidence</span></div>
                <ChevronRight className="la-conviction-chevron" size={16} />
              </summary>
              <div className="la-conviction-detail">
                <article><small>AGI thesis</small><p>{row.thesis}</p></article>
                <article><small>Risk and contradiction check</small><p>{row.risk_note}</p></article>
                <div className="la-component-grid">
                  {Object.entries(row.component_scores || {}).map(([key, value]) => (
                    <div key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{value == null ? '—' : Number(value).toFixed(0)}</strong></div>
                  ))}
                </div>
              </div>
            </details>
          ))}
        </div>
      ) : null}
    </section>
  );
}
