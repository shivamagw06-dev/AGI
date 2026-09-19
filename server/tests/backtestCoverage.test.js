import test from 'node:test';
import assert from 'node:assert/strict';
import { coverageProfile, backtestBlockers } from '../services/backtestCoverage.js';

const good = Array.from({ length: 11 }, (_, i) => ({ report_date: `2024-${String(i + 1).padStart(2, '0')}-30`, price_coverage: 0.98 }));

test('one badly covered period is not averaged away', () => {
  // The defect. A compounded return multiplies every period, so a quarter at
  // 20% coverage - four fifths of the book assumed flat - carries its error
  // into the product and every period after it. Averaged against eleven good
  // quarters it cleared a 70% floor comfortably.
  const periods = [...good, { report_date: '2024-12-31', price_coverage: 0.20 }];
  const profile = coverageProfile(periods);
  assert.ok(profile.average > 0.9, 'the mean looks healthy');
  assert.equal(profile.worst, 0.20);
  assert.equal(profile.worstPeriod, '2024-12-31');

  const blockers = backtestBlockers(profile, { periods: periods.length, benchmarkComplete: true });
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /2024-12-31/);
  assert.match(blockers[0], /20\.0%/);
});

test('a bad period hidden by many good ones is still caught', () => {
  // The case the gate exists for, and the one an average cannot see. Twenty
  // quarters at 99% and one at 50% average to 96.7% - clearing a 95% floor -
  // while half of one quarter's book was assumed flat and that error carries
  // through every period the return compounds over afterwards.
  const periods = [
    ...Array.from({ length: 20 }, (_, i) => ({ report_date: `2023-Q${i}`, price_coverage: 0.99 })),
    { report_date: '2025-06-30', price_coverage: 0.50 },
  ];
  const profile = coverageProfile(periods);
  assert.ok(profile.average > 0.95, `average ${profile.average.toFixed(3)} clears the floor`);
  assert.equal(profile.worst, 0.50);

  const blockers = backtestBlockers(profile, { periods: periods.length, benchmarkComplete: true });
  assert.equal(blockers.length, 1, 'gating on the average would report this run as calculated');
  assert.match(blockers[0], /2025-06-30/);
});

test('a run covered throughout is reportable', () => {
  const profile = coverageProfile(good);
  assert.deepEqual(backtestBlockers(profile, { periods: good.length, benchmarkComplete: true }), []);
});

test('the floor matches the screener, not the old 70%', () => {
  // Both surfaces answer "can this manager's performance be stated", and two
  // bars for one question is how one of them ends up wrong.
  const periods = good.map((row) => ({ ...row, price_coverage: 0.85 }));
  const blockers = backtestBlockers(coverageProfile(periods), { periods: periods.length, benchmarkComplete: true });
  assert.equal(blockers.length, 1, '85% cleared the old 70% floor and fails the 95% one');
  assert.match(blockers[0], /95% floor/);
});

test('every blocker is reported, not just the first', () => {
  // An operator fixing one only to meet the next learns the state one round
  // trip at a time.
  const profile = coverageProfile([{ report_date: '2024-03-31', price_coverage: 0.3 }]);
  const blockers = backtestBlockers(profile, { periods: 1, benchmarkComplete: false, skipped: ['2024-06-30'] });
  assert.equal(blockers.length, 4);
  assert.ok(blockers.some((b) => /1 period\(s\) could not be evaluated/.test(b)));
  assert.ok(blockers.some((b) => /at least 3 are required/.test(b)));
  assert.ok(blockers.some((b) => /below the 95% floor/.test(b)));
  assert.ok(blockers.some((b) => /benchmark is missing/.test(b)));
});

test('a run with no priced period says so rather than reporting zero coverage', () => {
  const profile = coverageProfile([]);
  assert.equal(profile.periods, 0);
  const blockers = backtestBlockers(profile, { periods: 0, benchmarkComplete: true });
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /No period could be priced/);
});

test('the average is still reported, because it answers a different question', () => {
  const profile = coverageProfile([...good, { report_date: '2024-12-31', price_coverage: 0.2 }]);
  assert.ok(profile.average > 0.9 && profile.worst === 0.2, 'both are kept');
});

test('a non-numeric coverage is not counted as zero', () => {
  // Treating a missing figure as zero coverage would block a run for a period
  // that was never measured rather than badly measured.
  const profile = coverageProfile([{ price_coverage: 0.99 }, { price_coverage: null }, {}]);
  assert.equal(profile.periods, 1);
  assert.equal(profile.worst, 0.99);
});
