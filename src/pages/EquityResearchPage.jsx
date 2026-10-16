import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { ArrowUpRight, BarChart3, Building2, MapPin } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

const MARKETS = [
  { id: 'india', label: 'India', description: 'Indian listed companies' },
  { id: 'us', label: 'US', description: 'United States listed companies' },
];

const VIEW_STYLES = {
  bullish: 'border-[#a7cdb4] bg-[#edf7f0] text-[#176137]',
  neutral: 'border-[#cfd5dc] bg-[#f3f5f7] text-[#4b5563]',
  bearish: 'border-[#e4b2aa] bg-[#fff1ef] text-[#9f2f24]',
};

function articleMarket(article) {
  const meta = article?.equity_research || {};
  const explicit = String(meta.market || meta.country || '').toLowerCase();
  const tags = Array.isArray(article?.tags) ? article.tags.join(' ').toLowerCase() : '';
  const section = String(article?.section || '').toLowerCase();

  if (/\b(us|usa|united states)\b/.test(explicit)) return 'us';
  if (/\bindia(n)?\b/.test(explicit)) return 'india';
  if (/global|united states|us market/.test(section) || /\b(us|usa|nasdaq|nyse)\b/.test(tags)) return 'us';
  return 'india';
}

function isIpoArticle(article) {
  const section = String(article?.section || '').trim().toLowerCase();
  return section === 'ipo' || section === 'ipos';
}

