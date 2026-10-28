import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CROSS_CHECK_TOLERANCE, balanceSheetRowFrom, bookEquityFrom, freeFloatMarketCap, freeFloatRatioFrom,
  marketCapFromEarnings,
  sizeForUniverse, sizeRows,
} from './aiEnablersSize.js';

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

/* ── the universe pass, Upstox derived and Yahoo checked ───────────── */

/** Payload shapes verbatim from the probe run. */
const fundamentalsFor = (overrides = {}) => async (isin, endpoint, params = {}) => {
  if (endpoint === 'balance-sheet') {
    if (overrides['balance-sheet']) return overrides['balance-sheet'];
    // Hitachi Energy India reports no consolidated statements, which is a
    // fact about the company rather than a fault - so consolidated comes
    // back empty and standalone carries the rows.
    if (params.type === 'consolidated') {
      return { status: 'success', data: { type: 'consolidated', units_in: 'crore', history: [], full_statement: [] } };
    }
    return {
      status: 'success',
      data: {
        type: 'standalone', units_in: 'crore',
        history: [POWERINDIA.balanceSheetRow],
        full_statement: [{
          particular: 'Equity Capital',
          history: [{ period: 'Mar 2026', value: 5175.96 }],
        }],
      },
    };
  }
  const map = {
    'key-ratios': { status: 'success', data: POWERINDIA.keyRatios },
    'share-holdings': { status: 'success', data: POWERINDIA.shareHoldings },
    ...overrides,
  };
  return map[endpoint];
};

const UNIVERSE = { members: [{ symbol: 'POWERINDIA', isin: 'INE07Y701011' }] };

test('a member whose Yahoo cap agrees is usable, with both figures kept', async () => {
  const sizes = await sizeForUniverse(UNIVERSE, {
    fetchFundamentals: fundamentalsFor(),
    fetchMarketCaps: async () => ({ bySymbol: { POWERINDIA: { crore: 134_900, reason: null } }, error: null }),
  });
  const row = sizes.bySymbol.POWERINDIA;
  assert.equal(row.usable, true);
  assert.equal(Math.round(row.marketCap), 134_937);
  assert.equal(row.independent.crore, 134_900);
  assert.equal(row.independent.source, 'external');
  assert.equal(Math.abs(row.crossCheck.gap) < 0.001, true);
  assert.deepEqual(sizes.usable, ['POWERINDIA']);
});

test('the balance sheet is read from the standalone variant that returns rows', async () => {
  // Consolidated comes back with history: [] from Upstox, so a pass that
  // only tried consolidated would find no equity for anyone.
  const sizes = await sizeForUniverse(UNIVERSE, {
    fetchFundamentals: fundamentalsFor({
      'balance-sheet': { status: 'success', data: { type: 'consolidated', units_in: 'crore', history: [] } },
    }),
    fetchMarketCaps: async () => ({ bySymbol: { POWERINDIA: { crore: 134_900, reason: null } }, error: null }),
  });
  assert.equal(sizes.bySymbol.POWERINDIA.usable, false);
  assert.match(sizes.bySymbol.POWERINDIA.reason, /missing book_equity/);
});

test('Yahoo being unreachable refuses every member rather than passing them', async () => {
  // The whole point of the cross-check: no second source means no verified
  // size, so nothing may reach the screen.
  const sizes = await sizeForUniverse(UNIVERSE, {
    fetchFundamentals: fundamentalsFor(),
    fetchMarketCaps: async () => ({ bySymbol: { POWERINDIA: { crore: null, reason: 'NOT_RETURNED' } }, error: 'yahoo quote request failed (429)' }),
  });
  assert.deepEqual(sizes.usable, []);
  assert.equal(sizes.crossCheckError, 'yahoo quote request failed (429)');
  assert.match(sizes.bySymbol.POWERINDIA.reason, /arithmetic, not a market cap/);
  // The derivation is still reported, so a reviewer sees what was refused.
  assert.equal(Math.round(sizes.bySymbol.POWERINDIA.marketCap), 134_937);
});

