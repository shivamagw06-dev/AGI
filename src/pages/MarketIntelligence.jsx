import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BrainCircuit,
  Clock3,
  LineChart,
  Scale,
  ShieldAlert,
  TrendingUp,
} from 'lucide-react';
import useMarketIntelligence from '@/hooks/useMarketIntelligence';
import Nifty500ResearchPanel from '@/components/Research/Nifty500ResearchPanel';
import InstitutionalIntelligenceLayer from '@/components/Research/InstitutionalIntelligenceLayer';
import DeskResearchFeed from '@/components/Research/DeskResearchFeed';
import MarketActivitiesRail from '@/components/Research/MarketActivitiesRail';
import { getMarketBriefing } from '@/api/marketApi';
import { getUiDashboard } from '@/lib/uiApi';

function tone(value = '') {
  const text = String(value).toLowerCase();
  if (text.includes('bearish') || text.includes('negative') || text.includes('weak')) {
    return 'bg-[#fff1f0] text-[#b42318] border-[#f7c5c0]';
  }
  if (text.includes('bullish') || text.includes('positive') || text.includes('leading') || text.includes('strong')) {
    return 'bg-[#ecfdf3] text-[#087443] border-[#b7ebcc]';
  }
  return 'bg-[#fff8e8] text-[#966a00] border-[#f4d99d]';
}

function SignalPill({ children }) {
  return <span className={`inline-flex w-fit border px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${tone(children)}`}>{children}</span>;
}

function MetricCard({ label, value, detail }) {
  return (
    <div className="min-w-0 border border-[#dde1e6] bg-white p-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#737982]">{label}</p>
      <p className="mt-2 break-words text-xl font-bold text-[#18202b]">{value || '—'}</p>
      {detail && <p className="mt-1 text-[11px] text-[#737982]">{detail}</p>}
    </div>
  );
}

