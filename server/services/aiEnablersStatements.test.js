import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CAPEX_AVAILABLE_FROM_CASH_FLOW, actionsNear, cagr, capexFrom, categoryHistory, lineHistory,
  operatingCashFlow, parseActionDate, resolveRatioBasis, statementFrom,
} from './aiEnablersStatements.js';

/** The documented Reliance income statement, verbatim. */
const INCOME = {
  data: {
    type: 'consolidated', time_period: 'yearly', units_in: 'crore',
    income_statement: [
      { category: 'revenue', history: [
        { value: 1086181, period: 'Mar 2026', change: '+10.53%' },
        { value: 982671, period: 'Mar 2025', change: '+7.15%' },
        { value: 917121, period: 'Mar 2024', change: '+3.1%' },
        { value: 889569, period: 'Mar 2023' },
      ] },
      { category: 'operating_profit', history: [
        { value: 123162, period: 'Mar 2026' }, { value: 106017, period: 'Mar 2025' },
        { value: 104340, period: 'Mar 2024' }, { value: 94046, period: 'Mar 2023' },
      ] },
      { category: 'net_profit', history: [
        { value: 95610, period: 'Mar 2026' }, { value: 80787, period: 'Mar 2025' },
        { value: 78633, period: 'Mar 2024' }, { value: 74088, period: 'Mar 2023' },
      ] },
    ],
    full_statement: [
      { particular: 'Profit After Tax', history: [
        { period: 'Mar 2025', value: 80787 }, { period: 'Mar 2024', value: 78633 },
      ] },
      { particular: 'EPS - Basic', history: [
        { period: 'Mar 2025', value: 51.47 }, { period: 'Mar 2024', value: 51.45 },
      ] },
    ],
  },
};

const rowsAt = (body) => body?.income_statement;

test('the statement is taken from the basis that carries values', () => {
  const picked = statementFrom([
    ['consolidated', { data: { units_in: 'crore', income_statement: [{ category: 'revenue', history: [] }] } }],
    ['standalone', INCOME],
  ], { rowsAt });
  // Consolidated returned its categories with empty histories - structure and
  // no values - which is not data and must not be chosen over one that has it.
  assert.equal(picked.basis, 'standalone');
  assert.equal(picked.rows.length, 3);
});

test('three categories with four periods each is not three periods', () => {
  // My own probe read income_statement: array(3) as three periods and
  // reported the three-year CAGR uncomputable. It is three categories, each
  // carrying four annual points.
  const picked = statementFrom([['consolidated', INCOME]], { rowsAt });
  assert.equal(picked.rows.length, 3);
  assert.equal(categoryHistory(picked.rows, 'revenue').length, 4);
  assert.equal(categoryHistory(picked.rows, 'net_profit')[0].value, 95610);
});

test('a three-year CAGR needs four points and gets them', () => {
  const revenue = categoryHistory(statementFrom([['consolidated', INCOME]], { rowsAt }).rows, 'revenue');
  const growth = cagr(revenue, { years: 3 });
  assert.equal(growth.from, 'Mar 2023');
  assert.equal(growth.to, 'Mar 2026');
  assert.equal(Number((growth.value * 100).toFixed(2)), 6.88);
});

test('a CAGR refuses rather than annualising too short a span', () => {
  const short = cagr([{ value: 200, period: 'Mar 2026' }, { value: 100, period: 'Mar 2025' }], { years: 3 });
  assert.equal(short.value, null);
  assert.equal(short.reason, 'INSUFFICIENT_PERIODS');
  assert.deepEqual({ have: short.have, need: short.need }, { have: 2, need: 4 });
});

test('a loss in the base period does not produce a growth rate', () => {
  const out = cagr([
    { value: 500, period: 'Mar 2026' }, { value: 300, period: 'Mar 2025' },
    { value: 100, period: 'Mar 2024' }, { value: -50, period: 'Mar 2023' },
  ], { years: 3 });
  assert.equal(out.value, null);
  assert.equal(out.reason, 'NON_POSITIVE_BASE');
});

