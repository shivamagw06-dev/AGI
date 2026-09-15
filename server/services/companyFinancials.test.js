import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  comparable, ratio, growth, cagr, freeCashFlow, netDebt, netDebtToEbitda,
  interestCover, outgrowingSales, cashConversion, sharesOf, shareCountChange,
} from './companyFinancials.js';

const period = (over) => ({
  ticker: 'ACME', period_type: 'annual', basis: 'consolidated',
  currency: 'INR', scale: 10000000, period_end: '2026-03-31', ...over,
});

// The worked example an underwriter would produce: revenue 14% higher,
// receivables 24% higher, cash conversion falling.
const FY26 = period({
  period_end: '2026-03-31', revenue: 11400, cost_of_sales: 7000, ebitda: 2280, ebit: 1800,
  interest_expense: 380, net_income: 1100, operating_cash_flow: 1930, capex: 780,
  receivables: 2480, inventories: 1500, payables: 1200, gross_debt: 6000, cash: 1200,
});
const FY25 = period({
  period_end: '2025-03-31', revenue: 10000, cost_of_sales: 6200, ebitda: 1900, ebit: 1500,
  interest_expense: 350, net_income: 910, operating_cash_flow: 1780, capex: 600,
  receivables: 2000, inventories: 1350, payables: 1100, gross_debt: 5800, cash: 900,
});

const near = (found, want, label) => {
  assert.equal(found.reason, null, `${label}: ${found.reason}`);
  assert.ok(Math.abs(found.value - want) < 0.005, `${label}: ${found.value} vs ${want}`);
};

describe('figures an underwriter derives', () => {
  test('growth, margin and leverage read as reported', () => {
    near(growth(FY26, FY25, 'revenue'), 0.14, 'revenue growth');
    near(ratio(FY26, 'ebitda', 'revenue'), 0.2, 'ebitda margin');
    near(netDebtToEbitda(FY26), (6000 - 1200) / 2280, 'net debt / ebitda');
    near(interestCover(FY26), 1800 / 380, 'interest cover');
    assert.equal(netDebt(FY26).value, 4800);
  });

  test('receivables outgrowing sales is the finding, not the ratio', () => {
    // 24% against 14%. The number an underwriter reads before the margin.
    near(outgrowingSales(FY26, FY25, 'receivables'), 0.24 - 0.14, 'receivables vs sales');
    near(growth(FY26, FY25, 'receivables'), 0.24, 'receivables growth');
  });

  test('cash conversion falls even as revenue and EBITDA rise', () => {
    const now = cashConversion(FY26);
    const before = cashConversion(FY25);
    assert.equal(now.reason, null);
    assert.ok(now.value < before.value,
      `conversion should fall: ${now.value} vs ${before.value}`);
  });

  test('capex is read by magnitude, so a sign convention cannot double it', () => {
    // One file records capex as an outflow and another as a positive number.
    // Trusting the sign makes the two disagree by twice the capex.
    const positive = freeCashFlow(period({ operating_cash_flow: 1930, capex: 780 }));
    const negative = freeCashFlow(period({ operating_cash_flow: 1930, capex: -780 }));
    assert.equal(positive.value, 1150);
    assert.equal(negative.value, 1150);
  });

  test('every figure carries the formula and the inputs that produced it', () => {
    const found = netDebtToEbitda(FY26);
    assert.equal(found.formula, '(gross_debt - cash) / ebitda');
    assert.deepEqual(found.inputs, { net_debt: 4800, ebitda: 2280 });
  });
});

