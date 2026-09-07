import test from 'node:test';
import assert from 'node:assert/strict';
import { canonicalSymbol, diagnosePipelineBottlenecks, settlementWindow, validateConfluenceCandidate, validateSettlementSnapshots } from './researchDataQuality.js';

test('requires canonical identity, instrument keys, sector and fresh positive anchors', () => {
  const now = new Date('2026-08-10T04:00:00Z');
  const item = { symbol: 'RELIANCE', sector: 'Energy', anchors: { captured_at: '2026-08-10T03:55:00Z', price_at_signal: 1400, benchmark_at_signal: 25000, sector_index_at_signal: 12000 } };
  const member = { symbol: 'RELIANCE', instrumentKey: 'NSE_EQ|INE002A01018', sectorInstrumentKey: 'NSE_INDEX|Nifty_Energy' };
  assert.equal(validateConfluenceCandidate(item, member, { benchmarkKey: 'NSE_INDEX|Nifty_50' }, { now }).valid, true);
  assert.equal(canonicalSymbol('../RELIANCE'), null);
  const invalid = validateConfluenceCandidate({ ...item, symbol: 'RIL', anchors: { ...item.anchors, captured_at: '2026-08-08T03:55:00Z' } }, member, { benchmarkKey: 'bad' }, { now });
  assert.equal(invalid.valid, false);
  assert.ok(invalid.reasons.includes('identity_symbol_mismatch'));
  assert.ok(invalid.reasons.includes('invalid_benchmark_instrument_key'));
  assert.ok(invalid.reasons.includes('stale_price_anchor'));
});

test('accepts canonical Upstox index keys containing spaces', () => {
  const now = new Date('2026-08-10T04:00:00Z');
  const item = { symbol: 'HDFCBANK', sector: 'FINANCIALS', anchors: { captured_at: '2026-08-10T03:55:00Z', price_at_signal: 1000, benchmark_at_signal: 25000, sector_index_at_signal: 28000 } };
  const member = { symbol: 'HDFCBANK', instrumentKey: 'NSE_EQ|INE040A01034', sectorInstrumentKey: 'NSE_INDEX|Nifty Financial Services' };
  const result = validateConfluenceCandidate(item, member, { benchmarkKey: 'NSE_INDEX|Nifty 50' }, { now });
  assert.equal(result.valid, true);
  assert.deepEqual(result.reasons, []);
});

test('bounds outcome observations and rejects asynchronous price triples', () => {
  const window = settlementWindow('2026-08-10T10:00:00Z', '5m');
  assert.equal(window.end, '2026-08-10T10:30:00.000Z');
  const rows = [{ ltp: 100, observed_at: '2026-08-10T10:00:00Z' }, { ltp: 200, observed_at: '2026-08-10T10:01:00Z' }, { ltp: 300, observed_at: '2026-08-10T10:02:00Z' }];
  assert.equal(validateSettlementSnapshots(rows).valid, true);
  assert.equal(validateSettlementSnapshots([rows[0], rows[1], { ...rows[2], observed_at: '2026-08-10T10:10:00Z' }]).reason, 'settlement_snapshot_skew');
});

test('reports the dominant blocking stage without treating a closed market as feed failure', () => {
  const diagnostics = diagnosePipelineBottlenecks({ scheduler: { last_capture: { candidates: 10, rejected: { incomplete_identity: 4 } } }, counts: { events: 5, memory: 3, feature_snapshots: 4, forecasts: 6 }, feeds: { market_feed: 'MARKET_CLOSED' }, marketClosed: true });
  assert.equal(diagnostics[0].stage, 'IDENTITY_AND_ANCHORS');
  assert.equal(diagnostics.some((row) => row.stage === 'COLLECTION'), false);
  assert.equal(diagnostics.some((row) => row.stage === 'FORECAST_GENERATION'), true);
});
