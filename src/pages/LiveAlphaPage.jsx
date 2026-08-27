import { useEffect, useMemo, useState } from 'react';
import API_ORIGIN from '@/config';
import {
  buildCanonicalSignals,
  interpretCanonicalSignal,
  LIVE_ALPHA_STRATEGIES,
} from '@/lib/liveAlphaSignalModel';
import {
  ENGINE_PLAIN,
  filterRadarRows,
  plainSignalDirection,
} from '@/lib/liveAlphaDashboardModel';
import './liveAlphaPage.css';

/**
 * Live Alpha — seven research strategies over the Nifty 500.
 *
 * Five intraday engines drive the composite; two scheduled end-of-day models
 * (sector rotation, equity opportunities) run beside it on the Groww feed and
 * are reported separately rather than blended in.
 *
 * Ordered so the least experienced reader reaches the right conclusion first.
 * The page opens with the state of the data, because a board computed nine
 * hours ago is a different product from a live one, and the previous layout
 * led with signals while freshness sat far below the fold.
 *
 * Three rules this page keeps:
 *   - Nothing appears as a recommendation. These are research observations.
 *   - Every strength claim carries its evidence, or states there is none.
 *     Model state and empirical validation are never conflated.
 *   - A measurement that was not taken reads as unknown, never as zero.
 */

const REFRESH_MS = 60_000;

async function readJson(response, label) {
  if (!response.ok) throw new Error(`${label} unavailable (${response.status})`);
  return response.json();
}

function ageLabel(seconds) {
  if (seconds === null || seconds === undefined) return 'never';
  if (seconds < 90) return `${Math.round(seconds)}s ago`;
  if (seconds < 5400) return `${Math.round(seconds / 60)} min ago`;
  return `${(seconds / 3600).toFixed(1)} hours ago`;
}

/** The single most important thing on the page. */
function StateBanner({ readiness, freshness, runtime }) {
  const stale = freshness?.stale !== false;
  const status = readiness?.status;
  const evaluation = runtime?.evaluation_status;
  const neverRan = runtime ? !runtime.last_successful_evaluation : false;

  let state;
  if (status === 'persistence_degraded') {
    state = {
      tone: 'bad',
      title: 'Storage degraded',
      detail: `Engines affected: ${(readiness?.degraded_engines || []).join(', ') || 'unknown'}.`,
    };
  } else if (neverRan && evaluation === 'warming_up') {
    state = {
      tone: 'warn',
      title: 'Warming up — no live evaluation yet',
      detail: runtime?.last_evaluation?.reason
        ? `Last attempt skipped: ${String(runtime.last_evaluation.reason).replace(/_/g, ' ')}. Signals below are from the last completed session.`
        : 'The evaluator has not completed a successful pass since starting.',
    };
  } else if (stale) {
    state = {
      tone: 'warn',
      title: 'Historical view — not live',
      detail: `Newest evaluation ${ageLabel(freshness?.age_seconds)}, against a ${Math.round((freshness?.stale_after_seconds || 900) / 60)} minute freshness limit. Signals below describe the last completed session.`,
    };
  } else {
    state = { tone: 'good', title: 'Live', detail: `Updated ${ageLabel(freshness?.age_seconds)}.` };
  }

  return (
    <div className={`la-banner la-banner--${state.tone}`}>
      <div className="la-banner__title">{state.title}</div>
      <p className="la-banner__detail">{state.detail}</p>
    </div>
  );
}

function Metric({ label, value, sub }) {
  return (
    <div className="la-metric">
      <div className="la-metric__label">{label}</div>
      <div className="la-metric__value">{value}</div>
      {sub ? <div className="la-metric__sub">{sub}</div> : null}
    </div>
  );
}

function ConfidenceBadge({ confidence, basis }) {
  const tone = confidence === 'SAMPLE-RICH' || confidence === 'HIGH' ? 'good'
    : confidence === 'MEDIUM' ? 'mid'
      : confidence === 'MODEL-ONLY' ? 'warn' : 'low';
  return (
    <span className={`la-badge la-badge--${tone}`} title={basis || ''}>
      {confidence === 'MODEL-ONLY' ? 'Model only' : confidence}
    </span>
  );
}

