/**
 * The dollars-vs-thousands rule, anchored on a real filing.
 *
 * Q4-2022 is the only quarter where keying on the report date and keying on the
 * filing date disagree, and it is the quarter two of the three code paths got
 * wrong. Berkshire's own filing settles it:
 *
 *   accession 0000950123-23-002585
 *   report 2022-12-31, accepted 2023-02-14T21:00:08Z
 *   value column sums to 299,007,622,119
 *
 * $299.0B matches the portfolio. Read as thousands it is $299 trillion.
 *
 *   node --test server/services/valueScale.test.js
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { stripCommentLines } from '../tests/stripComments.js';
import { valueScaleFor, filingDeadline, detectScaleMismatch, DOLLAR_RULE_DATE } from './valueScale.js';

test('Q4-2022 filed in February 2023 is whole dollars', () => {
  // The exact case. Keying on report_date gives 1000 and overstates by 1000x.
  const result = valueScaleFor({ acceptedAt: '2023-02-14T21:00:08.000Z', reportDate: '2022-12-31' });
  assert.equal(result.scale, 1);
  assert.match(result.basis, /filing date 2023-02-14/);
});

test('Q2-2022 filed in August 2022 is thousands', () => {
  const result = valueScaleFor({ acceptedAt: '2022-08-15T20:00:00.000Z', reportDate: '2022-06-30' });
  assert.equal(result.scale, 1000);
});

test('the rule turns on the filing date, never the quarter', () => {
  // Same quarter, two filing dates either side of the rule change.
  const before = valueScaleFor({ acceptedAt: '2022-12-30T20:00:00Z', reportDate: '2022-09-30' });
  const after = valueScaleFor({ acceptedAt: '2023-01-04T20:00:00Z', reportDate: '2022-09-30' });
  assert.equal(before.scale, 1000);
  assert.equal(after.scale, 1, 'an amendment to an old quarter filed after the rule change is in dollars');
});

test('the boundary date itself is already dollars', () => {
  assert.equal(valueScaleFor({ acceptedAt: `${DOLLAR_RULE_DATE}T14:00:00Z` }).scale, 1);
  assert.equal(valueScaleFor({ acceptedAt: '2023-01-02T14:00:00Z' }).scale, 1000);
});

test('filed_at is used when acceptance is absent', () => {
  assert.equal(valueScaleFor({ filedAt: '2023-02-14', reportDate: '2022-12-31' }).scale, 1);
});

test('with no filing date, the 45-day deadline is the proxy - and it is labelled one', () => {
  // The CMS path stamps acceptance as the moment of upload, so it cannot be
  // trusted as a filing date. The deadline is the best available substitute.
  assert.equal(filingDeadline('2022-12-31'), '2023-02-14');
  const q4 = valueScaleFor({ reportDate: '2022-12-31' });
  assert.equal(q4.scale, 1, 'Q4-2022 was due 2023-02-14, after the rule change');
  assert.match(q4.basis, /estimated/, 'an estimate must say it is one');

  const q2 = valueScaleFor({ reportDate: '2022-06-30' });
  assert.equal(q2.scale, 1000, 'Q2-2022 was due 2022-08-14, before the rule change');
});

test('a manager override wins over everything', () => {
  const result = valueScaleFor({ acceptedAt: '2023-02-14T21:00:00Z', override: 1000 });
  assert.equal(result.scale, 1000);
  assert.match(result.basis, /override/);
});

test('an unusable override is ignored rather than applied', () => {
  for (const override of [0, -1, 'lots', null, NaN]) {
    assert.equal(valueScaleFor({ acceptedAt: '2023-02-14T21:00:00Z', override }).scale, 1);
  }
});

test('with nothing to go on it falls back and says so', () => {
  const result = valueScaleFor({});
  assert.equal(result.scale, 1000);
  assert.match(result.basis, /no filing or report date/);
});

test('a malformed date is not treated as a filing date', () => {
  assert.match(valueScaleFor({ acceptedAt: 'sometime in February', reportDate: '2022-12-31' }).basis, /estimated/);
});

// ---------------------------------------------------------------------------
// The cross-check
// ---------------------------------------------------------------------------

test('values in thousands scaled as dollars are detected', () => {
  // 1,000,000 "dollars" over 5,000,000 shares is $0.20/share - not a real price.
  const rows = Array.from({ length: 10 }, () => ({ value_usd: 1_000_000, shares: 5_000_000 }));
  const mismatch = detectScaleMismatch(rows, 1);
  assert.ok(mismatch, 'a sub-dollar implied price should be flagged');
  assert.equal(mismatch.suspected, 1000);
});

test('a correctly scaled filing raises nothing', () => {
  // $150 a share.
  const rows = Array.from({ length: 10 }, () => ({ value_usd: 15_000_000, shares: 100_000 }));
  assert.equal(detectScaleMismatch(rows, 1), null);
});

test('too few rows to judge returns no opinion rather than a guess', () => {
  const rows = [{ value_usd: 1, shares: 1_000_000 }];
  assert.equal(detectScaleMismatch(rows, 1), null);
});

test('options positions are excluded from the cross-check', () => {
  const rows = Array.from({ length: 10 }, () => ({ value_usd: 1_000_000, shares: 5_000_000, put_call: 'Put' }));
  assert.equal(detectScaleMismatch(rows, 1), null, 'puts and calls distort the implied price');
});

// ---------------------------------------------------------------------------
// All three paths must share the one rule
// ---------------------------------------------------------------------------

test('no ingest path decides the value scale for itself', () => {
  // The defect was three independent decisions, two of them wrong. This fails
  // if a fourth appears, or if one of the three starts keying on report_date
  // again.
  const source = stripCommentLines(
    readFileSync(new URL('./institutionalHoldingsService.js', import.meta.url), 'utf8'));

  assert.equal(/POST_2022_VALUE_RULE_DATE/.test(source), false,
    'the local rule-date constant is back; the rule lives in valueScale.js');
  assert.equal(/report_date\s*<\s*[A-Z_]*RULE_DATE/.test(source), false,
    'a path is keying the scale to report_date again - that is the 1000x bug');

  const calls = source.match(/valueScaleFor\(/g) || [];
  assert.ok(calls.length >= 3,
    `expected all three ingest paths to call valueScaleFor, found ${calls.length}`);
});

test('the audit script never writes', () => {
  const source = readFileSync(new URL('../scripts/auditValueScale.mjs', import.meta.url), 'utf8');
  for (const write of ['.insert(', '.update(', '.upsert(', '.delete(']) {
    assert.equal(source.includes(write), false,
      `the value-scale audit calls ${write} - it is meant to measure, not repair`);
  }
});
