import assert from 'node:assert/strict';
import test from 'node:test';
import { getLiveAlphaWorkspace } from './liveAlphaWorkspace.js';

test('joins stored signals to their research engine without execution fields', async () => {
  const responses = [
    [{ id: 'run-1', engine: 'cross_sectional_momentum_v1', as_of: '2026-08-09T06:00:00Z' }],
    [{ id: 'signal-1', run_id: 'run-1', symbol: 'SBIN', classification: 'positive_research_candidate' }],
  ];
  const fetchImpl = async () => ({ ok: true, json: async () => responses.shift() || [] });
  const priorUrl = process.env.SUPABASE_URL; const priorKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  process.env.SUPABASE_URL = 'https://example.supabase.co'; process.env.SUPABASE_SERVICE_ROLE_KEY = 'test';
  const result = await getLiveAlphaWorkspace({ fetchImpl });
  assert.equal(result.signals[0].engine, 'cross_sectional_momentum_v1');
  assert.equal(result.execution_enabled, false);
  assert.equal(result.strategy_health.cross_sectional_momentum_v1.stored_signals, 1);
  if (priorUrl === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = priorUrl;
  if (priorKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = priorKey;
});

test('reports stale and orphaned engine runs instead of claiming readiness', async () => {
  const responses = [
    [
      { id: 'momentum-run', engine: 'cross_sectional_momentum_v1', as_of: '2026-08-11T04:00:00Z' },
      { id: 'volume-run', engine: 'volume_liquidity_anomaly_v1', as_of: '2026-08-11T04:00:00Z' },
    ],
    [{ id: 'signal-1', run_id: 'momentum-run', symbol: 'SBIN', classification: 'positive_research_candidate' }],
  ];
  const fetchImpl = async () => ({ ok: true, json: async () => responses.shift() || [] });
  const priorUrl = process.env.SUPABASE_URL; const priorKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  process.env.SUPABASE_URL = 'https://example.supabase.co'; process.env.SUPABASE_SERVICE_ROLE_KEY = 'test';
  try {
    const result = await getLiveAlphaWorkspace({ fetchImpl, now: new Date('2026-08-11T05:00:00Z') });
    assert.equal(result.readiness.status, 'persistence_degraded');
    assert.deepEqual(result.readiness.degraded_engines, ['volume_liquidity_anomaly_v1']);
    assert.equal(result.strategy_health.cross_sectional_momentum_v1.status, 'stale');
    assert.equal(result.strategy_health.volume_liquidity_anomaly_v1.status, 'persistence_failed');
    assert.equal(result.freshness.stale, true);
    assert.equal(result.freshness.latest_successful_at, '2026-08-11T04:00:00Z');
  } finally {
    if (priorUrl === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = priorUrl;
    if (priorKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = priorKey;
  }
});

test('returns the latest Groww sector and equity research results', async () => {
  const responses = [[], [{ id: 'sector-run', strategy: 'agi_sector_rotation_v1', as_of: '2026-08-09T06:00:00Z' }, { id: 'equity-run', strategy: 'agi_equity_opportunity_v1', as_of: '2026-08-09T06:05:00Z' }], [{ sector: 'BANK', rank: 1, score: 88 }], [{ symbol: 'SBIN', signal: 'research_candidate', rank: 1, score: 84 }]];
  const fetchImpl = async () => ({ ok: true, json: async () => responses.shift() || [] });
  const priorUrl = process.env.SUPABASE_URL; const priorKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  process.env.SUPABASE_URL = 'https://example.supabase.co'; process.env.SUPABASE_SERVICE_ROLE_KEY = 'test';
  const result = await getLiveAlphaWorkspace({ fetchImpl });
  assert.equal(result.groww.sectors[0].sector, 'BANK');
  assert.equal(result.groww.equities[0].symbol, 'SBIN');
  if (priorUrl === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = priorUrl;
  if (priorKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = priorKey;
});

test('returns an honest empty workspace when storage is not configured', async () => {
  const priorUrl = process.env.SUPABASE_URL; const priorKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  delete process.env.SUPABASE_URL; delete process.env.SUPABASE_SERVICE_ROLE_KEY;
  const result = await getLiveAlphaWorkspace();
  assert.deepEqual(result.runs, []); assert.deepEqual(result.signals, []);
  if (priorUrl !== undefined) process.env.SUPABASE_URL = priorUrl;
  if (priorKey !== undefined) process.env.SUPABASE_SERVICE_ROLE_KEY = priorKey;
});

test('reports database setup required when alpha tables are not migrated', async () => {
  const fetchImpl = async () => ({ ok: false, status: 404 });
  const priorUrl = process.env.SUPABASE_URL; const priorKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  process.env.SUPABASE_URL = 'https://example.supabase.co'; process.env.SUPABASE_SERVICE_ROLE_KEY = 'test';
  const result = await getLiveAlphaWorkspace({ fetchImpl });
  assert.equal(result.readiness.status, 'database_setup_required');
  assert.equal(result.signals.length, 0);
  assert.equal(result.execution_enabled, false);
  if (priorUrl === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = priorUrl;
  if (priorKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = priorKey;
});