function runAge(run) {
  if (!run?.as_of) return 'never run';
  const seconds = (Date.now() - Date.parse(run.as_of)) / 1000;
  return Number.isFinite(seconds) ? ageLabel(seconds) : 'unknown';
}

/**
 * Strategy 6 — Sector Rotation. Placed high on the page on purpose.
 *
 * Eleven rows that say where money is moving, against 500-row cross-sections
 * everywhere else. It is the densest information here and it frames how every
 * name below should be read, so it runs before the signal board rather than
 * after it.
 *
 * Note it is NOT joined to the signal rows. The two use different taxonomies -
 * signals carry NSE broad sectors (FINANCIAL_SERVICES, INFORMATION_TECHNOLOGY,
 * twenty of them) while this carries index names (NIFTYBANK, NIFTYIT, eleven).
 * They share no exact values, and the mapping is genuinely ambiguous: three
 * bank indices collapse onto one FINANCIAL_SERVICES, and NIFTYPHARMA is not
 * HEALTHCARE. A wrong sector label on a signal row would be worse than none.
 */
export function SectorRotation({ groww }) {
  const sectors = groww?.sectors || [];
  const run = (groww?.runs || []).find((item) => item.strategy === 'agi_sector_rotation_v1');
  const leading = sectors.filter((row) => row.rotation === 'leading').length;
  const lagging = sectors.filter((row) => row.rotation === 'lagging').length;

  return (
    <section className="la-section">
      <div className="la-section__head">
        <h2>Where the market is moving</h2>
        <p className="la-section__note">
          Strategy 6 · scheduled sector rotation over the Groww feed, {runAge(run)}.
          {sectors.length ? ` ${leading} leading, ${lagging} lagging.` : ''} Not joined to the
          signals below — the two use different sector taxonomies, so treat this as
          separate context rather than a label for individual names.
        </p>
      </div>
      {sectors.length ? (
        <div className="la-rot">
          {sectors.map((row) => (
            <div key={row.sector} className={`la-rot__card la-rot__card--${row.rotation}`}>
              <div className="la-rot__top">
                <span className="la-rot__name">{String(row.sector).replace(/^NIFTY/, '')}</span>
                <span className="la-rot__rank">#{row.rank}</span>
              </div>
              <div className={`la-rot__rel ${Number(row.relative_20d) >= 0 ? 'la-pos' : 'la-neg'}`}>
                {Number(row.relative_20d) >= 0 ? '+' : ''}{Number(row.relative_20d).toFixed(1)}%
              </div>
              <div className="la-rot__meta">
                <span className={`la-tag la-tag--${row.rotation}`}>{row.rotation}</span>
                <span className="la-muted">20d rel.</span>
              </div>
            </div>
          ))}
        </div>
      ) : <p className="la-muted">No sector rotation run received yet.</p>}
    </section>
  );
}

/**
 * The shortlist: names more than one engine agrees on.
 *
 * A client does not want 194 rows, and multi-engine agreement is the only
 * corroboration this system currently has - empirical validation needs 100
 * comparables and every signal has zero. So agreement across independent
 * engines is the strongest claim available, and it is stated as exactly that.
 */
