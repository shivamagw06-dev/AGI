// src/components/Opinions.jsx
import React, { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { supabase } from '@/lib/supabaseClient';

const POLL_INTERVAL_MS = 60000;

function estimateReadTime(html) {
  if (!html) return 1;
  // remove tags, count words
  const text = html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  const words = text ? text.split(' ').length : 0;
  return Math.max(1, Math.round(words / 200)); // 200 wpm
}

export default function Opinions() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchOpinions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch articles with section = opinions-editorials
      const q1 = supabase
        .from('articles')
        .select('id, title, slug, content, excerpt, cover_url, author, created_at, status, section, sections')
        .eq('status', 'published')
        .eq('section', 'opinions-editorials')
        .order('created_at', { ascending: false });

      // Fetch articles where sections array contains opinions-editorials
      const q2 = supabase
        .from('articles')
        .select('id, title, slug, content, excerpt, cover_url, author, created_at, status, section, sections')
        .eq('status', 'published')
        .contains('sections', ['opinions-editorials'])
        .order('created_at', { ascending: false });

      // run both queries in parallel
      const [{ data: data1, error: err1 }, { data: data2, error: err2 }] = await Promise.all([q1, q2]);

      if (err1 && err1.code !== 'PGRST116') throw err1; // PGRST116 may appear if column missing in some setups
      if (err2 && err2.code !== 'PGRST116') throw err2;

      const list1 = Array.isArray(data1) ? data1 : [];
      const list2 = Array.isArray(data2) ? data2 : [];

      // merge and dedupe by id
      const combinedMap = new Map();
      [...list1, ...list2].forEach((a) => {
        if (!combinedMap.has(a.id)) combinedMap.set(a.id, a);
      });

      const combined = Array.from(combinedMap.values()).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setArticles(combined);
    } catch (e) {
      console.error('Failed to fetch opinions', e);
      setError(e?.message || String(e));
      toast({
        title: 'Failed to load opinions',
        description: e?.message || 'See console for details',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchOpinions();
    const id = setInterval(fetchOpinions, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchOpinions]);

  return (
    <section className="py-20 bg-background">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
          <h1 className="text-4xl sm:text-5xl font-bold text-foreground mb-3">Opinions & Editorials</h1>
          <p className="text-lg text-foreground/70 max-w-3xl mx-auto">
            Founder’s takes, guest columns and perspectives from our contributors.
          </p>
        </motion.div>

        <div className="mb-6 flex items-center justify-end gap-3">
          <button
            onClick={() => {
              fetchOpinions();
              toast({ title: 'Refreshing', description: 'Fetching latest opinions...' });
            }}
            className="inline-flex items-center gap-2 px-3 py-1.5 border rounded shadow-sm hover:bg-gray-50"
            aria-label="Refresh opinions"
          >
            <RefreshCw className="w-4 h-4" />
            <span className="text-sm">Refresh</span>
          </button>
        </div>

        {loading && (
          <div className="space-y-6">
            {[1, 2].map((n) => (
              <div key={n} className="animate-pulse bg-card border border-border rounded-lg p-6 flex gap-6">
                <div className="w-36 h-24 bg-gray-200 rounded" />
                <div className="flex-1">
                  <div className="h-5 w-1/3 bg-gray-200 rounded mb-3" />
                  <div className="h-4 w-1/2 bg-gray-200 rounded mb-2" />
                  <div className="h-3 w-2/3 bg-gray-200 rounded" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="bg-red-50 border border-red-200 rounded p-4 text-sm text-red-700 mb-6">
            Error: {error}
          </div>
        )}

        {!loading && !error && articles.length === 0 && (
          <div className="bg-card border border-border rounded-lg p-12 text-center text-muted-foreground">
            <div className="mb-3 text-xl font-semibold">No opinions yet</div>
            <div className="max-w-xl mx-auto">This section is under construction — add opinion pieces via the editor to populate this page.</div>
          </div>
        )}

        <div className="space-y-8">
          {articles.map((a, i) => {
            const readMin = estimateReadTime(a.content || a.excerpt || '');
            const cover = a.cover_url || '';
            const author = a.author || '—';
            const dateStr = a.created_at ? new Date(a.created_at).toLocaleDateString() : '—';

            return (
              <motion.article
                key={a.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="bg-card border border-border rounded-lg overflow-hidden hover:shadow-md cursor-pointer"
                onClick={() => navigate(`/article/${a.slug || a.id}`)}
              >
                <div className="md:flex">
                  <div className="md:w-2/5 h-48 md:h-40 relative">
                    {cover ? (
                      // cover image
                      <img src={cover} alt={a.title} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full bg-gray-100 flex items-center justify-center text-muted-foreground">
                        No cover
                      </div>
                    )}
                  </div>

                  <div className="p-6 md:flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-sm text-muted-foreground">{dateStr} • {readMin} min</div>
                      <div className="text-xs text-muted-foreground">{a.section || (a.sections && a.sections.join(', '))}</div>
                    </div>
                    <h3 className="text-2xl font-semibold text-card-foreground mb-2">{a.title || 'Untitled'}</h3>
                    <p className="text-muted-foreground line-clamp-3 mb-4">{a.excerpt || (a.content ? a.content.replace(/<[^>]+>/g, '').slice(0, 220) + '…' : '')}</p>

                    <div className="flex items-center gap-3 text-sm">
                      <div className="text-sm font-medium">{author}</div>
                      <div className="text-sm text-muted-foreground">• View full piece</div>
                    </div>
                  </div>
                </div>
              </motion.article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
