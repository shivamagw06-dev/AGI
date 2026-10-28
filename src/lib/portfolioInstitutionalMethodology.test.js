import assert from 'node:assert/strict';
import test from 'node:test';
import {
  assessMetricAvailability,
  buildLookThroughExposure,
  buildMetricEnvelope,
  buildResearchImpactRecords,
  resolveBenchmarkPolicy,
} from './portfolioInstitutionalMethodology.js';

test('benchmark is unavailable until the user explicitly selects it', () => {
  const benchmark = resolveBenchmarkPolicy({
    benchmark_components: [{ symbol: 'NIFTY', weight: 0.6 }, { symbol: '^GSPC', weight: 0.4 }],
  });
  assert.equal(benchmark.available, false);
  assert.equal(benchmark.status, 'unassigned');
  assert.deepEqual(benchmark.components, []);
});

test('explicit benchmark must have valid weights summing to 100 percent', () => {
  const valid = resolveBenchmarkPolicy({
    benchmark_policy: { mode: 'explicit' },
    benchmark_components: [{ symbol: 'NIFTY', weight: 60 }, { symbol: '^GSPC', weight: 40 }],
  });
  assert.equal(valid.available, true);
  assert.deepEqual(valid.components, [{ symbol: 'NIFTY', weight: 0.6 }, { symbol: '^GSPC', weight: 0.4 }]);
  assert.equal(resolveBenchmarkPolicy({
    benchmark_policy: { mode: 'explicit' },
    benchmark_components: [{ symbol: 'NIFTY', weight: 0.7 }],
  }).status, 'invalid');
});

test('insufficient observations never become a zero metric', () => {
  const eligibility = assessMetricAvailability('var95', { returnObservations: 20 });
  assert.equal(eligibility.available, false);
  const metric = buildMetricEnvelope('var95', 0, { returnObservations: 20 });
  assert.equal(metric.available, false);
  assert.equal(metric.value, null);
  assert.match(metric.reason, /20\/60/);
});

test('missing numeric values remain unavailable while a real zero remains zero', () => {
  const counts = { returnObservations: 60 };
  for (const value of [null, undefined, '', '   ', 'not-a-number', false]) {
    const metric = buildMetricEnvelope('volatility', value, counts);
    assert.equal(metric.available, false);
    assert.equal(metric.value, null);
    assert.equal(metric.dataQuality.validNumericValue, false);
  }
  const zero = buildMetricEnvelope('volatility', 0, counts);
  assert.equal(zero.available, true);
  assert.equal(zero.value, 0);
});

test('missing benchmark observations fail closed', () => {
  const metric = buildMetricEnvelope('beta', 1.1, { alignedBenchmarkObservations: 0 });
  assert.equal(metric.available, false);
  assert.equal(metric.value, null);
  assert.match(metric.reason, /0\/60/);
});

test('look-through replaces a fund wrapper and aggregates overlapping exposure once', () => {
  const result = buildLookThroughExposure({
    asOf: '2026-08-27',
    holdings: [
      { id: 'direct', symbol: 'AAPL', asset_type: 'us_stock', market_value: 100 },
      { id: 'fund', instrument_id: 'fund-1', symbol: 'TECHETF', asset_type: 'etf', market_value: 100 },
    ],
    fundConstituents: [
      { fund_instrument_id: 'fund-1', constituent_symbol: 'AAPL', weight_pct: 50, effective_date: '2026-08-26' },
      { fund_instrument_id: 'fund-1', constituent_symbol: 'MSFT', weight_pct: 50, effective_date: '2026-08-26' },
    ],
  });
  assert.equal(result.totalValue, 200);
  assert.equal(result.coveragePct, 100);
  assert.equal(result.exposures.find((row) => row.symbol === 'AAPL').marketValue, 150);
  assert.equal(result.exposures.find((row) => row.symbol === 'MSFT').marketValue, 50);
  assert.equal(result.exposures.some((row) => row.symbol === 'TECHETF'), false);
});

test('missing fund constituents are disclosed rather than fabricated', () => {
  const result = buildLookThroughExposure({
    holdings: [{ id: 'fund', symbol: 'UNKNOWNETF', asset_type: 'etf', market_value: 100 }],
  });
  assert.equal(result.coveragePct, 0);
  assert.equal(result.unresolved.length, 1);
  assert.match(result.unresolved[0].reason, /unavailable/i);
});

test('missing prices and FX rates reduce valuation coverage instead of becoming zero', () => {
  const result = buildLookThroughExposure({
    holdings: [
      { id: 'missing-price', symbol: 'AAPL', asset_type: 'us_stock', currency: 'USD', quantity: 2, fx_rate_to_inr: 83 },
      { id: 'missing-fx', symbol: 'MSFT', asset_type: 'us_stock', currency: 'USD', quantity: 1, current_price: 400 },
      { id: 'valid-zero', symbol: 'CASH', asset_type: 'cash', currency: 'INR', quantity: 0, current_price: 1 },
    ],
  });
  assert.equal(result.availability, 'partial');
  assert.equal(result.dataQuality.valuedHoldings, 1);
  assert.equal(result.dataQuality.missingValueCount, 2);
  assert.equal(result.unresolved.filter((row) => /price or FX/.test(row.reason)).length, 2);
});

test('partial fund weights disclose unresolved exposure', () => {
  const result = buildLookThroughExposure({
    asOf: '2026-08-27',
    holdings: [{ id: 'fund', instrument_id: 'fund-1', symbol: 'PARTIAL', asset_type: 'etf', market_value: 100 }],
    fundConstituents: [
      { fund_instrument_id: 'fund-1', constituent_symbol: 'AAPL', weight_pct: 60, effective_date: '2026-08-26' },
      { fund_instrument_id: 'fund-1', constituent_symbol: 'MSFT', weight_pct: null, effective_date: '2026-08-26' },
    ],
  });
  assert.equal(result.coveragePct, 60);
  assert.equal(result.availability, 'partial');
  assert.equal(result.unresolved[0].marketValue, 40);
});

test('research impact preserves evidence and does not invent direction', () => {
  const records = buildResearchImpactRecords({
    portfolioId: 'p1',
    userId: 'u1',
    generatedAt: '2026-08-27T09:00:00Z',
    holdings: [{ id: 'h1', symbol: 'AAPL' }],
    events: [{ eventKey: 'news-1', eventType: 'news', symbol: 'AAPL', title: 'Filed an update', source: 'Primary filing' }],
  });
  assert.equal(records.length, 1);
  assert.equal(records[0].direction, null);
  assert.equal(records[0].status, 'evidence_only');
  assert.equal(records[0].evidence.source, 'Primary filing');
  assert.equal(records[0].provenance.matchedBy, 'symbol');
});
