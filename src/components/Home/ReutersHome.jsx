import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import useFeaturedArticle from '@/hooks/useFeaturedArticle';
import usePublishedArticles from '@/hooks/usePublishedArticles';
import { formatTimeAgo } from '@/lib/articleUtils';
import { HOME_CATEGORIES } from '@/config/contentCategories';
import HomeNewsletterSidebar from '@/components/Home/HomeNewsletterSidebar';

const DEFAULT_HERO = {
  title: 'Institutional-Quality Market Research for Indian Investors',
  excerpt:
    'Daily market updates, company research, earnings analysis, and actionable investment insights — built for serious investors.',
  cover_url:
    'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80',
  category: 'Research',
  slug: null,
};

function StoryLabel({ text }) {
  return (
    <span className="inline-block text-[11px] font-bold uppercase tracking-wider text-[#ff6600] mb-3">
      {text}
    </span>
  );
}

function TextStory({ article, bordered = true }) {
  return (
    <Link
      to={`/article/${article.slug}`}
      className={`block py-4 group ${bordered ? 'border-b border-[#eeeeee]' : ''}`}
    >
      <StoryLabel text={article.category || article.section || 'Research'} />
      <h3 className="text-base font-bold text-[#111111] leading-snug group-hover:underline decoration-[#ff6600] underline-offset-2">
        {article.title}
      </h3>
      {article.excerpt && (
        <p className="text-sm text-[#555555] mt-2 line-clamp-2 leading-relaxed hidden sm:block">
          {article.excerpt}
        </p>
      )}
      <p className="text-xs text-[#767676] mt-2">{formatTimeAgo(article.date || article.published_at)}</p>
    </Link>
  );
}

function ThumbStory({ article }) {
  return (
    <Link
      to={`/article/${article.slug}`}
      className="flex gap-3 py-4 border-b border-[#eeeeee] group last:border-0"
    >
      <img
        src={article.image || article.coverUrl}
        alt=""
        className="w-24 h-16 object-cover shrink-0 bg-[#f0f0f0]"
      />
      <div className="min-w-0">
        <StoryLabel text={article.category || 'Research'} />
        <h3 className="text-sm font-bold text-[#111111] leading-snug group-hover:underline decoration-[#ff6600] underline-offset-2 line-clamp-3">
          {article.title}
        </h3>
        <p className="text-xs text-[#767676] mt-1">{formatTimeAgo(article.date || article.published_at)}</p>
      </div>
    </Link>
  );
}

