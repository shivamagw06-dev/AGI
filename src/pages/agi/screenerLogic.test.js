import test from 'node:test';
import assert from 'node:assert/strict';
import { matchScreenerItem, sortScreenerItems } from './screenerLogic.js';

const items = [
  { symbol: 'AAA', overallSentiment: 'Strong Bullish', agiResearchScore: 82, aiConfidencePercent: 76, riskFactors: ['a'] },
  { symbol: 'BBB', overallSentiment: 'Bearish', agiResearchScore: 29, aiConfidencePercent: 81, riskFactors: ['a', 'b', 'c'] },
  { symbol: 'CCC', overallSentiment: 'Neutral', agiResearchScore: 50, aiConfidencePercent: 60, riskFactors: [] },
];

test('preset filters use numeric score, confidence and recorded risks', () => {
  assert.deepEqual(items.filter((item) => matchScreenerItem(item, { sentiment: 'Bullish side', minScore: 70, minConfidence: 70 })).map((item) => item.symbol), ['AAA']);
  assert.deepEqual(items.filter((item) => matchScreenerItem(item, { maxScore: 35, minRisks: 3 })).map((item) => item.symbol), ['BBB']);
  assert.equal(matchScreenerItem(items[2], { minConfidence: 70 }), false);
});

test('sorting leaves the input order untouched', () => {
  assert.deepEqual(sortScreenerItems(items, 'score-asc').map((item) => item.symbol), ['BBB', 'CCC', 'AAA']);
  assert.deepEqual(items.map((item) => item.symbol), ['AAA', 'BBB', 'CCC']);
});