test('EPS is read from the detailed breakdown', () => {
  const picked = statementFrom([['consolidated', INCOME]], { rowsAt });
  assert.equal(lineHistory(picked.full, 'EPS - Basic')[0].value, 51.47);
  assert.equal(lineHistory(picked.full, 'Profit After Tax')[0].value, 80787);
});

/* ── the basis question, answered by measurement ────────────────────── */

test('the P/E identifies which basis the ratios are quoted on', () => {
  // P/E is price over EPS. Dividing the price by each basis's EPS and
  // comparing against the stated P/E names the basis, instead of the code
  // carrying an assumption it cannot test.
  const resolved = resolveRatioBasis({
    statedPe: 25.0,
    price: 1286.75,                                   // 25.0 x 51.47
    epsByBasis: { consolidated: 51.47, standalone: 20.10 },
  });
  assert.equal(resolved.basis, 'consolidated');
  assert.equal(resolved.reason, null);
});

test('a P/E matching neither basis is reported, not forced onto one', () => {
  // It means the ratio is computed on something this code does not hold -
  // trailing twelve months, say - and proceeding would put a number on the
  // page whose basis nobody knows.
  const resolved = resolveRatioBasis({
    statedPe: 25.0, price: 1286.75,
    epsByBasis: { consolidated: 10.0, standalone: 8.0 },
  });
  assert.equal(resolved.basis, null);
  assert.equal(resolved.reason, 'PE_MATCHES_NO_AVAILABLE_BASIS');
  assert.equal(resolved.candidates.length, 2);
});

test('a company reporting one basis resolves to it', () => {
  const resolved = resolveRatioBasis({
    statedPe: 117.3, price: 31230, epsByBasis: { standalone: 266.24 },
  });
  assert.equal(resolved.basis, 'standalone');
});

test('a loss-making basis is not a candidate', () => {
  const resolved = resolveRatioBasis({
    statedPe: 25.0, price: 1286.75,
    epsByBasis: { consolidated: 51.47, standalone: -4.0 },
  });
  assert.equal(resolved.basis, 'consolidated');
  assert.equal(resolved.candidates.find((one) => one.basis === 'standalone').impliedPe, null);
});

test('units other than crore are refused', () => {
  const picked = statementFrom([
    ['consolidated', { data: { units_in: 'million', income_statement: [{ category: 'revenue', history: [{ value: 1, period: 'Mar 2026' }] }] } }],
  ], { rowsAt });
  assert.equal(picked.reason, 'UNEXPECTED_UNITS');
});

test('the percentage-change strings do not poison a numeric read', () => {
  const picked = statementFrom([['consolidated', INCOME]], { rowsAt });
  const revenue = categoryHistory(picked.rows, 'revenue');
  assert.equal(revenue.every((one) => typeof one.value === 'number'), true);
  assert.equal(revenue[0].value, 1086181);
});

/* ── cash flow, and the capex that is not in it ─────────────────────── */

/** The documented Reliance cash flow, verbatim. */
const CASHFLOW = {
  data: {
    type: 'consolidated', units_in: 'crore',
    cash_flow: [
      { category: 'operating', history: [
        { value: 178703, period: 'Mar 2025', change: '+12.54%' },
        { value: 158788, period: 'Mar 2024' }, { value: 115032, period: 'Mar 2023' },
        { value: 110654, period: 'Mar 2022' },
      ] },
      { category: 'investing', history: [
        { value: -137535, period: 'Mar 2025' }, { value: -113581, period: 'Mar 2024' },
      ] },
      { category: 'financing', history: [{ value: -31891, period: 'Mar 2025' }] },
    ],
    full_statement: [
      { particular: 'Cash flow from Operations', history: [{ period: 'Mar 2025', value: 178703 }] },
      { particular: 'Cash flow from Investing', history: [{ period: 'Mar 2025', value: -137535 }] },
      { particular: 'Cash (End of the year)', history: [{ period: 'Mar 2025', value: 106502 }] },
    ],
  },
};

