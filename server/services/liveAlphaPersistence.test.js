import assert from 'node:assert/strict';
import test from 'node:test';
import { pagedGet } from './liveAlphaPersistence.js';

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
