import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { HOMEPAGE_FEATURED_TAG, mapArticleForCard } from '@/lib/articleUtils';
import { queryArticlesSelectingLive } from '@/lib/liveArticle';

export default function usePublishedArticles({
  limit = 6,
  excludeSlug = null,
  section = null,
  sections = null,
  offset = 0,
  featuredFirst = false,
} = {}) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const sectionsKey = Array.isArray(sections) ? sections.join('\u0001') : '';

  useEffect(() => {
    let cancelled = false;
    const sectionList = sectionsKey ? sectionsKey.split('\u0001') : null;

    async function load() {
      setLoading(true);
      setError(null);

      const [{ data, error: fetchError }, featuredResult] = await Promise.all([
        queryArticlesSelectingLive((select) => {
          let query = supabase
            .from('articles')
            .select(select)
            .eq('status', 'published')
            .order('published_at', { ascending: false })
            .range(offset, offset + limit + (excludeSlug ? 1 : 0) - 1);
          if (section) query = query.eq('section', section);
          else if (sectionList?.length) query = query.in('section', sectionList);
          return query;
        }),
        featuredFirst && !section && !sectionList?.length
          ? queryArticlesSelectingLive((select) =>
              supabase
                .from('articles')
                .select(select)
                .eq('status', 'published')
                .contains('tags', [HOMEPAGE_FEATURED_TAG])
                .limit(1)
            )
          : Promise.resolve({ data: null, error: null }),
      ]);
      if (cancelled) return;

      if (fetchError) {
        console.error('Failed to load articles:', fetchError);
        setArticles([]);
        setError(fetchError.message);
      } else {
        const featured = featuredResult?.error ? null : featuredResult?.data?.[0] || null;
        const merged = featured
          ? [featured, ...(data || []).filter((row) => row.id !== featured.id)]
          : data || [];
        const mapped = merged
          .filter((row) => !excludeSlug || row.slug !== excludeSlug)
          .slice(0, limit)
          .map(mapArticleForCard)
          .filter(Boolean);
        setArticles(mapped);
      }

      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [limit, excludeSlug, section, sectionsKey, offset, featuredFirst]);

  return { articles, loading, error };
}
