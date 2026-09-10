/**
 * Ported from vitest to node:test.
 *
 * This one needs module mocking rather than injection: createMarketRouter
 * imports its services at module scope and starts four schedulers the moment it
 * is constructed, so there is no seam to pass fakes through, and refactoring a
 * production router to suit a test is the wrong way round.
 *
 * node:test provides mock.module behind --experimental-test-module-mocks, which
 * the npm test script passes. The router is imported dynamically, after the
 * mocks are registered: a static import is hoisted and would load the real
 * services - and start their schedulers - before any mock existed.
 */
import test, { describe, mock } from 'node:test';
import assert from 'node:assert/strict';
// Static, and deliberately: express is not mocked, and importing it through the
// module mocker breaks its own internal CommonJS resolution
// ("Cannot find module './middleware/init'"). A static import is hoisted above
// the mock registrations below, which is exactly right for a module that must
// stay real.
import express from 'express';

mock.module('../services/marketDataService.js', {
  namedExports: {
    getTickerData: async () => ({
      items: [{ name: 'NIFTY 50', price: 24000, percentChange: 0.1 }],
      source: 'test',
      updatedAt: '2026-08-05T00:00:00.000Z',
    }),
    getDashboardData: async () => ({
      gainers: [{ symbol: 'AAA', price: 1, change: 2 }],
      losers: [{ symbol: 'BBB', price: 1, change: -2 }],
      pulse: { label: 'Neutral' },
      outlook: { marketBreadth: 'mixed' },
    }),
  },
});

mock.module('../providers/yahooIndices.js', {
  namedExports: {
    fetchYahooIndices: async () => ([{ name: 'NASDAQ', price: 18000, percentChange: 0.5, source: 'Yahoo' }]),
  },
});

mock.module('../services/intelligenceService.js', {
  namedExports: { getAgiIntelligence: async () => ({}), getDashboardFromIntelligence: async () => ({}) },
});

mock.module('../services/growwHealth.js', { namedExports: { getGrowwHealth: async () => ({ ok: true }) } });

mock.module('../services/upstoxHealth.js', {
  namedExports: { getUpstoxHealth: async () => ({ ok: true }), getUpstoxCapabilities: async () => ({ ok: true }) },
});

mock.module('../services/marketBriefingService.js', {
  namedExports: { getMarketBriefing: async () => ({}), startMarketBriefingScheduler: () => {} },
});

mock.module('../services/macroBriefingService.js', {
  namedExports: { getMacroBriefing: async () => ({}), askMacroEconomist: async () => ({}), startMacroBriefingScheduler: () => {} },
});

mock.module('../services/preMarketBriefingService.js', {
  namedExports: { getPreMarketBriefing: async () => ({}), startPreMarketBriefingScheduler: () => {} },
});

mock.module('../services/fxIntelligenceService.js', {
  namedExports: {
    fetchFxIntelligence: async () => ({
      ok: true,
      pairs: [],
      drivers: [],
      providers: { upstox: { ok: true, quotes: 1, targets: 2 } },
    }),
  },
});

// Dynamic, and equally deliberately: this one must load after the mocks, and a
// static import would be hoisted above them - loading the real services and
// starting their schedulers.
const createMarketRouter = (await import('../routes/market.js')).default;

/** Start the router on an ephemeral port and return the response to one path. */
async function call(path) {
  const app = express();
  app.use('/api/market', createMarketRouter({}));
  const server = await new Promise((resolve) => { const s = app.listen(0, () => resolve(s)); });
  try {
    const res = await fetch(`http://127.0.0.1:${server.address().port}${path}`);
    return { res, body: await res.json() };
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

describe('market overview / global-snapshot routes', () => {
  test('serves /overview from Groww/NSE dashboard data (not IndianAPI)', async () => {
    const { res, body } = await call('/api/market/overview');
    assert.equal(res.status, 200);
    assert.equal(body.ok, true);
    assert.equal(body.items[0].name, 'NIFTY 50');
    assert.equal(body.gainers[0].symbol, 'AAA');
    assert.equal(body.error, undefined);
  });

  test('serves /global-snapshot from Yahoo', async () => {
    const { res, body } = await call('/api/market/global-snapshot');
    assert.equal(res.status, 200);
    assert.equal(body.source, 'yahoo');
    assert.equal(body.items[0].name, 'NASDAQ');
  });

  test('keeps the FX route cache aligned with its one-minute reference feed', async () => {
    const { res, body } = await call('/api/market/fx-intelligence');
    assert.equal(res.status, 200);
    assert.equal(body.ok, true);
    assert.equal(res.headers.get('cache-control'), 'public, max-age=30, stale-while-revalidate=30');
  });
});
