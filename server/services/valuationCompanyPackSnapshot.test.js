import assert from 'node:assert/strict';
import { describe, it, mock } from 'node:test';

import {
  freshnessForAge,
  getValuationPackRefreshStatus,
  normalizePackWindow,
  packCacheKey,
  refreshValuationCompanyPack,
} from './valuationCompanyPackSnapshot.js';

describe('valuation company pack helpers', () => {
  it('normalizes windows and cache keys', () => {
    assert.equal(normalizePackWindow('5y'), '5Y');
    assert.equal(normalizePackWindow('bad'), '5Y');
    assert.equal(packCacheKey('reliance', '5Y'), 'RELIANCE|5Y');
  });

  it('classifies freshness bands', () => {
    assert.equal(freshnessForAge(0), 'fresh');
    assert.equal(freshnessForAge(20 * 60_000), 'aging');
    assert.equal(freshnessForAge(2 * 60 * 60_000), 'stale');
  });

  it('exposes idle singleflight status', () => {
    const status = getValuationPackRefreshStatus();
    assert.equal(status.in_flight, 0);
    assert.ok(status.fresh_ms > 0);
  });
});

describe('valuation company pack singleflight', () => {
  it('launches only one engine snapshot job per symbol/window', async () => {
    let calls = 0;
    const engineFetch = mock.fn(async () => {
      calls += 1;
      await new Promise((resolve) => setTimeout(resolve, 40));
      return {
        ok: true,
        status: 200,
        data: {
          ok: true,
          pack_id: 'pack-1',
          generated_at: '2026-08-10T08:00:00Z',
          source_as_of: '2026-08-10',
          status: 'ready',
          freshness: 'fresh',
          schema_version: '1.0',
          calculation_version: 'valuation_company_pack_v1',
          data_quality: { health_score: 81 },
          payload: {
            ok: true,
            symbol: 'RELIANCE',
            window: '5Y',
            generated_at: '2026-08-10T08:00:00Z',
            overview: { name: 'Reliance Industries' },
            table: [],
          },
        },
      };
    });

    const [a, b] = await Promise.all([
      refreshValuationCompanyPack({ engineFetch, symbol: 'RELIANCE', window: '5Y' }),
      refreshValuationCompanyPack({ engineFetch, symbol: 'RELIANCE', window: '5Y' }),
    ]);

    assert.equal(calls, 1);
    assert.equal(a.ok, true);
    assert.equal(b.ok, true);
    assert.equal(a.cache?.source, 'engine_snapshot');
    assert.equal(a.read_model, 'supabase_valuation_company_pack');
  });
});
