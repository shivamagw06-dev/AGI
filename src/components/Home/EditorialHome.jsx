import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { ChevronRight } from 'lucide-react';
import MorningBriefHero from '@/components/Home/MorningBriefHero';
import PopularInvestorQuestions from '@/components/Home/PopularInvestorQuestions';
import TodayDashboard from '@/components/Home/TodayDashboard';
import IndexSentimentTicker from '@/components/Home/IndexSentimentTicker';
import HomeIntelligenceStrip from '@/components/Home/HomeIntelligenceStrip';
import ResearchNotesPreview from '@/components/Home/ResearchNotesPreview';
import NewsHeadlineBar from '@/components/Home/NewsHeadlineBar';
import Nifty500ResearchPreview from '@/components/Home/Nifty500ResearchPreview';
import IpoMonitorPreview from '@/components/Home/IpoMonitorPreview';
import InstitutionalResearchCard from '@/components/Home/InstitutionalResearchCard';
import NewsletterSection from '@/components/Home/NewsletterSection';
import usePublishedArticles from '@/hooks/usePublishedArticles';
import useUiHome from '@/hooks/useUiHome';
import { MARKET_UPDATE_SECTIONS, SECTOR_RESEARCH } from '@/config/sectors';
import { formatTimeAgo } from '@/lib/articleUtils';
import { trackProductEvent } from '@/lib/productAnalytics';
import { useAuth } from '@/contexts/AuthContext';
import { firstNameFromUser, greetingForNow } from '@/lib/authValidation';
import { hasPin } from '@/lib/devicePin';
import { useEffect } from 'react';

function SectionHeader({ title, subtitle, href, linkLabel = 'View all →' }) {
  return (
    <div className="flex items-end justify-between mb-5 pb-3 border-b border-[#eeeeee]">
      <div>
        <h2 className="text-lg font-bold text-[#111111]">{title}</h2>
        {subtitle && <p className="text-xs text-[#767676] mt-1">{subtitle}</p>}
      </div>
      {href && (
        <Link to={href} className="text-xs font-bold text-[#111111] hover:text-[#ff6600] shrink-0">
          {linkLabel}
        </Link>
      )}
    </div>
  );
}

function MarketUpdateStrip({ section, articles, loading }) {
  const latest = articles[0];
  return (
    <div className="border border-[#dddddd] p-4 hover:border-[#999] transition-colors">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-[#111111]">{section.title}</h3>
        <Link
          to={section.path}
          className="text-[#ccc] hover:text-[#ff6600] transition-colors"
          aria-label={`View ${section.title}`}
        >
          <ChevronRight className="w-4 h-4" />
        </Link>
      </div>
      {loading ? (
        <div className="h-16 bg-[#eee] animate-pulse" />
      ) : latest ? (
        <Link to={`/article/${latest.slug}`} className="group block">
          <p className="text-sm font-bold text-[#111111] leading-snug group-hover:underline line-clamp-2">
            {latest.title}
          </p>
          <p className="text-[11px] text-[#767676] mt-2">
            {formatTimeAgo(latest.date || latest.published_at)}
          </p>
        </Link>
      ) : (
        <Link to={section.path} className="text-xs text-[#767676] hover:text-[#ff6600]">
          Publish in CMS →
        </Link>
      )}
    </div>
  );
}

function SectorGrid() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-2">
      {SECTOR_RESEARCH.map((s) => (
        <Link
          key={s.id}
          to={s.path}
          className="border border-[#dddddd] px-3 py-3 text-center text-xs font-bold text-[#111111] hover:border-[#111111] hover:text-[#ff6600] transition-colors"
        >
          {s.name}
        </Link>
      ))}
    </div>
  );
}

function MarketUpdateSectionLoader({ sectionId }) {
  const section = MARKET_UPDATE_SECTIONS.find((s) => s.id === sectionId);
  const { articles, loading } = usePublishedArticles({ limit: 1, section: section?.section });
  return (
    <MarketUpdateStrip section={section} articles={articles} loading={loading} />
  );
}

