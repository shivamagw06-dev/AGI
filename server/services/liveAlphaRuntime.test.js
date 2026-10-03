import assert from 'node:assert/strict';
import test from 'node:test';
import { classifyEvaluationStatus, feedSupervisorAction, loadLiveAlphaPersistenceState, loadLiveAlphaUniverse, SECTOR_INDEX_BY_INDUSTRY, sectorKeyForLabel, shouldUseGrowwFallback, startLiveAlphaRuntime, stopLiveAlphaRuntime, validateLiveAlphaUniverse } from './liveAlphaRuntime.js';

const valid = { benchmarkKey: 'NSE_INDEX|Nifty 50', members: Array.from({ length: 10 }, (_, index) => ({ symbol: `S${index}`, sector: 'BANK', instrumentKey: `NSE_EQ|${index}`, sectorInstrumentKey: 'NSE_INDEX|Nifty Bank' })) };

test('validates unique stock and sector mappings', () => {
  assert.equal(validateLiveAlphaUniverse(valid).members.length, 10);
  assert.throws(() => validateLiveAlphaUniverse({ ...valid, members: valid.members.slice(0, 5) }), /at least 10/);
  const duplicate = structuredClone(valid); duplicate.members[1].symbol = duplicate.members[0].symbol;
  assert.throws(() => validateLiveAlphaUniverse(duplicate), /Duplicate/);
  const invalidDerivative = structuredClone(valid); invalidDerivative.members[0].derivativeInstrumentKey = 'NSE_EQ|NOT_A_FUTURE';
  assert.throws(() => validateLiveAlphaUniverse(invalidDerivative), /derivative instrument/);
});

test('loads the complete Nifty 500 default with unique equity keys', async () => {
  const priorPreset = process.env.LIVE_ALPHA_UNIVERSE_PRESET;
  const priorPath = process.env.LIVE_ALPHA_UNIVERSE_PATH;
  delete process.env.LIVE_ALPHA_UNIVERSE_PRESET;
  delete process.env.LIVE_ALPHA_UNIVERSE_PATH;
  try {
    const universe = await loadLiveAlphaUniverse();
    assert.equal(universe.name, 'nifty500');
    assert.equal(universe.expectedMembers, 500);
    assert.equal(universe.members.length, 500);
    assert.equal(new Set(universe.members.map((row) => row.symbol)).size, 500);
    assert.equal(new Set(universe.members.map((row) => row.instrumentKey)).size, 500);
    assert.ok(universe.members.every((row) => row.instrumentKey.startsWith('NSE_EQ|INE')));
    assert.ok(universe.members.every((row) => row.sectorInstrumentKey.startsWith('NSE_INDEX|')));
  } finally {
    if (priorPreset === undefined) delete process.env.LIVE_ALPHA_UNIVERSE_PRESET; else process.env.LIVE_ALPHA_UNIVERSE_PRESET = priorPreset;
    if (priorPath === undefined) delete process.env.LIVE_ALPHA_UNIVERSE_PATH; else process.env.LIVE_ALPHA_UNIVERSE_PATH = priorPath;
  }
});

test('runtime remains disabled without the explicit production flag', async () => {
  const prior = process.env.LIVE_ALPHA_SHADOW_ENABLED;
  delete process.env.LIVE_ALPHA_SHADOW_ENABLED;
  const status = await startLiveAlphaRuntime();
  assert.equal(status.status, 'disabled');
  assert.equal(status.execution_enabled, false);
  if (prior !== undefined) process.env.LIVE_ALPHA_SHADOW_ENABLED = prior;
  stopLiveAlphaRuntime();
});

test('separates a connected feed from evaluation readiness', () => {
  assert.equal(classifyEvaluationStatus(null), 'warming_up');
  assert.equal(classifyEvaluationStatus({ skipped: true, reason: 'benchmark_history_incomplete' }), 'warming_up');
  assert.equal(classifyEvaluationStatus({ skipped: true, reason: 'already_evaluated_bucket' }), 'live');
  assert.equal(classifyEvaluationStatus({ skipped: false, persistence: [{ status: 'stored' }] }), 'live');
  assert.equal(classifyEvaluationStatus({ skipped: false, persistence: [{ status: 'failed' }] }), 'degraded');
});

