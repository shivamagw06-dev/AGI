import assert from 'node:assert/strict';
import test from 'node:test';
import { evaluateCrossSectionalMomentum, evaluateDerivativesPositioning, evaluateIntradayMeanReversion, evaluateOpeningRangeExpansion, evaluateVolumeLiquidityAnomaly } from './liveAlphaEngine.js';

function universe(size = 20) {
  return Array.from({ length: size }, (_, index) => ({
    symbol: `STOCK${index + 1}`,
    sector: index < 10 ? 'BANKS' : 'IT',
    instrumentKey: `NSE_EQ|TEST${index + 1}`,
    return15m: index * 0.12 - 1,
    return60m: index * 0.25 - 2,
    benchmarkReturn15m: 0.2,
    benchmarkReturn60m: 0.4,
    sectorReturn15m: index < 10 ? 0.1 : -0.1,
    sectorReturn60m: index < 10 ? 0.2 : -0.2,
    cumulativeVolume: 100_000 + index * 12_000,
    expectedCumulativeVolume: 100_000,
    spreadBps: 8,
  }));
}

test('ranks residual momentum and selects both research tails', () => {
  const result = evaluateCrossSectionalMomentum(universe(), { asOf: '2026-08-09T06:00:00Z' });
  assert.equal(result.research_only, true);
  assert.equal(result.execution_enabled, false);
  assert.equal(result.tail_size, 2);
  assert.equal(result.signals[0].symbol, 'STOCK20');
  assert.equal(result.signals[0].classification, 'positive_research_candidate');
  assert.equal(result.signals[0].signal_quality.empirical, false);
  assert.equal(result.signals[0].empirical_confidence.status, 'unvalidated');
  assert.equal(result.signals.at(-1).classification, 'negative_research_candidate');
  assert.equal('order' in result.signals[0], false);
});

test('filters illiquid names even when their score is extreme', () => {
  const rows = universe();
  rows.at(-1).spreadBps = 90;
  const result = evaluateCrossSectionalMomentum(rows);
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK20').classification, 'filtered');
});

test('rejects undersized universes, duplicate symbols and invalid weights', () => {
  assert.throws(() => evaluateCrossSectionalMomentum(universe(5)), /at least 10/);
  const duplicate = universe();
  duplicate[1].symbol = duplicate[0].symbol;
  assert.throws(() => evaluateCrossSectionalMomentum(duplicate), /unique/);
  assert.throws(() => evaluateCrossSectionalMomentum(universe(), { weights: { residual15m: 1 } }), /sum to 1/);
});

test('uses stock-minus-sector residual without double-counting the market', () => {
  const rows = universe();
  rows[10] = {
    ...rows[10], symbol: 'RAWLEADER', return15m: 3, return60m: 5,
    benchmarkReturn15m: 1, benchmarkReturn60m: 2,
    sectorReturn15m: 2, sectorReturn60m: 3,
  };
  const result = evaluateCrossSectionalMomentum(rows);
  const leader = result.signals.find((row) => row.symbol === 'RAWLEADER');
  assert.equal(leader.residual_15m, 1);
  assert.equal(leader.residual_60m, 2);
  assert.equal(leader.sector_strength, 1);
});

test('ranks abnormal volume and labels accumulation versus distribution', () => {
  const rows = universe();
  rows[19].cumulativeVolume = 500_000;
  rows[18].cumulativeVolume = 450_000;
  rows[18].return15m = -4;
  rows[18].return60m = -5;
  const result = evaluateVolumeLiquidityAnomaly(rows, { asOf: '2026-08-09T06:00:00Z' });
  assert.equal(result.engine, 'volume_liquidity_anomaly_v1');
  assert.equal(result.research_only, true);
  assert.equal(result.execution_enabled, false);
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK20').classification, 'abnormal_accumulation_candidate');
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK19').classification, 'abnormal_distribution_candidate');
  assert.equal('order' in result.signals[0], false);
});

test('volume anomaly rejects weak participation and filters wide spreads', () => {
  const rows = universe();
  for (const row of rows) row.cumulativeVolume = 110_000;
  rows[19].cumulativeVolume = 500_000;
  rows[19].spreadBps = 80;
  const result = evaluateVolumeLiquidityAnomaly(rows);
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK20').classification, 'filtered');
  assert.equal(result.signals.some((row) => row.classification.includes('candidate')), false);
});

