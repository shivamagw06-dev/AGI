import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  BookOpen,
  Briefcase,
  Globe2,
  Landmark,
  Library,
  LineChart,
} from 'lucide-react';
import NewsletterSection from '@/components/Home/NewsletterSection';
import LiveBadge from '@/components/Article/LiveBadge';
import usePublishedArticles from '@/hooks/usePublishedArticles';
import useHomepageLatest from '@/hooks/useHomepageLatest';
import { formatTimeAgo } from '@/lib/articleUtils';
import {
  RESEARCH_DESK_ALL,
  RESEARCH_DESKS,
  articleMatchesDesk,
  getDeskForSection,
  getSectionsForDesk,
} from '@/lib/deskSections';

const DESK_BUTTONS = [
  { id: RESEARCH_DESK_ALL, label: 'Articles', icon: BookOpen, hint: 'All research' },
  {
    id: 'equity-research',
    label: 'Equity Research',
    icon: Library,
    hint: 'India & US',
    href: '/equity-research',
  },
  ...RESEARCH_DESKS.filter((desk) =>
    ['indian-market', 'global-markets', 'private-markets', 'economics'].includes(desk.id)
  ).map((desk) => ({
    id: desk.id,
    label: desk.label,
    icon:
      desk.id === 'indian-market'
        ? LineChart
        : desk.id === 'global-markets'
          ? Globe2
          : desk.id === 'private-markets'
            ? Briefcase
            : Landmark,
    hint: desk.hint,
  })),
];

const DEFAULT_COVER =
  'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1400&q=80';

function articleHref(article) {
  return article?.href || (article?.slug ? `/article/${article.slug}` : '/research');
}

function articleCover(article) {
  return article?.coverUrl || article?.cover_url || article?.image || DEFAULT_COVER;
}

function articleAuthor(article) {
  return article?.author || article?.byline || 'AGI Research';
}

function articleMeta(article) {
  const published =
    article?.isLive && article?.lastUpdatedAt
      ? `Updated ${formatTimeAgo(article.lastUpdatedAt)}`
      : article?.publishedLabel
        ? formatTimeAgo(article.publishedLabel) || article.publishedLabel
        : article?.date
          ? formatTimeAgo(article.date)
          : 'Recently';
  return {
    category: getDeskForSection(article?.section || article?.category)?.label
      || article?.section
      || article?.category
      || 'Research',
    summary: article?.excerpt || article?.summary || 'Institutional research note from the AGI desk.',
    author: articleAuthor(article),
    published,
    readTime: article?.readTime || '5 min read',
  };
}

function DeskCategory({ article, className = '' }) {
  const meta = articleMeta(article);
  return (
    <p className={`flex flex-wrap items-center gap-2 ${className}`.trim()}>
      {article?.isLive ? <LiveBadge /> : null}
      <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#6b7280]">{meta.category}</span>
    </p>
  );
}

function LiveNowStrip({ articles }) {
  const live = (articles || []).filter((article) => article?.isLive).slice(0, 3);
  if (!live.length) return null;
  return (
    <div className="mt-8 mb-0 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-[#f3d0cc] bg-[#fff7f6] px-4 py-3">
      <LiveBadge />
      <span className="text-sm font-semibold text-[#111]">Live coverage</span>
      {live.map((article) => (
        <Link
          key={article.id || article.slug}
          to={articleHref(article)}
          className="text-sm font-medium text-[#111] underline-offset-4 hover:underline"
        >
          {article.title}
        </Link>
      ))}
    </div>
  );
}

function isMorning(article) {
  const hay = `${article?.section || ''} ${article?.category || ''} ${article?.title || ''}`;
  return /morning|pre-?market|overnight|open/i.test(hay);
}

function isEvening(article) {
  const hay = `${article?.section || ''} ${article?.category || ''} ${article?.title || ''}`;
  return /evening|post\s*market|day\s*close|market\s*close|wrap/i.test(hay);
}

function isIpoArticle(article) {
  const section = String(article?.section || article?.category || '').trim().toLowerCase();
  return section === 'ipos' || section === 'ipo';
}

