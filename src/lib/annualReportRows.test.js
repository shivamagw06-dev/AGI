import test from 'node:test';
import assert from 'node:assert/strict';
import {
  LABEL, ORDER, citedPages, countRows, explain, periodsLine, rowsFor, statusOfBlocked,
} from './annualReportRows.js';

const question = (n, kind = 'computed') => ({ n, ask: `question ${n}`, kind, needs: [] });

test('a choice the reader can make outranks a search that found nothing', () => {
  // Making the choice answers the question. "Not disclosed" is the one claim
  // about what the filing contains and should not be made while something the
  // reader can fix is also in the way.
  const { status } = statusOfBlocked([
    { concept: 'ebitda', state: 'not_disclosed' },
    { concept: 'revenue', state: 'recovered_from_document', status: 'needs_a_definition' },
  ]);
  assert.equal(status, 'choose');
});

test('not having looked is never reported as not disclosed', () => {
  // Reliance states EBITDA of 2,07,911 crore. Calling that undisclosed because
  // nothing knows where to look would be the old error in a new word.
  assert.equal(statusOfBlocked([{ concept: 'ebitda', state: 'no_way_to_look' }]).status, 'not_looked_for');
  assert.equal(statusOfBlocked([{ concept: 'ebitda', state: 'not_disclosed' }]).status, 'not_disclosed');
  assert.notEqual(LABEL.not_looked_for, LABEL.not_disclosed);
});

test('a blocker is explained by what happened to the input', () => {
  assert.equal(explain({ concept: 'revenue', status: 'needs_a_definition',
    candidates: ['REVENUE.OPERATIONS_NET', 'REVENUE.TOTAL_INCOME'] }),
  'revenue is disclosed more than one way (OPERATIONS_NET or TOTAL_INCOME) - choose which');
  assert.equal(explain({ concept: 'ebitda', state: 'no_way_to_look' }), 'nothing looks for ebitda in a filing yet');
  assert.equal(explain({ concept: 'debt', state: 'not_disclosed' }), 'searched for debt; the report does not disclose it');
  assert.equal(explain({ concept: 'cfo', state: 'recovered_from_document', status: 'no_fit' }),
    'cfo was found, but not on a basis this question can use');
  assert.equal(explain(null), null);
});

test('an answered row lists the pages its inputs came from', () => {
  assert.deepEqual(citedPages({
    operating_cash_flow: { source_page: 103 }, capex: { source_page: 103 }, revenue: { source_page: 101 },
    cash: null, other: { source_page: null },
  }), [101, 103]);
});

test('a document reading renders with pages and reasons', () => {
  const result = {
    questions: [question(41), question(23), question(11)],
    computed: { answers: {
      41: { value: 192113, formula: 'operating_cash_flow', reason: null, used: { operating_cash_flow: { source_page: 103 } }, blocked_by: null },
      23: { value: null, reason: 'ebitda not reported', blocked_by: [{ concept: 'ebitda', state: 'no_way_to_look' }] },
      11: { value: null, reason: 'revenue not reported',
        blocked_by: [{ concept: 'revenue', status: 'needs_a_definition', candidates: ['REVENUE.OPERATIONS_NET', 'REVENUE.TOTAL_INCOME'] }] },
    } },
  };
  const rows = rowsFor(result);
  assert.equal(rows[0].status, 'computed');
  assert.deepEqual(rows[0].pages, [103]);
  assert.equal(rows[1].status, 'not_looked_for');
  assert.equal(rows[2].status, 'choose');
  assert.match(rows[2].explanation, /choose which/);
});

test('a pasted reading still renders the way it did', () => {
  const result = {
    questions: [question(41), question(5, 'stated')],
    computed: { answers: { 41: { value: null, formula: null, reason: 'operating_cash_flow not reported' } } },
  };
  const [computed, stated] = rowsFor(result);
  assert.equal(computed.status, 'needs_data');
  assert.equal(computed.explanation, 'operating_cash_flow not reported');
  assert.equal(stated.computed, null);
});

