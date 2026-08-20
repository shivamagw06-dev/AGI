import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import {
  AlertTriangle, ArrowDownRight, ArrowUpRight, CalendarDays, Search, ShieldCheck, Users,
} from 'lucide-react';

import { insiderActivity } from '@/lib/insiderTradingApi';
import { flowChart, shareBars } from '@/lib/insiderCharts';
import './insiderActivity.css';

/**
 * India Insider Activity.
 *
 * Built around one distinction the previous version did not draw: whether
 * anyone actually paid a market price. A promoter buying on the open market and
 * a director receiving an ESOP allotment are both "acquisitions", and a page
 * that adds them together turns a signal into noise. Only open-market filings
 * reach the flow chart and the clusters; everything else is shown, labelled, and
 * kept out of the totals.
 *
 * Two disclosure regimes arrive in the same feed. An insider filing is a
 * director or promoter trading their own company. A SAST filing is an acquirer
 * crossing a shareholding threshold under the takeover code - a real market
 * trade, but not an insider one, and never reported with a price. They are
 * counted apart, which is also why value coverage is quoted against insider
 * filings alone rather than reading as a third of the data being missing.
 *
 * Ordered so the strongest evidence is reachable first: clusters of independent
 * buyers, then the direction of flow, then the pledge risk, then the raw tape.
 */

const RANGES = [['30', '30D'], ['60', '60D'], ['90', '90D'], ['all', 'ALL']];

const money = (value) => {
  const amount = Number(value) || 0;
  if (amount >= 1e7) return `₹${(amount / 1e7).toFixed(1)} Cr`;
  if (amount >= 1e5) return `₹${(amount / 1e5).toFixed(1)} L`;
  return `₹${Math.round(amount).toLocaleString('en-IN')}`;
};

const count = (value) => Number(value || 0).toLocaleString('en-IN');