/** Featured story — image + copy in one balanced row on desktop. */
function FeaturedArticle({ article }) {
  if (!article) return null;
  const href = articleHref(article);
  const cover = articleCover(article);
  const meta = articleMeta(article);

  return (
    <article className="group grid h-full min-w-0 overflow-hidden rounded-xl border border-[#e4e7ec] bg-white lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] animate-home-rise">
      <Link to={href} className="agi-cover agi-cover--featured block min-w-0">
        <img
          src={cover}
          alt=""
          className="transition-transform duration-500 group-hover:scale-[1.02]"
          loading="eager"
        />
      </Link>
      <div className="flex min-w-0 flex-col justify-center p-6 md:p-8">
        <DeskCategory article={article} className="text-[11px]" />
        <h3 className="mt-3 font-serif text-2xl md:text-[1.75rem] font-bold leading-snug text-[#111111]">
          <Link to={href} className="hover:underline underline-offset-4 decoration-[#111]/25">
            {article.title}
          </Link>
        </h3>
        <p className="mt-3 text-sm md:text-[15px] leading-relaxed text-[#555555] line-clamp-4">{meta.summary}</p>
        <div className="mt-5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-[#767676]">
          <span className="font-medium text-[#333]">{meta.author}</span>
          <span aria-hidden>·</span>
          <span>{meta.published}</span>
          <span aria-hidden>·</span>
          <span>{meta.readTime}</span>
        </div>
        <Link
          to={href}
          className="mt-6 inline-flex w-fit text-sm font-semibold text-[#0b1f33] underline-offset-4 hover:underline"
        >
          Read research →
        </Link>
      </div>
    </article>
  );
}

/** Compact stacked row used beside the featured story. */
function StackArticle({ article, index = 0 }) {
  if (!article) return null;
  const href = articleHref(article);
  const cover = articleCover(article);
  const meta = articleMeta(article);

  return (
    <article
      className="group flex gap-4 border-b border-[#eceef2] py-4 first:pt-0 last:border-b-0 last:pb-0 animate-home-rise"
      style={{ animationDelay: `${Math.min(index, 6) * 40}ms` }}
    >
      <Link to={href} className="agi-cover agi-cover--thumb shrink-0 rounded-lg">
        <img
          src={cover}
          alt=""
          className="transition-transform duration-500 group-hover:scale-[1.03]"
          loading="lazy"
        />
      </Link>
      <div className="min-w-0 flex-1 py-0.5">
        <DeskCategory article={article} />
        <h3 className="mt-1 font-serif text-[1.05rem] font-bold leading-snug text-[#111111] line-clamp-2">
          <Link to={href} className="hover:underline underline-offset-4 decoration-[#111]/25">
            {article.title}
          </Link>
        </h3>
        <div className="mt-2 flex flex-wrap items-center gap-x-2 text-[11px] text-[#767676]">
          <span>{meta.published}</span>
          <span aria-hidden>·</span>
          <span>{meta.readTime}</span>
        </div>
      </div>
    </article>
  );
}

/** Equal grid card for the lower research shelf. */
function GridArticle({ article, index = 0 }) {
  if (!article) return null;
  const href = articleHref(article);
  const cover = articleCover(article);
  const meta = articleMeta(article);

  return (
    <article
      className="group flex h-full flex-col overflow-hidden rounded-xl border border-[#e4e7ec] bg-white transition-shadow hover:shadow-sm animate-home-rise"
      style={{ animationDelay: `${Math.min(index, 8) * 35}ms` }}
    >
      <Link to={href} className="agi-cover agi-cover--16-10 block">
        <img
          src={cover}
          alt=""
          className="transition-transform duration-500 group-hover:scale-[1.03]"
          loading="lazy"
        />
      </Link>
      <div className="flex flex-1 flex-col p-5">
        <DeskCategory article={article} />
        <h3 className="mt-2 font-serif text-lg font-bold leading-snug text-[#111111] line-clamp-2">
          <Link to={href} className="hover:underline underline-offset-4 decoration-[#111]/25">
            {article.title}
          </Link>
        </h3>
        <p className="mt-2 flex-1 text-sm leading-relaxed text-[#555555] line-clamp-2">{meta.summary}</p>
        <div className="mt-4 flex flex-wrap items-center gap-x-2 text-[11px] text-[#767676]">
          <span className="font-medium text-[#333]">{meta.author}</span>
          <span aria-hidden>·</span>
          <span>{meta.published}</span>
          <span aria-hidden>·</span>
          <span>{meta.readTime}</span>
        </div>
      </div>
    </article>
  );
}

function BriefCard({ title, description, href, cta }) {
  return (
    <Link
      to={href}
      className="group flex flex-col justify-between rounded-xl border border-[#e4e7ec] bg-white p-6 md:p-7 transition-shadow hover:shadow-sm"
    >
      <div>
        <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#6b7280]">Daily Brief</p>
        <h3 className="mt-2 font-serif text-xl md:text-2xl font-bold text-[#111111]">{title}</h3>
        <p className="mt-3 text-sm leading-relaxed text-[#555555] line-clamp-3">{description}</p>
      </div>
      <span className="mt-6 inline-flex text-sm font-semibold text-[#0b1f33] group-hover:underline underline-offset-4">
        {cta}
      </span>
    </Link>
  );
}

