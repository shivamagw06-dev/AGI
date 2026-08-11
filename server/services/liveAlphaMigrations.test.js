import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

test('forward repair migration permits every emitted Live Alpha classification', () => {
  const sql = fs.readFileSync(path.join(root, 'supabase/migrations/20260811101500_repair_live_alpha_strategy_classifications.sql'), 'utf8');
  const required = [
    'positive_research_candidate', 'negative_research_candidate', 'neutral', 'filtered',
    'abnormal_accumulation_candidate', 'abnormal_distribution_candidate',
    'upside_opening_breakout_candidate', 'downside_opening_breakout_candidate', 'invalid_opening_range',
    'negative_shock_rebound_candidate', 'positive_shock_pullback_candidate',
    'market_stress_filtered', 'event_volume_filtered', 'trend_filtered',
    'long_buildup_candidate', 'short_buildup_candidate', 'short_covering_candidate', 'long_unwinding_candidate',
  ];
  for (const classification of required) assert.match(sql, new RegExp(`'${classification}'`));
  assert.doesNotMatch(sql, /\)\);\s*\);/);
});
