import assert from 'node:assert/strict';
import test from 'node:test';
import { buildConfluenceQueue, decayScore, evaluateResearchConfluence } from './researchConfluence.js';

const now = new Date('2026-08-09T10:00:00Z');

test('decays evidence toward neutral according to its horizon', () => {
  assert.equal(decayScore(90, '2026-08-09T10:00:00Z', now, 1).effective, 90);
  assert.equal(decayScore(90, '2026-08-09T09:00:00Z', now, 1).effective, 70);
});

test('keeps score decomposition and classifies complete agreement', () => {
  const item = evaluateResearchConfluence({ symbol: 'ICICIBANK', fundamental_score: 88, valuation_score: 76, groww_equity_score: 82, groww_sector_rotation_score: 80, upstox_leadership_score: 91, upstox_activity_score: 85, catalyst_score: 73 }, { now });
  assert.equal(item.confluence_class, 'HIGH_CONFLUENCE');
  assert.equal(item.scores.fundamental_score, 88);
  assert.equal(item.flags.incomplete_research_evidence, false);
  assert.ok(item.research_priority_score > 80);
});

test('prevents live momentum from becoming an investment thesis', () => {
  const item = evaluateResearchConfluence({ symbol: 'TACTICAL', fundamental_score: 39, valuation_score: 46, groww_equity_score: 81, upstox_breakout_score: 95, upstox_activity_score: 90 }, { now });
  assert.equal(item.confluence_class, 'TACTICAL_ONLY');
  assert.equal(item.research_only, true);
});

test('assembles market evidence without inventing fundamentals', () => {
  const workspace = { groww: { runs: [{ strategy: 'agi_equity_opportunity_v1', as_of: now.toISOString() }, { strategy: 'agi_sector_rotation_v1', as_of: now.toISOString() }], equities: [{ symbol: 'SBIN', score: 84 }], sectors: [{ sector: 'BANK', score: 88 }] }, signals: [{ symbol: 'SBIN', sector: 'BANK', engine: 'cross_sectional_momentum_v1', direction: 'positive', signal_quality_score: 90, factor_values: { residual_15m_z: 1.25 }, as_of: now.toISOString() }] };
  const queue = buildConfluenceQueue({ workspace, now });
  assert.equal(queue.items[0].symbol, 'SBIN');
  assert.equal(queue.items[0].scores.fundamental_score, null);
  assert.equal(queue.items[0].flags.incomplete_research_evidence, true);
  assert.equal(queue.items[0].scores.live_confirmation_score, 90);
  assert.equal(queue.items[0].market_features.leadership.residual_15m_z, 1.25);
});
