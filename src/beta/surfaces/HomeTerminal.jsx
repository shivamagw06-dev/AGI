import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Loader2 } from 'lucide-react';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import {
  StorySection,
  InsightCard,
  OpportunityCard,
  RiskCard,
  CompanyCard,
  EmptyState,
} from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import { formatCountdown, getMarketSession, greetingForHour } from '@/beta/lib/marketClock';
import { buildStoryFromReport } from '@/beta/lib/reportStory';
import useMorningBrief from '@/hooks/useMorningBrief';
import useMarketDashboard from '@/hooks/useMarketDashboard';
import usePublishedArticles from '@/hooks/usePublishedArticles';
import useNifty500Research from '@/hooks/useNifty500Research';
import { getIntelligenceHealth, listResearchRuns, getResearchRun } from '@/lib/intelligenceApi';

export default function HomeTerminal() {
  const navigate = useNavigate();
  const { isExplain, isProfessional } = useBetaDepth();
  const { brief, loading: briefLoading } = useMorningBrief();
  const dash = useMarketDashboard();
  const { articles } = usePublishedArticles({ limit: 3 });
  const nifty = useNifty500Research();
  const [ask, setAsk] = useState('');
  const [now, setNow] = useState(() => new Date());
  const [cioRun, setCioRun] = useState(null);
  const [engineOk, setEngineOk] = useState(null);

  useEffect(() => {
    const t = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(t);
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const health = await getIntelligenceHealth();
        if (!active) return;
        setEngineOk(Boolean(health?.engine?.ok || health?.ok || health?.engineStatus === 200));
      } catch {
        if (active) setEngineOk(false);
      }
      try {
        const runs = await listResearchRuns({ limit: '8' });
        const list = Array.isArray(runs) ? runs : runs?.runs || [];
        const morning =
          list.find((r) => r.desk === 'cio_morning' && ['completed', 'partial'].includes(r.status)) ||
          list.find((r) => ['completed', 'partial'].includes(r.status));
        if (!morning?.run_id || !active) return;
        const full = await getResearchRun(morning.run_id);
        if (active) setCioRun(full);
      } catch {
        /* engine may be offline */
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const session = useMemo(() => getMarketSession(now), [now]);
  const countdown = formatCountdown(session.target, now);
  const greeting = greetingForHour(now);
  const story = buildStoryFromReport(cioRun?.report, { symbols: cioRun?.symbols || [] });

  const opportunities = story?.growth?.length
    ? story.growth
    : (dash.gainers || []).slice(0, 3).map((s) => `${s.symbol || s.name}: ${s.trend || 'in focus'}`);
  const risks = story?.risks?.length
    ? story.risks
    : (dash.losers || []).slice(0, 3).map((s) => `${s.symbol || s.name}: ${s.trend || 'watch'}`);

  const screenerPicks = (nifty?.topBullish || nifty?.leaders || nifty?.stocks || dash.stocksInFocus || []).slice(0, 4);

  const onAsk = (e) => {
    e.preventDefault();
    const q = ask.trim();
    navigate(q ? `/beta/copilot?q=${encodeURIComponent(q)}` : '/beta/copilot');
  };

  const briefBody =
    story?.summary ||
    brief?.excerpt ||
    'Your morning intelligence opens here — one clear view of what matters before the session.';

  return (
    <SurfaceChrome wide askPlaceholder="Ask what matters for today’s session…">
      {/* Hero: one composition — brand, one line, countdown, one CTA feel */}
      <section className="beta-hero">
        <div className="beta-hero-inner">
          <p className="beta-kicker beta-fade">Morning Intelligence</p>
          <h1 className="beta-display mt-4 beta-rise">AGI</h1>
          <p className="beta-lede mt-5 max-w-xl beta-rise-delay">
            Complex Markets. Simple Intelligence.
          </p>
          <p className="mt-8 text-[var(--beta-ink-soft)] beta-rise-delay-2">
            <span className="font-[family-name:var(--beta-serif)] text-xl">{greeting}, Shiv.</span>
            <span className="mx-2 text-[var(--beta-caption)]">·</span>
            <span>{session.label}</span>{' '}
            <span className="beta-countdown ml-1 font-[family-name:var(--beta-serif)] text-2xl font-semibold text-[var(--beta-navy)]">
              {countdown}
            </span>
          </p>
          <p className="beta-caption mt-4">
            {engineOk === false
              ? 'Engine offline — editorial + market context only.'
              : engineOk
                ? 'Live intelligence connected.'
                : 'Connecting…'}
          </p>
        </div>
      </section>

      <div className="beta-story-stack mt-4">
        <StorySection chapter="I." title="What do I need to know?">
          {briefLoading && !story ? (
            <div className="flex items-center gap-2 py-6 text-sm text-[var(--beta-muted)]">
              <Loader2 className="h-4 w-4 animate-spin" /> Opening the brief…
            </div>
          ) : (
            <InsightCard
              lede
              body={isExplain ? `${briefBody.slice(0, 240)}${briefBody.length > 240 ? '…' : ''}` : briefBody}
              meta={story?.stance || brief?.heroLabel || 'CIO Morning Brief'}
            >
              {!isExplain && (story?.takeaways || []).length > 0 && (
                <ul className="mt-6 max-w-xl space-y-3 text-[var(--beta-ink-soft)]">
                  {story.takeaways.slice(0, isProfessional ? 5 : 3).map((t) => (
                    <li key={t} className="flex gap-3">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--beta-navy)]" />
                      <span className="leading-relaxed">{t}</span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="mt-8 flex flex-wrap gap-3">
                <Link to="/beta/research" className="beta-btn">
                  Continue reading
                  <ArrowRight className="h-4 w-4" />
                </Link>
                {brief?.slug && (
                  <Link to={`/article/${brief.slug}`} className="beta-btn-ghost beta-btn">
                    Editorial brief
                  </Link>
                )}
              </div>
            </InsightCard>
          )}
        </StorySection>

        {!isExplain && (
          <StorySection chapter="II." title="The session climate">
            <div className="grid gap-8 sm:grid-cols-2">
              <div>
                <p className="beta-kicker">Pulse</p>
                <p className="mt-3 font-[family-name:var(--beta-serif)] text-2xl leading-snug text-[var(--beta-navy)]">
                  {dash.pulse || dash.summary || 'Awaiting open'}
                </p>
                <p className="beta-caption mt-3 max-w-sm">{dash.outlook || 'Outlook updates with live market intelligence.'}</p>
              </div>
              <div className="space-y-4">
                {(dash.sectors || []).slice(0, 3).map((s) => (
                  <div key={s.name || s.sector} className="flex items-baseline justify-between gap-4 border-t border-[var(--beta-border)] pt-3">
                    <p className="text-sm font-semibold text-[var(--beta-ink)]">{s.name || s.sector}</p>
                    <p className="beta-caption">{s.bias || s.trend || s.sentiment || '—'}</p>
                  </div>
                ))}
                {!(dash.sectors || []).length && (
                  <EmptyState title="Sector climate quiet" detail="Leadership names appear when market intelligence loads." />
                )}
              </div>
            </div>
            <Link to="/beta/macro" className="mt-8 inline-flex text-sm font-semibold text-[var(--beta-navy)] hover:underline">
              Open macro weather →
            </Link>
          </StorySection>
        )}

        <div className="grid gap-12 lg:grid-cols-2">
          <StorySection chapter="III." title="Opportunities">
            {opportunities.length ? (
              opportunities.slice(0, isExplain ? 2 : 4).map((item) => (
                <OpportunityCard key={item} title={typeof item === 'string' ? item : item.title} />
              ))
            ) : (
              <EmptyState title="No catalysts yet" detail="They appear from CIO briefs or market focus." />
            )}
          </StorySection>
          <StorySection chapter="IV." title="Risks">
            {risks.length ? (
              <div className="space-y-3">
                {risks.slice(0, isExplain ? 2 : 4).map((item) => (
                  <RiskCard key={item} title="Watch" items={[typeof item === 'string' ? item : item.title]} level="stated" />
                ))}
              </div>
            ) : (
              <EmptyState title="No risks listed yet" />
            )}
          </StorySection>
        </div>

        <StorySection chapter="V." title="Names worth opening">
          {screenerPicks.length ? (
            <div className="grid gap-4 sm:grid-cols-2">
              {screenerPicks.slice(0, isExplain ? 2 : 4).map((row) => {
                const symbol = row.symbol || row.ticker || row.name;
                return (
                  <CompanyCard
                    key={symbol}
                    symbol={symbol}
                    stance={row.overallSentiment || row.trend || row.sentiment}
                    confidence={row.agiResearchScore || row.aiConfidencePercent}
                    why={[row.researchSummary || row.reason || row.note].filter(Boolean)}
                    onOpen={() => navigate(`/beta/companies/${encodeURIComponent(symbol)}`)}
                  />
                );
              })}
            </div>
          ) : (
            <EmptyState title="No picks yet" detail="Interesting companies appear from Nifty research or market focus." />
          )}
          <button type="button" className="beta-btn mt-8" onClick={() => navigate('/beta/screener')}>
            See all interesting names
          </button>
        </StorySection>

        {!isExplain && (articles || []).length > 0 && (
          <StorySection chapter="VI." title="From the library">
            <div className="space-y-0">
              {(articles || []).slice(0, isProfessional ? 3 : 2).map((a) => (
                <Link
                  key={a.id || a.slug}
                  to={a.slug ? `/article/${a.slug}` : '/research'}
                  className="block border-t border-[var(--beta-border)] py-5 transition-colors hover:bg-white/40"
                >
                  <p className="beta-caption">{a.section || 'Research'}</p>
                  <p className="mt-1 font-[family-name:var(--beta-serif)] text-xl text-[var(--beta-ink)]">{a.title}</p>
                </Link>
              ))}
            </div>
          </StorySection>
        )}

        <StorySection chapter="VII." title="Ask AGI">
          <form onSubmit={onAsk} className="max-w-2xl">
            <p className="beta-lede">One question can turn the morning into a decision.</p>
            <textarea
              className="beta-textarea mt-6"
              value={ask}
              onChange={(e) => setAsk(e.target.value)}
              placeholder="How will lower oil prices affect Indian paint companies?"
            />
            <button type="submit" className="beta-btn mt-4">
              Ask
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>
        </StorySection>
      </div>
    </SurfaceChrome>
  );
}
