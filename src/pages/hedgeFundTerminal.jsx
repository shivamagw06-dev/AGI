import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, ChevronDown, ChevronRight, Layers3, Search, Sparkles, Target } from 'lucide-react';
import {
  getHflOpportunity,
  getHflScan,
  getHflTerminal,
  hflBacktest,
} from '@/lib/intelligenceApi';
import { postUiSearch } from '@/lib/uiApi';

const n = (v, digits = 2) => {
  if (v == null || v === '') return '—';
  if (typeof v !== 'number') return String(v);
  if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return Number.isInteger(v) ? String(v) : v.toFixed(digits);
};

const pct = (v, digits = 1) => (v == null ? '—' : `${n(v, digits)}%`);

const crore = (v) => (typeof v === 'number' && v > 0 ? `₹${n(v / 1e7, 0)} cr` : '—');

const HIDDEN_HEDGE_FUND_MODULES = ['reliability registry', 'live alpha', 'forecast intelligence'];

function isHiddenHedgeFundModule(item) {
  const identity = [item?.id, item?.label, item?.name]
    .filter(Boolean)
    .join(' ')
    .replaceAll('_', ' ')
    .toLowerCase();
  return HIDDEN_HEDGE_FUND_MODULES.some((module) => identity.includes(module));
}

function ConfluenceBadge({ label }) {
  if (!label) return '—';
  const slug = String(label).toLowerCase().replace(/\s+/g, '-');
  return <span className={`hft-label hft-label-${slug}`}>{label}</span>;
}

