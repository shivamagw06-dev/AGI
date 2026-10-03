/**
 * Scheduled refresh for aging valuation company packs.
 *
 * Prefer recently requested symbols. Cap each tick so Python is not woken for
 * a full-universe recompute. Staggered after HFL snapshot boot.
 */

import {
  getValuationPackRefreshStatus,
  listRecentPackRequests,
  normalizePackWindow,
  refreshValuationCompanyPack,
} from './valuationCompanyPackSnapshot.js';

let timer = null;
let lastRun = null;

function engineConfig() {
  let baseUrl = String(process.env.AGIB_INTELLIGENCE_ENGINE_URL || process.env.INTELLIGENCE_ENGINE_URL || '').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) baseUrl = `https://${baseUrl}`;
  return {
    baseUrl,
    token: String(process.env.AGIB_SERVICE_TOKEN || process.env.INTELLIGENCE_ENGINE_TOKEN || '').trim(),
  };
}

async function engineFetch(path, { method = 'GET', body, timeoutMs = 180_000 } = {}) {
  const { baseUrl, token } = engineConfig();
  if (!baseUrl || !token) throw new Error('intelligence_engine_not_configured');
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      'X-AGI-Intelligence-Token': token,
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });
  const data = await response.json().catch(() => ({}));
  return { ok: response.ok, status: response.status, data };
}

function seedSymbols() {
  return String(process.env.VALUATION_PACK_WARM_SYMBOLS || 'RELIANCE,TCS,HDFCBANK,INFY,ICICIBANK')
    .split(',')
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

export async function runValuationCompanyPackRefresh({ force = false, limit } = {}) {
  const capped = Math.max(1, Math.min(Number(limit || process.env.VALUATION_PACK_REFRESH_LIMIT || 4) || 4, 12));
  const recent = listRecentPackRequests({ limit: capped });
  const seeds = seedSymbols().map((symbol) => ({ symbol, window: '5Y' }));
  const seen = new Set();
  const queue = [];
  for (const item of [...recent, ...seeds]) {
    const key = `${item.symbol}|${normalizePackWindow(item.window)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    queue.push({ symbol: item.symbol, window: normalizePackWindow(item.window) });
    if (queue.length >= capped) break;
  }

  const results = [];
  for (const item of queue) {
    try {
      const pack = await refreshValuationCompanyPack({
        engineFetch,
        symbol: item.symbol,
        window: item.window,
        peerLimit: 12,
      });
      results.push({
        symbol: item.symbol,
        window: item.window,
        ok: Boolean(pack?.ok),
        generated_at: pack?.generated_at || null,
        freshness: pack?.freshness || null,
      });
    } catch (error) {
      results.push({
        symbol: item.symbol,
        window: item.window,
        ok: false,
        error: error?.message || String(error),
      });
    }
  }

  lastRun = {
    at: new Date().toISOString(),
    ok: results.some((r) => r.ok),
    forced: Boolean(force),
    refreshed: results.filter((r) => r.ok).length,
    attempted: results.length,
    results,
  };
  return lastRun;
}

export function startValuationCompanyPackScheduler() {
  if (
    timer ||
    String(process.env.VALUATION_PACK_SCHEDULER_ENABLED || 'true').toLowerCase() !== 'true'
  ) {
    return;
  }
  const intervalMs = Math.max(5 * 60_000, Number(process.env.VALUATION_PACK_INTERVAL_MS || 20 * 60_000));
  // After HFL snapshot (~2m). Keep light so it does not collide with quote jobs.
  const initialDelayMs = Math.max(60_000, Number(process.env.VALUATION_PACK_INITIAL_DELAY_MS || 300_000));
  const tick = () => {
    runValuationCompanyPackRefresh()
      .then((result) => { lastRun = result; })
      .catch((error) => {
        lastRun = { at: new Date().toISOString(), ok: false, error: error?.message || String(error) };
      });
  };
  setTimeout(tick, initialDelayMs);
  timer = setInterval(tick, intervalMs);
  timer.unref?.();
}

export function getValuationCompanyPackSchedulerStatus() {
  return {
    enabled: Boolean(timer),
    intervalMs: Number(process.env.VALUATION_PACK_INTERVAL_MS || 20 * 60_000),
    initialDelayMs: Number(process.env.VALUATION_PACK_INITIAL_DELAY_MS || 300_000),
    lastRun,
    refresh: getValuationPackRefreshStatus(),
  };
}
