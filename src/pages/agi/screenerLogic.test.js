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

test('all-NSE items without research are not treated as zero-score research', () => {
  const stock = { symbol: 'XYZ', name: 'XYZ Industries', hasResearch: false, lastPrice: 120, changePercent: 2.5, volume: 1500000 };
  assert.equal(matchScreenerItem(stock, {}), true);
  assert.equal(matchScreenerItem(stock, { search: 'industries', minChange: 2, minVolume: 1000000 }), true);
  assert.equal(matchScreenerItem(stock, { maxScore: 35 }), false);
  assert.equal(matchScreenerItem(stock, { minRisks: 0 }), false);
  assert.equal(matchScreenerItem(stock, { coverage: 'research' }), false);
  assert.equal(matchScreenerItem(stock, { maxChange: -2 }), false);
});
