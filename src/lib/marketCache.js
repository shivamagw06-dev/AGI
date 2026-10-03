/** Client-side market cache — aligned to the same 30-min wall-clock cycle as the API. */
export const MARKET_REFRESH_MS = 30 * 60 * 1000;

// v3: wall-clock cycle alignment (shared with server marketRefresh.js)
const STORAGE_KEY = 'agi_market_intelligence_v3';
const STORAGE_TS_KEY = 'agi_market_intelligence_v3_ts';
const STORAGE_CYCLE_KEY = 'agi_market_intelligence_v3_cycle';

/** Current 30-minute cycle id (ms at bucket start). Matches server getMarketCycle(). */
export function getMarketCycleId(now = Date.now()) {
  return String(Math.floor(now / MARKET_REFRESH_MS) * MARKET_REFRESH_MS);
}

export function msUntilNextMarketCycle(now = Date.now()) {
  const started = Math.floor(now / MARKET_REFRESH_MS) * MARKET_REFRESH_MS;
  return started + MARKET_REFRESH_MS - now;
}

export function readMarketCache() {
  try {
    const cycleId = sessionStorage.getItem(STORAGE_CYCLE_KEY);
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw || !cycleId) return null;
    if (cycleId !== getMarketCycleId()) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function writeMarketCache(data) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    sessionStorage.setItem(STORAGE_TS_KEY, String(Date.now()));
    sessionStorage.setItem(STORAGE_CYCLE_KEY, getMarketCycleId());
  } catch {
    /* quota / private mode */
  }
}

export function msUntilNextRefresh() {
  try {
    const cycleId = sessionStorage.getItem(STORAGE_CYCLE_KEY);
    if (!cycleId || cycleId !== getMarketCycleId()) return 0;
    return msUntilNextMarketCycle();
  } catch {
    return 0;
  }
}
