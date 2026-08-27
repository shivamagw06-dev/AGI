/**
 * AGI Macro data repository
 * Memory → disk → Supabase. Frontend never talks to third-party APIs.
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DISK_DIR = path.join(__dirname, '../data/macro-cache');
const memory = new Map();

/** Refresh TTLs — free APIs are reference sources, not live pipes. */
export const MACRO_REFRESH_MS = {
  world_bank_india: 30 * 24 * 60 * 60 * 1000, // monthly
  fred_rates: 12 * 60 * 60 * 1000, // 1–2x / day
  fx_usdinr: 60 * 60 * 1000, // hourly max
  weather_india: 8 * 60 * 60 * 1000, // 6–12h
  indianapi_commodities: 6 * 60 * 60 * 1000,
  alphavantage_commodities: 12 * 60 * 60 * 1000, // conserve 25/day quota
  alphavantage_economy: 24 * 60 * 60 * 1000, // official release cadence
  imf_forecasts: 90 * 24 * 60 * 60 * 1000,
  rbi_policy: 24 * 60 * 60 * 1000,
  macro_briefing: 6 * 60 * 60 * 1000,
  // Pre-market: global redistribution-friendly quotes (not NSE/BSE)
  global_indices: 20 * 60 * 1000, // 20 minutes
  global_drivers: 30 * 60 * 1000,
  finnhub_calendar: 6 * 60 * 60 * 1000,
  pre_market_briefing: 30 * 60 * 1000,
};

