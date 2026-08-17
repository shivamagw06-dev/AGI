import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { LiveAlphaPersistence } from './liveAlphaPersistence.js';
import { MomentumShadowPipeline } from './liveAlphaShadowPipeline.js';
import { VolumeBaselineIndex } from './minuteVolumeBaseline.js';
import { SynchronizedSnapshotStore, UpstoxMarketFeedV3 } from './upstoxMarketFeedV3.js';
import { bootstrapLiveAlphaVolumeBaselines } from './liveAlphaBaselineBootstrap.js';
import { resolveLiveAlphaDerivatives } from './liveAlphaDerivativeUniverse.js';
import { isUpstoxAuthError } from './upstoxMarketFeedV3.js';
import { attachGrowwDerivatives, GrowwLiveAlphaFeed } from './growwLiveAlphaFeed.js';
import { isGrowwConfigured } from '../providers/groww.js';

const serverDir = path.dirname(fileURLToPath(import.meta.url));
const defaultUniversePath = path.join(serverDir, '../config/live-alpha-universe.example.json');
const nifty500Path = path.join(serverDir, '../../indices/Nifty500.csv');
const SECTOR_INDEX_BY_INDUSTRY = Object.freeze({
  'FINANCIAL SERVICES': 'NSE_INDEX|Nifty Financial Services',
  'INFORMATION TECHNOLOGY': 'NSE_INDEX|Nifty IT',
  'AUTOMOBILE AND AUTO COMPONENTS': 'NSE_INDEX|Nifty Auto',
  'HEALTHCARE': 'NSE_INDEX|Nifty Pharma',
  'FAST MOVING CONSUMER GOODS': 'NSE_INDEX|Nifty FMCG',
  'METALS & MINING': 'NSE_INDEX|Nifty Metal',
  'OIL GAS & CONSUMABLE FUELS': 'NSE_INDEX|Nifty Energy',
  'POWER': 'NSE_INDEX|Nifty Energy',
  'REALTY': 'NSE_INDEX|Nifty Realty',
  'TELECOMMUNICATION': 'NSE_INDEX|Nifty India Digital',
  'CAPITAL GOODS': 'NSE_INDEX|Nifty Infrastructure',
  'CONSTRUCTION': 'NSE_INDEX|Nifty Infrastructure',
  'CONSTRUCTION MATERIALS': 'NSE_INDEX|Nifty Infrastructure',
  'SERVICES': 'NSE_INDEX|Nifty Infrastructure',
});
let runtime = null;
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

export function shouldUseGrowwFallback({ provider, feedStatus, allowFallback, growwConfigured }) {
  return provider === 'upstox'
    && ['auth_failed', 'failed'].includes(String(feedStatus || '').toLowerCase())
    && allowFallback === true
    && growwConfigured === true;
}

export async function loadLiveAlphaPersistenceState(persistence, {
  baselineLimit,
  openingLimit,
  recentLimit,
  now = new Date(),
} = {}) {
  const errors = [];
  const optionalLoad = async (name, load) => {
    try {
      return await load();
    } catch (error) {
      errors.push({ component: name, error: error?.message || String(error) });
      return [];
    }
  };
  const baselines = await optionalLoad('volume_baselines', () => persistence.loadVolumeBaselines({ limit: baselineLimit }));
  const openingSnapshots = await optionalLoad('session_opening_snapshots', () => persistence.loadSessionOpeningSnapshots?.({ now, limit: openingLimit }) || []);
  const recentSnapshots = await optionalLoad('recent_snapshots', () => persistence.loadRecentSnapshots?.({ minutes: 90, limit: recentLimit }) || []);
  return { baselines, openingSnapshots, recentSnapshots, errors };
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
  return { benchmarkKey, members: clean, name: String(config?.name || 'custom'), expectedMembers: Number(config?.expectedMembers || clean.length) };
}

