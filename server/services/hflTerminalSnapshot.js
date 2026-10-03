/**
 * Hedge Fund Lab terminal read model (Supabase).
 *
 * Node serves the latest stored snapshot. If none exists (or a refresh is
 * forced), a single in-flight Python snapshot job is launched (singleflight).
 */

const SCHEMA_VERSION = '1.0';
const CALCULATION_VERSION = 'hfl_terminal_v2';
const FRESH_MS = Number(process.env.HFL_SNAPSHOT_FRESH_MS || 15 * 60_000);
const AGING_MS = Number(process.env.HFL_SNAPSHOT_AGING_MS || 60 * 60_000);
const STALE_SERVE_MS = Number(process.env.HFL_SNAPSHOT_STALE_SERVE_MS || 24 * 60 * 60_000);

let refreshInFlight = null;

function credentials() {
  const url = String(process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
  const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  return url && key ? { url, key } : null;
}

async function rest(path, { method = 'GET', body, prefer, timeoutMs = 3_000 } = {}) {
  const auth = credentials();
  if (!auth) {
    const error = new Error('HFL snapshot store requires Supabase service credentials.');
    error.code = 'HFL_SNAPSHOT_NO_SUPABASE';
    throw error;
  }
  const headers = {
    apikey: auth.key,
    Authorization: `Bearer ${auth.key}`,
    Accept: 'application/json',
  };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (prefer) headers.Prefer = prefer;
  const response = await fetch(`${auth.url}/rest/v1/${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) {
    const detail = (await response.text()).slice(0, 300);
    const error = new Error(`HFL snapshot Supabase ${method} failed (${response.status}): ${detail}`);
    error.status = response.status;
    throw error;
  }
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

export function freshnessForAge(ageMs) {
  if (ageMs <= FRESH_MS) return 'fresh';
  if (ageMs <= AGING_MS) return 'aging';
  return 'stale';
}

function decoratePayload(row) {
  const generatedAt = row.generated_at || row.payload?.generated_at;
  const ageMs = generatedAt ? Math.max(0, Date.now() - Date.parse(generatedAt)) : null;
  const freshness = ageMs == null ? (row.freshness || 'stale') : freshnessForAge(ageMs);
  const payload = row.payload && typeof row.payload === 'object' ? { ...row.payload } : {};
  return {
    ...payload,
    ok: payload.ok !== false,
    generated_at: generatedAt,
    source_as_of: row.source_as_of || payload.source_as_of || payload.as_of || null,
    status: row.status || payload.status || 'ready',
    freshness,
    schema_version: row.schema_version || payload.schema_version || SCHEMA_VERSION,
    calculation_version: row.calculation_version || payload.calculation_version || CALCULATION_VERSION,
    data_quality: row.data_quality || payload.data_quality || {},
    read_model: 'supabase_hfl_terminal',
    cache: {
      stale: freshness !== 'fresh',
      age_ms: ageMs,
      source: 'supabase',
      snapshot_id: row.id || null,
    },
  };
}

export async function readLatestHflTerminalSnapshot({ maxAgeMs = STALE_SERVE_MS } = {}) {
  const query = new URLSearchParams({
    status: 'eq.ready',
    select: 'id,generated_at,source_as_of,status,freshness,schema_version,calculation_version,data_quality,limit_used,universe_scanned,live_opportunities,payload',
    order: 'generated_at.desc',
    limit: '1',
  }).toString();
  const rows = await rest(`hfl_terminal_snapshots?${query}`);
  const row = Array.isArray(rows) && rows[0] ? rows[0] : null;
  if (!row) return null;
  const ageMs = row.generated_at ? Math.max(0, Date.now() - Date.parse(row.generated_at)) : Number.POSITIVE_INFINITY;
  if (ageMs > maxAgeMs) {
    return { ...decoratePayload(row), status: 'stale', freshness: 'stale', cache: { ...(decoratePayload(row).cache || {}), expired: true } };
  }
  return decoratePayload(row);
}

export async function refreshHflTerminalSnapshot({ engineFetch, limit = 12 } = {}) {
  if (typeof engineFetch !== 'function') {
    throw new Error('refreshHflTerminalSnapshot requires engineFetch');
  }
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    const result = await engineFetch(
      `/v1/hedge-fund-lab/terminal/snapshot?limit=${encodeURIComponent(String(limit))}`,
      { method: 'POST', timeoutMs: 180_000 },
    );
    if (!result?.ok) {
      const error = new Error(result?.data?.error || `engine snapshot failed (${result?.status})`);
      error.status = result?.status || 502;
      error.data = result?.data;
      throw error;
    }
    // Prefer the just-written payload; fall back to a fresh Supabase read.
    if (result.data?.payload && result.data.payload.ok) {
      return {
        ...result.data.payload,
        generated_at: result.data.generated_at || result.data.payload.generated_at,
        source_as_of: result.data.source_as_of || result.data.payload.source_as_of,
        status: result.data.status || 'ready',
        freshness: result.data.freshness || 'fresh',
        schema_version: result.data.schema_version || SCHEMA_VERSION,
        calculation_version: result.data.calculation_version || CALCULATION_VERSION,
        data_quality: result.data.data_quality || result.data.payload.data_quality || {},
        read_model: 'supabase_hfl_terminal',
        cache: { stale: false, age_ms: 0, source: 'engine_snapshot', snapshot_id: result.data.snapshot_id || null },
      };
    }
    return readLatestHflTerminalSnapshot();
  })();
  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

/**
 * Serve terminal: Supabase first. Refresh via singleflight when missing/too old.
 * Never launches more than one Python snapshot job at a time.
 */
export async function getHflTerminalFromReadModel({
  engineFetch,
  limit = 12,
  forceRefresh = false,
  allowStale = true,
} = {}) {
  const maxServeMs = allowStale ? STALE_SERVE_MS : FRESH_MS;
  if (!forceRefresh && credentials()) {
    try {
      const stored = await readLatestHflTerminalSnapshot({ maxAgeMs: maxServeMs });
      if (stored?.ok) {
        const age = stored.cache?.age_ms ?? 0;
        // Background refresh when aging/stale, but still return stored payload.
        if (age > FRESH_MS) {
          refreshHflTerminalSnapshot({ engineFetch, limit }).catch(() => null);
        }
        return { data: stored, source: 'supabase' };
      }
    } catch (error) {
      if (error.code !== 'HFL_SNAPSHOT_NO_SUPABASE') {
        // Fall through to engine snapshot / legacy path.
      }
    }
  }

  // Page traffic must never wait for a full-universe Python scan. Start one
  // singleflight refresh in the background and return a lightweight read model.
  refreshHflTerminalSnapshot({ engineFetch, limit }).catch(() => null);
  return {
    source: 'warming',
    data: {
      ok: true,
      status: 'warming',
      freshness: 'unavailable',
      read_model: 'supabase_hfl_terminal',
      generated_at: null,
      source_as_of: null,
      hero: { universe_scanned: 0, live_opportunities: 0, companies_flagged: 0 },
      cards: [],
      overlap: [],
      research_queue: [],
      market_dashboard: {},
      daily_intelligence: { new_opportunities: [], removed_opportunities: [], note: 'Preparing the latest research snapshot.' },
      policy: 'Research snapshot is being prepared. No live request-time warehouse scan was run.',
      cache: { stale: true, age_ms: null, source: 'warming' },
    },
  };
}

export function getHflSnapshotRefreshStatus() {
  return { in_flight: Boolean(refreshInFlight), fresh_ms: FRESH_MS, aging_ms: AGING_MS, stale_serve_ms: STALE_SERVE_MS };
}