function supabaseConfig() {
  const url = (process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
  const key = (process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  if (!url || !key) return null;
  return { url, key };
}

async function ensureDiskDir() {
  await fs.mkdir(DISK_DIR, { recursive: true });
}

function diskPath(datasetKey) {
  return path.join(DISK_DIR, `${datasetKey.replace(/[^a-z0-9_-]/gi, '_')}.json`);
}

function normalizeRecord(datasetKey, row) {
  if (!row) return null;
  return {
    datasetKey,
    payload: row.payload ?? row,
    source: row.source || 'unknown',
    fetchedAt: row.fetched_at || row.fetchedAt || null,
    expiresAt: row.expires_at || row.expiresAt || null,
    refreshPolicy: row.refresh_policy || row.refreshPolicy || 'scheduled',
    meta: row.meta || {},
    stale: row.expires_at || row.expiresAt ? Date.parse(row.expires_at || row.expiresAt) < Date.now() : false,
  };
}

async function readDisk(datasetKey) {
  try {
    const raw = await fs.readFile(diskPath(datasetKey), 'utf8');
    return normalizeRecord(datasetKey, JSON.parse(raw));
  } catch {
    return null;
  }
}

async function writeDisk(record) {
  await ensureDiskDir();
  const body = {
    dataset_key: record.datasetKey,
    payload: record.payload,
    source: record.source,
    fetched_at: record.fetchedAt,
    expires_at: record.expiresAt,
    refresh_policy: record.refreshPolicy,
    meta: record.meta || {},
  };
  await fs.writeFile(diskPath(record.datasetKey), JSON.stringify(body, null, 2), 'utf8');
}

async function readSupabase(datasetKey) {
  const cfg = supabaseConfig();
  if (!cfg) return null;
  try {
    const response = await fetch(
      `${cfg.url}/rest/v1/macro_dataset_cache?dataset_key=eq.${encodeURIComponent(datasetKey)}&select=*&limit=1`,
      {
        headers: {
          apikey: cfg.key,
          Authorization: `Bearer ${cfg.key}`,
          Accept: 'application/json',
        },
        signal: AbortSignal.timeout(8_000),
      },
    );
    if (!response.ok) return null;
    const rows = await response.json();
    return normalizeRecord(datasetKey, rows?.[0]);
  } catch (error) {
    console.warn('[macro-repo] supabase read failed:', error.message);
    return null;
  }
}

async function writeSupabase(record) {
  const cfg = supabaseConfig();
  if (!cfg) return false;
  try {
    const body = {
      dataset_key: record.datasetKey,
      payload: record.payload,
      source: record.source,
      fetched_at: record.fetchedAt,
      expires_at: record.expiresAt,
      refresh_policy: record.refreshPolicy,
      meta: record.meta || {},
      updated_at: new Date().toISOString(),
    };
    const response = await fetch(`${cfg.url}/rest/v1/macro_dataset_cache`, {
      method: 'POST',
      headers: {
        apikey: cfg.key,
        Authorization: `Bearer ${cfg.key}`,
        'Content-Type': 'application/json',
        Prefer: 'resolution=merge-duplicates',
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(8_000),
    });
    return response.ok;
  } catch (error) {
    console.warn('[macro-repo] supabase write failed:', error.message);
    return false;
  }
}

async function appendHistory(datasetKey, observations, source) {
  if (!observations?.length) return;
  const cfg = supabaseConfig();

  // Always append lightweight history on disk for local continuity.
  try {
    await ensureDiskDir();
    const historyFile = path.join(DISK_DIR, `_history_${datasetKey.replace(/[^a-z0-9_-]/gi, '_')}.jsonl`);
    const lines = observations.map((item) => JSON.stringify({
      dataset_key: datasetKey,
      observed_at: new Date().toISOString(),
      ...item,
      source,
    })).join('\n') + '\n';
    await fs.appendFile(historyFile, lines, 'utf8');
  } catch (error) {
    console.warn('[macro-repo] disk history append failed:', error.message);
  }

  if (!cfg) return;
  try {
    const rows = observations.map((item) => ({
      dataset_key: datasetKey,
      observed_at: new Date().toISOString(),
      label: item.label || null,
      value_numeric: item.valueNumeric ?? item.value ?? null,
      value_text: item.valueText || null,
      direction: item.direction || null,
      unit: item.unit || null,
      payload: item.payload || {},
      source,
    }));
    await fetch(`${cfg.url}/rest/v1/macro_observation_history`, {
      method: 'POST',
      headers: {
        apikey: cfg.key,
        Authorization: `Bearer ${cfg.key}`,
        'Content-Type': 'application/json',
        Prefer: 'return=minimal',
      },
      body: JSON.stringify(rows),
      signal: AbortSignal.timeout(8_000),
    });
  } catch (error) {
    console.warn('[macro-repo] history write failed:', error.message);
  }
}

/**
 * Load dataset from memory → disk → supabase.
 * Returns stale records when present (never blank if we have history).
 */
export async function getCachedDataset(datasetKey) {
  const mem = memory.get(datasetKey);
  if (mem) {
    return { ...mem, stale: Date.parse(mem.expiresAt) < Date.now() };
  }
  const disk = await readDisk(datasetKey);
  if (disk) {
    memory.set(datasetKey, disk);
    return disk;
  }
  const remote = await readSupabase(datasetKey);
  if (remote) {
    memory.set(datasetKey, remote);
    await writeDisk(remote).catch(() => {});
    return remote;
  }
  return null;
}

export function isFresh(record) {
  if (!record?.expiresAt) return false;
  return Date.parse(record.expiresAt) > Date.now();
}

/**
 * Persist a successful upstream response into AGI's repository.
 */
export async function saveDataset(datasetKey, payload, {
  source,
  ttlMs,
  refreshPolicy = 'scheduled',
  meta = {},
  observations = [],
} = {}) {
  const fetchedAt = new Date().toISOString();
  const expiresAt = new Date(Date.now() + (ttlMs || MACRO_REFRESH_MS[datasetKey] || 6 * 60 * 60 * 1000)).toISOString();
  const record = {
    datasetKey,
    payload,
    source,
    fetchedAt,
    expiresAt,
    refreshPolicy,
    meta,
    stale: false,
  };
  memory.set(datasetKey, record);
  await writeDisk(record);
  await writeSupabase(record);
  if (observations.length) await appendHistory(datasetKey, observations, source);
  return record;
}

function sanitizeUpstreamError(message) {
  let text = String(message || '');
  // Alpha Vantage embeds the key in rate-limit copy — never leak it.
  text = text.replace(/We have detected your API key as\s+\S+/gi, 'Alpha Vantage rate limit reached');
  text = text.replace(/apikey=[^&\s]+/gi, 'apikey=REDACTED');
  text = text.replace(/\b[A-Z0-9]{16}\b/g, '[REDACTED]');
  return text.slice(0, 240);
}

/**
 * Fetch-through cache helper.
 * Uses cached data when fresh. On upstream failure, returns last good cache.
 */
export async function getOrFetchDataset(datasetKey, fetcher, {
  source,
  ttlMs,
  refreshPolicy = 'scheduled',
  toObservations = null,
} = {}) {
  const cached = await getCachedDataset(datasetKey);
  if (cached && isFresh(cached)) {
    return { ...cached, fromCache: true, refreshed: false };
  }

  try {
    const payload = await fetcher();
    if (payload == null) throw new Error('Empty upstream payload');
    const observations = typeof toObservations === 'function' ? toObservations(payload) || [] : [];
    const saved = await saveDataset(datasetKey, payload, {
      source,
      ttlMs: ttlMs || MACRO_REFRESH_MS[datasetKey],
      refreshPolicy,
      observations,
      meta: { lastSuccessAt: new Date().toISOString() },
    });
    return { ...saved, fromCache: false, refreshed: true };
  } catch (error) {
    const safeMessage = sanitizeUpstreamError(error.message);
    if (cached) {
      console.warn(`[macro-repo] ${datasetKey} upstream failed; serving stale cache:`, safeMessage);
      return {
        ...cached,
        stale: true,
        fromCache: true,
        refreshed: false,
        upstreamError: safeMessage,
      };
    }
    console.warn(`[macro-repo] ${datasetKey} unavailable and no cache:`, safeMessage);
    return {
      datasetKey,
      payload: null,
      source: 'unavailable',
      fetchedAt: null,
      expiresAt: null,
      stale: true,
      fromCache: false,
      refreshed: false,
      upstreamError: safeMessage,
      meta: {},
    };
  }
}

export async function saveBriefingCache(briefing, { ttlMs = MACRO_REFRESH_MS.macro_briefing, aiGenerated = false } = {}) {
  return saveDataset('macro_briefing', briefing, {
    source: 'agi-macro-engine',
    ttlMs,
    refreshPolicy: 'scheduled',
    meta: { aiGenerated },
  });
}

export async function getBriefingCache() {
  return getCachedDataset('macro_briefing');
}
