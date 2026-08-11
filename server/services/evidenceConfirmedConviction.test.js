import assert from 'node:assert/strict';
import test from 'node:test';
import { buildEvidenceConfirmedConvictionRanking, evaluateEvidenceConfirmedConviction } from './evidenceConfirmedConviction.js';

function item(symbol, overrides = {}) {
  return {
    symbol,
    sector: 'BANK',
    confluence_class: 'HIGH_CONFLUENCE',
    research_priority_score: 82,
    bullish_signal_count: 2,
    bearish_signal_count: 0,
    contradiction_count: 0,
    scores: { fundamental_score: 80, valuation_score: 70, eod_confirmation_score: 78, live_confirmation_score: 84, catalyst_relevance_score: 65 },
    flags: { incomplete_research_evidence: false },
    anchors: { market_regime: 'risk_on' },
    ...overrides,
  };
}

test('promotes only complete, agreeing evidence to high conviction', () => {
  const result = evaluateEvidenceConfirmedConviction(item('HDFCBANK'));
  assert.equal(result.conviction_label, 'HIGH_CONVICTION');
  assert.equal(result.evidence_coverage, 1);
  assert.equal(result.eligible_for_research_shortlist, true);
  assert.match(result.thesis, /Groww/);
  assert.match(result.thesis, /Upstox/);
});

test('caps an incomplete thesis below confirmed status', () => {
  const result = evaluateEvidenceConfirmedConviction(item('SBIN', {
    scores: { fundamental_score: null, valuation_score: null, eod_confirmation_score: 90, live_confirmation_score: 92, catalyst_relevance_score: null },
    flags: { incomplete_research_evidence: true },
    confluence_class: 'TACTICAL_ONLY',
  }));
  assert.equal(result.conviction_label, 'TACTICAL_ONLY');
  assert.equal(result.evidence_coverage, 0.4);
  assert.ok(result.conviction_score <= 59);
  assert.equal(result.eligible_for_research_shortlist, false);
});

test('ranks a complete Nifty 200 cross-section deterministically', () => {
  const items = Array.from({ length: 200 }, (_, index) => item(`S${String(index).padStart(3, '0')}`, { research_priority_score: 100 - index / 3 }));
  const ranking = buildEvidenceConfirmedConvictionRanking({ generated_at: '2026-08-11T09:00:00Z', items });
  assert.equal(ranking.universe, 'nifty200');
  assert.equal(ranking.universe_size, 200);
  assert.equal(ranking.rows.length, 200);
  assert.deepEqual(ranking.rows.map((row) => row.rank), Array.from({ length: 200 }, (_, index) => index + 1));
});
