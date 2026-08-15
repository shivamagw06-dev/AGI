import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import {
  buildAskDeskFallback,
  mergePublishedResearch,
  rankPublishedResearch,
} from '../services/askDeskFallback.js';

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

  it('makes a matched article primary evidence without discarding engine context', () => {
    const merged = mergePublishedResearch(
      {
        executive_summary: 'The deeper engine sees execution risk.',
        answer: { executive_summary: 'The deeper engine sees execution risk.', why: ['Order conversion matters.'] },
        evidence: [{ id: 'filing-1', title: 'Exchange filing' }],
        ask_orchestration: { completed: true, fallback: false },
      },
      'What is the view on the order?',
      {
        id: 'article-1',
        title: 'Company wins a major order',
        slug: 'company-major-order',
        excerpt: 'The order improves revenue visibility, while execution and cash conversion remain the key tests.',
        published_at: '2026-08-15T00:00:00Z',
      }
    );
    assert.equal(merged.evidence_grade, 'published_agi_research');
    assert.equal(merged.evidence[0].id, 'article-1');
    assert.equal(merged.evidence[1].id, 'filing-1');
    assert.match(merged.executive_summary, /AGI's published view/i);
    assert.match(merged.executive_summary, /deeper engine sees execution risk/i);
    assert.equal(merged.ask_orchestration.published_research.matched, true);
  });
});
