// src/components/SectionFeed.jsx
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '@/lib/supabaseClient';

export default function SectionFeed({ section }) {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    supabase.from('articles')
      .select('title, slug, excerpt, cover_url, tags, published_at')
      .eq('section', section).eq('status','published')
      .order('published_at', { ascending: false })
      .then(({ data }) => setRows(data || []));
  }, [section]);

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">{section}</h1>
        <Link to="/write" className="text-sm underline">+ New</Link>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {rows.map(a => (
          <Link key={a.slug} to={`/article/${a.slug}`} className="border rounded-lg overflow-hidden hover:shadow">
            {a.cover_url && <img src={a.cover_url} className="w-full h-40 object-cover" alt="" />}
            <div className="p-4">
              <h2 className="text-lg font-semibold">{a.title}</h2>
              <p className="text-sm text-muted-foreground line-clamp-3 mt-1">{a.excerpt}</p>
              <div className="text-xs text-muted-foreground mt-2">
                {a.published_at ? new Date(a.published_at).toLocaleDateString() : ''}
                {a.tags?.length ? <> · {a.tags[0]}</> : null}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