test('a disagreeing Yahoo cap refuses the member and names the gap', async () => {
  const sizes = await sizeForUniverse(UNIVERSE, {
    fetchFundamentals: fundamentalsFor(),
    fetchMarketCaps: async () => ({ bySymbol: { POWERINDIA: { crore: 337_000, reason: null } }, error: null }),
  });
  const row = sizes.bySymbol.POWERINDIA;
  assert.equal(row.usable, false);
  assert.equal(row.value, null);
  assert.equal(row.crossCheck.within, false);
  assert.match(row.reason, /wrong basis for this P\/B/);
  assert.deepEqual(sizes.refused.map((one) => one.symbol), ['POWERINDIA']);
});

test('a fundamentals fetch that throws does not fail the whole pass', async () => {
  const sizes = await sizeForUniverse(
    { members: [{ symbol: 'POWERINDIA', isin: 'INE07Y701011' }, { symbol: 'BROKEN', isin: 'INE000A01001' }] },
    {
      fetchFundamentals: async (isin, endpoint) => {
        if (isin === 'INE000A01001') throw new Error('Upstox HTTP 500');
        return fundamentalsFor()(isin, endpoint);
      },
      fetchMarketCaps: async () => ({
        bySymbol: { POWERINDIA: { crore: 134_900, reason: null }, BROKEN: { crore: 1_000, reason: null } },
        error: null,
      }),
    },
  );
  assert.deepEqual(sizes.usable, ['POWERINDIA']);
  assert.match(sizes.bySymbol.BROKEN.reason, /Upstox HTTP 500/);
});

test('sizeRows carries only verified sizes into the screen shape', async () => {
  const sizes = await sizeForUniverse(
    { members: [{ symbol: 'POWERINDIA', isin: 'INE07Y701011' }] },
    {
      fetchFundamentals: fundamentalsFor(),
      fetchMarketCaps: async () => ({ bySymbol: { POWERINDIA: { crore: 337_000, reason: null } }, error: null }),
    },
  );
  // Refused, so the screen sees null and reports it unscreened rather than
  // failing it on a size nobody verified.
  assert.deepEqual(sizeRows(sizes, { POWERINDIA: 4_029_500_000 }), [
    { symbol: 'POWERINDIA', freeFloatMarketCap: null, medianDailyTurnover: 4_029_500_000 },
  ]);
});


/* ── the earnings route, for when no third party is reachable ───────── */

test('market cap the other way round is P/E times net income', () => {
  // POWERINDIA: P/E 117.3. If net income is such that the two routes land in
  // the same place, the basis is coherent.
  const out = marketCapFromEarnings({ keyRatios: POWERINDIA.keyRatios, netIncome: 1_150.0 });
  assert.equal(Math.round(out.value), 134_895);
  assert.equal(out.reason, null);
});

test('a loss-making company has no P/E-implied market cap', () => {
  // Multiplying a negative P/E by a negative income yields a positive number
  // for entirely the wrong reason.
  assert.equal(marketCapFromEarnings({ keyRatios: POWERINDIA.keyRatios, netIncome: -400 }).reason,
    'NON_POSITIVE_NET_INCOME');
  assert.equal(marketCapFromEarnings({ keyRatios: [{ name: 'P/B', company_value: '3' }], netIncome: 100 }).reason,
    'NO_PE');
  assert.equal(marketCapFromEarnings({ keyRatios: POWERINDIA.keyRatios, netIncome: null }).reason,
    'NO_NET_INCOME');
});

test('the earnings route checks the balance-sheet route when no third party answers', async () => {
  const sizes = await sizeForUniverse(UNIVERSE, {
    fetchFundamentals: fundamentalsFor(),
    fetchMarketCaps: null,
    netIncomeFor: async () => 1_150.0,
  });
  const row = sizes.bySymbol.POWERINDIA;
  assert.equal(row.usable, true);
  assert.equal(row.crossCheck.checkedBy, 'earnings');
  assert.equal(sizes.crossCheckSource, 'earnings');
  // Both routes are kept, so a reviewer can see what agreed with what.
  assert.equal(Math.round(row.marketCap), 134_937);
  assert.equal(Math.round(row.earningsRoute.value), 134_895);
});

