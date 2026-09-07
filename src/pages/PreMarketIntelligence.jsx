import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  BrainCircuit,
  CalendarDays,
  Clock3,
  Globe2,
  Newspaper,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import { getPreMarketBriefing } from '@/api/marketApi';

function toneClass(tone = 'Neutral') {
  const text = String(tone).toLowerCase();
  if (/bear|neg|weak|risk-off|high/i.test(text)) return 'border-[#f7c5c0] bg-[#fff1f0] text-[#b42318]';
  if (/bull|pos|strong|mildly positive|risk-on/i.test(text)) return 'border-[#b7ebcc] bg-[#ecfdf3] text-[#087443]';
  return 'border-[#e7eaf0] bg-[#f4f6f9] text-[#59616d]';
}

function Badge({ children, tone = 'Neutral' }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${toneClass(tone)}`}>
      {children}
    </span>
  );
}

function Card({ children, className = '', id }) {
  return (
    <div id={id} className={`rounded-2xl border border-[#e7eaf0] bg-white shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_rgba(16,24,40,0.04)] ${className}`}>
      {children}
    </div>
  );
}

function Sparkline({ values = [], tone = 'Neutral' }) {
  const nums = (values || []).filter(Number.isFinite);
  if (nums.length < 2) return null;
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = max - min || 1;
  const w = 72;
  const h = 24;
  const points = nums.map((v, i) => {
    const x = (i / (nums.length - 1)) * w;
    const y = h - ((v - min) / span) * (h - 4) - 2;
    return `${x},${y}`;
  }).join(' ');
  const stroke = /bull|pos/i.test(tone) ? '#087443' : /bear|neg/i.test(tone) ? '#b42318' : '#3b6ea5';
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden>
      <polyline fill="none" stroke={stroke} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" points={points} />
    </svg>
  );
}

