/**
 * Upstox-first EMPTY statement fill.
 *
 * Pulls EMPTY/MINIMAL/thin INE* symbols from the intelligence-engine queue,
 * then reuses refreshUpstoxFundamentals({ dataset: 'statements' }) which
 * already calls:
 *   GET /v2/fundamentals/{isin}/income-statement|balance-sheet|cash-flow
 * with type=consolidated, yearly, fs=true.
 *
 * Prefer this over Yahoo fill on Render (Yahoo fundamentals are blocked).
 */

import { refreshUpstoxFundamentals } from './upstoxFundamentalsRefresh.js';

function engineConfig() {
  let baseUrl = (process.env.AGIB_INTELLIGENCE_ENGINE_URL || process.env.INTELLIGENCE_ENGINE_URL || '').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) baseUrl = `https://${baseUrl}`;
  const token = (process.env.AGIB_SERVICE_TOKEN || process.env.INTELLIGENCE_ENGINE_TOKEN || '').trim();
  return { baseUrl, token };
}

async function engineFetch(path, { timeoutMs = 180_000 } = {}) {
  const { baseUrl, token } = engineConfig();
  if (!baseUrl || !token) {
    return { ok: false, status: 503, data: { error: 'intelligence_engine_not_configured' } };
  }
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token}`,
      'X-AGI-Intelligence-Token': token,
    },
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: String(text || '').slice(0, 400) };
  }
  return { ok: response.ok, status: response.status, data };
}

function nowIso() {
  return new Date().toISOString();
}

const state = {
  status: 'idle', // idle | running | stopped
  startedAt: null,
  endedAt: null,
  stopped: false,
  batchSize: 10,
  concurrency: 2,
  pauseMs: 2000,
  normalPauseMs: 2000,
  includeThin: true,
  processed: 0,
  filled: 0,
  failed: 0,
  skipped: 0,
  lastBatch: null,
  lastError: null,
  recent: [],
  /** Symbols already attempted this run — keep the queue advancing. */
  attempted: [],
};

let loopPromise = null;

function pushRecent(entry) {
  state.recent = [{ at: nowIso(), ...entry }, ...(state.recent || [])].slice(0, 40);
}

function rememberAttempted(symbols) {
  const seen = new Set(state.attempted || []);
  for (const s of symbols || []) {
    const sym = String(s || '').trim().toUpperCase();
    if (sym) seen.add(sym);
  }
  // Cap memory; oldest drop first so recent skips stay excluded.
  state.attempted = [...seen].slice(-2000);
}

export function summarizeStatementBatch(todo, result = {}) {
  const companyOk = new Set(
    (result.ingest?.results || []).filter((r) => r?.ok && r?.symbol)
      .map((r) => String(r.symbol).toUpperCase()),
  );
  const rateLimited = new Set(
    (result.errors || []).filter((e) => Number(e.status) === 429)
      .map((e) => String(e.symbol || '').toUpperCase()),
  );
  if (Number(result.status) === 429) {
    for (const symbol of todo) if (!companyOk.has(symbol)) rateLimited.add(symbol);
  }
  const settled = todo.filter((symbol) => !rateLimited.has(symbol));
  return {
    settled,
    filledCount: companyOk.size,
    failedCount: Math.max(0, settled.length - companyOk.size),
    rateLimitedCount: rateLimited.size,
  };
}

async function loadQueue(limit) {
  const qs = new URLSearchParams({
    // Fetch the ranked candidate list once, then exclude every attempted name
    // locally. Sending only the last 150 exclusions made long runs cycle back
    // to already-attempted companies.
    limit: String(Math.max(5000, limit)),
    include_thin: state.includeThin ? 'true' : 'false',
  });
  const result = await engineFetch(`/v1/warehouse/upstox-fill/queue?${qs}`);
  if (!result.ok) {
    throw new Error(result.data?.error || `queue_http_${result.status}`);
  }
  return result.data || {};
}

async function runBatch({ batchSize = state.batchSize, symbols = null } = {}) {
  let todo = Array.isArray(symbols) ? symbols.map((s) => String(s).toUpperCase()).filter(Boolean) : null;
  let queueMeta = null;
  if (!todo) {
    queueMeta = await loadQueue(batchSize);
    const attempted = new Set(state.attempted || []);
    todo = (queueMeta.rows || []).map((r) => r.symbol).filter((symbol) => symbol && !attempted.has(symbol));
  }
  todo = todo.slice(0, Math.max(1, Math.min(Number(batchSize) || 10, 50)));
  if (!todo.length) {
    return {
      ok: true,
      batch: { size: 0, filled: 0, failed: 0, at: nowIso() },
      queue: queueMeta?.counts || null,
      plain_english: 'Upstox EMPTY queue is dry.',
    };
  }

  const result = await refreshUpstoxFundamentals({
    dataset: 'statements',
    limit: todo.length,
    concurrency: state.concurrency,
    symbols: todo,
    annualOnly: true,
  });

  const fetched = Number(result.fetched || 0);
  const ingestRows = Number(result.ingest?.totals?.rows || 0);
  const { settled, filledCount, failedCount, rateLimitedCount } = summarizeStatementBatch(todo, result);
  // Prefer explicit per-company ingest success; do not invent fills from row totals.

  rememberAttempted(settled);
  state.processed += settled.length;
  state.filled += filledCount;
  state.failed += failedCount;
  state.skipped = (state.attempted || []).length;
  state.lastBatch = {
    size: todo.length,
    filled: filledCount,
    failed: failedCount,
    rate_limited: rateLimitedCount,
    fetched,
    ingest_rows: ingestRows,
    errors: (result.errors || []).slice(0, 8),
    at: nowIso(),
  };
  pushRecent({
    event: filledCount ? 'batch_ok' : 'batch_fail',
    symbols: todo,
    filled: filledCount,
    failed: failedCount,
    error: result.error || null,
  });

  if (rateLimitedCount) {
    // Upstox's standard-API rolling allowance is 2,000 requests per 30 min.
    // A one-minute retry loop cannot recover that window and can exhaust it.
    state.pauseMs = Math.max(state.pauseMs, 30 * 60 * 1000);
  } else {
    state.pauseMs = state.normalPauseMs;
  }

  return {
    ok: true,
    source: 'upstox',
    batch: state.lastBatch,
    queue: queueMeta?.counts || null,
    refresh: {
      ok: result.ok,
      error: result.error || null,
      fetched,
      ingest: result.ingest || null,
      errors: (result.errors || []).slice(0, 10),
    },
    plain_english: (
      `Upstox batch: ${filledCount} filled, ${failedCount} failed, `
      + `${ingestRows} statement rows written. `
      + (result.error ? `Last error: ${result.error}` : '')
    ),
  };
}

async function loop() {
  state.status = 'running';
  state.stopped = false;
  state.startedAt = state.startedAt || nowIso();
  state.endedAt = null;
  state.lastError = null;
  try {
    while (!state.stopped && state.status === 'running') {
      let out;
      try {
        // eslint-disable-next-line no-await-in-loop
        out = await runBatch({ batchSize: state.batchSize });
      } catch (err) {
        state.lastError = err?.message || String(err);
        pushRecent({ event: 'batch_error', error: state.lastError });
        state.pauseMs = Math.min(120_000, Math.max(state.pauseMs * 2, 15_000));
        // eslint-disable-next-line no-await-in-loop
        await new Promise((r) => setTimeout(r, state.pauseMs));
        continue;
      }
      if (!out.batch?.size) {
        break;
      }
      // eslint-disable-next-line no-await-in-loop
      await new Promise((r) => setTimeout(r, state.pauseMs));
    }
    state.status = state.stopped ? 'stopped' : 'idle';
    state.endedAt = nowIso();
  } catch (err) {
    // Last-resort: never leave a permanent failed state for transient faults.
    state.lastError = err?.message || String(err);
    state.status = 'idle';
    state.endedAt = nowIso();
    pushRecent({ event: 'loop_ended', error: state.lastError });
  } finally {
    loopPromise = null;
  }
}

export function getUpstoxEmptyFillStatus() {
  return {
    ok: true,
    source: 'upstox',
    runtime: { ...state, loopAlive: Boolean(loopPromise) },
    recent: state.recent,
    plain_english: (
      `Upstox EMPTY fill is ${state.status}. `
      + `Processed ${state.processed}, filled ${state.filled}, failed ${state.failed}. `
      + 'Uses three annual Upstox statement calls per eligible company (consolidated).'
    ),
    what_this_does: (
      'Fills warehouse financials_annual / financials_quarterly for EMPTY equities '
      + 'with INE* ISINs via three annual Upstox fundamentals calls. Prefer over Yahoo on Render.'
    ),
  };
}

export async function startUpstoxEmptyFill({
  batchSize = 10,
  concurrency = 2,
  pauseMs = 2500,
  includeThin = true,
} = {}) {
  if (loopPromise) {
    return { ok: true, already_running: true, ...getUpstoxEmptyFillStatus() };
  }
  state.batchSize = Math.max(1, Math.min(Number(batchSize) || 10, 40));
  state.concurrency = Math.max(1, Math.min(Number(concurrency) || 2, 4));
  state.pauseMs = Math.max(500, Number(pauseMs) || 2500);
  state.normalPauseMs = state.pauseMs;
  state.includeThin = includeThin !== false;
  state.processed = 0;
  state.filled = 0;
  state.failed = 0;
  state.skipped = 0;
  state.attempted = [];
  state.startedAt = nowIso();
  state.recent = [];
  loopPromise = loop();
  return { ok: true, started: true, ...getUpstoxEmptyFillStatus() };
}

export async function stopUpstoxEmptyFill() {
  state.stopped = true;
  state.status = 'stopped';
  return { ok: true, stopped: true, ...getUpstoxEmptyFillStatus() };
}

export async function runUpstoxEmptyFillBatch(opts = {}) {
  return runBatch(opts);
}