test('only activates Groww fallback for a failed Upstox primary with explicit permission', () => {
  assert.equal(shouldUseGrowwFallback({ provider: 'upstox', feedStatus: 'auth_failed', allowFallback: true, growwConfigured: true }), true);
  assert.equal(shouldUseGrowwFallback({ provider: 'upstox', feedStatus: 'reconnecting', reconnects: 3, lastError: 'Unexpected server response: 403', allowFallback: true, growwConfigured: true }), true);
  assert.equal(shouldUseGrowwFallback({ provider: 'upstox', feedStatus: 'reconnecting', reconnects: 2, lastError: 'Unexpected server response: 403', allowFallback: true, growwConfigured: true }), false);
  assert.equal(shouldUseGrowwFallback({ provider: 'upstox', feedStatus: 'connected', allowFallback: true, growwConfigured: true }), false);
  assert.equal(shouldUseGrowwFallback({ provider: 'upstox', feedStatus: 'auth_failed', allowFallback: false, growwConfigured: true }), false);
  assert.equal(shouldUseGrowwFallback({ provider: 'upstox', feedStatus: 'auth_failed', allowFallback: true, growwConfigured: false }), false);
  assert.equal(shouldUseGrowwFallback({ provider: 'groww', feedStatus: 'failed', allowFallback: true, growwConfigured: true }), false);
});

test('optional persistence timeouts do not disable live alpha startup', async () => {
  const persistence = {
    loadVolumeBaselines: async () => { throw new Error('statement timeout'); },
    loadSessionOpeningSnapshots: async () => [{ instrument_key: 'NSE_EQ|1' }],
    loadRecentSnapshots: async () => { throw new Error('statement timeout'); },
  };

  const restored = await loadLiveAlphaPersistenceState(persistence, {
    baselineLimit: 100,
    openingLimit: 20,
    recentLimit: 50,
  });

  assert.deepEqual(restored.baselines, []);
  assert.equal(restored.openingSnapshots.length, 1);
  assert.deepEqual(restored.recentSnapshots, []);
  assert.deepEqual(restored.errors.map((row) => row.component), ['volume_baselines', 'recent_snapshots']);
});

test('sector benchmarks use keys Upstox actually publishes', async () => {
  // Checked against the public history endpoint on 19 Sep 2026. The three
  // older names returned "Invalid Instrument key", so the feed never sent them
  // and about 200 names had no sector anchor.
  const published = new Set([
    'NSE_INDEX|Nifty 50', 'NSE_INDEX|Nifty Fin Service', 'NSE_INDEX|Nifty IT', 'NSE_INDEX|Nifty Auto',
    'NSE_INDEX|Nifty Pharma', 'NSE_INDEX|Nifty FMCG', 'NSE_INDEX|Nifty Metal', 'NSE_INDEX|Nifty Energy',
    'NSE_INDEX|Nifty Realty', 'NSE_INDEX|NIFTY IND DIGITAL', 'NSE_INDEX|Nifty Infra',
  ]);
  for (const key of Object.values(SECTOR_INDEX_BY_INDUSTRY)) assert.ok(published.has(key), key);
  const prior = process.env.LIVE_ALPHA_UNIVERSE_PATH;
  delete process.env.LIVE_ALPHA_UNIVERSE_PATH;
  try {
    const universe = await loadLiveAlphaUniverse();
    for (const member of universe.members) assert.ok(published.has(member.sectorInstrumentKey), member.symbol);
    assert.equal(universe.members.find((member) => member.symbol === 'HDFCBANK').sectorInstrumentKey, 'NSE_INDEX|Nifty Fin Service');
  } finally {
    if (prior !== undefined) process.env.LIVE_ALPHA_UNIVERSE_PATH = prior;
  }
});

test('the supervisor re-arms an exhausted feed only during market hours', () => {
  const now = Date.parse('2026-09-17T05:00:00Z');
  assert.equal(feedSupervisorAction({ status: 'exhausted' }, { now, marketOpen: true }), 'rearm');
  assert.equal(feedSupervisorAction({ status: 'exhausted' }, { now, marketOpen: false }), null);
  assert.equal(feedSupervisorAction({ status: 'exhausted' }, { now, marketOpen: true, lastRearmMs: now - 60_000 }), null);
  assert.equal(feedSupervisorAction({ status: 'auth_failed' }, { now, marketOpen: true }), null);
  const silent = { status: 'connected', last_message_at: new Date(now - 5 * 60_000).toISOString() };
  assert.equal(feedSupervisorAction(silent, { now, marketOpen: true }), 'recycle_silent');
  const live = { status: 'connected', last_message_at: new Date(now - 10_000).toISOString() };
  assert.equal(feedSupervisorAction(live, { now, marketOpen: true }), null);
});

test('stored sector labels resolve to the index they were anchored to', () => {
  assert.equal(sectorKeyForLabel('BANK'), 'NSE_INDEX|Nifty Bank');
  assert.equal(sectorKeyForLabel('FINANCIAL_SERVICES'), 'NSE_INDEX|Nifty Fin Service');
  assert.equal(sectorKeyForLabel('METALS_MINING'), 'NSE_INDEX|Nifty Metal');
  assert.equal(sectorKeyForLabel('TEXTILES'), null);
});
