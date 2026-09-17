import test from 'node:test';
import assert from 'node:assert/strict';
import { bookEquityFrom, freeFloatMarketCap, freeFloatRatioFrom } from './aiEnablersSize.js';

/** Verbatim from the probe run against POWERINDIA on 2026-09-17. */
const POWERINDIA = {
  keyRatios: [
    { name: 'P/E', company_value: '117.3', sector_value: '26.84' },
    { name: 'P/B', company_value: '26.07', sector_value: '5.71' },
    { name: 'ROE', company_value: '19.09%', sector_value: '9.89%' },
  ],
  balanceSheetRow: { total_asset: 12043.72, total_liability: 6867.76, period: 'Mar 2026' },
  shareHoldings: [
    { category: 'promoters', history: [{ value: 71.31, period: 'Jun 2026' }] },
    { category: 'fii', history: [{ value: 12.44, period: 'Jun 2026' }] },
    { category: 'other_dii', history: [{ value: 2.82, period: 'Jun 2026' }] },
    { category: 'retail_and_other', history: [{ value: 9.92, period: 'Jun 2026' }] },
    { category: 'mutual_funds', history: [{ value: 3.51, period: 'Jun 2026' }] },
  ],
};

test('book equity is assets less liabilities, with its basis recorded', () => {
  const equity = bookEquityFrom(POWERINDIA.balanceSheetRow);
  assert.equal(Number(equity.equity.toFixed(2)), 5175.96);
  assert.equal(equity.basis, 'standalone');
  assert.equal(equity.period, 'Mar 2026');
});

test('an empty balance sheet is a reason, not a zero equity', () => {
  // Upstox returns consolidated statements with no rows at all, so this is
  // the normal case rather than an edge one.
  assert.equal(bookEquityFrom({}).reason, 'NO_BALANCE_SHEET');
  assert.equal(bookEquityFrom({}).equity, null);
  assert.equal(bookEquityFrom({ total_asset: 100, total_liability: 140 }).reason, 'NON_POSITIVE_EQUITY');
});

test('the free float is one less the promoter share', () => {
  const float = freeFloatRatioFrom(POWERINDIA.shareHoldings);
  assert.equal(Number(float.ratio.toFixed(4)), 0.2869);
  assert.equal(float.promoterPct, 71.31);
  assert.equal(float.asOf, 'Jun 2026');
  assert.equal(float.categoriesSumTo, 100);
  assert.equal(float.reason, null);
});

test('categories that do not account for the register are flagged', () => {
  // If the parts do not sum to a hundred, the promoter figure may be on a
  // different base and the float derived from it would be wrong.
  const float = freeFloatRatioFrom([
    { category: 'promoters', history: [{ value: 40, period: 'Jun 2026' }] },
    { category: 'fii', history: [{ value: 10, period: 'Jun 2026' }] },
  ]);
  assert.equal(float.reason, 'CATEGORIES_DO_NOT_SUM_TO_100');
  assert.equal(float.categoriesSumTo, 50);
});

test('market cap is P/B times book equity, and needs no share count', () => {
  const size = freeFloatMarketCap({ ...POWERINDIA, independentMarketCap: 134_900 });
  assert.equal(Math.round(size.marketCap), 134_937);
  assert.equal(size.usable, true);
  assert.equal(size.provenance, 'DERIVED');
  assert.equal(Math.round(size.value), 38_714);
  assert.equal(size.lineage.formula.startsWith('market_cap = pb * book_equity'), true);
  assert.equal(size.lineage.inputs.book_equity.source, 'upstox balance-sheet (standalone)');
});

test('the P/B basis is recorded as unstated, because the source does not state it', () => {
  const size = freeFloatMarketCap({ ...POWERINDIA, independentMarketCap: 134_900 });
  assert.equal(size.lineage.inputs.pb.basis, 'not stated by the source');
});

test('nothing is usable without an independent figure to check against', () => {
  // The identity is exact; the basis assumption is not. A second source
  // agreeing is the only thing separating a usable figure from a
  // plausible-looking one.
  const size = freeFloatMarketCap({ ...POWERINDIA, independentMarketCap: null });
  assert.equal(size.usable, false);
  assert.equal(size.value, null);
  assert.match(size.reason, /arithmetic, not a market cap/);
  // The derived figure is still returned, so a reviewer can see what was rejected.
  assert.equal(Math.round(size.marketCap), 134_937);
});

test('a holding company fails the cross-check instead of reporting a wrong size', () => {
  // The hazard this guard exists for. Adani Enterprises' standalone book is
  // a fraction of its consolidated book, so a consolidated P/B against a
  // standalone equity understates market cap by a multiple. Numbers here are
  // illustrative of that shape: a small standalone book, a real market cap.
  const holdingCo = {
    keyRatios: [{ name: 'P/B', company_value: '6.40' }],
    balanceSheetRow: { total_asset: 9_000, total_liability: 7_500, period: 'Mar 2026' },
    shareHoldings: [
      { category: 'promoters', history: [{ value: 74.9, period: 'Jun 2026' }] },
      { category: 'fii', history: [{ value: 13.1, period: 'Jun 2026' }] },
      { category: 'other_dii', history: [{ value: 5.0, period: 'Jun 2026' }] },
      { category: 'retail_and_other', history: [{ value: 7.0, period: 'Jun 2026' }] },
    ],
  };
  const size = freeFloatMarketCap({ ...holdingCo, independentMarketCap: 337_000 });
  assert.equal(Math.round(size.marketCap), 9_600);     // 6.40 x 1,500
  assert.equal(size.usable, false);
  assert.equal(size.value, null);
  assert.equal(size.crossCheck.within, false);
  assert.match(size.reason, /wrong basis for this P\/B/);
});

test('a P/B that is missing refuses rather than defaulting', () => {
  const size = freeFloatMarketCap({
    keyRatios: [{ name: 'P/E', company_value: '117.3' }],
    balanceSheetRow: POWERINDIA.balanceSheetRow,
    shareHoldings: POWERINDIA.shareHoldings,
    independentMarketCap: 134_900,
  });
  assert.equal(size.usable, false);
  assert.match(size.reason, /missing pb/);
});

test('percent signs and commas in the source strings do not become NaN', () => {
  // key-ratios serves strings, and ROE arrives as "19.09%".
  const size = freeFloatMarketCap({
    keyRatios: [{ name: 'P/B', company_value: '26.07' }],
    balanceSheetRow: { total_asset: '12,043.72', total_liability: '6,867.76', period: 'Mar 2026' },
    shareHoldings: POWERINDIA.shareHoldings,
    independentMarketCap: 134_900,
  });
  assert.equal(Math.round(size.marketCap), 134_937);
  assert.equal(size.usable, true);
});

test('the P/B rounding cannot move the answer materially', () => {
  // key-ratios rounds to two decimals. Bound what that can cost.
  const at = (pb) => freeFloatMarketCap({
    ...POWERINDIA,
    keyRatios: [{ name: 'P/B', company_value: String(pb) }],
    independentMarketCap: 134_900,
  }).marketCap;
  const spread = Math.abs(at(26.075) / at(26.065) - 1);
  assert.ok(spread < 0.001, `P/B rounding moved market cap by ${(spread * 100).toFixed(3)}%`);
});
