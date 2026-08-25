import { Link } from 'react-router-dom';
import usePublishedArticles from '@/hooks/usePublishedArticles';

const GLOBAL_SECTIONS = ['Global Markets', 'Commodities'];

function formatDate(value) {
  if (!value) return 'Recently published';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Recently published';
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function ArticleCard({ article, featured = false }) {
  const href = article?.slug ? `/article/${article.slug}` : '/research';
  const image = article.coverUrl || article.cover_url;
  return (
    <article className={`overflow-hidden border border-slate-800 bg-[#0d131c] ${featured ? 'lg:col-span-2' : ''}`}>
      <div className={featured ? 'grid md:grid-cols-[1.1fr_1fr]' : ''}>
        <Link to={href} className={`block overflow-hidden bg-slate-900 ${featured ? 'min-h-[250px] md:min-h-full' : 'aspect-[16/9]'}`}>
          <img
            src={image}
            alt=""
            loading={featured ? 'eager' : 'lazy'}
            className="h-full w-full object-cover transition duration-500 hover:scale-[1.02]"
          />
        </Link>
        <div className={`p-5 ${featured ? 'md:p-7' : ''}`}>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-sky-300">
            {article.section || 'Global Markets'} · {formatDate(article.date)}
          </p>
          <h2 className={`mt-3 font-semibold leading-tight ${featured ? 'text-2xl md:text-3xl' : 'text-xl'}`} style={{ color: '#f8fafc' }}>
            <Link to={href} className="hover:text-sky-200" style={{ color: 'inherit' }}>{article.title}</Link>
          </h2>
          {article.excerpt ? (
            <p className={`mt-3 max-w-3xl leading-7 text-slate-400 ${featured ? 'text-base' : 'text-sm'}`}>
              {article.excerpt}
            </p>
          ) : null}
          <Link to={href} className="mt-5 inline-block text-sm font-semibold text-sky-300 hover:text-sky-200">
            Read research →
          </Link>
        </div>
      </div>
    </article>
  );
}

export default function GlobalMarketsPage() {
  const { articles, loading, error } = usePublishedArticles({
    limit: 18,
    sections: GLOBAL_SECTIONS,
  });
  const [featured, ...latest] = articles;

  return (
    <main className="min-h-screen bg-[#070b10] pb-14 text-slate-100">
      <div className="border-b border-slate-800 bg-[#0a1017]">
        <div className="mx-auto flex max-w-[1400px] items-center gap-3 px-4 py-2 text-[11px] md:px-6">
          <span className="font-bold tracking-[0.18em] text-sky-300">AGI GLOBAL MARKETS</span>
          <span className="text-slate-500">Editorial macro · cross-asset · India implications</span>
        </div>
      </div>

      <div className="mx-auto max-w-[1400px] px-4 md:px-6">
        <header className="border-b border-slate-800 py-10 md:py-14">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-sky-300">AGI research desk</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">Global Markets</h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400 md:text-base">
            Independent research on global growth, central banks, rates, currencies, commodities and their potential implications for India.
          </p>
          <Link
            to="/us-stock-intelligence"
            className="mt-6 inline-flex items-center border border-emerald-700/70 bg-emerald-950/30 px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-emerald-200 transition hover:border-emerald-400 hover:bg-emerald-950/60"
          >
            Open US Stock Intelligence
          </Link>
        </header>

        <section className="py-7 md:py-9">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-sky-300">Published research</p>
              <h2 className="mt-1 text-xl font-semibold text-white">Latest notes</h2>
            </div>
            <Link to="/research" className="text-sm font-semibold text-sky-300 hover:text-sky-200">All AGI research →</Link>
          </div>

          {loading ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="h-64 animate-pulse border border-slate-800 bg-[#0d131c] lg:col-span-2" />
              <div className="h-48 animate-pulse border border-slate-800 bg-[#0d131c]" />
              <div className="h-48 animate-pulse border border-slate-800 bg-[#0d131c]" />
            </div>
          ) : error ? (
            <div className="border border-amber-900 bg-amber-950/20 p-5 text-sm text-amber-100">
              Research could not be loaded right now. Please refresh shortly.
            </div>
          ) : !featured ? (
            <div className="border border-slate-800 bg-[#0d131c] p-6 md:p-8">
              <p className="text-lg font-semibold text-white">No Global Markets research has been published yet.</p>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
                In Admin → Articles, create an article, choose the <b className="text-slate-200">Global Markets</b> research desk, then publish it. It will appear here automatically.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              <ArticleCard article={featured} featured />
              {latest.map((article) => <ArticleCard key={article.id || article.slug} article={article} />)}
            </div>
          )}
        </section>

        <section className="border-t border-slate-800 py-7">
          <p className="max-w-4xl text-xs leading-6 text-slate-500">
            AGI research is for information and research discussion only. It is not personalised investment advice, a recommendation, or an offer to buy or sell any security.
          </p>
        </section>
      </div>
    </main>
  );
}
