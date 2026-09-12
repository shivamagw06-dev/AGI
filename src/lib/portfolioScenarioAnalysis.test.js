import test from 'node:test';
import assert from 'node:assert/strict';

import {
  PORTFOLIO_SCENARIO_PRESETS,
  buildPortfolioScenarioReport,
  runPortfolioScenario,
} from './portfolioScenarioAnalysis.js';

test('calculates a weighted scenario impact and its contributors', () => {
  const result = runPortfolioScenario({
    holdings: [
      { symbol: 'AAPL', weight: 0.6, asset_class: 'equity' },
      { symbol: 'BOND', weight: 0.4, asset_class: 'fixed income' },
    ],
    scenario: PORTFOLIO_SCENARIO_PRESETS.find((item) => item.id === 'global_equity_correction'),
  });

  assert.equal(result.status, 'available');
  assert.ok(Math.abs(result.modeledImpact - (-0.082)) < 1e-12);
  assert.equal(result.affectedWeight, 1);
  assert.equal(result.contributors.length, 2);
  assert.equal(result.contributors[0].symbol, 'AAPL');
});

test('missing weights are unavailable, not zero', () => {
  const result = runPortfolioScenario({
    holdings: [{ symbol: 'AAPL', asset_class: 'equity' }],
  });

  assert.equal(result.status, 'unavailable');
  assert.equal(result.modeledImpact, null);
  assert.deepEqual(result.missing, ['weights']);
});

test('a valid unaffected portfolio produces an actual zero impact', () => {
  const result = runPortfolioScenario({
    holdings: [{ symbol: 'JPM', weight: 1, sector: 'Financials' }],
    scenario: PORTFOLIO_SCENARIO_PRESETS.find((item) => item.id === 'technology_compression'),
  });

  assert.equal(result.status, 'available');
  assert.equal(result.modeledImpact, 0);
  assert.equal(result.affectedWeight, 0);
  assert.equal(result.contributors.length, 0);
});

test('missing required classifications make the result partial', () => {
  const result = runPortfolioScenario({
    holdings: [{ symbol: 'UNKNOWN', weight: 1 }],
    scenario: PORTFOLIO_SCENARIO_PRESETS.find((item) => item.id === 'technology_compression'),
  });

  assert.equal(result.status, 'partial');
  assert.equal(result.modeledImpact, 0);
  assert.deepEqual(result.missing, ['classifications']);
});

test('client report preserves data-quality counts', () => {
  const report = buildPortfolioScenarioReport({
    portfolioName: 'Test portfolio',
    holdings: [{ symbol: 'AAPL', weight: 1, asset_class: 'equity', sector: 'Technology', currency: 'USD' }],
  });

  assert.equal(report.results.length, PORTFOLIO_SCENARIO_PRESETS.length);
  assert.equal(
    report.dataQuality.available + report.dataQuality.partial + report.dataQuality.unavailable,
    report.results.length,
  );
  assert.match(report.methodology, /not forecasts/i);
});
