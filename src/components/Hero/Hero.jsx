import { motion } from 'framer-motion';
import useFeaturedArticle from '@/hooks/useFeaturedArticle';
import usePublishedArticles from '@/hooks/usePublishedArticles';
import {
  ArrowRight,
  Building2,
  Clock3,
  Globe2,
  TrendingUp,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';

const quickLinks = [
  { title: 'Markets', path: '/markets/stocks' },
  { title: 'Research Library', path: '/sections/live-articles' },
  { title: 'Deal Tracker', path: '/sections/deal-tracker' },
];

export default function Hero() {
  const navigate = useNavigate();
  const { article: featuredArticle, loading: articleLoading } = useFeaturedArticle();
  const { articles: recentArticles, loading: recentLoading } = usePublishedArticles({
    limit: 4,
    excludeSlug: featuredArticle?.slug,
  });

  return (
    <section className="bg-slate-950 border-b border-white/10">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-12 lg:py-16">
        <div className="grid lg:grid-cols-12 gap-10 lg:gap-12">
          <motion.div
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="lg:col-span-8"
          >
            <div className="inline-flex items-center gap-2 rounded-full bg-blue-600/20 border border-blue-500/30 text-blue-300 px-4 py-2 text-sm font-semibold">
              <TrendingUp size={16} />
              {featuredArticle ? 'Featured Research' : 'Research Platform'}
            </div>

            {articleLoading ? (
              <div className="mt-6 space-y-4 animate-pulse">
                <div className="aspect-[2/1] bg-white/5 rounded-2xl" />
                <div className="h-10 bg-white/5 rounded-lg w-3/4" />
                <div className="h-6 bg-white/5 rounded-lg w-1/2" />
              </div>
            ) : featuredArticle ? (
              <>
                {featuredArticle.cover_url && (
                  <button
                    type="button"
                    onClick={() => navigate(`/article/${featuredArticle.slug}`)}
                    className="mt-6 block w-full rounded-2xl overflow-hidden border border-white/10 aspect-[2/1] lg:aspect-[21/9]"
                  >
                    <img
                      src={featuredArticle.cover_url}
                      alt={featuredArticle.title}
                      className="w-full h-full object-cover hover:scale-[1.02] transition-transform duration-500"
                    />
                  </button>
                )}

                <h1 className="mt-6 text-3xl md:text-4xl lg:text-5xl font-bold leading-tight tracking-tight text-white">
                  {featuredArticle.title}
                </h1>

                <div className="mt-5 flex flex-wrap items-center gap-5 text-sm text-slate-400">
                  <span className="flex items-center gap-2">
                    <Clock3 size={16} /> {featuredArticle.publishedLabel}
                  </span>
                  <span className="flex items-center gap-2">
                    <Building2 size={16} /> {featuredArticle.category}
                  </span>
                  {Array.isArray(featuredArticle.tags) && featuredArticle.tags[0] && (
                    <span className="flex items-center gap-2">
                      <Globe2 size={16} /> {featuredArticle.tags[0]}
                    </span>
                  )}
                </div>

                <p className="mt-6 max-w-3xl text-lg leading-8 text-slate-300">
                  {featuredArticle.excerpt || 'Read our latest institutional research and market analysis.'}
                </p>

                <div className="mt-8 flex flex-wrap gap-4">
                  <Button
                    size="lg"
                    className="rounded-lg h-12 px-7 bg-blue-600 hover:bg-blue-700"
                    onClick={() => navigate(`/article/${featuredArticle.slug}`)}
                  >
                    Read full research <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="lg"
                    className="rounded-lg h-12 px-7 border-white/20 text-white hover:bg-white/10"
                    onClick={() => navigate('/sections/live-articles')}
                  >
                    Browse research library
                  </Button>
                </div>
              </>
            ) : (
              <>
                <h1 className="mt-6 text-4xl md:text-5xl font-bold leading-tight tracking-tight text-white">
                  Independent Research for Serious Investors
                </h1>
                <p className="mt-6 max-w-3xl text-lg leading-8 text-slate-300">
                  Publish research in the CMS and your latest article appears here as the featured story.
                </p>
                <div className="mt-8 flex flex-wrap gap-4">
                  <Button
                    size="lg"
                    className="rounded-lg h-12 px-7 bg-blue-600 hover:bg-blue-700"
                    onClick={() => navigate('/admin/articles/new')}
                  >
                    Write your first article <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="lg"
                    className="rounded-lg h-12 px-7 border-white/20 text-white hover:bg-white/10"
                    onClick={() => navigate('/markets/stocks')}
                  >
                    View Markets
                  </Button>
                </div>
              </>
            )}

            <div className="flex flex-wrap gap-2 mt-10">
              {quickLinks.map((link) => (
                <button
                  key={link.path}
                  type="button"
                  onClick={() => navigate(link.path)}
                  className="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm text-slate-300 hover:border-blue-500/50 hover:text-white transition-colors"
                >
                  {link.title}
                </button>
              ))}
            </div>
          </motion.div>

          <motion.aside
            initial={{ opacity: 0, x: 25 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="lg:col-span-4"
          >
            <div className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
              <div className="border-b border-white/10 px-6 py-5">
                <h2 className="text-lg font-bold text-white">Recent Research</h2>
                <p className="text-sm text-slate-400 mt-1">Latest published articles</p>
              </div>

              <div className="divide-y divide-white/10">
                {recentLoading ? (
                  Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="px-6 py-4 animate-pulse">
                      <div className="h-4 bg-white/10 rounded w-3/4 mb-2" />
                      <div className="h-3 bg-white/5 rounded w-1/2" />
                    </div>
                  ))
                ) : recentArticles.length === 0 ? (
                  <p className="px-6 py-8 text-sm text-slate-500 text-center">
                    No articles yet — publish from CMS to populate this list.
                  </p>
                ) : (
                  recentArticles.map((article) => (
                    <button
                      key={article.id}
                      type="button"
                      onClick={() => navigate(`/article/${article.slug}`)}
                      className="flex w-full gap-4 px-6 py-4 hover:bg-white/5 text-left transition-colors"
                    >
                      <img
                        src={article.image}
                        alt=""
                        className="w-16 h-16 rounded-lg object-cover shrink-0 bg-slate-800"
                      />
                      <div className="min-w-0">
                        <p className="font-medium text-white text-sm line-clamp-2 leading-snug">
                          {article.title}
                        </p>
                        <p className="text-xs text-slate-500 mt-1.5">{article.publishedLabel}</p>
                      </div>
                    </button>
                  ))
                )}
              </div>

              <div className="border-t border-white/10 p-4">
                <Button
                  variant="ghost"
                  className="w-full text-blue-400 hover:text-blue-300 hover:bg-white/5"
                  onClick={() => navigate('/sections/live-articles')}
                >
                  View all research
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          </motion.aside>
        </div>
      </div>
    </section>
  );
}