test('operating cash flow is served, and negatives survive the read', () => {
  const picked = statementFrom([['consolidated', CASHFLOW]], { rowsAt: (b) => b?.cash_flow });
  const cfo = operatingCashFlow(picked);
  assert.equal(cfo.history[0].value, 178703);
  assert.equal(cfo.from, 'category');
  // Investing is an outflow; the sign has to survive, because a lost minus
  // turns money leaving into money arriving.
  assert.equal(categoryHistory(picked.rows, 'investing')[0].value, -137535);
});

test('capex refuses rather than returning an empty history', () => {
  // The statement has no capex line on either the categories or the
  // breakdown. An empty array would be read downstream as no spending.
  const out = capexFrom();
  assert.equal(out.value, null);
  assert.equal(out.reason, 'CAPEX_NOT_IN_CASH_FLOW_STATEMENT');
  assert.equal(CAPEX_AVAILABLE_FROM_CASH_FLOW, false);
  assert.match(out.detail, /not a capex proxy/);
});

/* ── corporate actions, and the return that never happened ──────────── */

const ACTION = (name, date, extra = {}) => ({
  data: [{ name, expiry_date: date, amount: null, ratio: null, event_details: [], ...extra }],
});

test('a date in the documented format parses', () => {
  assert.equal(parseActionDate('14 Aug 2025'), Date.UTC(2025, 7, 14));
  assert.equal(parseActionDate('1 Mar 2026'), Date.UTC(2026, 2, 1));
  assert.equal(parseActionDate('not a date'), null);
  assert.equal(parseActionDate(null), null);
});

test('a bonus on its ex-date breaks the price and is flagged', () => {
  // A one-for-one bonus halves the quote overnight. Against an unadjusted
  // previous close the basket would read a 50% loss that did not happen.
  const now = Date.UTC(2026, 7, 14);
  const near = actionsNear(ACTION('Bonus', '14 Aug 2026', { ratio: '1:1' }), { now });
  assert.equal(near.priceBreak, true);
  assert.equal(near.reason, 'DILUTIVE_ACTION_ON_OR_NEAR_EX_DATE');
  assert.equal(near.actions[0].dilutive, true);
  assert.equal(near.actions[0].ratio, '1:1');
});

test('a split and a rights issue break the price the same way', () => {
  const now = Date.UTC(2026, 7, 14);
  assert.equal(actionsNear(ACTION('Split', '14 Aug 2026'), { now }).priceBreak, true);
  assert.equal(actionsNear(ACTION('Rights', '14 Aug 2026'), { now }).priceBreak, true);
});

test('a dividend is a real return to a holder and is not flagged', () => {
  // The price falls by the dividend, and the holder received it. That is a
  // return, not an artefact, and flagging it would drop a member for nothing.
  const now = Date.UTC(2026, 7, 14);
  const near = actionsNear(ACTION('Dividend', '14 Aug 2026', { amount: 5.5 }), { now });
  assert.equal(near.priceBreak, false);
  assert.equal(near.actions.length, 1);
  assert.equal(near.actions[0].dilutive, false);
});

test('an action outside the window does not flag anything', () => {
  const now = Date.UTC(2026, 7, 14);
  assert.equal(actionsNear(ACTION('Bonus', '20 Aug 2026'), { now }).priceBreak, false);
  assert.equal(actionsNear(ACTION('Bonus', '01 Jan 2020'), { now }).actions.length, 0);
});

test('the day either side is covered, because the ex-date is a boundary', () => {
  // Which side of midnight a feed adjusts on is not knowable from here, so
  // the window covers both.
  const now = Date.UTC(2026, 7, 14);
  assert.equal(actionsNear(ACTION('Bonus', '13 Aug 2026'), { now }).priceBreak, true);
  assert.equal(actionsNear(ACTION('Bonus', '15 Aug 2026'), { now }).priceBreak, true);
});
