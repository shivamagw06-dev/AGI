import { useEffect, useState } from 'react';
import { getUiHome } from '@/lib/uiApi';
import { getMarketCycleId, msUntilNextMarketCycle, MARKET_REFRESH_MS } from '@/lib/marketCache';

const STORAGE_KEY = 'agi_market_snapshot_v1';
const STORAGE_META_KEY = 'agi_market_snapshot_v1_meta';

function readCache() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    const metaRaw = sessionStorage.getItem(STORAGE_META_KEY);
    if (!raw) return null;
    const items = JSON.parse(raw);
    if (!Array.isArray(items) || !items.length) return null;
    const meta = metaRaw ? JSON.parse(metaRaw) : {};
    return {
      items,
      cycleId: meta.cycleId || null,
      updatedAt: meta.updatedAt || null,
      stale: Boolean(meta.stale),
    };
  } catch {
    return null;
  }
}

function writeCache(items, { stale = false, updatedAt = null } = {}) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    sessionStorage.setItem(
      STORAGE_META_KEY,
      JSON.stringify({
        cycleId: getMarketCycleId(),
        updatedAt: updatedAt || new Date().toISOString(),
        stale,
      })
    );
  } catch {
    /* quota / private mode */
  }
}

function formatUpdatedLabel(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    timeZone: 'Asia/Kolkata',
  });
}

/**
 * Live market strip quotes from /api/ui/home market_snapshot
 * (Groww / NSE / Yahoo — real prices, not AGI sentiment scores).
 * Keeps last successful snapshot when live providers are rate-limited.
 */
export default function useMarketSnapshot() {
  const cached = readCache();
  const [items, setItems] = useState(Array.isArray(cached?.items) ? cached.items : []);
  const [loading, setLoading] = useState(!cached?.items?.length);
  const [stale, setStale] = useState(Boolean(cached?.stale));
  const [updatedAt, setUpdatedAt] = useState(cached?.updatedAt || null);

  useEffect(() => {
    let cancelled = false;
    let timeoutId = null;

    async function load(force = false) {
      if (!force) {
        const fresh = readCache();
        if (fresh?.items?.length && fresh.cycleId === getMarketCycleId() && !fresh.stale) {
          if (!cancelled) {
            setItems(fresh.items);
            setStale(false);
            setUpdatedAt(fresh.updatedAt);
            setLoading(false);
          }
          return;
        }
      }
      try {
        const data = await getUiHome();
        const snap = Array.isArray(data?.market_snapshot) ? data.market_snapshot : [];
        const live = snap.filter((row) => Number(row?.price) > 0);
        const liveUnavailable = live.some((row) => row.liveUnavailable || row.stale);
        if (!cancelled) {
          if (live.length) {
            writeCache(live, {
              stale: liveUnavailable,
              updatedAt: live[0]?.updatedAt || new Date().toISOString(),
            });
            setItems(live);
            setStale(Boolean(liveUnavailable));
            setUpdatedAt(live[0]?.updatedAt || new Date().toISOString());
          } else {
            // Keep last good — never blank the strip after a successful print.
            const previous = readCache();
            if (previous?.items?.length) {
              writeCache(previous.items, { stale: true, updatedAt: previous.updatedAt });
              setItems(previous.items);
              setStale(true);
              setUpdatedAt(previous.updatedAt);
            }
          }
        }
      } catch {
        const previous = readCache();
        if (!cancelled && previous?.items?.length) {
          setItems(previous.items);
          setStale(true);
          setUpdatedAt(previous.updatedAt);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    function scheduleNext() {
      const wait = Math.max(250, Math.min(msUntilNextMarketCycle(), MARKET_REFRESH_MS));
      timeoutId = setTimeout(async () => {
        await load(true);
        if (!cancelled) scheduleNext();
      }, wait);
    }

    load(false).then(() => {
      if (!cancelled) scheduleNext();
    });

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, []);

  return {
    items,
    loading,
    stale,
    updatedAt,
    updatedLabel: formatUpdatedLabel(updatedAt),
  };
}
