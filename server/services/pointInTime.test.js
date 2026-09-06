/**
 * Point-in-time rules, tested against the exact failures an adversarial audit
 * confirmed in the previous implementation. Every case here is one that used
 * to produce a number flattering to the manager.
 *
 *   node --test server/services/pointInTime.test.js
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  easternParts, firstTradableSession, sessionsFromPrices, closeOn,
  periodReturn, benchmarkReturn, orderByAcceptance,
} from './pointInTime.js';

// A real February week: the 17th is Presidents' Day, so there is no session.
const SESSIONS = [
  '2024-02-09', '2024-02-12', '2024-02-13', '2024-02-14', '2024-02-15',
  '2024-02-16', '2024-02-20', '2024-02-21',
];

// ---------------------------------------------------------------------------
// Time zone
// ---------------------------------------------------------------------------

test('acceptance timestamps are read in US Eastern, not UTC', () => {
  // 21:05Z in November is 16:05 ET the same day - after the close.
  assert.deepEqual(easternParts('2025-11-14T21:05:03.000Z'), { date: '2025-11-14', hour: 16, minute: 5 });
  // The same wall clock in August is 20:05Z, because of daylight time.
  assert.deepEqual(easternParts('2026-08-14T20:05:04.000Z'), { date: '2026-08-14', hour: 16, minute: 5 });
});

test('a late-evening UTC instant is still the same Eastern day', () => {
  // The old code truncated in UTC, so this read as 2024-02-15 and the boundary
  // it enforced was 19:00 ET, not the 16:00 ET close.
  assert.equal(easternParts('2024-02-14T23:30:00.000Z').date, '2024-02-14');
  assert.equal(easternParts('2024-02-15T02:30:00.000Z').date, '2024-02-14');
});

// ---------------------------------------------------------------------------
// Entry timing - the confirmed critical defect
// ---------------------------------------------------------------------------

test('a filing accepted after the close enters on the NEXT session', () => {
  // 16:05 ET on the 14th. The old code entered at the 14th's close, a price
  // struck five minutes before the filing existed.
  assert.equal(firstTradableSession('2024-02-14T21:05:00.000Z', SESSIONS), '2024-02-15');
});

test('a filing accepted during the session still does not use that session', () => {
  // Conservative by design: the position is only known once public, and the
  // same session's close is what the look-ahead rule exists to exclude.
  assert.equal(firstTradableSession('2024-02-14T15:00:00.000Z', SESSIONS), '2024-02-15');
});

test('a Friday-evening filing enters on Monday, not Saturday', () => {
  // 2024-02-16 is a Friday; the 19th is Presidents' Day, so the next session
  // is the 20th. A calendar +1 would have produced a date with no market.
  assert.equal(firstTradableSession('2024-02-16T22:00:00.000Z', SESSIONS), '2024-02-20');
});

test('a filing after the last known session has no entry rather than a guess', () => {
  assert.equal(firstTradableSession('2024-03-01T21:00:00.000Z', SESSIONS), null);
});

test('the session calendar comes from observed prices, skipping holidays and blanks', () => {
  const sessions = sessionsFromPrices([
    { price_date: '2024-02-14', adjusted_close: 10 },
    { price_date: '2024-02-16', adjusted_close: 11 },
    { price_date: '2024-02-15', adjusted_close: null },   // no print, not a session
    { price_date: '2024-02-14', adjusted_close: 10 },     // duplicate
  ]);
  assert.deepEqual(sessions, ['2024-02-14', '2024-02-16']);
});

// ---------------------------------------------------------------------------
// Price lookup
// ---------------------------------------------------------------------------

test('a price is taken from the exact session or not at all', () => {
  const series = [
    { price_date: '2024-02-14', adjusted_close: 100 },
    { price_date: '2024-02-20', adjusted_close: 110 },
  ];
  assert.equal(closeOn(series, '2024-02-14'), 100);
  // The old `>=` lookup returned the 20th here, valuing a position on a price
  // from six days later without saying so.
  assert.equal(closeOn(series, '2024-02-15'), null);
});

// ---------------------------------------------------------------------------
// Survivorship - four independent lenses confirmed this one
// ---------------------------------------------------------------------------

const PRICES = new Map([
  ['AAPL', [{ price_date: '2024-02-15', adjusted_close: 100 }, { price_date: '2024-05-15', adjusted_close: 110 }]],
  ['MSFT', [{ price_date: '2024-02-15', adjusted_close: 200 }, { price_date: '2024-05-15', adjusted_close: 220 }]],
  // Delisted mid-period: priced at entry, gone at exit.
  ['DEAD', [{ price_date: '2024-02-15', adjusted_close: 50 }]],
]);

test('an unpriced position is excluded and named, not silently dropped', () => {
  const result = periodReturn({
    positions: [
      { ticker: 'AAPL', value_usd: 500 },
      { ticker: 'MSFT', value_usd: 300 },
      { ticker: 'DEAD', value_usd: 200 },
    ],
    prices: PRICES,
    entryDate: '2024-02-15',
    exitDate: '2024-05-15',
  });

  assert.equal(result.priced, 2);
  assert.equal(result.excluded.length, 1);
  assert.equal(result.excluded[0].key, 'DEAD');
  assert.equal(result.excluded[0].reason, 'no price at exit');
  assert.ok(Math.abs(result.coverage - 0.8) < 1e-9, 'coverage must state the measured share');
});

test('survivors are NOT renormalized to 100%', () => {
  // The old code returned result/coverage, which re-weights the priced names
  // to the full portfolio and presents a partial measurement as a complete one.
  // AAPL +10% at 50%, MSFT +10% at 30%: measured contribution is 8%, not 10%.
  const result = periodReturn({
    positions: [
      { ticker: 'AAPL', value_usd: 500 },
      { ticker: 'MSFT', value_usd: 300 },
      { ticker: 'DEAD', value_usd: 200 },
    ],
    prices: PRICES,
    entryDate: '2024-02-15',
    exitDate: '2024-05-15',
  });
  assert.ok(Math.abs(result.value - 0.08) < 1e-9,
    `expected 8% measured, got ${result.value} - the survivors were renormalized`);
});

test('a period with nothing priced returns null rather than zero', () => {
  const result = periodReturn({
    positions: [{ ticker: 'NOPE', value_usd: 100 }],
    prices: PRICES,
    entryDate: '2024-02-15',
    exitDate: '2024-05-15',
  });
  assert.equal(result.value, null);
  assert.equal(result.coverage, 0);
});

// ---------------------------------------------------------------------------
// Benchmark - a missing benchmark must invalidate, not win
// ---------------------------------------------------------------------------

test('a missing benchmark price yields null, never a 0% benchmark', () => {
  // This is the defect that turned an entire strategy return into "alpha":
  // absent SPY compounded to 0 and excess_vs_spy became the whole return.
  assert.equal(benchmarkReturn([], '2024-02-15', '2024-05-15'), null);
  assert.equal(benchmarkReturn([{ price_date: '2024-02-15', adjusted_close: 500 }], '2024-02-15', '2024-05-15'), null);
});

test('a benchmark priced at both ends returns its real move', () => {
  const spy = [
    { price_date: '2024-02-15', adjusted_close: 500 },
    { price_date: '2024-05-15', adjusted_close: 525 },
  ];
  assert.ok(Math.abs(benchmarkReturn(spy, '2024-02-15', '2024-05-15') - 0.05) < 1e-9);
});

// ---------------------------------------------------------------------------
// Amendments breaking the period chain
// ---------------------------------------------------------------------------

test('filings are ordered by when the market learned of them', () => {
  // A Q1 amendment accepted in November lands after Q2 and Q3 originals.
  // Ordering by report_date put it between Q1 and Q2, producing a period whose
  // exit preceded its entry.
  const ordered = orderByAcceptance([
    { report_date: '2024-03-31', accepted_at: '2024-05-15T20:00:00Z', tag: 'q1' },
    { report_date: '2024-06-30', accepted_at: '2024-08-14T20:00:00Z', tag: 'q2' },
    { report_date: '2024-03-31', accepted_at: '2024-11-08T20:00:00Z', tag: 'q1-amended' },
    { report_date: '2024-09-30', accepted_at: '2024-11-14T20:00:00Z', tag: 'q3' },
  ]);
  assert.deepEqual(ordered.map((f) => f.tag), ['q1', 'q2', 'q1-amended', 'q3']);
});

test('a filing with no acceptance time at all is dropped from the chain', () => {
  const ordered = orderByAcceptance([
    { tag: 'undated' },
    { tag: 'dated', accepted_at: '2024-05-15T20:00:00Z' },
  ]);
  assert.deepEqual(ordered.map((f) => f.tag), ['dated']);
});

// ---------------------------------------------------------------------------
// The defects must not be able to come back
// ---------------------------------------------------------------------------

/**
 * Comments are stripped first. The service carries a note explaining that the
 * `price_date >= date` lookup was removed, and a guard that cannot tell a
 * warning from the thing it warns about is a guard that gets deleted.
 */
