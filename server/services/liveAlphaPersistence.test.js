import assert from 'node:assert/strict';
import test from 'node:test';
import { LiveAlphaPersistence, pagedGet } from './liveAlphaPersistence.js';

test('reads past the Supabase 1000-row response boundary', async () => {
  const priorUrl = process.env.SUPABASE_URL;
  const priorKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const priorFetch = globalThis.fetch;
  process.env.SUPABASE_URL = 'https://example.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-service-key';
  const offsets = [];
  globalThis.fetch = async (url) => {
    const parsed = new URL(url);
    const offset = Number(parsed.searchParams.get('offset'));
    const limit = Number(parsed.searchParams.get('limit'));
    offsets.push(offset);
    const available = Math.max(0, 2_350 - offset);
    const count = Math.min(limit, available);
    return { ok: true, text: async () => JSON.stringify(Array.from({ length: count }, (_, index) => ({ id: offset + index }))) };
  };
  try {
    const rows = await pagedGet('rows', { select: 'id', order: 'id.asc' }, { limit: 5_000, pageSize: 1_000 });
    assert.equal(rows.length, 2_350);
    assert.deepEqual(offsets, [0, 1000, 2000]);
    assert.equal(rows.at(-1).id, 2_349);
  } finally {
    globalThis.fetch = priorFetch;
    if (priorUrl === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = priorUrl;
    if (priorKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = priorKey;
  }
});

test('removes the parent run when signal persistence fails', async () => {
  const priorUrl = process.env.SUPABASE_URL;
  const priorKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const priorFetch = globalThis.fetch;
  process.env.SUPABASE_URL = 'https://example.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-service-key';
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, method: options.method });
    if (url.includes('/live_alpha_runs') && options.method === 'POST') {
      return { ok: true, text: async () => JSON.stringify([{ id: 'run-failed' }]) };
    }
    if (url.includes('/live_alpha_signals')) {
      return { ok: false, status: 400, text: async () => 'classification constraint failed' };
    }
    if (url.includes('/live_alpha_runs') && options.method === 'DELETE') {
      return { ok: true, text: async () => '' };
    }
    throw new Error(`Unexpected request: ${options.method} ${url}`);
  };
  const result = {
    engine: 'volume_liquidity_anomaly_v1', as_of: '2026-08-11T04:30:00Z',
    universe_size: 1, config: {}, signals: [{
      symbol: 'SBIN', instrument_key: 'NSE_EQ|SBIN', sector: 'BANK', rank: 1,
      classification: 'abnormal_accumulation_candidate', alpha_z: 1.2,
      signal_quality: { score: 70, label: 'strong' },
      empirical_confidence: { score: null, comparable_observations: 0 },
      liquidity_ok: true, factors: {}, direction: 'positive', price_at_signal: 100,
      nifty_at_signal: 24000, sector_at_signal: 50000, volume_surprise: 1.5,
    }],
  };
  try {
    await assert.rejects(() => new LiveAlphaPersistence().saveVolumeAnomalyRun(result), /classification constraint failed/);
    const cleanup = calls.find((call) => call.method === 'DELETE');
    assert.ok(cleanup);
    assert.match(cleanup.url, /live_alpha_runs\?id=eq\.run-failed/);
  } finally {
    globalThis.fetch = priorFetch;
    if (priorUrl === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = priorUrl;
    if (priorKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = priorKey;
  }
});

test('chunks large snapshot batches for Nifty 200 persistence', async () => {
  const priorUrl = process.env.SUPABASE_URL;
  const priorKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const priorFetch = globalThis.fetch;
  process.env.SUPABASE_URL = 'https://example.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-service-key';
  const sizes = [];
  globalThis.fetch = async (_url, options = {}) => {
    sizes.push(JSON.parse(options.body).length);
    return { ok: true, text: async () => '' };
  };
  try {
    const snapshots = Array.from({ length: 501 }, (_, index) => ({
      instrument_key: `NSE_EQ|${index}`, received_at: '2026-08-11T05:40:00.000Z', ltp: 100,
    }));
    const saved = await new LiveAlphaPersistence().persistBatch({ snapshots });
    assert.equal(saved, 501);
    assert.deepEqual(sizes, [250, 250, 1]);
  } finally {
    globalThis.fetch = priorFetch;
    if (priorUrl === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = priorUrl;
    if (priorKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = priorKey;
  }
});