describe('what it refuses to compute', () => {
  test('a missing input is a blank that names itself', () => {
    const found = netDebtToEbitda(period({ gross_debt: 6000, ebitda: 2280 }));
    assert.equal(found.value, null);
    assert.match(found.reason, /cash not reported/);
  });

  test('a quarter is not compared against a year', () => {
    // The mistake a column of numbers makes easy and a reader never sees.
    const q = period({ period_type: 'quarter', period_end: '2026-06-30', revenue: 3000 });
    const found = growth(q, FY25, 'revenue');
    assert.equal(found.value, null);
    assert.match(found.reason, /annual cannot be compared against a quarter/);
  });

  test('crore is not compared against millions', () => {
    // A thousand-fold error that looks exactly like a very good year.
    const millions = period({ period_end: '2025-03-31', scale: 1000000, revenue: 120 });
    const found = growth(FY26, millions, 'revenue');
    assert.equal(found.value, null);
    assert.match(found.reason, /different scales/);
  });

  test('consolidated is not compared against standalone', () => {
    const standalone = period({ period_end: '2025-03-31', basis: 'standalone', revenue: 8000 });
    assert.match(growth(FY26, standalone, 'revenue').reason, /standalone/);
  });

  test('a different currency is not compared', () => {
    const usd = period({ period_end: '2025-03-31', currency: 'USD', revenue: 1200 });
    assert.match(growth(FY26, usd, 'revenue').reason, /USD/);
  });

  test('a zero denominator is a refusal, never an infinity', () => {
    assert.match(ratio(period({ ebitda: 100, revenue: 0 }), 'ebitda', 'revenue').reason, /zero/);
    assert.match(netDebtToEbitda(period({ gross_debt: 10, cash: 1, ebitda: 0 })).reason, /zero/);
    assert.match(growth(FY26, period({ period_end: '2025-03-31', revenue: 0 }), 'revenue').reason, /was zero/);
  });

  test('negative EBITDA is not a leverage multiple', () => {
    // 4800 / -500 is -9.6x, which reads as less levered than zero.
    const found = netDebtToEbitda(period({ gross_debt: 6000, cash: 1200, ebitda: -500 }));
    assert.equal(found.value, null);
    assert.match(found.reason, /negative/);
  });

  test('CAGR uses the years between the dates, not the rows between them', () => {
    // A company that changes its financial year has periods that are not a
    // year apart, and counting rows reports a fifteen-month year as a year.
    const start = period({ period_end: '2021-03-31', revenue: 5000 });
    const five = cagr(FY26, start, 'revenue');
    near(five, (11400 / 5000) ** (1 / 5) - 1, 'five-year CAGR');
    assert.match(five.formula, /1 \/ 5\.00 years/);

    const fifteenMonths = period({ period_end: '2025-01-01', revenue: 10000 });
    const found = cagr(FY26, fifteenMonths, 'revenue');
    assert.ok(Math.abs(found.value - (0.14)) > 0.01,
      'a fifteen-month gap must not produce the same figure as a year');
  });

  test('periods out of order are refused rather than inverted', () => {
    assert.match(cagr(FY25, FY26, 'revenue').reason, /not in order|less than a year/);
  });

  test('a negative starting value has no compound rate', () => {
    const loss = period({ period_end: '2021-03-31', revenue: -100 });
    assert.match(cagr(FY26, loss, 'revenue').reason, /not positive/);
  });
});

describe('a share count is not money', () => {
  // Berkshire reports money in millions and 1,438,223 Class A shares in
  // shares. Under one scale that is 1.4 trillion shares, which is why the
  // count was left out of the first load entirely.
  const y25 = period({ period_end: '2025-12-31', share_count: 1438223, share_scale: 1 });
  const y24 = period({ period_end: '2024-12-31', share_count: 1437720, share_scale: 1 });

  test('the count is read in actual shares', () => {
    const found = sharesOf(y25);
    assert.equal(found.value, 1438223);
    assert.deepEqual(found.inputs, { share_count: 1438223, share_scale: 1 });
  });

  test('a filing that reports shares in millions reads the same way', () => {
    const inMillions = period({ share_count: 1.438223, share_scale: 1000000 });
    assert.equal(Math.round(sharesOf(inMillions).value), 1438223);
  });

  test('a change in unit cannot become a change in count', () => {
    // The failure this exists to prevent: the same 1.44m shares reported two
    // ways, which without conversion reads as the count collapsing by 99.9999%.
    const millions = period({ period_end: '2024-12-31', share_count: 1.437720, share_scale: 1000000 });
    const found = shareCountChange(y25, millions);
    assert.equal(found.reason, null);
    assert.ok(Math.abs(found.value - (1438223 / 1437720 - 1)) < 1e-9,
      `unit change leaked into the result: ${found.value}`);
  });

  test('Berkshire bought back almost nothing in 2025', () => {
    // 1,438,223 against 1,437,720 average Class A equivalents: up 0.03%.
    const found = shareCountChange(y25, y24);
    assert.ok(Math.abs(found.value) < 0.001, String(found.value));
  });

  test('a count without its scale is refused, not assumed', () => {
    const noScale = period({ share_count: 1438223 });
    assert.match(sharesOf(noScale).reason, /share_scale not reported/);
    assert.match(shareCountChange(noScale, y24).reason, /later period/);
    assert.match(shareCountChange(y25, noScale).reason, /earlier period/);
  });

  test('a missing count is refused rather than treated as zero', () => {
    assert.match(sharesOf(period({})).reason, /share_count not reported/);
  });
});
