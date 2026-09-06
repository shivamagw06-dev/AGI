/**
 * What a looked-up identifier may claim, and which ones to look up first.
 *
 *   node --test server/services/identifierBackfill.test.js
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { mappingFromLookup, rankUnmapped, earliestObservation, coverage } from './identifierBackfill.js';

test('a looked-up mapping claims from the first date the CUSIP was seen', () => {
  // Not from 1900. OpenFIGI answers what a CUSIP maps to now; the interval it
  // is entitled to is bounded by evidence that the CUSIP existed.
  const row = mappingFromLookup({
    cusip: '037833100', ticker: 'aapl', issuerName: 'APPLE INC', observedFrom: '2019-03-31',
  });
  assert.equal(row.valid_from, '2019-03-31');
  assert.equal(row.ticker, 'AAPL', 'tickers are stored uppercase');
  assert.equal(row.valid_to, null);
  assert.equal(row.manually_verified, false, 'a vendor answer is not a verified one');
  assert.equal(row.security_key, '037833100', 'a security is its own key until merged');
});

test('the 1900 claim is not producible', () => {
  // The defect stated as a test: nothing this builder returns may reach back
  // before the evidence for it.
  for (const observedFrom of ['2015-06-30', '2024-12-31']) {
    assert.equal(mappingFromLookup({ cusip: 'X', ticker: 'T', observedFrom }).valid_from, observedFrom);
  }
});

test('nothing is claimed without a ticker or without an observation', () => {
  assert.equal(mappingFromLookup({ cusip: 'X', ticker: '', observedFrom: '2020-01-01' }), null);
  assert.equal(mappingFromLookup({ cusip: '', ticker: 'T', observedFrom: '2020-01-01' }), null);
  assert.equal(mappingFromLookup({ cusip: 'X', ticker: 'T', observedFrom: null }), null);
  assert.equal(mappingFromLookup({ cusip: 'X', ticker: 'T', observedFrom: 'sometime' }), null);
});

test('the earliest observation is the earliest, not the first encountered', () => {
  assert.equal(earliestObservation([
    { report_date: '2024-06-30' }, { report_date: '2019-03-31' }, { report_date: '2022-12-31' },
  ]), '2019-03-31');
  assert.equal(earliestObservation([{ report_date: 'rubbish' }]), null);
  assert.equal(earliestObservation([]), null);
});

// ---------------------------------------------------------------------------
// Which to resolve first
// ---------------------------------------------------------------------------

const UNMAPPED = [
  { cusip: 'BIG', issuer_name: 'BIG CO',   value_usd: 900_000_000, report_date: '2024-03-31' },
  { cusip: 'BIG', issuer_name: 'BIG CO',   value_usd: 800_000_000, report_date: '2021-06-30' },
  { cusip: 'WIDE', issuer_name: 'WIDE CO', value_usd: 100_000_000, report_date: '2023-03-31' },
  { cusip: 'WIDE', issuer_name: 'WIDE CO', value_usd: 100_000_000, report_date: '2023-06-30' },
  { cusip: 'WIDE', issuer_name: 'WIDE CO', value_usd: 100_000_000, report_date: '2023-09-30' },
  { cusip: 'TINY', issuer_name: 'TINY CO', value_usd: 5_000,       report_date: '2024-03-31' },
];

test('the largest disclosed value is resolved first', () => {
  // Roughly ninety per cent of rows are unmapped and a rate-limited vendor
  // cannot take them all at once, so each run should close the gap where it
  // changes the most numbers.
  const ranked = rankUnmapped(UNMAPPED);
  assert.equal(ranked[0].cusip, 'BIG');
  assert.equal(ranked[0].value, 1_700_000_000, 'value is summed across observations');
  assert.equal(ranked.at(-1).cusip, 'TINY');
});

test('each ranked entry carries the earliest date it was seen', () => {
  const ranked = rankUnmapped(UNMAPPED);
  const big = ranked.find((r) => r.cusip === 'BIG');
  assert.equal(big.observed_from, '2021-06-30', 'the interval must be anchored to the earliest sighting');
  assert.equal(big.observations, 2);
});

test('breadth breaks a tie on value', () => {
  const rows = [
    { cusip: 'ONE', value_usd: 300, report_date: '2024-03-31' },
    { cusip: 'MANY', value_usd: 100, report_date: '2024-03-31' },
    { cusip: 'MANY', value_usd: 100, report_date: '2024-06-30' },
    { cusip: 'MANY', value_usd: 100, report_date: '2024-09-30' },
  ];
  const ranked = rankUnmapped(rows);
  assert.equal(ranked[0].cusip, 'MANY', 'equal value, more managers reporting it');
});

test('the limit is honoured', () => {
  assert.equal(rankUnmapped(UNMAPPED, 2).length, 2);
});

// ---------------------------------------------------------------------------
// Coverage as a quotable figure
// ---------------------------------------------------------------------------

test('coverage is a measurement, not an impression', () => {
  assert.deepEqual(coverage({ total: 561209, mapped: 52000 }), {
    total_rows: 561209, mapped_rows: 52000, unmapped_rows: 509209, mapped_pct: 9.27,
  });
  assert.equal(coverage({ total: 0, mapped: 0 }).mapped_pct, 0, 'an empty table is not 100% covered');
});

test('the inline enrichment no longer writes a 1900 interval either', () => {
  const src = readFileSync(new URL('./institutionalHoldingsService.js', import.meta.url), 'utf8');
  assert.equal(/valid_from: '1900-01-01'/.test(src), false,
    "a mapping claiming validity from 1900 is back; point-in-time resolution will apply today's ticker to every filing ever made");
});

test('a manual mapping is scoped to its interval, not stamped on every filing', () => {
  // saveSecurityMapping used to set the ticker on every holding for a CUSIP
  // regardless of date. That is the same error as resolving with the newest
  // mapping: it relabels filings the mapping says nothing about.
  const src = readFileSync(new URL('./institutionalHoldingsService.js', import.meta.url), 'utf8');
  const fn = /export async function saveSecurityMapping[\s\S]*?\n}/.exec(src)?.[0];
  assert.ok(fn, 'saveSecurityMapping is gone');
  assert.match(fn, /gte\('report_date', from\)/,
    'the denormalised update must start where the mapping starts');
  assert.equal(/update\(\{ ticker: cleanTicker \}\)\.eq\('cusip', cleanCusip\);/.test(fn), false,
    'the unscoped blanket update is back');
  assert.match(fn, /order\('report_date', \{ ascending: true \}\)/,
    'the interval must default to the earliest observation, not to 1900');
});

// ---------------------------------------------------------------------------
// The runner
// ---------------------------------------------------------------------------

test('the backfill writes nothing unless asked', () => {
  // A bulk write of thousands of identifier mappings deserves to be read
  // first, the same way the amendment repair does.
  const script = readFileSync(new URL('../scripts/backfillIdentifiers.mjs', import.meta.url), 'utf8');
  assert.match(script, /const APPLY = args\.includes\('--apply'\)/,
    'writing must be opt-in');
  assert.match(script, /nothing will be written/,
    'a dry run must say so plainly');

  const svc = readFileSync(new URL('./institutionalHoldingsService.js', import.meta.url), 'utf8');
  const fn = /export async function runIdentifierBackfill[\s\S]*?\n}/.exec(svc)?.[0];
  assert.ok(fn, 'runIdentifierBackfill is gone');
  // The anchor must be asserted before slicing on it. A first version did not:
  // when the mutation deleted `if (!apply)`, indexOf returned -1, the slice came
  // back empty, and "no write call in an empty string" passed trivially.
  const guardAt = fn.indexOf('if (!apply)');
  assert.notEqual(guardAt, -1, 'the dry-run guard is gone, so every run writes');
  const dryBranch = fn.slice(guardAt, fn.indexOf('const outcome'));
  assert.ok(dryBranch.length > 40, 'the dry-run branch is empty; the slice anchors have moved');
  assert.equal(/enrichSecurityIdentifiers/.test(dryBranch), false,
    'the dry-run branch must not call the routine that writes');
});

test('the backfill reports coverage either side of itself', () => {
  const svc = readFileSync(new URL('./institutionalHoldingsService.js', import.meta.url), 'utf8');
  const fn = /export async function runIdentifierBackfill[\s\S]*?\n}/.exec(svc)?.[0];
  assert.match(fn, /coverage_before/, 'a claim about coverage must be traceable to a measurement');
  assert.match(fn, /coverage_after/);
  assert.match(fn, /const before = await measure\(\)/,
    'the before measurement must be taken before anything is written');
});

test('the runner refuses to start without credentials', () => {
  const script = readFileSync(new URL('../scripts/backfillIdentifiers.mjs', import.meta.url), 'utf8');
  const check = script.indexOf('SUPABASE_SERVICE_ROLE_KEY');
  const work = script.indexOf('await runIdentifierBackfill');
  assert.ok(check !== -1 && check < work,
    'credentials must be checked before any vendor call, or a config error spends the rate budget');
  assert.match(script, /process\.exit\(78\)/, 'a configuration failure should be distinguishable from a data one');
});

test('the limit is clamped', () => {
  const script = readFileSync(new URL('../scripts/backfillIdentifiers.mjs', import.meta.url), 'utf8');
  assert.match(script, /Math\.min\(Math\.max\(Number\(flag\('limit'/,
    'an unbounded limit would page the whole holdings table into memory');
});
