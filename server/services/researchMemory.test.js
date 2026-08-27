import assert from 'node:assert/strict';
import test from 'node:test';
import { assessPrediction, createResearchMemoryState, detectThesisChange } from './researchMemory.js';

test('creates an append-only state from an immutable confluence event', () => {
  const state = createResearchMemoryState({ id: 'e1', symbol: 'ICICIBANK', captured_at: '2026-08-09T06:00:00Z', classification: 'CONFIRMED', fundamental_score: 88, valuation_score: 76, eod_confirmation: 82, live_confirmation: 91, catalyst_score: 73, leadership: 91, research_priority: 84, evidence_snapshot: {} });
  assert.equal(state.state_key, 'ICICIBANK:2026-08-09T06:00:00Z');
  assert.equal(state.key_bull_evidence.some((row) => row.label === 'Leadership'), true);
  assert.equal(state.research_only, true);
});

test('detects strengthening, valuation improvement and market confirmation separately', () => {
  const prior = { symbol: 'ICICIBANK', fundamental_score: 88, valuation_score: 62, eod_confirmation: 70, live_confirmation: 58, catalyst_score: 60, research_priority: 70, confluence_class: 'CONFIRMED', catalysts: [], risks: [] };
  const current = { ...prior, valuation_score: 76, eod_confirmation: 82, live_confirmation: 91, research_priority: 89, confluence_class: 'HIGH_CONFLUENCE' };
  const change = detectThesisChange(current, prior);
  assert.deepEqual(change.change_types, ['THESIS_STRENGTHENING','VALUATION_IMPROVING','MARKET_CONFIRMING']);
  assert.equal(change.material, true);
  assert.equal(change.field_changes.confluence_class.to, 'HIGH_CONFLUENCE');
});

test('does not manufacture a change from small score noise', () => {
  const prior = { symbol: 'TCS', fundamental_score: 80, valuation_score: 60, eod_confirmation: 55, live_confirmation: 52, research_priority: 70, confluence_class: 'WATCH', catalysts: [], risks: [] };
  assert.deepEqual(detectThesisChange({ ...prior, live_confirmation: 54 }, prior).change_types, ['NO_MATERIAL_CHANGE']);
});

test('attaches prediction accountability from completed sector alpha', () => {
  assert.deepEqual(assessPrediction({ status: 'completed', sector_adjusted_alpha_pct: -2.1 }), { result: 'FAILED', sector_adjusted_alpha_pct: -2.1 });
});