export async function loadLiveAlphaUniverse(filePath = process.env.LIVE_ALPHA_UNIVERSE_PATH || defaultUniversePath) {
  const preset = String(process.env.LIVE_ALPHA_UNIVERSE_PRESET || 'nifty500').trim().toLowerCase();
  if (!process.env.LIVE_ALPHA_UNIVERSE_PATH && preset === 'nifty500') {
    const lines = (await fs.readFile(nifty500Path, 'utf8')).split(/\r?\n/).filter(Boolean);
    const members = lines.slice(1).map((line, index) => {
      const columns = line.split(',').map((value) => value.trim());
      if (columns.length !== 5) throw new Error(`Invalid Nifty 200 CSV row ${index + 2}.`);
      const [, industry, symbol, series, isin] = columns;
      if (series !== 'EQ' || !/^INE[A-Z0-9]{8}[0-9]$/.test(isin)) throw new Error(`Invalid Nifty 200 security at row ${index + 2}.`);
      const normalizedIndustry = industry.toUpperCase();
      return {
        symbol,
        sector: normalizedIndustry.replace(/[^A-Z0-9]+/g, '_').replace(/^_|_$/g, ''),
        instrumentKey: `NSE_EQ|${isin}`,
        sectorInstrumentKey: SECTOR_INDEX_BY_INDUSTRY[normalizedIndustry] || 'NSE_INDEX|Nifty 50',
      };
    });
    return validateLiveAlphaUniverse({ name: 'nifty500', expectedMembers: 500, benchmarkKey: 'NSE_INDEX|Nifty 50', members });
  }
  return validateLiveAlphaUniverse(JSON.parse(await fs.readFile(filePath, 'utf8')));
}

