import { useEffect, useMemo, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Clock3, Loader2, Search } from 'lucide-react';
import OfficeNav from '@/office/OfficeNav';
import Sparkline from '@/office/Sparkline';
import { getUiAutocomplete, getUiHome } from '@/lib/uiApi';
import { getInvestmentOfficeDashboard } from '@/lib/intelligenceApi';
import { useAuth } from '@/contexts/AuthContext';
import { trackProductEvent } from '@/lib/productAnalytics';
import { resolveInitialHome, writeHomeCache } from '@/office/homeDeskFallback';
import '@/office/theme.css';

function greetingForHour(date = new Date()) {
  const h = date.getHours();
  if (h < 12) return 'Good Morning';
  if (h < 17) return 'Good Afternoon';
  return 'Good Evening';
}

function fmtPct(v) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

function fmtPrice(v) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  if (n >= 1000) return n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  return n.toLocaleString('en-IN', { maximumFractionDigits: 4 });
}

function SectionHead({ title, subtitle, href, linkLabel = 'Open →' }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-3">
      <div>
        <h2 className="io-title text-xl">{title}</h2>
        {subtitle && <p className="mt-1 text-xs text-[var(--io-muted)]">{subtitle}</p>}
      </div>
      {href && (
        <Link to={href} className="text-xs font-semibold text-[var(--io-gold)] hover:underline">
          {linkLabel}
        </Link>
      )}
    </div>
  );
}

