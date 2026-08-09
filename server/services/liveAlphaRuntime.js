import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { LiveAlphaPersistence } from './liveAlphaPersistence.js';
import { MomentumShadowPipeline } from './liveAlphaShadowPipeline.js';
import { VolumeBaselineIndex } from './minuteVolumeBaseline.js';
import { SynchronizedSnapshotStore, UpstoxMarketFeedV3 } from './upstoxMarketFeedV3.js';

const serverDir = path.dirname(fileURLToPath(import.meta.url));
const defaultUniversePath = path.join(serverDir, '../config/live-alpha-universe.example.json');
let runtime = null;
let state = { enabled: false, status: 'disabled', started_at: null, last_evaluation: null, last_error: null };

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
      minimumLiquidity: row.minimumLiquidity !== false,
    };
    if (!/^[A-Z0-9&-]+$/.test(member.symbol) || !member.sector || !member.instrumentKey.includes('|') || !member.sectorInstrumentKey.startsWith('NSE_INDEX|')) throw new Error(`Invalid universe member at index ${index}.`);
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
    const universe = await loadLiveAlphaUniverse();
    const persistence = new Persistence();
    const baselines = new VolumeBaselineIndex(await persistence.loadVolumeBaselines());
    const pipeline = new MomentumShadowPipeline({ ...universe, universe: universe.members, baselineIndex: baselines, repository: persistence });
    const store = new SynchronizedSnapshotStore();
    const instrumentKeys = [...new Set([universe.benchmarkKey, ...universe.members.flatMap((row) => [row.instrumentKey, row.sectorInstrumentKey])])];
    let lastEvaluationMs = 0;
    const feed = new Feed({ instrumentKeys, snapshotStore: store, onBatch: async (batch) => {
      pipeline.ingest(batch);
      await persistence.persistBatch(batch);
      if (Date.now() - lastEvaluationMs >= 5_000) {
        lastEvaluationMs = Date.now();
        const evaluation = await pipeline.evaluate(new Date());
        state.last_evaluation = { at: new Date().toISOString(), skipped: Boolean(evaluation.skipped), reason: evaluation.reason || null, universe_size: evaluation.universe_size || evaluation.coverage || 0 };
      }
    } });
    runtime = { feed, pipeline, persistence, store, universe };
    state = { enabled: true, status: 'starting', started_at: new Date().toISOString(), last_evaluation: null, last_error: null };
    await feed.start();
    state.status = 'running';
    return getLiveAlphaRuntimeStatus();
  } catch (error) {
    state = { ...state, enabled: true, status: 'failed', last_error: error.message };
    return getLiveAlphaRuntimeStatus();
  }
}

export function stopLiveAlphaRuntime() {
  runtime?.feed.stop();
  runtime = null;
  state.status = 'stopped';
  return getLiveAlphaRuntimeStatus();
}

export function getLiveAlphaRuntimeStatus() {
  return {
    ...state,
    feed: runtime?.feed.status() || null,
    universe: runtime ? { members: runtime.universe.members.length, subscribed_instruments: runtime.feed.instrumentKeys.length, benchmark_key: runtime.universe.benchmarkKey } : null,
    research_only: true,
    execution_enabled: false,
  };
}
