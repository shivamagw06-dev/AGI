import test from 'node:test';
import assert from 'node:assert/strict';
import { clearNifty500ResearchCache, getResearchUniverse } from './nifty500ResearchService.js';

test('screener universe loads the complete published run without exposing service credentials', async () => {
  const oldFetch = globalThis.fetch;
  const oldUrl = process.env.SUPABASE_URL;
  const oldKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  process.env.SUPABASE_URL = 'https://example.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'server-only-test-key';
  const requests = [];
  globalThis.fetch = async (url, options) => {
    requests.push({ url: String(url), options });
    const data = String(url).includes('nifty500_research_runs')
      ? [{ id: 'run-1', status: 'published', generated_at: '2026-09-29T00:00:00Z', total_stocks_analyzed: 500 }]
      : [{ symbol: 'TCS', overall_sentiment: 'Bullish', agi_research_score: 72.5, ai_confidence_percent: 81, risk_factors: ['Valuation'], supporting_factors: ['Cash flow'], last_updated: '2026-09-29T00:00:00Z' }];
    return { ok: true, json: async () => data };
  };
  try {
    clearNifty500ResearchCache();
    const result = await getResearchUniverse();
    assert.equal(result.items.length, 1);
    assert.equal(result.items[0].symbol, 'TCS');
    assert.equal(result.items[0].agiResearchScore, 72.5);
    assert.equal(requests.length, 2);
    assert.match(requests[1].url, /limit=1000/);
    assert.equal(JSON.stringify(result).includes('server-only-test-key'), false);
  } finally {
    globalThis.fetch = oldFetch;
    if (oldUrl === undefined) delete process.env.SUPABASE_URL;
    else process.env.SUPABASE_URL = oldUrl;
    if (oldKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY;
    else process.env.SUPABASE_SERVICE_ROLE_KEY = oldKey;
    clearNifty500ResearchCache();
  }
});
