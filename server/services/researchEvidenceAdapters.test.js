import assert from 'node:assert/strict';
import test from 'node:test';
import { mergeResearchEvidence, normalizeCatalystEvidence, normalizeHedgeFundEvidence, normalizeValuationEvidence } from './researchEvidenceAdapters.js';

test('normalizes fundamental and value scanners independently', () => {
  const rows = normalizeHedgeFundEvidence({ as_of: '2026-08-09', cards: [
    { id: 'quality', results: [{ ticker: 'SBIN', confidence: 86 }] },
    { id: 'growth', results: [{ ticker: 'SBIN', confidence: 74 }] },
    { id: 'value', results: [{ ticker: 'SBIN', confidence: 80 }] },
    { id: 'momentum', results: [{ ticker: 'SBIN', confidence: 99 }] },
  ] });
  assert.equal(rows[0].fundamental_score, 80);
  assert.equal(rows[0].valuation_score, 80);
  assert.equal(rows[0].provenance.fundamental.length, 2);
});

test('converts valuation richness into attractiveness', () => {
  const row = normalizeValuationEvidence('TCS', { as_of: '2026-08-09', derived: { relative_valuation: { score: 82 } } });
  assert.equal(row.valuation_score, 18);
});

test('scores catalyst relevance by importance and proximity, not polarity', () => {
  const row = normalizeCatalystEvidence('BEL', { catalysts: [{ importance: 'High', date: '2026-08-09', polarity: 'Negative' }] }, { now: new Date('2026-08-09T00:00:00Z') });
  assert.equal(row.catalyst_score, 90);
  assert.equal(row.catalyst_count, 1);
});

test('merges evidence while retaining provenance and timestamps', () => {
  const [row] = mergeResearchEvidence([{ symbol: 'SBIN', fundamental_score: 80, observed_at: { fundamental: 'a' }, provenance: { fundamental: ['x'] } }], [{ symbol: 'SBIN', valuation_score: 70, observed_at: { valuation: 'b' }, provenance: { valuation: ['y'] } }]);
  assert.equal(row.fundamental_score, 80);
  assert.equal(row.valuation_score, 70);
  assert.deepEqual(row.observed_at, { fundamental: 'a', valuation: 'b' });
});
