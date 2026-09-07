import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import test from 'node:test';
import { ingestPayload, normalizePayload, verifySignature } from './researchSignalIngest.js';

const now = new Date('2026-08-09T06:30:00.000Z');

function sectorPayload() {
  return {
    strategy: 'agi_sector_rotation_v1',
    run_id: 'agi_sector_rotation_v1:2026-08-09',
    as_of: '2026-08-09T06:00:00.000Z',
    schema_version: '1.0',
    research_only: true,
    sectors: [{ sector: 'NIFTYBANK', rank: 1, score: 82.3, close: 50000, ret_5d: 1.2, ret_20d: 3.4, ret_60d: 8.2, rel_20d: 2.1, rel_60d: 4.5, vol_20d: 14.2, max_drawdown: -6.1, rotation: 'leading', risk: 'moderate' }],
    errors: [],
  };
}

test('normalizes the sector strategy payload', () => {
  const result = normalizePayload(sectorPayload(), { now });
  assert.equal(result.table, 'sector_rotation_signals');
  assert.equal(result.run.coverage, 1);
  assert.equal(result.signals[0].return_20d, 3.4);
});

test('normalizes candidates and deterioration rows', () => {
  const payload = {
    strategy: 'agi_equity_opportunity_v1',
    run_id: 'agi_equity_opportunity_v1:2026-08-09',
    as_of: '2026-08-09T06:00:00.000Z', schema_version: '1.0', research_only: true, processed: 50,
    candidates: [{ symbol: 'RELIANCE', rank: 1, score: 78, trend: 'positive', risk: 'low', volume_confirmation: true }],
    deteriorating: [{ symbol: 'EXAMPLE', score: 22, trend: 'negative', risk: 'high', reasons: ['weak relative strength'] }],
  };
  const result = normalizePayload(payload, { now });
  assert.equal(result.run.coverage, 50);
  assert.deepEqual(result.signals.map((row) => row.signal), ['research_candidate', 'risk_review']);
});

test('counts unique company coverage when a risk-review row duplicates a ranked symbol', () => {
  const shared = { symbol: 'RELIANCE', score: 78, trend: 'positive', risk: 'low', volume_confirmation: true };
  const payload = {
    strategy: 'agi_equity_opportunity_v1', run_id: 'agi_equity_opportunity_v1:2026-08-09-duplicate',
    as_of: '2026-08-09T06:00:00.000Z', schema_version: '1.0', research_only: true, processed: 1,
    candidates: [{ ...shared, rank: 1 }], deteriorating: [{ ...shared }],
  };
  const normalized = normalizePayload(payload, { now });
  assert.equal(normalized.coverage, 1);
  assert.equal(normalized.signals.length, 2);
});

test('rejects trading-capable and stale payloads', () => {
  assert.throws(() => normalizePayload({ ...sectorPayload(), research_only: false }, { now }), /research_only/);
  assert.throws(() => normalizePayload({ ...sectorPayload(), as_of: '2026-08-01T00:00:00Z' }, { now }), /accepted window/);
});

test('verifies the exact HMAC request body', () => {
  const body = Buffer.from(JSON.stringify(sectorPayload()));
  const signature = crypto.createHmac('sha256', 'secret').update(body).digest('hex');
  assert.equal(verifySignature(body, signature, 'secret'), true);
  assert.equal(verifySignature(body, signature, 'wrong'), false);
});

test('stores normalized rows and treats a repeated run as idempotent', async () => {
  const calls = [];
  const repository = {
    findRun: async () => null,
    createRun: async (run) => (calls.push(['run', run]), { id: 'run-uuid' }),
    insertSignals: async (table, rows) => calls.push(['signals', table, rows]),
    markProcessed: async (id) => calls.push(['processed', id]),
    removeRun: async () => {},
  };
  const payload = sectorPayload();
  const result = await ingestPayload(payload, Buffer.from(JSON.stringify(payload)), { repository, now });
  assert.equal(result.accepted, 1);
  assert.equal(calls[1][2][0].strategy_run_id, 'run-uuid');
  const duplicate = await ingestPayload(payload, Buffer.from(JSON.stringify(payload)), {
    repository: { ...repository, findRun: async () => ({ id: 'run-uuid', status: 'processed' }) }, now,
  });
  assert.equal(duplicate.duplicate, true);
});