const withoutComments = (source) => source
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/(^|[^:])\/\/.*$/gm, '$1');

test('the backtest no longer contains a same-session price lookup', () => {
  const source = withoutComments(
    readFileSync(new URL('./institutionalResearchLayerService.js', import.meta.url), 'utf8'));
  assert.equal(/price_date\s*>=\s*date/.test(source), false,
    'the `price_date >= date` lookup is back - that selects the acceptance day\'s own close');
  assert.equal(/result\s*\/\s*coverage/.test(source), false,
    'survivors are being renormalized to 100% again');
  assert.equal(/no_look_ahead/.test(source), false,
    'the no-look-ahead attestation is back; it must only return with a test proving it');
});

test('the backtest derives its dates through the point-in-time rules', () => {
  const source = readFileSync(new URL('./institutionalResearchLayerService.js', import.meta.url), 'utf8');
  for (const symbol of ['firstTradableSession', 'benchmarkReturn', 'orderByAcceptance']) {
    assert.match(source, new RegExp(`\\b${symbol}\\(`), `the backtest no longer calls ${symbol}`);
  }
});

test('a run cannot be reported as calculated while its benchmark is missing', () => {
  const source = readFileSync(new URL('./institutionalResearchLayerService.js', import.meta.url), 'utf8');
  const gate = /const status = [^;]+;/.exec(source)?.[0] || '';
  assert.match(gate, /benchmarkComplete/,
    'the calculated gate does not require a complete benchmark, so a missing SPY becomes 0% and the whole return becomes alpha');
});
