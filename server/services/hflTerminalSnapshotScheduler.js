/**
 * Scheduled Hedge Fund Lab terminal snapshot refresh.
 *
 * One calm Python compute → Supabase write. Page traffic reads the store.
 * Staggered after boot so it does not wake the engine with quote/candle jobs.
 */

import {
  getHflSnapshotRefreshStatus,
  readLatestHflTerminalSnapshot,
  refreshHflTerminalSnapshot,
} from './hflTerminalSnapshot.js';

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

export async function runHflTerminalSnapshotRefresh({ force = false, limit } = {}) {
  const capped = Math.max(1, Math.min(Number(limit || process.env.HFL_SNAPSHOT_LIMIT || 12) || 12, 50));
  if (!force) {
    try {
      const latest = await readLatestHflTerminalSnapshot({ maxAgeMs: Number(process.env.HFL_SNAPSHOT_FRESH_MS || 15 * 60_000) });
      if (latest?.ok && latest.freshness === 'fresh') {
        lastRun = {
          at: new Date().toISOString(),
          ok: true,
          skipped: true,
          reason: 'snapshot_still_fresh',
          generated_at: latest.generated_at,
        };
        return lastRun;
      }
    } catch {
      /* missing store / credentials — still attempt engine refresh */
    }
  }

  const result = await refreshHflTerminalSnapshot({ engineFetch, limit: capped });
  lastRun = {
    at: new Date().toISOString(),
    ok: Boolean(result?.ok),
    skipped: false,
    generated_at: result?.generated_at || null,
    snapshot_id: result?.cache?.snapshot_id || null,
    freshness: result?.freshness || null,
  };
  return lastRun;
}

export function startHflTerminalSnapshotScheduler() {
  if (
    timer ||
    String(process.env.HFL_SNAPSHOT_SCHEDULER_ENABLED || 'true').toLowerCase() !== 'true'
  ) {
    return;
  }
  const intervalMs = Math.max(5 * 60_000, Number(process.env.HFL_SNAPSHOT_INTERVAL_MS || 15 * 60_000));
  // Run before quote/candle schedulers so page traffic has a store to hit.
  const initialDelayMs = Math.max(30_000, Number(process.env.HFL_SNAPSHOT_INITIAL_DELAY_MS || 120_000));
  const tick = () => {
    runHflTerminalSnapshotRefresh()
      .then((result) => { lastRun = result; })
      .catch((error) => {
        lastRun = { at: new Date().toISOString(), ok: false, error: error?.message || String(error) };
      });
  };
  setTimeout(tick, initialDelayMs);
  timer = setInterval(tick, intervalMs);
  timer.unref?.();
}

export function getHflTerminalSnapshotSchedulerStatus() {
  return {
    enabled: Boolean(timer),
    intervalMs: Number(process.env.HFL_SNAPSHOT_INTERVAL_MS || 15 * 60_000),
    initialDelayMs: Number(process.env.HFL_SNAPSHOT_INITIAL_DELAY_MS || 120_000),
    lastRun,
    refresh: getHflSnapshotRefreshStatus(),
  };
}
