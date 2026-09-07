/**
 * Point-in-time identifier resolution.
 *
 * Resolution used to order a CUSIP's mappings by valid_from descending and keep
 * the first, so the newest mapping was applied to every filing however old. A
 * CUSIP reassigned in 2025 relabelled a 2023 holding as whatever it means now.
 *
 *   node --test server/services/securityIdentity.test.js
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { mappingAsOf, securityKeyAsOf, resolveAsOf, cleanIdentifier } from './securityIdentity.js';

// A CUSIP genuinely reassigned: one issuer until 2024, another after.
const REASSIGNED = [
  { cusip: '12345AB01', ticker: 'OLDCO', issuer_name: 'OLD COMPANY INC',
    security_key: 'KEY-OLD', valid_from: '2015-01-01', valid_to: '2024-06-30' },
  { cusip: '12345AB01', ticker: 'NEWCO', issuer_name: 'NEW COMPANY PLC',
    security_key: 'KEY-NEW', valid_from: '2024-06-30', valid_to: null },
];

test('a filing gets the mapping that applied when it was filed', () => {
  assert.equal(mappingAsOf(REASSIGNED, '2023-03-31').ticker, 'OLDCO');
  assert.equal(mappingAsOf(REASSIGNED, '2025-03-31').ticker, 'NEWCO');
});

test('the newest mapping is not applied to an older filing', () => {
  // The defect, stated directly: taking the newest row would return NEWCO here.
  const resolved = mappingAsOf(REASSIGNED, '2020-12-31');
  assert.equal(resolved.ticker, 'OLDCO');
  assert.equal(resolved.security_key, 'KEY-OLD');
});

test('valid_to is exclusive, so a mapping ending on the report date has stopped', () => {
  assert.equal(mappingAsOf(REASSIGNED, '2024-06-30').ticker, 'NEWCO');
  assert.equal(mappingAsOf(REASSIGNED, '2024-06-29').ticker, 'OLDCO');
});

test('a mapping that has expired does not apply, even with nothing to replace it', () => {
  // Isolates valid_to. In the reassignment fixture the later row's valid_from
  // filters it out anyway, so ignoring valid_to changed nothing and the test
  // passed while asserting nothing. Here the mapping simply ended - the
  // security was delisted, or the CUSIP retired - and no row succeeds it.
  const expired = [
    { cusip: 'Z', ticker: 'GONE', issuer_name: 'DELISTED CO',
      security_key: 'KEY-GONE', valid_from: '2015-01-01', valid_to: '2020-12-31' },
  ];
  assert.equal(mappingAsOf(expired, '2019-06-30').ticker, 'GONE', 'in force before it ended');
  assert.equal(mappingAsOf(expired, '2023-06-30'), null, 'an expired mapping must not be applied');
  assert.equal(resolveAsOf(expired, ['Z'], '2023-06-30').has('Z'), false);
});

test('a date before any mapping resolves to nothing, not to the earliest', () => {
  // An unmapped holding is visibly incomplete. A confidently mislabelled one is
  // not, and it propagates into consensus, sector weights and prices.
  assert.equal(mappingAsOf(REASSIGNED, '2010-01-01'), null);
});

test('a manually verified mapping outranks an automatic one on the same day', () => {
  const rows = [
    { cusip: 'X', ticker: 'AUTO', valid_from: '2024-01-01', valid_to: null, source: 'openfigi', manually_verified: false },
    { cusip: 'X', ticker: 'CHECKED', valid_from: '2024-01-01', valid_to: null, source: 'manual', manually_verified: true },
  ];
  assert.equal(mappingAsOf(rows, '2025-01-01').ticker, 'CHECKED');
});

test('a later start wins over an earlier one that is still open', () => {
  const rows = [
    { cusip: 'X', ticker: 'EARLY', valid_from: '2020-01-01', valid_to: null },
    { cusip: 'X', ticker: 'LATER', valid_from: '2023-01-01', valid_to: null },
  ];
  assert.equal(mappingAsOf(rows, '2024-01-01').ticker, 'LATER');
  assert.equal(mappingAsOf(rows, '2021-01-01').ticker, 'EARLY');
});

// ---------------------------------------------------------------------------
// The canonical key
// ---------------------------------------------------------------------------

test('the canonical key follows the mapping in force, not the CUSIP', () => {
  assert.equal(securityKeyAsOf(REASSIGNED, '2023-03-31', '12345AB01'), 'KEY-OLD');
  assert.equal(securityKeyAsOf(REASSIGNED, '2025-03-31', '12345AB01'), 'KEY-NEW');
});

test('an unmapped security is its own key rather than nothing', () => {
  // Bootstrap identity: aggregation still groups something sensible for a
  // security nobody has mapped yet.
  assert.equal(securityKeyAsOf([], '2025-03-31', '037833100'), '037833100');
  assert.equal(securityKeyAsOf([], '2025-03-31', ' 037833100 '), '037833100');
});

test('two CUSIPs can share one key once merged', () => {
  // Alphabet A and C, or an ordinary line and its ADR: different CUSIPs, one
  // issuer. This is what lets the product aggregate them together.
  const rows = [
    { cusip: '02079K305', ticker: 'GOOGL', security_key: 'ALPHABET', valid_from: '2015-01-01', valid_to: null },
    { cusip: '02079K107', ticker: 'GOOG',  security_key: 'ALPHABET', valid_from: '2015-01-01', valid_to: null },
  ];
  const resolved = resolveAsOf(rows, ['02079K305', '02079K107'], '2026-06-30');
  assert.equal(resolved.get('02079K305').security_key, 'ALPHABET');
  assert.equal(resolved.get('02079K107').security_key, 'ALPHABET');
  assert.notEqual(resolved.get('02079K305').ticker, resolved.get('02079K107').ticker);
});

// ---------------------------------------------------------------------------
// Bulk resolution
// ---------------------------------------------------------------------------

test('a CUSIP with no mapping for the date is absent, not guessed', () => {
  const resolved = resolveAsOf(REASSIGNED, ['12345AB01', '99999ZZ99'], '2023-03-31');
  assert.equal(resolved.get('12345AB01').ticker, 'OLDCO');
  assert.equal(resolved.has('99999ZZ99'), false, 'an unknown CUSIP must not appear at all');
});

test('resolution is case and whitespace insensitive', () => {
  const resolved = resolveAsOf(REASSIGNED, [' 12345ab01 '], '2023-03-31');
  assert.equal(resolved.get('12345AB01').ticker, 'OLDCO');
  assert.equal(cleanIdentifier(' aapl '), 'AAPL');
  assert.equal(cleanIdentifier(''), null);
});

test('the old newest-wins resolution is gone from the service', () => {
  const src = readFileSync(new URL('./institutionalHoldingsService.js', import.meta.url), 'utf8');
  const fn = /async function mappingsFor[\s\S]*?\n}/.exec(src)?.[0];
  assert.ok(fn, 'mappingsFor is gone');
  assert.equal(/for \(const row of rows\) if \(!map\.has\(row\.cusip\)\) map\.set/.test(fn), false,
    'the newest-mapping-wins loop is back, which relabels old filings with current identifiers');
  assert.match(fn, /asOf|resolveAsOf/,
    'resolution must take the filing date into account');
});
