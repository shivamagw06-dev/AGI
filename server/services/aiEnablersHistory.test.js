import test from 'node:test';
import assert from 'node:assert/strict';
import { closesFrom, dailyIndex, dilutiveExDates } from './aiEnablersHistory.js';

const m = (entries) => new Map(Object.entries(entries));
const bench = m({ '2026-09-16': 100, '2026-09-17': 100, '2026-09-18': 101, '2026-09-21': 102.01 });

test('a member enters at the close of its decision day and contributes from the next session', () => {
  const out = dailyIndex({
    members: [{ symbol: 'A', membershipStart: '2026-09-17' }, { symbol: 'B', membershipStart: '2026-09-18' }],
    closes: {
      A: m({ '2026-09-17': 100, '2026-09-18': 110, '2026-09-21': 110 }),
      B: m({ '2026-09-17': 100, '2026-09-18': 50, '2026-09-21': 60 }),
    },
    benchmark: bench,
  });
  assert.equal(out.base, '2026-09-17');
  // 18 Sep: only A (B was decided that day). +10%.
  assert.equal(out.points[1].basket, 110);
  assert.equal(out.points[1].members, 1);
  // 21 Sep: A flat, B +20%, equal weight: +10%.
  assert.equal(out.points[2].basket, 121);
  assert.equal(out.points[2].members, 2);
  // B's -50% on 18 Sep, before it was a member, never touches the basket.
  assert.equal(out.points[2].benchmark, 102.01);
});

test('nothing starts before the first decision date', () => {
  const out = dailyIndex({
    members: [{ symbol: 'A', membershipStart: '2026-09-17' }],
    closes: { A: m({ '2026-09-16': 50, '2026-09-17': 100, '2026-09-18': 100 }) },
    benchmark: bench,
  });
  assert.equal(out.points[0].date, '2026-09-17');
  assert.equal(out.points[0].basket, 100);
});

test('a member going ex a bonus is left out that session, not counted as a crash', () => {
  const out = dailyIndex({
    members: [{ symbol: 'A', membershipStart: '2026-09-17' }, { symbol: 'B', membershipStart: '2026-09-17' }],
    closes: { A: m({ '2026-09-17': 100, '2026-09-18': 110 }), B: m({ '2026-09-17': 100, '2026-09-18': 50 }) },
    benchmark: bench,
    exDates: { B: new Set(['2026-09-18']) },
  });
  assert.equal(out.points[1].basket, 110);
  assert.deepEqual(out.points[1].excluded, ['B']);
});

test('a missing close is reported, and the basket averages the members that have one', () => {
  const out = dailyIndex({
    members: [{ symbol: 'A', membershipStart: '2026-09-17' }, { symbol: 'B', membershipStart: '2026-09-17' }],
    closes: { A: m({ '2026-09-17': 100, '2026-09-18': 104 }), B: m({ '2026-09-17': 100 }) },
    benchmark: bench,
  });
  assert.equal(out.points[1].basket, 104);
  assert.deepEqual(out.points[1].missing, ['B']);
});

test('no benchmark close on the base date means no series, not a guessed one', () => {
  const out = dailyIndex({
    members: [{ symbol: 'A', membershipStart: '2026-09-19' }],
    closes: {}, benchmark: bench,
  });
  assert.equal(out.reason, 'NO_BENCHMARK_CLOSE_ON_BASE_DATE');
  assert.deepEqual(out.points, []);
});

test('candles and corporate actions are read into dates', () => {
  const closes = closesFrom({ data: { candles: [['2026-09-18T00:00:00+05:30', 1, 1, 1, 105, 1, 0], ['2026-09-17T00:00:00+05:30', 1, 1, 1, 100, 1, 0]] } });
  assert.deepEqual([...closes.entries()], [['2026-09-17', 100], ['2026-09-18', 105]]);
  const ex = dilutiveExDates({ data: [{ name: 'Bonus 1:1', expiry_date: '18 Sep 2026' }, { name: 'Dividend', expiry_date: '18 Sep 2026' }] });
  assert.deepEqual([...ex], ['2026-09-18']);
});
