import { useCallback, useEffect, useState } from 'react';
import API_ORIGIN from '@/config';

const API_BASE = API_ORIGIN || '';

async function fetchJson(path) {
  const res = await fetch(`${API_BASE}${path}`, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`PE API ${res.status}`);
  return res.json();
}

export function usePeOverview(options = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const normalized = typeof options === 'string' ? { sector: options } : options;
      const params = new URLSearchParams();
      Object.entries(normalized || {}).forEach(([key, value]) => value !== null && value !== undefined && value !== '' && params.set(key, String(value)));
      setData(await fetchJson('/api/pe/overview' + (params.size ? '?' + params : '')));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [JSON.stringify(options)]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload };
}

export function usePeFirm(slug) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const json = await fetchJson(`/api/pe/firms/${encodeURIComponent(slug)}`);
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [slug]);

  return { data, loading, error };
}
