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
 * Live Alpha — five intraday research engines over the Nifty 500.
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
  const tone = confidence === 'VALIDATED' || confidence === 'HIGH' ? 'good'
    : confidence === 'MEDIUM' ? 'mid'
      : confidence === 'MODEL-ONLY' ? 'warn' : 'low';
  return (
    <span className={`la-badge la-badge--${tone}`} title={basis || ''}>
      {confidence === 'MODEL-ONLY' ? 'Model only' : confidence}
    </span>
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
          <td colSpan={6}>
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
          Five intraday research engines across the Nifty 500. These are research
          observations for analyst review — not recommendations, price targets, or orders.
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
          label="Empirically validated"
          value={directional.filter((row) => row.confidence === 'VALIDATED').length}
          sub="requires 100+ comparables"
        />
      </section>

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

      <footer className="la-foot">
        <p>
          <strong>Score</strong> is a composite of the active engines, from −99 to +99. It
          measures how strongly the model currently reads a name, not expected return.
        </p>
        <p>
          <strong>Confidence</strong> separates model state from evidence. “Model only” means
          no historical comparables exist behind the signal yet — the empirical validation
          layer is still collecting, and no signal on this page has reached the 100
          observations required to read as validated.
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
