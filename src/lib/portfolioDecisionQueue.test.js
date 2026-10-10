import test from 'node:test';
import assert from 'node:assert/strict';

import { buildPortfolioDecisionQueue } from './portfolioDecisionQueue.js';

test('ranks material negative holding evidence for review', () => {
  const queue = buildPortfolioDecisionQueue({
    holdings: [{ symbol: 'AAPL' }],
    researchImpacts: [{
      id: 'impact-1',
      symbol: 'AAPL',
      title: 'Margin warning',
      direction: 'negative',
      severity: 'high',
      confidence: 0.8,
      evidence: [{ title: 'Company filing', url: 'https://example.com/filing' }],
    }],
  });

  assert.equal(queue.status, 'available');
  assert.equal(queue.counts.review_now, 1);
  assert.equal(queue.items[0].priority, 'review_now');
  assert.equal(queue.items[0].portfolioMatch, true);
  assert.equal(queue.items[0].confidence, 0.8);
});

test('missing evidence is a research gap rather than a recommendation', () => {
  const queue = buildPortfolioDecisionQueue({
    holdings: [{ symbol: 'MSFT' }],
    researchImpacts: [{ symbol: 'MSFT', title: 'Unverified claim', severity: 'high' }],
  });

  assert.equal(queue.items[0].priority, 'research_gap');
  assert.equal(queue.items[0].availability, 'partial');
  assert.equal(queue.items[0].confidence, null);
  assert.equal(queue.items[0].direction, 'unavailable');
});

test('empty research remains unavailable and is not coerced into a clean result', () => {
  const queue = buildPortfolioDecisionQueue({ holdings: [{ symbol: 'AAPL' }] });

  assert.equal(queue.status, 'unavailable');
  assert.equal(queue.items.length, 0);
  assert.match(queue.message, /No portfolio-linked research/i);
});
