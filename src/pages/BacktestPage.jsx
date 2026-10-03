import React from 'react';
import { getInstitutionalOverview, getInstitutionalBacktest } from '@/lib/institutionalHoldingsApi';
import './backtestTheme.css';

/**
 * What a manager's disclosed book would have returned.
 *
 * The page exists to be doubted, so it shows what a reader needs in order to
 * doubt it: how many periods were evaluated, how many were refused and why,
 * what fraction of each book could be priced, and the rule that decides when a
 * position is bought. A single number with none of that is a claim rather than
 * a result.
 *
 * Entry is the first session strictly after the SEC accepted the filing. That
 * is the whole difference between a backtest and a fantasy - a 13F is public
 * forty-five days after the quarter it describes, and anything that enters
 * earlier is reading the future.
 */

const pct = (value, digits = 1) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return `${number >= 0 ? '+' : ''}${(number * 100).toFixed(digits)}%`;
};

/** Compound a per-period return series into a cumulative curve. */
function curve(periods, key) {
  let value = 1;
  return (periods || []).map((row) => {
    const step = Number(row?.[key]);
    if (Number.isFinite(step)) value *= (1 + step);
    return { date: row.exit_date || row.entry_date, value: value - 1 };
  });
}

/**
 * Three cumulative series on one scale.
 *
 * One scale for all three, because the point of the chart is the gap between
 * them. Drawn as an SVG rather than with a charting library: three polylines
 * and an axis do not justify a dependency, and every label here names a value
 * the data actually reaches.
 */
