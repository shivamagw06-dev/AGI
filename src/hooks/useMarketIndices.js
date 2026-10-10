import { useEffect, useState } from 'react';
import { getIndices } from '@/api/indianApi';

const FALLBACK = [
  { name: 'NIFTY 50', value: '—', change: 0 },
  { name: 'SENSEX', value: '—', change: 0 },
  { name: 'NIFTY BANK', value: '—', change: 0 },
  { name: 'INDIA VIX', value: '—', change: 0 },
];

/**
 * @param {boolean} [enabled=true] Fetch only when true. The Markets dropdown
 *   passes false until it is first opened, so a nav menu most visitors never
 *   touch costs no request on page load. Defaults to true, so existing callers
 *   behave exactly as before.
 */
export default function useMarketIndices(enabled = true) {
  const [indices, setIndices] = useState(FALLBACK);
  const [loading, setLoading] = useState(enabled);

  useEffect(() => {
    if (!enabled) return undefined;
    let cancelled = false;

    getIndices()
      .then((data) => {
        if (cancelled) return;
        const list = (data?.indices || []).slice(0, 8).map((idx) => ({
          name: idx.name,
          value: idx.value ?? idx.price ?? idx.last ?? '—',
          change: idx.change ?? idx.percentChange ?? idx.per_change ?? 0,
        }));
        if (list.length) setIndices(list);
      })
      .catch(() => {
        if (!cancelled) setIndices(FALLBACK);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [enabled]);

  return { indices, loading };
}
