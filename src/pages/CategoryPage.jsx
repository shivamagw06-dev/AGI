import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Clock3, ArrowLeft } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import useCategories from '@/hooks/useCategories';
import { formatArticleDate } from '@/lib/articleUtils';

export default function CategoryPage() {
  const { slug } = useParams();
  const { categories } = useCategories();
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  const category = categories.find((c) => c.slug === slug);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;

    (async () => {
      setLoading(true);
      const categoryName = category?.name || slug.replace(/-/g, ' ');

      const { data, error } = await supabase
        .from('articles')
        .select('id, title, slug, excerpt, cover_url, section, tags, published_at')
        .eq('status', 'published')
        .eq('section', categoryName)
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
          .ilike('section', `%${categoryName}%`)
          .order('published_at', { ascending: false })
          .limit(48);

        if (!cancelled) setArticles(fallback || []);
      }

      setLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [slug, category?.name]);

  const title = category?.name || slug?.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="bg-white min-h-screen reuters-page">
      <Helmet>
        <title>{title} | Agarwal Global Investments</title>
        <meta name="description" content={category?.description || `Browse ${title} articles and market updates.`} />
      </Helmet>

      <div className="max-w-6xl mx-auto px-6 py-12">
        <Link to="/" className="inline-flex items-center gap-2 text-xs text-[#767676] hover:text-[#ff8000] mb-6">
          <ArrowLeft size={14} /> Back to Home
        </Link>

        <h1 className="reuters-heading text-3xl md:text-4xl border-b border-[#dddddd] pb-4">{title}</h1>
        {category?.description && (
          <p className="reuters-body mt-4 text-base max-w-3xl">{category.description}</p>
        )}

        {loading ? (
          <p className="mt-12 text-[#767676] text-center text-sm">Loading articles…</p>
        ) : articles.length === 0 ? (
          <div className="mt-12 text-center py-12 reuters-card">
            <p className="text-[#555555]">No published articles in this category yet.</p>
          </div>
        ) : (
          <div className="mt-10 grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {articles.map((article) => (
              <Link
                key={article.id}
                to={`/article/${article.slug}`}
                className="reuters-card group overflow-hidden"
              >
                {article.cover_url && (
                  <img src={article.cover_url} alt="" className="w-full h-40 object-cover border-b border-[#dddddd]" />
                )}
                <div className="p-4">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-[#767676]">
                    {article.section}
                  </span>
                  <h2 className="mt-1 text-base font-bold text-[#111111] group-hover:text-[#ff8000] transition-colors line-clamp-2">
                    {article.title}
                  </h2>
                  {article.excerpt && (
                    <p className="mt-2 text-sm text-[#555555] line-clamp-3 leading-relaxed">{article.excerpt}</p>
                  )}
                  <div className="mt-3 flex items-center gap-1.5 text-[11px] text-[#767676]">
                    <Clock3 size={12} />
                    {formatArticleDate(article.published_at)}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