function SectionTitle({ eyebrow, title, detail }) {
  return (
    <div className="mb-4">
      {eyebrow && <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#3b6ea5]">{eyebrow}</p>}
      <h2 className="mt-1 text-lg font-semibold tracking-tight text-[#101828]">{title}</h2>
      {detail && <p className="mt-1 text-xs text-[#667085]">{detail}</p>}
    </div>
  );
}

export default function PreMarketIntelligence() {
  const [state, setState] = useState({ loading: true, data: null, error: null });

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const data = await getPreMarketBriefing();
        if (active) setState({ loading: false, data, error: null });
      } catch (error) {
        if (active) setState((prev) => ({ loading: false, data: prev.data, error }));
      }
    };
    load();
    const interval = window.setInterval(load, 5 * 60_000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const briefing = state.data;
  const note = briefing?.morningNote || {};
  const workspace = briefing?.workspace || {};
  const scenarios = note.scenarios || workspace.scenarios || {};

  const updatedLabel = useMemo(() => {
    if (!briefing?.updatedAt) return 'Awaiting refresh';
    return new Date(briefing.updatedAt).toLocaleString('en-IN', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
    });
  }, [briefing?.updatedAt]);

  return (
    <div className="min-h-screen bg-[#f5f7fb] text-[#101828]">
      <Helmet>
        <title>Pre-Market Intelligence | Agarwal Global Investments</title>
        <meta name="description" content="AGI Pre-Market Intelligence — global overnight markets with Morning Investment Committee research for the India open." />
      </Helmet>

      <section className="border-b border-[#e7eaf0] bg-white">
        <div className="mx-auto max-w-[1500px] px-4 py-8 sm:px-6 lg:py-10">
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-[#3b6ea5]">AGI Pre-Market Intelligence</p>
          <h1 className="mt-2 max-w-3xl text-3xl font-semibold tracking-tight sm:text-4xl">
            Morning Investment Committee Desk
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#667085]">
            Live global context from redistribution-friendly market-data APIs — paired with AGI’s original morning research note. No raw NSE/BSE real-time quotes.
          </p>
          <div className="mt-5 flex flex-wrap gap-4 text-xs text-[#667085]">
            <span className="inline-flex items-center gap-1.5"><Clock3 className="h-3.5 w-3.5" /> Updated {updatedLabel}</span>
            <span className="inline-flex items-center gap-1.5"><Globe2 className="h-3.5 w-3.5" /> {(briefing?.sourcesUsed || []).join(' · ') || 'Loading sources'}</span>
            {briefing?.stale && <span className="font-medium text-[#966a00]">Serving last cached repository data</span>}
          </div>
        </div>
      </section>

      <main className="mx-auto max-w-[1500px] space-y-6 px-4 py-6 sm:px-6 lg:py-8">
        {state.loading ? (
          <div className="h-[520px] animate-pulse rounded-2xl bg-white ring-1 ring-[#e7eaf0]" />
        ) : state.error && !briefing ? (
          <Card className="p-10 text-center">
            <ShieldAlert className="mx-auto h-6 w-6 text-[#966a00]" />
            <h2 className="mt-3 text-lg font-semibold">Pre-market briefing temporarily unavailable</h2>
          </Card>
        ) : (
          <>
            {/* 50/50 Hero */}
            <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <Card className="p-5 sm:p-6">
                <div className="mb-5 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#3b6ea5]">Global Markets</p>
                    <h2 className="mt-1 text-xl font-semibold">Overnight risk dashboard</h2>
                  </div>
                  <Badge tone="Neutral">API proxies</Badge>
                </div>
                <div className="space-y-3">
                  {(workspace.globalMarkets || []).map((market) => (
                    <article key={market.id} className="rounded-2xl border border-[#eef1f6] bg-[#fafbfd] p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#98a2b3]">{market.group || 'Global'}</p>
                          <h3 className="mt-1 text-base font-semibold text-[#101828]">{market.label}</h3>
                        </div>
                        <div className="text-right">
                          <p className={`text-lg font-semibold ${/bull/i.test(market.tone) ? 'text-[#087443]' : /bear/i.test(market.tone) ? 'text-[#b42318]' : 'text-[#101828]'}`}>
                            {market.changeLabel}
                          </p>
                          <div className="mt-1 flex justify-end"><Badge tone={market.tone}>{market.tone}</Badge></div>
                        </div>
                      </div>
                      <div className="mt-3 flex items-end justify-between gap-3">
                        <p className="max-w-[70%] text-xs leading-relaxed text-[#667085]">{market.note}</p>
                        <Sparkline values={market.sparkline} tone={market.tone} />
                      </div>
                      {market.price != null && (
                        <p className="mt-2 text-[10px] text-[#98a2b3]">Proxy level {market.price} · {market.source}</p>
                      )}
                    </article>
                  ))}
                </div>
              </Card>

              <Card id="morning-note" className="p-5 sm:p-6">
                <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[#eef1f6] pb-4">
                  <div className="flex items-start gap-2">
                    <Sparkles className="mt-1 h-4 w-4 text-[#3b6ea5]" />
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#3b6ea5]">Only AI note on this page</p>
                      <h2 className="text-xl font-semibold">{note.title || 'AGI Morning Strategy Note'}</h2>
                      <p className="mt-1 text-xs text-[#667085]">{note.subtitle}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge tone={note.outlook}>{note.outlook || 'Selective'}</Badge>
                    <p className="mt-2 text-[11px] font-semibold text-[#667085]">Confidence {note.confidence ?? '—'}%</p>
                  </div>
                </div>

                <section className="pt-5">
                  <h3 className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#3b6ea5]">Executive Thesis</h3>
                  <p className="mt-3 text-[15px] leading-8 text-[#344054]">{note.executiveThesis}</p>
                </section>

                <section className="mt-6 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-[#eef1f6] p-4">
                    <p className="text-[11px] font-bold uppercase tracking-wide text-[#667085]">Overnight developments</p>
                    <ul className="mt-3 space-y-2">
                      {(note.overnightDevelopments || []).slice(0, 4).map((item) => (
                        <li key={item.market} className="text-xs leading-relaxed text-[#475467]">
                          <span className="font-semibold text-[#101828]">{item.market}</span> {item.move} — {item.why}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="rounded-xl border border-[#eef1f6] p-4">
                    <p className="text-[11px] font-bold uppercase tracking-wide text-[#667085]">What matters today</p>
                    <ul className="mt-3 space-y-2">
                      {(note.whatMattersToday || []).map((item) => (
                        <li key={item} className="text-xs leading-relaxed text-[#475467]">• {item}</li>
                      ))}
                    </ul>
                  </div>
                </section>

                <section className="mt-6 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-[#ecfdf3] bg-[#f6fef9] p-4">
                    <p className="text-[11px] font-bold uppercase tracking-wide text-[#087443]">Sector outlook — winners</p>
                    <ul className="mt-3 space-y-2">
                      {(note.sectorOutlook?.winners || []).map((item) => (
                        <li key={item.name}>
                          <p className="text-sm font-semibold">{item.name}</p>
                          <p className="text-xs text-[#667085]">{item.why}</p>
                        </li>
                      ))}
                      {!note.sectorOutlook?.winners?.length && <li className="text-xs text-[#667085]">Leadership still forming.</li>}
                    </ul>
                  </div>
                  <div className="rounded-xl border border-[#fff1f0] bg-[#fffafa] p-4">
                    <p className="text-[11px] font-bold uppercase tracking-wide text-[#b42318]">Sector risks</p>
                    <ul className="mt-3 space-y-2">
                      {(note.sectorOutlook?.risks || []).map((item) => (
                        <li key={item.name}>
                          <p className="text-sm font-semibold">{item.name}</p>
                          <p className="text-xs text-[#667085]">{item.why}</p>
                        </li>
                      ))}
                      {!note.sectorOutlook?.risks?.length && <li className="text-xs text-[#667085]">No dominant weak sector yet.</li>}
                    </ul>
                  </div>
                </section>

                <section className="mt-6 rounded-xl border border-[#d9e4f2] bg-[#eef4fb] p-4">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-[#1d4f91]">Three things to watch</p>
                  <ul className="mt-3 space-y-2">
                    {(note.threeThingsToWatch || []).map((item) => (
                      <li key={item} className="text-sm text-[#344054]">• {item}</li>
                    ))}
                  </ul>
                </section>
              </Card>
            </section>

            {/* Drivers */}
            <section>
              <SectionTitle eyebrow="Transmission" title="Today's key drivers" detail="Move → India impact → sectors. No raw dump — transmission only." />
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
                {(workspace.drivers || []).map((driver) => (
                  <Card key={driver.id} className="p-4">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold">{driver.label}</p>
                      <span className="inline-flex items-center gap-1 text-xs font-semibold">
                        {/bull|pos/i.test(driver.tone) ? <ArrowUpRight className="h-3.5 w-3.5 text-[#087443]" /> : null}
                        {/bear|neg/i.test(driver.tone) ? <ArrowDownRight className="h-3.5 w-3.5 text-[#b42318]" /> : null}
                        {driver.move}
                      </span>
                    </div>
                    <div className="mt-3"><Badge tone={driver.indiaTone}>{driver.indiaTone}</Badge></div>
                    <div className="mt-3 space-y-1">
                      {(driver.transmission || []).map((step, index) => (
                        <p key={step} className="text-[11px] text-[#667085]">
                          {index > 0 && <span className="mr-1 text-[#98a2b3]">↓</span>}
                          {step}
                        </p>
                      ))}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-1">
                      {(driver.sectors || []).map((sector) => (
                        <span key={sector} className="rounded-full bg-[#f2f4f7] px-2 py-0.5 text-[10px] font-medium text-[#475467]">{sector}</span>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
            </section>

            {/* Heat map + scenarios + sidebar research */}
            <section className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)_minmax(240px,0.7fr)]">
              <Card className="p-5">
                <SectionTitle eyebrow="McKinsey lens" title="Institutional heat map" />
                <div className="overflow-hidden rounded-xl border border-[#eef1f6]">
                  <div className="grid grid-cols-[1.2fr_0.8fr] bg-[#f8fafc] px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-[#667085]">
                    <span>Global driver</span>
                    <span>India impact</span>
                  </div>
                  {(workspace.heatMap || []).map((row) => (
                    <div key={row.driver} className="grid grid-cols-[1.2fr_0.8fr] items-center border-t border-[#eef1f6] px-3 py-3">
                      <span className="text-sm font-medium text-[#101828]">{row.driver}</span>
                      <Badge tone={row.indiaImpact}>{row.indiaImpact}</Badge>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-5">
                <SectionTitle eyebrow="Scenario analysis" title="Base · Bull · Bear" />
                <div className="space-y-3">
                  {[
                    ['Base Case', scenarios.base, 'positive'],
                    ['Bull Case', scenarios.bull, 'positive'],
                    ['Bear Case', scenarios.bear, 'negative'],
                  ].map(([label, item, tone]) => (
                    <div key={label} className="rounded-xl border border-[#eef1f6] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold">{label}</p>
                        <Badge tone={tone}>{item?.probability ?? '—'}%</Badge>
                      </div>
                      <p className="mt-2 text-sm font-medium text-[#101828]">{item?.label}</p>
                      <p className="mt-1 text-xs leading-relaxed text-[#667085]">{item?.detail}</p>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-5">
                <SectionTitle eyebrow="Research desk" title="Sidebar" />
                <div className="space-y-2">
                  {(workspace.researchSidebar || []).map((item) => (
                    item.href?.startsWith('#') ? (
                      <a key={item.label} href={item.href} className="flex items-center justify-between rounded-xl border border-[#eef1f6] px-3 py-2.5 text-sm font-medium text-[#101828] hover:border-[#3b6ea5]">
                        {item.label} <ArrowRight className="h-3.5 w-3.5 text-[#98a2b3]" />
                      </a>
                    ) : (
                      <Link key={item.label} to={item.href} className="flex items-center justify-between rounded-xl border border-[#eef1f6] px-3 py-2.5 text-sm font-medium text-[#101828] hover:border-[#3b6ea5]">
                        {item.label} <ArrowRight className="h-3.5 w-3.5 text-[#98a2b3]" />
                      </Link>
                    )
                  ))}
                </div>
              </Card>
            </section>

            {/* Overnight news */}
            <section>
              <SectionTitle eyebrow="Overnight news" title="What happened · Why it matters" detail="Not a headline dump — institutional transmission." />
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                {(workspace.overnightNews || []).map((item) => (
                  <Card key={item.headline} className="p-4">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-sm font-semibold leading-snug text-[#101828]">{item.headline}</h3>
                      <Badge tone={item.importance === 'HIGH' ? 'Bearish' : 'Neutral'}>{item.importance}</Badge>
                    </div>
                    <div className="mt-3 space-y-2 text-xs text-[#667085]">
                      <p><span className="font-semibold text-[#344054]">Why it matters ↓ </span>{item.whyItMatters}</p>
                      <p><span className="font-semibold text-[#344054]">Affected ↓ </span>{(item.affectedSectors || []).join(' · ')}</p>
                    </div>
                    {item.url && (
                      <a href={item.url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-[11px] font-semibold text-[#1d4f91]">
                        Source <ArrowRight className="h-3 w-3" />
                      </a>
                    )}
                  </Card>
                ))}
                {!workspace.overnightNews?.length && (
                  <Card className="p-6 text-sm text-[#667085] md:col-span-2 xl:col-span-3">
                    Overnight news will populate from AGI’s cached IndianAPI / research feed.
                  </Card>
                )}
              </div>
            </section>

            {/* Calendar + corporate + sectors + questions */}
            <section className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-4">
              <Card className="p-5">
                <div className="mb-4 flex items-center gap-2">
                  <CalendarDays className="h-4 w-4 text-[#3b6ea5]" />
                  <h2 className="text-lg font-semibold">Economic calendar</h2>
                </div>
                <div className="space-y-3">
                  {(workspace.economicCalendar || []).slice(0, 6).map((item) => (
                    <div key={`${item.event}-${item.date}`} className="border-b border-[#eef1f6] pb-2 last:border-0">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-[11px] text-[#98a2b3]">{item.country}</p>
                        <Badge tone={item.impact === 'High' ? 'Bearish' : 'Neutral'}>{item.impact}</Badge>
                      </div>
                      <p className="mt-1 text-sm font-medium">{item.event}</p>
                    </div>
                  ))}
                  {!workspace.economicCalendar?.length && <p className="text-xs text-[#667085]">Calendar refreshes from Finnhub when available.</p>}
                </div>
              </Card>

              <Card className="p-5">
                <div className="mb-4 flex items-center gap-2">
                  <Newspaper className="h-4 w-4 text-[#3b6ea5]" />
                  <h2 className="text-lg font-semibold">Corporate & earnings radar</h2>
                </div>
                <div className="space-y-3">
                  {(workspace.earningsCalendar || []).slice(0, 6).map((item) => (
                    <div key={`${item.symbol}-${item.date}`} className="flex items-center justify-between gap-3 border-b border-[#eef1f6] pb-2 last:border-0">
                      <div>
                        <p className="text-sm font-semibold">{item.symbol}</p>
                        <p className="text-[11px] text-[#98a2b3]">{item.date}{item.hour ? ` · ${item.hour}` : ''}</p>
                      </div>
                      <Badge>Earnings</Badge>
                    </div>
                  ))}
                  {!workspace.earningsCalendar?.length && <p className="text-xs text-[#667085]">Earnings radar populates from Finnhub calendar cache.</p>}
                </div>
              </Card>

              <Card className="p-5">
                <div className="mb-4 flex items-center gap-2">
                  <BrainCircuit className="h-4 w-4 text-[#3b6ea5]" />
                  <h2 className="text-lg font-semibold">Sector watch</h2>
                </div>
                <div className="space-y-3">
                  {(workspace.sectorWatch || []).map((item) => (
                    <div key={item.name} className="rounded-xl border border-[#eef1f6] p-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold">{item.name}</p>
                        <Badge tone={item.direction}>{item.direction}</Badge>
                      </div>
                      <p className="mt-1 text-xs text-[#667085]">{item.why}</p>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-5">
                <div className="mb-4 flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-[#3b6ea5]" />
                  <h2 className="text-lg font-semibold">Questions before open</h2>
                </div>
                <ul className="space-y-2">
                  {(workspace.questions || note.questions || []).map((q) => (
                    <li key={q} className="rounded-xl border border-[#eef1f6] bg-[#fafbfd] px-3 py-2.5 text-sm leading-relaxed text-[#344054]">
                      {q}
                    </li>
                  ))}
                </ul>
              </Card>
            </section>

            <p className="pb-6 text-center text-[11px] leading-relaxed text-[#98a2b3]">
              {briefing?.disclaimer}
              {' '}
              {briefing?.compliance?.indianQuotes}
            </p>
          </>
        )}
      </main>
    </div>
  );
}
