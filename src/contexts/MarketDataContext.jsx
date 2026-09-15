import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { getMarketIntelligence } from '@/api/marketApi';
import {
  MARKET_REFRESH_MS,
  readMarketCache,
  writeMarketCache,
  msUntilNextMarketCycle,
} from '@/lib/marketCache';

const EMPTY = {
  pulse: null,
  outlook: null,
  insightStrip: [],
  summary: '',
  sectors: [],
  stocksInFocus: [],
  breadth: { label: 'Neutral', advancing: 0, declining: 0 },
  indexSentiments: [],
  disclaimer: '',
};

const MarketDataContext = createContext(null);

/**
 * Market intelligence refreshes every 30 minutes on the shared wall-clock cycle
 * (same cadence as homepage Groww/Yahoo snapshot and /api/market/*).
 * Session cache prevents API calls on every page load / login within that window.
 */
export function MarketDataProvider({ children, pollMs = MARKET_REFRESH_MS, enabled = true }) {
  const cached = readMarketCache();
  const [intelligence, setIntelligence] = useState(cached ? { ...EMPTY, ...cached } : EMPTY);
  const [loading, setLoading] = useState(!cached);
  const busy = useRef(false);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return undefined;
    }
    let cancelled = false;
    let timeoutId = null;

    async function load(force = false) {
      if (busy.current) return;

      if (!force) {
        const fresh = readMarketCache();
        if (fresh) {
          if (!cancelled) {
            setIntelligence({ ...EMPTY, ...fresh });
            setLoading(false);
          }
          return;
        }
      }

      busy.current = true;
      try {
        const data = await getMarketIntelligence();
        if (!cancelled && data) {
          writeMarketCache(data);
          setIntelligence({ ...EMPTY, ...data });
        }
      } catch {
        /* keep last good data */
      } finally {
        busy.current = false;
        if (!cancelled) setLoading(false);
      }
    }

    function scheduleNext() {
      // Align to wall-clock :00 / :30 so strip + snapshot refresh together.
      const wait = Math.max(250, Math.min(msUntilNextMarketCycle(), pollMs));
      timeoutId = setTimeout(async () => {
        await load(true);
        if (!cancelled) scheduleNext();
      }, wait);
    }

    const fresh = readMarketCache();
    if (fresh) {
      setLoading(false);
      scheduleNext();
    } else {
      load(true).finally(() => {
        if (!cancelled) scheduleNext();
      });
    }

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [enabled, pollMs]);

  return (
    <MarketDataContext.Provider value={{ intelligence, loading }}>
      {children}
    </MarketDataContext.Provider>
  );
}

export function useMarketDataContext() {
  const ctx = useContext(MarketDataContext);
  if (!ctx) throw new Error('useMarketDataContext requires MarketDataProvider');
  return ctx;
}
