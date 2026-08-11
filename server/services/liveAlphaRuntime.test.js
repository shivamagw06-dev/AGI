import assert from 'node:assert/strict';
import test from 'node:test';
import { classifyEvaluationStatus, startLiveAlphaRuntime, stopLiveAlphaRuntime, validateLiveAlphaUniverse } from './liveAlphaRuntime.js';

const valid = { benchmarkKey: 'NSE_INDEX|Nifty 50', members: Array.from({ length: 10 }, (_, index) => ({ symbol: `S${index}`, sector: 'BANK', instrumentKey: `NSE_EQ|${index}`, sectorInstrumentKey: 'NSE_INDEX|Nifty Bank' })) };

test('validates unique stock and sector mappings', () => {
  assert.equal(validateLiveAlphaUniverse(valid).members.length, 10);
  assert.throws(() => validateLiveAlphaUniverse({ ...valid, members: valid.members.slice(0, 5) }), /at least 10/);
  const duplicate = structuredClone(valid); duplicate.members[1].symbol = duplicate.members[0].symbol;
  assert.throws(() => validateLiveAlphaUniverse(duplicate), /Duplicate/);
  const invalidDerivative = structuredClone(valid); invalidDerivative.members[0].derivativeInstrumentKey = 'NSE_EQ|NOT_A_FUTURE';
  assert.throws(() => validateLiveAlphaUniverse(invalidDerivative), /derivative instrument/);
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
