/**
 * Phase 7.4E — UIFI bootstrap (resumable, adaptive).
 * Reuses Phase 7.4D patterns: checkpointed queue, 429 backoff, never full restart.
 */

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { refreshUpstoxFundamentals, DATASETS } from './upstoxFundamentalsRefresh.js';
import { loadIsinUniverse } from './upstoxValuationRatiosRefresh.js';

const BOOTSTRAP_DATASETS = Object.freeze([
  'profile',
  'statements',
  'share-holdings',
  'competitors',
  'corporate-actions',
]);

function stateDir() {
  const root = process.env.UIFI_BOOTSTRAP_STATE_DIR
    || process.env.UPSTOX_BOOTSTRAP_STATE_DIR
    || process.env.KIP_DATA_DIR
    || path.join(process.cwd(), 'data');
  const dir = path.join(root, 'uifi_bootstrap');
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function statePath() {
  return process.env.UIFI_BOOTSTRAP_STATE_PATH || path.join(stateDir(), 'state.json');
}

function nowIso() {
  return new Date().toISOString();
}

function emptyRun() {
  return {
    runId: null,
    status: 'idle',
    startedAt: null,
    endedAt: null,
    datasetCursor: 0,
    datasets: [...BOOTSTRAP_DATASETS],
    batchSize: Number(process.env.UIFI_BOOTSTRAP_BATCH || 25),
    concurrency: Number(process.env.UIFI_BOOTSTRAP_CONCURRENCY || 2),
    pauseMs: Number(process.env.UIFI_BOOTSTRAP_PAUSE_MS || 2500),
    offset: 0,
    masters: 0,
    withIsin: 0,
    metrics: {
      batches: 0,
      successBatches: 0,
      failedBatches: 0,
      fetched: 0,
      http429: 0,
    },
    recentLog: [],
    lastCoverage: null,
    error: null,
  };
}

let run = emptyRun();
let loopPromise = null;
let stopRequested = false;

function persist() {
  try {
    fs.writeFileSync(statePath(), JSON.stringify(run, null, 2));
  } catch (err) {
    console.warn('[uifi-bootstrap] persist failed', err?.message || err);
  }
}

function loadPersisted() {
  try {
    if (!fs.existsSync(statePath())) return;
    const raw = JSON.parse(fs.readFileSync(statePath(), 'utf8'));
    run = { ...emptyRun(), ...raw, metrics: { ...emptyRun().metrics, ...(raw.metrics || {}) } };
    if (run.status === 'running') run.status = 'paused';
  } catch (err) {
    console.warn('[uifi-bootstrap] load failed', err?.message || err);
  }
}

loadPersisted();

function pushLog(entry) {
  run.recentLog = [{ at: nowIso(), ...entry }, ...(run.recentLog || [])].slice(0, 80);
}

async function tickOnce() {
  const dataset = run.datasets[run.datasetCursor] || null;
  if (!dataset) {
    run.status = 'completed';
    run.endedAt = nowIso();
    persist();
    return false;
  }

  const universe = await loadIsinUniverse({ limit: 20000 });
  run.masters = universe.length;
  run.withIsin = universe.filter((r) => r.isin).length;
  const slice = universe.slice(run.offset, run.offset + run.batchSize);
  if (!slice.length) {
    // Advance to next dataset
    run.datasetCursor += 1;
    run.offset = 0;
    pushLog({ event: 'dataset_complete', dataset });
    persist();
    return run.datasetCursor < run.datasets.length;
  }

  const symbols = slice.map((r) => String(r.symbol || '').toUpperCase()).filter(Boolean);
  const result = await refreshUpstoxFundamentals({
    dataset,
    limit: symbols.length,
    concurrency: run.concurrency,
    symbols,
  });

  run.metrics.batches += 1;
  run.metrics.fetched += result.fetched || 0;
  if (result.ok) run.metrics.successBatches += 1;
  else run.metrics.failedBatches += 1;
  if ((result.errors || []).some((e) => e.status === 429)) {
    run.metrics.http429 += 1;
    run.pauseMs = Math.min(60_000, Math.max(run.pauseMs * 2, 5_000));
  } else {
    run.pauseMs = Math.max(1_500, Math.floor(run.pauseMs * 0.9));
  }

  run.offset += slice.length;
  pushLog({
    event: result.ok ? 'batch_ok' : 'batch_fail',
    dataset,
    symbols: symbols.length,
    fetched: result.fetched || 0,
    error: result.error || null,
  });
  persist();
  return true;
}

async function loop() {
  stopRequested = false;
  run.status = 'running';
  run.startedAt = run.startedAt || nowIso();
  persist();
  try {
    while (!stopRequested && run.status === 'running') {
      // eslint-disable-next-line no-await-in-loop
      const more = await tickOnce();
      if (!more) break;
      // eslint-disable-next-line no-await-in-loop
      await new Promise((r) => setTimeout(r, run.pauseMs));
    }
    if (stopRequested) {
      run.status = 'stopped';
      run.endedAt = nowIso();
    }
  } catch (err) {
    run.status = 'failed';
    run.error = err?.message || String(err);
    run.endedAt = nowIso();
  } finally {
    persist();
    loopPromise = null;
  }
}

export function getUifiBootstrapStatus() {
  return {
    ok: true,
    ...run,
    datasetsAvailable: DATASETS,
    bootstrapDatasets: BOOTSTRAP_DATASETS,
  };
}

export async function startUifiBootstrap({
  reset = false,
  dataset = null,
  batchSize = null,
  concurrency = null,
} = {}) {
  if (loopPromise) {
    return { ok: false, error: 'bootstrap_already_running', status: getUifiBootstrapStatus() };
  }
  if (reset) {
    run = emptyRun();
  }
  if (dataset) {
    const ds = String(dataset).toLowerCase();
    run.datasets = ds === 'all' ? [...BOOTSTRAP_DATASETS] : [ds];
    run.datasetCursor = 0;
    run.offset = 0;
  }
  if (batchSize) run.batchSize = Number(batchSize) || run.batchSize;
  if (concurrency) run.concurrency = Number(concurrency) || run.concurrency;
  run.runId = run.runId || crypto.randomBytes(6).toString('hex');
  run.error = null;
  loopPromise = loop();
  return { ok: true, started: true, status: getUifiBootstrapStatus() };
}

export async function stopUifiBootstrap() {
  stopRequested = true;
  run.status = 'stopped';
  persist();
  return { ok: true, stopped: true, status: getUifiBootstrapStatus() };
}

export async function resetUifiBootstrap() {
  if (loopPromise) {
    return { ok: false, error: 'stop_before_reset', status: getUifiBootstrapStatus() };
  }
  run = emptyRun();
  persist();
  return { ok: true, reset: true, status: getUifiBootstrapStatus() };
}
