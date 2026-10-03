import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import {
  Activity, ArrowDownRight, ArrowUpRight, BrainCircuit, Clock3, ExternalLink, Newspaper, Pause,
  Play, ShieldAlert, Sparkles, Sunrise, Sunset,
} from 'lucide-react';
import { getMarketBriefing } from '@/api/marketApi';

const REFRESH_MS = 60_000;
const FILTERS = ['All', 'Markets', 'Companies', 'Economy', 'Policy', 'Commodities', 'Results', 'Banking', 'Global', 'IPO', 'Corporate Actions', 'Announcements'];
const SESSION_TABS = [
  { id: 'preMarket', label: 'Pre-Market', icon: Sunrise },
  { id: 'midDay', label: '12 PM', icon: Clock3 },
  { id: 'postMarket', label: 'Market Close', icon: Sunset },
];

function tone(value = '') {
  const text = String(value).toLowerCase();
  if (/bearish|negative|weak|easing|high/i.test(text)) return 'border-[#f7c5c0] bg-[#fff1f0] text-[#b42318]';
  if (/bullish|positive|strong|leading|firming/i.test(text)) return 'border-[#b7ebcc] bg-[#ecfdf3] text-[#087443]';
  return 'border-[#f4d99d] bg-[#fff8e8] text-[#966a00]';
}

function directionIcon(value = '') {
  return /positive|bullish|firming|strong|leading/i.test(value)
    ? <ArrowUpRight className="h-4 w-4" />
    : /negative|bearish|easing|weak/i.test(value)
      ? <ArrowDownRight className="h-4 w-4" />
      : <Activity className="h-4 w-4" />;
}

function relativeTime(value) {
  if (!value) return 'Latest';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60_000));
  if (minutes < 2) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

function ImpactPill({ value }) {
  return <span className={`inline-flex w-fit border px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${tone(value)}`}>{value}</span>;
}

