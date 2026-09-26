/**
 * Shared market refresh cycle — all market surfaces refresh together.
 *
 * Wall-clock aligned to 30-minute buckets (…:00 and …:30 UTC) so homepage
 * Groww snapshots, AGI Market Outlook strip, pulse/dashboard, and client
 * caches expire and refresh on the same cadence.
 */

export const MARKET_REFRESH_MS = 30 * 60 * 1000;

const cycleSlots = new Map();

/** Current 30-minute market cycle metadata. */
export function getMarketCycle(now = Date.now()) {
  const startedMs = Math.floor(now / MARKET_REFRESH_MS) * MARKET_REFRESH_MS;
  const expiresMs = startedMs + MARKET_REFRESH_MS;
  return {
    cycleId: String(startedMs),
    startedMs,
    expiresMs,
    startedAt: new Date(startedMs).toISOString(),
    expiresAt: new Date(expiresMs).toISOString(),
    msRemaining: Math.max(0, expiresMs - now),
    refreshMinutes: MARKET_REFRESH_MS / 60_000,
  };
}

/** Human label matching the insight strip ("Updated 04:09 am"). */
export function formatMarketUpdatedLabel(isoOrDate, timeZone = 'Asia/Kolkata') {
  const d = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate || Date.now());
  if (Number.isNaN(d.getTime())) return '';
  const label = d.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    timeZone,
  });
  return `Updated ${label}`;
}

/**
 * Run `producer` at most once per market cycle for `key`.
 * Concurrent callers share the same in-flight promise.
 */
export async function oncePerMarketCycle(key, producer) {
  const { cycleId, startedAt, expiresMs, msRemaining } = getMarketCycle();
  const existing = cycleSlots.get(key);

  if (existing?.cycleId === cycleId) {
    if (existing.value !== undefined) return existing.value;
    if (existing.promise) return existing.promise;
  }

  const promise = Promise.resolve()
    .then(() => producer({ cycleId, startedAt, expiresMs, msRemaining }))
    .then((value) => {
      let stamped = value;
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        stamped = {
          ...value,
          marketCycleId: cycleId,
          marketCycleStartedAt: startedAt,
          updatedAt: value.updatedAt || new Date().toISOString(),
        };
      }
      cycleSlots.set(key, { cycleId, value: stamped, promise: null });
      return stamped;
    })
    .catch((err) => {
      const cur = cycleSlots.get(key);
      if (cur?.promise === promise) {
        // Keep prior cycle value if we have one; otherwise clear inflight.
        if (existing?.value !== undefined && existing.cycleId !== cycleId) {
          cycleSlots.set(key, { cycleId: existing.cycleId, value: existing.value, promise: null });
        } else {
          cycleSlots.set(key, { cycleId, value: undefined, promise: null });
        }
      }
      throw err;
    });

  cycleSlots.set(key, {
    cycleId,
    value: existing?.cycleId === cycleId ? existing.value : undefined,
    promise,
  });
  return promise;
}

/** Cache-Control max-age (seconds) remaining in the current market cycle. */
export function marketCycleCacheMaxAgeSeconds(now = Date.now()) {
  const { msRemaining } = getMarketCycle(now);
  return Math.max(1, Math.floor(msRemaining / 1000));
}
