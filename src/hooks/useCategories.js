import { useCallback, useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { DEFAULT_CATEGORIES, getLocalCategories, saveLocalCategories } from '@/lib/cmsCategories';
import { toSlug } from '@/lib/articleUtils';

export default function useCategories() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState('loading');

  const load = useCallback(async () => {
    setLoading(true);
    const { data, error } = await supabase
      .from('article_categories')
      .select('*')
      .order('sort_order', { ascending: true });

    if (!error && data?.length) {
      setCategories(data.filter((c) => c.is_active !== false));
      setSource('supabase');
    } else {
      setCategories(getLocalCategories());
      setSource('local');
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const saveCategory = async (category) => {
    const payload = {
      name: category.name,
      slug: category.slug || toSlug(category.name),
      description: category.description || '',
      sort_order: category.sort_order ?? categories.length + 1,
      is_active: category.is_active !== false,
      updated_at: new Date().toISOString(),
    };

    if (source === 'supabase') {
      if (category.id && !String(category.id).startsWith('local-')) {
        const { error } = await supabase
          .from('article_categories')
          .update(payload)
          .eq('id', category.id);
        if (error) throw error;
      } else {
        const { error } = await supabase.from('article_categories').insert(payload);
        if (error) throw error;
      }
      await load();
      return;
    }

    const next = category.id
      ? categories.map((c) => (c.id === category.id ? { ...c, ...payload, id: category.id } : c))
      : [...categories, { ...payload, id: `local-${Date.now()}` }];
    saveLocalCategories(next);
    setCategories(next.filter((c) => c.is_active !== false));
  };

  const deleteCategory = async (id) => {
    if (source === 'supabase' && !String(id).startsWith('local-')) {
      const { error } = await supabase
        .from('article_categories')
        .update({ is_active: false, updated_at: new Date().toISOString() })
        .eq('id', id);
      if (error) throw error;
      await load();
      return;
    }

    const next = categories.filter((c) => c.id !== id);
    saveLocalCategories(next);
    setCategories(next);
  };

  const reorderCategory = async (id, direction) => {
    const idx = categories.findIndex((c) => c.id === id);
    if (idx < 0) return;
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= categories.length) return;

    const next = [...categories];
    [next[idx], next[swapIdx]] = [next[swapIdx], next[idx]];
    const reordered = next.map((c, i) => ({ ...c, sort_order: i + 1 }));

    if (source === 'supabase') {
      await Promise.all(
        reordered.map((c) =>
          supabase.from('article_categories').update({ sort_order: c.sort_order }).eq('id', c.id)
        )
      );
      await load();
      return;
    }

    saveLocalCategories(reordered);
    setCategories(reordered);
  };

  const seedDefaults = async () => {
    if (source === 'supabase') {
      for (const cat of DEFAULT_CATEGORIES) {
        await supabase.from('article_categories').upsert(cat, { onConflict: 'slug' });
      }
      await load();
      return;
    }
    saveLocalCategories(DEFAULT_CATEGORIES.map((c, i) => ({ ...c, id: `local-${i}`, is_active: true })));
    setCategories(getLocalCategories());
  };

  return {
    categories,
    loading,
    source,
    reload: load,
    saveCategory,
    deleteCategory,
    reorderCategory,
    seedDefaults,
  };
}
