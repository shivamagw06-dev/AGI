import assert from 'node:assert/strict';
import test from 'node:test';
import { collectResearchEvidence } from './researchEvidenceCollector.js';

test('collects all three missing evidence layers with partial-source tolerance', async () => {
  const fetchImpl = async (url) => {
    if (url.includes('hedge-fund-lab')) return { ok: true, json: async () => ({ as_of: '2026-08-09', cards: [{ id: 'quality', results: [{ ticker: 'SBIN', confidence: 84 }] }] }) };
    if (url.includes('valuation-terminal')) return { ok: true, json: async () => ({ as_of: '2026-08-09', derived: { relative_valuation: { score: 25 } } }) };
    if (url.includes('forecast/catalysts')) return { ok: true, json: async () => ({ as_of: '2026-08-09', catalysts: [{ importance: 'High', date: '2026-08-10' }] }) };
    return { ok: false, status: 404 };
  };
  const result = await collectResearchEvidence({ workspace: { groww: { equities: [{ symbol: 'SBIN' }] }, signals: [] }, fetchImpl, now: new Date('2026-08-09T00:00:00Z') });
  assert.equal(result.evidence[0].fundamental_score, 84);
  assert.equal(result.evidence[0].valuation_score, 75);
  assert.ok(result.evidence[0].catalyst_score > 80);
  assert.equal(result.health.errors.length, 0);
});

test('treats a missing forecast as normal availability state, not a route error', async () => {
  const fetchImpl = async (url) => {
    if (url.includes('hedge-fund-lab')) return { ok: true, json: async () => ({ cards: [] }) };
    if (url.includes('valuation-terminal')) return { ok: true, json: async () => ({ valuation_attractiveness: 70 }) };
    return { ok: false, status: 404 };
  };
  const result = await collectResearchEvidence({ workspace: { groww: { equities: [{ symbol: 'SBIN' }] }, signals: [] }, fetchImpl });
  assert.equal(result.health.errors.length, 0);
  assert.equal(result.health.unavailable[0].reason, 'NO_ELIGIBLE_FORECAST_YET');
  assert.equal(result.evidence[0].provenance.catalyst.forecast_available, false);
});
