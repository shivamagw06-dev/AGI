import { useEffect, useState } from 'react';
import { fetchEntity, fetchEntityFull, searchEntities } from '@/lib/intelligencePlatformApi';

export function useIntelligenceEntity(slug, { refresh = false, full = false } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(Boolean(slug));
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!slug) return;
    let mounted = true;
    setLoading(true);
    setError(null);
    const fetcher = full ? fetchEntityFull : fetchEntity;
    fetcher(slug, { refresh })
      .then((payload) => {
        if (mounted) setData(payload);
      })
      .catch((e) => {
        if (mounted) setError(e.message);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [slug, refresh, full]);

  return { data, loading, error };
}

export function useUniversalSearch(query, { limit = 8, debounceMs = 200 } = {}) {
  const [result, setResult] = useState({ groups: [], total: 0, query: '', took_ms: 0 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const q = String(query || '').trim();
    if (q.length < 2) {
      setResult({ groups: [], total: 0, query: q, took_ms: 0 });
      return;
    }
    let mounted = true;
    const timer = setTimeout(() => {
      setLoading(true);
      searchEntities(q, { limit })
        .then((payload) => {
          if (mounted) setResult(payload);
        })
        .catch(() => {
          if (mounted) setResult({ groups: [], total: 0, query: q, took_ms: 0 });
        })
        .finally(() => {
          if (mounted) setLoading(false);
        });
    }, debounceMs);
    return () => {
      mounted = false;
      clearTimeout(timer);
    };
  }, [query, limit, debounceMs]);

  return { ...result, loading };
}
