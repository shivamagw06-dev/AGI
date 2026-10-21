import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { QUESTIONS, byKind, lineItemsNeeded } from './annualReportQuestions.js';

describe('the hundred questions', () => {
  test('there are a hundred, numbered in order', () => {
    assert.equal(QUESTIONS.length, 100);
    QUESTIONS.forEach((question, at) => assert.equal(question.n, at + 1));
  });

  test('every question says which machine answers it', () => {
    for (const question of QUESTIONS) {
      assert.ok(['stated', 'computed', 'judgment'].includes(question.kind), `${question.n}`);
      assert.ok(question.ask && question.ask.length > 10, `${question.n} has no question`);
    }
  });

  test('a computed question names the line items it needs', () => {
    // Without this the register would claim a question is answerable and give
    // no way to find out whether the inputs exist. Every one of these is
    // blocked on data AGI does not store.
    for (const question of QUESTIONS.filter((q) => q.kind === 'computed')) {
      assert.ok(Array.isArray(question.needs) && question.needs.length,
        `${question.n} is computed from nothing`);
    }
  });

  test('a judgment question says why no rule can answer it', () => {
    // The same discipline the chain already applies to catalysts and so_what:
    // a gap is rendered with its reason rather than left blank.
    for (const question of QUESTIONS.filter((q) => q.kind === 'judgment')) {
      assert.ok(question.note && question.note.length > 25, `${question.n} has no stated reason`);
    }
  });

  test('question 100 is a judgment and says it depends on the rest', () => {
    const last = QUESTIONS[99];
    assert.equal(last.kind, 'judgment');
    assert.match(last.note, /ninety-nine/);
  });

  test('the register is honest about how the work divides', () => {
    // Asserted so that reclassifying a question is a deliberate act with a
    // visible diff, rather than a quiet change to what the page promises.
    assert.deepEqual(byKind(), { stated: 40, computed: 51, judgment: 9 });
  });

  test('the computed half needs line items AGI does not store', () => {
    const needed = lineItemsNeeded();
    // valuation_consensus holds revenue and ebitda per ticker and nothing else
    // on this list. Naming the rest is what makes the gap a plan.
    for (const item of ['receivables', 'inventories', 'payables', 'capex',
      'operating_cash_flow', 'gross_debt', 'cash', 'share_count', 'debt_schedule']) {
      assert.ok(needed.includes(item), `${item} is needed by no question`);
    }
    assert.ok(needed.length > 25, `only ${needed.length} line items named`);
  });
});
