import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import {
  buildAskDeskFallback,
  mergePublishedResearch,
  publishedResearchPack,
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

  it('replaces a cut-off CMS excerpt with complete article sentences', () => {
    const pack = publishedResearchPack('What is the tariff view?', {
      id: 'airtel-1',
      title: 'Airtel Fires the First Shot',
      slug: 'airtel-first-shot',
      excerpt: 'India may be entering a tariff cycle, effectively raising the cost for a',
      content: '<p>Airtel has raised prepaid pricing, signalling a new phase of tariff repair.</p><p>The change may support revenue growth, but customer churn and competitive responses remain important risks.</p>',
    });
    assert.doesNotMatch(pack.executive_summary, /cost for a$/);
    assert.match(pack.executive_summary, /tariff repair\./);
    assert.ok(pack.key_risks.some((risk) => /churn/i.test(risk)));
    assert.ok(pack.key_catalysts.some((catalyst) => /revenue growth/i.test(catalyst)));
    assert.notEqual(pack.answer.bottom_line, pack.answer.summary);
  });

  it('adds an industry-aware causal and financial reasoning pack', () => {
    const pack = publishedResearchPack('Why does Airtel matter in the next tariff cycle?', {
      id: 'airtel-2',
      title: 'Airtel starts the next telecom tariff cycle',
      excerpt: 'Airtel has raised prepaid pricing, signalling a new phase of tariff repair.',
      content: 'The change may support revenue growth, but customer churn and competitive responses remain important risks.',
    });
    assert.equal(pack.research_plan.industry, 'telecom');
    assert.equal(pack.research_plan.event_type, 'pricing');
    assert.equal(pack.research_plan.question_type, 'causal_analysis');
    assert.deepEqual(pack.financial_transmission.slice(0, 3), [
      'Tariff or plan-price change',
      'Realised ARPU',
      'Revenue per subscriber',
    ]);
    assert.ok(pack.affected_metrics.includes('churn'));
    assert.match(pack.reasoning_framework.what_could_go_wrong, /churn/i);
    assert.equal(pack.evidence_boundary.quantified_impact_available, false);
  });

  it('maps a defence order through execution and cash conversion', () => {
    const pack = publishedResearchPack("What is AGI's view on Zen Technologies' order?", {
      id: 'zen-2',
      title: 'Zen Technologies wins a defence order',
      excerpt: 'The contract adds to the company order pipeline while execution remains the key test.',
    });
    assert.equal(pack.research_plan.industry, 'defence');
    assert.equal(pack.research_plan.event_type, 'order_win');
    assert.ok(pack.financial_transmission.includes('Project margin and working capital'));
    assert.ok(pack.affected_metrics.includes('operating cash flow'));
  });
});
