import { useCallback, useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/contexts/AuthContext';
import { isAdmin } from '@/lib/adminAuth';

export default function useArticlesAdmin() {
  const { user } = useAuth();
  const admin = isAdmin(user);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!user?.id) {
      setArticles([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    let query = supabase
      .from('articles')
      .select(
        'id, title, slug, section, excerpt, status, published_at, created_at, cover_url, tags, author_id, intelligence_document_id, intelligence_ingested_at, last_learned_at, learn_status, learn_count'
      )
      .order('created_at', { ascending: false });

    // Authors only see articles they uploaded; admins see the full CMS library.
    if (!isAdmin(user)) {
      query = query.eq('author_id', user.id);
    }

    const { data, error: fetchError } = await query;

    if (fetchError) {
      setError(fetchError.message);
      setArticles([]);
    } else {
      setArticles(data || []);
    }
    setLoading(false);
  }, [user]);

  useEffect(() => {
    load();
  }, [load]);

  const deleteArticle = async (id) => {
    let query = supabase.from('articles').delete().eq('id', id);
    if (!admin && user?.id) {
      query = query.eq('author_id', user.id);
    }
    const { error: deleteError } = await query;
    if (deleteError) throw deleteError;
    await load();
  };

  const stats = {
    total: articles.length,
    published: articles.filter((a) => a.status === 'published').length,
    drafts: articles.filter((a) => a.status === 'draft' && !(a.tags || []).includes('intelligence-only')).length,
    intelligence: articles.filter(
      (a) => a.status === 'intelligence' || (Array.isArray(a.tags) && a.tags.includes('intelligence-only'))
    ).length,
  };

  return { articles, loading, error, reload: load, deleteArticle, stats };
}