test('opening range requires buffered, volume-confirmed breakouts', () => {
  const rows = universe().map((row) => ({ ...row, currentPrice: 100, openingHigh: 100, openingLow: 99 }));
  rows[19].currentPrice = 102;
  rows[19].cumulativeVolume = 300_000;
  rows[18].currentPrice = 97;
  rows[18].cumulativeVolume = 300_000;
  const result = evaluateOpeningRangeExpansion(rows, { asOf: '2026-08-09T06:00:00Z' });
  assert.equal(result.engine, 'opening_range_expansion_v1');
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK20').classification, 'upside_opening_breakout_candidate');
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK19').classification, 'downside_opening_breakout_candidate');
  assert.equal(result.execution_enabled, false);
  assert.equal('order' in result.signals[0], false);
});

test('opening range filters weak volume, wide spreads and invalid ranges', () => {
  const rows = universe().map((row) => ({ ...row, currentPrice: 102, openingHigh: 100, openingLow: 99, cumulativeVolume: 105_000 }));
  rows[0].spreadBps = 90;
  rows[1].openingLow = 99.95;
  const result = evaluateOpeningRangeExpansion(rows);
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK1').classification, 'filtered');
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK2').classification, 'invalid_opening_range');
  assert.equal(result.signals.some((row) => row.classification.includes('candidate')), false);
});

test('mean reversion identifies isolated positive and negative residual shocks', () => {
  const rows = universe().map((row) => ({ ...row, cumulativeVolume: 100_000, return15m: row.sectorReturn15m, return60m: row.sectorReturn60m }));
  rows[0].return15m = rows[0].sectorReturn15m - 4;
  rows[1].return15m = rows[1].sectorReturn15m + 4;
  const result = evaluateIntradayMeanReversion(rows, { asOf: '2026-08-09T06:00:00Z' });
  assert.equal(result.engine, 'intraday_mean_reversion_v1');
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK1').classification, 'negative_shock_rebound_candidate');
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK2').classification, 'positive_shock_pullback_candidate');
  assert.equal(result.execution_enabled, false);
  assert.equal('order' in result.signals[0], false);
});

test('mean reversion rejects market stress, event volume, trends and wide spreads', () => {
  const base = universe().map((row) => ({ ...row, cumulativeVolume: 100_000, return15m: row.sectorReturn15m, return60m: row.sectorReturn60m }));
  base[0].return15m -= 4; base[0].spreadBps = 90;
  base[1].return15m += 4; base[1].benchmarkReturn15m = 1;
  base[2].return15m -= 4; base[2].cumulativeVolume = 300_000;
  base[3].return15m += 2; base[3].return60m = base[3].sectorReturn60m + 5;
  const result = evaluateIntradayMeanReversion(base);
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK1').classification, 'filtered');
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK2').classification, 'market_stress_filtered');
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK3').classification, 'event_volume_filtered');
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK4').classification, 'trend_filtered');
});

test('derivatives positioning classifies all four price and OI states', () => {
  const rows = Array.from({ length: 12 }, (_, index) => ({ symbol: `FUT${index}`, sector: 'BANK', instrumentKey: `NSE_FO|${index}`, priceReturn15m: 0.1, oiChange15m: 0.2, openInterest: 100_000, spreadBps: 8 }));
  Object.assign(rows[0], { priceReturn15m: 2, oiChange15m: 5 });
  Object.assign(rows[1], { priceReturn15m: -2, oiChange15m: 5 });
  Object.assign(rows[2], { priceReturn15m: 2, oiChange15m: -5 });
  Object.assign(rows[3], { priceReturn15m: -2, oiChange15m: -5 });
  const result = evaluateDerivativesPositioning(rows, { asOf: '2026-08-09T06:00:00Z' });
  assert.equal(result.signals.find((row) => row.symbol === 'FUT0').classification, 'long_buildup_candidate');
  assert.equal(result.signals.find((row) => row.symbol === 'FUT1').classification, 'short_buildup_candidate');
  assert.equal(result.signals.find((row) => row.symbol === 'FUT2').classification, 'short_covering_candidate');
  assert.equal(result.signals.find((row) => row.symbol === 'FUT3').classification, 'long_unwinding_candidate');
  assert.equal(result.execution_enabled, false);
  assert.equal('order' in result.signals[0], false);
});

