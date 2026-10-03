import assert from 'node:assert/strict';
import test from 'node:test';
import { getLiveAlphaWorkspace } from './liveAlphaWorkspace.js';

function withSupabaseEnv(run) {
  const priorUrl = process.env.SUPABASE_URL;
  const priorKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  process.env.SUPABASE_URL = 'https://example.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test';
  return Promise.resolve()
    .then(run)
    .finally(() => {
      if (priorUrl === undefined) delete process.env.SUPABASE_URL;
      else process.env.SUPABASE_URL = priorUrl;
      if (priorKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY;
      else process.env.SUPABASE_SERVICE_ROLE_KEY = priorKey;
    });
}

function mockFetch(handlers) {
  return async (url) => {
    for (const [match, rows] of handlers) {
      if (match(url)) return { ok: true, json: async () => rows };
    }
    return { ok: true, json: async () => [] };
  };
}

test('joins stored signals to their research engine without execution fields', async () => {
  await withSupabaseEnv(async () => {
    const fetchImpl = mockFetch([
      [
        (url) => url.includes('live_alpha_runs') && url.includes('engine=eq.cross_sectional_momentum_v1'),
        [{ id: 'run-1', engine: 'cross_sectional_momentum_v1', as_of: '2026-08-09T06:00:00Z' }],
      ],
      [
        (url) => url.includes('live_alpha_signals') && url.includes('run_id=eq.run-1'),
        [{ id: 'signal-1', run_id: 'run-1', symbol: 'SBIN', classification: 'positive_research_candidate' }],
      ],
    ]);
    const result = await getLiveAlphaWorkspace({ fetchImpl });
    assert.equal(result.signals[0].engine, 'cross_sectional_momentum_v1');
    assert.equal(result.execution_enabled, false);
    assert.equal(result.strategy_health.cross_sectional_momentum_v1.stored_signals, 1);
  });
});

test('reports stale and orphaned engine runs instead of claiming readiness', async () => {
  await withSupabaseEnv(async () => {
    const fetchImpl = mockFetch([
      [
        (url) => url.includes('live_alpha_runs') && url.includes('engine=eq.cross_sectional_momentum_v1'),
        [{ id: 'momentum-run', engine: 'cross_sectional_momentum_v1', as_of: '2026-08-11T04:00:00Z' }],
      ],
      [
        (url) => url.includes('live_alpha_runs') && url.includes('engine=eq.volume_liquidity_anomaly_v1'),
        [{ id: 'volume-run', engine: 'volume_liquidity_anomaly_v1', as_of: '2026-08-11T04:00:00Z' }],
      ],
      [
        (url) => url.includes('live_alpha_signals') && url.includes('run_id=eq.momentum-run'),
        [{ id: 'signal-1', run_id: 'momentum-run', symbol: 'SBIN', classification: 'positive_research_candidate' }],
      ],
      [
        (url) => url.includes('live_alpha_signals') && url.includes('run_id=eq.volume-run'),
        [],
      ],
    ]);
    const result = await getLiveAlphaWorkspace({ fetchImpl, now: new Date('2026-08-11T05:00:00Z') });
    assert.equal(result.readiness.status, 'persistence_degraded');
    assert.deepEqual(result.readiness.degraded_engines, ['volume_liquidity_anomaly_v1']);
    assert.equal(result.strategy_health.cross_sectional_momentum_v1.status, 'stale');
    assert.equal(result.strategy_health.volume_liquidity_anomaly_v1.status, 'persistence_failed');
    assert.equal(result.freshness.stale, true);
    assert.equal(result.freshness.latest_successful_at, '2026-08-11T04:00:00Z');
  });
});

test('loads signals per latest engine run so newer engines cannot crowd older ones out', async () => {
  await withSupabaseEnv(async () => {
    const engines = [
      'cross_sectional_momentum_v1',
      'volume_liquidity_anomaly_v1',
      'opening_range_expansion_v1',
      'intraday_mean_reversion_v1',
      'derivatives_positioning_v1',
    ];
    const runs = engines.map((engine, index) => ({
      id: `run-${index}`,
      engine,
      as_of: '2026-08-13T07:20:00Z',
    }));
    const urls = [];
    const fetchImpl = async (url) => {
      urls.push(url);
      const runMatch = engines.findIndex((engine) => url.includes(`live_alpha_runs`) && url.includes(`engine=eq.${engine}`));
      if (runMatch >= 0) return { ok: true, json: async () => [runs[runMatch]] };
      const signalMatch = runs.find((run) => url.includes(`live_alpha_signals`) && url.includes(`run_id=eq.${run.id}`));
      if (signalMatch) {
        return {
          ok: true,
          json: async () => Array.from({ length: 500 }, (_, index) => ({
            id: `${signalMatch.id}-${index}`,
            run_id: signalMatch.id,
            symbol: `S${index}`,
          })),
        };
      }
      return { ok: true, json: async () => [] };
    };
    const result = await getLiveAlphaWorkspace({ fetchImpl, now: new Date('2026-08-13T07:21:00Z') });
    assert.equal(result.signals.length, 2500);
    assert.equal(result.readiness.status, 'ready');
    assert.deepEqual(result.readiness.degraded_engines, []);
    for (const run of runs) {
      assert.equal(result.strategy_health[run.engine].status, 'ready');
      assert.equal(result.strategy_health[run.engine].stored_signals, 500);
    }
    const signalUrls = urls.filter((url) => url.includes('live_alpha_signals'));
    assert.equal(signalUrls.length, engines.length);
    for (const url of signalUrls) assert.match(url, /limit=500/);
    assert.equal(signalUrls.some((url) => url.includes('run_id=in.')), false);
  });
});

test('returns the latest Groww sector and equity research results', async () => {
  await withSupabaseEnv(async () => {
    const fetchImpl = async (url) => {
      if (url.includes('research_strategy_runs')) {
        return {
          ok: true,
          json: async () => [
            { id: 'sector-run', strategy: 'agi_sector_rotation_v1', as_of: '2026-08-09T06:00:00Z' },
            { id: 'equity-run', strategy: 'agi_equity_opportunity_v1', as_of: '2026-08-09T06:05:00Z' },
          ],
        };
      }
      if (url.includes('sector_rotation_signals')) {
        return { ok: true, json: async () => [{ sector: 'BANK', rank: 1, score: 88 }] };
      }
      if (url.includes('equity_opportunity_signals')) {
        return { ok: true, json: async () => [{ symbol: 'SBIN', signal: 'research_candidate', rank: 1, score: 84 }] };
      }
      return { ok: true, json: async () => [] };
    };
    const result = await getLiveAlphaWorkspace({ fetchImpl });
    assert.equal(result.groww.sectors[0].sector, 'BANK');
    assert.equal(result.groww.equities[0].symbol, 'SBIN');
  });
});

test('returns an honest empty workspace when storage is not configured', async () => {
  const priorUrl = process.env.SUPABASE_URL;
  const priorKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  delete process.env.SUPABASE_URL;
  delete process.env.SUPABASE_SERVICE_ROLE_KEY;
  try {
    const result = await getLiveAlphaWorkspace();
    assert.deepEqual(result.runs, []);
    assert.deepEqual(result.signals, []);
  } finally {
    if (priorUrl !== undefined) process.env.SUPABASE_URL = priorUrl;
    if (priorKey !== undefined) process.env.SUPABASE_SERVICE_ROLE_KEY = priorKey;
  }
});

test('reports database setup required when alpha tables are not migrated', async () => {
  await withSupabaseEnv(async () => {
    const fetchImpl = async () => ({ ok: false, status: 404 });
    const result = await getLiveAlphaWorkspace({ fetchImpl });
    assert.equal(result.readiness.status, 'database_setup_required');
    assert.equal(result.signals.length, 0);
    assert.equal(result.execution_enabled, false);
  });
});