const pretty = (value) => (value
  ? new Date(`${value}T00:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
  : '—');

const shortDate = (value) => (value
  ? new Date(`${value}T00:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
  : '');

const isBuy = (row) => /acquisition|purchase|buy/i.test(String(row?.action || ''));
const openMarket = (row) => String(row?.is_open_market) === 'true';

/**
 * Buys above the line, sells below, running total across.
 *
 * The running total is the point of the chart. A single heavy day of selling
 * says little; a fortnight where sellers outnumber buyers every day is the
 * thing worth seeing, and only a cumulative line shows it.
 */
export function FlowChart({ days }) {
  const chart = useMemo(() => flowChart(days, { width: 960, height: 250 }), [days]);
  if (chart.empty) {
    return <p className="ia-empty">No open-market filings in this window.</p>;
  }
  const { width, height, zeroY, bars, line, marks, barBound, netBound } = chart;
  const labelEvery = Math.ceil(marks.length / 8);

  return (
    <figure className="ia-flow">
      <svg viewBox={`0 0 ${width} ${height + 26}`} role="img" preserveAspectRatio="none"
           aria-label={`Daily open-market insider filings. Running net stands at ${marks.at(-1)?.cumulativeNet}.`}>
        <line className="ia-axis" x1="0" y1={zeroY} x2={width} y2={zeroY} />
        {bars.map((bar) => (
          <rect key={`${bar.date}-${bar.kind}`} className={`ia-bar ia-bar-${bar.kind}`}
                x={bar.x} y={bar.y} width={bar.width} height={bar.height} rx="1">
            <title>{`${shortDate(bar.date)} · ${bar.count} ${bar.kind === 'buy' ? 'buys' : 'sells'}`}</title>
          </rect>
        ))}
        <path className="ia-net-line" d={line} fill="none" />
        {marks.map((mark, index) => (index % labelEvery === 0 ? (
          <text key={mark.date} className="ia-tick" x={mark.x} y={height + 18} textAnchor="middle">
            {shortDate(mark.date)}
          </text>
        ) : null))}
      </svg>
      <figcaption>
        <span><i className="ia-key ia-key-buy" /> Buys</span>
        <span><i className="ia-key ia-key-sell" /> Sells</span>
        <span><i className="ia-key ia-key-net" /> Running net</span>
        <small>
          Bars to ±{barBound} filings a day; the net line to ±{netBound}. Separate
          scales, so a rising total cannot flatten the daily bars.
        </small>
      </figcaption>
    </figure>
  );
}

/**
 * Companies several different insiders bought at a market price at once.
 *
 * One promoter buying is a data point. Four separate people buying the same
 * company inside a month is the pattern that has held up out of sample, so it
 * leads the page.
 */
export function Clusters({ rows }) {
  if (!rows?.length) {
    return <p className="ia-empty">No company had three or more separate open-market buyers this month.</p>;
  }
  return (
    <div className="ia-clusters">
      {rows.slice(0, 8).map((row) => (
        <article key={row.company}>
          <header>
            <strong>{row.company}</strong>
            {row.symbol ? <em>{row.symbol}</em> : null}
          </header>
          <div className="ia-cluster-count">
            <Users aria-hidden="true" />
            <b>{row.buyers}</b>
            <span>separate buyers · {row.filings} filings</span>
          </div>
          <dl>
            <div><dt>Shares</dt><dd>{count(row.quantity)}</dd></div>
            <div>
              <dt>Stated value</dt>
              <dd>{row.valued ? money(row.value) : 'not disclosed'}</dd>
            </div>
            <div><dt>Latest</dt><dd>{pretty(row.lastReported)}</dd></div>
          </dl>
          {row.valued && row.valued < row.filings ? (
            <small>{row.valued} of {row.filings} filings state a value.</small>
          ) : null}
        </article>
      ))}
    </div>
  );
}

/** How the shares changed hands. Only the market rows are evidence of a price. */
export function ModeMix({ modes }) {
  const bars = useMemo(() => shareBars(modes), [modes]);
  if (!bars.length) return null;
  return (
    <div className="ia-modes">
      <div className="ia-mode-track">
        {bars.map((bar) => (
          <span key={bar.mode} className={bar.openMarket ? 'ia-mode on' : 'ia-mode'}
                style={{ width: `${bar.width}%` }} title={`${bar.mode}: ${bar.count}`} />
        ))}
      </div>
      <ul>
        {bars.slice(0, 7).map((bar) => (
          <li key={bar.mode}>
            <i className={bar.openMarket ? 'ia-key ia-key-buy' : 'ia-key ia-key-off'} />
            <span>{bar.mode}</span>
            <b>{bar.count}</b>
            <small>{bar.pct.toFixed(1)}%</small>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Pledge activity, which is a risk disclosure rather than a conviction one.
 *
 * A promoter pledging shares has borrowed against the company. It belongs
 * nowhere near the buy and sell counts, so it gets its own panel.
 */
export function PledgeWatch({ rows }) {
  if (!rows?.length) return <p className="ia-empty">No pledge filings in this window.</p>;
  return (
    <ul className="ia-pledges">
      {rows.slice(0, 8).map((row) => (
        <li key={row.company}>
          <div>
            <strong>{row.company}</strong>
            <small>{pretty(row.lastReported)}</small>
          </div>
          <span className={row.created > row.released ? 'ia-pledge up' : 'ia-pledge down'}>
            {row.created} created · {row.released} released
          </span>
          <b>{count(row.quantity)} shares</b>
        </li>
      ))}
    </ul>
  );
}

export function TradeRow({ row }) {
  const buy = isBuy(row);
  const market = openMarket(row);
  return (
    <article className={market ? 'ia-trade' : 'ia-trade muted'}>
      <div className={`ia-action ${buy ? 'buy' : 'sale'}`}>
        {buy ? <ArrowUpRight aria-hidden="true" /> : <ArrowDownRight aria-hidden="true" />}
      </div>
      <div className="ia-who">
        <h3>{row.company_name}{row.symbol ? <em>{row.symbol}</em> : null}</h3>
        <p>{row.person} · {row.category || 'category undisclosed'}</p>
      </div>
      <span className={market ? 'ia-tag on' : 'ia-tag'}>{row.mode}</span>
      <div className="ia-number">
        <strong>{row.value ? money(row.value) : count(row.quantity)}</strong>
        <small>{row.value ? `${count(row.quantity)} shares` : 'shares · no value stated'}</small>
      </div>
    </article>
  );
}

export default function InsiderActivityPage() {
  const [data, setData] = useState(null);
  const [range, setRange] = useState('60');
  const [search, setSearch] = useState('');
  const [regime, setRegime] = useState('insider');
  const [error, setError] = useState('');

  useEffect(() => {
    const start = new Date();
    start.setDate(start.getDate() - Number(range));
    const params = { from: range === 'all' ? '' : start.toISOString().slice(0, 10), search, regime };
    const timer = setTimeout(() => {
      insiderActivity(params).then((body) => { setData(body); setError(''); })
        .catch((issue) => setError(issue.message));
    }, 200);
    return () => clearTimeout(timer);
  }, [range, search, regime]);

  const stats = data?.stats || {};
  const trades = data?.trades || [];
  const latestNet = data?.daily?.at(-1)?.cumulativeNet ?? null;

  const byDate = useMemo(() => {
    const groups = new Map();
    for (const row of trades) {
      const date = String(row.reported_on || '').slice(0, 10);
      if (!date) continue;
      if (!groups.has(date)) groups.set(date, []);
      groups.get(date).push(row);
    }
    return [...groups.entries()].sort((a, b) => b[0].localeCompare(a[0])).slice(0, 20);
  }, [trades]);

  return (
    <div className="ia">
      <Helmet><title>India Insider Activity | Agarwal Global Investments</title></Helmet>

      <header className="ia-hero">
        <div>
          <span>AGI / INDIA INSIDER ACTIVITY</span>
          <h1>Follow the people<br /><i>closest to the business.</i></h1>
          <p>
            Exchange filings, split by whether anyone actually paid a market price.
            Gifts, ESOP allotments and off-market transfers are shown, but they never
            enter the flow or the clusters.
          </p>
        </div>
        <aside>
          <small>Net open-market filings</small>
          <strong className={latestNet > 0 ? 'up' : latestNet < 0 ? 'down' : ''}>
            {latestNet == null ? '—' : `${latestNet > 0 ? '+' : ''}${latestNet}`}
          </strong>
          <small>Latest disclosure</small>
          <b>{pretty(stats.latestDate)}</b>
          <p><ShieldCheck aria-hidden="true" /> Observed filings only. Nothing is estimated.</p>
        </aside>
      </header>

      <nav className="ia-country">
        <button type="button" className="active">India</button>
        <button type="button" disabled>United States <small>Coming next</small></button>
      </nav>

      <section className="ia-controls">
        <div>
          {RANGES.map(([value, label]) => (
            <button type="button" key={value} className={range === value ? 'active' : ''}
                    onClick={() => setRange(value)}>{label}</button>
          ))}
        </div>
        <div className="ia-regime">
          {[['insider', 'Insider filings'], ['sast', 'Takeover code'], ['all', 'Both']].map(([value, label]) => (
            <button type="button" key={value} className={regime === value ? 'active' : ''}
                    onClick={() => setRegime(value)}>{label}</button>
          ))}
        </div>
        <label className="ia-search">
          <Search aria-hidden="true" />
          <input value={search} onChange={(event) => setSearch(event.target.value)}
                 placeholder="Company, insider or ticker" />
        </label>
      </section>

      {error ? <p className="ia-error">{error}</p> : (
        <>
          <section className="ia-stats">
            {[
              ['Filings', count(stats.records)],
              ['Companies', count(stats.companies)],
              ['At a market price', count(stats.openMarket)],
              ['Open-market buys', count(stats.buys)],
              ['Open-market sells', count(stats.sells)],
              ['Value stated on', stats.valueCoveragePct == null ? '—' : `${stats.valueCoveragePct}%`],
            ].map(([label, value]) => (
              <article key={label}><small>{label}</small><strong>{value}</strong></article>
            ))}
          </section>

          <p className="ia-note">
            <CalendarDays aria-hidden="true" />
            {count(stats.insiderRecords)} insider filings and {count(stats.sastRecords)} takeover-code
            filings. Takeover-code filings disclose a shareholding change and never a
            price, which is why value coverage is quoted against insider filings alone.
          </p>

          <main className="ia-main">
            <section className="ia-panel">
              <div className="ia-section-title">
                <span>CONVICTION CLUSTERS</span>
                <h2>Where several insiders bought at once</h2>
              </div>
              <Clusters rows={data?.clusters} />
            </section>

            <section className="ia-panel">
              <div className="ia-section-title">
                <span>DIRECTION OF FLOW</span>
                <h2>Open-market buying against selling</h2>
              </div>
              <FlowChart days={data?.daily} />
            </section>

            <div className="ia-split">
              <section className="ia-panel">
                <div className="ia-section-title">
                  <span>HOW SHARES CHANGED HANDS</span>
                  <h2>Market trades against everything else</h2>
                </div>
                <ModeMix modes={data?.modes} />
              </section>

              <section className="ia-panel">
                <div className="ia-section-title">
                  <span>PLEDGE WATCH</span>
                  <h2><AlertTriangle aria-hidden="true" /> Borrowing against the holding</h2>
                </div>
                <PledgeWatch rows={data?.pledges} />
              </section>
            </div>

            <section className="ia-panel">
              <div className="ia-section-title">
                <span>TRANSACTION TAPE</span>
                <h2>Every filing, in the order it was reported</h2>
              </div>
              {byDate.map(([date, rows]) => (
                <div className="ia-day" key={date}>
                  <header>
                    <strong>{pretty(date)}</strong>
                    <span>{rows.length} filings · {rows.filter(openMarket).length} at a market price</span>
                  </header>
                  {rows.map((row, index) => (
                    <TradeRow key={`${date}-${row.person}-${row.quantity}-${index}`} row={row} />
                  ))}
                </div>
              ))}
            </section>
          </main>

          <footer className="ia-method">
            <b>How to read this page</b>
            <p>
              An acquisition is not automatically bullish. ESOP allotments are pay,
              gifts move shares without a price, and inter-se transfers move them
              between people who already control the company. Only the filings marked
              at a market price are evidence that someone put money at risk.
            </p>
            {data?.degraded ? (
              <p className="ia-degraded">
                Showing the older uploaded copy — the live warehouse did not answer.
              </p>
            ) : null}
          </footer>
        </>
      )}
    </div>
  );
}