test('a computed answer with a reason is not counted as answered', () => {
  const rows = rowsFor({
    questions: [question(64)],
    computed: { answers: { 64: { value: 0.6, reason: 'cash not reported' } } },
  });
  assert.equal(rows[0].status, 'needs_data');
});

test('counts cover every row once', () => {
  const rows = [{ status: 'computed' }, { status: 'choose' }, { status: 'computed' }];
  assert.deepEqual(countRows(rows), { computed: 2, choose: 1 });
  for (const status of ORDER) assert.ok(LABEL[status], `${status} has no label`);
});

test('both response shapes describe their periods', () => {
  assert.equal(periodsLine({ ticker: 'RELIANCE', periods: { periods: 5, from: '2022-03-31', to: '2026-03-31', units: ['INR x10000000'] } }),
    'RELIANCE: 5 annual periods, 2022-03-31 to 2026-03-31, INR x10000000');
  assert.equal(periodsLine({ company: 'RELIANCE', periods: ['2026-03-31', '2025-03-31'], recovered: 22 }),
    'RELIANCE: 2026-03-31, 2025-03-31, 22 figures read from the document');
  assert.equal(periodsLine({ periods: [] }), null);
  assert.equal(periodsLine(null), null);
});

test('a row with no figure is not answered, even without a reason', () => {
  // A response with neither a value nor a reason would otherwise render as
  // computed with a blank where the number goes - a row that looks answered
  // and says nothing.
  const [row] = rowsFor({
    questions: [question(41)],
    computed: { answers: { 41: { value: null, formula: 'operating_cash_flow', reason: null } } },
  });
  assert.notEqual(row.status, 'computed');
});

test('an input that was never resolved is not reported as unlooked-for', () => {
  // The first live upload resolved no periods, so no input was resolved at
  // all - and every row said "nothing looks for cfo in a filing yet". The
  // search for cfo works. What was missing was a period to run it against.
  const blocker = { need: 'operating_cash_flow', concept: 'cfo', state: 'not_asked_for' };
  assert.equal(statusOfBlocked([blocker]).status, 'not_resolved');
  assert.equal(explain(blocker), 'cfo was not resolved for this period');
  assert.doesNotMatch(explain(blocker), /nothing looks for/);
});

test('a reason that stopped the whole reading is what every computed row says', () => {
  // Deriving a cause per row from an empty resolution invents fifty-one
  // explanations for one fact.
  const rows = rowsFor({
    questions: [question(41), question(62), question(5, 'stated')],
    computed: {
      reason: 'no period could be resolved: the statements state years but no balance sheet date',
      answers: {
        41: { value: null, reason: 'no rule computes this yet', blocked_by: [{ concept: 'cfo', state: 'not_asked_for' }] },
        62: { value: null, reason: 'no rule computes this yet', blocked_by: [{ concept: 'cash', state: 'not_asked_for' }] },
      },
    },
  });
  assert.deepEqual(rows.slice(0, 2).map((row) => row.status), ['not_resolved', 'not_resolved']);
  assert.match(rows[0].explanation, /no balance sheet date/);
  assert.equal(rows[2].computed, null);
});

test('every input resolved and no formula is a missing rule, not a missing statement', () => {
  const [row] = rowsFor({
    questions: [question(46)],
    computed: { answers: { 46: { value: null, reason: 'no rule computes this yet', no_rule: true, blocked_by: null } } },
  });
  assert.equal(row.status, 'no_rule');
});

test('every input resolved and too few years is a refusal, not a missing statement', () => {
  // Reliance's report covers two years. A three-year rate needs four.
  const [row] = rowsFor({
    questions: [question(12)],
    computed: { answers: { 12: { value: null, reason: 'four annual periods are needed for a three-year rate', blocked_by: null } } },
  });
  assert.equal(row.status, 'cannot_compute');
  assert.match(row.explanation, /four annual periods/);
});
