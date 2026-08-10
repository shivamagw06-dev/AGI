/**
 * Valuation company-pack read model (Supabase).
 *
 * Node serves the latest stored pack per (symbol, window). Missing/aging packs
 * refresh through a per-key singleflight Python snapshot job.
 */

const SCHEMA_VERSION = '1.0';
const CALCULATION_VERSION = 'valuation_company_pack_v1';
const FRESH_MS = Number(process.env.VALUATION_PACK_FRESH_MS || 15 * 60_000);
const AGING_MS = Number(process.env.VALUATION_PACK_AGING_MS || 60 * 60_000);
const STALE_SERVE_MS = Number(process.env.VALUATION_PACK_STALE_SERVE_MS || 24 * 60 * 60_000);
const ALLOWED_WINDOWS = new Set(['1Y', '3Y', '5Y', '10Y', 'MAX']);

/** @type {Map<string, Promise<any>>} */
const refreshInFlight = new Map();
/** @type {Map<string, number>} */
const recentRequests = new Map();

function credentials() {
  const url = String(process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
  const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  return url && key ? { url, key } : null;
}

async function rest(path, { method = 'GET', body, prefer } = {}) {
  const auth = credentials();
  if (!auth) {
    const error = new Error('Valuation pack store requires Supabase service credentials.');
    error.code = 'VALUATION_PACK_NO_SUPABASE';
    throw error;
  }
  const headers = {
    apikey: auth.key,
    Authorization: `Bearer ${auth.key}`,
    Accept: 'application/json',
  };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (prefer) headers.Prefer = prefer;
  const response = await fetch(`${auth.url}/rest/v1/${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = (await response.text()).slice(0, 300);
    const error = new Error(`Valuation pack Supabase ${method} failed (${response.status}): ${detail}`);
    error.status = response.status;
    throw error;
  }
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

export function normalizePackWindow(window) {
  const value = String(window || '5Y').trim().toUpperCase();
  return ALLOWED_WINDOWS.has(value) ? value : '5Y';
}

export function packCacheKey(symbol, window = '5Y') {
  return `${String(symbol || '').trim().toUpperCase()}|${normalizePackWindow(window)}`;
}

export function freshnessForAge(ageMs) {
  if (ageMs <= FRESH_MS) return 'fresh';
  if (ageMs <= AGING_MS) return 'aging';
  return 'stale';
}

function noteRecent(symbol, window) {
  const key = packCacheKey(symbol, window);
  if (!key.startsWith('|')) recentRequests.set(key, Date.now());
  // Bound memory.
  if (recentRequests.size > 200) {
    const ordered = [...recentRequests.entries()].sort((a, b) => a[1] - b[1]);
    for (const [oldKey] of ordered.slice(0, recentRequests.size - 200)) {
      recentRequests.delete(oldKey);
    }
  }
}

export function listRecentPackRequests({ limit = 12, maxAgeMs = 24 * 60 * 60_000 } = {}) {
  const cutoff = Date.now() - maxAgeMs;
  return [...recentRequests.entries()]
    .filter(([, at]) => at >= cutoff)
    .sort((a, b) => b[1] - a[1])
    .slice(0, Math.max(1, Math.min(limit, 40)))
    .map(([key]) => {
      const [symbol, window] = key.split('|');
      return { symbol, window };
    });
}

function decoratePayload(row) {
  const generatedAt = row.generated_at || row.payload?.generated_at;
  const ageMs = generatedAt ? Math.max(0, Date.now() - Date.parse(generatedAt)) : null;
  const freshness = ageMs == null ? (row.freshness || 'stale') : freshnessForAge(ageMs);
  const payload = row.payload && typeof row.payload === 'object' ? { ...row.payload } : {};
  return {
    ...payload,
    ok: payload.ok !== false,
    symbol: row.symbol || payload.symbol,
    window: row.window || payload.window,
    generated_at: generatedAt,
    source_as_of: row.source_as_of || payload.source_as_of || null,
    status: row.status || payload.status || 'ready',
    freshness,
    schema_version: row.schema_version || payload.schema_version || SCHEMA_VERSION,
    calculation_version: row.calculation_version || payload.calculation_version || CALCULATION_VERSION,
    snapshot_data_quality: row.data_quality || payload.snapshot_data_quality || {},
    read_model: 'supabase_valuation_company_pack',
    cache: {
      stale: freshness !== 'fresh',
      age_ms: ageMs,
      source: 'supabase',
      pack_id: row.pack_id || row.id || null,
    },
  };
}

export async function readLatestValuationCompanyPack(symbol, {
  window = '5Y',
  maxAgeMs = STALE_SERVE_MS,
} = {}) {
  const ticker = String(symbol || '').trim().toUpperCase();
  const win = normalizePackWindow(window);
  if (!ticker) return null;
  const query = new URLSearchParams({
    symbol: `eq.${ticker}`,
    window: `eq.${win}`,
    select: 'pack_id,symbol,window,generated_at,source_as_of,status,freshness,schema_version,calculation_version,data_quality,health_score,payload',
    limit: '1',
  }).toString();
  const rows = await rest(`valuation_company_packs_latest?${query}`);
  const row = Array.isArray(rows) && rows[0] ? rows[0] : null;
  if (!row) return null;
  const ageMs = row.generated_at ? Math.max(0, Date.now() - Date.parse(row.generated_at)) : Number.POSITIVE_INFINITY;
  if (ageMs > maxAgeMs) {
    const decorated = decoratePayload(row);
    return {
      ...decorated,
      status: 'stale',
      freshness: 'stale',
      cache: { ...(decorated.cache || {}), expired: true },
    };
  }
  return decoratePayload(row);
}

export async function refreshValuationCompanyPack({
  engineFetch,
  symbol,
  window = '5Y',
  peerLimit = 12,
} = {}) {
  if (typeof engineFetch !== 'function') {
    throw new Error('refreshValuationCompanyPack requires engineFetch');
  }
  const ticker = String(symbol || '').trim().toUpperCase();
  const win = normalizePackWindow(window);
  if (!ticker) throw new Error('symbol_required');
  const key = packCacheKey(ticker, win);
  if (refreshInFlight.has(key)) return refreshInFlight.get(key);

  const job = (async () => {
    const qs = new URLSearchParams({
      window: win,
      peer_limit: String(Math.max(1, Math.min(Number(peerLimit) || 12, 40))),
    }).toString();
    const result = await engineFetch(
      `/v1/valuation-engine/terminal/company/${encodeURIComponent(ticker)}/snapshot?${qs}`,
      { method: 'POST', timeoutMs: 180_000 },
    );
    if (!result?.ok) {
      const error = new Error(result?.data?.error || `engine valuation snapshot failed (${result?.status})`);
      error.status = result?.status || 502;
      error.data = result?.data;
      throw error;
    }
    if (result.data?.payload?.ok) {
      return {
        ...result.data.payload,
        generated_at: result.data.generated_at || result.data.payload.generated_at,
        source_as_of: result.data.source_as_of || result.data.payload.source_as_of,
        status: result.data.status || 'ready',
        freshness: result.data.freshness || 'fresh',
        schema_version: result.data.schema_version || SCHEMA_VERSION,
        calculation_version: result.data.calculation_version || CALCULATION_VERSION,
        snapshot_data_quality: result.data.data_quality || result.data.payload.snapshot_data_quality || {},
        read_model: 'supabase_valuation_company_pack',
        cache: {
          stale: false,
          age_ms: 0,
          source: 'engine_snapshot',
          pack_id: result.data.pack_id || null,
        },
      };
    }
    return readLatestValuationCompanyPack(ticker, { window: win });
  })();

  refreshInFlight.set(key, job);
  try {
    return await job;
  } finally {
    refreshInFlight.delete(key);
  }
}

/**
 * Serve company pack: Supabase first. Refresh via singleflight when missing/too old.
 */
export async function getValuationCompanyPackFromReadModel({
  engineFetch,
  symbol,
  window = '5Y',
  peerLimit = 12,
  forceRefresh = false,
  allowStale = true,
} = {}) {
  const ticker = String(symbol || '').trim().toUpperCase();
  const win = normalizePackWindow(window);
  noteRecent(ticker, win);
  const maxServeMs = allowStale ? STALE_SERVE_MS : FRESH_MS;

  if (!forceRefresh && credentials()) {
    try {
      const stored = await readLatestValuationCompanyPack(ticker, { window: win, maxAgeMs: maxServeMs });
      if (stored?.ok) {
        const age = stored.cache?.age_ms ?? 0;
        if (age > FRESH_MS) {
          refreshValuationCompanyPack({ engineFetch, symbol: ticker, window: win, peerLimit }).catch(() => null);
        }
        return { data: stored, source: 'supabase' };
      }
    } catch (error) {
      if (error.code !== 'VALUATION_PACK_NO_SUPABASE') {
        // Fall through.
      }
    }
  }

  try {
    const refreshed = await refreshValuationCompanyPack({
      engineFetch,
      symbol: ticker,
      window: win,
      peerLimit,
    });
    if (refreshed?.ok) return { data: refreshed, source: 'engine_snapshot' };
  } catch {
    if (credentials()) {
      try {
        const stored = await readLatestValuationCompanyPack(ticker, {
          window: win,
          maxAgeMs: Number.POSITIVE_INFINITY,
        });
        if (stored?.ok) {
          return {
            data: { ...stored, status: 'stale', freshness: 'stale' },
            source: 'supabase_expired',
          };
        }
      } catch {
        /* ignore */
      }
    }
  }
  return null;
}

export function getValuationPackRefreshStatus() {
  return {
    in_flight: refreshInFlight.size,
    keys: [...refreshInFlight.keys()],
    fresh_ms: FRESH_MS,
    aging_ms: AGING_MS,
    stale_serve_ms: STALE_SERVE_MS,
    recent: listRecentPackRequests({ limit: 10 }),
  };
}