function LatestRail({ articles, loading }) {
  return (
    <aside className="min-w-0 border border-[#e4e7ec] bg-white xl:self-start" aria-label="Latest selected headlines">
      <div className="flex items-center justify-between border-b border-[#e4e7ec] px-5 py-4">
        <h2 className="text-2xl font-bold tracking-tight text-[#e1251b]">Latest</h2>
        <span className="rounded-full bg-[#111] px-3 py-1 text-xs font-semibold text-white">AGI</span>
      </div>
      <div className="px-5">
        {loading ? (
          <div className="space-y-4 py-5">
            {[0, 1, 2, 3].map((item) => <div key={item} className="h-14 animate-pulse bg-[#f2f3f5]" />)}
          </div>
        ) : articles.length ? (
          articles.map((article) => {
            const meta = articleMeta(article);
            return (
              <article key={article.id || article.slug} className="grid grid-cols-[68px_minmax(0,1fr)] gap-3 border-b border-[#eceef2] py-5 last:border-b-0">
                <div className="pt-0.5">
                  {article.isLive ? (
                    <LiveBadge />
                  ) : (
                    <time className="text-sm font-semibold text-[#e1251b]">{meta.published}</time>
                  )}
                </div>
                <h3 className="font-serif text-lg font-bold leading-snug text-[#111]">
                  <Link to={articleHref(article)} className="hover:underline underline-offset-4">{article.title}</Link>
                </h3>
              </article>
            );
          })
        ) : (
          <p className="px-1 py-8 text-sm leading-relaxed text-[#767676]">
            Select “Show in Homepage Latest” when publishing an article in the CMS.
          </p>
        )}
      </div>
      <Link to="/research" className="block border-t border-[#e4e7ec] px-5 py-4 text-right text-sm font-semibold hover:underline">
        See all research →
      </Link>
    </aside>
  );
}

