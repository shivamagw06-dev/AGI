import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { computedAnswers, periodsRead } from './annualReportComputed.js';

// Berkshire's statements as imported: three annual periods, money in millions.
const p = (over) => ({ period_type: 'annual', basis: 'consolidated', currency: 'USD', scale: 1000000, ...over });
const BERKSHIRE = [
  p({ period_end: '2025-12-31', revenue: 371444, interest_expense: 5069, pre_tax_income: 82459,
    tax_expense: 15199, net_income: 66968, depreciation: 13476, operating_cash_flow: 45969,
    capex: 20927, cash: 51877, receivables: 48718, inventories: 24424, gross_debt: 129081,
    total_equity: 719703, share_count: 1438223, share_scale: 1 }),
  p({ period_end: '2024-12-31', revenue: 371433, net_income: 88995, operating_cash_flow: 30592,
    capex: 18976, cash: 47729, receivables: 48390, inventories: 24008, gross_debt: 124762,
    share_count: 1437720, share_scale: 1 }),
  p({ period_end: '2023-12-31', revenue: 364482, net_income: 96223, operating_cash_flow: 49196, capex: 19409 }),
];

const answer = (n, periods = BERKSHIRE) => computedAnswers(periods).get(n);

describe('questions the statements answer', () => {
  test('the figures an underwriter reads first', () => {
    assert.equal(answer(42).value, 25042, 'free cash flow');
    assert.equal(answer(63).value, 77204, 'net debt');
    assert.equal(answer(61).value, 129081, 'gross debt');
    assert.equal(answer(62).value, 51877, 'cash');
    assert.ok(Math.abs(answer(53).value - 20927 / 371444) < 1e-9, 'capex / revenue');
  });

  test('capex as a share of revenue is positive', () => {
    // Stored as a magnitude since the outflow fix; before it, a cash flow
    // statement's "(20,927)" produced -5.6%, which reads as money coming in.
    assert.ok(answer(53).value > 0, String(answer(53).value));
  });

  test('every answer carries the formula that produced it', () => {
    for (const [n, result] of computedAnswers(BERKSHIRE)) {
      if (result.reason !== null) continue;
      assert.ok(result.formula && result.formula.length > 2, `question ${n} has no formula`);
      assert.ok(result.inputs && Object.keys(result.inputs).length, `question ${n} has no inputs`);
    }
  });
});

describe('questions the statements refuse', () => {
  test('a company that reports no EBITDA has no leverage multiple', () => {
    // Berkshire does not publish EBITDA. Deriving one from EBIT plus D&A and
    // presenting it as reported is the thing this refuses to do.
    assert.equal(answer(64).value, null);
    assert.match(answer(64).reason, /ebitda not reported/);
    assert.match(answer(23).reason, /ebitda not reported/);
  });

  test('a refusal names the line item that is missing', () => {
    // The reason is the specification for what to load next, so it has to
    // name something rather than say "unavailable".
    for (const [n, result] of computedAnswers(BERKSHIRE)) {
      if (result.reason === null) continue;
      assert.ok(/not reported|periods|needed|zero|positive|compared/.test(result.reason),
        `question ${n}: "${result.reason}"`);
    }
  });

  test('one period compares against nothing', () => {
    const single = computedAnswers([BERKSHIRE[0]]);
    assert.match(single.get(11).reason, /only one period/);
    assert.match(single.get(47).reason, /only one period/);
    // A single-period figure is still answerable.
    assert.equal(single.get(63).value, 77204);
  });

  test('no annual periods means no answers at all', () => {
    assert.equal(computedAnswers([]).size, 0);
    assert.equal(computedAnswers([{ ...BERKSHIRE[0], period_type: 'quarter' }]).size, 0);
  });

  test('a quarter is never mixed into an annual series', () => {
    // Growth against three months is the mistake a column of numbers makes
    // easy; it is excluded here as well as refused in the comparison.
    const withQuarter = [...BERKSHIRE, p({ period_end: '2026-06-30', period_type: 'quarter', revenue: 190000 })];
    assert.equal(computedAnswers(withQuarter).get(11).value, computedAnswers(BERKSHIRE).get(11).value);
  });
});

describe('describing what is stored', () => {
  test('the range and the units are reported together', () => {
    assert.deepEqual(periodsRead(BERKSHIRE),
      { periods: 3, from: '2023-12-31', to: '2025-12-31', units: ['USD x1000000'] });
  });

  test('more than one unit is named rather than merged', () => {
    // Two scales for one company is legitimate across a currency change, and
    // is otherwise a file that will produce a thousand-fold error.
    const mixed = [...BERKSHIRE, p({ period_end: '2022-12-31', currency: 'USD', scale: 1, revenue: 302089000000 })];
    assert.equal(periodsRead(mixed).units.length, 2);
  });

  test('nothing stored is null, not an empty description', () => {
    assert.equal(periodsRead([]), null);
  });
});
