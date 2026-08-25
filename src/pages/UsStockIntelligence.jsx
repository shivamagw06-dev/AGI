import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  CalendarClock,
  Database,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { getUsMarketOverview, getUsStockIntelligence } from '@/lib/intelligenceApi';
import './usStockIntelligence.css';

const QUICK_TICKERS = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'JPM', 'BRK-B'];
const SCREENER_LABELS = {
  day_gainers: 'Top gainers',
  day_losers: 'Top losers',
  most_active: 'Most active',
  value: 'Value screen',
  momentum: '12M momentum',
  dividend: 'Dividend leaders',
};

const num = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

function money(value, currency = 'USD', compact = false) {
  const parsed = num(value);
  if (parsed === null) return '--';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    notation: compact ? 'compact' : 'standard',
    maximumFractionDigits: compact ? 2 : 2,
  }).format(parsed);
}

function decimal(value, suffix = '', digits = 2) {
  const parsed = num(value);
  return parsed === null ? '--' : `${parsed.toFixed(digits)}${suffix}`;
}

function compact(value) {
  const parsed = num(value);
  if (parsed === null) return '--';
  return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(parsed);
}

function dateLabel(value) {
  if (!value) return '--';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? String(value)
    : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function Change({ value, suffix = '%' }) {
  const parsed = num(value);
  const positive = parsed !== null && parsed >= 0;
  return (
    <span className={`usi-change ${positive ? 'is-positive' : 'is-negative'}`}>
      {positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
      {parsed === null ? '--' : `${Math.abs(parsed).toFixed(2)}${suffix}`}
    </span>
  );
}

function Metric({ label, value, detail }) {
  return (
    <div className="usi-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

function SectionHeading({ eyebrow, title, note, icon: Icon }) {
  return (
    <div className="usi-section-heading">
      <div>
        <p>{eyebrow}</p>
        <h2>{Icon ? <Icon size={19} /> : null}{title}</h2>
      </div>
      {note ? <span>{note}</span> : null}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="usi-loading" aria-live="polite">
      <div className="usi-loading-mark"><Activity /></div>
      <p>Building the intelligence package</p>
      <span>Normalizing quote, valuation, financial history and corporate events.</span>
    </div>
  );
}

export default function UsStockIntelligence() {
  const [desk, setDesk] = useState('overview');
  const [input, setInput] = useState('AAPL');
  const [symbol, setSymbol] = useState('AAPL');
  const [requestKey, setRequestKey] = useState(0);
  const [range, setRange] = useState('1Y');
  const [screener, setScreener] = useState('day_gainers');
  const [data, setData] = useState(null);
  const [market, setMarket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [marketLoading, setMarketLoading] = useState(true);
  const [error, setError] = useState('');
  const [marketError, setMarketError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    getUsStockIntelligence(symbol)
      .then((result) => {
        if (active) setData(result);
      })
      .catch((err) => {
        if (active) setError(err?.message || 'US stock intelligence is temporarily unavailable.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [symbol, requestKey]);

  useEffect(() => {
    let active = true;
    let timer;
    const loadMarket = async (quiet = false) => {
      if (!quiet) setMarketLoading(true);
      setMarketError('');
      try {
        const result = await getUsMarketOverview();
        if (active) setMarket(result);
      } catch (err) {
        if (active) setMarketError(err?.message || 'US market overview is temporarily unavailable.');
      } finally {
        if (active) setMarketLoading(false);
      }
    };
    loadMarket();
    timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') loadMarket(true);
    }, 60_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  const chartData = useMemo(() => {
    const all = (data?.price_history || []).map((row) => ({
      date: row.ts,
      close: num(row.close),
    })).filter((row) => row.close !== null);
    const sessions = { '1M': 22, '3M': 66, '6M': 132, '1Y': 270 }[range] || 270;
    return all.slice(-sessions);
  }, [data, range]);

  const submit = (event) => {
    event?.preventDefault();
    const next = input.trim().toUpperCase().replace('BRK.B', 'BRK-B');
    if (next) { setSymbol(next); setDesk('stock'); }
  };

  const openStock = (ticker) => {
    if (!ticker || ticker.startsWith('^')) return;
    setInput(ticker);
    setSymbol(ticker);
    setDesk('stock');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const quote = data?.quote || {};
  const profile = data?.profile || {};
  const valuation = data?.valuation || {};
  const technicals = data?.technicals || {};
  const financials = data?.financials || {};
  const analyst = data?.analyst || {};
  const currency = profile.currency || financials.currency || 'USD';

  return (
    <main className="usi-page">
      <Helmet>
        <title>US Stock Intelligence | AGI</title>
        <meta name="description" content="US equity market, valuation, financial and risk intelligence using canonical Yahoo Finance data." />
      </Helmet>

      <div className="usi-grid-lines" aria-hidden="true" />
      <section className="usi-shell">
        <header className="usi-hero">
          <div className="usi-kicker"><span /> AGI GLOBAL EQUITIES / YAHOO CANONICAL</div>
          <div className="usi-hero-copy">
            <div>
              <h1>US Stock<br /><em>Intelligence</em></h1>
              <p>One evidence-led view of price behavior, valuation, business performance, analyst expectations and risk.</p>
            </div>
            <div className="usi-source-stamp">
              <Database size={18} />
              <div><strong>Yahoo Finance</strong><span>Market and secondary research source</span></div>
            </div>
          </div>

          <form className="usi-search" onSubmit={submit}>
            <Search size={20} />
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Enter a US ticker: AAPL, MSFT, NVDA"
              aria-label="US stock ticker"
            />
            <button type="submit">Build intelligence</button>
          </form>
          <div className="usi-quick-list">
            <span>Desk list</span>
            {QUICK_TICKERS.map((ticker) => (
              <button key={ticker} className={symbol === ticker ? 'is-active' : ''} onClick={() => openStock(ticker)}>
                {ticker}
              </button>
            ))}
          </div>
          <nav className="usi-desk-tabs" aria-label="US Stock Intelligence desks">
            <button className={desk === 'overview' ? 'is-active' : ''} onClick={() => setDesk('overview')}>Market overview</button>
            <button className={desk === 'screeners' ? 'is-active' : ''} onClick={() => setDesk('screeners')}>Live screeners</button>
            <button className={desk === 'stock' ? 'is-active' : ''} onClick={() => setDesk('stock')}>Stock research</button>
          </nav>
        </header>

        {desk === 'overview' && marketLoading ? <LoadingState /> : null}
        {desk === 'overview' && !marketLoading && marketError ? (
          <div className="usi-error"><AlertTriangle /><div><strong>Market overview unavailable</strong><p>{marketError}</p></div></div>
        ) : null}

        {desk === 'overview' && !marketLoading && !marketError && market ? (
          <div className="usi-market-desk">
            <section className="usi-market-status">
              <div><span className={`usi-live-dot ${market.market_state === 'REGULAR' ? 'is-live' : ''}`} /><p><strong>{market.market_state || 'UNKNOWN'}</strong><small>US market session</small></p></div>
              <div><strong>{market.breadth?.advancing || 0}</strong><small>Advancing</small></div>
              <div><strong>{market.breadth?.declining || 0}</strong><small>Declining</small></div>
              <div><strong>{decimal(market.breadth?.advance_ratio_pct, '%', 1)}</strong><small>Advance ratio</small></div>
              <div><strong>{market.quality?.bellwether_coverage || 0}</strong><small>Bellwethers live</small></div>
              <div><RefreshCw size={13} /><small>Auto-refresh 60s</small></div>
            </section>

            <section className="usi-market-section">
              <SectionHeading eyebrow="US market tape" title="Benchmarks" note={`Updated ${dateLabel(market.as_of)}`} icon={Activity} />
              <div className="usi-index-grid">
                {(market.benchmarks || []).map((row) => (
                  <article key={row.symbol}>
                    <span>{row.symbol}</span><h3>{row.name}</h3><strong>{num(row.price) === null ? '--' : Number(row.price).toLocaleString('en-US', { maximumFractionDigits: 2 })}</strong><Change value={row.change_pct} />
                  </article>
                ))}
              </div>
            </section>

            <section className="usi-market-section">
              <SectionHeading eyebrow="Daily leadership" title="Sector heatmap" note="Select sector ETFs" icon={BarChart3} />
              <div className="usi-sector-heatmap">
                {(market.sectors || []).map((row) => {
                  const change = num(row.change_pct) || 0;
                  return <article key={row.symbol} className={change >= 0 ? 'is-up' : 'is-down'} style={{ '--heat': Math.min(Math.abs(change) / 3 + 0.12, 0.8) }}><span>{row.symbol}</span><strong>{row.name}</strong><b>{change >= 0 ? '+' : ''}{change.toFixed(2)}%</b></article>;
                })}
              </div>
            </section>

            <section className="usi-two-column usi-leaderboards">
              {['day_gainers', 'day_losers'].map((key) => (
                <div className="usi-panel" key={key}>
                  <SectionHeading eyebrow="Broad US market" title={SCREENER_LABELS[key]} note="Yahoo daily screen" icon={key === 'day_gainers' ? ArrowUpRight : ArrowDownRight} />
                  <div className="usi-mini-table">
                    {(market.screeners?.[key] || []).slice(0, 8).map((row) => <button key={row.symbol} onClick={() => openStock(row.symbol)}><span><b>{row.symbol}</b><small>{row.name}</small></span><strong>{money(row.price, row.currency || 'USD')}</strong><Change value={row.change_pct} /></button>)}
                  </div>
                </div>
              ))}
            </section>
          </div>
        ) : null}

        {desk === 'screeners' && marketLoading ? <LoadingState /> : null}
        {desk === 'screeners' && !marketLoading && marketError ? (
          <div className="usi-error"><AlertTriangle /><div><strong>Screeners unavailable</strong><p>{marketError}</p></div></div>
        ) : null}
        {desk === 'screeners' && !marketLoading && !marketError && market ? (
          <div className="usi-screener-desk">
            <div className="usi-screener-tabs">
              {Object.entries(SCREENER_LABELS).map(([key, label]) => <button key={key} className={screener === key ? 'is-active' : ''} onClick={() => setScreener(key)}>{label}</button>)}
            </div>
            <section className="usi-panel">
              <SectionHeading eyebrow="Yahoo canonical screen" title={SCREENER_LABELS[screener]} note={`${(market.screeners?.[screener] || []).length} results`} icon={Search} />
              <div className="usi-screener-table-wrap">
                <table className="usi-screener-table">
                  <thead><tr><th>Company</th><th>Price</th><th>Day</th><th>Market cap</th><th>Volume ratio</th><th>P/E</th><th>Dividend</th><th>12M</th></tr></thead>
                  <tbody>
                    {(market.screeners?.[screener] || []).map((row) => (
                      <tr key={row.symbol} onClick={() => openStock(row.symbol)}>
                        <td><b>{row.symbol}</b><span>{row.name}</span></td><td>{money(row.price, row.currency || 'USD')}</td><td><Change value={row.change_pct} /></td><td>{money(row.market_cap, row.currency || 'USD', true)}</td><td>{decimal(row.volume_ratio, 'x')}</td><td>{decimal(row.trailing_pe, 'x')}</td><td>{decimal(row.dividend_yield_pct, '%')}</td><td><Change value={row.fifty_two_week_change_pct} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="usi-screener-note">Gainers, losers and most active cover Yahoo's broad US market screens. Value, momentum and dividend screens use AGI's liquid cross-sector bellwether universe.</p>
            </section>
          </div>
        ) : null}

        {desk === 'stock' && loading ? <LoadingState /> : null}
        {desk === 'stock' && !loading && error ? (
          <div className="usi-error">
            <AlertTriangle />
            <div><strong>Intelligence package unavailable</strong><p>{error}</p></div>
            <button onClick={() => setRequestKey((current) => current + 1)}><RefreshCw size={16} /> Retry</button>
          </div>
        ) : null}

        {desk === 'stock' && !loading && !error && data ? (
          <div className="usi-report">
            <section className="usi-tape">
              <div className="usi-company">
                <span>{data.symbol}</span>
                <h2>{profile.name || data.symbol}</h2>
                <p>{[profile.exchange, profile.sector, profile.industry].filter(Boolean).join(' / ') || 'US listed equity'}</p>
              </div>
              <div className="usi-price">
                <small>Last recorded price</small>
                <strong>{money(quote.last, currency)}</strong>
                <Change value={quote.change_percent} />
                <span>{quote.session_date ? `Session ${dateLabel(quote.session_date)}` : 'Yahoo market timestamp'}</span>
              </div>
              <div className="usi-quality-ring" style={{ '--score': `${data.quality?.coverage_score || 0}%` }}>
                <div><strong>{data.quality?.grade || '--'}</strong><span>{data.quality?.coverage_score || 0}% coverage</span></div>
              </div>
            </section>

            <section className="usi-metrics-row">
              <Metric label="Market cap" value={money(valuation.market_cap, currency, true)} />
              <Metric label="Trailing P/E" value={decimal(valuation.trailing_pe, 'x')} />
              <Metric label="Forward P/E" value={decimal(valuation.forward_pe, 'x')} />
              <Metric label="Revenue growth" value={decimal(financials.revenue_growth_pct, '%')} />
              <Metric label="Net margin" value={decimal(financials.net_margin_pct, '%')} />
              <Metric label="Realized volatility" value={decimal(technicals.annualized_volatility_pct, '%')} />
            </section>

            <section className="usi-two-column">
              <div className="usi-panel usi-chart-panel">
                <SectionHeading eyebrow="Market behavior" title="Price regime" note={`${data.quality?.price_sessions || 0} sessions`} icon={BarChart3} />
                <div className="usi-range-tabs">
                  {['1M', '3M', '6M', '1Y'].map((item) => <button key={item} className={range === item ? 'is-active' : ''} onClick={() => setRange(item)}>{item}</button>)}
                </div>
                <div className="usi-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 15, right: 5, left: -18, bottom: 0 }}>
                      <defs>
                        <linearGradient id="usiPriceFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#42d3b1" stopOpacity={0.35} />
                          <stop offset="100%" stopColor="#42d3b1" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="#20313d" strokeDasharray="3 5" vertical={false} />
                      <XAxis dataKey="date" tickFormatter={(v) => dateLabel(v).replace(/, \d{4}/, '')} minTickGap={45} tick={{ fill: '#718391', fontSize: 10 }} axisLine={false} tickLine={false} />
                      <YAxis domain={['auto', 'auto']} tick={{ fill: '#718391', fontSize: 10 }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={{ background: '#0c1820', border: '1px solid #29404d', color: '#e8f2f5' }} labelFormatter={dateLabel} formatter={(v) => [money(v, currency), 'Close']} />
                      <Area type="monotone" dataKey="close" stroke="#42d3b1" strokeWidth={2.2} fill="url(#usiPriceFill)" />
                      <Line type="monotone" dataKey="close" stroke="#c7ffef" strokeWidth={0.5} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <div className="usi-chart-stats">
                  <div><span>1 month</span><Change value={technicals.return_1m_pct} /></div>
                  <div><span>3 months</span><Change value={technicals.return_3m_pct} /></div>
                  <div><span>1 year</span><Change value={technicals.return_1y_pct} /></div>
                  <div><span>Max drawdown</span><Change value={technicals.max_drawdown_pct} /></div>
                </div>
              </div>

              <div className="usi-panel usi-thesis-panel">
                <SectionHeading eyebrow="AGI derived view" title="Signal matrix" note="Research, not a rating" icon={Sparkles} />
                <div className="usi-signal-list">
                  <div><span>Price trend</span><strong className={`is-${technicals.trend || 'mixed'}`}>{technicals.trend || '--'}</strong><small>Price vs. 50D and 200D averages</small></div>
                  <div><span>Growth pulse</span><strong>{num(financials.revenue_growth_pct) === null ? '--' : num(financials.revenue_growth_pct) >= 0 ? 'expanding' : 'contracting'}</strong><small>Latest annual revenue direction</small></div>
                  <div><span>Valuation context</span><strong>{num(valuation.trailing_pe) === null ? '--' : num(valuation.trailing_pe) > 35 ? 'premium' : num(valuation.trailing_pe) < 18 ? 'low multiple' : 'mid-range'}</strong><small>Mechanical trailing P/E screen</small></div>
                  <div><span>Street stance</span><strong>{analyst.recommendation || 'not available'}</strong><small>{analyst.analyst_count ? `${analyst.analyst_count} reported analyst opinions` : 'Coverage not established'}</small></div>
                </div>
                <div className="usi-target-band">
                  <span>Reported analyst target range</span>
                  <div><b>{money(analyst.target_low_price, currency)}</b><i /><b>{money(analyst.target_mean_price, currency)}</b><i /><b>{money(analyst.target_high_price, currency)}</b></div>
                  <small>Low / mean / high. Third-party consensus, not AGI fair value.</small>
                </div>
              </div>
            </section>

            <section className="usi-panel">
              <SectionHeading eyebrow="Financial evidence" title="Business trajectory" note={`${data.quality?.annual_periods || 0} annual periods`} icon={Activity} />
              <div className="usi-financial-grid">
                <div className="usi-financial-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={[...(financials.annual || [])].reverse()} margin={{ top: 15, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid stroke="#20313d" strokeDasharray="3 5" vertical={false} />
                      <XAxis dataKey="period" tick={{ fill: '#718391', fontSize: 10 }} axisLine={false} tickLine={false} />
                      <YAxis tickFormatter={compact} tick={{ fill: '#718391', fontSize: 10 }} axisLine={false} tickLine={false} width={55} />
                      <Tooltip contentStyle={{ background: '#0c1820', border: '1px solid #29404d', color: '#e8f2f5' }} formatter={(v, name) => [compact(v), name === 'revenue' ? 'Revenue' : 'Net income']} />
                      <Area type="monotone" dataKey="revenue" stroke="#47a9ff" fill="#47a9ff18" strokeWidth={2} />
                      <Area type="monotone" dataKey="net_income" stroke="#f0b35a" fill="#f0b35a12" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <div className="usi-financial-table-wrap">
                  <table className="usi-financial-table">
                    <thead><tr><th>Period</th><th>Revenue</th><th>Net income</th><th>FCF</th><th>EPS</th></tr></thead>
                    <tbody>
                      {(financials.annual || []).slice(0, 5).map((row) => (
                        <tr key={row.period || JSON.stringify(row)}>
                          <td>{row.period || '--'}</td><td>{compact(row.revenue)}</td><td>{compact(row.net_income)}</td><td>{compact(row.free_cash_flow)}</td><td>{decimal(row.eps, '', 2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!(financials.annual || []).length ? <p className="usi-empty">Yahoo financial history was not available for this ticker.</p> : null}
                </div>
              </div>
            </section>

            <section className="usi-three-column">
              <div className="usi-panel">
                <SectionHeading eyebrow="Valuation" title="Multiple board" icon={BarChart3} />
                <div className="usi-data-list">
                  <div><span>Price / book</span><strong>{decimal(valuation.price_to_book, 'x')}</strong></div>
                  <div><span>Price / sales</span><strong>{decimal(valuation.price_to_sales, 'x')}</strong></div>
                  <div><span>EV / EBITDA</span><strong>{decimal(valuation.enterprise_to_ebitda, 'x')}</strong></div>
                  <div><span>PEG ratio</span><strong>{decimal(valuation.peg_ratio, 'x')}</strong></div>
                  <div><span>Dividend yield</span><strong>{num(valuation.dividend_yield) === null ? '--' : decimal(num(valuation.dividend_yield) < 1 ? num(valuation.dividend_yield) * 100 : valuation.dividend_yield, '%')}</strong></div>
                  <div><span>Beta</span><strong>{decimal(valuation.beta, '', 2)}</strong></div>
                </div>
              </div>

              <div className="usi-panel">
                <SectionHeading eyebrow="Risk monitor" title="What needs attention" icon={AlertTriangle} />
                <div className="usi-risk-list">
                  {(data.risk_flags || []).map((flag) => (
                    <div key={`${flag.label}-${flag.detail}`} className={`is-${flag.level}`}>
                      <span /><p><strong>{flag.label}</strong><small>{flag.detail}</small></p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="usi-panel">
                <SectionHeading eyebrow="Event radar" title="Catalysts and actions" icon={CalendarClock} />
                <div className="usi-event-list">
                  {(data.events || []).slice(0, 4).map((event) => (
                    <div key={event.event_id || `${event.title}-${event.event_time}`}><span>{dateLabel(event.event_time)}</span><strong>{event.title || event.event_type}</strong></div>
                  ))}
                  {(data.corporate_actions || []).slice(0, 3).map((action, index) => (
                    <div key={`${action.action_type}-${action.ex_date}-${index}`}><span>{dateLabel(action.ex_date)}</span><strong>{action.action_type}{action.amount ? ` ${money(action.amount, action.currency || currency)}` : ''}</strong></div>
                  ))}
                  {!(data.events || []).length && !(data.corporate_actions || []).length ? <p className="usi-empty">No current event record returned.</p> : null}
                </div>
              </div>
            </section>

            <section className="usi-integrity">
              <div><ShieldCheck size={22} /><p><strong>Evidence and source integrity</strong><span>Provider-native data is normalized into AGI canonical fields before display.</span></p></div>
              <div className="usi-integrity-facts">
                <span>Source <b>Yahoo Finance</b></span>
                <span>Cache <b>{data.cache_hit ? 'reused' : 'fresh pull'}</b></span>
                <span>Coverage <b>{data.quality?.coverage_score || 0}%</b></span>
                <span>As of <b>{dateLabel(data.as_of)}</b></span>
              </div>
              {Object.keys(data.quality?.errors || {}).length ? (
                <p className="usi-partial-warning">Partial package: {Object.keys(data.quality.errors).join(', ')} unavailable.</p>
              ) : null}
            </section>
          </div>
        ) : null}

        <footer className="usi-disclaimer">
          Yahoo Finance data may be delayed, incomplete or revised. AGI calculations are for research discussion only and are not investment advice, a recommendation, or an offer to transact.
        </footer>
      </section>
    </main>
  );
}