export async function startLiveAlphaRuntime({ Feed = null, FallbackFeed = GrowwLiveAlphaFeed, Persistence = LiveAlphaPersistence } = {}) {
  const enabled = String(process.env.LIVE_ALPHA_SHADOW_ENABLED || '').toLowerCase() === 'true';
  if (!enabled) {
    state = { ...state, enabled: false, status: 'disabled' };
    return getLiveAlphaRuntimeStatus();
  }
  if (runtime) return getLiveAlphaRuntimeStatus();
  try {
    // Live Alpha research engines consume Upstox V3 market-data websocket by default.
    // Groww remains available only when LIVE_ALPHA_PROVIDER=groww is set explicitly.
    const provider = String(process.env.LIVE_ALPHA_PROVIDER || 'upstox').trim().toLowerCase();
    let universe = await loadLiveAlphaUniverse();
    if (provider === 'groww') {
      universe = await attachGrowwDerivatives(universe);
      universe = {
        ...universe,
        members: universe.members.map((member) => member.growwDerivativeInstrumentKey
          ? { ...member, derivativeInstrumentKey: member.growwDerivativeInstrumentKey }
          : member),
        derivativeResolution: universe.growwDerivativeResolution,
      };
    } else {
      universe = await resolveLiveAlphaDerivatives(universe);
    }
    const persistence = new Persistence();
    const baselineLimit = Math.max(20_000, universe.members.length * 376);
    // Preserve the rolling 15m/60m feature window across deploys and brief
    // restarts. Only genuine persisted observations are restored; missing
    // market history is never synthesized. A slow optional restore must not
    // disable the Upstox feed or the strategies that can warm up from live data.
    const estimatedInstrumentCount = universe.members.length * 2 + 20;
    const restored = await loadLiveAlphaPersistenceState(persistence, {
      baselineLimit,
      openingLimit: estimatedInstrumentCount * 15,
      recentLimit: estimatedInstrumentCount * 90,
    });
    const baselines = new VolumeBaselineIndex(restored.baselines);
    const pipeline = new MomentumShadowPipeline({ ...universe, universe: universe.members, baselineIndex: baselines, repository: persistence });
    const { openingSnapshots, recentSnapshots } = restored;
    if (openingSnapshots.length) pipeline.ingest({ snapshots: openingSnapshots });
    if (recentSnapshots.length) pipeline.ingest({ snapshots: recentSnapshots });
    const store = new SynchronizedSnapshotStore();
    const instrumentKeys = [...new Set([universe.benchmarkKey, ...universe.members.flatMap((row) => [row.instrumentKey, row.sectorInstrumentKey, row.derivativeInstrumentKey]).filter(Boolean)])];
    let lastEvaluationMs = 0;
    const FeedClass = Feed || (provider === 'groww' ? GrowwLiveAlphaFeed : UpstoxMarketFeedV3);
    // Upstox-only mode: full websocket feed. Do not mix Groww quote polling.
    const onBatch = async (batch) => {
      pipeline.ingest(batch);
      await persistence.persistBatch(batch);
      if (Date.now() - lastEvaluationMs >= 5_000) {
        lastEvaluationMs = Date.now();
        const evaluation = await pipeline.evaluate(new Date());
        const currentEvaluation = {
          at: new Date().toISOString(), skipped: Boolean(evaluation.skipped), reason: evaluation.reason || null,
          universe_size: evaluation.universe_size || evaluation.coverage || 0,
          required_coverage: evaluation.required_coverage || null,
          coverage_diagnostics: evaluation.coverage_diagnostics || null,
          opening_range_status: evaluation.opening_range_status || null,
          derivatives_status: evaluation.derivatives_status || null,
          persistence: evaluation.persistence || [],
        };
        state.last_evaluation = currentEvaluation;
        state.evaluation_status = classifyEvaluationStatus(currentEvaluation);
        if (!currentEvaluation.skipped) state.last_successful_evaluation = currentEvaluation;
      }
    };
    let feed = new FeedClass({ instrumentKeys, universe, snapshotStore: store, mode: 'full', onBatch });
    runtime = { provider, feed, pipeline, persistence, store, universe, bootstrap: { opening_snapshots: openingSnapshots.length, recent_snapshots: recentSnapshots.length, volume_baselines: baselines.values.size, restore_errors: restored.errors, derivatives: universe.derivativeResolution } };
    state = {
      enabled: true, status: 'starting', evaluation_status: 'warming_up',
      started_at: new Date().toISOString(), last_evaluation: null,
      last_successful_evaluation: null, last_error: null,
    };
    await feed.start();
    const allowGrowwFallback = String(process.env.LIVE_ALPHA_ALLOW_GROWW_FALLBACK || '').toLowerCase() === 'true';
    const initialFeedStatus = feed.status?.().status || feed.state?.status;
    if (shouldUseGrowwFallback({ provider, feedStatus: initialFeedStatus, allowFallback: allowGrowwFallback, growwConfigured: isGrowwConfigured() })) {
      feed.stop?.();
      feed = new FallbackFeed({ instrumentKeys, universe, snapshotStore: store, mode: 'full', onBatch });
      await feed.start();
      runtime.feed = feed;
      runtime.provider = 'groww';
      state.feed_fallback = {
        mode: 'groww_full_research_feed', status: feed.status?.().status || 'connected',
        reason: `upstox_${initialFeedStatus}`,
        derivatives: 'unavailable_until_groww_derivative_mapping',
      };
      state.status = feed.status?.().status === 'connected' ? 'running' : 'degraded';
    } else if (['auth_failed', 'failed'].includes(String(initialFeedStatus || '').toLowerCase())) {
      state.status = initialFeedStatus;
      state.evaluation_status = 'blocked';
      state.last_error = feed.status?.().last_error || `Primary provider ${initialFeedStatus}`;
    } else {
      state.status = 'running';
    }
    const missingBaselineMembers = universe.members.filter((member) => !baselines.hasInstrument(member.instrumentKey));
    if (missingBaselineMembers.length) {
      state.baseline_bootstrap = { status: 'running', rows: baselines.values.size, covered_instruments: baselines.instrumentCount(), missing_instruments: missingBaselineMembers.length, failures: [] };
      const retryMs = Math.max(60_000, Number(process.env.LIVE_ALPHA_BASELINE_RETRY_MS || 5 * 60_000));
      const bootstrap = async () => {
        try {
          const remainingMembers = universe.members.filter((member) => !baselines.hasInstrument(member.instrumentKey));
          const result = await bootstrapLiveAlphaVolumeBaselines({ members: remainingMembers, persistence, baselineIndex: baselines });
          result.covered_instruments = baselines.instrumentCount();
          result.missing_instruments = universe.members.filter((member) => !baselines.hasInstrument(member.instrumentKey)).length;
          if (result.missing_instruments > 0) result.status = 'partial';
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
      state.baseline_bootstrap = { status: 'ready', rows: baselines.values.size, covered_instruments: baselines.instrumentCount(), missing_instruments: 0, failures: [] };
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
  runtime?.feed.stop();
  runtime = null;
  state.status = 'stopped';
  state.evaluation_status = 'stopped';
  return getLiveAlphaRuntimeStatus();
}

export async function restartLiveAlphaRuntime() {
  stopLiveAlphaRuntime();
  return startLiveAlphaRuntime();
}

export function getLiveAlphaRuntimeStatus() {
  const feed = runtime?.feed.status() || null;
  const runtimeStatus = !runtime || !feed || ['connected', 'idle'].includes(feed.status)
    ? state.status
    : ['auth_failed', 'failed'].includes(feed.status) ? feed.status : 'degraded';
  return {
    ...state, status: runtimeStatus,
    provider: runtime?.provider || null,
    feed,
    universe: runtime ? { name: runtime.universe.name, members: runtime.universe.members.length, expected_members: runtime.universe.expectedMembers, coverage_complete: runtime.universe.members.length === runtime.universe.expectedMembers, subscribed_instruments: runtime.feed.instrumentKeys.length, benchmark_key: runtime.universe.benchmarkKey, derivatives: runtime.universe.derivativeResolution } : null,
    bootstrap: runtime?.bootstrap || null,
    provider_policy: {
      primary: String(process.env.LIVE_ALPHA_PROVIDER || 'upstox').trim().toLowerCase(),
      fallback: 'groww',
      fallback_allowed: String(process.env.LIVE_ALPHA_ALLOW_GROWW_FALLBACK || '').toLowerCase() === 'true',
      fallback_configured: isGrowwConfigured(),
      active: runtime?.provider || null,
    },
    research_only: true,
    execution_enabled: false,
  };
}

export function getLiveAlphaMarketSnapshot(symbols = [], { now = new Date() } = {}) {
  const status = getLiveAlphaRuntimeStatus();
  const requested = [...new Set((symbols || []).map((value) => String(value || '').trim().toUpperCase()).filter(Boolean))];
  const members = new Map((runtime?.universe?.members || []).map((member) => [member.symbol, member]));
  const quotes = {};

  for (const symbol of requested) {
    const member = members.get(symbol);
    const snapshot = member ? runtime?.store.get(member.instrumentKey) : null;
    const quality = member && runtime?.store ? runtime.store.quality(member.instrumentKey, { now }) : null;
    const quoteAgeMs = quality?.age_ms ?? null;
    const checks = {
      live_feed_connected: status.feed?.status === 'connected',
      instrument_mapped: Boolean(member),
      quote_received: Boolean(snapshot),
      quote_fresh: Boolean(quality?.pass),
      timestamp_valid: Boolean(snapshot?.effective_timestamp),
      session_valid: Boolean(snapshot?.received_at),
    };
    const reasonCodes = [];
    if (!checks.live_feed_connected) reasonCodes.push('LIVE_FEED_DISCONNECTED');
    if (!checks.instrument_mapped) reasonCodes.push('INSTRUMENT_NOT_MAPPED');
    if (checks.instrument_mapped && !checks.quote_received) reasonCodes.push('LIVE_QUOTE_NOT_RECEIVED');
    if (checks.quote_received) reasonCodes.push(...(quality?.reason_codes || []));
    if (checks.quote_received && !checks.timestamp_valid) reasonCodes.push('INVALID_LIVE_TIMESTAMP');
    if (checks.quote_received && !checks.session_valid) reasonCodes.push('INVALID_LIVE_SESSION');
    quotes[symbol] = {
      symbol,
      instrument_key: member?.instrumentKey || null,
      source: status.provider || 'upstox',
      ltp: snapshot?.ltp ?? null,
      previous_close: snapshot?.previous_close ?? null,
      average_traded_price: snapshot?.average_traded_price ?? null,
      cumulative_volume: snapshot?.cumulative_volume ?? null,
      open_interest: snapshot?.open_interest ?? null,
      best_bid: snapshot?.best_bid ?? null,
      best_ask: snapshot?.best_ask ?? null,
      spread_bps: snapshot?.spread_bps ?? null,
      day_ohlc: snapshot?.ohlc || null,
      exchange_timestamp: snapshot?.exchange_timestamp || null,
      provider_timestamp: snapshot?.server_timestamp || null,
      received_at: snapshot?.received_at || null,
      ingested_at: snapshot?.ingested_at || snapshot?.received_at || null,
      effective_timestamp: snapshot?.effective_timestamp || null,
      timestamp_source: snapshot?.timestamp_source || null,
      quote_age_ms: quoteAgeMs,
      data_quality: reasonCodes.length ? 'BLOCKED' : 'PASS',
      checks: checks,
      reason_codes: reasonCodes,
    };
  }

  return {
    provider: status.provider || 'upstox',
    status: status.feed?.status || status.status,
    observed_at: now.toISOString(),
    last_heartbeat: status.feed?.last_message_at || null,
    subscribed_instruments: status.feed?.subscribed_instruments || 0,
    observed_instruments: runtime?.store?.latest?.size || 0,
    messages: status.feed?.messages || 0,
    decode_errors: status.feed?.decode_errors || 0,
    reconnects: status.feed?.reconnects || 0,
    snapshot_quality: runtime?.store?.stats() || null,
    research_only: true,
    quotes,
  };
}