test('derivatives positioning rejects weak changes, wide spreads and incomplete coverage', () => {
  const rows = Array.from({ length: 10 }, (_, index) => ({ symbol: `FUT${index}`, sector: 'BANK', instrumentKey: `NSE_FO|${index}`, priceReturn15m: 0.1, oiChange15m: 0.2, openInterest: 100_000, spreadBps: 8 }));
  rows[0].priceReturn15m = 2; rows[0].oiChange15m = 5; rows[0].spreadBps = 90;
  const result = evaluateDerivativesPositioning(rows);
  assert.equal(result.signals.find((row) => row.symbol === 'FUT0').classification, 'filtered');
  assert.equal(result.signals.find((row) => row.symbol === 'FUT1').classification, 'neutral');
  assert.throws(() => evaluateDerivativesPositioning(rows.slice(0, 5)), /at least 10/);
});

test('a proxied sector reports no reading rather than a measured zero', () => {
  // When a sector index has no history the pipeline substitutes the benchmark
  // for the sector, so sectorReturn60m - benchmarkReturn60m is 0 by
  // construction. 1,586 of 2,198 stored signals carried that structural zero.
  const rows = Array.from({ length: 12 }, (_, i) => ({
    symbol: `S${i}`, sector: 'IT', instrumentKey: `k${i}`,
    return15m: 0.01 * i, return60m: 0.02 * i,
    benchmarkReturn15m: 0.005, benchmarkReturn60m: 0.01,
    sectorReturn15m: 0.005, sectorReturn60m: 0.01, // proxy: equals benchmark
    sectorProxyUsed: true,
    cumulativeVolume: 1000 + i, expectedCumulativeVolume: 1000,
    spreadBps: 5, minimumLiquidity: true,
  }));
  const out = evaluateCrossSectionalMomentum(rows, { asOf: '2026-08-20T04:00:00Z' });
  for (const signal of out.signals) {
    assert.equal(signal.sector_strength, null, 'proxied sector must not report a value');
    assert.equal(signal.factors.sector_strength_z, null);
    assert.ok(Number.isFinite(signal.alpha_z), 'alpha must still be computable');
  }
});

test('a measured sector still contributes to the composite', () => {
  const rows = Array.from({ length: 12 }, (_, i) => ({
    symbol: `S${i}`, sector: 'IT', instrumentKey: `k${i}`,
    return15m: 0.01 * i, return60m: 0.02 * i,
    benchmarkReturn15m: 0.005, benchmarkReturn60m: 0.01,
    sectorReturn15m: 0.006 + i * 0.001, sectorReturn60m: 0.012 + i * 0.002,
    sectorProxyUsed: false,
    cumulativeVolume: 1000 + i, expectedCumulativeVolume: 1000,
    spreadBps: 5, minimumLiquidity: true,
  }));
  const out = evaluateCrossSectionalMomentum(rows, { asOf: '2026-08-20T04:00:00Z' });
  assert.ok(out.signals.every((s) => typeof s.sector_strength === 'number'));
  assert.ok(out.signals.some((s) => s.factors.sector_strength_z !== 0));
});

test('an unmeasurable spread is flagged rather than passed off as liquid', () => {
  const rows = Array.from({ length: 12 }, (_, i) => ({
    symbol: `S${i}`, sector: 'IT', instrumentKey: `k${i}`,
    return15m: 0.01 * i, return60m: 0.02 * i,
    benchmarkReturn15m: 0.005, benchmarkReturn60m: 0.01,
    sectorReturn15m: 0.005, sectorReturn60m: 0.01, sectorProxyUsed: true,
    cumulativeVolume: 1000 + i, expectedCumulativeVolume: 1000,
    spreadBps: null, minimumLiquidity: true,
  }));
  const out = evaluateCrossSectionalMomentum(rows, { asOf: '2026-08-20T04:00:00Z' });
  for (const signal of out.signals) {
    assert.equal(signal.liquidity_ok, true, 'permissive gate is unchanged');
    assert.equal(signal.liquidity_verified, false, 'but it must not claim verification');
    assert.equal(signal.liquidity_reason, 'spread_unknown');
  }
});
