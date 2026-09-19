import test from 'node:test';
import assert from 'node:assert/strict';
import { backtestInputs } from '../services/institutionalResearchLayerService.js';

/**
 * A Supabase query builder that records what was asked for.
 *
 * Enough of the surface to answer the three reads backtestInputs makes, and
 * nothing more. The point is to assert the shape of the holdings query: this
 * function used to read every position of every filing and sort in JavaScript,
 * and getting the order wrong now changes which ten positions the portfolio
 * holds rather than merely making it slow.
 */
function fakeClient({ managers, filings, holdingsByFiling, calls }) {
  return {
    from(table) {
      const q = { table, filters: {}, orders: [], ranges: [] };
      const builder = {
        select() { return builder; },
        eq(column, value) { q.filters[column] = value; return builder; },
        limit() { return builder; },
        order(column, options) { q.orders.push({ column, ascending: options?.ascending !== false }); return builder; },
        range(from, to) {
          q.ranges.push([from, to]);
          calls.push({ ...q, orders: [...q.orders] });
          const rows = holdingsByFiling[q.filters.filing_id] || [];
          return Promise.resolve({ data: rows.slice(from, to + 1), error: null });
        },
        then(resolve) {
          calls.push({ ...q, orders: [...q.orders] });
          if (table === 'institutional_managers') return resolve({ data: managers, error: null });
          if (table === 'institutional_filings') return resolve({ data: filings, error: null });
          return resolve({ data: [], error: null });
        },
      };
      return builder;
    },
  };
}

const manager = { id: 'm1', slug: 'acme-capital', display_name: 'Acme Capital' };
const filings = [
  { id: 'f1', manager_id: 'm1', report_date: '2026-06-30', filed_at: '2026-08-14T00:00:00Z', is_active: true },
];
const position = (n, value, over = {}) => ({ id: `h${n}`, filing_id: 'f1', ticker: `T${n}`, value_usd: value, put_call: null, ...over });

test('asks the database for the largest positions, not for all of them', async () => {
  // The 547-second read this replaces: every position of every filing, then a
  // JavaScript sort to keep ten.
  const calls = [];
  const holdings = Array.from({ length: 400 }, (_, i) => position(i, 1000 - i));
  await backtestInputs(fakeClient({ managers: [manager], filings, holdingsByFiling: { f1: holdings }, calls }), 'acme-capital', 4, { topN: 10 });

  const holdingCalls = calls.filter((c) => c.table === 'institutional_holdings');
  assert.equal(holdingCalls.length, 1, 'one request per filing, not one per thousand rows');
  assert.deepEqual(holdingCalls[0].orders, [
    { column: 'value_usd', ascending: false },
    { column: 'id', ascending: true },
  ], 'largest first, with a tie-break so paging has a total order');
});

test('returns the largest positions in order', async () => {
  const calls = [];
  const holdings = [position(1, 50), position(2, 900), position(3, 100), position(4, 700)];
  // Largest-first is the database's job here, so the fake returns them sorted.
  holdings.sort((a, b) => b.value_usd - a.value_usd);
  const { holdings: out } = await backtestInputs(
    fakeClient({ managers: [manager], filings, holdingsByFiling: { f1: holdings }, calls }), 'acme-capital', 4, { topN: 2 });
  assert.deepEqual(out.map((row) => row.ticker), ['T2', 'T4']);
});

test('keeps paging while puts and calls fill the top of the book', async () => {
  // The reason the filter stayed in JavaScript. A book whose largest
  // disclosures are options must still yield ten real positions, so the read
  // continues rather than returning short.
  const calls = [];
  const options = Array.from({ length: 250 }, (_, i) => position(`p${i}`, 10_000 - i, { put_call: 'Call' }));
  const real = Array.from({ length: 20 }, (_, i) => position(i, 500 - i));
  const { holdings: out } = await backtestInputs(
    fakeClient({ managers: [manager], filings, holdingsByFiling: { f1: [...options, ...real] }, calls }), 'acme-capital', 4, { topN: 10 });

  assert.equal(out.length, 10, 'ten real positions, not ten options');
  assert.ok(out.every((row) => !row.put_call), 'no option reached the portfolio');
  assert.ok(calls.filter((c) => c.table === 'institutional_holdings').length > 1, 'it paged past the options');
});

test('a position with no ticker is not a position', async () => {
  // It cannot be priced, so it cannot be held. It must not occupy one of the
  // ten slots either.
  const calls = [];
  const holdings = [position(1, 900, { ticker: null }), position(2, 800), position(3, 700, { ticker: '' }), position(4, 600)];
  const { holdings: out } = await backtestInputs(
    fakeClient({ managers: [manager], filings, holdingsByFiling: { f1: holdings }, calls }), 'acme-capital', 4, { topN: 2 });
  assert.deepEqual(out.map((row) => row.ticker), ['T2', 'T4']);
});

test('a filing with fewer positions than asked for returns what it has', async () => {
  const calls = [];
  const { holdings: out } = await backtestInputs(
    fakeClient({ managers: [manager], filings, holdingsByFiling: { f1: [position(1, 100)] }, calls }), 'acme-capital', 4, { topN: 10 });
  assert.equal(out.length, 1);
});

test('an unknown manager is refused rather than returning an empty book', async () => {
  // An empty book would backtest as a flat return, which is a number and
  // therefore worse than an error.
  const calls = [];
  await assert.rejects(
    () => backtestInputs(fakeClient({ managers: [], filings: [], holdingsByFiling: {}, calls }), 'nobody', 4, {}),
    /Tracked manager not found/,
  );
});