export default function ResearchTerminalHome() {
  const navigate = useNavigate();
  const [activeDesk, setActiveDesk] = useState(RESEARCH_DESK_ALL);
  const deskSections = useMemo(
    () => (activeDesk === RESEARCH_DESK_ALL ? null : getSectionsForDesk(activeDesk)),
    [activeDesk]
  );
  const { articles: fetchedArticles, loading } = usePublishedArticles({
    limit: 36,
    section: null,
    sections: deskSections,
    featuredFirst: activeDesk === RESEARCH_DESK_ALL,
  });
  const { articles: latestArticles, loading: latestLoading } = useHomepageLatest(7);

  const articles = useMemo(() => {
    const homepageArticles = fetchedArticles.filter((article) => !isIpoArticle(article));
    if (activeDesk === RESEARCH_DESK_ALL) return homepageArticles;
    return homepageArticles.filter((article) => articleMatchesDesk(article, activeDesk));
  }, [activeDesk, fetchedArticles]);
  const homepageLatestArticles = useMemo(
    () => latestArticles.filter((article) => !isIpoArticle(article)),
    [latestArticles]
  );

  const activeDeskLabel = DESK_BUTTONS.find((desk) => desk.id === activeDesk)?.label || 'Articles';

  const featured = articles[0] || null;
  const stack = articles.slice(1, 4);
  const grid = articles.slice(4, 10);

  const morningArticle = useMemo(() => articles.find(isMorning), [articles]);
  const eveningArticle = useMemo(() => articles.find(isEvening), [articles]);

  return (
    <div className="home-terminal min-h-screen bg-white text-[#111111]">
      <Helmet>
        <title>AGI — Institutional Research</title>
        <meta
          name="description"
          content="Read institutional equity research across Indian and US companies, Indian markets, private equity and economics."
        />
      </Helmet>

      {/* Desk navigation — six equal professional buttons */}
      <section className="border-b border-[#e8eaee] bg-white" aria-label="Research desks">
        <div className="mx-auto max-w-[1680px] px-4 sm:px-6 lg:px-8 py-5">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
            {DESK_BUTTONS.map((desk) => {
              const Icon = desk.icon;
              const isActive = activeDesk === desk.id;
              return (
                <button
                  key={desk.id}
                  type="button"
                  onClick={() => desk.href ? navigate(desk.href) : setActiveDesk(desk.id)}
                  aria-pressed={desk.href ? undefined : isActive}
                  className={`group flex items-center gap-3 rounded-xl border px-3.5 py-3.5 text-left transition-colors ${
                    isActive
                      ? 'border-[#0b1f33] bg-[#0b1f33] text-white'
                      : 'border-[#e4e7ec] bg-[#fafbfc] hover:border-[#0b1f33]/35 hover:bg-white'
                  }`}
                >
                  <span
                    className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${
                      isActive
                        ? 'border-white/20 bg-white/10 text-white'
                        : 'border-[#e8eaee] bg-white text-[#0b1f33] group-hover:border-[#0b1f33]/20'
                    }`}
                  >
                    <Icon className="h-4 w-4" aria-hidden />
                  </span>
                  <span className="min-w-0">
                    <span className={`block text-sm font-semibold ${isActive ? 'text-white' : 'text-[#111111]'}`}>
                      {desk.label}
                    </span>
                    <span className={`block text-[11px] ${isActive ? 'text-white/75' : 'text-[#767676]'}`}>
                      {desk.hint}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* Research mosaic */}
      <section id="latest-research" className="border-b border-[#e8eaee] bg-white" aria-label="Latest research">
        <div className="mx-auto w-full max-w-none px-4 sm:px-6 lg:px-8 2xl:px-12 py-10 md:py-12">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="font-serif text-3xl font-bold tracking-tight text-[#111111]">
                {activeDesk === RESEARCH_DESK_ALL ? 'Latest Research' : `${activeDeskLabel} Research`}
              </h2>
              <p className="mt-1.5 text-sm text-[#555555]">
                {activeDesk === RESEARCH_DESK_ALL
                  ? 'Editorial research from the AGI desk.'
                  : `Research notes from the ${activeDeskLabel} desk.`}
              </p>
            </div>
            <Link to="/research" className="text-sm font-semibold text-[#111111] hover:underline underline-offset-4">
              View all research →
            </Link>
          </div>

          <LiveNowStrip articles={articles} />

          <div className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_clamp(320px,20vw,380px)] xl:items-start">
          <div className="min-w-0">
          {loading ? (
            <div className="mt-8 grid grid-cols-1 gap-5 lg:grid-cols-[1.6fr_1fr]">
              <div className="h-[340px] animate-pulse rounded-xl border border-[#e8eaee] bg-[#f7f8fa]" />
              <div className="h-[340px] animate-pulse rounded-xl border border-[#e8eaee] bg-[#f7f8fa]" />
            </div>
          ) : !articles.length ? (
            <div className="mt-8 rounded-xl border border-[#e8eaee] px-6 py-14 text-center">
              <p className="font-serif text-xl font-bold text-[#111111]">
                {activeDesk === RESEARCH_DESK_ALL
                  ? 'Research notes are publishing soon'
                  : `No ${activeDeskLabel.toLowerCase()} research yet`}
              </p>
              <p className="mt-2 text-sm text-[#555555]">
                {activeDesk === RESEARCH_DESK_ALL
                  ? 'New notes appear here as the desk publishes them.'
                  : 'Try another desk.'}
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)] lg:items-stretch">
                <FeaturedArticle article={featured} />
                <div className="min-w-0 rounded-xl border border-[#e4e7ec] bg-white px-5 py-4 md:px-6">
                  <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.14em] text-[#6b7280]">
                    Also on the desk
                  </p>
                  <div>
                    {stack.map((article, i) => (
                      <StackArticle key={article.id || article.slug || i} article={article} index={i} />
                    ))}
                  </div>
                </div>
              </div>

              {grid.length > 0 ? (
                <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
                  {grid.map((article, i) => (
                    <GridArticle key={article.id || article.slug || i} article={article} index={i} />
                  ))}
                </div>
              ) : null}
            </>
          )}
          </div>
          <LatestRail articles={homepageLatestArticles} loading={latestLoading} />
          </div>
        </div>
      </section>

      {/* Morning / Evening */}
      <section className="border-b border-[#e8eaee] bg-[#f7f8fa]" aria-label="Morning and evening intelligence">
        <div className="mx-auto max-w-[1680px] px-4 sm:px-6 lg:px-8 py-10 md:py-12">
          <h2 className="font-serif text-2xl md:text-3xl font-bold text-[#111111]">Daily Intelligence</h2>
          <p className="mt-1.5 text-sm text-[#555555]">Overnight developments and market-close summaries.</p>
          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
            <BriefCard
              title="Morning Intelligence"
              description={
                morningArticle?.excerpt ||
                morningArticle?.title ||
                'Latest overnight developments shaping the Indian and global open.'
              }
              href={morningArticle ? articleHref(morningArticle) : '/pre-market'}
              cta="Read morning brief →"
            />
            <BriefCard
              title="Evening Intelligence"
              description={
                eveningArticle?.excerpt ||
                eveningArticle?.title ||
                'Market close summary with the moves, catalysts and overnight watchlist.'
              }
              href={eveningArticle ? articleHref(eveningArticle) : '/research'}
              cta="Read evening brief →"
            />
          </div>
        </div>
      </section>

      <NewsletterSection variant="minimal" />
    </div>
  );
}
