import test from 'node:test';
import assert from 'node:assert/strict';
import { detectScaleMismatch, resolveScale } from '../services/valueScale.js';

/**
 * Renaissance Technologies, Q3 2023, filed 2023-11-14 - ten months after the
 * whole-dollars rule took effect. Real figures from the filing.
 */
const renaissanceQ3_2023 = [
  { shares: 4_201_607, value_usd: 719_357 },   // Apple: $0.17 a share as filed
  { shares: 106_949, value_usd: 1_417 },
  { shares: 50_000, value_usd: 900 },
  { shares: 1_000_000, value_usd: 21_000 },
  { shares: 250_000, value_usd: 4_100 },
  { shares: 80_000, value_usd: 1_600 },
];

test('a filing that ignores the whole-dollars rule is corrected, not just flagged', () => {
  // 719,357 / 4,201,607 is $0.17. Times a thousand it is $171.21, which is
  // what Apple closed at on 2023-09-29. Storing the filed figure records a
  // $60bn book as $60m, and nothing downstream can see it: every position is
  // wrong by the same factor, so weights and shares still agree.
  const mismatch = detectScaleMismatch(renaissanceQ3_2023, 1);
  assert.equal(mismatch.suspected, 1000);

  const resolved = resolveScale({ scale: 1, basis: 'filing date' }, mismatch);
  assert.equal(resolved.scale, 1000);
  assert.equal(resolved.overridden, true);
  assert.match(resolved.basis, /implied price/);
});

test('a compliant filing is left alone', () => {
  // Renaissance's Q2 2026 table, same manager, filed in dollars: Apple at
  // 459,058,610 against 1,586,526 shares is $289.35.
  const compliant = [
    { shares: 1_586_526, value_usd: 459_058_610 },
    { shares: 100_000, value_usd: 25_000_000 },
    { shares: 500_000, value_usd: 60_000_000 },
    { shares: 20_000, value_usd: 3_000_000 },
    { shares: 750_000, value_usd: 90_000_000 },
    { shares: 40_000, value_usd: 6_000_000 },
  ];
  assert.equal(detectScaleMismatch(compliant, 1), null);
  const resolved = resolveScale({ scale: 1, basis: 'filing date' }, null);
  assert.equal(resolved.scale, 1);
  assert.equal(resolved.overridden, false);
});

test('the correction must land where a share can actually trade', () => {
  // The guard against trading one wrong answer for another. If multiplying by
  // a thousand produces a price no share trades at, the evidence does not
  // support the correction and the documented rule stands.
  const absurd = { suspected: 1000, applied: 1, median: 0.0000001 };
  const resolved = resolveScale({ scale: 1, basis: 'filing date' }, absurd);
  assert.equal(resolved.overridden, false, 'a correction to $0.0001 is not plausible');
  assert.equal(resolved.scale, 1);
});

test('a marginal reading stays a warning rather than an override', () => {
  // $0.80 a share is odd but a share can trade there. Only an untenable
  // reading is overridden; the rest is reported and left to a person.
  const marginal = { suspected: 1000, applied: 1, median: 0.8 };
  assert.equal(resolveScale({ scale: 1, basis: 'filing date' }, marginal).overridden, false);
});

test('the reverse error is corrected too', () => {
  // Thousands applied to a table already in dollars: implied prices in the
  // millions, corrected to something a share trades at.
  const mismatch = { suspected: 1, applied: 1000, median: 600_000 };
  const resolved = resolveScale({ scale: 1000, basis: 'filing date' }, mismatch);
  assert.equal(resolved.scale, 1);
  assert.equal(resolved.overridden, true);
});

test('Berkshire A shares do not trip the reverse guard', () => {
  // Class A trades above $700,000. A real price must not read as a scale error.
  const berkshire = Array.from({ length: 6 }, () => ({ shares: 100, value_usd: 74_000_000 }));
  assert.equal(detectScaleMismatch(berkshire, 1), null);
});

test('the basis records what the numbers showed, not just that it changed', () => {
  const mismatch = detectScaleMismatch(renaissanceQ3_2023, 1);
  const { basis } = resolveScale({ scale: 1, basis: 'filing date' }, mismatch);
  assert.match(basis, /filing's own figures/);
  assert.match(basis, /the filing date rule says 1/);
});
