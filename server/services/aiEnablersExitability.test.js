import test from 'node:test';
import assert from 'node:assert/strict';
import { executableFor, minimumAdvt, normalAdvt, sizePositions } from './aiEnablersExitability.js';

const CR = 1e7;

/** The seven, at their measured median daily turnover. */
const MEMBERS = [
  { symbol: 'NETWEB', medianDailyTurnover: 593.04 * CR },
  { symbol: 'ADANIENT', medianDailyTurnover: 479.47 * CR },
  { symbol: 'POWERINDIA', medianDailyTurnover: 402.95 * CR },
  { symbol: 'KAYNES', medianDailyTurnover: 396.47 * CR },
  { symbol: 'CGPOWER', medianDailyTurnover: 264.79 * CR },
  { symbol: 'ANANTRAJ', medianDailyTurnover: 103.09 * CR },
  { symbol: 'CLEANMAX', medianDailyTurnover: 23.38 * CR },
];

test('the turnover a target position requires', () => {
  // A 50cr position, out in three days, at no more than a fifth of volume.
  const required = minimumAdvt({ targetPosition: 50 * CR, exitDays: 3, maxParticipation: 0.2 });
  assert.equal(Number((required.value / CR).toFixed(2)), 83.33);
});

test('the requirement scales with the position, not with the universe', () => {
  const at = (cr) => Number((minimumAdvt({ targetPosition: cr * CR, exitDays: 3, maxParticipation: 0.2 }).value / CR).toFixed(1));
  assert.deepEqual([at(10), at(25), at(50), at(100)], [16.7, 41.7, 83.3, 166.7]);
});

test('an impossible participation rate is refused', () => {
  assert.equal(minimumAdvt({ targetPosition: 50 * CR, maxParticipation: 1.4 }).reason, 'INVALID_PARTICIPATION');
  assert.equal(minimumAdvt({ targetPosition: 50 * CR, maxParticipation: 0 }).reason, 'INVALID_PARTICIPATION');
  assert.equal(minimumAdvt({ targetPosition: 0 }).reason, 'NO_TARGET_POSITION');
});

test('normal turnover is the lower of the two windows', () => {
  // Twenty busy sessions in front of forty quiet ones. The short window alone
  // would call this liquid; the longer one says otherwise and wins.
  const series = [...Array(20).fill(500 * CR), ...Array(40).fill(50 * CR)];
  const advt = normalAdvt({ turnoverSeries: series });
  assert.equal(advt.value / CR, 50);
  assert.equal(advt.windowUsed, 60);
});

test('a median, not a mean, so one block trade cannot carry a thin name', () => {
  const series = [5_000 * CR, ...Array(29).fill(10 * CR)];
  const advt = normalAdvt({ turnoverSeries: series, shortWindow: 30, longWindow: 30 });
  const mean = series.reduce((a, b) => a + b, 0) / series.length;
  assert.ok(mean / CR > 170, 'the mean would have looked liquid');
  assert.equal(advt.value / CR, 10);
});

test('too little history is a reason, not a small number', () => {
  const advt = normalAdvt({ turnoverSeries: Array(5).fill(100 * CR) });
  assert.equal(advt.value, null);
  assert.equal(advt.reason, 'INSUFFICIENT_HISTORY');
  assert.deepEqual({ have: advt.sessions, need: advt.need }, { have: 5, need: 20 });
});

test('executable size is turnover times days times participation', () => {
  const out = executableFor({ advt: 100 * CR, exitDays: 3, maxParticipation: 0.2 });
  assert.equal(out.maxExecutablePosition / CR, 60);
});

test('with no target set, whether a size suffices is not answered', () => {
  // Nobody asked the question, so it is null rather than false.
  assert.equal(executableFor({ advt: 100 * CR }).meetsTarget, null);
});

test('a company too small for the target stays in the universe, sized down', () => {
  // The change this module exists for. CLEANMAX cannot carry 50cr, and that
  // is a fact about the position rather than grounds to stop calling it an
  // AI enabler.
  const screen = sizePositions(MEMBERS, { targetPosition: 50 * CR, exitDays: 3, maxParticipation: 0.2 });
  assert.equal(screen.sized.length, 7);
  assert.equal(screen.excluded.length, 0);
  assert.deepEqual(screen.belowTarget, ['CLEANMAX']);

  const cleanmax = screen.sized.find((one) => one.symbol === 'CLEANMAX');
  assert.equal(Number((cleanmax.maxExecutablePosition / CR).toFixed(2)), 14.03);
  assert.equal(cleanmax.meetsTarget, false);
  assert.equal(Number((cleanmax.shortfall / CR).toFixed(2)), 35.97);
});

test('a larger mandate moves the line without changing the universe', () => {
  const screen = sizePositions(MEMBERS, { targetPosition: 100 * CR, exitDays: 3, maxParticipation: 0.2 });
  assert.equal(screen.sized.length, 7);
  assert.deepEqual(screen.belowTarget.sort(), ['ANANTRAJ', 'CLEANMAX']);
  assert.equal(Number((screen.minimumAdvtForTarget / CR).toFixed(1)), 166.7);
});

test('nothing is excluded unless somebody set a floor', () => {
  // The decision to drop a name is always explicit.
  const screen = sizePositions(MEMBERS, { targetPosition: 500 * CR });
  assert.equal(screen.excluded.length, 0);
  assert.equal(screen.sized.length, 7);
});