function formatDate(value) {
  if (!value) return 'Recently published';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Recently published';
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function ResearchCard({ article, featured = false }) {
  const meta = article.equity_research || {};
  const view = String(meta.view || 'neutral').toLowerCase();
  const viewLabel = view.charAt(0).toUpperCase() + view.slice(1);
  const cover = article.cover_url;

  return (
    <article
      className={`group overflow-hidden rounded-2xl border border-[#dfe3e8] bg-white shadow-[0_14px_40px_rgba(13,31,51,0.05)] ${
        featured ? 'lg:col-span-2' : ''
      }`}
    >
      <div className={featured ? 'grid min-h-full md:grid-cols-[1.08fr_1fr]' : ''}>
        <Link
          to={`/article/${article.slug}`}
          className={`relative block overflow-hidden bg-[#0b1f33] ${featured ? 'min-h-[260px]' : 'aspect-[16/9]'}`}
        >
          {cover ? (
            <img
              src={cover}
              alt=""
              loading={featured ? 'eager' : 'lazy'}
              className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.025]"
            />
          ) : (
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(80,132,167,0.62),transparent_38%),linear-gradient(135deg,#0b1f33_0%,#173d54_55%,#bd8d50_140%)]" />
          )}
          <div className="absolute inset-x-0 bottom-0 flex items-end justify-between bg-gradient-to-t from-black/70 to-transparent p-5 text-white">
            <span className="text-[10px] font-bold uppercase tracking-[0.18em]">AGI Equity Research</span>
            {meta.ticker ? <span className="rounded bg-white/15 px-2 py-1 text-xs font-semibold backdrop-blur">{meta.ticker}</span> : null}
          </div>
        </Link>

        <div className={`flex flex-col ${featured ? 'p-6 md:p-8' : 'p-5'}`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className={`rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-[0.14em] ${VIEW_STYLES[view] || VIEW_STYLES.neutral}`}>
              {viewLabel}
            </span>
            <time className="text-xs font-medium text-[#707780]">{formatDate(article.published_at)}</time>
          </div>

          <div className="mt-5 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-[#607080]">
            <Building2 className="h-3.5 w-3.5" aria-hidden />
            <span>{meta.company || meta.ticker || 'Company research'}</span>
          </div>

          <h2 className={`mt-3 font-serif font-bold leading-[1.12] text-[#111820] ${featured ? 'text-3xl md:text-[2.15rem]' : 'text-2xl'}`}>
            <Link to={`/article/${article.slug}`} className="transition-colors hover:text-[#245d78]">
              {article.title}
            </Link>
          </h2>

          {article.excerpt ? (
            <p className="mt-4 line-clamp-3 text-sm leading-6 text-[#5d6670]">{article.excerpt}</p>
          ) : null}

          <div className="mt-auto flex flex-wrap items-end justify-between gap-4 pt-6">
            <div className="flex gap-5 text-xs text-[#68717b]">
              {meta.current_price ? <span>Price <b className="text-[#18222c]">{meta.current_price}</b></span> : null}
              {meta.price_target ? <span>Reference <b className="text-[#18222c]">{meta.price_target}</b></span> : null}
            </div>
            <Link to={`/article/${article.slug}`} className="inline-flex items-center gap-1 text-sm font-bold text-[#0b1f33] hover:text-[#245d78]">
              Read research <ArrowUpRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}

export default function EquityResearchPage() {
  const [market, setMarket] = useState('india');
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function loadArticles() {
      setLoading(true);
      setError('');
      const { data, error: loadError } = await supabase
        .from('articles')
        .select('id, title, slug, section, excerpt, cover_url, tags, published_at, article_type, equity_research')
        .eq('status', 'published')
        .eq('article_type', 'equity_research')
        .order('published_at', { ascending: false })
        .limit(60);

      if (cancelled) return;
      if (loadError) {
        console.error('Failed to load equity research:', loadError);
        setError('Equity research could not be loaded right now.');
        setArticles([]);
      } else {
        setArticles((data || []).filter((article) => !isIpoArticle(article)));
      }
      setLoading(false);
    }

    loadArticles();
    return () => {
      cancelled = true;
    };
  }, []);

  const counts = useMemo(() => ({
    india: articles.filter((article) => articleMarket(article) === 'india').length,
    us: articles.filter((article) => articleMarket(article) === 'us').length,
  }), [articles]);

  const visibleArticles = useMemo(
    () => articles.filter((article) => articleMarket(article) === market),
    [articles, market]
  );
  const [featured, ...latest] = visibleArticles;

  return (
    <main className="min-h-screen bg-[#f4f1ea] text-[#111820]">
      <Helmet>
        <title>Equity Research | Agarwal Global Investments</title>
        <meta
          name="description"
          content="Independent company research and investment theses across Indian and United States listed equities."
        />
      </Helmet>

      <section className="relative overflow-hidden border-b border-[#cfcbc1] bg-[#0b1f33] text-white">
        <div className="absolute inset-0 opacity-35 [background-image:linear-gradient(rgba(255,255,255,.06)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.06)_1px,transparent_1px)] [background-size:44px_44px]" />
        <div className="relative mx-auto max-w-[1500px] px-4 py-14 sm:px-6 md:py-20 lg:px-8">
          <div className="flex max-w-4xl items-center gap-2 text-[11px] font-bold uppercase tracking-[0.2em] text-[#d8b17a]">
            <BarChart3 className="h-4 w-4" aria-hidden />
            Independent company research
          </div>
          <h1 className="mt-5 max-w-4xl font-serif text-4xl font-bold tracking-[-0.035em] sm:text-5xl md:text-6xl">
            Equity Research
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-[#c9d3dc] md:text-lg">
            Evidence-led company analysis across the two markets we cover: India and the United States.
          </p>
          <p className="mt-5 max-w-3xl border-l-2 border-[#d8b17a] pl-4 text-xs leading-6 text-[#9fb0bf]">
            Views are expressed as Bullish, Neutral or Bearish and are provided for informational research only.
          </p>
        </div>
      </section>

      <section className="sticky top-[58px] z-30 border-b border-[#d9d5cc] bg-[#f4f1ea]/95 backdrop-blur" aria-label="Equity research markets">
        <div className="mx-auto flex max-w-[1500px] gap-2 px-4 py-4 sm:px-6 lg:px-8">
          {MARKETS.map((option) => {
            const active = market === option.id;
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => setMarket(option.id)}
                aria-pressed={active}
                className={`flex min-w-[138px] items-center justify-between gap-4 rounded-full border px-4 py-2.5 text-left transition ${
                  active
                    ? 'border-[#0b1f33] bg-[#0b1f33] text-white'
                    : 'border-[#c9c5bb] bg-white text-[#25313d] hover:border-[#78838d]'
                }`}
              >
                <span>
                  <span className="block text-sm font-bold">{option.label}</span>
                  <span className={`block text-[10px] ${active ? 'text-white/65' : 'text-[#7a8087]'}`}>{option.description}</span>
                </span>
                <span className={`text-xs font-bold ${active ? 'text-[#d8b17a]' : 'text-[#66717c]'}`}>{counts[option.id]}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="mx-auto max-w-[1500px] px-4 py-10 sm:px-6 md:py-14 lg:px-8">
        <div className="mb-7 flex flex-wrap items-end justify-between gap-4 border-b border-[#cfcbc1] pb-5">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.18em] text-[#7c643f]">
              <MapPin className="h-3.5 w-3.5" aria-hidden />
              {market === 'india' ? 'India coverage' : 'United States coverage'}
            </div>
            <h2 className="mt-2 font-serif text-3xl font-bold">Latest company research</h2>
          </div>
          <span className="text-sm text-[#68717b]">{counts[market]} published {counts[market] === 1 ? 'report' : 'reports'}</span>
        </div>

        {loading ? (
          <div className="grid gap-5 lg:grid-cols-2">
            <div className="h-[360px] animate-pulse rounded-2xl bg-white lg:col-span-2" />
            <div className="h-[300px] animate-pulse rounded-2xl bg-white" />
            <div className="h-[300px] animate-pulse rounded-2xl bg-white" />
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-[#e2b9ae] bg-[#fff6f2] p-6 text-sm text-[#8d3025]">{error}</div>
        ) : !featured ? (
          <div className="rounded-2xl border border-dashed border-[#bcb7ac] bg-white/55 px-6 py-16 text-center">
            <p className="font-serif text-2xl font-bold">{market === 'india' ? 'India' : 'US'} reports are coming soon</p>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-[#68717b]">
              Published equity research for this market will appear here automatically.
            </p>
          </div>
        ) : (
          <div className="grid gap-5 lg:grid-cols-2">
            <ResearchCard article={featured} featured />
            {latest.map((article) => <ResearchCard key={article.id} article={article} />)}
          </div>
        )}
      </section>

      <section className="border-t border-[#cfcbc1] bg-[#ebe7de]">
        <div className="mx-auto max-w-[1500px] px-4 py-7 text-xs leading-6 text-[#68717b] sm:px-6 lg:px-8">
          AGI research is informational and does not constitute personalised investment advice or an offer to buy or sell securities.
        </div>
      </section>
    </main>
  );
}
