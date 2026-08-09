import assert from 'node:assert/strict';
import test from 'node:test';
import { startLiveAlphaRuntime, stopLiveAlphaRuntime, validateLiveAlphaUniverse } from './liveAlphaRuntime.js';

const valid = { benchmarkKey: 'NSE_INDEX|Nifty 50', members: Array.from({ length: 10 }, (_, index) => ({ symbol: `S${index}`, sector: 'BANK', instrumentKey: `NSE_EQ|${index}`, sectorInstrumentKey: 'NSE_INDEX|Nifty Bank' })) };

test('validates unique stock and sector mappings', () => {
  assert.equal(validateLiveAlphaUniverse(valid).members.length, 10);
  assert.throws(() => validateLiveAlphaUniverse({ ...valid, members: valid.members.slice(0, 5) }), /at least 10/);
  const duplicate = structuredClone(valid); duplicate.members[1].symbol = duplicate.members[0].symbol;
  assert.throws(() => validateLiveAlphaUniverse(duplicate), /Duplicate/);
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
