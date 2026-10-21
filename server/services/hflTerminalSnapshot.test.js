import assert from 'node:assert/strict';
import { describe, it, mock } from 'node:test';

import {
  freshnessForAge,
  getHflTerminalFromReadModel,
  getHflSnapshotRefreshStatus,
  refreshHflTerminalSnapshot,
} from './hflTerminalSnapshot.js';

describe('HFL terminal snapshot freshness', () => {
  it('classifies fresh / aging / stale bands', () => {
    assert.equal(freshnessForAge(0), 'fresh');
    assert.equal(freshnessForAge(14 * 60_000), 'fresh');
    assert.equal(freshnessForAge(20 * 60_000), 'aging');
    assert.equal(freshnessForAge(2 * 60 * 60_000), 'stale');
  });

  it('exposes idle singleflight status by default', () => {
    const status = getHflSnapshotRefreshStatus();
    assert.equal(status.in_flight, false);
    assert.ok(status.fresh_ms > 0);
  });
});

describe('HFL terminal snapshot singleflight', () => {
  it('returns a warming read model without waiting for a cold engine scan', async () => {
    const engineFetch = mock.fn(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
      return { ok: false, status: 503, data: { error: 'warming' } };
    });
    const started = Date.now();

    const result = await getHflTerminalFromReadModel({ engineFetch, limit: 12 });

    assert.equal(result.source, 'warming');
    assert.equal(result.data.status, 'warming');
    assert.equal(result.data.ok, true);
    assert.ok(Date.now() - started < 40);
    await new Promise((resolve) => setTimeout(resolve, 60));
  });

  it('launches only one engine snapshot job for concurrent refreshers', async () => {
    let calls = 0;
    const engineFetch = mock.fn(async () => {
      calls += 1;
      await new Promise((resolve) => setTimeout(resolve, 40));
      return {
        ok: true,
        status: 200,
        data: {
          ok: true,
          snapshot_id: 'snap-1',
          generated_at: '2026-08-10T07:00:00Z',
          source_as_of: '2026-08-10',
          status: 'ready',
          freshness: 'fresh',
          schema_version: '1.0',
          calculation_version: 'hfl_terminal_v1',
          data_quality: { live_opportunities: 3 },
          payload: {
            ok: true,
            generated_at: '2026-08-10T07:00:00Z',
            hero: { live_opportunities: 3 },
            cards: [],
          },
        },
      };
    });

    const [a, b] = await Promise.all([
      refreshHflTerminalSnapshot({ engineFetch, limit: 12 }),
      refreshHflTerminalSnapshot({ engineFetch, limit: 12 }),
    ]);

    assert.equal(calls, 1);
    assert.equal(a.ok, true);
    assert.equal(b.ok, true);
    assert.equal(a.cache?.source, 'engine_snapshot');
    assert.equal(a.read_model, 'supabase_hfl_terminal');
  });
});
