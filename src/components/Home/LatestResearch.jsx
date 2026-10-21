import { motion } from 'framer-motion';
import { Clock3, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import usePublishedArticles from '@/hooks/usePublishedArticles';
import useFeaturedArticle from '@/hooks/useFeaturedArticle';

export default function LatestResearch() {
  const navigate = useNavigate();
  const { article: featured } = useFeaturedArticle();
  const { articles, loading } = usePublishedArticles({
    limit: 6,
    excludeSlug: featured?.slug,
    offset: featured ? 0 : 0,
  });

  return (
    <section className="bg-slate-950 py-20 lg:py-24">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-12">
          <div>
            <p className="text-blue-400 uppercase tracking-widest text-sm font-semibold">
              Research Feed
            </p>
            <h2 className="text-3xl md:text-4xl font-bold text-white mt-2">
              Latest Research
            </h2>
            <p className="text-slate-400 mt-2">
              Published analysis from the AGI research team
            </p>
          </div>
          <Button
            variant="outline"
            className="border-white/20 text-white hover:bg-white/10 shrink-0"
            onClick={() => navigate('/sections/live-articles')}
          >
            View all research
          </Button>
        </div>

        {loading ? (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-8">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-80 rounded-2xl bg-white/5 animate-pulse" />
            ))}
          </div>
        ) : articles.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-12 text-center">
            <p className="text-slate-300 text-lg font-medium">No published research yet</p>
            <p className="text-slate-500 mt-2 max-w-md mx-auto">
              Publish articles in the CMS and they will appear here automatically.
            </p>
            <Button
              className="mt-6 bg-blue-600 hover:bg-blue-700"
              onClick={() => navigate('/sections/live-articles')}
            >
              Browse research library
            </Button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-8">
            {articles.map((article, index) => (
              <motion.article
                key={article.id}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.06 }}
                className="group rounded-2xl border border-white/10 bg-white/5 overflow-hidden hover:border-blue-500/40 transition-colors cursor-pointer"
                onClick={() => navigate(`/article/${article.slug}`)}
              >
                <div className="aspect-video overflow-hidden bg-slate-900">
                  <img
                    src={article.image}
                    alt={article.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    loading="lazy"
                  />
                </div>
                <div className="p-6">
                  <span className="text-blue-400 text-xs font-semibold uppercase tracking-wide">
                    {article.category}
                  </span>
                  <h3 className="mt-3 text-xl font-semibold text-white group-hover:text-blue-300 transition-colors line-clamp-2">
                    {article.title}
                  </h3>
                  {article.excerpt && (
                    <p className="mt-3 text-slate-400 text-sm leading-relaxed line-clamp-3">
                      {article.excerpt}
                    </p>
                  )}
                  <div className="mt-5 flex items-center justify-between">
                    <span className="flex items-center gap-2 text-xs text-slate-500">
                      <Clock3 size={14} />
                      {article.readTime}
                    </span>
                    <span className="inline-flex items-center text-sm text-blue-400 font-medium">
                      Read
                      <ArrowRight size={14} className="ml-1 group-hover:translate-x-1 transition-transform" />
                    </span>
                  </div>
                </div>
              </motion.article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
