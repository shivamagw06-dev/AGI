import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { LiveAlphaPersistence } from './liveAlphaPersistence.js';
import { MomentumShadowPipeline } from './liveAlphaShadowPipeline.js';
import { VolumeBaselineIndex } from './minuteVolumeBaseline.js';
import { SynchronizedSnapshotStore, UpstoxMarketFeedV3 } from './upstoxMarketFeedV3.js';
import { bootstrapLiveAlphaVolumeBaselines } from './liveAlphaBaselineBootstrap.js';
import { resolveLiveAlphaDerivatives } from './liveAlphaDerivativeUniverse.js';
import { pollGrowwIndexSnapshots } from './sectorIndexGrowwFallback.js';
import { isUpstoxAuthError } from './upstoxMarketFeedV3.js';

const serverDir = path.dirname(fileURLToPath(import.meta.url));
const defaultUniversePath = path.join(serverDir, '../config/live-alpha-universe.example.json');
let runtime = null;
let growwFallbackTimer = null;
let state = {
  enabled: false, status: 'disabled', evaluation_status: 'disabled', started_at: null,
  last_evaluation: null, last_successful_evaluation: null, last_error: null,
};

export function classifyEvaluationStatus(evaluation) {
  if (!evaluation) return 'warming_up';
  if (evaluation.skipped) {
    if (['benchmark_history_incomplete', 'insufficient_complete_universe'].includes(evaluation.reason)) return 'warming_up';
    if (evaluation.reason === 'already_evaluated_bucket') return 'live';
    return 'blocked';
  }
  return (evaluation.persistence || []).some((row) => row.status === 'failed') ? 'degraded' : 'live';
}

export function validateLiveAlphaUniverse(config) {
  const benchmarkKey = String(config?.benchmarkKey || '').trim();
  const members = config?.members;
  if (!benchmarkKey.includes('|')) throw new Error('Live alpha benchmarkKey is invalid.');
  if (!Array.isArray(members) || members.length < 10) throw new Error('Live alpha universe requires at least 10 members.');
  const symbols = new Set();
  const keys = new Set();
  const clean = members.map((row, index) => {
    const member = {
      symbol: String(row.symbol || '').trim().toUpperCase(), sector: String(row.sector || '').trim().toUpperCase(),
      instrumentKey: String(row.instrumentKey || '').trim(), sectorInstrumentKey: String(row.sectorInstrumentKey || '').trim(),
      derivativeInstrumentKey: String(row.derivativeInstrumentKey || '').trim() || null,
      minimumLiquidity: row.minimumLiquidity !== false,
    };
    if (!/^[A-Z0-9&-]+$/.test(member.symbol) || !member.sector || !member.instrumentKey.includes('|') || !member.sectorInstrumentKey.startsWith('NSE_INDEX|')) throw new Error(`Invalid universe member at index ${index}.`);
    if (member.derivativeInstrumentKey && !member.derivativeInstrumentKey.startsWith('NSE_FO|')) throw new Error(`Invalid derivative instrument at index ${index}.`);
    if (symbols.has(member.symbol) || keys.has(member.instrumentKey)) throw new Error(`Duplicate universe member: ${member.symbol}.`);
    symbols.add(member.symbol); keys.add(member.instrumentKey);
    return member;
  });
  return { benchmarkKey, members: clean };
}

export async function loadLiveAlphaUniverse(filePath = process.env.LIVE_ALPHA_UNIVERSE_PATH || defaultUniversePath) {
  return validateLiveAlphaUniverse(JSON.parse(await fs.readFile(filePath, 'utf8')));
}

