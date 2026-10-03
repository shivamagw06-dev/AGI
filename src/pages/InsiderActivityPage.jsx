import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  AlertTriangle, ArrowDownRight, ArrowUpRight, CalendarDays, Minus, Search, ShieldCheck, Users,
} from 'lucide-react';

import { insiderActivity } from '@/lib/insiderTradingApi';
import { flowChart, shareBars } from '@/lib/insiderCharts';
import './insiderActivity.css';
import IntelligenceDesk from '@/components/Insider/IntelligenceDesk';

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

const money = (value, country='IN') => {
  if(country==='US')return new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(Number(value)||0);
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

const openMarket = (row) => row?.country==='US'?String(row?.is_purchase_sale)==='true':String(row?.is_open_market) === 'true';

/**
 * Which way a filing points, in three states rather than two.
 *
 * A pledge creation is neither a purchase nor a sale, and the previous version
 * drew a down arrow on it because it was not a buy. That reads as selling. A
 * filing that states no direction gets a bar instead.
 */
function direction(row) {
  const action = String(row?.action || '');
  if (/acquisition|purchase|buy/i.test(action)) return 'buy';
  if (/disposal|sale|sell/i.test(action)) return 'sell';
  return 'flat';
}

/**
 * Buys above the line, sells below, running total across.
 *
 * The running total is the point of the chart. A single heavy day of selling
 * says little; a fortnight where sellers outnumber buyers every day is the
 * thing worth seeing, and only a cumulative line shows it.
 */
export function FlowChart({ days, country='IN' }) {
  const chart = useMemo(() => flowChart(days, { width: 960, height: 250 }), [days]);
  if (chart.empty) {
    return <p className="ia-empty">No purchase/sale activity in this window.</p>;
  }
  const { width, height, zeroY, bars, line, marks, barBound, netBound, breaks } = chart;
  const labelEvery = Math.ceil(marks.length / 8);

  return (
    <figure className="ia-flow">
      <svg viewBox={`0 0 ${width} ${height + 26}`} role="img" preserveAspectRatio="none"
           aria-label={`Daily ${country === 'US' ? 'purchase and sale' : 'open-market insider'} filings. Running net stands at ${marks.at(-1)?.cumulativeNet}.`}>
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
          {breaks ? ` The line breaks over ${breaks === 1 ? 'a stretch' : `${breaks} stretches`} with no filings — those days are not covered by any export, which is not the same as nothing having happened.` : ''}
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

/**
 * What the current view is made of, in words.
 *
 * The sentence has to follow the filter. Written as a fixed split it read
 * "743 insider filings and 0 takeover-code filings" while the takeover filter
 * was simply switched off, which states that none exist rather than that none
 * are being shown.
 */
export function RegimeNote({ stats }) {
  const insider = Number(stats?.insiderRecords) || 0;
  const sast = Number(stats?.sastRecords) || 0;
  const coverage = stats?.valueCoveragePct;
  if (insider && sast) {
    return (
      <>
        {count(insider)} insider filings and {count(sast)} takeover-code filings.
        A takeover-code filing discloses a shareholding change and never a price,
        which is why value coverage is quoted against insider filings alone.
      </>
    );
  }
  if (sast) {
    return (
      <>
        Takeover-code filings only — an acquirer crossing a shareholding threshold,
        rather than a director trading their own company. These disclose how much
        of the company moved, never what was paid for it.
      </>
    );
  }
  return (
    <>
      Insider filings only — directors and promoters trading their own company.
      {coverage == null ? null : ` Value is stated on ${coverage}% of them.`} Switch
      to the takeover code for acquirers crossing a shareholding threshold.
    </>
  );
}

export function TradeRow({ row, country='IN' }) {
  const way = direction(row);
  const market = openMarket(row);
  const share = Number(row.traded_pct);
  return (
    <article className={market ? 'ia-trade' : 'ia-trade muted'}>
      <div className={`ia-action ${way}`}>
        {way === 'buy' ? <ArrowUpRight aria-hidden="true" /> : null}
        {way === 'sell' ? <ArrowDownRight aria-hidden="true" /> : null}
        {way === 'flat' ? <Minus aria-hidden="true" /> : null}
      </div>
      <div className="ia-who">
        <h3>{row.company_name}{row.symbol ? <em>{row.symbol}</em> : null}</h3>
        <p>{row.person} · {row.category || 'category undisclosed'}{country==='US'?` · Code ${row.transaction_code} · 10b5-1: ${row.planned||'unknown'}`:''}</p>
      </div>
      <span className={market ? 'ia-tag on' : 'ia-tag'}>{row.mode}</span>
      <div className="ia-number">
        <strong>{row.value ? money(row.value,country) : count(row.quantity)}</strong>
        <small>{row.value ? `${count(row.quantity)} shares` : `${count(row.quantity)} shares · no value stated`}</small>
        {Number.isFinite(share) && share >= 0.01 ? <b>{share}% of the company</b> : null}
      </div>
    </article>
  );
}

export default function InsiderActivityPage() {
  const [params,setParams]=useSearchParams();const country=params.get('country')==='US'?'US':'IN';
  function switchCountry(next){setData(null);setError('');setParams(p=>{const q=new URLSearchParams(p);q.set('country',next);q.delete('company');return q;});}
  const [data, setData] = useState(null);
  const [range, setRange] = useState('60');
  const [search, setSearch] = useState('');
  const [regime, setRegime] = useState('insider');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [visibleDates,setVisibleDates] = useState(20);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoading(true);setVisibleDates(20);
    const start = new Date();
    start.setDate(start.getDate() - Number(range));
    const params = { country, from: range === 'all' ? '' : start.toISOString().slice(0, 10), search, regime:country==='US'?'insider':regime };
    const timer = setTimeout(() => {
      insiderActivity(params,{signal:controller.signal}).then((body) => { if(active){setData(body); setError('');} })
        .catch((issue) => {if(active)setError(issue.message);}).finally(()=>{if(active)setLoading(false);});
    }, 200);
    return () => {active=false;clearTimeout(timer);controller.abort();};
  }, [range, search, regime,country]);

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
    return [...groups.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  }, [trades]);

  return (
    <div className="ia">
      <Helmet><title>{country==='US'?'US':'India'} Insider Activity | Agarwal Global Investments</title></Helmet>

      <header className="ia-hero">
        <div>
          <span>AGI / {country==='US'?'US':'INDIA'} INSIDER ACTIVITY</span>
          <h1>Follow the people<br /><i>closest to the business.</i></h1>
          <p>
            {country==='US'?'US insider disclosures you upload, with purchases and sales separated from awards, exercises, tax withholding and gifts. P/S codes include open-market and private transactions.':'Exchange filings, with open-market trades separated from gifts, ESOP allotments and off-market transfers.'}
          </p>
        </div>
        <aside>
          <small>{country==='US'?'Net purchase / sale transactions':'Net open-market filings'}</small>
          <strong className={latestNet > 0 ? 'up' : latestNet < 0 ? 'down' : ''}>
            {latestNet == null ? '—' : `${latestNet > 0 ? '+' : ''}${latestNet}`}
          </strong>
          <small>Latest disclosure</small>
          <b>{pretty(stats.latestDate)}</b>
          <p><ShieldCheck aria-hidden="true" /> Observed filings only. Nothing is estimated.</p>
        </aside>
      </header>

      <nav className="ia-country">
        <button type="button" className={country==='IN'?'active':''} onClick={()=>switchCountry('IN')}>India</button>
        <button type="button" className={country==='US'?'active':''} onClick={()=>switchCountry('US')}>United States</button>
      </nav>

      <IntelligenceDesk key={country} country={country} />

      <section className="ia-controls" aria-label="Historical filing filters">
        <div>
          {RANGES.map(([value, label]) => (
            <button type="button" key={value} className={range === value ? 'active' : ''}
                    onClick={() => setRange(value)}>{label}</button>
          ))}
        </div>
        {country==='IN'&&<div className="ia-regime">
          {[['insider', 'Insider filings'], ['sast', 'Takeover code'], ['all', 'Both']].map(([value, label]) => (
            <button type="button" key={value} className={regime === value ? 'active' : ''}
                    onClick={() => setRegime(value)}>{label}</button>
          ))}
        </div>}
        <label className="ia-search">
          <Search aria-hidden="true" />
          <input value={search} onChange={(event) => setSearch(event.target.value)}
                 placeholder="Company, insider or ticker" />
        </label>
      </section>

      {loading&&<p className="ia-note" role="status">Updating historical filings…</p>}
      {error ? <p className="ia-error">{error}</p> : (
        <>
          <section className="ia-stats">
            {[
              [country==='US'?'Transactions':'Filings', count(stats.records)],
              ['Companies', count(stats.companies)],
              [country==='US'?'Purchases / sales':'Open-market filings', count(stats.openMarket)],
              [country==='US'?'Purchases (P)':'Open-market buys', count(stats.buys)],
              [country==='US'?'Sales (S)':'Open-market sells', count(stats.sells)],
              ['Value stated on', stats.valueCoveragePct == null ? '—' : `${stats.valueCoveragePct}%`],
            ].map(([label, value]) => (
              <article key={label}><small>{label}</small><strong>{value}</strong></article>
            ))}
          </section>

          <p className="ia-note">
            <CalendarDays aria-hidden="true" />
            {country==='US'?'US dollars. P/S codes do not establish exchange execution or trading motive. Plan status is unknown unless supplied.':<RegimeNote stats={stats} />}
          </p>

          {!loading&&!trades.length&&<p className="ia-note">{country==='US'?'No US trades have been published for this selection yet. Publish a US batch from the administrator paste screen.':'No filings match this selection.'}</p>}
          <main className="ia-main">
            <section className="ia-panel">
              <div className="ia-section-title">
                <span>DIRECTION OF FLOW</span>
                <h2>{country==='US'?'Purchases against sales':'Open-market buying against selling'}</h2>
              </div>
              <FlowChart days={data?.daily} country={country} />
            </section>

            <div className="ia-split">
              <section className="ia-panel">
                <div className="ia-section-title">
                  <span>HOW SHARES CHANGED HANDS</span>
                  <h2>{country === 'US' ? 'Purchases and sales against other transactions' : 'Market trades against everything else'}</h2>
                </div>
                <ModeMix modes={data?.modes} />
              </section>

{country==='IN'&&              <section className="ia-panel">
                <div className="ia-section-title">
                  <span>PLEDGE WATCH</span>
                  <h2><AlertTriangle aria-hidden="true" /> Borrowing against the holding</h2>
                </div>
                <PledgeWatch rows={data?.pledges} />
              </section>}
            </div>

            <section className="ia-panel">
              <div className="ia-section-title">
                <span>TRANSACTION TAPE</span>
                <h2>Every filing, in the order it was reported</h2>
              </div>
              {byDate.slice(0,visibleDates).map(([date, rows]) => (
                <div className="ia-day" key={date}>
                  <header>
                    <strong>{pretty(date)}</strong>
                    <span>{rows.length} filings · {rows.filter(openMarket).length} {country==='US'?'purchases / sales':'open-market'}</span>
                  </header>
                  {rows.map((row, index) => (
                    <TradeRow key={`${date}-${row.person}-${row.quantity}-${index}`} row={row} country={country} />
                  ))}
                </div>
              ))}
              <p className="ia-note">Showing {byDate.slice(0,visibleDates).reduce((sum,[,rows])=>sum+rows.length,0)} of {trades.length} available filings.</p>
              {visibleDates<byDate.length&&<button className="ii-button" onClick={()=>setVisibleDates(n=>n+20)}>Load earlier filings</button>}
            </section>
          </main>

          <footer className="ia-method">
            <b>How to read this page</b>
            <p>
              {country==='US'?'P/S transactions can be private or open-market. Awards, gifts, tax withholding and exercises are different events. A disclosed 10b5-1 plan indicates a pre-arranged plan; missing plan information is not confirmation of discretionary trading.':'An acquisition is not automatically bullish. ESOP allotments are pay, gifts move shares without a price, and inter-se transfers can move them between connected people.'}
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
