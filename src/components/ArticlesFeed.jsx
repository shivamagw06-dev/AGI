import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { Calendar, Clock, ArrowRight, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import { supabase } from '@/lib/supabaseClient';
import {
  RESEARCH_DESKS,
  articleMatchesDesk,
  getDeskForSection,
} from '@/lib/deskSections';

const DEFAULT_CATEGORIES = ['All', ...RESEARCH_DESKS.map((desk) => desk.label)];

/**
 * Props:
 *   section?: string  -> filters by articles.section in DB (e.g., 'Research Notes')
 */
export default function ArticlesFeed({ section, variant = 'light' }) {
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  const { toast } = useToast();

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      // Build the query
      let query = supabase
        .from('articles')
        .select('id,title,slug,excerpt,cover_url,tags,published_at,section,status')
        .eq('status', 'published')
        .order('published_at', { ascending: false })
        .limit(36);

      if (section) query = query.eq('section', section);

      const { data, error } = await query;
      if (cancelled) return;

      if (error) {
        console.error(error);
        toast({ title: 'Failed to load articles', description: error.message, variant: 'destructive' });
        setArticles([]);
      } else {
        // Normalize for UI
        const mapped = (data || []).map((a) => ({
          id: a.id,
          title: a.title,
          excerpt: a.excerpt,
          slug: a.slug,
          image: a.cover_url || 'https://images.unsplash.com/photo-1595872018818-97555653a011',
          section: a.section,
          category: getDeskForSection(a.section)?.label || a.section || 'Research',
          date: a.published_at,
          readTime: estimateReadTime(a.excerpt),
        }));
        setArticles(mapped);
      }
      setLoading(false);
    };

    load();
    return () => { cancelled = true; };
  }, [section, toast]);

  // Build categories set from data + defaults
  const categories = useMemo(() => {
    const set = new Set(DEFAULT_CATEGORIES);
    articles.forEach((a) => set.add(a.category));
    return Array.from(set);
  }, [articles]);

  const filteredArticles =
    selectedCategory === 'All'
      ? articles
      : articles.filter((article) => {
          const desk = RESEARCH_DESKS.find((d) => d.label === selectedCategory);
          if (!desk) return article.category === selectedCategory;
          return articleMatchesDesk(article, desk.id);
        });

  const pageTitle = section || 'Research';
  const isLight = variant === 'light';

  return (
    <div className={`min-h-screen reuters-page ${isLight ? 'bg-white' : 'bg-slate-950'}`}>
      <Helmet>
        <title>{pageTitle} | Agarwal Global Investments</title>
        <meta
          name="description"
          content="Browse institutional research, macro analysis, and market commentary from Agarwal Global Investments."
        />
      </Helmet>

      <div className={`border-b ${isLight ? 'border-[#dddddd] bg-white' : 'border-white/10'}`}>
        <div className="max-w-6xl mx-auto px-6 py-10">
          <Link
            to="/"
            className={`inline-flex items-center gap-2 text-xs mb-5 transition-colors ${
              isLight ? 'text-[#767676] hover:text-[#ff8000]' : 'text-slate-400 hover:text-white'
            }`}
          >
            <ArrowLeft size={14} /> Back to Home
          </Link>
          <span className={`text-xs font-semibold uppercase tracking-widest ${isLight ? 'text-[#767676]' : 'text-blue-400'}`}>
            Research
          </span>
          <h1 className={`mt-2 text-3xl font-bold tracking-tight ${isLight ? 'text-[#111111] reuters-heading' : 'text-white'}`}>
            {pageTitle}
          </h1>
          <p className={`mt-3 text-base max-w-2xl ${isLight ? 'text-[#555555]' : 'text-slate-400'}`}>
            In-depth reports, sector analysis, and investment insights.
          </p>
        </div>
      </div>

      <section id="articles" className="py-12">
        <div className="max-w-6xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="flex flex-wrap gap-2 mb-12"
        >
          {categories.map((category) => (
            <Button
              key={category}
              variant={selectedCategory === category ? 'default' : 'outline'}
              onClick={() => setSelectedCategory(category)}
              className={
                selectedCategory === category
                  ? 'bg-[#ff8000] hover:bg-[#e67300] text-white border-[#ff8000]'
                  : isLight
                    ? 'border-[#dddddd] text-[#555555] hover:bg-[#f7f7f7]'
                    : 'border-white/20 text-slate-300 hover:bg-white/10 hover:text-white'
              }
            >
              {category}
            </Button>
          ))}
        </motion.div>

        {/* Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className={`h-72 rounded-xl animate-pulse ${isLight ? 'bg-slate-100' : 'bg-white/5'}`} />
            ))}
          </div>
        ) : filteredArticles.length === 0 ? (
          <div className={`text-center py-16 rounded-xl border ${isLight ? 'border-slate-200 bg-slate-50' : 'border-white/10 bg-white/5'}`}>
            <p className={isLight ? 'text-slate-600' : 'text-slate-400'}>No articles published yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredArticles.map((article, index) => (
              <motion.article
                key={article.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.05 }}
                className={`overflow-hidden group flex flex-col transition-all ${
                  isLight
                    ? 'reuters-card'
                    : 'rounded-2xl border border-white/10 bg-white/5 hover:border-blue-500/40'
                }`}
              >
                <Link to={`/article/${article.slug}`} className="block">
                  <div className={`agi-cover agi-cover--16-9 relative ${isLight ? 'bg-slate-100' : 'bg-slate-900'}`}>
                    <img
                      className="group-hover:scale-105 transition-transform duration-500"
                      alt={article.title}
                      src={article.image}
                    />
                    <div className="absolute top-4 left-4">
                      <span className="bg-[#ff8000] text-white text-[10px] font-semibold uppercase px-2 py-0.5">
                        {article.category}
                      </span>
                    </div>
                  </div>
                </Link>

                <div className="p-5 flex flex-col flex-grow">
                  <div className={`flex items-center gap-4 text-xs mb-3 ${isLight ? 'text-slate-500' : 'text-slate-500'}`}>
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5" />
                      <span>{formatDate(article.date)}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" />
                      <span>{article.readTime}</span>
                    </div>
                  </div>

                  <Link to={`/article/${article.slug}`}>
                    <h3 className={`text-base font-bold mb-2 line-clamp-2 transition-colors ${
                      isLight ? 'text-[#111111] group-hover:text-[#ff8000]' : 'text-white group-hover:text-blue-300'
                    }`}>
                      {article.title}
                    </h3>
                  </Link>

                  <p className={`text-sm mb-4 line-clamp-3 flex-grow leading-relaxed ${isLight ? 'text-slate-600' : 'text-slate-400'}`}>
                    {article.excerpt}
                  </p>

                  <Link
                    to={`/article/${article.slug}`}
                    className="mt-auto inline-flex items-center text-xs font-semibold uppercase tracking-wide text-[#ff8000] hover:text-[#e67300]"
                  >
                    Read article
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </div>
              </motion.article>
            ))}
          </div>
        )}
        </div>
      </section>
    </div>
  );
}

/* —— utils —— */
function formatDate(d) {
  try {
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return '';
  }
}
function estimateReadTime(text = '') {
  const words = (text || '').split(/\s+/).filter(Boolean).length;
  const mins = Math.max(3, Math.round(words / 200)); // ~200 wpm, min 3 mins
  return `${mins} min read`;
}
