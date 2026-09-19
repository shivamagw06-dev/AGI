import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import {
  Activity,
  ArrowRight,
  BarChart3,
  BrainCircuit,
  Building2,
  ChevronRight,
  Compass,
  Gauge,
  Layers3,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
} from 'lucide-react';
import useMarketIntelligence from '@/hooks/useMarketIntelligence';
import { searchNifty500Research } from '@/lib/nifty500ResearchApi';

const SENTIMENT_ORDER = {
  'strongly bullish': 6,
  bullish: 5,
  'mildly bullish': 4,
  neutral: 3,
  'mildly bearish': 2,
  bearish: 1,
  'strongly bearish': 0,
};

function sentimentClass(value = '') {
  const text = String(value).toLowerCase();
  if (text.includes('bullish') || text.includes('positive') || text.includes('leading') || text.includes('strong')) {
    return 'border-[#9fc9ad] bg-[#eaf5ee] text-[#17633a]';
  }
  if (text.includes('bearish') || text.includes('negative') || text.includes('pressure') || text.includes('weak')) {
    return 'border-[#e2aea4] bg-[#fff0ec] text-[#a13a2b]';
  }
  return 'border-[#d7c39c] bg-[#fff7e7] text-[#805d1f]';
}

function Signal({ children }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${sentimentClass(children)}`}>
      {children || 'Neutral'}
    </span>
  );
}

function Metric({ label, value, note, icon: Icon }) {
  return (
    <article className="border-l border-white/15 px-5 first:border-l-0">
      <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[#91a8b7]">
        {Icon ? <Icon className="h-3.5 w-3.5 text-[#d2a865]" aria-hidden /> : null}
        {label}
      </div>
      <p className="mt-3 font-serif text-2xl font-bold text-white">{value || '-'}</p>
      {note ? <p className="mt-1 text-[11px] text-[#91a8b7]">{note}</p> : null}
    </article>
  );
}

export default function IndiaStockIntelligencePage() {
  const navigate = useNavigate();
  const {
    pulse,
    outlook,
    sectors = [],
    stocksInFocus = [],
    breadth,
    indexSentiments = [],
    updatedAt,
    loading,
  } = useMarketIntelligence();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState('');

  useEffect(() => {
    const cleaned = query.trim();
    if (!cleaned) {
      setResults([]);
      setSearchError('');
      return undefined;
    }

    let active = true;
    const timer = window.setTimeout(() => {
      setSearching(true);
      setSearchError('');
      searchNifty500Research(cleaned)
        .then((data) => {
          if (active) setResults((data?.items || []).slice(0, 8));
        })
        .catch(() => {
          if (active) {
            setResults([]);
            setSearchError('Stock search is temporarily unavailable.');
          }
        })
        .finally(() => active && setSearching(false));
    }, 250);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [query]);

  const orderedIndices = useMemo(
    () => [...indexSentiments].sort((a, b) => {
      const aRank = SENTIMENT_ORDER[String(a.sentiment || '').toLowerCase()] ?? 3;
      const bRank = SENTIMENT_ORDER[String(b.sentiment || '').toLowerCase()] ?? 3;
      return bRank - aRank;
    }),
    [indexSentiments]
  );

  const leadingSectors = useMemo(
    () => sectors.filter((sector) => sector.direction === '↑').slice(0, 5),
    [sectors]
  );
  const pressuredSectors = useMemo(
    () => sectors.filter((sector) => sector.direction !== '↑').slice(0, 5),
    [sectors]
  );

  const openStock = (symbol) => {
    const cleaned = String(symbol || '').trim().toUpperCase();
    if (cleaned) navigate(`/research/stocks/${encodeURIComponent(cleaned)}`);
  };

  const submitSearch = (event) => {
    event.preventDefault();
    openStock(results[0]?.symbol || query);
  };

  return (
    <div className="min-h-screen bg-[#f3f0e8] text-[#102433]">
      <Helmet>
        <title>India Stock Intelligence | Agarwal Global Investments</title>
        <meta
          name="description"
          content="Search Indian stocks and explore AGI market regime, breadth, sector leadership, technical signals, risks and company intelligence."
        />
      </Helmet>

      <section className="relative overflow-hidden bg-[#092536] text-white">
        <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(255,255,255,.06)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.06)_1px,transparent_1px)] [background-size:42px_42px]" />
        <div className="absolute -right-32 -top-32 h-[520px] w-[520px] rounded-full bg-[#b98047]/15 blur-3xl" />
        <div className="relative mx-auto max-w-[1500px] px-4 pb-9 pt-12 sm:px-6 md:pb-12 md:pt-16 lg:px-8">
          <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.22em] text-[#ddb77e]">
            <Sparkles className="h-4 w-4" aria-hidden /> AGI India intelligence desk
          </div>
          <div className="mt-5 grid gap-8 lg:grid-cols-[1fr_430px] lg:items-end">
            <div>
              <h1 className="max-w-4xl font-serif text-4xl font-bold leading-[0.98] tracking-[-0.035em] sm:text-5xl md:text-6xl">
                India Stock Intelligence
              </h1>
              <p className="mt-5 max-w-2xl text-sm leading-7 text-[#bfd0da] md:text-base">
                Find a listed company, understand the market regime around it, and move from signal to evidence in one research workflow.
              </p>
            </div>
            <div className="flex items-center gap-3 border-l border-white/20 pl-4 text-xs leading-5 text-[#9fb3bf]">
              <ShieldCheck className="h-8 w-8 shrink-0 text-[#d2a865]" aria-hidden />
              Informational intelligence only. AGI uses Bullish, Neutral and Bearish research views, not buy or sell calls.
            </div>
          </div>

          <div className="relative mt-9 max-w-4xl">
            <form onSubmit={submitSearch} className="flex overflow-hidden rounded-xl bg-white shadow-[0_18px_55px_rgba(0,0,0,.25)]">
              <Search className="ml-5 mt-5 h-5 w-5 shrink-0 text-[#6b7780]" aria-hidden />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search NSE symbol or company, for example RELIANCE"
                aria-label="Search India stock intelligence"
                className="min-w-0 flex-1 bg-white px-4 py-5 text-sm font-medium text-[#102433] outline-none placeholder:text-[#8a949b]"
              />
              <button type="submit" className="m-2 inline-flex items-center gap-2 rounded-lg bg-[#b5783e] px-5 text-sm font-bold text-white transition hover:bg-[#985f2d]">
                Open intelligence <ArrowRight className="h-4 w-4" aria-hidden />
              </button>
            </form>
            {query.trim() ? (
              <div className="absolute inset-x-0 top-[76px] z-40 overflow-hidden rounded-xl border border-[#d9ddd9] bg-white text-[#102433] shadow-2xl">
                {searching ? <p className="p-4 text-sm text-[#68747c]">Searching published intelligence...</p> : null}
                {!searching && searchError ? <p className="p-4 text-sm text-[#a13a2b]">{searchError}</p> : null}
                {!searching && !searchError && results.length === 0 ? <p className="p-4 text-sm text-[#68747c]">No published research matches yet.</p> : null}
                {!searching && results.map((item) => (
                  <button
                    key={item.symbol}
                    type="button"
                    onClick={() => openStock(item.symbol)}
                    className="flex w-full items-center justify-between border-t border-[#edf0ed] px-4 py-3 text-left first:border-t-0 hover:bg-[#f6f4ee]"
                  >
                    <span>
                      <span className="block text-sm font-bold">{item.symbol}</span>
                      <span className="mt-0.5 block text-[11px] text-[#768089]">AGI score {item.agiResearchScore ?? '-'} / 100 - confidence {item.aiConfidencePercent ?? '-'}%</span>
                    </span>
                    <Signal>{item.overallSentiment}</Signal>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        </div>

        <div className="relative border-t border-white/10 bg-[#071d2b]/75">
          <div className="mx-auto grid max-w-[1500px] grid-cols-2 gap-y-6 px-4 py-6 sm:px-6 md:grid-cols-3 lg:grid-cols-6 lg:px-8">
            <Metric icon={Gauge} label="AGI market score" value={pulse?.agiMarketScore != null ? `${pulse.agiMarketScore}/100` : '-'} note="Derived model" />
            <Metric icon={Compass} label="Market stance" value={pulse?.outlook || outlook?.outlook} />
            <Metric icon={Activity} label="Breadth" value={breadth?.label || pulse?.marketBreadth} />
            <Metric icon={BrainCircuit} label="Confidence" value={pulse?.confidence ? `${pulse.confidence}%` : '-'} />
            <Metric icon={BarChart3} label="Volatility" value={pulse?.volatility} />
            <Metric icon={ShieldCheck} label="Risk level" value={pulse?.risk} />
          </div>
        </div>
      </section>

      <main className="mx-auto max-w-[1500px] px-4 py-10 sm:px-6 md:py-14 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-[#cec9bd] pb-5">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#8a6338]">Daily decision surface</p>
            <h2 className="mt-2 font-serif text-3xl font-bold">What deserves attention now</h2>
          </div>
          <p className="text-xs text-[#707981]">
            {updatedAt ? `Model updated ${new Date(updatedAt).toLocaleString('en-IN')}` : loading ? 'Loading latest model run...' : 'Awaiting model refresh'}
          </p>
        </div>

        <div className="mt-7 grid gap-6 xl:grid-cols-[1.45fr_.8fr]">
          <section className="overflow-hidden rounded-2xl border border-[#d8d5cc] bg-white">
            <div className="flex items-center justify-between border-b border-[#e4e1da] px-5 py-4 sm:px-6">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8a6338]">Model watchlist</p>
                <h3 className="mt-1 font-serif text-2xl font-bold">Stocks in focus</h3>
              </div>
              <Target className="h-5 w-5 text-[#b5783e]" aria-hidden />
            </div>
            <div className="divide-y divide-[#ece9e2]">
              {stocksInFocus.length ? stocksInFocus.slice(0, 8).map((stock, index) => (
                <Link
                  key={stock.symbol}
                  to={`/research/stocks/${stock.symbol}`}
                  className="grid gap-3 px-5 py-4 transition hover:bg-[#f8f6f1] sm:grid-cols-[40px_1fr_auto] sm:items-center sm:px-6"
                >
                  <span className="font-serif text-lg font-bold text-[#b6a994]">{String(index + 1).padStart(2, '0')}</span>
                  <span>
                    <span className="block text-sm font-bold">{stock.name || stock.symbol}</span>
                    <span className="mt-1 block text-[11px] text-[#727c84]">{stock.symbol} - {stock.momentum || 'Developing'} momentum - {stock.category || 'AGI watchlist'}</span>
                  </span>
                  <span className="flex items-center gap-3"><Signal>{stock.trend}</Signal><ChevronRight className="h-4 w-4 text-[#8b949b]" /></span>
                </Link>
              )) : (
                <p className="px-6 py-12 text-center text-sm text-[#727c84]">Watchlist signals will appear after the next successful model refresh.</p>
              )}
            </div>
          </section>

          <section className="rounded-2xl bg-[#123f4c] p-6 text-white sm:p-7">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#d8b277]">Research workflow</p>
            <h3 className="mt-3 font-serif text-3xl font-bold leading-tight">From ticker to thesis</h3>
            <p className="mt-3 text-sm leading-6 text-[#bed0d4]">Each company record connects multiple intelligence layers instead of presenting a single opaque score.</p>
            <div className="mt-7 space-y-5">
              {[
                ['01', 'Market structure', 'Trend, momentum, volume, volatility and relative strength.'],
                ['02', 'Fundamental trust', 'Management quality, accounting behaviour and evidence quality.'],
                ['03', 'Forward path', 'Catalysts, risks, scenarios, forecast confidence and portfolio fit.'],
              ].map(([number, title, description]) => (
                <div key={number} className="grid grid-cols-[38px_1fr] gap-3 border-t border-white/15 pt-4">
                  <span className="font-serif text-xl font-bold text-[#d8b277]">{number}</span>
                  <span><strong className="block text-sm">{title}</strong><span className="mt-1 block text-xs leading-5 text-[#a9c0c5]">{description}</span></span>
                </div>
              ))}
            </div>
            <Link to="/market-intelligence" className="mt-8 inline-flex items-center gap-2 text-sm font-bold text-[#f0cf9b] hover:text-white">
              Open India market overview <ArrowRight className="h-4 w-4" />
            </Link>
          </section>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <section className="rounded-2xl border border-[#d8d5cc] bg-white p-5 sm:p-6">
            <div className="flex items-center gap-3"><Layers3 className="h-5 w-5 text-[#b5783e]" /><h3 className="font-serif text-2xl font-bold">Sector rotation</h3></div>
            <div className="mt-6 grid gap-5 sm:grid-cols-2">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#367451]">Leadership</p>
                <div className="mt-3 space-y-2">
                  {leadingSectors.length ? leadingSectors.map((sector) => <div key={sector.name} className="flex items-center justify-between border-b border-[#ece9e2] py-2.5 text-sm"><span className="font-semibold">{sector.name}</span><Signal>{sector.strength || 'Leading'}</Signal></div>) : <p className="text-sm text-[#727c84]">No leadership signal available.</p>}
                </div>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#a14a39]">Under pressure</p>
                <div className="mt-3 space-y-2">
                  {pressuredSectors.length ? pressuredSectors.map((sector) => <div key={sector.name} className="flex items-center justify-between border-b border-[#ece9e2] py-2.5 text-sm"><span className="font-semibold">{sector.name}</span><Signal>{sector.strength || 'Weak'}</Signal></div>) : <p className="text-sm text-[#727c84]">No pressure signal available.</p>}
                </div>
              </div>
            </div>
            <Link to="/market-sector-intelligence" className="mt-6 inline-flex items-center gap-2 text-xs font-bold text-[#245b70] hover:underline">Explore sector intelligence <ArrowRight className="h-3.5 w-3.5" /></Link>
          </section>

          <section className="rounded-2xl border border-[#d8d5cc] bg-white p-5 sm:p-6">
            <div className="flex items-center gap-3"><TrendingUp className="h-5 w-5 text-[#b5783e]" /><h3 className="font-serif text-2xl font-bold">Index pulse</h3></div>
            <div className="mt-5 divide-y divide-[#ece9e2]">
              {orderedIndices.length ? orderedIndices.slice(0, 6).map((index) => (
                <div key={index.key || index.label} className="flex items-center justify-between gap-4 py-3.5">
                  <span><strong className="block text-sm">{index.label}</strong><span className="mt-1 block text-[11px] text-[#727c84]">{index.strength || 'Trend and momentum model'}</span></span>
                  <Signal>{index.sentiment}</Signal>
                </div>
              )) : <p className="py-10 text-center text-sm text-[#727c84]">Index signals are awaiting the next model refresh.</p>}
            </div>
          </section>
        </div>

        <section className="mt-6 grid gap-4 rounded-2xl border border-[#d8d5cc] bg-[#e9e4d9] p-5 sm:grid-cols-3 sm:p-6">
          {[
            [Building2, 'Company intelligence', 'A consolidated company view with technical, fundamental and institutional context.'],
            [BrainCircuit, 'Explainable scoring', 'Scores remain paired with confidence, supporting factors, risks and model timestamps.'],
            [ShieldCheck, 'Editorial guardrails', 'Research views use Bullish, Neutral or Bearish and remain informational, not personalised advice.'],
          ].map(([Icon, title, body]) => (
            <article key={title} className="rounded-xl bg-white/70 p-5">
              <Icon className="h-5 w-5 text-[#9b652f]" aria-hidden />
              <h3 className="mt-4 font-serif text-lg font-bold">{title}</h3>
              <p className="mt-2 text-xs leading-5 text-[#667078]">{body}</p>
            </article>
          ))}
        </section>

        <section className="mt-8 border-t border-[#cec9bd] pt-6 text-xs leading-6 text-[#687178]">
          India Stock Intelligence is an analytical research surface for informational purposes. It is not personalised investment advice, an offer, or a recommendation to buy or sell any security. Market and model conditions can change after the displayed update time.
        </section>
      </main>
    </div>
  );
}