export function Shortlist({ rows, onSelect }) {
  const top = rows
    .filter((row) => row.active.length >= 2)
    .slice()
    .sort((a, b) => (b.active.length - a.active.length) || (Math.abs(b.composite) - Math.abs(a.composite)))
    .slice(0, 12);

  if (!top.length) {
    return (
      <section className="la-section">
        <div className="la-section__head">
          <h2>Shortlist</h2>
          <p className="la-section__note">
            No name currently has two or more engines pointing the same way. That is a
            quiet market reading, not a failure — the full board below still has signals.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="la-section">
      <div className="la-section__head">
        <h2>Shortlist — where engines agree</h2>
        <p className="la-section__note">
          Names flagged by two or more independent engines, strongest agreement first.
          Agreement is corroboration between models, not evidence of future return.
        </p>
      </div>
      <div className="la-short">
        {top.map((row) => (
          <button key={row.symbol} type="button" className="la-short__card" onClick={() => onSelect?.(row.symbol)}>
            <div className="la-short__top">
              <span className="la-short__sym">{row.symbol}</span>
              <span className={`la-short__score ${row.composite > 0 ? 'la-pos' : 'la-neg'}`}>
                {row.composite > 0 ? '+' : ''}{row.composite}
              </span>
            </div>
            <div className="la-short__engines">
              {row.active.map((signal) => (
                <span key={signal.engine} className="la-pill">
                  {ENGINE_PLAIN[signal.engine]?.label || signal.engine}
                </span>
              ))}
            </div>
            <div className="la-short__foot">
              <span className="la-muted">{row.sector}</span>
              <ConfidenceBadge confidence={row.confidence} basis={row.confidence_basis} />
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

/** Strategy 7 — scheduled end-of-day equity screen. */
export function EquityOpportunities({ groww }) {
  const equities = groww?.equities || [];
  const run = (groww?.runs || []).find((item) => item.strategy === 'agi_equity_opportunity_v1');
  const top = equities.slice(0, 15);

  return (
    <section className="la-section">
      <div className="la-section__head">
        <h2>End-of-day equity screen</h2>
        <p className="la-section__note">
          Strategy 7 · scheduled over the Groww feed, {runAge(run)}. Ranked by score across
          {' '}{equities.length} names. Every name carries the same
          {' '}<code>research_candidate</code> label, so the ranking is the information here
          and the label is not — it does not separate one name from another.
        </p>
      </div>
      {top.length ? (
        <div className="la-tablewrap">
          <table className="la-table la-table--compact">
            <thead>
              <tr>
                <th>#</th><th>Stock</th><th className="la-num">Last price</th><th className="la-num">Score</th>
                <th className="la-num">20d rel.</th><th className="la-num">60d rel.</th><th>Volume</th>
              </tr>
            </thead>
            <tbody>
              {top.map((row) => (
                <tr key={row.symbol}>
                  <td className="la-muted">{row.rank}</td>
                  <td><strong>{row.symbol}</strong></td>
                  <td className="la-num">
                    {row.price
                      ? Number(row.price).toLocaleString('en-IN', { maximumFractionDigits: 2 })
                      : '—'}
                  </td>
                  <td className="la-num">{Number(row.score).toFixed(0)}</td>
                  <td className={`la-num ${Number(row.relative_20d) >= 0 ? 'la-pos' : 'la-neg'}`}>
                    {Number(row.relative_20d) >= 0 ? '+' : ''}{Number(row.relative_20d).toFixed(1)}%
                  </td>
                  <td className={`la-num ${Number(row.relative_60d) >= 0 ? 'la-pos' : 'la-neg'}`}>
                    {Number(row.relative_60d) >= 0 ? '+' : ''}{Number(row.relative_60d).toFixed(1)}%
                  </td>
                  <td className={row.volume_confirmation ? '' : 'la-muted'}>
                    {Number(row.volume_ratio).toFixed(2)}×{row.volume_confirmation ? '' : ' unconfirmed'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="la-muted">No equity screen run received yet.</p>}
    </section>
  );
}


// Exported so a smoke test can render real production signals through it.
export function SignalRow({ row, expanded, onToggle }) {
  const view = useMemo(() => interpretCanonicalSignal(row), [row]);
  // plainSignalDirection returns { key, label }; rendering the object itself
  // throws "Objects are not valid as a React child" and blanks the page.
  const direction = plainSignalDirection(row)?.label ?? '—';
  // Signals stored before liquidity_verified existed have no such field, which
  // is unknown rather than fine — only an explicit false is a measured miss.
  const unverified = row.active.filter((signal) => signal.liquidity_verified === false).length;
  const unknownLiquidity = row.active.filter((signal) => signal.liquidity_verified === undefined).length;

  return (
    <>
      <tr className={`la-row ${expanded ? 'la-row--open' : ''}`} onClick={onToggle}>
        <td className="la-cell-sym">
          <span className="la-sym">{row.symbol}</span>
          <span className="la-sector">{row.sector}</span>
        </td>
        <td>
          <span className={`la-dir la-dir--${row.composite > 0 ? 'pos' : row.composite < 0 ? 'neg' : 'flat'}`}>
            {direction}
          </span>
        </td>
        <td className="la-num">
          {row.live_price
            ? Number(row.live_price).toLocaleString('en-IN', { maximumFractionDigits: 2 })
            : '—'}
        </td>
        <td className="la-num">{row.composite > 0 ? '+' : ''}{row.composite}</td>
        <td><ConfidenceBadge confidence={row.confidence} basis={row.confidence_basis} /></td>
        <td className="la-cell-drivers">
          {row.active.length
            ? row.active.map((signal) => ENGINE_PLAIN[signal.engine]?.label || signal.engine).join(' · ')
            : <span className="la-muted">none active</span>}
        </td>
        <td className="la-num">
          {unverified > 0
            ? <span className="la-warn-inline" title="Bid-ask spread could not be measured for these components">{unverified} unverified</span>
            : unknownLiquidity > 0
              ? <span className="la-muted" title="Recorded before liquidity verification existed">not recorded</span>
              : <span className="la-muted">ok</span>}
        </td>
      </tr>
      {expanded ? (
        <tr className="la-detail">
          <td colSpan={7}>
            <div className="la-detail__grid">
              <div>
                <h4>What the model sees</h4>
                <p>{view.summary}</p>
                <ul className="la-list">
                  {view.why_flagged.map((line) => <li key={line}>{line}</li>)}
                </ul>
              </div>
              <div>
                <h4>Evidence</h4>
                <p className="la-basis">{row.confidence_basis}</p>
                <h4>Read this carefully</h4>
                <ul className="la-list la-list--caveat">
                  {view.caveats.map((line) => <li key={line}>{line}</li>)}
                </ul>
              </div>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}

export default function LiveAlphaPage() {
  const [payload, setPayload] = useState({});
  const [runtime, setRuntime] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(null);

  const load = async () => {
    setError('');
    try {
      if (!API_ORIGIN) throw new Error('AGI backend origin is not configured.');
      const [workspace, status] = await Promise.all([
        fetch(`${API_ORIGIN}/api/market/live-alpha/workspace`, { headers: { Accept: 'application/json' } }),
        fetch(`${API_ORIGIN}/api/market/live-alpha/status`, { headers: { Accept: 'application/json' } }),
      ]);
      setPayload(await readJson(workspace, 'Live Alpha research store'));
      setRuntime(await readJson(status, 'Live Alpha runtime'));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    document.title = 'Live Alpha | Agarwal Global Investments';
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, []);

  const allRows = useMemo(
    () => buildCanonicalSignals(payload.signals || [], payload.strategy_health || {}),
    [payload.signals, payload.strategy_health],
  );
  const isFresh = payload.freshness?.stale === false;
  const directional = useMemo(() => allRows.filter((row) => row.active?.length), [allRows]);
  const shown = useMemo(
    () => filterRadarRows(directional, filter, { search })
      .slice()
      .sort((a, b) => Math.abs(b.composite) - Math.abs(a.composite)),
    [directional, filter, search],
  );

  const engineCounts = useMemo(() => {
    const counts = {};
    for (const [key] of LIVE_ALPHA_STRATEGIES) {
      counts[key] = directional.filter((row) => row.strategies[key]?.direction).length;
    }
    return counts;
  }, [directional]);

  if (loading) return <div className="la-page la-page--center">Loading Live Alpha…</div>;

  return (
    <div className="la-page">
      <header className="la-head">
        <h1>Live Alpha</h1>
        <p className="la-sub">
          Seven research strategies across the Nifty 500 — five intraday engines,
          plus scheduled sector and equity models. These are research observations
          for analyst review, not recommendations, price targets, or orders.
        </p>
      </header>

      {error ? (
        <div className="la-banner la-banner--bad">
          <div className="la-banner__title">Data unavailable</div>
          <p className="la-banner__detail">{error}</p>
        </div>
      ) : null}

      <StateBanner readiness={payload.readiness} freshness={payload.freshness} runtime={runtime} />

      <section className="la-metrics">
        <Metric label="Names with an active signal" value={directional.length} sub={`of ${allRows.length} evaluated`} />
        <Metric label="Positive" value={directional.filter((row) => row.composite > 0).length} />
        <Metric label="Negative" value={directional.filter((row) => row.composite < 0).length} />
        <Metric
          label="Multi-engine agreement"
          value={directional.filter((row) => row.active.length >= 2).length}
          sub="two or more engines aligned"
        />
        <Metric
          label="Sample threshold met"
          value={directional.filter((row) => row.confidence === 'SAMPLE-RICH').length}
          sub="100+ comparables; not a validation gate"
        />
      </section>

      <SectorRotation groww={payload.groww} />

      <Shortlist rows={directional} onSelect={setSearch} />

      <section className="la-board">
        <div className="la-board__bar">
          <div className="la-filters">
            {['all', 'positive', 'negative'].map((option) => (
              <button
                key={option}
                type="button"
                className={filter === option ? 'is-active' : ''}
                onClick={() => setFilter(option)}
              >
                {option[0].toUpperCase() + option.slice(1)}
              </button>
            ))}
          </div>
          <input
            className="la-search"
            placeholder="Search symbol or sector"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        {shown.length === 0 ? (
          <div className="la-empty">
            No names currently carry an active directional signal.
            {isFresh ? '' : ' The last evaluation is stale, so this reflects the previous session.'}
          </div>
        ) : (
          <div className="la-tablewrap">
            <table className="la-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Direction</th>
                  <th className="la-num">Last price</th>
                  <th className="la-num">Score</th>
                  <th>Confidence</th>
                  <th>Driven by</th>
                  <th className="la-num">Liquidity</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((row) => (
                  <SignalRow
                    key={row.symbol}
                    row={row}
                    expanded={open === row.symbol}
                    onToggle={() => setOpen(open === row.symbol ? null : row.symbol)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <EquityOpportunities groww={payload.groww} />

      <section className="la-section">
        <div className="la-section__head">
          <h2>Engine health</h2>
          <p className="la-section__note">
            The five intraday engines and what each is currently contributing. An engine
            reporting zero active names is not necessarily broken — it may simply have
            nothing to say — but Positioning is coverage-limited: only 208 of 500
            derivative instruments resolve, so its silence is partly structural.
          </p>
        </div>
      <section className="la-engines">
        {LIVE_ALPHA_STRATEGIES.map(([key]) => {
          const meta = ENGINE_PLAIN[key] || {};
          const health = payload.strategy_health?.[key]?.status;
          return (
            <div key={key} className="la-engine">
              <div className="la-engine__top">
                <span className="la-engine__label">{meta.label || key}</span>
                <span className={`la-chip la-chip--${health === 'ready' ? 'good' : health === 'stale' ? 'warn' : 'bad'}`}>
                  {health || 'unknown'}
                </span>
              </div>
              <p className="la-engine__plain">{meta.plain}</p>
              <div className="la-engine__count">{engineCounts[key] ?? 0} active</div>
            </div>
          );
        })}
      </section>
      </section>


      <footer className="la-foot">
        <p>
          <strong>Score</strong> is a composite of the active engines, from −99 to +99. It
          measures how strongly the model currently reads a name, not expected return.
        </p>
        <p>
          <strong>Confidence</strong> separates model state from evidence. “Model only” means
          no historical comparables exist behind the signal yet — the empirical validation
          layer is still collecting. Reaching 100 observations is only a sample-size
          threshold; research validation also requires point-in-time, costed,
          out-of-sample evidence and does not follow from count alone.
        </p>
        <p>
          <strong>Liquidity</strong> flags components whose bid-ask spread could not be measured
          at evaluation time. Unmeasured is not the same as tight.
        </p>
        <p className="la-foot__legal">
          Research output only. No execution is enabled from this page. Nothing here is
          investment advice or a solicitation to trade.
        </p>
      </footer>
    </div>
  );
}
