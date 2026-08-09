import assert from 'node:assert/strict';
import test from 'node:test';
import { getLiveAlphaWorkspace } from './liveAlphaWorkspace.js';

test('joins stored signals to their research engine without execution fields', async () => {
  const responses = [
    [{ id: 'run-1', engine: 'cross_sectional_momentum_v1', as_of: '2026-08-09T06:00:00Z' }],
    [{ id: 'signal-1', run_id: 'run-1', symbol: 'SBIN', classification: 'positive_research_candidate' }],
  ];
  const fetchImpl = async () => ({ ok: true, json: async () => responses.shift() });
  const priorUrl = process.env.SUPABASE_URL; const priorKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  process.env.SUPABASE_URL = 'https://example.supabase.co'; process.env.SUPABASE_SERVICE_ROLE_KEY = 'test';
  const result = await getLiveAlphaWorkspace({ fetchImpl });
  assert.equal(result.signals[0].engine, 'cross_sectional_momentum_v1');
  assert.equal(result.execution_enabled, false);
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
