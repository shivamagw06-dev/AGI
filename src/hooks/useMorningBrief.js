import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { readingTime, formatArticleDate, formatTimeAgo } from '@/lib/articleUtils';

const MORNING_SECTIONS = [
  'Pre-Market Update',
  'Morning Market Update',
  "Today's Market Brief",
  'Market Opening Outlook',
];

const DEFAULT_BRIEF = {
  title: "Today's Market Brief",
  excerpt:
    'Your daily institutional-quality overview of Indian markets — what happened, what matters, and what to read next.',
  section: 'Research',
  slug: null,
  cover_url:
    'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80',
};

export default function useMorningBrief() {
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);

      for (const section of MORNING_SECTIONS) {
        const { data } = await supabase
          .from('articles')
          .select('id, title, slug, excerpt, section, tags, published_at, cover_url, content')
          .eq('status', 'published')
          .eq('section', section)
          .order('published_at', { ascending: false })
          .limit(1)
          .maybeSingle();

        if (cancelled) return;
        if (data) {
          setBrief({
            ...data,
            readTime: data.content ? readingTime(data.content) : 5,
            publishedLabel: formatArticleDate(data.published_at),
            timeAgo: formatTimeAgo(data.published_at),
            heroLabel: section.includes('Pre-Market')
              ? 'Morning Market Update'
              : section,
          });
          setLoading(false);
          return;
        }
      }

      const { data: latest } = await supabase
        .from('articles')
        .select('id, title, slug, excerpt, section, tags, published_at, cover_url, content')
        .eq('status', 'published')
        .order('published_at', { ascending: false })
        .limit(1)
        .maybeSingle();

      if (cancelled) return;

      if (latest) {
        setBrief({
          ...latest,
          readTime: latest.content ? readingTime(latest.content) : 5,
          publishedLabel: formatArticleDate(latest.published_at),
          timeAgo: formatTimeAgo(latest.published_at),
          heroLabel: latest.section || "Today's Research",
        });
      } else {
        setBrief({ ...DEFAULT_BRIEF, readTime: 4, heroLabel: "Today's Market Brief" });
      }
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { brief, loading };
}
