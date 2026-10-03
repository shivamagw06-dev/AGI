import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Clock3 } from 'lucide-react';
import PageShell from '@/components/Layout/PageShell';
import { getCategoryById } from '@/config/contentCategories';
import { supabase } from '@/lib/supabaseClient';
import { formatArticleDate } from '@/lib/articleUtils';

export default function SectionArticlesPage({ overrideId }) {
  const { sectionId: paramId } = useParams();
  const sectionId = overrideId || paramId;
  const category = getCategoryById(sectionId);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!category?.section) return;
    let cancelled = false;

    (async () => {
      setLoading(true);
      const { data, error } = await supabase
        .from('articles')
        .select('id, title, slug, excerpt, cover_url, section, tags, published_at')
        .eq('status', 'published')
        .eq('section', category.section)
        .order('published_at', { ascending: false })
        .limit(48);

      if (cancelled) return;

      if (!error && data?.length) {
        setArticles(data);
      } else {
        const { data: fallback } = await supabase
          .from('articles')
          .select('id, title, slug, excerpt, cover_url, section, tags, published_at')
          .eq('status', 'published')
          .ilike('section', `%${category.section}%`)
          .order('published_at', { ascending: false })
          .limit(48);

        if (!cancelled) setArticles(fallback || []);
      }
      setLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [category?.section]);

  if (!category) {
    return (
      <PageShell theme="light" title="Section not found" backTo="/">
        <p className="text-slate-600">This section does not exist.</p>
      </PageShell>
    );
  }

  return (
    <PageShell
      theme="light"
      eyebrow="Updates"
      title={category.title}
      description={category.description}
      metaTitle={`${category.title} | Agarwal Global Investments`}
    >
      {loading ? (
        <div className="grid md:grid-cols-2 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-48 rounded-xl bg-slate-100 animate-pulse" />
          ))}
        </div>
      ) : articles.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-sm">
          <p className="text-slate-700 font-medium">No articles published yet</p>
          <p className="text-slate-500 text-sm mt-2 max-w-md mx-auto">
            Publish articles in the CMS with section &quot;{category.section}&quot; and they will appear here.
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
          {articles.map((article) => (
            <Link
              key={article.id}
              to={`/article/${article.slug}`}
              className="group rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm hover:shadow-md hover:border-slate-300 transition-all"
            >
              {article.cover_url && (
                <img
                  src={article.cover_url}
                  alt=""
                  className="w-full h-44 object-cover"
                />
              )}
              <div className="p-5">
                <h2 className="font-semibold text-slate-900 group-hover:text-blue-800 transition-colors line-clamp-2">
                  {article.title}
                </h2>
                {article.excerpt && (
                  <p className="mt-2 text-sm text-slate-600 line-clamp-3 leading-relaxed">
                    {article.excerpt}
                  </p>
                )}
                <div className="mt-4 flex items-center gap-1.5 text-xs text-slate-500">
                  <Clock3 size={13} />
                  {formatArticleDate(article.published_at)}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </PageShell>
  );
}