test('an explicit floor excludes, and says which rule did it', () => {
  const screen = sizePositions(MEMBERS, { targetPosition: 50 * CR, excludeBelow: 20 * CR });
  assert.deepEqual(screen.excluded.map((one) => one.symbol), ['CLEANMAX']);
  assert.equal(screen.excluded[0].reason, 'BELOW_MINIMUM_EXECUTABLE_POSITION');
});

test('a member with no turnover history is unscreened, not excluded', () => {
  const screen = sizePositions([...MEMBERS, { symbol: 'NEW' }], { targetPosition: 50 * CR });
  assert.deepEqual(screen.unscreened, [{ symbol: 'NEW', reason: 'NO_TURNOVER_HISTORY' }]);
  assert.equal(screen.sized.length, 7);
});

test('the policy travels with the result, so the number can be argued with', () => {
  const screen = sizePositions(MEMBERS, { targetPosition: 50 * CR, exitDays: 3, maxParticipation: 0.2 });
  assert.deepEqual(screen.policy, {
    targetPosition: 50 * CR, exitDays: 3, maxParticipation: 0.2, excludeBelow: null,
  });
});

/* ── sizing the universe from candles ─────────────────────────────────── */

import { exitabilityForUniverse } from './aiEnablersExitability.js';

// Upstox daily candles, newest first as served: [ts, o, h, l, close, volume, oi].
const daily = (closes, volumes) => ({
  data: {
    candles: closes.map((close, i) => [
      new Date(Date.UTC(2026, 8, 17) - i * 86_400_000).toISOString(), close, close, close, close, volumes[i], 0,
    ]),
  },
});

const universe = (policy) => ({
  thresholds: { targetPosition: 100 * CR, exitDays: 3, maxParticipation: 0.2, ...policy },
  members: [
    { symbol: 'DEEP', instrumentKey: 'NSE_EQ|INE000A01001' },
    { symbol: 'THIN', instrumentKey: 'NSE_EQ|INE000A01002' },
    { symbol: 'NOKEY', instrumentKey: '' },
  ],
});

test('members are sized against the universe policy, and a thin one stays in with a smaller size', async () => {
  const candles = {
    // Rs 1 per share x 400 crore shares = Rs 400 crore a day.
    'NSE_EQ|INE000A01001': daily(Array(60).fill(1), Array(60).fill(400 * CR)),
    // Rs 100 crore a day: carries Rs 60 crore at 3 days x 20%.
    'NSE_EQ|INE000A01002': daily(Array(60).fill(1), Array(60).fill(100 * CR)),
  };
  const result = await exitabilityForUniverse(universe(), { fetchCandles: async (key) => candles[key] });
  assert.equal(Number((result.minimumAdvtForTarget / CR).toFixed(2)), 166.67);
  const bySymbol = Object.fromEntries(result.sized.map((one) => [one.symbol, one]));
  assert.equal(bySymbol.DEEP.meetsTarget, true);
  assert.equal(bySymbol.THIN.meetsTarget, false);
  assert.equal(bySymbol.THIN.maxExecutablePosition / CR, 60);
  assert.deepEqual(result.belowTarget, ['THIN']);
  assert.deepEqual(result.failures, [{ symbol: 'NOKEY', error: 'MALFORMED_INSTRUMENT_KEY' }]);
});

test('the twenty-day window is the latest twenty sessions, not the oldest', async () => {
  // Newest 20 sessions quiet (Rs 10 crore), older 40 busy (Rs 500 crore).
  // Read the wrong way round, the short window would be the busy sessions.
  const volumes = [...Array(20).fill(10 * CR), ...Array(40).fill(500 * CR)];
  const result = await exitabilityForUniverse(
    { ...universe(), members: [universe().members[0]] },
    { fetchCandles: async () => daily(Array(60).fill(1), volumes) },
  );
  assert.equal(result.windows.DEEP.short / CR, 10);
  assert.equal(result.sized[0].normalAdvt / CR, 10);
});

test('with no target set, nothing is called below target', async () => {
  const result = await exitabilityForUniverse(universe({ targetPosition: null }), {
    fetchCandles: async () => daily(Array(60).fill(1), Array(60).fill(10 * CR)),
  });
  assert.deepEqual(result.belowTarget, []);
  assert.ok(result.sized.every((one) => one.meetsTarget === null));
});

test('an exception moves a member out of belowTarget without changing what it can carry', async () => {
  const policy = {
    sizingExceptions: [{ symbol: 'THIN', decided: '2026-09-18', by: 'portfolio owner' }],
  };
  const candles = {
    'NSE_EQ|INE000A01001': daily(Array(60).fill(1), Array(60).fill(400 * CR)),
    'NSE_EQ|INE000A01002': daily(Array(60).fill(1), Array(60).fill(100 * CR)),
  };
  const result = await exitabilityForUniverse(universe(policy), { fetchCandles: async (key) => candles[key] });
  assert.deepEqual(result.belowTarget, []);
  assert.deepEqual(result.excepted, ['THIN']);
  const thin = result.sized.find((one) => one.symbol === 'THIN');
  assert.equal(thin.meetsTarget, false);
  assert.equal(thin.maxExecutablePosition / CR, 60);
  assert.equal(thin.shortfall / CR, 40);
  assert.equal(thin.exception.decided, '2026-09-18');
  // An exception for a member that meets the target is recorded but excepts nothing.
  const deep = await exitabilityForUniverse(
    universe({ sizingExceptions: [{ symbol: 'DEEP' }] }), { fetchCandles: async (key) => candles[key] },
  );
  assert.deepEqual(deep.excepted, []);
});