function AskHero({ placeholder, chips, inputRef }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setSuggestions(null);
      return undefined;
    }
    let alive = true;
    const t = window.setTimeout(async () => {
      try {
        const data = await getUiAutocomplete(q);
        if (alive) setSuggestions(data);
      } catch {
        if (alive) setSuggestions(null);
      }
    }, 160);
    return () => {
      alive = false;
      window.clearTimeout(t);
    };
  }, [query]);

  const submit = (raw) => {
    const q = String(raw || query).trim();
    if (!q) return;
    setLoading(true);
    trackProductEvent('question_asked', { question: q, surface: 'office_home' });
    navigate(`/ask?q=${encodeURIComponent(q)}`);
  };

  const groups = [
    { key: 'questions', label: 'Questions', items: suggestions?.questions },
    { key: 'companies', label: 'Companies', items: suggestions?.companies },
    { key: 'themes', label: 'Themes', items: suggestions?.themes },
    { key: 'sectors', label: 'Sectors', items: suggestions?.sectors },
    { key: 'articles', label: 'Articles', items: suggestions?.articles },
  ];

  return (
    <div className="io-card p-5 md:p-7 h-full flex flex-col">
      <p className="io-kicker">Flagship</p>
      <h2 className="io-title mt-2 text-3xl md:text-4xl">Ask AGI</h2>
      <p className="mt-2 text-sm text-[var(--io-muted)]">
        Institutional answer experience — house view, evidence, what changed, what to explore next.
      </p>

      <form
        className="relative mt-6"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[var(--io-muted)]" />
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder={placeholder}
          className="w-full rounded-2xl border border-[var(--io-border-strong)] bg-[rgba(255,255,255,0.03)] py-4 pl-12 pr-28 text-[15px] text-[var(--io-ink)] outline-none transition focus:border-[var(--io-gold)]"
        />
        <button
          type="submit"
          disabled={loading}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-xl bg-[var(--io-gold)] px-4 py-2.5 text-xs font-bold text-[#16120a] hover:brightness-110 disabled:opacity-70"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Ask AGI'}
        </button>

        {open && (query.trim() || (suggestions && groups.some((g) => (g.items || []).length))) && (
          <div className="absolute z-30 mt-2 max-h-[50vh] w-full overflow-y-auto rounded-2xl border border-[var(--io-border)] bg-[var(--io-bg-elevated)] shadow-2xl">
            {groups.map(
              (g) =>
                (g.items || []).length > 0 && (
                  <div key={g.key} className="border-b border-[var(--io-border)] p-2">
                    <p className="px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-[var(--io-caption)]">
                      {g.label}
                    </p>
                    {g.items.map((item) => (
                      <button
                        key={`${g.key}-${item.id || item.label}`}
                        type="button"
                        className="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-[var(--io-surface)]"
                        onClick={() => {
                          if (g.key === 'companies') {
                            navigate(`/research/stocks/${encodeURIComponent(item.id || item.label)}`);
                            return;
                          }
                          if (g.key === 'themes') {
                            navigate(`/themes/${encodeURIComponent(item.id || item.label)}`);
                            return;
                          }
                          if (g.key === 'sectors') {
                            navigate(`/sectors/${encodeURIComponent(item.id || item.label)}`);
                            return;
                          }
                          submit(item.label || item.id);
                        }}
                      >
                        <span className="font-semibold text-[var(--io-ink)]">{item.label}</span>
                        {item.reason && (
                          <span className="mt-0.5 block text-[11px] text-[var(--io-muted)]">{item.reason}</span>
                        )}
                      </button>
                    ))}
                  </div>
                )
            )}
          </div>
        )}
      </form>

      <div className="mt-5 flex flex-wrap gap-2">
        {(chips || []).slice(0, 6).map((chip) => (
          <button key={chip} type="button" className="io-chip" onClick={() => submit(chip)}>
            {chip}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function InvestmentOfficeHome() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const searchRef = useRef(null);
  const initial = useMemo(() => resolveInitialHome(), []);
  const [state, setState] = useState({
    loading: true,
    data: initial.data,
    error: null,
    source: initial.source,
  });
  const [ioDesk, setIoDesk] = useState(null);
  const [dashTab, setDashTab] = useState('Heatmap');

  useEffect(() => {
    let alive = true;
    let cycleTimer = null;
    trackProductEvent('session_start', { surface: 'investment_office_home' });

    // Progressive: priority desks already painted from cache/fallback; upgrade live.
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 12_000);

    const loadHome = () =>
      getUiHome()
        .then((data) => {
          if (!alive || !data) return;
          writeHomeCache(data);
          const source = data?.meta?.source || (data?.meta?.fallback_used ? 'market_api' : 'live');
          setState({ loading: false, data, error: null, source });
          if (data?.investment_office?.enabled) setIoDesk(data.investment_office);
        })
        .catch((error) => {
          if (!alive) return;
          // Keep cache/desk data — never wipe widgets blank.
          setState((prev) => ({
            loading: false,
            data: prev.data || initial.data,
            error,
            source: prev.source || initial.source,
          }));
        });

    loadHome().finally(() => {
      window.clearTimeout(timer);
    });

    getInvestmentOfficeDashboard()
      .then((desk) => {
        if (alive && desk?.enabled) setIoDesk(desk);
      })
      .catch(() => {});

    // Refresh homepage market snapshot on the shared 30-min wall-clock cycle.
    const scheduleHomeCycle = async () => {
      try {
        const { msUntilNextMarketCycle } = await import('@/lib/marketCache');
        const wait = Math.max(250, msUntilNextMarketCycle());
        cycleTimer = window.setTimeout(async () => {
          if (!alive) return;
          await loadHome();
          if (alive) scheduleHomeCycle();
        }, wait);
      } catch {
        /* soft */
      }
    };
    scheduleHomeCycle();

    return () => {
      alive = false;
      window.clearTimeout(timer);
      if (cycleTimer) window.clearTimeout(cycleTimer);
      controller.abort();
    };
  }, [initial.data, initial.source]);

  const data = state.data;
  const firstName =
    user?.user_metadata?.full_name?.split?.(' ')?.[0] ||
    user?.email?.split('@')?.[0] ||
    'Shiv';
  const greeting = `${greetingForHour()}, ${firstName}.`;
  const cards = data?.morning_intelligence?.cards || [];
  const questions = (data?.popular_questions || []).slice(0, 12);
  const featured = data?.featured_research || data?.feeds?.latest_research || [];
  const themes = data?.market_themes || data?.feeds?.trending_themes || [];
  const companies = data?.top_companies || data?.feeds?.trending_companies || [];
  const calendar = data?.economic_calendar || [];
  const feed = data?.knowledge_feed || [];
  const predictions = data?.feeds?.latest_predictions || [];
  const snapshot = data?.market_snapshot || [];
  const session = data?.market_session || {};
  const metrics = data?.footer_metrics || {};
  const dashboard = data?.market_dashboard || {};
  const newsletter = data?.newsletter || {};
  const sessionLabel =
    session.updated_label ||
    session.time_remaining ||
    (state.source !== 'live' ? 'Updated 17 mins ago' : '—');
  const chips =
    data?.example_questions?.length
      ? data.example_questions
      : [
          'Should I buy ICICI Bank?',
          'What changed after RBI?',
          'Best defence companies',
          'AI Theme Outlook',
          'Why is Nifty falling?',
          'Latest Tata Motors outlook?',
        ];

  const focusSearch = () => {
    searchRef.current?.focus();
    searchRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const heatmap = useMemo(() => dashboard.heatmap || [], [dashboard.heatmap]);

  return (
    <div className="agi-office">
      <Helmet>
        <title>AGI Investment Office — What should an investor know right now?</title>
        <meta
          name="description"
          content="Live institutional investment office homepage — house view, Ask AGI, research, themes, predictions and market intelligence."
        />
        <link rel="canonical" href="https://agarwalglobalinvestments.com/" />
        <meta property="og:title" content="AGI Investment Office" />
        <meta property="og:description" content="Premium institutional research platform — Ask AGI and live market intelligence." />
      </Helmet>

      <OfficeNav onFocusSearch={focusSearch} />

      <main className="io-shell py-6 md:py-8 space-y-8 md:space-y-10">
        {/* SECTION 1 — HERO */}
        <section className="grid grid-cols-1 gap-4 xl:grid-cols-12 io-rise">
          {/* LEFT — Morning Intelligence */}
          <div className="xl:col-span-3 io-card p-5 md:p-6">
            <p className="io-kicker">Morning Intelligence</p>
            <h1 className="io-title mt-3 text-2xl leading-tight">{greeting}</h1>
            <p className="mt-2 text-sm text-[var(--io-ink-soft)]">
              {data?.morning_intelligence?.greeting_line ||
                "Here's what the AGI Investment Office believes today."}
            </p>
            <div className="mt-5 grid grid-cols-1 gap-2.5 sm:grid-cols-2 xl:grid-cols-1">
              {state.loading && !cards.length
                ? [1, 2, 3, 4, 5, 6].map((i) => <div key={i} className="io-skeleton h-16" />)
                : cards.map((card) => (
                    <div
                      key={card.id}
                      className="rounded-[var(--io-radius-sm)] border border-[var(--io-border)] bg-[rgba(255,255,255,0.02)] p-3"
                    >
                      <p className="text-[10px] font-bold uppercase tracking-wide text-[var(--io-caption)]">
                        {card.label}
                      </p>
                      <p className="mt-1 text-sm font-semibold text-[var(--io-ink)] line-clamp-3">
                        {card.value}
                      </p>
                    </div>
                  ))}
            </div>
          </div>

          {/* CENTER — Ask AGI */}
          <div className="xl:col-span-5">
            <AskHero
              placeholder={data?.ask_placeholder}
              chips={chips}
              inputRef={searchRef}
            />
          </div>

          {/* RIGHT — Market Snapshot */}
          <div className="xl:col-span-4 io-card p-5 md:p-6">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="io-kicker">Market Snapshot</p>
                <h2 className="io-title mt-2 text-2xl">Live markets</h2>
              </div>
              <div className="text-right">
                <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--io-gold)]">
                  {session.label || 'Session'}
                </p>
                <p className="mt-1 text-[11px] text-[var(--io-muted)] flex items-center gap-1 justify-end">
                  <Clock3 className="h-3 w-3" />
                  {sessionLabel}
                </p>
              </div>
            </div>

            <div className="mt-4 max-h-[420px] space-y-2 overflow-y-auto pr-1">
              {state.loading && !snapshot.length &&
                [1, 2, 3, 4, 5, 6].map((i) => <div key={i} className="io-skeleton h-14" />)}
              {snapshot.map((row) => {
                  const up = Number(row.percentChange) >= 0;
                  return (
                    <div
                      key={row.name}
                      className="flex items-center justify-between gap-3 rounded-[var(--io-radius-sm)] border border-[var(--io-border)] px-3 py-2.5"
                    >
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-[var(--io-ink)]">{row.name}</p>
                        <p className="text-[11px] text-[var(--io-muted)]">{fmtPrice(row.price)}</p>
                      </div>
                      <Sparkline points={row.sparkline} up={up} />
                      <p className={`text-xs font-bold tabular-nums ${up ? 'io-up' : 'io-down'}`}>
                        {fmtPct(row.percentChange)}
                      </p>
                    </div>
                  );
                })}
            </div>

            <Link
              to="/market-intelligence"
              className="mt-4 inline-flex items-center gap-2 text-xs font-bold text-[var(--io-gold)] hover:underline"
            >
              Go To Market Dashboard <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </section>

        {/* SECTION 2 — Popular Investor Questions */}
        <section className="io-fade">
          <SectionHead
            title="Popular Investor Questions"
            subtitle="Generated from macro, research, calendar, themes and latest AGI notes"
            href="/ask"
            linkLabel="Ask AGI →"
          />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {state.loading && !questions.length
              ? [1, 2, 3, 4, 5, 6, 7, 8].map((i) => <div key={i} className="io-skeleton h-24" />)
              : questions.map((row) => {
                  const q = row.question || row.label || row;
                  return (
                    <button
                      key={q}
                      type="button"
                      onClick={() => navigate(`/ask?q=${encodeURIComponent(q)}`)}
                      className="io-card p-4 text-left"
                    >
                      <p className="text-sm font-semibold leading-snug text-[var(--io-ink)]">{q}</p>
                      {row.reason && (
                        <p className="mt-2 text-[11px] text-[var(--io-muted)] line-clamp-2">{row.reason}</p>
                      )}
                    </button>
                  );
                })}
          </div>
        </section>

        {/* SECTION 3 — Four column grid */}
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-4">
          <div className="io-card p-5">
            <SectionHead title="Featured Research" href="/research" />
            <div className="space-y-3">
              {(featured || []).slice(0, 4).map((r) => (
                <Link
                  key={r.id || r.title}
                  to={r.href || (r.id ? `/article/${encodeURIComponent(r.id)}` : '/research')}
                  className="block rounded-[var(--io-radius-sm)] border border-[var(--io-border)] p-3 hover:border-[var(--io-border-strong)]"
                >
                  <p className="text-[10px] font-bold uppercase tracking-wide text-[var(--io-gold)]">
                    {r.category || 'Research'}
                  </p>
                  <p className="mt-1 text-sm font-semibold text-[var(--io-ink)] line-clamp-2">
                    {r.title}
                  </p>
                  {r.summary && (
                    <p className="mt-1 text-[11px] text-[var(--io-muted)] line-clamp-2">{r.summary}</p>
                  )}
                  <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-[var(--io-muted)]">
                    <span>{r.read_time || '5 min'}</span>
                    <span>·</span>
                    <span>{r.house_view || 'House view'}</span>
                    {r.as_of && (
                      <>
                        <span>·</span>
                        <span>{String(r.as_of).slice(0, 10)}</span>
                      </>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </div>

          <div className="io-card p-5">
            <SectionHead title="Market Dashboard" href="/market-intelligence" />
            <div className="mb-3 flex flex-wrap gap-1.5">
              {(dashboard.tabs || ['Heatmap', 'Breadth', 'Flows', 'Market Health']).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setDashTab(tab)}
                  className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                    dashTab === tab
                      ? 'bg-[var(--io-gold-soft)] text-[var(--io-gold)]'
                      : 'text-[var(--io-muted)] hover:text-[var(--io-ink)]'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
            {dashTab === 'Heatmap' && (
              <div className="space-y-2">
                {heatmap.slice(0, 8).map((row) => (
                  <div key={row.name} className="flex items-center justify-between border-b border-[var(--io-border)] py-2 text-sm">
                    <span className="font-semibold">{row.name}</span>
                    <span className="text-[var(--io-muted)]">{row.bias || 'Watch'}</span>
                  </div>
                ))}
              </div>
            )}
            {dashTab === 'Breadth' && (
              <div className="space-y-3 text-sm">
                <p>Coverage names: <span className="font-bold">{dashboard.breadth?.coverage ?? '—'}</span></p>
                <p>Advancers: <span className="font-bold">{dashboard.breadth?.advancers ?? '—'}</span></p>
                <p>Decliners: <span className="font-bold">{dashboard.breadth?.declining ?? '—'}</span></p>
                <p className="text-[var(--io-muted)]">Regime: {dashboard.breadth?.label || '—'}</p>
              </div>
            )}
            {dashTab === 'Flows' && (
              <div className="space-y-2 text-sm">
                <p>FII: <span className="font-bold">{dashboard.flows?.fii || 'Mixed'}</span></p>
                <p>DII: <span className="font-bold">{dashboard.flows?.dii || 'Supportive'}</span></p>
                <p className="text-[var(--io-ink-soft)]">
                  {dashboard.flows?.note || 'Institutional flow context updates with portfolio coverage.'}
                </p>
              </div>
            )}
            {dashTab === 'Market Health' && (
              <div className="space-y-2 text-sm">
                <p>Regime: <span className="font-bold">{dashboard.market_health?.regime || '—'}</span></p>
                <p>Risk: <span className="font-bold">{dashboard.market_health?.risk || '—'}</span></p>
                <p>Platform: <span className="font-bold capitalize">{dashboard.market_health?.platform || '—'}</span></p>
              </div>
            )}
          </div>

          <div className="io-card p-5">
            <SectionHead title="Trending Themes" href="/themes/credit_growth" />
            <div className="space-y-2">
              {themes.slice(0, 7).map((t) => {
                const id = t.id || t.name;
                const conf = t.confidence ?? t.score;
                return (
                  <Link
                    key={id}
                    to={`/themes/${encodeURIComponent(id)}`}
                    className="flex items-center justify-between gap-3 rounded-[var(--io-radius-sm)] border border-[var(--io-border)] px-3 py-2.5 hover:border-[var(--io-border-strong)]"
                  >
                    <div>
                      <p className="text-sm font-semibold">{t.name || t.id}</p>
                      <p className="text-[11px] text-[var(--io-muted)]">
                        {t.bias || t.trend || 'Trend forming'}
                        {conf != null ? ` · conf ${Number(conf) <= 1 ? `${Math.round(Number(conf) * 100)}%` : conf}` : ''}
                        {(t.related_companies || t.tickers)?.length
                          ? ` · ${(t.related_companies || t.tickers).slice(0, 2).join(', ')}`
                          : ''}
                      </p>
                    </div>
                    <Sparkline points={[40, 42, 41, 45, 48, 47, 50]} up />
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="io-card p-5">
            <SectionHead title="Top Companies" href="/portfolio" />
            <div className="space-y-2">
              {companies.slice(0, 8).map((row) => (
                <Link
                  key={row.ticker}
                  to={`/research/stocks/${encodeURIComponent(row.ticker)}`}
                  className="flex items-center justify-between rounded-[var(--io-radius-sm)] border border-[var(--io-border)] px-3 py-2.5 hover:border-[var(--io-border-strong)]"
                >
                  <div>
                    <p className="text-sm font-bold">{row.ticker}</p>
                    <p className="text-[11px] text-[var(--io-muted)]">
                      {row.label || 'Under review'}
                      {row.sector ? ` · ${row.sector}` : ''}
                    </p>
                  </div>
                  <p className="text-[11px] font-semibold text-[var(--io-gold)]">
                    {row.confidence != null
                      ? `${Math.round(Number(row.confidence) * (Number(row.confidence) <= 1 ? 100 : 1))}%`
                      : 'Open'}
                  </p>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* SECTION 4 — Four column grid */}
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-4">
          <div className="io-card p-5">
            <SectionHead title="Economic Calendar" href="/macro-intelligence" linkLabel="Open Calendar →" />
            <ul className="space-y-2">
              {calendar.slice(0, 6).map((e, idx) => (
                <li key={e.id || e.title || idx} className="border-b border-[var(--io-border)] pb-2">
                  <p className="text-sm font-semibold">{e.title || e.name}</p>
                  <p className="text-[11px] text-[var(--io-muted)]">
                    {(e.when || e.country || e.region || 'IN') +
                      (e.importance ? ` · ${e.importance}` : '') +
                      (e.as_of || e.date ? ` · ${String(e.as_of || e.date).slice(0, 10)}` : '')}
                  </p>
                  {(e.expected_impact || e.affected_sectors?.length) && (
                    <p className="mt-1 text-[11px] text-[var(--io-ink-soft)] line-clamp-2">
                      {e.expected_impact ||
                        `Affects ${(e.affected_sectors || []).slice(0, 3).join(', ')}`}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div className="io-card p-5">
            <SectionHead title="Knowledge Feed" href="/research" />
            <ul className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
              {feed.slice(0, 10).map((item, idx) => (
                <li key={`${item.title}-${idx}`}>
                  <Link
                    to={item.href || '/research'}
                    className="block rounded-[var(--io-radius-sm)] border border-[var(--io-border)] px-3 py-2.5 hover:border-[var(--io-border-strong)]"
                  >
                    <p className="text-[10px] font-bold uppercase tracking-wide text-[var(--io-caption)]">
                      {item.type || 'update'}
                    </p>
                    <p className="mt-1 text-sm font-semibold line-clamp-2">{item.title}</p>
                    <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                      {item.as_of ? String(item.as_of).slice(0, 16).replace('T', ' ') : 'Just now'}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="io-card p-5">
            <SectionHead title="Latest Predictions" href="/predictions" linkLabel="Open Prediction →" />
            <div className="space-y-2">
              {predictions.slice(0, 5).map((p) => (
                <Link
                  key={p.id}
                  to={p.ticker ? `/research/stocks/${encodeURIComponent(p.ticker)}` : '/predictions'}
                  className="block rounded-[var(--io-radius-sm)] border border-[var(--io-border)] px-3 py-2.5 hover:border-[var(--io-border-strong)]"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-bold">{p.ticker || 'Prediction'}</p>
                    <span className="text-[10px] font-bold uppercase text-[var(--io-gold)]">
                      {p.current_status || 'open'}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-[var(--io-ink-soft)] line-clamp-2">{p.thesis}</p>
                  <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                    {p.target_horizon || 'medium-term'}
                    {p.confidence != null
                      ? ` · ${Math.round(Number(p.confidence) * (Number(p.confidence) <= 1 ? 100 : 1))}%`
                      : ''}
                    {p.current_return ? ` · ${p.current_return}` : ''}
                  </p>
                </Link>
              ))}
            </div>
          </div>

          <div className="io-card p-5 relative overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(500px_200px_at_80%_0%,rgba(201,162,39,0.14),transparent_60%)]" />
            <div className="relative">
              <p className="io-kicker">Newsletter</p>
              <h3 className="io-title mt-2 text-2xl">Stay Ahead with AGI</h3>
              <p className="mt-2 text-sm text-[var(--io-ink-soft)]">
                Institutional research, morning intelligence and weekly reports — delivered to your desk.
              </p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-[var(--io-muted)]">
                <p>Subscribers <span className="font-semibold text-[var(--io-ink)]">{newsletter.subscribers || '12.4k'}</span></p>
                <p>Research <span className="font-semibold text-[var(--io-ink)]">{newsletter.research_published || metrics.research_articles || '—'}</span></p>
                <p>Last <span className="font-semibold text-[var(--io-ink)]">{newsletter.last_newsletter || 'AGI Weekly'}</span></p>
                <p>Next <span className="font-semibold text-[var(--io-ink)]">{newsletter.next_release || 'Sunday 08:00 IST'}</span></p>
              </div>
              <form
                className="mt-5 space-y-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  trackProductEvent('subscription_conversion', { surface: 'office_home' });
                  navigate('/workspace');
                }}
              >
                <input
                  type="email"
                  required
                  placeholder="you@institution.com"
                  className="w-full rounded-xl border border-[var(--io-border)] bg-[rgba(255,255,255,0.03)] px-3 py-2.5 text-sm outline-none focus:border-[var(--io-gold)]"
                />
                <button
                  type="submit"
                  className="w-full rounded-xl bg-[var(--io-gold)] py-2.5 text-xs font-bold text-[#16120a] hover:brightness-110"
                >
                  Subscribe to AGI Intelligence
                </button>
              </form>
            </div>
          </div>
        </section>

        {/* Investment Office V1 — operating cockpit (aggregate of CMS / CA / Academy / IOC) */}
        {ioDesk?.enabled ? (
          <section className="space-y-4">
            <SectionHead
              title="Investment Office Desk"
              subtitle="What happened · what changed · what needs attention · what to write"
              href="/admin/investment-office"
              linkLabel="Admin →"
            />
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-4">
              <div className="io-card p-5">
                <p className="io-kicker">Attention</p>
                <h3 className="io-title mt-2 text-xl">Companies requiring attention</h3>
                <ul className="mt-3 space-y-2 max-h-64 overflow-y-auto">
                  {(ioDesk.companies_requiring_attention || []).slice(0, 8).map((row) => (
                    <li key={row.ticker} className="border-b border-[var(--io-border)] pb-2">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-bold">{row.ticker}</p>
                        <span className="text-[10px] font-bold uppercase text-[var(--io-gold)]">{row.priority}</span>
                      </div>
                      <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                        {(row.reasons || []).join(' · ') || 'Monitor signal'}
                      </p>
                    </li>
                  ))}
                  {!(ioDesk.companies_requiring_attention || []).length ? (
                    <li className="text-sm text-[var(--io-muted)]">Queue clear — institutional monitor nominal.</li>
                  ) : null}
                </ul>
              </div>

              <div className="io-card p-5">
                <p className="io-kicker">Research queue</p>
                <h3 className="io-title mt-2 text-xl">Today&apos;s analyst work</h3>
                <ul className="mt-3 space-y-2 max-h-64 overflow-y-auto">
                  {(ioDesk.todays_research_queue || []).slice(0, 8).map((task) => (
                    <li key={task.id} className="border-b border-[var(--io-border)] pb-2">
                      <p className="text-sm font-semibold">{task.title}</p>
                      <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                        {task.priority} · {task.estimated_effort} · {task.suggested_owner}
                      </p>
                      <p className="mt-1 text-[11px] text-[var(--io-ink-soft)] line-clamp-2">{task.reason}</p>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="io-card p-5">
                <p className="io-kicker">Knowledge growth</p>
                <h3 className="io-title mt-2 text-xl">What AGI learned</h3>
                <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                  {[
                    ['Books', ioDesk.knowledge_growth?.books_learned],
                    ['Concepts', ioDesk.knowledge_growth?.concepts_added],
                    ['Frameworks', ioDesk.knowledge_growth?.frameworks_added],
                    ['Monitored', ioDesk.knowledge_growth?.companies_updated],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-[var(--io-radius-sm)] border border-[var(--io-border)] p-3">
                      <p className="text-[10px] font-bold uppercase text-[var(--io-caption)]">{label}</p>
                      <p className="mt-1 text-lg font-semibold tabular-nums">{value ?? '—'}</p>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-[11px] text-[var(--io-muted)]">
                  Coverage {(ioDesk.coverage_dashboard || {}).coverage_pct ?? '—'}% · IOC{' '}
                  {(ioDesk.system_health || {}).overall || '—'}
                </p>
              </div>

              <div className="io-card p-5">
                <p className="io-kicker">Executive Copilot</p>
                <h3 className="io-title mt-2 text-xl">Ask the desk</h3>
                <ul className="mt-3 space-y-2">
                  {((ioDesk.executive_copilot || {}).prompts || []).slice(0, 6).map((prompt) => (
                    <li key={prompt}>
                      <button
                        type="button"
                        onClick={() => navigate(`/ask?q=${encodeURIComponent(prompt)}`)}
                        className="w-full rounded-[var(--io-radius-sm)] border border-[var(--io-border)] px-3 py-2 text-left text-xs font-semibold text-[var(--io-ink)] hover:border-[var(--io-gold)]"
                      >
                        {prompt}
                      </button>
                      {(ioDesk.executive_copilot || {}).answers?.[prompt] ? (
                        <p className="mt-1 px-1 text-[11px] text-[var(--io-muted)] line-clamp-2">
                          {ioDesk.executive_copilot.answers[prompt]}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="io-card p-5">
                <SectionHead title="Risk Centre" subtitle="Critical / high alerts from Company Monitor + IOC" />
                <ul className="space-y-2 max-h-48 overflow-y-auto">
                  {[
                    ...((ioDesk.risk_centre || {}).critical_alerts || []),
                    ...((ioDesk.risk_centre || {}).high_alerts || []),
                  ]
                    .slice(0, 8)
                    .map((a, idx) => (
                      <li key={`${a.ticker}-${idx}`} className="text-sm text-[var(--io-ink-soft)]">
                        <span className="font-bold text-[var(--io-ink)]">{a.ticker}</span> · {a.significance} —{' '}
                        {a.detail || a.change_type}
                      </li>
                    ))}
                  {!((ioDesk.risk_centre || {}).critical_alerts || []).length &&
                  !((ioDesk.risk_centre || {}).high_alerts || []).length ? (
                    <li className="text-sm text-[var(--io-muted)]">No high/critical monitor alerts.</li>
                  ) : null}
                </ul>
              </div>
              <div className="io-card p-5">
                <SectionHead title="Notifications" subtitle="Coverage · predictions · house-view · system" />
                <ul className="space-y-2 max-h-48 overflow-y-auto">
                  {(ioDesk.notifications || []).slice(0, 8).map((n, idx) => (
                    <li key={`${n.type}-${idx}`} className="text-sm">
                      <span className="text-[10px] font-bold uppercase text-[var(--io-gold)]">{n.type}</span>
                      <p className="text-[var(--io-ink-soft)]">
                        {n.ticker ? `${n.ticker}: ` : ''}
                        {n.message}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        ) : null}

        {/* FOOTER METRICS */}
        <section className="io-card p-5 md:p-6">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
            {[
              ['Research Coverage', metrics.research_coverage],
              ['Companies Covered', metrics.companies_covered],
              ['Predictions', metrics.predictions],
              ['Research Articles', metrics.research_articles],
              ['Knowledge Nodes', metrics.knowledge_nodes || metrics.knowledge_documents],
              ['Themes', metrics.themes || metrics.data_points],
              ['Research Since', metrics.research_since],
            ].map(([label, value]) => (
              <div key={label} className="rounded-[var(--io-radius-sm)] border border-[var(--io-border)] p-3">
                <p className="text-[10px] font-bold uppercase tracking-wide text-[var(--io-caption)]">{label}</p>
                <p className="mt-2 text-xl font-semibold tabular-nums text-[var(--io-ink)]">
                  {value ?? (state.loading ? '…' : '—')}
                </p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
