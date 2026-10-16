import assert from 'node:assert/strict';
import test from 'node:test';
import { latestForecastRankingRows } from './forecastV2Store.js';

test('keeps only the latest forecast per symbol and recomputes the ranking', () => {
  const rows = [
    { symbol: 'HCLTECH', forecast_rank: 1, created_at: '2026-08-11T04:00:00Z', forecast: { forecast_time: '2026-08-11T04:00:00Z', expected_alpha_pct: 0.2 } },
    { symbol: 'HCLTECH', forecast_rank: 2, created_at: '2026-08-11T05:00:00Z', forecast: { forecast_time: '2026-08-11T05:00:00Z', expected_alpha_pct: 0.5 } },
    { symbol: 'TITAN', forecast_rank: 3, created_at: '2026-08-11T05:00:00Z', forecast: { forecast_time: '2026-08-11T05:00:00Z', expected_alpha_pct: 0.8 } },
  ];
  const result = latestForecastRankingRows(rows);
  assert.deepEqual(result.map(({ symbol }) => symbol), ['TITAN', 'HCLTECH']);
  assert.deepEqual(result.map(({ forecast_rank }) => forecast_rank), [1, 2]);
  assert.equal(result[0].universe_size, 2);
});