export default function MarketIntelligence() {
  const {
    pulse,
    outlook,
    sectors = [],
    stocksInFocus = [],
    breadth,
    indexSentiments = [],
    disclaimer,
    loading,
    updatedAt,
  } = useMarketIntelligence();
  const [briefingState, setBriefingState] = useState({ loading: true, data: null });
  const [uiDash, setUiDash] = useState(null);

  useEffect(() => {
    let active = true;
    const loadBriefing = async () => {
      try {
        const data = await getMarketBriefing();
        if (active && data) setBriefingState({ loading: false, data });
        else if (active) setBriefingState((previous) => ({ ...previous, loading: false }));
      } catch {
        if (active) setBriefingState((previous) => ({ ...previous, loading: false }));
      }
    };
    // Briefing first — page shell must not wait on the heavier UI dashboard.
    loadBriefing();
    // Enrichment only; 12s client timeout + Node 12s proxy. Failures stay silent.
    const dashTimer = window.setTimeout(() => {
      getUiDashboard()
        .then((data) => active && setUiDash(data))
        .catch(() => active && setUiDash(null));
    }, 0);
    const interval = window.setInterval(loadBriefing, 60_000);
    return () => {
      active = false;
      window.clearTimeout(dashTimer);
      window.clearInterval(interval);
    };
  }, []);

  const orderedIndices = [...indexSentiments].sort((a, b) => {
    const ordering = { 'Strongly Bullish': 5, Bullish: 4, 'Mildly Bullish': 3, Neutral: 2, 'Mildly Bearish': 1, Bearish: 0, 'Strongly Bearish': -1 };
    return (ordering[b.sentiment] ?? 2) - (ordering[a.sentiment] ?? 2);
  });

  return (
    <>
      <Helmet>
        <title>Market Intelligence | Agarwal Global Investments</title>
        <meta name="description" content="AGI derived market intelligence, sector leadership and research context for Indian markets." />
      </Helmet>

      <div className="market-intelligence-page min-h-screen bg-[#f8fafb]">
        <section className="border-b border-[#dde1e6] bg-[#0d1d33] text-white">
          <div className="max-w-[1800px] mx-auto px-4 sm:px-6 py-8 sm:py-10 lg:py-14">
            <div className="flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase tracking-[0.12em] text-[#a7c5ec]">
              <Activity className="h-4 w-4" /> AGI research platform
            </div>
            <div className="mt-4 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h1 className="text-3xl font-bold tracking-tight md:text-5xl">Market Intelligence</h1>
                <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#d2dceb] md:text-base">
                  Mint-style Pre-Market, 12 PM and Market Close notes — Bullish, Bearish or Neutral, with clear reasoning.
                </p>
              </div>
              <div className="flex flex-col items-stretch gap-3 sm:items-end">
                <Link
                  to="/valuation-intelligence"
                  className="inline-flex items-center justify-center gap-2 border border-[#7ea2cf] bg-white px-4 py-2.5 text-sm font-bold text-[#0d1d33] transition hover:bg-[#e8f0fa]"
                >
                  <LineChart className="h-4 w-4" />
                  Broker Estimates
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  to="/market-sector-intelligence"
                  className="inline-flex items-center justify-center gap-2 border border-[#7ea2cf] bg-white px-4 py-2.5 text-sm font-bold text-[#0d1d33] transition hover:bg-[#e8f0fa]"
                >
                  <TrendingUp className="h-4 w-4" />
                  Sector Intelligence
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  to="/valuation-terminal"
                  className="inline-flex items-center justify-center gap-2 border border-[#7ea2cf] bg-white px-4 py-2.5 text-sm font-bold text-[#0d1d33] transition hover:bg-[#e8f0fa]"
                >
                  <Scale className="h-4 w-4" />
                  Valuation Table
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <div className="flex items-start gap-2 text-xs leading-relaxed text-[#c6d4e7]">
                  <Clock3 className="h-4 w-4 shrink-0" />
                  {updatedAt ? `Updated ${new Date(updatedAt).toLocaleString('en-IN')}` : 'Awaiting model refresh'}
                </div>
              </div>
            </div>
          </div>
        </section>

        <main className="max-w-[1800px] mx-auto px-4 sm:px-6 py-6 sm:py-8 lg:py-10">
          <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
            <div className="rounded-xl border border-[#dde1e6] bg-white p-5 sm:p-6 lg:col-span-8">
              <DeskResearchFeed
                deskId="indian-market"
                title="Indian Market Research"
                gridClassName="grid-cols-1 gap-4 sm:grid-cols-2"
              />
            </div>
            <MarketActivitiesRail className="lg:col-span-4 lg:sticky lg:top-24" />
          </div>

          <Nifty500ResearchPanel />

          {uiDash && (
            <section className="mb-6 border border-[#dde1e6] bg-white p-4" aria-label="Investment office desk">
              <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">Investment Office Desk</p>
              <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
                <MetricCard label="Market brief" value={uiDash.market_brief?.regime || uiDash.market_regime?.label} detail={uiDash.market_brief?.summary} />
                <MetricCard label="Market regime" value={uiDash.market_regime?.label} />
                <MetricCard label="Market risk" value={uiDash.market_risk?.label} />
                <MetricCard
                  label="Research queue"
                  value={(uiDash.research_queue || []).length}
                  detail={`${(uiDash.latest_reports || []).length} latest reports`}
                />
              </div>
            </section>
          )}

          <section aria-label="Market overview">
            <div className="mb-4 flex items-center gap-2">
              <BrainCircuit className="h-5 w-5 text-[#274c77]" />
              <h2 className="text-lg font-bold text-[#18202b]">AGI Market Overview</h2>
              <span className="text-[10px] font-semibold uppercase tracking-wide text-[#737982]">Model metrics</span>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
              <MetricCard label="Market intelligence score" value={pulse?.agiMarketScore != null ? `${pulse.agiMarketScore}/100` : '—'} detail="Derived model score" />
              <MetricCard label="Overall market mood" value={pulse?.outlook || outlook?.outlook} />
              <MetricCard label="AI confidence" value={pulse?.confidence ? `${pulse.confidence}%` : '—'} />
              <MetricCard label="Market breadth" value={breadth?.label || pulse?.marketBreadth} />
              <MetricCard label="Volatility" value={pulse?.volatility} />
              <MetricCard label="Risk level" value={pulse?.risk} />
            </div>
          </section>

          <InstitutionalIntelligenceLayer briefing={briefingState.data} loading={briefingState.loading} />

          <div className="mt-8 grid grid-cols-1 gap-8 xl:grid-cols-12">
            <section className="xl:col-span-8">
              <div className="mb-4 flex items-end justify-between border-b border-[#dde1e6] pb-3">
                <div>
                  <h2 className="text-lg font-bold text-[#18202b]">Index Intelligence</h2>
                  <p className="mt-1 text-xs text-[#737982]">Ranked by AGI-derived trend and momentum conditions. No exchange quotes displayed.</p>
                </div>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {orderedIndices.length ? orderedIndices.map((index) => (
                  <article key={index.key} className="border border-[#dde1e6] bg-white p-4">
                    <div className="flex flex-col items-start justify-between gap-3 sm:flex-row">
                      <div>
                        <h3 className="font-bold text-[#18202b]">{index.label}</h3>
                        <p className="mt-1 text-[11px] text-[#737982]">Technical strength · Momentum · Trend model</p>
                      </div>
                      <SignalPill>{index.sentiment}</SignalPill>
                    </div>
                    <p className="mt-4 text-xs font-medium text-[#4b5563]">{index.strength}</p>
                  </article>
                )) : (
                  <div className="border border-dashed border-[#cbd2da] bg-white p-6 text-sm text-[#737982]">
                    Index signals will appear after the next successful model refresh.
                  </div>
                )}
              </div>
            </section>

            <section className="xl:col-span-4">
              <div className="border border-[#dde1e6] bg-white">
                <div className="border-b border-[#dde1e6] p-4">
                  <h2 className="font-bold text-[#18202b]">Market Breadth</h2>
                  <p className="mt-1 text-xs text-[#737982]">Participation signal from available market inputs</p>
                </div>
                <div className="divide-y divide-[#edf0f2] p-4">
                  <div className="flex items-center justify-between py-2 text-sm"><span className="text-[#737982]">Breadth condition</span><SignalPill>{breadth?.label || 'Neutral'}</SignalPill></div>
                  <div className="flex items-center justify-between py-2 text-sm"><span className="text-[#737982]">Advancing signals</span><span className="font-bold text-[#18202b]">{breadth?.advancing ?? '—'}</span></div>
                  <div className="flex items-center justify-between py-2 text-sm"><span className="text-[#737982]">Declining signals</span><span className="font-bold text-[#18202b]">{breadth?.declining ?? '—'}</span></div>
                  <div className="flex items-center justify-between py-2 text-sm"><span className="text-[#737982]">Participation ratio</span><span className="font-bold text-[#18202b]">{breadth?.ratio?.toFixed?.(2) ?? '—'}</span></div>
                </div>
              </div>

              <div className="mt-4 border border-[#f2d7a0] bg-[#fffaf0] p-4">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-[#8a5b00]"><ShieldAlert className="h-4 w-4" /> Model limitations</div>
                <p className="mt-2 text-xs leading-relaxed text-[#6f5a2e]">Signals are descriptive technical analytics. They are not investment recommendations or calls to action.</p>
              </div>
            </section>
          </div>

          <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
            <section>
              <div className="mb-4 flex items-end justify-between border-b border-[#dde1e6] pb-3">
                <div>
                  <h2 className="text-lg font-bold text-[#18202b]">Sector Dashboard</h2>
                  <p className="mt-1 text-xs text-[#737982]">Leadership and relative trend conditions</p>
                </div>
              </div>
              <div className="border border-[#dde1e6] bg-white divide-y divide-[#edf0f2]">
                {sectors.slice(0, 8).map((sector) => (
                  <div key={sector.name} className="flex flex-col items-start justify-between gap-3 p-4 sm:flex-row sm:items-center">
                    <div className="flex items-center gap-3">
                      {sector.direction === '↑' ? <ArrowUpRight className="h-4 w-4 text-[#087443]" /> : <ArrowDownRight className="h-4 w-4 text-[#b42318]" />}
                      <span className="font-semibold text-[#18202b]">{sector.name}</span>
                    </div>
                    <SignalPill>{sector.direction === '↑' ? `Leading · ${sector.strength}` : `Under pressure · ${sector.strength}`}</SignalPill>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <div className="mb-4 flex items-end justify-between border-b border-[#dde1e6] pb-3">
                <div>
                  <h2 className="text-lg font-bold text-[#18202b]">Technical Strength Watchlist</h2>
                  <p className="mt-1 text-xs text-[#737982]">Companies selected by the AGI technical model—not recommendations</p>
                </div>
                <Link to="/research" className="text-xs font-bold text-[#274c77] hover:underline">Research →</Link>
              </div>
              <div className="border border-[#dde1e6] bg-white divide-y divide-[#edf0f2]">
                {stocksInFocus.slice(0, 8).map((stock) => (
                  <div key={stock.symbol} className="flex flex-col items-start justify-between gap-3 p-4 sm:flex-row sm:items-center">
                    <div>
                      <p className="font-semibold text-[#18202b]">{stock.name || stock.symbol}</p>
                      <p className="mt-1 text-[11px] text-[#737982]">{stock.momentum || 'Developing'} momentum · {stock.category || 'AGI watchlist'}</p>
                    </div>
                    <SignalPill>{stock.trend || 'Neutral'}</SignalPill>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <section className="mt-8 border border-[#dde1e6] bg-white p-5 text-xs leading-relaxed text-[#59616d]">
            <p className="font-bold uppercase tracking-wide text-[#18202b]">Disclosure</p>
            <p className="mt-2">{disclaimer || 'The information provided on this platform is for educational and informational purposes only. It should not be construed as investment advice, research recommendations, portfolio management services, or a solicitation to buy or sell securities. Users should conduct their own research and consult a SEBI-registered investment professional before making investment decisions.'}</p>
          </section>
        </main>
      </div>
    </>
  );
}