test('the two routes diverging refuses the member, which is the holding-company case', async () => {
  // A consolidated ratio against a standalone statement breaks both routes,
  // but by different factors, because net income and book equity do not
  // scale between the two books the same way. The disagreement is the signal.
  const sizes = await sizeForUniverse(UNIVERSE, {
    fetchFundamentals: fundamentalsFor(),
    fetchMarketCaps: null,
    netIncomeFor: async () => 3_000.0,        // implies 352,000 via P/E
  });
  const row = sizes.bySymbol.POWERINDIA;
  assert.equal(row.usable, false);
  assert.equal(row.value, null);
  assert.equal(row.crossCheck.within, false);
});

test('no third party and no earnings source still refuses rather than passing', async () => {
  const sizes = await sizeForUniverse(UNIVERSE, {
    fetchFundamentals: fundamentalsFor(),
    fetchMarketCaps: null,
    netIncomeFor: null,
  });
  assert.deepEqual(sizes.usable, []);
  assert.match(sizes.bySymbol.POWERINDIA.reason, /arithmetic, not a market cap/);
});

/* ── which basis, and does Upstox's own equity line agree ───────────── */

test('consolidated is preferred where it exists', () => {
  const chosen = balanceSheetRowFrom([
    ['consolidated', { data: { units_in: 'crore', history: [{ total_asset: 100, total_liability: 40, period: 'Mar 2026' }] } }],
    ['standalone', { data: { units_in: 'crore', history: [{ total_asset: 20, total_liability: 8, period: 'Mar 2026' }] } }],
  ]);
  assert.equal(chosen.basis, 'consolidated');
  assert.equal(chosen.row.total_asset, 100);
});

test('an empty consolidated sheet is a fact about the company, not a failure', () => {
  // Upstox defaults to consolidated and returns nothing for a company with
  // no subsidiaries to consolidate. For that company standalone is the whole
  // company, and the basis question this derivation worries about does not
  // arise at all.
  const chosen = balanceSheetRowFrom([
    ['consolidated', { data: { units_in: 'crore', history: [] } }],
    ['standalone', { data: { units_in: 'crore', history: [{ total_asset: 12043.72, total_liability: 6867.76, period: 'Mar 2026' }] } }],
  ]);
  assert.equal(chosen.basis, 'standalone');
  assert.equal(chosen.reason, null);
});

test('no rows on any basis is named, not treated as zero equity', () => {
  const chosen = balanceSheetRowFrom([
    ['consolidated', { data: { history: [] } }],
    ['standalone', { data: { history: [] } }],
  ]);
  assert.equal(chosen.row, null);
  assert.equal(chosen.reason, 'NO_BALANCE_SHEET_ON_ANY_BASIS');
});

test('units are read, not assumed', () => {
  // The whole derivation is denominated in crore; a sheet in anything else
  // would be out by orders of magnitude and still look like a number.
  const chosen = balanceSheetRowFrom([
    ['consolidated', { data: { units_in: 'million', history: [{ total_asset: 100, total_liability: 40, period: 'Mar 2026' }] } }],
  ]);
  assert.equal(chosen.reason, 'UNEXPECTED_UNITS');
  assert.equal(chosen.units, 'million');
});

test('the Equity Capital line is picked up and matched to the same period', () => {
  const chosen = balanceSheetRowFrom([
    ['standalone', { data: {
      units_in: 'crore',
      history: [{ total_asset: 12043.72, total_liability: 6867.76, period: 'Mar 2026' }],
      full_statement: [{ particular: 'Equity Capital', history: [
        { period: 'Mar 2025', value: 4000 },
        { period: 'Mar 2026', value: 5175.96 },
      ] }],
    } }],
  ]);
  assert.equal(chosen.statedEquity, 5175.96);
});

test('the derivation records that the subtraction agrees with Equity Capital', async () => {
  const sizes = await sizeForUniverse(UNIVERSE, {
    fetchFundamentals: fundamentalsFor(),
    fetchMarketCaps: async () => ({ bySymbol: { POWERINDIA: { crore: 134_900, reason: null } }, error: null }),
  });
  const row = sizes.bySymbol.POWERINDIA;
  assert.equal(row.basisUsed, 'standalone');
  assert.equal(row.lineage.inputs.book_equity.agreesWithStated, true);
  assert.equal(row.lineage.inputs.book_equity.statedEquityCapital, 5175.96);
  assert.equal(row.usable, true);
});

