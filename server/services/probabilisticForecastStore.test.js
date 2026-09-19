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

test('scores due forecasts from price history, without waiting on the confluence queue', async () => {
  const { settleDueForecasts } = await import('./probabilisticForecastStore.js');
  const event = (capturedAt) => ({ captured_at: capturedAt, instrument_key: 'NSE_EQ|A', sector_instrument_key: 'NSE_INDEX|Nifty IT', benchmark_instrument_key: 'NSE_INDEX|Nifty 50', price_at_signal: 100, sector_index_at_signal: 1000, benchmark_at_signal: 20000 });
  const forecasts = {
    '1d': [
      { id: 'due', horizon: '1d', expected_alpha_pct: 0.3, probability_positive: 0.6, event: event('2026-09-16T09:55:00Z') },
      { id: 'weekend', horizon: '1d', expected_alpha_pct: 0.3, probability_positive: 0.6, event: event('2026-09-13T09:55:00Z') },
      { id: 'not-due', horizon: '1d', expected_alpha_pct: 0.3, probability_positive: 0.6, event: event('2026-09-18T09:55:00Z') },
    ],
  };
  const requests = [];
  const request = async (table, options) => {
    requests.push({ table, ...options });
    if (options.method === 'POST') return [];
    const horizon = /horizon=eq\.(\w+)/.exec(options.query)[1];
    return /offset=0$/.test(options.query) ? forecasts[horizon] || [] : [];
  };
  // Due 17 Sep close: stock +2%, sector +1%, so 1% ahead of its sector.
  const book = { async priceAt(key) { return { price: { 'NSE_EQ|A': 102, 'NSE_INDEX|Nifty IT': 1010, 'NSE_INDEX|Nifty 50': 20100 }[key], candle_end: '2026-09-17T10:00:00.000Z' }; } };
  const summary = await settleDueForecasts({ now: new Date('2026-09-19T06:00:00Z'), book, request, force: true });
  assert.equal(summary.completed, 1);
  assert.equal(summary.skipped.event_outside_session, 1);
  assert.equal(summary.not_due, 1);
  const read = requests.find((entry) => entry.table === 'research_forecasts');
  assert.match(decodeURIComponent(read.query), /research_forecast_outcomes=is\.null/);
  const write = requests.find((entry) => entry.method === 'POST');
  assert.match(write.query, /on_conflict=forecast_id/);
  assert.equal(write.body.length, 1);
  assert.equal(write.body[0].forecast_id, 'due');
  assert.equal(write.body[0].actual_alpha_pct, 1);
  assert.equal(write.body[0].direction_correct, true);
});
