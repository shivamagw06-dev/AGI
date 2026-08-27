import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, NavLink } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Bell,
  BookOpen,
  BrainCircuit,
  CalendarDays,
  ChevronRight,
  Clock3,
  Globe2,
  Home,
  Landmark,
  LineChart,
  Newspaper,
  Search,
  Settings,
  ShieldAlert,
  Sparkles,
  X,
} from 'lucide-react';
import { askMacroEconomist, getMacroBriefing } from '@/api/marketApi';
import { getIntelligenceHealth, listResearchRuns } from '@/lib/intelligenceApi';
import { getUiMacro } from '@/lib/uiApi';
import { supabase } from '@/lib/supabaseClient';
import { mapArticleForCard } from '@/lib/articleUtils';

const NAV = [
  { id: 'overview', label: 'Overview', icon: Home },
  { id: 'brief', label: 'Chief Economist Brief', icon: BrainCircuit },
  { id: 'indicators', label: 'Macro Dashboard', icon: LineChart },
  { id: 'transmission', label: 'Transmission Maps', icon: Activity },
  { id: 'changes', label: 'What Changed', icon: Newspaper },
  { id: 'sectors', label: 'Sector Impact', icon: ArrowUpRight },
  { id: 'policy', label: 'Policy Tracker', icon: Landmark },
  { id: 'risks', label: 'Risk Monitor', icon: AlertTriangle },
  { id: 'calendar', label: 'Economic Calendar', icon: CalendarDays },
  { id: 'research', label: 'Research', icon: BookOpen },
];

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'brief', label: 'Global Economy' },
  { id: 'indicators', label: 'India Focus' },
  { id: 'policy', label: 'Monetary Policy' },
  { id: 'changes', label: 'Commodities' },
  { id: 'transmission', label: 'Currencies' },
  { id: 'policy', label: 'Policy Tracker' },
  { id: 'research', label: 'Watchlist' },
];

function scrollToId(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function toneClass(tone = 'neutral') {
  if (tone === 'positive') return 'bg-[#ecfdf3] text-[#087443] border-[#b7ebcc]';
  if (tone === 'negative') return 'bg-[#fff1f0] text-[#b42318] border-[#f7c5c0]';
  return 'bg-[#f4f6f9] text-[#59616d] border-[#e7eaf0]';
}

function statusTone(value = '') {
  const text = String(value).toLowerCase();
  if (/weak|high|risk|tight|delay|cautious|bear|neg|dry|restrict/i.test(text)) return 'negative';
  if (/improv|construct|positive|strong|wet|eas|moderat|support|bull/i.test(text)) return 'positive';
  return 'neutral';
}

function Badge({ children, tone = 'neutral' }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold tracking-wide ${toneClass(tone)}`}>
      {children}
    </span>
  );
}

function Card({ children, className = '' }) {
  return (
    <div className={`rounded-2xl border border-[#e7eaf0] bg-white shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_rgba(16,24,40,0.04)] ${className}`}>
      {children}
    </div>
  );
}

function Sparkline({ values = [], tone = 'neutral' }) {
  const nums = values.filter(Number.isFinite);
  if (nums.length < 2) return null;
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = max - min || 1;
  const w = 88;
  const h = 28;
  const points = nums.map((v, i) => {
    const x = (i / (nums.length - 1)) * w;
    const y = h - ((v - min) / span) * (h - 4) - 2;
    return `${x},${y}`;
  }).join(' ');
  const stroke = tone === 'positive' ? '#087443' : tone === 'negative' ? '#b42318' : '#3b6ea5';
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible" aria-hidden>
      <polyline fill="none" stroke={stroke} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" points={points} />
    </svg>
  );
}

function SectionTitle({ eyebrow, title, action }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div>
        {eyebrow && <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#3b6ea5]">{eyebrow}</p>}
        <h2 className="mt-1 text-lg font-semibold tracking-tight text-[#101828]">{title}</h2>
      </div>
      {action}
    </div>
  );
}

