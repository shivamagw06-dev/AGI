import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { buildAskDeskFallback, rankPublishedResearch } from '../services/askDeskFallback.js';

describe('askDeskFallback', () => {
  it('does not pretend market context is a research answer', async () => {
    const pack = await buildAskDeskFallback("What is Reliance's business model?");
    assert.equal(pack.mode, 'node_desk_fallback');
    assert.equal(pack.degraded, true);
    assert.equal(pack.retryable, true);
    assert.match(pack.executive_summary, /could not complete a research answer/i);
    assert.doesNotMatch(pack.executive_summary, /^On “/);
    assert.equal(pack.ask_orchestration?.fallback, true);
    assert.equal(pack.entities?.ticker, null);
  });

  it('ranks a matching published company-event report ahead of unrelated research', () => {
    const ranked = rankPublishedResearch("What is AGI's view on Zen Technologies' ₹295 crore defence order?", [
      { id: 'other', title: 'India inflation update', excerpt: 'CPI and rates' },
      { id: 'zen', title: 'Zen Technologies wins a ₹295 crore defence order', excerpt: 'AGI assesses the earnings impact.' },
    ]);
    assert.equal(ranked[0]?.article?.id, 'zen');
    assert.ok(ranked[0]?.score >= 8);
  });
});
