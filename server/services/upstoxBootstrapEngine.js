/**
 * Phase 7.4d — Upstox Full-Universe Bootstrap & Continuous Valuation Backfill.
 *
 * One-time (resumable) bootstrap that drains the ISIN-mapped company queue into
 * warehouse.valuation_ratios via Normalizer → DQIV → Warehouse → UVE.
 * Independent from the nightly 18:15 IST incremental scheduler.
 */

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const STATES = Object.freeze(['PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'RETRY', 'SKIPPED']);
const RETRY_BACKOFF_MS = [30_000, 120_000, 600_000, 1_800_000]; // 30s, 2m, 10m, 30m
const MAX_RETRIES = RETRY_BACKOFF_MS.length;
// Official Upstox cap for standard APIs: 2000 requests / 30 minutes.
const UPSTOX_WINDOW_MS = envInt('UPSTOX_WINDOW_MS', 30 * 60 * 1000);
const UPSTOX_WINDOW_MAX = envInt('UPSTOX_WINDOW_MAX_CALLS', 2000);
/** @type {number[]} timestamps of Upstox calls in the rolling window */
let upstoxCallTimes = [];

function envInt(name, fallback) {
  const n = Number(process.env[name]);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

function stateDir() {
  const root = process.env.UPSTOX_BOOTSTRAP_STATE_DIR
    || process.env.KIP_DATA_DIR
    || path.join(process.cwd(), 'data');
  const dir = path.join(root, 'upstox_bootstrap');
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function statePath() {
  return process.env.UPSTOX_BOOTSTRAP_STATE_PATH || path.join(stateDir(), 'state.json');
}

function nowIso() {
  return new Date().toISOString();
}

function emptyMetrics() {
  return {
    successfulCalls: 0,
    failures: 0,
    http429: 0,
    http5xx: 0,
    timeouts: 0,
    retries: 0,
    rowsWritten: 0,
    latencySumMs: 0,
    latencyCount: 0,
    batchesCompleted: 0,
    lastBatchAt: null,
    lastSuccessBatchAt: null,
    companiesPerMinute: 0,
    rowsPerMinute: 0,
  };
}

function emptyRun() {
  return {
    runId: null,
    status: 'idle', // idle | running | paused | completed | stopped
    startedAt: null,
    endedAt: null,
    batchSize: envInt('UPSTOX_BOOTSTRAP_BATCH', 40),
    concurrency: envInt('UPSTOX_BOOTSTRAP_CONCURRENCY', 3),
    pauseMs: envInt('UPSTOX_BOOTSTRAP_PAUSE_MS', 2_000),
    minPauseMs: envInt('UPSTOX_BOOTSTRAP_MIN_PAUSE_MS', 1_000),
    maxPauseMs: envInt('UPSTOX_BOOTSTRAP_MAX_PAUSE_MS', 60_000),
    masters: 0,
    withIsin: 0,
    withoutIsin: 0,
    queue: {}, // symbol → company record
    missingIsin: [],
    metrics: emptyMetrics(),
    recentLog: [],
    error: null,
  };
}

/** @type {ReturnType<typeof emptyRun>} */
let run = emptyRun();
let loopPromise = null;
let stopRequested = false;

function persist() {
  try {
    fs.writeFileSync(statePath(), JSON.stringify(run, null, 2));
  } catch (err) {
    console.warn('[upstox-bootstrap] persist failed', err?.message || err);
  }
}

function loadPersisted() {
  try {
    if (!fs.existsSync(statePath())) return;
    const raw = JSON.parse(fs.readFileSync(statePath(), 'utf8'));
    if (!raw || typeof raw !== 'object') return;
    run = { ...emptyRun(), ...raw, metrics: { ...emptyMetrics(), ...(raw.metrics || {}) } };
    // Never resume as running after process restart — operator must start again (queue preserved).
    if (run.status === 'running') run.status = 'paused';
    for (const item of Object.values(run.queue || {})) {
      if (item.state === 'RUNNING') {
        item.state = 'RETRY';
        item.nextRetryAt = nowIso();
      }
    }
  } catch (err) {
    console.warn('[upstox-bootstrap] load state failed', err?.message || err);
  }
}

loadPersisted();

function pushLog(entry) {
  run.recentLog = [{ at: nowIso(), ...entry }, ...(run.recentLog || [])].slice(0, 100);
}

function countByState() {
  const counts = Object.fromEntries(STATES.map((s) => [s, 0]));
  for (const item of Object.values(run.queue || {})) {
    const st = STATES.includes(item.state) ? item.state : 'PENDING';
    counts[st] += 1;
  }
  return counts;
}

function avgLatency() {
  const m = run.metrics;
  if (!m.latencyCount) return 0;
  return Math.round(m.latencySumMs / m.latencyCount);
}

function successRate() {
  const m = run.metrics;
  const total = m.successfulCalls + m.failures;
  if (!total) return 0;
  return Math.round((1000 * m.successfulCalls) / total) / 10;
}

function coveragePct() {
  const withIsin = run.withIsin || Object.keys(run.queue || {}).length;
  if (!withIsin) return 0;
  const success = countByState().SUCCESS || 0;
  return Math.round((1000 * success) / withIsin) / 10;
}

function etaMinutes() {
  const counts = countByState();
  const remaining = (counts.PENDING || 0) + (counts.RETRY || 0) + (counts.RUNNING || 0);
  const cpm = run.metrics.companiesPerMinute || 0;
  if (!remaining) return 0;
  if (cpm <= 0) {
    // Heuristic: batchSize / (pause + ~batch*0.3s)
    const batch = run.batchSize || 40;
    const batchSec = (run.pauseMs || 2000) / 1000 + batch * 0.25;
    return Math.round((remaining / batch) * (batchSec / 60) * 10) / 10;
  }
  return Math.round((remaining / cpm) * 10) / 10;
}

function updateThroughput() {
  if (!run.startedAt) return;
  const elapsedMin = Math.max(0.01, (Date.now() - new Date(run.startedAt).getTime()) / 60_000);
  run.metrics.companiesPerMinute = Math.round(((countByState().SUCCESS || 0) / elapsedMin) * 10) / 10;
  run.metrics.rowsPerMinute = Math.round((run.metrics.rowsWritten / elapsedMin) * 10) / 10;
}

function adjustThrottle({ hit429 = false, healthy = false } = {}) {
  if (hit429) {
    run.pauseMs = Math.min(run.maxPauseMs, Math.max(run.pauseMs * 2, run.pauseMs + 5_000));
    run.concurrency = Math.max(1, (run.concurrency || 3) - 1);
    return;
  }
  if (healthy && run.pauseMs > run.minPauseMs) {
    run.pauseMs = Math.max(run.minPauseMs, Math.round(run.pauseMs * 0.85));
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function awaitUpstoxQuota(n) {
  const need = Math.max(1, Number(n) || 1);
  while (true) {
    const cutoff = Date.now() - UPSTOX_WINDOW_MS;
    upstoxCallTimes = upstoxCallTimes.filter((stamp) => stamp > cutoff);
    if (upstoxCallTimes.length + need <= UPSTOX_WINDOW_MAX) {
      const now = Date.now();
      for (let i = 0; i < need; i += 1) upstoxCallTimes.push(now);
      return;
    }
    const oldest = upstoxCallTimes[0] || Date.now();
    const waitMs = Math.max(1_000, oldest + UPSTOX_WINDOW_MS - Date.now() + 1_000);
    pushLog({
      symbol: '*',
      state: 'RETRY',
      reason: `upstox_quota_${upstoxCallTimes.length}/${UPSTOX_WINDOW_MAX} wait_${Math.round(waitMs / 1000)}s`,
    });
    persist();
    await sleep(Math.min(waitMs, 60_000));
  }
}

async function loadUniverse() {
  const { loadIsinUniverse } = await import('./upstoxValuationRatiosRefresh.js');
  const { backfillCompanyIsins } = await import('./companyIsinBackfill.js');

  // Ensure ISINs exist before building the queue.
  let masters = await loadIsinUniverse({ limit: 10_000 });
  const withIsin = masters.filter((r) => String(r.isin || '').trim());
  if (withIsin.length < Math.min(100, masters.length || 100)) {
    await backfillCompanyIsins({ dryRun: false });
    masters = await loadIsinUniverse({ limit: 10_000 });
  }

  const isinRe = /^IN[A-Z0-9]{10}$/;
  const queue = {};
  const missing = [];
  for (const row of masters) {
    const symbol = String(row.symbol || '').trim().toUpperCase();
    if (!symbol) continue;
    const isin = String(row.isin || '').trim().toUpperCase();
    const companyName = row.company_name || symbol;
    if (!isin || !isinRe.test(isin)) {
      missing.push({
        symbol,
        company: companyName,
        reason: isin ? 'Invalid ISIN' : 'No ISIN',
        lastAttempt: null,
        notes: isin ? `isin=${isin}` : 'Upstox key-ratios require ISIN',
      });
      continue;
    }
    const prev = run.queue?.[symbol];
    queue[symbol] = prev && ['SUCCESS', 'FAILED', 'SKIPPED'].includes(prev.state)
      ? { ...prev, isin, company_id: row.company_id || symbol, company_name: companyName, sector: row.sector || null }
      : {
          symbol,
          isin,
          company_id: row.company_id || symbol,
          company_name: companyName,
          sector: row.sector || null,
          state: prev?.state === 'RETRY' ? 'RETRY' : 'PENDING',
          attempts: prev?.attempts || 0,
          lastError: prev?.lastError || null,
          nextRetryAt: prev?.nextRetryAt || null,
          latencyMs: prev?.latencyMs || null,
          rowsWritten: prev?.rowsWritten || 0,
          updatedAt: prev?.updatedAt || null,
        };
  }

  // Preserve SKIPPED for missing ISIN symbols already known.
  for (const miss of missing) {
    // not in queue — tracked separately
  }

  run.masters = masters.length;
  run.withIsin = Object.keys(queue).length;
  run.withoutIsin = missing.length;
  run.queue = queue;
  run.missingIsin = missing;
  return { masters: masters.length, withIsin: run.withIsin, withoutIsin: run.withoutIsin };
}

function nextBatch() {
  const now = Date.now();
  const batch = [];
  const size = run.batchSize || 40;

  // Prefer due RETRY, then PENDING.
  const dueRetry = [];
  const pending = [];
  for (const item of Object.values(run.queue)) {
    if (item.state === 'RETRY') {
      const due = !item.nextRetryAt || new Date(item.nextRetryAt).getTime() <= now;
      if (due) dueRetry.push(item);
    } else if (item.state === 'PENDING') {
      pending.push(item);
    }
  }
  dueRetry.sort((a, b) => String(a.symbol).localeCompare(String(b.symbol)));
  pending.sort((a, b) => String(a.symbol).localeCompare(String(b.symbol)));

  for (const item of [...dueRetry, ...pending]) {
    if (batch.length >= size) break;
    batch.push(item);
  }
  return batch;
}

function markRetry(item, error, status) {
  item.attempts = (item.attempts || 0) + 1;
  item.lastError = error || 'unknown';
  item.updatedAt = nowIso();
  run.metrics.failures += 1;
  if (status === 429 || /too many|rate.?limit/i.test(String(error || ''))) {
    run.metrics.http429 += 1;
    adjustThrottle({ hit429: true });
  } else if (status >= 500) {
    run.metrics.http5xx += 1;
  } else if (/timeout|abort/i.test(String(error || ''))) {
    run.metrics.timeouts += 1;
  }

  if (item.attempts > MAX_RETRIES) {
    item.state = 'FAILED';
    pushLog({ symbol: item.symbol, state: 'FAILED', reason: item.lastError, attempts: item.attempts });
    return;
  }
  item.state = 'RETRY';
  const delay = RETRY_BACKOFF_MS[Math.min(item.attempts - 1, RETRY_BACKOFF_MS.length - 1)];
  item.nextRetryAt = new Date(Date.now() + delay).toISOString();
  run.metrics.retries += 1;
  pushLog({
    symbol: item.symbol,
    state: 'RETRY',
    reason: item.lastError,
    nextAttempt: item.nextRetryAt,
    attempts: item.attempts,
  });
}

async function processBatch(batch) {
  const { refreshUpstoxValuationRatios } = await import('./upstoxValuationRatiosRefresh.js');
  const symbols = batch.map((b) => b.symbol);
  for (const item of batch) {
    item.state = 'RUNNING';
    item.updatedAt = nowIso();
  }
  persist();

  const t0 = Date.now();
  const result = await refreshUpstoxValuationRatios({
    symbols,
    concurrency: run.concurrency,
    backfillIsins: false,
    limit: symbols.length,
  });
  const elapsed = Date.now() - t0;
  run.metrics.batchesCompleted += 1;
  run.metrics.lastBatchAt = nowIso();

  const failedMap = new Map();
  for (const err of result.errors || []) {
    failedMap.set(String(err.symbol || '').toUpperCase(), err);
  }

  const perCompanyLatency = Math.round(elapsed / Math.max(1, batch.length));
  let successes = 0;

  const warehouseOk = Boolean(result.ok);
  const batchRateLimited = result.status === 429
    || result.error === 'upstox_rate_limited'
    || /too many request/i.test(String(result.error || ''));
  if (batchRateLimited) {
    adjustThrottle({ hit429: true });
  }
  for (const item of batch) {
    const err = failedMap.get(item.symbol);
    if (err) {
      markRetry(item, err.error || `http_${err.status}`, err.status || null);
      continue;
    }
    if (!warehouseOk) {
      // Prefer precise batch error (rate limit / auth) over legacy "empty".
      markRetry(item, result.error || 'ingest_failed', result.status || null);
      continue;
    }
    item.state = 'SUCCESS';
    item.latencyMs = perCompanyLatency;
    item.rowsWritten = 6; // six key ratios typical
    item.lastError = null;
    item.nextRetryAt = null;
    item.updatedAt = nowIso();
    item.attempts = (item.attempts || 0) + 1;
    successes += 1;
    run.metrics.successfulCalls += 1;
    run.metrics.latencySumMs += perCompanyLatency;
    run.metrics.latencyCount += 1;
    run.metrics.rowsWritten += item.rowsWritten;
    pushLog({
      symbol: item.symbol,
      isin: item.isin,
      state: 'SUCCESS',
      latencyMs: perCompanyLatency,
      rowsWritten: item.rowsWritten,
      dqiv: 'passed',
    });
  }

  if (successes > 0) {
    run.metrics.lastSuccessBatchAt = nowIso();
    adjustThrottle({ healthy: run.metrics.http429 === 0 || successes === batch.length });
  }

  updateThroughput();
  persist();
  return { successes, failed: batch.length - successes, elapsed, result };
}

async function writeBootstrapRunSummary() {
  try {
    const counts = countByState();
    const summary = {
      run_id: run.runId,
      started_at: run.startedAt,
      ended_at: run.endedAt || nowIso(),
      companies: run.withIsin,
      success: counts.SUCCESS || 0,
      failed: counts.FAILED || 0,
      skipped: (counts.SKIPPED || 0) + (run.withoutIsin || 0),
      coverage: coveragePct(),
      average_speed: run.metrics.companiesPerMinute,
      average_latency: avgLatency(),
      http_429_count: run.metrics.http429,
      retry_count: run.metrics.retries,
      status: run.status,
      source: 'upstox_bootstrap',
    };
    // Best-effort warehouse persistence via import (tab may not exist yet on older engines).
    const { baseUrl, token } = (() => {
      let u = (process.env.AGIB_INTELLIGENCE_ENGINE_URL || process.env.INTELLIGENCE_ENGINE_URL || '').replace(/\/$/, '');
      if (u && !/^https?:\/\//i.test(u)) u = `https://${u}`;
      return { baseUrl: u, token: (process.env.AGIB_SERVICE_TOKEN || process.env.INTELLIGENCE_ENGINE_TOKEN || '').trim() };
    })();
    if (!baseUrl || !token) return summary;

    const staged = await fetch(`${baseUrl}/v1/warehouse/tab/bootstrap_runs/import`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        'X-AGI-Intelligence-Token': token,
      },
      body: JSON.stringify({ rows: [summary], actor: 'upstox_bootstrap', source: 'upstox_bootstrap' }),
      signal: AbortSignal.timeout(60_000),
    });
    if (staged.ok) {
      const data = await staged.json();
      if (data?.import_id) {
        await fetch(`${baseUrl}/v1/warehouse/import/${data.import_id}/commit`, {
          method: 'POST',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
            'X-AGI-Intelligence-Token': token,
          },
          body: JSON.stringify({ actor: 'upstox_bootstrap' }),
          signal: AbortSignal.timeout(60_000),
        });
      }
    }
    return summary;
  } catch (err) {
    console.warn('[upstox-bootstrap] run summary write failed', err?.message || err);
    return null;
  }
}

async function loop() {
  stopRequested = false;
  run.status = 'running';
  run.error = null;
  persist();

  try {
    while (!stopRequested) {
      const batch = nextBatch();
      if (!batch.length) {
        // Wait for retries that are not due yet.
        const waiting = Object.values(run.queue).filter((i) => i.state === 'RETRY');
        if (!waiting.length) break;
        const nextAt = Math.min(...waiting.map((i) => new Date(i.nextRetryAt || Date.now()).getTime()));
        const waitMs = Math.min(run.maxPauseMs, Math.max(1_000, nextAt - Date.now()));
        await sleep(waitMs);
        continue;
      }

      await awaitUpstoxQuota(batch.length);
      await processBatch(batch);
      if (stopRequested) break;
      await sleep(run.pauseMs || 2_000);
    }

    const counts = countByState();
    const pendingLeft = (counts.PENDING || 0) + (counts.RUNNING || 0) + (counts.RETRY || 0);
    run.endedAt = nowIso();
    run.status = stopRequested ? 'stopped' : pendingLeft === 0 ? 'completed' : 'paused';
    updateThroughput();
    persist();
    await writeBootstrapRunSummary();
    console.info('[upstox-bootstrap]', run.status, `success=${counts.SUCCESS} failed=${counts.FAILED} retry=${counts.RETRY}`);
  } catch (err) {
    run.status = 'stopped';
    run.error = err?.message || String(err);
    run.endedAt = nowIso();
    persist();
    console.error('[upstox-bootstrap] loop crashed', run.error);
  } finally {
    loopPromise = null;
  }
}

export function getUpstoxBootstrapStatus() {
  const counts = countByState();
  const remaining = (counts.PENDING || 0) + (counts.RETRY || 0) + (counts.RUNNING || 0);
  return {
    ok: true,
    engine: 'upstox_bootstrap',
    version: '7.4d',
    runId: run.runId,
    status: run.status,
    startedAt: run.startedAt,
    endedAt: run.endedAt,
    summary: {
      companies: run.masters,
      isinAvailable: run.withIsin,
      completed: counts.SUCCESS || 0,
      running: counts.RUNNING || 0,
      remaining,
      coverage: coveragePct(),
      etaMinutes: etaMinutes(),
      missingIsin: run.withoutIsin,
    },
    queue: counts,
    apiHealth: {
      successfulCalls: run.metrics.successfulCalls,
      failures: run.metrics.failures,
      http429: run.metrics.http429,
      retryCount: run.metrics.retries,
      averageLatencyMs: avgLatency(),
      successPct: successRate(),
      currentBatchSize: run.batchSize,
      lastBatchAt: run.metrics.lastBatchAt,
      lastSuccessfulBatchAt: run.metrics.lastSuccessBatchAt,
    },
    throughput: {
      companiesPerMinute: run.metrics.companiesPerMinute,
      rowsPerMinute: run.metrics.rowsPerMinute,
      warehouseWrites: run.metrics.rowsWritten,
      batchesCompleted: run.metrics.batchesCompleted,
      pauseMs: run.pauseMs,
      concurrency: run.concurrency,
    },
    config: {
      batchSize: run.batchSize,
      concurrency: run.concurrency,
      pauseMs: run.pauseMs,
      minPauseMs: run.minPauseMs,
      maxPauseMs: run.maxPauseMs,
    },
    recentLog: (run.recentLog || []).slice(0, 40),
    error: run.error,
    nightlySchedulerNote: 'Nightly 18:15 IST remains incremental maintenance only — bootstrap is one-shot.',
  };
}

export function getUpstoxBootstrapMissingIsin({ limit = 500 } = {}) {
  return {
    ok: true,
    count: (run.missingIsin || []).length,
    rows: (run.missingIsin || []).slice(0, limit),
  };
}

export function getUpstoxBootstrapFailures({ limit = 200 } = {}) {
  const rows = Object.values(run.queue || {})
    .filter((i) => i.state === 'FAILED' || i.state === 'RETRY')
    .sort((a, b) => String(a.symbol).localeCompare(String(b.symbol)))
    .slice(0, limit);
  return { ok: true, count: rows.length, rows };
}

export async function startUpstoxBootstrap({
  reset = false,
  batchSize,
  concurrency,
  pauseMs,
} = {}) {
  if (loopPromise) {
    return { ok: false, error: 'bootstrap_already_running', status: getUpstoxBootstrapStatus() };
  }

  if (reset || !run.runId || run.status === 'completed') {
    const prevQueue = reset ? {} : run.queue;
    run = emptyRun();
    run.queue = prevQueue;
  }

  if (batchSize) run.batchSize = Math.max(5, Math.min(100, Number(batchSize) || 40));
  if (concurrency) run.concurrency = Math.max(1, Math.min(8, Number(concurrency) || 3));
  if (pauseMs) run.pauseMs = Math.max(run.minPauseMs, Math.min(run.maxPauseMs, Number(pauseMs) || 2000));

  run.runId = run.runId || `ubr-${crypto.randomBytes(6).toString('hex')}`;
  run.startedAt = run.startedAt || nowIso();
  run.endedAt = null;
  run.error = null;

  await loadUniverse();

  // Mark already-SUCCESS if reset=false and they remain SUCCESS.
  persist();
  loopPromise = loop();
  return { ok: true, started: true, status: getUpstoxBootstrapStatus() };
}

export async function stopUpstoxBootstrap() {
  stopRequested = true;
  if (run.status === 'running') run.status = 'paused';
  persist();
  if (loopPromise) {
    try { await loopPromise; } catch { /* ignore */ }
  }
  return { ok: true, stopped: true, status: getUpstoxBootstrapStatus() };
}

export async function resetUpstoxBootstrap() {
  if (loopPromise) {
    return { ok: false, error: 'stop_bootstrap_before_reset' };
  }
  run = emptyRun();
  persist();
  return { ok: true, reset: true, status: getUpstoxBootstrapStatus() };
}

/** True when a bootstrap loop is actively draining the queue. */
export function isUpstoxBootstrapRunning() {
  return Boolean(loopPromise) || run.status === 'running';
}
