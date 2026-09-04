import { useEffect, useMemo, useState } from 'react';
import { getIpoPlatform } from '@/lib/ipoApi';
import { supabase } from '@/lib/supabaseClient';
import {
  enrichArticle,
  intelligencePanel,
  aggregateInsights,
  compareSources,
  detectContradictions,
} from '@/lib/ipoIntelligence';

export default function useIpoPlatform() {
  const [ipoState, setIpoState] = useState({ loading: true, data: null, error: null });
  const [articleState, setArticleState] = useState({ loading: true, articles: [], error: null });

  useEffect(() => {
    let active = true;
    getIpoPlatform()
      .then((data) => active && setIpoState({ loading: false, data, error: null }))
      .catch((error) => active && setIpoState({ loading: false, data: null, error }));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setArticleState((prev) => ({ ...prev, loading: true }));
      const select =
        'id, title, slug, excerpt, cover_url, tags, published_at, section, status, author_id, equity_research';
      let { data, error } = await supabase
        .from('articles')
        .select(select)
        .eq('status', 'published')
        .eq('section', 'IPOs')
        .order('published_at', { ascending: false })
        .limit(80);

      if (error || !data?.length) {
        const fallback = await supabase
          .from('articles')
          .select(select)
          .eq('status', 'published')
          .or('section.ilike.%IPO%,title.ilike.%IPO%')
          .order('published_at', { ascending: false })
          .limit(80);
        data = fallback.data || data || [];
        error = fallback.error || error;
      }

      if (cancelled) return;

      const chronological = [...(data || [])].sort((a, b) =>
        String(a.published_at || '').localeCompare(String(b.published_at || ''))
      );
      const enriched = [];
      for (const row of chronological) {
        enriched.push(enrichArticle(row, enriched.slice(-3)));
      }
      enriched.reverse();

      setArticleState({
        loading: false,
        articles: enriched,
        error: error?.message || null,
      });
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const research = useMemo(() => {
    const articles = articleState.articles;
    return {
      articles,
      panel: intelligencePanel(articles),
      insights: aggregateInsights(articles),
      comparison: compareSources(articles),
      contradictions: detectContradictions(articles),
      publishers: [...new Set(articles.map((a) => a.publisher))],
    };
  }, [articleState.articles]);

  return {
    loading: ipoState.loading || articleState.loading,
    ipoLoading: ipoState.loading,
    articleLoading: articleState.loading,
    platform: ipoState.data,
    error: ipoState.error,
    articleError: articleState.error,
    research,
  };
}