export default function ReutersHome() {
  const { article: featured, loading: featuredLoading } = useFeaturedArticle();
  const { articles: recent, loading: recentLoading } = usePublishedArticles({
    limit: 8,
    excludeSlug: featured?.slug,
  });

  const hero = featured || DEFAULT_HERO;
  const heroLink = featured ? `/article/${featured.slug}` : '/research';
  const label = (featured?.category || featured?.section || 'Featured').toUpperCase();

  const textStories = recent.slice(0, 3);
  const thumbStories = recent.slice(3, 6);

  return (
    <div className="bg-white min-h-screen">
      <div className="max-w-[1280px] mx-auto px-4">
        {/* —— Hero: Reuters 3-column —— */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 py-6 lg:py-8 border-b border-[#dddddd]">
          {/* Lead story */}
          <div className="lg:col-span-4 flex flex-col justify-center order-2 lg:order-1">
            {featuredLoading ? (
              <div className="animate-pulse space-y-3">
                <div className="h-4 w-20 bg-[#eee]" />
                <div className="h-10 bg-[#eee]" />
                <div className="h-20 bg-[#eee]" />
              </div>
            ) : (
              <Link to={heroLink} className="group">
                <StoryLabel text={label} />
                <h1 className="text-2xl md:text-[1.75rem] lg:text-[2rem] font-bold text-[#111111] leading-[1.15] tracking-tight group-hover:underline decoration-[#ff6600] underline-offset-4">
                  {hero.title}
                </h1>
                <p className="text-base text-[#555555] mt-4 leading-relaxed line-clamp-4">
                  {hero.excerpt}
                </p>
                {featured?.published_at && (
                  <p className="text-xs text-[#767676] mt-4">{formatTimeAgo(featured.published_at)}</p>
                )}
              </Link>
            )}
          </div>

          {/* Hero image */}
          <div className="lg:col-span-5 order-1 lg:order-2">
            <Link to={heroLink} className="block group">
              <div className="aspect-[4/3] lg:aspect-[3/2] bg-[#f0f0f0] overflow-hidden">
                <img
                  src={hero.cover_url || DEFAULT_HERO.cover_url}
                  alt={hero.title}
                  className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-500"
                />
              </div>
              <p className="text-[11px] text-[#767676] mt-2 leading-snug">
                {featured
                  ? `${featured.category || 'Research'} · Agarwal Global Investments`
                  : 'Market research · Agarwal Global Investments'}
              </p>
            </Link>
          </div>

          {/* Sidebar */}
          <aside className="lg:col-span-3 order-3 space-y-4">
            <div className="border border-[#dddddd] p-4 bg-white">
              <h3 className="text-xs font-bold uppercase tracking-wide text-[#767676] mb-3">
                Quick access
              </h3>
              <ul className="space-y-0">
                {HOME_CATEGORIES.slice(0, 4).map((cat) => (
                  <li key={cat.id} className="border-t border-[#eeeeee] first:border-0">
                    <Link
                      to={cat.path}
                      className="flex items-center justify-between py-2.5 text-sm font-semibold text-[#111111] hover:text-[#ff6600] transition-colors group"
                    >
                      {cat.title}
                      <ChevronRight className="w-4 h-4 text-[#ccc] group-hover:text-[#ff6600]" />
                    </Link>
                  </li>
                ))}
              </ul>
              <Link
                to="/market-updates"
                className="mt-3 block text-xs font-bold text-[#111111] hover:text-[#ff6600]"
              >
                All market updates →
              </Link>
            </div>
            <HomeNewsletterSidebar />
          </aside>
        </section>

        {/* —— Secondary stories —— */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-0 py-2 lg:py-4 border-b border-[#dddddd]">
          <div className="lg:col-span-5 lg:pr-8 lg:border-r border-[#eeeeee]">
            {recentLoading ? (
              <div className="py-8 text-sm text-[#767676]">Loading latest research…</div>
            ) : textStories.length === 0 ? (
              <div className="py-8">
                <p className="text-sm text-[#555555]">Publish articles in CMS to populate this feed.</p>
                <Link to="/research" className="text-sm font-bold text-[#111111] hover:text-[#ff6600] mt-2 inline-block">
                  Browse research →
                </Link>
              </div>
            ) : (
              textStories.map((a) => <TextStory key={a.id} article={a} />)
            )}
          </div>

          <div className="lg:col-span-4 lg:px-8 lg:border-r border-[#eeeeee] pt-4 lg:pt-0">
            {!recentLoading &&
              thumbStories.map((a) => <ThumbStory key={a.id} article={a} />)}
          </div>

          <div className="lg:col-span-3 lg:pl-4 pt-6 lg:pt-0">
            <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676] mb-2 pb-2 border-b border-[#eeeeee]">
              Explore sections
            </h2>
            <ul className="divide-y divide-[#eeeeee]">
              {HOME_CATEGORIES.map((cat) => (
                <li key={cat.id}>
                  <Link
                    to={cat.path}
                    className="block py-3 text-sm font-bold text-[#111111] hover:text-[#ff6600] leading-snug"
                  >
                    {cat.title}
                  </Link>
                  <p className="text-xs text-[#767676] pb-3 leading-relaxed">{cat.description.slice(0, 80)}…</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* —— Bottom CTA strip —— */}
        <section className="py-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-[#111111]">Today&apos;s research</h2>
            <p className="text-sm text-[#555555] mt-1">Deep-dive reports, sector notes, and investment ideas.</p>
          </div>
          <Link
            to="/research"
            className="inline-flex items-center justify-center bg-[#111111] text-white text-sm font-bold px-6 py-2.5 hover:bg-[#333] transition-colors shrink-0"
          >
            Explore research
          </Link>
        </section>
      </div>
    </div>
  );
}