test('a row whose Equity Capital disagrees is refused', async () => {
  // Same quantity by two names. If they differ, the row is not what it is
  // being taken for and nothing downstream should proceed on it.
  const sizes = await sizeForUniverse(UNIVERSE, {
    fetchFundamentals: fundamentalsFor({
      'balance-sheet': { status: 'success', data: {
        type: 'standalone', units_in: 'crore',
        history: [{ total_asset: 12043.72, total_liability: 6867.76, period: 'Mar 2026' }],
        full_statement: [{ particular: 'Equity Capital', history: [{ period: 'Mar 2026', value: 9000 }] }],
      } },
    }),
    fetchMarketCaps: async () => ({ bySymbol: { POWERINDIA: { crore: 134_900, reason: null } }, error: null }),
  });
  const row = sizes.bySymbol.POWERINDIA;
  assert.equal(row.usable, false);
  assert.match(row.reason, /disagrees with the Equity Capital line/);
});

test('time_period is never sent to balance-sheet, which does not take it', async () => {
  const seen = [];
  await sizeForUniverse(UNIVERSE, {
    fetchFundamentals: async (isin, endpoint, params) => {
      if (endpoint === 'balance-sheet') seen.push(params);
      return fundamentalsFor()(isin, endpoint, params);
    },
    fetchMarketCaps: async () => ({ bySymbol: { POWERINDIA: { crore: 134_900, reason: null } }, error: null }),
  });
  assert.equal(seen.length, 2);
  assert.deepEqual(seen.map((one) => one.type), ['consolidated', 'standalone']);
  assert.equal(seen.every((one) => one.time_period === undefined), true);
  assert.equal(seen.every((one) => one.fs === true), true);
});

test('the earnings route refuses when the P/E is on a different period', () => {
  // Measured against Hitachi Energy India's FY26 filing. Upstox quotes a P/E
  // of 117.3; the filed EPS is 221.63 and the close was 31,230, so price over
  // filed EPS is 140.91. The stated P/E implies 266.24 - a trailing twelve
  // months containing a far stronger Q1 FY27. Multiplying it by annual net
  // profit understates market cap by roughly what earnings grew.
  const out = marketCapFromEarnings({
    keyRatios: [{ name: 'P/E', company_value: '117.3' }],
    netIncome: 987.84,
    filedEps: 221.63,
    price: 31230,
  });
  assert.equal(out.value, null);
  assert.equal(out.reason, 'PE_PERIOD_DOES_NOT_MATCH_EARNINGS');
  assert.equal(out.impliedEps, 266.24);
  assert.equal(Number((out.gap * 100).toFixed(1)), 20.1);
});

test('and it proceeds when the periods do agree', () => {
  const out = marketCapFromEarnings({
    keyRatios: [{ name: 'P/E', company_value: '140.91' }],
    netIncome: 987.84,
    filedEps: 221.63,
    price: 31230,
  });
  assert.equal(Math.round(out.value), 139_197);
  assert.equal(out.reason, null);
});

test('without a filed EPS the period cannot be checked, and is not assumed to match', () => {
  // The check is skipped rather than passed, and the caller still has the
  // cross-check tolerance behind it.
  const out = marketCapFromEarnings({
    keyRatios: [{ name: 'P/E', company_value: '117.3' }], netIncome: 987.84,
  });
  assert.equal(Math.round(out.value), 115_874);
  assert.equal(out.reason, null);
});

test('the 25% cross-check tolerance would not have caught the period mismatch', () => {
  // Demonstrated, not asserted: 20.1% is inside 25%, so the earnings route
  // would have corroborated a market cap it had no business corroborating.
  const wrong = 117.3 * 987.84;          // P/E on TTM, profit on FY26
  const right = 140.91 * 987.84;
  const gap = Math.abs(wrong / right - 1);
  assert.ok(gap < CROSS_CHECK_TOLERANCE, `${(gap * 100).toFixed(1)}% is inside the tolerance`);
});
