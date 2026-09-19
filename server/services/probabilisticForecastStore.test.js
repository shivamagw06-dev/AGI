import assert from 'node:assert/strict';
import test from 'node:test';
import { selectDailyForecastEvents } from './probabilisticForecastStore.js';
import { indiaTradingDayAfterClose } from './dailyForecastSchedule.js';

test('selects one latest confluence event per stock and trading date', () => {
  const rows=selectDailyForecastEvents([{id:'a1',symbol:'INFY',captured_at:'2026-08-11T04:00:00Z'},{id:'a2',symbol:'INFY',captured_at:'2026-08-11T10:00:00Z'},{id:'b1',symbol:'TCS',captured_at:'2026-08-11T09:00:00Z'}]);
  assert.deepEqual(rows.map((row)=>row.id),['b1','a2']);
});

test('opens the daily forecast window only after 15:40 IST on weekdays', () => {
  assert.equal(indiaTradingDayAfterClose(new Date('2026-08-11T10:09:00Z')),null);
  assert.equal(indiaTradingDayAfterClose(new Date('2026-08-11T10:10:00Z')),'2026-08-11');
  assert.equal(indiaTradingDayAfterClose(new Date('2026-08-15T11:00:00Z')),null);
});

test('scores only unscored forecasts whose matching outcome completed, in one write', async () => {
  const requests = [];
  const prior = { url: process.env.SUPABASE_URL, key: process.env.SUPABASE_SERVICE_ROLE_KEY, fetch: globalThis.fetch };
  process.env.SUPABASE_URL = 'https://db.example';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-key';
  globalThis.fetch = async (url, options = {}) => {
    requests.push({ url: decodeURIComponent(url), method: options.method || 'GET', body: options.body ? JSON.parse(options.body) : null });
    const body = options.method === 'POST' ? '' : String(url).includes('horizon=eq.1d')
      ? JSON.stringify([{ id: 'f1', horizon: '1d', expected_alpha_pct: 0.3, probability_positive: 0.6, research_forecast_outcomes: null, event: { outcomes: [{ observed_at: '2026-09-02T10:00:00Z', sector_adjusted_alpha_pct: 0.8, horizon: '1d', status: 'completed' }] } }])
      : '[]';
    return { ok: true, status: 200, text: async () => body };
  };
  try {
    const { settleDueForecasts } = await import('./probabilisticForecastStore.js');
    const summary = await settleDueForecasts();
    assert.equal(summary.completed, 1);
    const read = requests.find((request) => request.url.includes('horizon=eq.1d'));
    assert.match(read.url, /research_forecast_outcomes=is\.null/);
    assert.match(read.url, /event\.outcomes\.status=eq\.completed/);
    assert.match(read.url, /event\.outcomes\.horizon=eq\.1d/);
    const write = requests.find((request) => request.method === 'POST');
    assert.match(write.url, /on_conflict=forecast_id/);
    assert.deepEqual(write.body.map((row) => [row.forecast_id, row.actual_alpha_pct, row.direction_correct]), [['f1', 0.8, true]]);
  } finally {
    globalThis.fetch = prior.fetch;
    if (prior.url === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = prior.url;
    if (prior.key === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = prior.key;
  }
});