function Curve({ periods }) {
  const series = [
    { key: 'net_return', label: 'Strategy', className: 'is-strategy' },
    { key: 'spy_return', label: 'SPY', className: 'is-spy' },
    { key: 'qqq_return', label: 'QQQ', className: 'is-qqq' },
  ].map((row) => ({ ...row, points: curve(periods, row.key) }));

  const all = series.flatMap((row) => row.points.map((point) => point.value));
  if (all.length < 2) return null;

  const min = Math.min(0, ...all);
  const max = Math.max(...all);
  const span = (max - min) || 1;
  const width = 720;
  const height = 260;
  const padX = 52;
  const padY = 18;

  const x = (index, length) => padX + (index / Math.max(1, length - 1)) * (width - padX - 12);
  const y = (value) => padY + (1 - (value - min) / span) * (height - padY * 2);

  // Ticks at values the data reaches, not at round numbers outside it.
  const ticks = [min, min + span / 2, max];

  return (
    <figure className="bt-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img"
        aria-label={`Cumulative return by period: ${series.map((s) => `${s.label} ${pct(s.points[s.points.length - 1]?.value)}`).join(', ')}`}>
        {ticks.map((tick) => (
          <g key={tick}>
            <line className="bt-grid" x1={padX} x2={width - 12} y1={y(tick)} y2={y(tick)} />
            <text className="bt-axis" x={padX - 8} y={y(tick) + 4} textAnchor="end">{pct(tick, 0)}</text>
          </g>
        ))}
        {series.map((row) => (
          <polyline
            key={row.key}
            className={`bt-line ${row.className}`}
            fill="none"
            points={row.points.map((point, index) => `${x(index, row.points.length)},${y(point.value)}`).join(' ')}
          />
        ))}
      </svg>
      <figcaption className="bt-legend">
        {series.map((row) => (
          <span key={row.key} className={row.className}>
            <i aria-hidden="true" /> {row.label} {pct(row.points[row.points.length - 1]?.value)}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

export default function BacktestPage() {
  const [managers, setManagers] = React.useState([]);
  const [slug, setSlug] = React.useState('');
  const [quarters, setQuarters] = React.useState(40);
  const [topN, setTopN] = React.useState(10);
  const [run, setRun] = React.useState(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    let live = true;
    getInstitutionalOverview()
      .then((data) => {
        if (!live) return;
        const rows = (data?.managers || []).filter((row) => row?.slug);
        setManagers(rows);
        setSlug((current) => current || rows[0]?.slug || '');
      })
      .catch((err) => live && setError(err.message));
    return () => { live = false; };
  }, []);

  const load = async () => {
    setBusy(true); setError(null); setRun(null);
    try {
      setRun(await getInstitutionalBacktest(slug, { quarters, topN }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const metrics = run?.metrics || {};
  const calculated = run?.status === 'calculated';

  return (
    <main className="bt-page">
      <header className="bt-header">
        <h1>Manager backtest</h1>
        <p className="bt-rule">
          Each quarter&rsquo;s disclosed top holdings, bought at the first session
          <strong> strictly after the SEC accepted the filing</strong> and held until the next one.
          A 13F is public forty-five days after the quarter it describes; anything entering sooner is reading the future.
        </p>
      </header>

      <section className="bt-controls">
        <label>Manager
          <select value={slug} onChange={(e) => setSlug(e.target.value)}>
            {managers.map((row) => <option key={row.slug} value={row.slug}>{row.display_name || row.slug}</option>)}
          </select>
        </label>
        <label>Quarters
          <input type="number" min="2" max="48" value={quarters}
            onChange={(e) => setQuarters(Number(e.target.value))} />
        </label>
        <label>Top holdings
          <input type="number" min="1" max="50" value={topN}
            onChange={(e) => setTopN(Number(e.target.value))} />
        </label>
        <button type="button" onClick={load} disabled={busy || !slug}>
          {busy ? 'Running…' : 'Run'}
        </button>
      </section>

      {error && <p className="bt-error">{error}</p>}

      {run && !calculated && (
        <section className="bt-blocked">
          <h2>Not calculable</h2>
          <p>{metrics.reason}</p>
          {metrics.skipped?.length > 0 && (
            <ul>
              {metrics.skipped.slice(0, 12).map((row, i) => (
                <li key={i}><strong>{row.report_date}</strong> — {row.reason}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {run && calculated && (
        <>
          <section className="bt-metrics">
            <div className="bt-tile">
              <span>Strategy</span>
              <strong className={metrics.total_return >= 0 ? 'is-up' : 'is-down'}>{pct(metrics.total_return)}</strong>
            </div>
            <div className="bt-tile">
              <span>SPY</span><strong>{pct(metrics.spy_return)}</strong>
            </div>
            <div className="bt-tile">
              <span>QQQ</span><strong>{pct(metrics.qqq_return)}</strong>
            </div>
            <div className="bt-tile">
              <span>vs SPY</span>
              <strong className={metrics.excess_vs_spy >= 0 ? 'is-up' : 'is-down'}>{pct(metrics.excess_vs_spy)}</strong>
            </div>
            <div className="bt-tile">
              <span>Periods</span><strong>{metrics.periods}</strong>
            </div>
            <div className="bt-tile">
              <span>Worst coverage</span>
              <strong>{pct(metrics.worst_period_coverage, 1)}</strong>
              <em>{metrics.worst_coverage_period}</em>
            </div>
          </section>

          <Curve periods={run.periods} />

          {/* Stated rather than left to interpretation: it is a difference of
              compounded returns, which is directionally right and is not a
              risk-adjusted attribution. */}
          <p className="bt-note">
            &ldquo;vs SPY&rdquo; is the difference between the two compounded returns, not a
            risk-adjusted attribution. Positions without an adjusted close at both ends of a period
            are excluded and counted in coverage, never re-weighted onto the rest.
            {run.from_cache ? ' Served from today’s stored run.' : ' Computed just now.'}
          </p>

          <section className="bt-block">
            <h2>By period</h2>
            <div className="bt-scroll">
              <table className="bt-table">
                <thead>
                  <tr>
                    <th scope="col">Quarter</th>
                    <th scope="col">Known at</th>
                    <th scope="col">Entry</th>
                    <th scope="col">Exit</th>
                    <th scope="col" className="num">Strategy</th>
                    <th scope="col" className="num">SPY</th>
                    <th scope="col" className="num">Coverage</th>
                    <th scope="col" className="num">Priced</th>
                  </tr>
                </thead>
                <tbody>
                  {(run.periods || []).map((row) => (
                    <tr key={`${row.report_date}-${row.entry_date}`}>
                      <th scope="row">{row.report_date}</th>
                      <td>{String(row.known_at || '').slice(0, 10)}</td>
                      <td>{row.entry_date}</td>
                      <td>{row.exit_date}</td>
                      <td className={`num ${row.net_return >= 0 ? 'is-up' : 'is-down'}`}>{pct(row.net_return)}</td>
                      <td className="num">{pct(row.spy_return)}</td>
                      <td className="num">{pct(row.price_coverage)}</td>
                      <td className="num">
                        {row.positions_priced}
                        {row.positions_excluded > 0 && <em> (−{row.positions_excluded})</em>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
