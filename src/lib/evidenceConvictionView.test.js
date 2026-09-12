import assert from 'node:assert/strict';
import test from 'node:test';
import { convictionTone, filterConvictionRows, readableConvictionLabel } from './evidenceConvictionView.js';

const rows = [
  { symbol: 'A', conviction_label: 'HIGH_CONVICTION', eligible_for_research_shortlist: true },
  { symbol: 'B', conviction_label: 'WATCH', eligible_for_research_shortlist: false },
  { symbol: 'C', conviction_label: 'INCOMPLETE', eligible_for_research_shortlist: false },
];

test('keeps the default shortlist focused on eligible research names', () => {
  assert.deepEqual(filterConvictionRows(rows, 'shortlist').map((row) => row.symbol), ['A']);
  assert.deepEqual(filterConvictionRows(rows, 'incomplete').map((row) => row.symbol), ['C']);
});

test('maps labels into restrained visual tones and readable text', () => {
  assert.equal(convictionTone('CONFIRMED'), 'positive');
  assert.equal(convictionTone('CONTRADICTED'), 'negative');
  assert.equal(readableConvictionLabel('HIGH_CONVICTION'), 'high conviction');
});