export default function EditorialHome() {
  const { user } = useAuth();
  const { data: uiHome, loading: uiLoading } = useUiHome();
  const { articles: research, loading: researchLoading } = usePublishedArticles({
    limit: 6,
    section: null,
  });
  const firstName = firstNameFromUser(user);
  const showPinNudge = Boolean(user?.id && !hasPin(user.id));

  useEffect(() => {
    trackProductEvent('session_start', { surface: 'home', authenticated: Boolean(user) });
  }, [user]);

  const featuredResearch = research.filter(
    (a) =>
      a.section?.includes('Research') ||
      a.category?.includes('Research') ||
      !a.section?.includes('Update')
  ).slice(0, 4);

  const companyUpdates = research.filter(
    (a) => a.section === 'Company Updates' || a.category === 'Company Updates'
  ).slice(0, 3);

  const macroArticles = research.filter(
    (a) =>
      a.section?.includes('Macro') ||
      (Array.isArray(a.tags) && a.tags.some((t) => /macro|global/i.test(t)))
  ).slice(0, 3);

  const topCompanies = uiHome?.top_companies || uiHome?.feeds?.trending_companies || [];
  const themes = uiHome?.market_themes || uiHome?.feeds?.trending_themes || [];
  const calendar = uiHome?.economic_calendar || [];
  const knowledge = uiHome?.latest_news || [];
  const predictions = uiHome?.feeds?.latest_predictions || [];

  return (
    <div className="bg-white min-h-screen">
      <Helmet>
        <title>AGI — Institutional Investment Research</title>
        <meta
          name="description"
          content="What AGI believes today, why, the evidence, what changed, and where to explore next — Ask AGI, company, sector, theme and macro intelligence."
        />
        <link rel="canonical" href="https://agarwalglobalinvestments.com/" />
        <meta property="og:title" content="Agarwal Global Investments" />
        <meta property="og:description" content="Talk to the Investment Office. Evidence-backed institutional research." />
        <script type="application/ld+json">
          {JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Organization',
            name: 'Agarwal Global Investments',
            url: 'https://agarwalglobalinvestments.com/',
            description: 'Independent institutional investment research',
          })}
        </script>
      </Helmet>
      <div className="max-w-[1800px] mx-auto px-4 sm:px-6">
        {user && (
          <section className="border-b border-[#dddddd] py-5" aria-label="Personal greeting">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[#ff6600]">Your desk</p>
            <h2 className="mt-1 text-xl md:text-2xl font-bold text-[#111111]">
              {greetingForNow()}, {firstName}
            </h2>
            <p className="mt-1 text-sm text-[#767676]">
              Continue with Ask AGI, your workspace, and today&apos;s market brief.
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-bold">
              <Link to="/ask" className="border border-[#ddd] px-2.5 py-1.5 hover:text-[#ff6600]">
                Ask AGI
              </Link>
              <Link to="/workspace" className="border border-[#ddd] px-2.5 py-1.5 hover:text-[#ff6600]">
                Workspace
              </Link>
              <Link to="/account/security" className="border border-[#ddd] px-2.5 py-1.5 hover:text-[#ff6600]">
                Security &amp; PIN
              </Link>
              {showPinNudge && (
                <Link
                  to="/account/security"
                  className="border border-[#ff6600] bg-[#fff7f0] px-2.5 py-1.5 text-[#ff6600]"
                >
                  Set a device PIN
                </Link>
              )}
            </div>
          </section>
        )}

        {/* Hero — existing design, live intelligence */}
        <MorningBriefHero uiHome={uiHome} uiLoading={uiLoading} />

        {/* Ask AGI — flagship */}
        <section className="py-8 border-b border-[#dddddd]" aria-labelledby="ask-agi-heading">
          <div className="max-w-[900px]">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[#ff6600]">Ask AGI</p>
            <h2 id="ask-agi-heading" className="mt-2 text-2xl md:text-3xl font-bold text-[#111111]">
              {user ? `${firstName}, talk to the Investment Office` : 'Talk to the Investment Office'}
            </h2>
            <p className="mt-2 text-sm text-[#767676] max-w-2xl">
              Ask about markets, companies, sectors or the economy. Every answer is evidence-based —
              house view, confidence, research and conflicting opinions.
            </p>
            <div className="mt-4 flex flex-wrap gap-2 text-[11px] font-bold">
              <Link to="/ask" className="border border-[#ddd] px-2.5 py-1.5 hover:text-[#ff6600]">Open Ask AGI</Link>
              <Link to="/predictions" className="border border-[#ddd] px-2.5 py-1.5 hover:text-[#ff6600]">Prediction Centre</Link>
              <Link to="/workspace" className="border border-[#ddd] px-2.5 py-1.5 hover:text-[#ff6600]">Personal Workspace</Link>
              <Link to="/macro-intelligence" className="border border-[#ddd] px-2.5 py-1.5 hover:text-[#ff6600]">Macro Intelligence</Link>
            </div>
          </div>
        </section>

        <div className="pt-8">
          <PopularInvestorQuestions
            questions={uiHome?.popular_questions || []}
            loading={uiLoading}
          />
        </div>

        <NewsHeadlineBar />
        <IndexSentimentTicker />

        {/* Today's Market Intelligence */}
        <HomeIntelligenceStrip />

        {/* Market Dashboard */}
        <TodayDashboard />

        <ResearchNotesPreview />
        <Nifty500ResearchPreview />
        <IpoMonitorPreview />

        {/* Featured Research */}
        <section className="py-8 border-b border-[#dddddd]">
          <SectionHeader
            title="Featured Research"
            subtitle="Independent perspectives from the AGI research desk"
            href="/research"
          />
          {researchLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-64 bg-[#eee] animate-pulse" />
              ))}
            </div>
          ) : featuredResearch.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {featuredResearch.map((a) => (
                <InstitutionalResearchCard key={a.id} article={a} />
              ))}
            </div>
          ) : (uiHome?.latest_published || []).length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {(uiHome.latest_published || []).slice(0, 4).map((r) => (
                <div key={r.research_id || r.title} className="border border-[#dddddd] p-4">
                  <p className="text-[10px] font-bold uppercase text-[#ff6600]">Research desk</p>
                  <p className="mt-2 text-sm font-bold text-[#111] line-clamp-3">{r.title}</p>
                  <p className="mt-2 text-[11px] text-[#767676]">{(r.tickers || []).join(', ')}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[#767676]">
              Publish research notes in CMS to populate this section.{' '}
              <Link to="/research" className="font-bold text-[#111] hover:text-[#ff6600]">
                Browse research →
              </Link>
            </p>
          )}
        </section>

        {/* Trending Themes */}
        <section className="py-8 border-b border-[#dddddd]">
          <SectionHeader title="Trending Themes" subtitle="Live themes from institutional knowledge" href="/themes/credit_growth" />
          {themes.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {themes.slice(0, 12).map((t) => (
                <Link
                  key={t.id || t.name}
                  to={`/themes/${encodeURIComponent(t.id || t.name)}`}
                  className="text-xs font-bold border border-[#dddddd] px-3 py-2 hover:border-[#111] hover:text-[#ff6600]"
                >
                  {t.name || t.id}
                </Link>
              ))}
            </div>
          ) : (
            <SectorGrid />
          )}
        </section>

        {/* Top Companies */}
        <section className="py-8 border-b border-[#dddddd]">
          <SectionHeader title="Top Companies" subtitle="Composite book snapshot" href="/portfolio" />
          {topCompanies.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
              {topCompanies.slice(0, 8).map((row) => (
                <Link
                  key={row.ticker}
                  to={`/research/stocks/${encodeURIComponent(row.ticker)}`}
                  className="border border-[#dddddd] p-3 hover:border-[#111]"
                >
                  <p className="text-sm font-bold text-[#111]">{row.ticker}</p>
                  <p className="text-[11px] text-[#767676] mt-1">{row.label || '—'}</p>
                </Link>
              ))}
            </div>
          ) : companyUpdates.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {companyUpdates.map((a) => (
                <InstitutionalResearchCard key={a.id} article={a} showImage={false} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-[#767676]">Composite coverage will appear as opinions load.</p>
          )}
        </section>

        {/* Economic Calendar */}
        <section className="py-8 border-b border-[#dddddd]">
          <SectionHeader title="Economic Calendar" href="/macro-intelligence" />
          {calendar.length > 0 ? (
            <ul className="space-y-2">
              {calendar.slice(0, 6).map((e, idx) => (
                <li key={e.id || e.title || idx} className="border border-[#dddddd] px-4 py-3 text-sm">
                  {e.title || e.name}
                </li>
              ))}
            </ul>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <MarketUpdateSectionLoader sectionId="pre-market" />
              <MarketUpdateSectionLoader sectionId="midday" />
              <MarketUpdateSectionLoader sectionId="market-close" />
            </div>
          )}
        </section>

        {/* Latest Predictions */}
        <section className="py-8 border-b border-[#dddddd]">
          <SectionHeader title="Latest Predictions" subtitle="Public prediction tracker" href="/predictions" />
          {predictions.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {predictions.slice(0, 6).map((p) => (
                <Link
                  key={p.id}
                  to={p.ticker ? `/research/stocks/${encodeURIComponent(p.ticker)}` : '/predictions'}
                  className="border border-[#dddddd] p-4 hover:border-[#111]"
                >
                  <p className="text-[10px] font-bold uppercase text-[#ff6600]">{p.ticker || 'Prediction'}</p>
                  <p className="mt-2 text-sm font-bold text-[#111] line-clamp-2">{p.thesis || p.target_horizon}</p>
                  <p className="mt-2 text-[11px] text-[#767676] capitalize">{p.current_status || 'open'}</p>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[#767676]">
              Predictions populate as forward-looking views are recorded.{' '}
              <Link to="/predictions" className="font-bold hover:text-[#ff6600]">Open Prediction Centre →</Link>
            </p>
          )}
        </section>

        {/* Knowledge Feed */}
        <section className="py-8 border-b border-[#dddddd]">
          <SectionHeader title="Knowledge Feed" subtitle="Latest institutional memory" href="/research" />
          {knowledge.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {knowledge.slice(0, 6).map((n) => (
                <div key={n.id || n.title} className="border border-[#dddddd] p-4">
                  <p className="text-sm font-bold text-[#111] line-clamp-2">{n.title}</p>
                  {n.snippet && <p className="text-xs text-[#767676] mt-2 line-clamp-3">{n.snippet}</p>}
                </div>
              ))}
            </div>
          ) : macroArticles.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {macroArticles.map((a) => (
                <InstitutionalResearchCard key={a.id} article={a} showImage={false} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-[#767676]">Knowledge feed populates as documents are ingested.</p>
          )}
        </section>

        {/* Sector research grid retained */}
        <section className="py-8 border-b border-[#dddddd]">
          <SectionHeader title="Sector Research" subtitle="Deep-dive coverage across key sectors" href="/research" />
          <SectorGrid />
        </section>
      </div>

      <NewsletterSection />
    </div>
  );
}
