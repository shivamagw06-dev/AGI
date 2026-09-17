import test from 'node:test';
import assert from 'node:assert/strict';
import { cagr, categoryHistory, lineHistory, resolveRatioBasis, statementFrom } from './aiEnablersStatements.js';

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
