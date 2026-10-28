import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';

/** Lightweight, public preview feed for analyst-authored research notes. */
export default function useResearchNotesPreview(limit = 3) {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function load() {
      const { data, error } = await supabase
        .from('research_notes')
        .select('id,title,summary,tags,published_at,created_at')
        .order('published_at', { ascending: false })
        .limit(limit);

      if (!active) return;
      if (error) {
        console.warn('[research notes] preview unavailable:', error.message);
        setNotes([]);
      } else {
        setNotes(data || []);
      }
      setLoading(false);
    }

    load();
    return () => {
      active = false;
    };
  }, [limit]);

  return { notes, loading };
}