export default function MacroIntelligence() {
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [research, setResearch] = useState([]);
  const [engineStatus, setEngineStatus] = useState({ loading: true, health: null, latestRun: null });
  const [activeTab, setActiveTab] = useState('overview');
  const [askOpen, setAskOpen] = useState(false);
  const [askQuery, setAskQuery] = useState('');
  const [askAnswer, setAskAnswer] = useState(null);
  const [askLoading, setAskLoading] = useState(false);
  const [nodePanel, setNodePanel] = useState(null);
  const [briefExpanded, setBriefExpanded] = useState(false);
  const [uiMacro, setUiMacro] = useState(null);
  const [indiaOverlay, setIndiaOverlay] = useState('');
  const [researchNotes, setResearchNotes] = useState('');

  useEffect(() => {
    setIndiaOverlay(window.localStorage.getItem('agi-macro-india-overlay') || '');
    setResearchNotes(window.localStorage.getItem('agi-macro-research-notes') || '');
  }, []);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const data = await getMacroBriefing();
        if (active) setState({ loading: false, data, error: null });
      } catch (error) {
        if (active) setState((prev) => ({ loading: false, data: prev.data, error }));
      }
    };
    load();
    getUiMacro()
      .then((data) => active && setUiMacro(data))
      .catch(() => active && setUiMacro(null));
    const interval = window.setInterval(load, 30 * 60_000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [health, runs] = await Promise.all([
          getIntelligenceHealth().catch(() => null),
          listResearchRuns({ limit: '1' }).catch(() => []),
        ]);
        if (!active) return;
        setEngineStatus({
          loading: false,
          health,
          latestRun: Array.isArray(runs) && runs[0] ? runs[0] : null,
        });
      } catch {
        if (active) setEngineStatus({ loading: false, health: null, latestRun: null });
      }
    })();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { data } = await supabase
        .from('articles')
        .select('id, title, slug, excerpt, cover_url, tags, published_at, section, status')
        .eq('status', 'published')
        .order('published_at', { ascending: false })
        .limit(24);
      if (cancelled) return;
      const macroSections = /economy|macro|global|commodit|research|policy|budget|inflation|rbi/i;
      const mapped = (data || []).map(mapArticleForCard).filter(Boolean);
      const filtered = mapped.filter((article) => {
        const haystack = `${article.section || ''} ${(article.tags || []).join(' ')} ${article.title || ''}`;
        return macroSections.test(haystack);
      });
      setResearch((filtered.length ? filtered : mapped).slice(0, 6));
    })();
    return () => { cancelled = true; };
  }, []);

  const briefing = state.data;
  const brief = briefing?.chiefEconomistBrief || {};
  const snapshot = briefing?.snapshot || {};
  const workspace = briefing?.workspace || {};
  const regime = workspace.regime || {};
  const indicators = workspace.indicators || [];
  const whatChanged = workspace.whatChanged || [];
  const transmission = workspace.transmission || {};
  const confidence = workspace.confidenceBreakdown || {};

  const updatedLabel = useMemo(() => {
    if (!briefing?.updatedAt) return 'Awaiting refresh';
    return new Date(briefing.updatedAt).toLocaleString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  }, [briefing?.updatedAt]);

  const handleAsk = async (query) => {
    const q = String(query || askQuery).trim();
    if (!q) return;
    setAskQuery(q);
    setAskOpen(true);
    setAskLoading(true);
    setAskAnswer({ query: q, response: '', evidence: [], implications: null, related: [], outlook: 'Loading', source: null });
    try {
      const answer = await askMacroEconomist(q);
      setAskAnswer(answer);
    } catch {
      setAskAnswer({
        query: q,
        response: brief.executiveThesis || 'Macro research is temporarily unavailable. Please retry shortly.',
        evidence: brief.whyReached || [],
        implications: brief.sectorImpact || null,
        related: brief.institutionalQuestions || [],
        outlook: brief.outlook || 'Data-dependent',
        source: 'briefing fallback',
      });
    } finally {
      setAskLoading(false);
    }
  };

  const goTab = (id) => {
    setActiveTab(id);
    scrollToId(id === 'overview' ? 'macro-hero' : id);
  };

  const intel = uiMacro?.intelligence || {};
  const indiaCountry = (snapshot.countries || []).find((country) => country.name === 'India');
  const indiaImpact = [
    indiaCountry?.why,
    snapshot.fx?.[0]?.implication,
    snapshot.commodities?.[0]?.implication,
  ].filter(Boolean).slice(0, 3);

  return (
    <div className="min-h-screen bg-[#f5f7fb] text-[#101828]">
      <Helmet>
        <title>Global Markets | Agarwal Global Investments</title>
        <meta name="description" content="AGI global markets and macro research workspace — global developments, India transmission, sector impact, and the house view." />
        <link rel="canonical" href="https://agarwalglobalinvestments.com/global-markets" />
        <meta property="og:title" content="Global Markets | AGI" />
        <meta property="og:description" content="Transform global markets and macro data into India investment intelligence." />
        <script type="application/ld+json">
          {JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'WebPage',
            name: 'AGI Global Markets',
            description: intel.what_happened || 'Institutional global markets and macro investment intelligence',
          })}
        </script>
      </Helmet>

      {(intel.what_happened || (uiMacro?.follow_up_questions || []).length > 0) && (
        <section className="border-b border-[#e7eaf0] bg-white">
          <div className="mx-auto max-w-[1600px] px-4 py-5 sm:px-6">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#ff6600]">Investment intelligence</p>
            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="border border-[#e7eaf0] p-4">
                <p className="text-[10px] font-bold uppercase text-[#667085]">What happened</p>
                <p className="mt-2 text-sm font-semibold text-[#101828]">{intel.what_happened || uiMacro?.current_regime?.label || '—'}</p>
              </div>
              <div className="border border-[#e7eaf0] p-4">
                <p className="text-[10px] font-bold uppercase text-[#667085]">Why</p>
                <p className="mt-2 text-sm text-[#344054]">{intel.why || 'Regime context from the institutional desk.'}</p>
              </div>
              <div className="border border-[#e7eaf0] p-4">
                <p className="text-[10px] font-bold uppercase text-[#667085]">Who benefits</p>
                <p className="mt-2 text-sm text-[#344054]">{(intel.who_benefits || []).join(' · ') || '—'}</p>
              </div>
              <div className="border border-[#e7eaf0] p-4">
                <p className="text-[10px] font-bold uppercase text-[#667085]">How AGI view changed</p>
                <p className="mt-2 text-sm text-[#344054]">{intel.how_view_changed || 'See What Changed below.'}</p>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {(uiMacro?.follow_up_questions || []).slice(0, 4).map((q) => (
                <Link
                  key={q}
                  to={`/ask?q=${encodeURIComponent(q)}`}
                  className="text-[11px] border border-[#ddd] bg-white px-2.5 py-1.5 font-bold text-[#101828] hover:text-[#ff6600]"
                >
                  {q}
                </Link>
              ))}
              <Link to="/predictions" className="text-[11px] border border-[#ddd] bg-white px-2.5 py-1.5 font-bold hover:text-[#ff6600]">
                Prediction Centre →
              </Link>
            </div>
          </div>
        </section>
      )}

      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        {/* Workspace sidebar */}
        <aside className="sticky top-0 hidden h-screen w-[240px] shrink-0 flex-col border-r border-[#e7eaf0] bg-white lg:flex">
          <div className="border-b border-[#e7eaf0] px-5 py-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3b6ea5]">AGI Intelligence</p>
            <p className="mt-1 text-sm font-semibold text-[#101828]">Global Markets Terminal</p>
          </div>
          <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
            {NAV.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => goTab(item.id)}
                  className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-[13px] transition ${
                    activeTab === item.id
                      ? 'bg-[#eef4fb] font-semibold text-[#1d4f91]'
                      : 'text-[#475467] hover:bg-[#f8fafc]'
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0 opacity-80" />
                  <span className="truncate">{item.label}</span>
                </button>
              );
            })}
          </nav>
          <div className="space-y-3 border-t border-[#e7eaf0] p-4">
            <div className="rounded-2xl bg-gradient-to-br from-[#eef4fb] to-white p-4 ring-1 ring-[#d9e4f2]">
              <p className="text-xs font-semibold text-[#101828]">AGI Global Markets Brief</p>
              <p className="mt-1 text-[11px] leading-relaxed text-[#667085]">Daily global markets and macro note for CIOs and research desks.</p>
              <button type="button" onClick={() => goTab('brief')} className="mt-3 text-[11px] font-semibold text-[#1d4f91]">
                Open brief →
              </button>
            </div>
            <NavLink to="/research" className="flex items-center gap-2 px-1 text-[12px] text-[#667085] hover:text-[#101828]">
              <Settings className="h-3.5 w-3.5" /> Research library
            </NavLink>
          </div>
        </aside>

        {/* Main workspace */}
        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 border-b border-[#e7eaf0] bg-white/90 backdrop-blur">
            <div className="flex flex-wrap items-center gap-3 px-4 py-3 sm:px-6">
              <div className="relative min-w-[200px] flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#98a2b3]" />
                <input
                  value={askQuery}
                  onChange={(e) => setAskQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
                  placeholder="Search macro, markets, reports…"
                  className="w-full rounded-xl border border-[#e7eaf0] bg-[#f8fafc] py-2.5 pl-10 pr-3 text-sm outline-none ring-[#3b6ea5]/30 focus:bg-white focus:ring-2"
                />
              </div>
              <button
                type="button"
                onClick={() => handleAsk(askQuery || workspace.askPrompts?.[0])}
                className="inline-flex items-center gap-2 rounded-xl bg-[#1d4f91] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#163f75]"
              >
                <Sparkles className="h-4 w-4" />
                Ask AGI Economist
              </button>
              <button type="button" className="rounded-xl border border-[#e7eaf0] p-2.5 text-[#667085]" aria-label="Notifications">
                <Bell className="h-4 w-4" />
              </button>
            </div>
            <div className="flex gap-1 overflow-x-auto px-4 pb-3 sm:px-6">
              {TABS.map((tab, index) => (
                <button
                  key={`${tab.label}-${index}`}
                  type="button"
                  onClick={() => goTab(tab.id)}
                  className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-semibold transition ${
                    activeTab === tab.id
                      ? 'bg-[#101828] text-white'
                      : 'bg-[#f2f4f7] text-[#475467] hover:bg-[#e7eaf0]'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </header>

          <main className="space-y-6 px-4 py-6 sm:px-6 lg:py-8">
            {state.loading ? (
              <div className="h-[520px] animate-pulse rounded-2xl bg-white ring-1 ring-[#e7eaf0]" />
            ) : state.error && !briefing ? (
              <Card className="p-10 text-center">
                <ShieldAlert className="mx-auto h-6 w-6 text-[#966a00]" />
                <h2 className="mt-3 text-lg font-semibold">Macro briefing temporarily unavailable</h2>
                <p className="mt-2 text-sm text-[#667085]">AGI will serve the last repository cache when available.</p>
              </Card>
            ) : (
              <>
                {/* Hero */}
                <section id="macro-hero" className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.55fr)_minmax(280px,0.75fr)]">
                  <Card className="p-6 sm:p-8">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3b6ea5]">Global Markets & Macro Intelligence</p>
                        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-[#101828] sm:text-4xl">Global Markets Brief</h1>
                        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#667085]">
                          Global economy. Indian economy. Investment implications — an institutional research workspace, not a data dashboard.
                        </p>
                      </div>
                      <Badge tone={statusTone(brief.outlook)}>{brief.outlook || 'Data-dependent'}</Badge>
                    </div>
                    <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-[#667085]">
                      <span className="inline-flex items-center gap-1.5"><Clock3 className="h-3.5 w-3.5" /> Updated {updatedLabel}</span>
                      <span className="inline-flex items-center gap-1.5"><Globe2 className="h-3.5 w-3.5" /> Sources: {(briefing?.sourcesUsed || []).join(' · ') || 'AGI repository'}</span>
                      {briefing?.stale && <span className="font-medium text-[#966a00]">Serving last cached repository data</span>}
                      <span className="inline-flex items-center gap-1.5">
                        <BrainCircuit className="h-3.5 w-3.5" />
                        {engineStatus.loading
                          ? 'Intelligence Engine…'
                          : engineStatus.health?.engine?.ok || engineStatus.health?.ok
                            ? `Intelligence Engine online${engineStatus.latestRun?.run_id ? ` · last run ${String(engineStatus.latestRun.run_id).slice(0, 12)}` : ''}`
                            : 'Intelligence Engine offline (deterministic desk active)'}
                      </span>
                    </div>
                    {briefing?.stale && (
                      <div className="mt-4 rounded-xl border border-[#f4d28b] bg-[#fff8e8] px-3 py-2 text-xs text-[#8a5a00]">
                        This macro brief is using the last verified snapshot. Check each indicator date before acting on it.
                      </div>
                    )}
                  </Card>

                  <Card className="p-5">
                    <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#3b6ea5]">Macro Regime</p>
                    <div className="mt-4 grid grid-cols-2 gap-3">
                      {[
                        ['Regime', regime.macroRegime],
                        ['Confidence', regime.confidence != null ? `${regime.confidence}%` : '—'],
                        ['Cycle', regime.cycle],
                        ['Inflation', regime.inflation],
                        ['Policy', regime.policy],
                        ['Liquidity', regime.liquidity],
                      ].map(([label, value]) => (
                        <div key={label} className="rounded-xl border border-[#eef1f6] bg-[#fafbfd] p-3">
                          <p className="text-[10px] font-semibold uppercase tracking-wide text-[#98a2b3]">{label}</p>
                          <p className="mt-1 text-sm font-semibold text-[#101828]">{value || '—'}</p>
                        </div>
                      ))}
                    </div>
                  </Card>
                </section>

                {/* India impact + private analyst workspace */}
                <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <Card className="p-6">
                    <SectionTitle eyebrow="India transmission" title="How the latest macro view affects India" />
                    <p className="text-sm leading-7 text-[#344054]">
                      {indiaCountry?.why || 'India-specific transmission is awaiting the next verified macro refresh.'}
                    </p>
                    {indiaImpact.length > 1 && (
                      <ul className="mt-4 space-y-2">
                        {indiaImpact.slice(1).map((item) => <li key={item} className="text-xs leading-relaxed text-[#667085]">• {item}</li>)}
                      </ul>
                    )}
                    <label className="mt-5 block text-[11px] font-semibold uppercase tracking-wide text-[#667085]" htmlFor="india-overlay">
                      Your India view / override
                    </label>
                    <textarea
                      id="india-overlay"
                      value={indiaOverlay}
                      onChange={(event) => setIndiaOverlay(event.target.value)}
                      onBlur={() => window.localStorage.setItem('agi-macro-india-overlay', indiaOverlay)}
                      placeholder="Add your interpretation, conviction, or condition that would change the view…"
                      className="mt-2 min-h-28 w-full rounded-xl border border-[#d0d5dd] bg-white p-3 text-sm text-[#101828] outline-none focus:border-[#3b6ea5] focus:ring-2 focus:ring-[#3b6ea5]/20"
                    />
                    <p className="mt-2 text-[11px] text-[#98a2b3]">Private browser note — it never changes AGI’s automated macro evidence.</p>
                  </Card>

                  <Card className="p-6">
                    <SectionTitle eyebrow="Analyst workspace" title="My research notes" />
                    <textarea
                      value={researchNotes}
                      onChange={(event) => setResearchNotes(event.target.value)}
                      onBlur={() => window.localStorage.setItem('agi-macro-research-notes', researchNotes)}
                      placeholder="Write your macro thesis, questions for the research desk, upcoming catalysts, and sources to verify…"
                      className="min-h-60 w-full rounded-xl border border-[#d0d5dd] bg-white p-3 text-sm leading-6 text-[#101828] outline-none focus:border-[#3b6ea5] focus:ring-2 focus:ring-[#3b6ea5]/20"
                    />
                    <p className="mt-2 text-[11px] text-[#98a2b3]">Saved automatically in this browser. It is separate from published research and automated data.</p>
                  </Card>
                </section>

                {/* AI Brief + Indicators */}
                <section id="brief" className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
                  <Card className="p-6 sm:p-7">
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#eef1f6] pb-4">
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-[#3b6ea5]" />
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#3b6ea5]">Only AI note on this page</p>
                          <h2 className="text-xl font-semibold text-[#101828]">{brief.title || 'AGI Chief Economist Brief'}</h2>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge>{briefing?.aiGenerated ? 'AI Generated' : 'AGI Desk'}</Badge>
                        <Badge tone={statusTone(brief.outlook)}>{brief.outlook}</Badge>
                      </div>
                    </div>

                    <p className={`mt-5 text-[15px] leading-8 text-[#344054] ${briefExpanded ? '' : 'line-clamp-6'}`}>
                      {brief.executiveThesis}
                    </p>
                    <button type="button" onClick={() => setBriefExpanded((v) => !v)} className="mt-3 text-sm font-semibold text-[#1d4f91]">
                      {briefExpanded ? 'Collapse brief' : 'Read full brief'} →
                    </button>

                    <div className="mt-6 grid gap-3 sm:grid-cols-2">
                      {(brief.whyReached || []).slice(0, 4).map((item, index) => (
                        <div key={item.title} className="rounded-xl border border-[#eef1f6] bg-[#fafbfd] p-4">
                          <p className="text-sm font-semibold text-[#101828]">{index + 1}. {item.title}</p>
                          <p className="mt-2 text-xs leading-relaxed text-[#667085]">{item.explanation}</p>
                        </div>
                      ))}
                    </div>
                  </Card>

                  <div id="indicators" className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-2">
                    {indicators.map((item) => (
                      <Card key={item.id} className="p-4">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-[11px] font-semibold text-[#667085]">{item.label}</p>
                          <Badge tone={item.tone}>{item.status}</Badge>
                        </div>
                        <p className="mt-3 text-2xl font-semibold tracking-tight text-[#101828]">{item.value}</p>
                        <div className="mt-3 flex items-end justify-between">
                          <Sparkline values={item.sparkline} tone={item.tone} />
                          <p className="text-[10px] text-[#98a2b3]">{item.asOf || item.source}</p>
                        </div>
                      </Card>
                    ))}
                  </div>
                </section>

                {/* Countries */}
                <section>
                  <SectionTitle eyebrow="Global macro snapshot" title="Country intelligence" />
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
                    {(snapshot.countries || []).map((country) => (
                      <Card key={country.name} className="p-4 transition hover:-translate-y-0.5 hover:shadow-md">
                        <p className="text-[11px] font-semibold text-[#667085]">{country.name}</p>
                        <div className="mt-3"><Badge tone={statusTone(country.condition)}>{country.condition}</Badge></div>
                        <p className="mt-3 line-clamp-4 text-xs leading-relaxed text-[#667085]">{country.why}</p>
                      </Card>
                    ))}
                  </div>
                </section>

                {/* Transmission + What changed + Sectors */}
                <section className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(260px,0.7fr)_minmax(260px,0.7fr)]">
                  <Card id="transmission" className="p-5 sm:p-6">
                    <SectionTitle eyebrow="AGI signature" title={transmission.title || 'Macro Transmission Map'} />
                    <p className="mb-5 text-xs text-[#667085]">{transmission.subtitle}</p>
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                      <div>
                        <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-[#98a2b3]">Drivers</p>
                        <div className="space-y-2">
                          {(transmission.drivers || []).map((node) => (
                            <button
                              key={node.id}
                              type="button"
                              onClick={() => setNodePanel({ ...node, kind: 'driver' })}
                              className="flex w-full items-center justify-between rounded-xl border border-[#e7eaf0] bg-[#f8fafc] px-3 py-2.5 text-left text-xs font-semibold text-[#101828] hover:border-[#3b6ea5]"
                            >
                              {node.label}
                              <ChevronRight className="h-3.5 w-3.5 text-[#98a2b3]" />
                            </button>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-[#98a2b3]">Transmission</p>
                        <div className="space-y-2">
                          {(transmission.transmissions || []).map((node) => (
                            <button
                              key={node.id}
                              type="button"
                              onClick={() => setNodePanel({ ...node, kind: 'transmission' })}
                              className="w-full rounded-xl border border-[#d9e4f2] bg-[#eef4fb] px-3 py-2.5 text-left text-xs font-semibold text-[#1d4f91]"
                            >
                              {node.label}
                            </button>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-[#98a2b3]">Outcomes</p>
                        <div className="space-y-2">
                          {(transmission.outcomes || []).map((node) => (
                            <button
                              key={node.id}
                              type="button"
                              onClick={() => setNodePanel({ ...node, kind: 'outcome' })}
                              className={`w-full rounded-xl border px-3 py-2.5 text-left text-xs font-semibold ${toneClass(node.tone)}`}
                            >
                              {node.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                    {(transmission.maps || []).length > 0 && (
                      <div className="mt-6 grid gap-3 lg:grid-cols-3">
                        {transmission.maps.map((map) => (
                          <div key={map.id} className="rounded-xl border border-[#eef1f6] p-3">
                            <p className="text-[11px] font-semibold text-[#3b6ea5]">{map.title}</p>
                            <p className="mt-1 text-xs font-medium text-[#101828]">{map.trigger}</p>
                            <ol className="mt-2 space-y-1">
                              {(map.steps || []).slice(0, 4).map((step) => (
                                <li key={step} className="text-[11px] leading-relaxed text-[#667085]">→ {step}</li>
                              ))}
                            </ol>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>

                  <Card id="changes" className="p-5">
                    <SectionTitle eyebrow="Today" title="What changed" />
                    <div className="space-y-3">
                      {whatChanged.map((item) => (
                        <div key={item.id} className="rounded-xl border border-[#eef1f6] p-3">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-[#101828]">{item.title}</p>
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#475467]">
                              {item.tone === 'positive' ? <ArrowUpRight className="h-3.5 w-3.5 text-[#087443]" /> : null}
                              {item.tone === 'negative' ? <ArrowDownRight className="h-3.5 w-3.5 text-[#b42318]" /> : null}
                              {item.move}
                            </span>
                          </div>
                          <p className="mt-2 text-xs leading-relaxed text-[#667085]"><span className="font-semibold text-[#344054]">Why: </span>{item.why}</p>
                          <p className="mt-1 text-[11px] font-medium text-[#3b6ea5]">Impact: {item.impact}</p>
                        </div>
                      ))}
                    </div>
                  </Card>

                  <Card id="sectors" className="p-5">
                    <SectionTitle eyebrow="Allocation lens" title="Sector impact (India)" />
                    <div className="space-y-4">
                      <div>
                        <p className="text-[11px] font-bold uppercase tracking-wide text-[#087443]">Beneficiaries</p>
                        <ul className="mt-2 space-y-2">
                          {(brief.sectorImpact?.beneficiaries || []).map((item) => (
                            <li key={item.name} className="rounded-xl border border-[#ecfdf3] bg-[#f6fef9] p-3">
                              <div className="flex items-center justify-between gap-2">
                                <p className="text-sm font-semibold text-[#101828]">{item.name}</p>
                                <Badge tone="positive">Positive</Badge>
                              </div>
                              <p className="mt-1 text-xs text-[#667085]">{item.why}</p>
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <p className="text-[11px] font-bold uppercase tracking-wide text-[#b42318]">Headwinds</p>
                        <ul className="mt-2 space-y-2">
                          {(brief.sectorImpact?.challenged || []).map((item) => (
                            <li key={item.name} className="rounded-xl border border-[#fff1f0] bg-[#fffafa] p-3">
                              <div className="flex items-center justify-between gap-2">
                                <p className="text-sm font-semibold text-[#101828]">{item.name}</p>
                                <Badge tone="negative">Negative</Badge>
                              </div>
                              <p className="mt-1 text-xs text-[#667085]">{item.why}</p>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </Card>
                </section>

                {/* Debate + Confidence */}
                <section className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.6fr)]">
                  <Card className="p-6">
                    <SectionTitle eyebrow="AI debate" title="Bull case · Bear case · AGI verdict" />
                    <div className="grid gap-4 md:grid-cols-3">
                      <div className="rounded-2xl border border-[#ecfdf3] bg-[#f6fef9] p-4">
                        <p className="text-[11px] font-bold uppercase tracking-wide text-[#087443]">Bull case</p>
                        <ul className="mt-3 space-y-2">
                          {(brief.debate?.bullishFactors || []).map((item) => (
                            <li key={item} className="text-xs leading-relaxed text-[#344054]">• {item}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="rounded-2xl border border-[#fff1f0] bg-[#fffafa] p-4">
                        <p className="text-[11px] font-bold uppercase tracking-wide text-[#b42318]">Bear case</p>
                        <ul className="mt-3 space-y-2">
                          {(brief.debate?.bearishFactors || []).map((item) => (
                            <li key={item} className="text-xs leading-relaxed text-[#344054]">• {item}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="rounded-2xl border border-[#d9e4f2] bg-[#eef4fb] p-4">
                        <p className="text-[11px] font-bold uppercase tracking-wide text-[#1d4f91]">AGI verdict</p>
                        <p className="mt-3 text-lg font-semibold text-[#101828]">{brief.outlook}</p>
                        <p className="mt-2 text-xs leading-relaxed text-[#475467]">{brief.debate?.verdict}</p>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-5">
                    <SectionTitle eyebrow="Conviction" title="Confidence" />
                    <p className="text-3xl font-semibold text-[#101828]">{confidence.score ?? brief.confidence ?? '—'}%</p>
                    <p className="mt-2 text-xs leading-relaxed text-[#667085]">{confidence.rationale || brief.confidenceRationale}</p>
                    <div className="mt-4 space-y-2">
                      {(confidence.supports || []).map((item) => (
                        <p key={`s-${item}`} className="text-xs font-medium text-[#087443]">✔ {item}</p>
                      ))}
                      {(confidence.challenges || []).map((item) => (
                        <p key={`c-${item}`} className="text-xs font-medium text-[#b42318]">✘ {item}</p>
                      ))}
                    </div>
                    <p className="mt-4 rounded-xl bg-[#f8fafc] p-3 text-xs leading-relaxed text-[#475467]">
                      {confidence.summary || 'Several indicators disagree. Therefore confidence is moderate rather than high.'}
                    </p>
                  </Card>
                </section>

                {/* Bottom grid */}
                <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <Card className="p-5">
                    <SectionTitle eyebrow="Global" title="Overview" />
                    <div className="space-y-3">
                      {(snapshot.countries || []).filter((c) => ['United States', 'Europe', 'China'].includes(c.name)).map((country) => (
                        <div key={country.name} className="flex items-center justify-between gap-3 border-b border-[#eef1f6] pb-2 last:border-0">
                          <p className="text-sm font-medium text-[#101828]">{country.name === 'United States' ? 'United States' : country.name}</p>
                          <Badge tone={statusTone(country.condition)}>{country.condition}</Badge>
                        </div>
                      ))}
                    </div>
                  </Card>

                  <Card id="calendar" className="p-5">
                    <SectionTitle eyebrow="Calendar" title="Upcoming key events" />
                    <div className="space-y-3">
                      {(snapshot.calendar || []).slice(0, 5).map((item) => (
                        <div key={item.event} className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-[11px] font-semibold text-[#98a2b3]">{item.date || 'TBD'}</p>
                            <p className="text-sm font-medium text-[#101828]">{item.event}</p>
                          </div>
                          <Badge tone={item.importance === 'High' ? 'negative' : 'neutral'}>{item.importance}</Badge>
                        </div>
                      ))}
                    </div>
                  </Card>

                  <Card id="policy" className="p-5">
                    <SectionTitle eyebrow="Policy" title="Policy tracker" />
                    <div className="space-y-3">
                      {(snapshot.policyTracker || []).map((item) => (
                        <div key={item.body} className="border-l-2 border-[#3b6ea5] pl-3">
                          <p className="text-sm font-semibold text-[#101828]">{item.body}</p>
                          <p className="mt-1 text-xs text-[#667085]">{item.whatChanged}</p>
                          <p className="mt-1 text-[11px] text-[#98a2b3]">Affected: {item.whoAffected}</p>
                        </div>
                      ))}
                    </div>
                  </Card>

                  <Card id="risks" className="p-5">
                    <SectionTitle eyebrow="Risks" title="Risk monitor" />
                    <div className="space-y-3">
                      {(snapshot.risks || brief.keyRisks || []).slice(0, 4).map((risk) => (
                        <div key={risk.label} className="rounded-xl border border-[#eef1f6] p-3">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-semibold">{risk.label}</p>
                            <Badge tone={statusTone(risk.level)}>{risk.level}</Badge>
                          </div>
                          <p className="mt-1 text-xs text-[#667085]">{risk.why}</p>
                          <p className="mt-1 text-[11px] text-[#3b6ea5]">Watch: {risk.watch}</p>
                        </div>
                      ))}
                    </div>
                  </Card>
                </section>

                {/* Questions + Research */}
                <section className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                  <Card className="p-6">
                    <SectionTitle eyebrow="Return reason" title="Questions we are watching" />
                    <ul className="space-y-2">
                      {(brief.institutionalQuestions || []).map((q) => (
                        <li key={q}>
                          <button
                            type="button"
                            onClick={() => handleAsk(q)}
                            className="flex w-full items-start gap-2 rounded-xl border border-[#eef1f6] bg-[#fafbfd] px-3 py-3 text-left text-sm text-[#344054] hover:border-[#3b6ea5]"
                          >
                            <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-[#3b6ea5]" />
                            {q}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </Card>

                  <Card id="research" className="p-6">
                    <SectionTitle
                      eyebrow="AGI moat"
                      title="Research highlights"
                      action={<Link to="/research" className="text-xs font-semibold text-[#1d4f91]">Open library →</Link>}
                    />
                    <div className="grid gap-3 sm:grid-cols-2">
                      {research.length ? research.map((article) => (
                        <Link
                          key={article.id || article.slug}
                          to={`/article/${article.slug}`}
                          className="rounded-2xl border border-[#eef1f6] p-4 transition hover:border-[#98a2b3]"
                        >
                          <Badge>{article.section || 'Research'}</Badge>
                          <h3 className="mt-3 text-sm font-semibold leading-snug text-[#101828]">{article.title}</h3>
                          <p className="mt-2 line-clamp-2 text-xs text-[#667085]">{article.excerpt}</p>
                          <p className="mt-3 inline-flex items-center gap-1 text-[11px] font-semibold text-[#1d4f91]">
                            Read note <ArrowRight className="h-3.5 w-3.5" />
                          </p>
                        </Link>
                      )) : (
                        <div className="rounded-2xl border border-dashed border-[#d0d5dd] p-6 text-sm text-[#667085] sm:col-span-2">
                          Publish Economy / Global / Policy notes in the CMS to populate this shelf.
                        </div>
                      )}
                    </div>
                  </Card>
                </section>

                <p className="pb-8 text-center text-[11px] leading-relaxed text-[#98a2b3]">
                  {briefing?.disclaimer}
                </p>
              </>
            )}
          </main>
        </div>
      </div>

      {/* Transmission node panel */}
      {nodePanel && (
        <div className="fixed inset-0 z-40 flex justify-end bg-black/20 p-3 sm:p-6" onClick={() => setNodePanel(null)}>
          <div
            className="h-full w-full max-w-md overflow-y-auto rounded-2xl border border-[#e7eaf0] bg-white p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#3b6ea5]">{nodePanel.kind}</p>
                <h3 className="mt-1 text-xl font-semibold text-[#101828]">{nodePanel.label}</h3>
              </div>
              <button type="button" onClick={() => setNodePanel(null)} className="rounded-lg p-1 hover:bg-[#f2f4f7]" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-[#475467]">
              AGI treats this node as part of the macro transmission engine. It answers what changed, why it matters, and which sectors absorb the shock.
            </p>
            {(transmission.maps || []).slice(0, 1).map((map) => (
              <div key={map.id} className="mt-5 rounded-xl border border-[#eef1f6] p-4">
                <p className="text-sm font-semibold">{map.title}</p>
                <p className="mt-1 text-xs text-[#667085]">{map.trigger}</p>
                <ul className="mt-3 space-y-1">
                  {(map.steps || []).map((step) => <li key={step} className="text-xs text-[#475467]">→ {step}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ask AGI panel */}
      {askOpen && askAnswer && (
        <div className="fixed inset-0 z-40 flex items-end justify-center bg-black/25 p-3 sm:items-center sm:p-6" onClick={() => setAskOpen(false)}>
          <div
            className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-[#e7eaf0] bg-white p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#3b6ea5]">Ask AGI Economist</p>
                <h3 className="mt-1 text-lg font-semibold text-[#101828]">{askAnswer.query}</h3>
              </div>
              <button type="button" onClick={() => setAskOpen(false)} className="rounded-lg p-1 hover:bg-[#f2f4f7]" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-4 rounded-xl bg-[#f8fafc] p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-[#3b6ea5]">AI response</p>
              <p className="mt-2 text-sm leading-7 text-[#344054]">{askLoading ? 'AGI Economist is analysing the current macro evidence…' : askAnswer.response}</p>
              <div className="mt-3"><Badge tone={statusTone(askAnswer.outlook)}>{askAnswer.outlook}</Badge></div>
              {!askLoading && askAnswer.source && <p className="mt-2 text-[11px] text-[#667085]">Answer source: {askAnswer.source}</p>}
            </div>
            <div className="mt-5">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-[#667085]">Evidence</p>
              <div className="mt-2 space-y-2">
                {(askAnswer.evidence || []).map((item) => (
                  <div key={item.title} className="rounded-xl border border-[#eef1f6] p-3">
                    <p className="text-sm font-semibold">{item.title}</p>
                    <p className="mt-1 text-xs text-[#667085]">{item.explanation}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-[#ecfdf3] bg-[#f6fef9] p-3">
                <p className="text-[11px] font-bold text-[#087443]">Related sectors — beneficiaries</p>
                <ul className="mt-2 space-y-1">
                  {(askAnswer.implications?.beneficiaries || []).map((item) => (
                    <li key={item.name} className="text-xs text-[#344054]">{item.name}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-xl border border-[#fff1f0] bg-[#fffafa] p-3">
                <p className="text-[11px] font-bold text-[#b42318]">Related sectors — headwinds</p>
                <ul className="mt-2 space-y-1">
                  {(askAnswer.implications?.challenged || []).map((item) => (
                    <li key={item.name} className="text-xs text-[#344054]">{item.name}</li>
                  ))}
                </ul>
              </div>
            </div>
            {(askAnswer.related || []).length > 0 && (
              <div className="mt-5">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-[#667085]">Related research questions</p>
                <ul className="mt-2 space-y-1">
                  {askAnswer.related.map((item) => (
                    <li key={item} className="text-xs text-[#475467]">• {item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
