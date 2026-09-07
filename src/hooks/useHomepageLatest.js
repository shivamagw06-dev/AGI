import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { HOMEPAGE_LATEST_TAG, mapArticleForCard } from '@/lib/articleUtils';
import { queryArticlesSelectingLive } from '@/lib/liveArticle';

export default function useHomepageLatest(limit = 7) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      const { data, error } = await queryArticlesSelectingLive((select) =>
        supabase
          .from('articles')
          .select(select)
          .eq('status', 'published')
          .contains('tags', [HOMEPAGE_LATEST_TAG])
          .order('published_at', { ascending: false })
          .limit(limit)
      );

      if (cancelled) return;
      setArticles(error ? [] : (data || []).map(mapArticleForCard).filter(Boolean));
      setLoading(false);
    }

    load();
    return () => { cancelled = true; };
  }, [limit]);

  return { articles, loading };
}
