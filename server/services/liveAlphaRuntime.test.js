import assert from 'node:assert/strict';
import test from 'node:test';
import { classifyEvaluationStatus, loadLiveAlphaUniverse, shouldUseGrowwFallback, startLiveAlphaRuntime, stopLiveAlphaRuntime, validateLiveAlphaUniverse } from './liveAlphaRuntime.js';

const valid = { benchmarkKey: 'NSE_INDEX|Nifty 50', members: Array.from({ length: 10 }, (_, index) => ({ symbol: `S${index}`, sector: 'BANK', instrumentKey: `NSE_EQ|${index}`, sectorInstrumentKey: 'NSE_INDEX|Nifty Bank' })) };

test('validates unique stock and sector mappings', () => {
  assert.equal(validateLiveAlphaUniverse(valid).members.length, 10);
  assert.throws(() => validateLiveAlphaUniverse({ ...valid, members: valid.members.slice(0, 5) }), /at least 10/);
  const duplicate = structuredClone(valid); duplicate.members[1].symbol = duplicate.members[0].symbol;
  assert.throws(() => validateLiveAlphaUniverse(duplicate), /Duplicate/);
  const invalidDerivative = structuredClone(valid); invalidDerivative.members[0].derivativeInstrumentKey = 'NSE_EQ|NOT_A_FUTURE';
  assert.throws(() => validateLiveAlphaUniverse(invalidDerivative), /derivative instrument/);
});

test('loads the complete Nifty 200 default with unique Upstox equity keys', async () => {
  const priorPreset = process.env.LIVE_ALPHA_UNIVERSE_PRESET;
  const priorPath = process.env.LIVE_ALPHA_UNIVERSE_PATH;
  delete process.env.LIVE_ALPHA_UNIVERSE_PRESET;
  delete process.env.LIVE_ALPHA_UNIVERSE_PATH;
  try {
    const universe = await loadLiveAlphaUniverse();
    assert.equal(universe.name, 'nifty200');
    assert.equal(universe.expectedMembers, 200);
    assert.equal(universe.members.length, 200);
    assert.equal(new Set(universe.members.map((row) => row.symbol)).size, 200);
    assert.equal(new Set(universe.members.map((row) => row.instrumentKey)).size, 200);
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
  assert.equal(shouldUseGrowwFallback({ provider: 'upstox', feedStatus: 'connected', allowFallback: true, growwConfigured: true }), false);
  assert.equal(shouldUseGrowwFallback({ provider: 'upstox', feedStatus: 'auth_failed', allowFallback: false, growwConfigured: true }), false);
  assert.equal(shouldUseGrowwFallback({ provider: 'upstox', feedStatus: 'auth_failed', allowFallback: true, growwConfigured: false }), false);
  assert.equal(shouldUseGrowwFallback({ provider: 'groww', feedStatus: 'failed', allowFallback: true, growwConfigured: true }), false);
});