export async function startLiveAlphaRuntime({ Feed = UpstoxMarketFeedV3, Persistence = LiveAlphaPersistence } = {}) {
  const enabled = String(process.env.LIVE_ALPHA_SHADOW_ENABLED || '').toLowerCase() === 'true';
  if (!enabled) {
    state = { ...state, enabled: false, status: 'disabled' };
    return getLiveAlphaRuntimeStatus();
  }
  if (runtime) return getLiveAlphaRuntimeStatus();
  try {
    const universe = await resolveLiveAlphaDerivatives(await loadLiveAlphaUniverse());
    const persistence = new Persistence();
    const baselines = new VolumeBaselineIndex(await persistence.loadVolumeBaselines());
    const pipeline = new MomentumShadowPipeline({ ...universe, universe: universe.members, baselineIndex: baselines, repository: persistence });
    // Preserve the rolling 15m/60m feature window across deploys and brief
    // restarts. Only genuine persisted observations are restored; missing
    // market history is never synthesized.
    const openingSnapshots = await persistence.loadSessionOpeningSnapshots?.({ now: new Date(), limit: 1000 }) || [];
    const recentSnapshots = await persistence.loadRecentSnapshots?.({ minutes: 90, limit: 5000 }) || [];
    if (openingSnapshots.length) pipeline.ingest({ snapshots: openingSnapshots });
    if (recentSnapshots.length) pipeline.ingest({ snapshots: recentSnapshots });
    const store = new SynchronizedSnapshotStore();
    const instrumentKeys = [...new Set([universe.benchmarkKey, ...universe.members.flatMap((row) => [row.instrumentKey, row.sectorInstrumentKey, row.derivativeInstrumentKey]).filter(Boolean)])];
    let lastEvaluationMs = 0;
    const feed = new Feed({ instrumentKeys, snapshotStore: store, onBatch: async (batch) => {
      pipeline.ingest(batch);
      await persistence.persistBatch(batch);
      if (Date.now() - lastEvaluationMs >= 5_000) {
        lastEvaluationMs = Date.now();
        const evaluation = await pipeline.evaluate(new Date());
        const currentEvaluation = {
          at: new Date().toISOString(), skipped: Boolean(evaluation.skipped), reason: evaluation.reason || null,
          universe_size: evaluation.universe_size || evaluation.coverage || 0,
          opening_range_status: evaluation.opening_range_status || null,
          derivatives_status: evaluation.derivatives_status || null,
          persistence: evaluation.persistence || [],
        };
        state.last_evaluation = currentEvaluation;
        state.evaluation_status = classifyEvaluationStatus(currentEvaluation);
        if (!currentEvaluation.skipped) state.last_successful_evaluation = currentEvaluation;
      }
    } });
    runtime = { feed, pipeline, persistence, store, universe, bootstrap: { opening_snapshots: openingSnapshots.length, recent_snapshots: recentSnapshots.length, volume_baselines: baselines.values.size, derivatives: universe.derivativeResolution } };
    state = {
      enabled: true, status: 'starting', evaluation_status: 'warming_up',
      started_at: new Date().toISOString(), last_evaluation: null,
      last_successful_evaluation: null, last_error: null,
    };
    await feed.start();
    state.status = 'running';
    if (feed.state?.status === 'auth_failed') startGrowwSectorIndexFallback({ store, pipeline, instrumentKeys });
    if (baselines.values.size < universe.members.length) {
      state.baseline_bootstrap = { status: 'running', rows: baselines.values.size, failures: [] };
      const retryMs = Math.max(60_000, Number(process.env.LIVE_ALPHA_BASELINE_RETRY_MS || 5 * 60_000));
      const bootstrap = async () => {
        try {
          const result = await bootstrapLiveAlphaVolumeBaselines({ members: universe.members, persistence, baselineIndex: baselines });
          state.baseline_bootstrap = result;
          if (runtime?.bootstrap) runtime.bootstrap.volume_baselines = baselines.values.size;
          if (result.status !== 'ready' && runtime) {
            const retry = setTimeout(bootstrap, retryMs); retry.unref?.();
          }
        } catch (error) {
          state.baseline_bootstrap = { status: 'failed', rows: baselines.values.size, error: error.message, failures: [] };
          if (runtime) { const retry = setTimeout(bootstrap, retryMs); retry.unref?.(); }
        }
      };
      void bootstrap();
    } else {
      state.baseline_bootstrap = { status: 'ready', rows: baselines.values.size, failures: [] };
    }
    return getLiveAlphaRuntimeStatus();
  } catch (error) {
    state = { ...state, enabled: true, status: isUpstoxAuthError(error) ? 'auth_failed' : 'failed', last_error: error.message };
    if (isUpstoxAuthError(error)) {
      state.auth_hint = 'Update UPSTOX_ACCESS_TOKEN on Render, then POST /api/market/upstox-feed/restart.';
    }
    return getLiveAlphaRuntimeStatus();
  }
}

export function stopLiveAlphaRuntime() {
  if (growwFallbackTimer) clearInterval(growwFallbackTimer);
  growwFallbackTimer = null;
  runtime?.feed.stop();
  runtime = null;
  state.status = 'stopped';
  state.evaluation_status = 'stopped';
  return getLiveAlphaRuntimeStatus();
}

function startGrowwSectorIndexFallback({ store, pipeline, instrumentKeys }) {
  if (growwFallbackTimer) return;
  const indexKeys = instrumentKeys.filter((key) => String(key).startsWith('NSE_INDEX|'));
  if (!indexKeys.length) return;
  state.feed_fallback = { mode: 'groww_sector_indices', status: 'active' };
  const pollMs = Math.max(60_000, Number(process.env.LIVE_ALPHA_GROWW_FALLBACK_MS || 120_000));
  const tick = async () => {
    try {
      const snapshots = await pollGrowwIndexSnapshots(indexKeys);
      if (!snapshots.length) return;
      const batch = { snapshots, type: 'groww_fallback' };
      store.ingest(batch);
      pipeline.ingest(batch);
    } catch (error) {
      state.feed_fallback = { mode: 'groww_sector_indices', status: 'failed', error: error.message };
    }
  };
  void tick();
  growwFallbackTimer = setInterval(tick, pollMs);
  growwFallbackTimer.unref?.();
}

export async function restartLiveAlphaRuntime() {
  stopLiveAlphaRuntime();
  return startLiveAlphaRuntime();
}

export function getLiveAlphaRuntimeStatus() {
  return {
    ...state,
    feed: runtime?.feed.status() || null,
    universe: runtime ? { members: runtime.universe.members.length, subscribed_instruments: runtime.feed.instrumentKeys.length, benchmark_key: runtime.universe.benchmarkKey, derivatives: runtime.universe.derivativeResolution } : null,
    bootstrap: runtime?.bootstrap || null,
    research_only: true,
    execution_enabled: false,
  };
}
