import { Link } from 'react-router-dom';
import { useMemo } from 'react';
import usePublishedArticles from '@/hooks/usePublishedArticles';
import {
  articleMatchesDesk,
  getDeskById,
  getSectionsForDesk,
} from '@/lib/deskSections';

function articleHref(article) {
  return article?.slug ? `/article/${article.slug}` : '/research';
}

const FALLBACK_COVER =
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80';

function articleCover(article) {
  return article?.coverUrl || article?.cover_url || FALLBACK_COVER;
}

function formatDate(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return '—';
  }
}

/**
 * Desk-scoped research list for nav pages (Market Intelligence, Hedge Fund, etc.).
 * Only shows articles whose CMS Research Desk matches the given deskId.
 */
export default function DeskResearchFeed({
  deskId,
  title = 'Latest Research',
  limit = 12,
  emptyHint,
  className = '',
  /** Override article grid columns (e.g. when beside a side rail). */
  gridClassName = 'grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3',
}) {
  const desk = getDeskById(deskId);
  const sections = useMemo(() => getSectionsForDesk(deskId), [deskId]);
  const { articles: fetched, loading } = usePublishedArticles({
    limit,
    section: null,
    sections,
  });

  const articles = useMemo(
    () => fetched.filter((article) => articleMatchesDesk(article, deskId)),
    [fetched, deskId]
  );

  const deskLabel = desk?.label || 'Desk';

  return (
    <section className={`desk-research-feed ${className}`} aria-label={`${deskLabel} research`}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#6b7280]">
            {deskLabel} desk
          </p>
          <h2 className="mt-1 font-serif text-2xl font-bold text-[#111111] md:text-3xl">{title}</h2>
          <p className="mt-1.5 text-sm text-[#555555]">
            Only articles published to the {deskLabel} research desk.
          </p>
        </div>
        <Link
          to="/research"
          className="text-sm font-semibold text-[#111111] underline-offset-4 hover:underline"
        >
          All research →
        </Link>
      </div>

      {loading ? (
        <div className={`mt-6 grid ${gridClassName}`}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-56 animate-pulse rounded-xl border border-[#e8eaee] bg-[#f7f8fa]" />
          ))}
        </div>
      ) : !articles.length ? (
        <div className="mt-6 rounded-xl border border-[#e8eaee] px-6 py-12 text-center">
          <p className="font-serif text-xl font-bold text-[#111111]">No {deskLabel} research yet</p>
          <p className="mt-2 text-sm text-[#555555]">
            {emptyHint ||
              `Publish an article in Admin → Articles and set Research Desk to “${deskLabel}”.`}
          </p>
        </div>
      ) : (
        <div className={`mt-6 grid ${gridClassName}`}>
          {articles.map((article, i) => {
            const href = articleHref(article);
            const cover = articleCover(article);
            return (
              <article
                key={article.id || article.slug || i}
                className="group flex min-w-0 flex-col overflow-hidden rounded-xl border border-[#e4e7ec] bg-white"
              >
                <Link to={href} className="agi-cover agi-cover--16-10 block min-w-0">
                  <img src={cover} alt="" loading="lazy" />
                </Link>
                <div className="flex min-w-0 flex-1 flex-col p-5">
                  <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#6b7280]">
                    {article.section || deskLabel}
                  </p>
                  <h3 className="mt-2 font-serif text-lg font-bold leading-snug text-[#111111] line-clamp-2">
                    <Link to={href} className="hover:underline underline-offset-4">
                      {article.title}
                    </Link>
                  </h3>
                  {article.excerpt ? (
                    <p className="mt-2 flex-1 text-sm leading-relaxed text-[#555555] line-clamp-2">
                      {article.excerpt}
                    </p>
                  ) : null}
                  <p className="mt-4 text-[11px] text-[#767676]">{formatDate(article.publishedAt)}</p>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