function NewsCard({ article }) {
  const visual = article.category?.slice(0, 1) || 'M';
  return (
    <article className="group border border-[#dde1e6] bg-white p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-[#b8c1cc] hover:shadow-md">
      <div className="flex gap-3">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center border border-[#d9e2ee] bg-[#edf3fa] text-sm font-bold text-[#274c77]">{visual}</div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <ImpactPill value={article.importance} />
            <span className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">{article.category}</span>
          </div>
          {article.url ? (
            <a href={article.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-start gap-1.5 text-base font-bold leading-snug text-[#18202b] hover:underline">
              <span>{article.title}</span><ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#737982]" />
            </a>
          ) : <h2 className="mt-2 text-base font-bold leading-snug text-[#18202b]">{article.title}</h2>}
        </div>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-[#59616d]">{article.summary}</p>
      <div className="mt-4 flex items-center justify-between border-t border-[#edf0f2] pt-3 text-[11px] text-[#737982]">
        <span className="font-semibold">{article.source}</span>
        <span>{relativeTime(article.publishedAt)}</span>
      </div>
    </article>
  );
}

function SnapshotCard({ name, direction }) {
  return (
    <article className="border border-[#dde1e6] bg-white p-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#737982]">{name}</p>
      <div className="mt-2 flex items-center gap-2">
        <span className={tone(direction).split(' ').filter((item) => item.startsWith('text-')).join(' ')}>{directionIcon(direction)}</span>
        <p className="text-sm font-bold text-[#18202b]">{direction || 'Neutral'}</p>
      </div>
    </article>
  );
}

function PanelTitle({ icon: Icon, eyebrow, title, action }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-[#edf0f2] pb-4">
      <div className="flex gap-2">
        <Icon className="mt-0.5 h-4 w-4 text-[#274c77]" />
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#274c77]">{eyebrow}</p>
          <h2 className="mt-1 text-lg font-bold text-[#18202b]">{title}</h2>
        </div>
      </div>
      {action}
    </div>
  );
}

export default function MarketDataCentre() {
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [filter, setFilter] = useState('All');
  const [tickerPaused, setTickerPaused] = useState(false);
  const [sessionTab, setSessionTab] = useState('preMarket');

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const data = await getMarketBriefing();
        if (active) {
          setState({ loading: false, data, error: null });
          const next = data?.intelligence?.sessionNotes?.active;
          if (next) setSessionTab(next);
        }
      } catch (error) {
        if (active) setState((previous) => ({ loading: false, data: previous.data, error }));
      }
    };
    load();
    const interval = window.setInterval(load, REFRESH_MS);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const briefing = state.data;
  const articles = briefing?.articles || [];
  const visibleArticles = useMemo(
    () => (filter === 'All' ? articles : articles.filter((article) => article.category === filter)),
    [articles, filter],
  );
  const intelligence = briefing?.intelligence || {};
  const notes = intelligence.sessionNotes || {};
  const note = notes[sessionTab] || intelligence.activeSessionNote || {};
  const mood = intelligence.mood || {};
  const ticker = briefing?.ticker || [];

  return (
    <div className="min-h-screen bg-[#f7f9fb]">
      <Helmet>
        <title>Market News | Agarwal Global Investments</title>
        <meta name="description" content="AGI’s source-linked market news with Mint-style Pre-Market, 12 PM and Market Close notes." />
      </Helmet>

      <section className="border-b border-[#dde1e6] bg-[#0d1d33] text-white">
        <div className="mx-auto max-w-[1800px] px-4 py-7 sm:px-6 sm:py-9">
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase tracking-[0.14em] text-[#a7c5ec]">
            <BrainCircuit className="h-4 w-4" /> AGI Strategy Desk
          </div>
          <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Market News</h1>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[#d2dceb]">
                Source-linked developments on the left. Professional Pre-Market, 12 PM and Market Close notes on the right — Bullish, Bearish or Neutral, with reasoning.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-[#c6d4e7]">
              <span className={`h-2 w-2 rounded-full ${briefing?.live ? 'bg-[#5ed18b]' : 'bg-[#f2c14e]'}`} />
              {briefing?.live ? 'Live model context' : 'Cached model context'} · Briefing checks every minute
            </div>
          </div>
        </div>
      </section>

      <main className="mx-auto max-w-[1800px] px-4 py-5 sm:px-6 sm:py-7">
        <section className="overflow-hidden border border-[#dde1e6] bg-white" aria-label="Breaking news ticker">
          <div className="flex items-stretch">
            <div className="hidden shrink-0 items-center gap-2 border-r border-[#dde1e6] bg-[#f8fafb] px-4 sm:flex">
              <span className="h-2 w-2 animate-pulse rounded-full bg-[#d92d20]" />
              <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#18202b]">Live</span>
            </div>
            <div className="min-w-0 flex-1 overflow-hidden py-3">
              <div className="agi-headline-ticker-track items-center gap-8 pr-8" style={{ animationPlayState: tickerPaused ? 'paused' : 'running' }} onMouseEnter={() => setTickerPaused(true)} onMouseLeave={() => setTickerPaused(false)}>
                {[...ticker, ...ticker].map((article, index) => (
                  <a key={`${article.url || article.title}-${index}`} href={article.url} target="_blank" rel="noreferrer" className="flex max-w-[480px] shrink-0 items-center gap-2 text-xs text-[#374151] hover:text-[#274c77]">
                    <span className="font-bold text-[#59616d]">{article.source}</span><span className="truncate">{article.title}</span><span className="text-[#98a2b3]">{relativeTime(article.publishedAt)}</span>
                  </a>
                ))}
              </div>
            </div>
            <button type="button" onClick={() => setTickerPaused((value) => !value)} className="border-l border-[#dde1e6] px-3 text-[#59616d] hover:bg-[#f8fafb]" aria-label={tickerPaused ? 'Play ticker' : 'Pause ticker'}>
              {tickerPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            </button>
          </div>
        </section>

        {state.loading ? (
          <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.85fr)_minmax(360px,1fr)]">
            <div className="h-[900px] animate-pulse border border-[#dde1e6] bg-white" />
            <div className="h-[900px] animate-pulse border border-[#dde1e6] bg-white" />
          </div>
        ) : state.error && !briefing ? (
          <section className="mt-5 border border-dashed border-[#cbd2da] bg-white p-10 text-center">
            <ShieldAlert className="mx-auto h-6 w-6 text-[#966a00]" />
            <h2 className="mt-3 text-lg font-bold text-[#18202b]">The market briefing is temporarily unavailable</h2>
            <p className="mt-2 text-sm text-[#667085]">No conclusion should be drawn from an unavailable information feed.</p>
          </section>
        ) : (
          <>
            <section className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8" aria-label="Market direction snapshot">
              {(briefing?.snapshot?.indices || []).map((index) => (
                <SnapshotCard key={index.name} name={index.name} direction={index.direction} />
              ))}
              {(briefing?.snapshot?.commodities || []).slice(0, 3).map((commodity) => (
                <SnapshotCard key={commodity.name} name={commodity.name} direction={commodity.trend || commodity.direction} />
              ))}
              <SnapshotCard name="Market breadth" direction={briefing?.snapshot?.breadth?.label || mood.label} />
            </section>

            <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.85fr)_minmax(360px,1fr)]">
              <section>
                <div className="border border-[#dde1e6] bg-white p-5">
                  <PanelTitle icon={Newspaper} eyebrow="Live market news" title="Developments worth understanding" action={<span className="text-[11px] text-[#737982]">{visibleArticles.length} items</span>} />
                  <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
                    {FILTERS.map((item) => (
                      <button key={item} type="button" onClick={() => setFilter(item)} className={`shrink-0 border px-3 py-1.5 text-xs font-bold transition-colors ${filter === item ? 'border-[#274c77] bg-[#274c77] text-white' : 'border-[#d9dee5] bg-white text-[#59616d] hover:border-[#98a2b3]'}`}>{item}</button>
                    ))}
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                  {visibleArticles.length ? visibleArticles.map((article, index) => <NewsCard key={`${article.url || article.title}-${index}`} article={article} />) : (
                    <div className="col-span-full border border-dashed border-[#cbd2da] bg-white p-8 text-center text-sm text-[#667085]">No items match this filter in the current briefing.</div>
                  )}
                </div>
                <section className="mt-5 border border-[#dde1e6] bg-white p-5">
                  <PanelTitle icon={Clock3} eyebrow="Today’s timeline" title="What to watch next" />
                  <ol className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
                    {(intelligence.events || []).map((event) => (
                      <li key={`${event.timing}-${event.event}`} className="border-l-2 border-[#274c77] bg-[#f8fafb] p-3">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-[#274c77]">{event.timing}</p>
                        <p className="mt-1 text-sm font-bold text-[#18202b]">{event.event}</p>
                        <p className="mt-1 text-xs leading-relaxed text-[#667085]">{event.detail}</p>
                      </li>
                    ))}
                  </ol>
                </section>
              </section>

              <aside className="space-y-4">
                <section className="border border-[#ccd9e8] bg-white p-5">
                  <PanelTitle icon={Sparkles} eyebrow="AGI Strategy Desk" title="Daily Market Notes" />
                  <div className="mt-4 flex gap-2 overflow-x-auto">
                    {SESSION_TABS.map((tab) => {
                      const Icon = tab.icon;
                      const selected = sessionTab === tab.id;
                      return (
                        <button
                          key={tab.id}
                          type="button"
                          onClick={() => setSessionTab(tab.id)}
                          className={`inline-flex shrink-0 items-center gap-1.5 border px-2.5 py-1.5 text-[11px] font-bold ${selected ? 'border-[#274c77] bg-[#274c77] text-white' : 'border-[#d9dee5] bg-white text-[#59616d]'}`}
                        >
                          <Icon className="h-3.5 w-3.5" />
                          {tab.label}
                        </button>
                      );
                    })}
                  </div>

                  <div className="mt-5 flex gap-4">
                    <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full" style={{ background: `conic-gradient(#274c77 ${note.confidence || mood.confidence || 0}%, #e7edf4 0)` }}>
                      <div className="flex h-[64px] w-[64px] flex-col items-center justify-center rounded-full bg-white">
                        <span className="text-sm font-bold text-[#18202b]">{note.confidence || mood.confidence || '—'}%</span>
                        <span className="text-[8px] font-bold uppercase text-[#737982]">Conf.</span>
                      </div>
                    </div>
                    <div>
                      <ImpactPill value={note.outlook || mood.label || 'Neutral'} />
                      <h3 className="mt-2 text-base font-bold text-[#18202b]">{note.title || 'Session note'}</h3>
                      <p className="mt-1 text-[11px] text-[#737982]">{note.subtitle}</p>
                    </div>
                  </div>

                  <p className="mt-5 text-sm font-semibold leading-7 text-[#18202b]">{note.lead}</p>
                  <p className="mt-3 text-sm leading-7 text-[#374151]">{note.body || intelligence.marketExplained}</p>

                  {(note.why || []).length > 0 && (
                    <div className="mt-5 border-t border-[#edf0f2] pt-4">
                      <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#274c77]">Why this view</p>
                      <ul className="mt-3 space-y-2">
                        {note.why.slice(0, 4).map((item) => (
                          <li key={item} className="text-xs leading-relaxed text-[#667085]">• {item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {(note.watch || []).length > 0 && (
                    <div className="mt-5 border-t border-[#edf0f2] pt-4">
                      <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#274c77]">Watch points</p>
                      <ol className="mt-3 space-y-2">
                        {note.watch.slice(0, 4).map((item, index) => (
                          <li key={item} className="flex gap-2 text-xs leading-relaxed text-[#4b5563]">
                            <span className="font-bold text-[#274c77]">{index + 1}.</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                </section>

                {(intelligence.themes || []).length > 0 && (
                  <section className="border border-[#dde1e6] bg-white p-5">
                    <PanelTitle icon={Activity} eyebrow="Structured context" title="Key themes" />
                    <div className="mt-4 flex flex-wrap gap-2">
                      {intelligence.themes.map((theme) => (
                        <span key={theme} className="border border-[#d9e2ee] bg-[#f8fafb] px-2.5 py-1 text-[11px] font-bold text-[#59616d]">{theme}</span>
                      ))}
                    </div>
                  </section>
                )}

                <section className="border border-[#dde1e6] bg-white p-5">
                  <PanelTitle icon={Activity} eyebrow="Relative tape" title="Session leaders & laggards" />
                  <div className="mt-4 grid grid-cols-1 gap-4">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wide text-[#087443]">Stronger</p>
                      <ul className="mt-2 space-y-2">
                        {(briefing?.snapshot?.movers?.stronger || []).map((item) => (
                          <li key={`s-${item.symbol}`} className="flex items-center justify-between gap-3 text-sm">
                            <span className="font-bold text-[#18202b]">{item.name}</span>
                            <ImpactPill value="Bullish" />
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wide text-[#b42318]">Weaker</p>
                      <ul className="mt-2 space-y-2">
                        {(briefing?.snapshot?.movers?.weaker || []).map((item) => (
                          <li key={`w-${item.symbol}`} className="flex items-center justify-between gap-3 text-sm">
                            <span className="font-bold text-[#18202b]">{item.name}</span>
                            <ImpactPill value="Bearish" />
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </section>

                {(intelligence.sectorImpact || []).length > 0 && (
                  <section className="border border-[#dde1e6] bg-white p-5">
                    <PanelTitle icon={Activity} eyebrow="Model read" title="Sector direction" />
                    <div className="mt-4 divide-y divide-[#edf0f2]">
                      {intelligence.sectorImpact.slice(0, 6).map((sector) => (
                        <div key={sector.name} className="flex items-start justify-between gap-3 py-3">
                          <div>
                            <p className="text-sm font-bold text-[#18202b]">{sector.name}</p>
                            <p className="mt-1 text-xs leading-relaxed text-[#667085]">{sector.explanation}</p>
                          </div>
                          <ImpactPill value={sector.direction === 'Positive' ? 'Bullish' : sector.direction === 'Negative' ? 'Bearish' : 'Neutral'} />
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </aside>
            </div>
          </>
        )}
        <p className="mt-6 text-center text-[11px] leading-relaxed text-[#737982]">{briefing?.disclaimer || 'AGI market context is informational only and not investment advice.'}</p>
      </main>
    </div>
  );
}
