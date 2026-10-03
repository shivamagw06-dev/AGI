import assert from 'node:assert/strict';
import test from 'node:test';
import { summarizeForecastValidation } from './forecastValidationReport.js';

function row(symbol, day, expected, probability, actual, horizon = '1d') {
  return { forecast_id: `${symbol}-${day}-${horizon}`, actual_alpha_pct: actual, forecast: { symbol, horizon, forecast_time: `${day}T10:00:00Z`, expected_alpha_pct: expected, probability_positive: probability } };
}

test('a model that ranks well shows positive rank IC and quintile spread', () => {
  const rows = [];
  for (let day = 1; day <= 3; day += 1) {
    for (let i = 0; i < 20; i += 1) rows.push(row(`S${i}`, `2026-09-0${day}`, (i - 10) / 10, 0.5 + (i - 10) / 100, (i - 10) / 5 + (day - 2) * 0.1));
  }
  const report = summarizeForecastValidation(rows, { horizon: '1d' });
  assert.equal(report.observations, 60);
  assert.equal(report.forecast_days, 3);
  assert.equal(report.rank_ic_daily_mean, 1);
  assert.ok(report.top_minus_bottom_quintile_pct > 0);
  assert.equal(report.sample_adequate, false);
  assert.equal(report.calibrated, false);
});

test('Brier skill compares with always predicting the base rate', () => {
  // Every forecast says 50%; half the stocks beat their sector. No skill.
  const flat = [row('A', '2026-09-01', 0.1, 0.5, 1), row('B', '2026-09-01', -0.1, 0.5, -1)];
  const report = summarizeForecastValidation(flat, { horizon: '1d' });
  assert.equal(report.brier_score, 0.25);
  assert.equal(report.brier_skill, 0);
  assert.equal(report.directional_accuracy, 100);
  assert.deepEqual(report.calibration.map((band) => [band.band, band.n, band.observed_rate]), [['0.50–0.55', 2, 0.5]]);
});

test('the all-horizon summary keeps rankings within each horizon', () => {
  const rows = [row('A', '2026-09-01', 0.2, 0.55, 0.5, '1d'), row('A', '2026-09-01', 0.4, 0.6, -1, '5d')];
  const report = summarizeForecastValidation(rows);
  assert.equal(report.observations, 2);
  assert.equal(report.rank_ic_daily_mean, undefined);
  assert.deepEqual(Object.keys(report.by_horizon), ['1d', '5d']);
});
