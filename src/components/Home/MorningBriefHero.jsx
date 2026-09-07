import { Link } from 'react-router-dom';
import { Clock, BookOpen } from 'lucide-react';
import useMorningBrief from '@/hooks/useMorningBrief';
import useMarketDashboard from '@/hooks/useMarketDashboard';

function OutlookBadge({ outlook }) {
  if (!outlook) return null;
  const key = String(outlook).toLowerCase();
  const bullish = key.includes('bullish') && !key.includes('bear');
  const bearish = key.includes('bearish');
  const cls = bullish
    ? 'bg-[#e8f5e9] text-[#1b5e20] border-[#a5d6a7]'
    : bearish
      ? 'bg-[#ffebee] text-[#b71c1c] border-[#ef9a9a]'
      : 'bg-[#fff8e1] text-[#f57f17] border-[#ffe082]';

  return (
    <span className={`inline-flex items-center text-[11px] font-bold uppercase tracking-wide px-2.5 py-1 border ${cls}`}>
      {outlook}
    </span>
  );
}

function Metric({ label, value }) {
  return (
    <div className="border border-[#eeeeee] bg-white p-3">
      <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676]">{label}</p>
      <p className="mt-1 text-sm font-bold text-[#111111] line-clamp-2">{value || '—'}</p>
    </div>
  );
}

export default function MorningBriefHero({ uiHome = null, uiLoading = false }) {
  const { brief, loading } = useMorningBrief();
  const { outlook, loading: dashLoading } = useMarketDashboard();

  const link = brief?.slug ? `/article/${brief.slug}` : '/updates/pre-market';
  const label = brief?.heroLabel || 'AGI Morning Brief';
  const hero = uiHome?.hero || {};
  const regime = hero.market_regime || uiHome?.market_regime?.label || outlook?.outlook;
  const risk = hero.risk_level || uiHome?.market_risk?.label;

  return (
    <section className="border-b border-[#dddddd] py-8 lg:py-10">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <div className="lg:col-span-7">
          {loading ? (
            <div className="animate-pulse space-y-4">
              <div className="h-4 w-32 bg-[#eee]" />
              <div className="h-12 bg-[#eee]" />
              <div className="h-24 bg-[#eee]" />
            </div>
          ) : (
            <>
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#ff6600]">
                {label}
              </span>

              <h1 className="mt-3 text-3xl md:text-4xl lg:text-[2.75rem] font-bold text-[#111111] leading-[1.1] tracking-tight">
                {hero.headline || brief?.title || 'What do I need to know today?'}
              </h1>

              <div className="flex flex-wrap items-center gap-3 mt-4 text-xs text-[#767676]">
                {(brief?.published_at || hero.latest_update) && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {brief?.publishedLabel || brief?.timeAgo || hero.latest_update || 'Updated today'}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <BookOpen className="w-3.5 h-3.5" />
                  {hero.research_published_today != null
                    ? `${hero.research_published_today} research today`
                    : `${brief?.readTime || 5} min read`}
                </span>
                {!dashLoading && regime && <OutlookBadge outlook={regime} />}
              </div>

              <p className="mt-5 text-base md:text-lg text-[#444444] leading-relaxed max-w-2xl">
                {hero.house_view || uiHome?.market_brief?.summary || brief?.excerpt}
              </p>

              <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 gap-2">
                <Metric label="Market Regime" value={regime} />
                <Metric label="Risk Level" value={risk} />
                <Metric
                  label="Platform Health"
                  value={uiLoading ? '…' : hero.platform_health || uiHome?.system_health?.overall || '—'}
                />
                <Metric label="Research Count" value={hero.research_count} />
                <Metric label="Published Today" value={hero.research_published_today} />
                <Metric label="House View" value={regime ? 'Live desk' : 'Forming'} />
              </div>

              <Link
                to={link}
                className="inline-flex mt-6 bg-[#111111] text-white text-sm font-bold px-6 py-3 hover:bg-[#333333] transition-colors"
              >
                Read Full Report →
              </Link>
            </>
          )}
        </div>

        <div className="lg:col-span-5">
          <Link to={link} className="block group">
            <div className="aspect-[16/10] bg-[#f0f0f0] overflow-hidden">
              <img
                src={brief?.cover_url || 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80'}
                alt={brief?.title || "Today's market brief"}
                className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-500"
              />
            </div>
            <p className="text-[11px] text-[#767676] mt-2">
              Updated every trading day · Agarwal Global Investments
            </p>
          </Link>
        </div>
      </div>
    </section>
  );
}
