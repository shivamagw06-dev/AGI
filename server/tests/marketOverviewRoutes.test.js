import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../services/marketDataService.js', () => ({
  getTickerData: vi.fn(async () => ({
    items: [{ name: 'NIFTY 50', price: 24000, percentChange: 0.1 }],
    source: 'test',
    updatedAt: '2026-08-05T00:00:00.000Z',
  })),
  getDashboardData: vi.fn(async () => ({
    gainers: [{ symbol: 'AAA', price: 1, change: 2 }],
    losers: [{ symbol: 'BBB', price: 1, change: -2 }],
    pulse: { label: 'Neutral' },
    outlook: { marketBreadth: 'mixed' },
  })),
}));

vi.mock('../providers/yahooIndices.js', () => ({
  fetchYahooIndices: vi.fn(async () => ([
    { name: 'NASDAQ', price: 18000, percentChange: 0.5, source: 'Yahoo' },
  ])),
}));

vi.mock('../services/intelligenceService.js', () => ({
  getAgiIntelligence: vi.fn(async () => ({})),
  getDashboardFromIntelligence: vi.fn(async () => ({})),
}));

vi.mock('../services/growwHealth.js', () => ({
  getGrowwHealth: vi.fn(async () => ({ ok: true })),
}));

vi.mock('../services/upstoxHealth.js', () => ({
  getUpstoxHealth: vi.fn(async () => ({ ok: true })),
  getUpstoxCapabilities: vi.fn(async () => ({ ok: true })),
}));

vi.mock('../services/marketBriefingService.js', () => ({
  getMarketBriefing: vi.fn(async () => ({})),
  startMarketBriefingScheduler: vi.fn(),
}));

vi.mock('../services/macroBriefingService.js', () => ({
  getMacroBriefing: vi.fn(async () => ({})),
  askMacroEconomist: vi.fn(async () => ({})),
  startMacroBriefingScheduler: vi.fn(),
}));

vi.mock('../services/preMarketBriefingService.js', () => ({
  getPreMarketBriefing: vi.fn(async () => ({})),
  startPreMarketBriefingScheduler: vi.fn(),
}));

vi.mock('../services/fxIntelligenceService.js', () => ({
  fetchFxIntelligence: vi.fn(async () => ({
    ok: true,
    pairs: [],
    drivers: [],
    providers: { upstox: { ok: true, quotes: 1, targets: 2 } },
  })),
}));

import express from 'express';
import createMarketRouter from '../routes/market.js';

function listen(app) {
  return new Promise((resolve) => {
    const server = app.listen(0, () => resolve(server));
  });
}

describe('market overview / global-snapshot routes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('serves /overview from Groww/NSE dashboard data (not IndianAPI)', async () => {
    const app = express();
    app.use('/api/market', createMarketRouter({}));
    const server = await listen(app);
    const { port } = server.address();
    const res = await fetch(`http://127.0.0.1:${port}/api/market/overview`);
    const body = await res.json();
    server.close();
    expect(res.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.items[0].name).toBe('NIFTY 50');
    expect(body.gainers[0].symbol).toBe('AAA');
    expect(body.error).toBeUndefined();
  });

  it('serves /global-snapshot from Yahoo', async () => {
    const app = express();
    app.use('/api/market', createMarketRouter({}));
    const server = await listen(app);
    const { port } = server.address();
    const res = await fetch(`http://127.0.0.1:${port}/api/market/global-snapshot`);
    const body = await res.json();
    server.close();
    expect(res.status).toBe(200);
    expect(body.source).toBe('yahoo');
    expect(body.items[0].name).toBe('NASDAQ');
  });

  it('keeps the FX route cache aligned with its one-minute reference feed', async () => {
    const app = express();
    app.use('/api/market', createMarketRouter({}));
    const server = await listen(app);
    const { port } = server.address();
    const res = await fetch(`http://127.0.0.1:${port}/api/market/fx-intelligence`);
    const body = await res.json();
    server.close();
    expect(res.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(res.headers.get('cache-control')).toBe('public, max-age=30, stale-while-revalidate=30');
  });
});