function Stars({ n: count }) {
  if (!count) return <span className="hft-dim">—</span>;
  return (
    <span className="hft-stars" aria-label={`${count} of 5`}>
      {'★'.repeat(count)}
      <span className="dim">{'★'.repeat(Math.max(0, 5 - count))}</span>
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Inline Ask — answers on this page, never a redirect                  */
/* ------------------------------------------------------------------ */
const ASK_EXAMPLES = [
  'Why is Axis Bank in the value scanner?',
  'Compare Axis Bank and ICICI Bank on valuation',
  'Which sector looks most attractive today and why?',
  'What does a widening pair spread in cement imply?',
];

export function InlineAsk() {
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState('');

  const ask = useCallback(async (question) => {
    const value = String(question || '').trim();
    if (!value || busy) return;
    setBusy(true);
    setError('');
    setAnswer(null);
    try {
      const res = await postUiSearch(value);
      const text =
        res?.answer?.summary ||
        res?.executive_summary ||
        res?.answer?.executive_summary ||
        '';
      if (!text) {
        setError('AGI returned no answer for that question.');
      } else {
        setAnswer({
          text,
          why: Array.isArray(res?.why) ? res.why.slice(0, 5) : [],
          risks: Array.isArray(res?.key_risks) ? res.key_risks.slice(0, 3) : [],
          catalysts: Array.isArray(res?.key_catalysts) ? res.key_catalysts.slice(0, 3) : [],
          confidence: res?.confidence ?? null,
          stance: res?.answer?.stance || res?.house_view || null,
        });
      }
    } catch (err) {
      setError(err?.message || 'Ask failed');
    } finally {
      setBusy(false);
    }
  }, [busy]);

  return (
    <div className="hft-ask">
      <form
        className="hft-ask-bar"
        onSubmit={(e) => {
          e.preventDefault();
          ask(q);
        }}
      >
        <Search size={15} />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ask AGI about any company, scanner result, sector or spread"
          aria-label="Ask AGI"
        />
        <button type="submit" disabled={busy}>{busy ? 'Thinking…' : 'Ask'}</button>
      </form>

      <div className="hft-ask-examples">
        {ASK_EXAMPLES.map((example) => (
          <button key={example} type="button" onClick={() => { setQ(example); ask(example); }}>
            {example}
          </button>
        ))}
      </div>

      {busy ? <div className="hft-ask-answer hft-dim">Running the full AGI pipeline — this can take up to a minute.</div> : null}
      {error ? <div className="hft-ask-answer hft-error">{error}</div> : null}
      {answer ? (
        <div className="hft-ask-answer">
          <div className="hft-ask-head">
            <Sparkles size={13} /> AGI
            {answer.confidence != null ? <span className="hft-dim">confidence {answer.confidence}</span> : null}
            {answer.stance ? <span className="hft-dim">{answer.stance}</span> : null}
          </div>
          <p>{answer.text}</p>
          {answer.why.length ? (
            <ul className="hft-ask-why">{answer.why.map((w) => <li key={w}>{w}</li>)}</ul>
          ) : null}
          {answer.risks.length ? <div className="hft-dim">Risks: {answer.risks.join(' · ')}</div> : null}
          {answer.catalysts.length ? <div className="hft-dim">Catalysts: {answer.catalysts.join(' · ')}</div> : null}
        </div>
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Regime strip                                                         */
/* ------------------------------------------------------------------ */
function RegimeStrip({ regime }) {
  if (!regime?.ok) return null;
  const rotation = regime.sector_rotation || {};
  const cells = [
    ['Market regime', regime.stance],
    ['1Y positive-return breadth', pct(regime.positive_1y_return_pct ?? regime.breadth_advancing_pct)],
    ['Daily advance / decline', regime.advance_decline_ratio == null ? 'Not available' : n(regime.advance_decline_ratio)],
    ['Median 1Y return', pct(regime.median_return_1y_pct)],
    ['Return dispersion', pct(regime.return_dispersion_pct)],
    ['Median P/E', n(regime.median_pe)],
    ['Valuation', regime.valuation_stance],
    ['Consensus upside', pct(regime.median_consensus_upside_pct)],
    ['Sentiment', regime.institutional_sentiment],
    ['Most attractive sector', rotation.most_attractive?.sector || '—'],
    ['Least attractive sector', rotation.least_attractive?.sector || '—'],
    ['Universe', n(regime.universe)],
  ];
  return (
    <>
      <section className="hft-regime">
        {cells.map(([label, value]) => (
          <div key={label}>
            <span className="k">{label}</span>
            <span className="v">{value ?? '—'}</span>
            {label === 'Market regime' ? <span className="k">AGI model output</span> : null}
          </div>
        ))}
      </section>
      <p className="hft-dim hft-lead">
        Why: {regime.methodology?.drivers || 'covered-universe 1Y breadth, momentum and valuation'}.
        {' '}This is not a live daily advance/decline classification.
      </p>
    </>
  );
}

function InstitutionalStack({ stack }) {
  if (!stack) return null;
  const library = stack.strategy_library || {};
  const scanners = stack.research_scanners || {};
  const alpha = stack.alpha_opportunity || {};
  const cells = [
    { icon: Layers3, label: 'Strategy library', value: library.count, detail: 'Institutional methodologies' },
    { icon: Activity, label: 'Research scanners', value: scanners.count, detail: `${scanners.operational || 0} operational · ${scanners.experimental || 0} experimental` },
    { icon: Target, label: 'Alpha Opportunity', value: alpha.companies_flagged ?? 0, detail: `${alpha.multi_strategy_companies || 0} multi-strategy · ${alpha.queue_size || 0} queued` },
  ];
  return (
    <section className="hft-stack" aria-label="AGI institutional strategy stack">
      {cells.map(({ icon: Icon, label, value, detail }) => (
        <div key={label} className="hft-stack-cell">
          <Icon size={16} />
          <div><span>{label}</span><strong>{n(value, 0)}</strong><small>{detail}</small></div>
        </div>
      ))}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Opportunity explanation                                              */
/* ------------------------------------------------------------------ */
function Explanation({ ticker }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let live = true;
    getHflOpportunity(ticker)
      .then((res) => { if (live) setData(res); })
      .catch((err) => { if (live) setError(err?.message || 'Failed to load'); });
    return () => { live = false; };
  }, [ticker]);

  if (error) return <div className="hft-error">{error}</div>;
  if (!data) return <div className="hft-dim">Assembling the evidence…</div>;
  if (!data.ok) return <div className="hft-dim">No detail available for {ticker}.</div>;

  return (
    <div className="hft-explain">
      <div className="hft-explain-grid">
        <div>
          <h5>Why AGI surfaced this</h5>
          <ul>
            {(data.strategies_matched || []).map((m) => (
              <li key={m.strategy}>
                <b>{m.label}</b> · confidence {m.confidence}
                <div className="hft-dim">{m.why}</div>
              </li>
            ))}
            {!(data.strategies_matched || []).length ? <li className="hft-dim">No scanner currently flags this company.</li> : null}
          </ul>
        </div>
        <div>
          <h5>How the score is built</h5>
          <table className="hft-chain">
            <tbody>
              {(data.calculation_chain || []).map((step) => (
                <tr key={step.step}><td>{step.step}</td><td>{n(step.value)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <h5>Risks</h5>
          <ul>{(data.risks || []).map((r) => <li key={r}>{r}</li>)}</ul>
          <h5>Catalysts</h5>
          <ul>{(data.catalysts || []).map((c) => <li key={c}>{c}</li>)}</ul>
        </div>
        <div>
          <h5>Evidence</h5>
          <table className="hft-chain">
            <tbody>
              <tr><td>Market data · Yahoo</td><td>P/E {n(data.market?.pe)} · P/B {n(data.market?.pb)} · yield {pct(data.market?.dividend_yield)}</td></tr>
              <tr><td>Quality · annual warehouse</td><td>ROE {pct(data.quality?.roe)} · margin {pct(data.quality?.profit_margin)} · D/E {data.quality?.debt_to_equity == null ? '—' : `${n(data.quality.debt_to_equity)}x`}</td></tr>
              <tr><td>Industry · AGI</td><td>{data.industry_context?.primary_metric?.toUpperCase()} {n(data.industry_context?.company_value)} vs median {n(data.industry_context?.industry_median)} ({pct(data.industry_context?.gap_pct)})</td></tr>
              <tr><td>AGI Market Consensus</td><td>{pct(data.consensus?.upside)} upside · {n(data.consensus?.coverage)} brokers</td></tr>
            </tbody>
          </table>
          {(data.timeline || []).length ? (
            <>
              <h5>Scanner timeline</h5>
              <ul className="hft-timeline">
                {data.timeline.slice(-6).map((t, i) => (
                  <li key={`${t.date}-${t.event}-${i}`}><span>{t.date}</span> {t.event}</li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      </div>
      <p className="hft-bottom">{data.bottom_line}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Opportunity table for one scanner                                    */
/* ------------------------------------------------------------------ */
export function OpportunityTable({ scan, label, previewRows = null, researchQuestion = '' }) {
  const [rows, setRows] = useState(() => (Array.isArray(previewRows) ? previewRows : []));
  const [meta, setMeta] = useState(() => (
    Array.isArray(previewRows) && previewRows.length
      ? { count: previewRows.length, research_question: researchQuestion, universe_scanned: null }
      : null
  ));
  const [open, setOpen] = useState(null);
  const [busy, setBusy] = useState(!(Array.isArray(previewRows) && previewRows.length));
  const [error, setError] = useState('');

  useEffect(() => {
    let live = true;
    setOpen(null);
    // Prefer embedded terminal preview so first paint does not re-scan the universe.
    if (Array.isArray(previewRows) && previewRows.length) {
      setRows(previewRows);
      setMeta({
        count: previewRows.length,
        research_question: researchQuestion,
        universe_scanned: null,
      });
      setBusy(false);
      setError('');
      return () => { live = false; };
    }
    setBusy(true);
    getHflScan(scan, { limit: 15 })
      .then((res) => {
        if (!live) return;
        setRows(res?.results || []);
        setMeta(res || null);
        setError(res?.ok === false ? res?.error || 'Scan failed' : '');
      })
      .catch((err) => { if (live) setError(err?.message || 'Scan failed'); })
      .finally(() => { if (live) setBusy(false); });
    return () => { live = false; };
  }, [scan, previewRows, researchQuestion]);

  if (busy) return <div className="hft-dim">Scanning the universe…</div>;
  if (error) return <div className="hft-error">{error}</div>;

  const pairs = scan === 'pairs';
  return (
    <div className="hft-opps">
      <div className="hft-opps-head">
        <div>
          <b>{label}</b> · {meta?.count || 0} opportunities from {n(meta?.universe_scanned)} companies
        </div>
        <div className="hft-dim">{meta?.research_question}</div>
      </div>
      <div className="hft-table-wrap">
        <table className="hft-table">
          <thead>
            <tr>
              <th />
              <th>{pairs ? 'Long leg' : 'Company'}</th>
              <th>{pairs ? 'Short leg' : 'Sector'}</th>
              <th>Industry</th>
              <th>Confidence</th>
              <th>Consensus</th>
              <th>Why it qualified</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const ticker = pairs ? row.long_leg?.ticker : row.ticker;
              const key = pairs ? `${row.industry}-${ticker}` : ticker;
              const isOpen = open === key;
              const colSpan = 7;
              return (
                <Fragment key={key}>
                  <tr className={isOpen ? 'open' : ''}>
                    <td>
                      <button type="button" className="hft-toggle" onClick={() => setOpen(isOpen ? null : key)}>
                        {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </button>
                    </td>
                    <td>
                      <strong>{pairs ? row.long_leg?.company_name : row.company_name}</strong>
                      <div className="hft-dim">{ticker}</div>
                    </td>
                    <td>{pairs ? row.short_leg?.company_name : row.sector}</td>
                    <td>{row.industry}</td>
                    <td><span className="hft-conf">{row.confidence ?? '—'}</span></td>
                    <td>{pairs ? `${n(row.spread_multiple)}× spread` : pct(row.consensus_upside)}</td>
                    <td className="hft-why">{row.why}</td>
                  </tr>
                  {isOpen && ticker ? (
                    <tr className="hft-detail-row">
                      <td colSpan={colSpan}><Explanation ticker={ticker} /></td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="hft-note">
        Market data, daily and intraday observations, financial history and consensus from the AGI research warehouse; interpretation by AGI. Research observations only — never a buy, sell or target price.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* The terminal                                                         */
/* ------------------------------------------------------------------ */
export default function HedgeFundTerminal() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [scan, setScan] = useState('value');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let live = true;
    setLoading(true);
    setError('');
    getHflTerminal({ limit: 12 })
      .then((res) => {
        if (!live) return;
        if (res?.ok === false) {
          setError(res?.error || 'Terminal unavailable');
          setData(null);
        } else {
          setData(res);
          setError('');
        }
      })
      .catch((err) => {
        if (!live) return;
        setError(err?.message || 'Terminal unavailable');
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => { live = false; };
  }, [reloadKey]);

  const hero = data?.hero || {};
  const dash = data?.market_dashboard || {};
  const daily = data?.daily_intelligence || {};
  const cards = useMemo(
    () => (data?.cards || []).filter((card) => !isHiddenHedgeFundModule(card)),
    [data?.cards],
  );
  const active = cards.find((c) => c.id === scan) || cards[0];

  return (
    <div className="hft">
      {loading && !data ? (
        <div className="hft-dim" style={{ padding: '1rem 0' }}>
          Loading the terminal…
        </div>
      ) : null}
      {error ? (
        <div className="hft-error" style={{ marginBottom: '0.75rem' }}>
          {error}
          <div style={{ marginTop: '0.5rem' }}>
            <button type="button" className="hft-toggle" onClick={() => setReloadKey((k) => k + 1)}>
              Retry terminal
            </button>
          </div>
        </div>
      ) : null}
      {!data && !loading ? (
        <div className="hft-dim">
          Terminal data is unavailable right now. Strategy library and calculators below still work.
        </div>
      ) : null}

      {data ? <RegimeStrip regime={data.regime} /> : null}
      {data ? <InstitutionalStack stack={data.institutional_stack} /> : null}

      {data?.generated_at || data?.freshness ? (
        <p className="hft-freshness" data-freshness={data.freshness || 'unknown'}>
          Snapshot{' '}
          {data.generated_at
            ? new Date(data.generated_at).toLocaleString('en-IN', {
                timeZone: 'Asia/Kolkata',
                day: '2-digit',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
              })
            : '—'}
          {data.freshness ? ` · ${data.freshness}` : ''}
          {data.source_as_of || data.as_of ? ` · source ${data.source_as_of || data.as_of}` : ''}
          {data.cache?.stale || data.freshness === 'stale' ? ' · serving stored result' : ''}
        </p>
      ) : null}

      <section className="hft-hero">
        {[
          ['Universe scanned', n(hero.universe_scanned)],
          ['Strategies running', n(hero.strategies_running)],
          ['Research modules', n(hero.research_modules)],
          ['Live opportunities', n(hero.live_opportunities)],
          ['Companies flagged', n(hero.companies_flagged)],
          ['Multi-strategy names', n(hero.multi_strategy_companies)],
        ].map(([label, value]) => (
          <div key={label} className="hft-stat">
            <span className="k">{label}</span>
            <span className="v">{value}</span>
          </div>
        ))}
      </section>

      <section className="hft-highlights">
        {(hero.highlights || []).filter((h) => !isHiddenHedgeFundModule(h)).map((h) => {
          const row = h.row || {};
          const name = row.company_name || row.long_leg?.company_name;
          return (
            <div key={h.label} className="hft-highlight">
              <span className="k">{h.label}</span>
              <strong>{name}</strong>
              <p>{row.why}</p>
            </div>
          );
        })}
      </section>

      <h2 id="live-strategy-scanners" className="hft-title"><Activity size={15} /> Live strategy scanners</h2>
      <p className="hft-dim hft-lead">
        Operational means the scanner runs on available data; it does not mean the strategy is research or investment
        validated. Confidence is a screen-strength score, not a probability of profit.
      </p>
      <section className="hft-scanners">
        {cards.map((card) => (
          <button
            key={card.id}
            type="button"
            className={`hft-scan-card ${scan === card.id ? 'active' : ''}`}
            onClick={() => setScan(card.id)}
          >
            <div className="top">
              <span className="name">{card.label}</span>
              <Stars n={card.suitability_stars} />
            </div>
            <div className="hft-dim">{card.qualification_label || 'Candidate'}</div>
            <div className="hft-dim">{card.backtest_status === 'not_backtested' ? 'Not backtested' : card.backtest_status}</div>
            <div className="count">{n(card.count)}<span>opportunities</span></div>
            <div className="meta">
              <span>Avg confidence {card.avg_confidence ?? '—'}</span>
              <span>{card.entered_today ? `+${card.entered_today} today` : 'no change today'}</span>
            </div>
            <div className="alpha">{card.alpha_source}</div>
            <div className="risk">{card.risk_level}</div>
          </button>
        ))}
      </section>

      {active ? (
        <OpportunityTable
          scan={active.id}
          label={active.label}
          previewRows={active.results || null}
          researchQuestion={active.research_question || ''}
        />
      ) : null}

      <BacktestPanel />

      {data ? (
        <>
      <h2 className="hft-title">Strategy overlap</h2>
      <p className="hft-dim hft-lead">
        Independent Hedge Fund scanners reaching the same company. The composite is AGI-designed and not empirically
        optimized; it is a research-prioritisation score, not evidence of investment performance.
      </p>
      <div className="hft-table-wrap">
        <table className="hft-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Sector</th>
              <th>Label</th>
              <th>Strategies</th>
              <th>Unified</th>
            </tr>
          </thead>
          <tbody>
            {(data.overlap || []).slice(0, 12).map((row) => (
              <tr key={row.ticker}>
                <td><strong>{row.company_name}</strong><div className="hft-dim">{row.ticker}</div></td>
                <td>{row.sector}</td>
                <td><ConfluenceBadge label={row.confluence_label} /></td>
                <td>{(row.strategies || []).join(' · ')}</td>
                <td>{row.unified_score ?? row.priority_score ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="hft-title">Today&rsquo;s research queue</h2>
      <div className="hft-table-wrap">
        <table className="hft-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Company</th>
              <th>Label</th>
              <th>Priority</th>
              <th>Why</th>
              <th>Unified</th>
            </tr>
          </thead>
          <tbody>
            {(data.research_queue || []).map((row) => (
              <tr key={row.ticker}>
                <td>{row.rank}</td>
                <td><strong>{row.company_name}</strong><div className="hft-dim">{row.industry}</div></td>
                <td><ConfluenceBadge label={row.confluence_label} /></td>
                <td><Stars n={row.stars} /></td>
                <td className="hft-why">{row.why}</td>
                <td>{row.unified_score ?? row.confidence ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
        </>
      ) : null}

      {data ? (
        <>
      <h2 className="hft-title">Daily intelligence</h2>
      <div className="hft-daily">
        <div>
          <h5>Entered the scanners</h5>
          {(daily.new_opportunities || []).length ? (
            <ul>
              {daily.new_opportunities.slice(0, 8).map((o) => (
                <li key={`${o.ticker}-${o.strategy}`}><b>{o.company_name}</b> · {o.strategy_label}</li>
              ))}
            </ul>
          ) : <p className="hft-dim">{daily.note}</p>}
        </div>
        <div>
          <h5>Left the scanners</h5>
          {(daily.removed_opportunities || []).length ? (
            <ul>
              {daily.removed_opportunities.slice(0, 8).map((o) => (
                <li key={`${o.ticker}-${o.strategy}`}><b>{o.ticker}</b> · {o.strategy_label}</li>
              ))}
            </ul>
          ) : <p className="hft-dim">Nothing dropped out since the last recorded scan.</p>}
        </div>
      </div>

      <h2 className="hft-title">Market dashboard</h2>
      <div className="hft-dash">
        <div>
          <h5>Sector valuation data</h5>
          <p className="hft-dim">
            Lowest median P/E: <b>{dash.lowest_median_pe_sector?.sector || dash.cheapest_sector?.sector || '—'}</b> at {n(dash.lowest_median_pe_sector?.median_pe ?? dash.cheapest_sector?.median_pe)}× ·
            {' '}Highest median P/E: <b>{dash.highest_median_pe_sector?.sector || dash.most_expensive_sector?.sector || '—'}</b> at {n(dash.highest_median_pe_sector?.median_pe ?? dash.most_expensive_sector?.median_pe)}×
          </p>
          <p className="hft-dim">
            {dash.methodology?.definition || 'Median constituent trailing P/E'} · {dash.methodology?.weighting || 'equal-weighted median'}<br />
            Universe: {dash.methodology?.universe || 'covered warehouse companies grouped by primary sector'} · Excludes: {dash.methodology?.exclusions || 'missing and invalid observations'}<br />
            Accounting: {dash.methodology?.accounting || 'reported trailing metrics; scope disclosed where available'} · As of: {dash.methodology?.period || data.as_of || '—'} · Source: {dash.methodology?.source || 'AGI Research Warehouse'}
          </p>
          {dash.metric_methodology ? (
            <p className="hft-dim">
              P/B: {dash.metric_methodology.pb}<br />
              EV/EBITDA: {dash.metric_methodology.ev_ebitda}
            </p>
          ) : null}
          <div className="hft-table-wrap">
            <table className="hft-table compact">
              <thead><tr><th>Sector</th><th>P/E</th><th>ROE</th><th>Yield</th><th>1Y</th><th>Upside</th></tr></thead>
              <tbody>
                {(dash.sectors || []).map((s) => (
                  <tr key={s.sector}>
                    <td>{s.sector}</td><td>{n(s.median_pe)}</td><td>{pct(s.median_roe)}</td>
                    <td>{pct(s.median_yield)}</td><td>{pct(s.median_return_1y)}</td><td>{pct(s.median_upside)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <h5>Largest headline discounts to industry</h5>
          <ul className="hft-list">
            {(dash.largest_discounts || []).map((r) => (
              <li key={r.ticker}><b>{r.company_name}</b> {n(r.value)}× vs {n(r.industry_median)}× · {n(r.relative_multiple)}× relative <span className="hft-dim">{r.validation_status === 'normalization_required' ? 'Normalization required' : crore(r.market_cap)}</span></li>
            ))}
          </ul>
          <h5>Largest headline premiums to industry</h5>
          <ul className="hft-list">
            {(dash.largest_premiums || []).map((r) => (
              <li key={r.ticker}><b>{r.company_name}</b> {n(r.value)}× vs {n(r.industry_median)}× · {n(r.relative_multiple)}× relative</li>
            ))}
          </ul>
        </div>
        <div>
          <h5>Highest return on equity</h5>
          <ul className="hft-list">
            {(dash.highest_roe || []).map((r) => <li key={r.ticker}><b>{r.company_name}</b> {pct(r.roe)}</li>)}
          </ul>
          <h5>Highest consensus upside</h5>
          <ul className="hft-list">
            {(dash.highest_conviction || []).map((r) => (
              <li key={r.ticker}><b>{r.company_name}</b> {pct(r.upside)} · {n(r.coverage)} brokers</li>
            ))}
          </ul>
        </div>
        <div>
          <h5>Factor readings</h5>
          <p className="hft-dim">{data.factors?.methodology?.warning || 'Screening counts, not pure factor portfolios.'}</p>
          <ul className="hft-list">
            {((data.factors || {}).factors || []).map((f) => (
              <li key={f.factor}>
                <b>{f.factor}</b> {f.companies} companies ({f.share_pct}%)
                <div className="hft-dim">{f.definition}</div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <p className="hft-note">
        Scanned {n(data.hero?.universe_scanned)} companies on {data.source_as_of || data.as_of}
        {data.generated_at ? ` · generated ${new Date(data.generated_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}` : ''}
        {data.freshness ? ` · ${data.freshness}` : ''}
        {data.compared_with ? `, compared with ${data.compared_with}` : ''}. {data.policy}
      </p>
        </>
      ) : null}
    </div>
  );
}

function BacktestPanel() {
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const run = async () => {
    setBusy(true); setError('');
    try {
      const response = await hflBacktest('momentum');
      if (!response?.ok) setError(response?.detail || response?.error || 'Backtest unavailable');
      else setResult(response);
    } catch (err) {
      setError(err?.message || 'Backtest unavailable');
    } finally { setBusy(false); }
  };
  const metrics = result?.metrics || {};
  return (
    <section className="hft-dash">
      <div>
        <h5>Backtest specification</h5>
        <p className="hft-dim">12–1 momentum, monthly rebalance, next-close execution, turnover costs and close-based stop.</p>
        <button className="hft-ask-bar" type="button" onClick={run} disabled={busy}>
          {busy ? 'Running point-in-time backtest…' : 'Run momentum backtest'}
        </button>
        {error ? <p className="hft-error">{error}</p> : null}
      </div>
      {result ? <div>
        <h5>Research output — not a recommendation</h5>
        <p>Cumulative return: <b>{pct(metrics.cumulative_return_pct)}</b> · Annualised: <b>{pct(metrics.annualized_return_pct)}</b></p>
        <p>Volatility: {pct(metrics.annualized_volatility_pct)} · Sharpe: {n(metrics.sharpe)} · Max drawdown: {pct(metrics.max_drawdown_pct)}</p>
        <p className="hft-dim">{result.coverage?.backtest_sessions} sessions · {result.coverage?.symbols_with_price_history} symbols · {result.average_turnover_pct}% average one-way turnover.</p>
      </div> : null}
    </section>
  );
}
