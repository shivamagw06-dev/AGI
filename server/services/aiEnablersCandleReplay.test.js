import test from 'node:test';
import assert from 'node:assert/strict';
import {
  parseCandles, previousCloseBefore, replaySession, sessionDateOf,
} from './aiEnablersCandleReplay.js';
import { AiEnablersLiveRuntime } from './aiEnablersLiveRuntime.js';
import { LastGoodPrices } from './aiEnablersQuotes.js';

const A = 'NSE_EQ|INE000A01001';
const B = 'NSE_EQ|INE000A01002';
const NIFTY = 'NSE_INDEX|Nifty 50';

const UNIVERSE = {
  benchmarkKey: NIFTY,
  members: [
    { symbol: 'AAA', instrumentKey: A, layer: 'power', subLayers: ['equipment'] },
    { symbol: 'BBB', instrumentKey: B, layer: 'data_centre', subLayers: ['hardware'] },
  ],
};

const ist = (hhmm, date = '2026-09-17') => Date.parse(`${date}T${hhmm}:00+05:30`);
const row = (hhmm, close, volume = 1_000, date = '2026-09-17') => (
  [`${date}T${hhmm}:00+05:30`, close, close, close, close, volume, 0]
);
/** Upstox serves newest first. */
const payload = (...rows) => ({ status: 'success', data: { candles: [...rows].reverse() } });
const minutes = (from, count, close) => Array.from({ length: count }, (_, i) => {
  const t = new Date(ist(from) + i * 60_000 + 330 * 60_000).toISOString().slice(11, 16);
  return row(t, typeof close === 'function' ? close(i) : close);
});

const BASES = { [A]: 100, [B]: 100, [NIFTY]: 25_000 };

const replay = (candles, options = {}) => replaySession(UNIVERSE, {
  candlesByKey: Object.fromEntries(Object.entries(candles).map(([k, v]) => [k, parseCandles(payload(...v))])),
  previousCloseByKey: BASES,
  until: ist('15:31'),
  ...options,
});

test('candles are read oldest first, each with the instant it closed', () => {
  const parsed = parseCandles(payload(row('09:15', 101), row('09:16', 102)));
  assert.deepEqual(parsed.map((one) => one.close), [101, 102]);
  assert.equal(parsed[0].end, ist('09:16'));
  assert.deepEqual(parseCandles({ data: { candles: [['bad'], null, row('09:15', 0)] } }), []);
});

test('a snapshot sees a candle only once it has closed', () => {
  const snapshots = replay({
    [A]: [row('09:15', 110), row('09:16', 120)],
    [B]: [row('09:15', 100), row('09:16', 100)],
    [NIFTY]: [row('09:15', 25_000), row('09:16', 25_000)],
  });
  // The 09:15 candle closes at 09:16, so nothing exists before 09:16.
  assert.equal(snapshots[0].at, new Date(ist('09:16')).toISOString());
  // At 09:16 AAA is at the 09:15 close (+10%), not the 09:16 close (+20%).
  const at916 = Object.fromEntries(snapshots[0].index.contributions.byName.map((o) => [o.symbol, o.contribution_pp]));
  assert.equal(at916.AAA, 5);
  const at917 = Object.fromEntries(snapshots[1].index.contributions.byName.map((o) => [o.symbol, o.contribution_pp]));
  assert.equal(at917.AAA, 10);
  assert.ok(snapshots.every((one) => one.origin === 'candles'));
});

test('a rebuilt minute equals what the live runtime computes from the same prices', () => {
  const [snapshot] = replay({
    [A]: [row('09:15', 110)], [B]: [row('09:15', 90)], [NIFTY]: [row('09:15', 25_250)],
  }, { until: ist('09:17') });
  const at = ist('09:16');
  const store = {
    get: (key) => ({
      [A]: { ltp: 110, previous_close: 100, effective_timestamp: new Date(at).toISOString() },
      [B]: { ltp: 90, previous_close: 100, effective_timestamp: new Date(at).toISOString() },
      [NIFTY]: { ltp: 25_250, previous_close: 25_000, effective_timestamp: new Date(at).toISOString() },
    })[key] || null,
  };
  const live = new AiEnablersLiveRuntime({
    universe: UNIVERSE, store, lastGood: new LastGoodPrices(), now: () => at,
  }).current();
  assert.deepEqual(snapshot.index, live.index);
});

test('nothing is rebuilt at or after the cut-off, and the forming candle is ignored', () => {
  const snapshots = replay({
    [A]: minutes('09:15', 10, (i) => 100 + i), [B]: minutes('09:15', 10, 100), [NIFTY]: minutes('09:15', 10, 25_000),
  }, { until: ist('09:20') });
  assert.equal(snapshots.length, 4);   // 09:16, 09:17, 09:18, 09:19
  assert.equal(snapshots.at(-1).at, new Date(ist('09:19')).toISOString());
  // At 09:19 the newest closed candle is 09:18 (close 103), not 09:19's.
  const last = Object.fromEntries(snapshots.at(-1).index.contributions.byName.map((o) => [o.symbol, o.contribution_pp]));
  assert.equal(last.AAA, 1.5);
});

test('a member with no base is missing, and the minute refuses below the floor', () => {
  const snapshots = replay({
    [A]: [row('09:15', 110)], [B]: [row('09:15', 90)], [NIFTY]: [row('09:15', 25_000)],
  }, { previousCloseByKey: { [A]: 100, [NIFTY]: 25_000 }, until: ist('09:17') });
  assert.equal(snapshots[0].status, 'insufficient_coverage');
  assert.deepEqual(snapshots[0].index.missing, ['BBB']);
});

test('a quiet member falls back to its last price, then drops out, as it would live', () => {
  const snapshots = replay({
    [A]: [row('09:15', 110)],
    [B]: minutes('09:15', 12, 100),
    [NIFTY]: minutes('09:15', 12, 25_000),
  }, { until: ist('09:27') });
  const at = (hhmm) => snapshots.find((one) => one.at === new Date(ist(hhmm)).toISOString());
  assert.equal(at('09:16').quality.live, 2);
  // Two minutes after its last close, AAA is stale and priced from last-good.
  assert.equal(at('09:18').status, 'ok');
  assert.equal(at('09:18').quality.last_good, 1);
  assert.deepEqual(at('09:18').index.fallback.map((one) => one.symbol), ['AAA']);
  // Past the five-minute last-good limit it is missing, and the basket refuses.
  assert.equal(at('09:22').status, 'insufficient_coverage');
  assert.deepEqual(at('09:22').index.missing, ['AAA']);
});

test('a corporate-action exclusion applies to rebuilt minutes too', () => {
  const [snapshot] = replay({
    [A]: [row('09:15', 110)], [B]: [row('09:15', 50)], [NIFTY]: [row('09:15', 25_000)],
  }, { until: ist('09:17'), coverageFloor: 0.5, priceBreaks: { BBB: { priceBreak: true, reason: 'BONUS' } } });
  assert.deepEqual(snapshot.index.priceBreak.map((one) => one.symbol), ['BBB']);
  assert.equal(snapshot.index.return_pp, 10);
});

test('the previous close is the last day strictly before the session', () => {
  const daily = payload(
    ['2026-09-15T00:00:00+05:30', 1, 1, 1, 95, 1, 0],
    ['2026-09-16T00:00:00+05:30', 1, 1, 1, 98, 1, 0],
    ['2026-09-17T00:00:00+05:30', 1, 1, 1, 104, 1, 0],
  );
  assert.deepEqual(previousCloseBefore(daily, '2026-09-17'), { close: 98, date: '2026-09-16' });
  assert.equal(previousCloseBefore(payload(), '2026-09-17'), null);
});

test('the session date comes from the candles, and other days are left out', () => {
  const candles = { [A]: parseCandles(payload(row('15:29', 90, 1, '2026-09-16'), row('09:15', 110))) };
  assert.equal(sessionDateOf(candles), '2026-09-17');
  assert.equal(sessionDateOf({}), null);
});

test("yesterday's candles in the payload are not replayed as today's", () => {
  const snapshots = replay({
    [A]: [row('15:29', 50, 1, '2026-09-16'), row('09:15', 110)],
    [B]: [row('15:29', 50, 1, '2026-09-16'), row('09:15', 90)],
    [NIFTY]: [row('15:29', 20_000, 1, '2026-09-16'), row('09:15', 25_000)],
  }, { until: ist('09:17') });
  assert.equal(snapshots.length, 1);
  assert.equal(snapshots[0].at, new Date(ist('09:16')).toISOString());
});

/* ── the runtime ─────────────────────────────────────────────────────── */

const intraday = {
  [A]: payload(...minutes('09:15', 30, 110)),
  [B]: payload(...minutes('09:15', 30, 90)),
  [NIFTY]: payload(...minutes('09:15', 30, 25_250)),
};
const dailyFor = (closes) => (key) => payload(['2026-09-16T00:00:00+05:30', 1, 1, 1, closes[key], 1, 0]);

const runtimeAt = (nowMs, extra = {}) => new AiEnablersLiveRuntime({
  universe: UNIVERSE,
  store: { get: () => null, stats: () => ({}) },
  lastGood: new LastGoodPrices(),
  now: () => nowMs,
  fetchIntradayCandles: async (key) => intraday[key],
  fetchDailyCandles: async (key) => dailyFor(BASES)(key),
  ...extra,
});

test('a restart refills the session up to now', async () => {
  const runtime = runtimeAt(ist('09:40'));
  const result = await runtime.rebuildHistory();
  assert.equal(result.status, 'rebuilt');
  assert.equal(result.sessionDate, '2026-09-17');
  assert.equal(result.from, new Date(ist('09:16')).toISOString());
  assert.equal(result.to, new Date(ist('09:39')).toISOString());
  assert.equal(result.basis[A], 'daily:2026-09-16');
  assert.equal(runtime.history().at(-1).index.return_pp, 0);
});

test('rebuilt minutes go in front of observed ones and never replace them', async () => {
  const runtime = runtimeAt(ist('09:40'));
  runtime.snapshots.push({ at: new Date(ist('09:25')).toISOString(), origin: 'feed', status: 'ok' });
  await runtime.rebuildHistory();
  const history = runtime.history();
  assert.equal(history.at(-1).origin, 'feed');
  assert.ok(history.slice(0, -1).every((one) => one.origin === 'candles' && Date.parse(one.at) < ist('09:25')));
  // A second rebuild does not duplicate the first.
  await runtime.rebuildHistory();
  assert.equal(runtime.history().length, history.length);
});

test("the feed's previous close is preferred for the same session, and a disagreement is reported", async () => {
  const seen = new Date(ist('09:39')).toISOString();
  const runtime = runtimeAt(ist('09:40'), {
    store: {
      get: (key) => ({
        [A]: { ltp: 110, previous_close: 101, effective_timestamp: seen },
      })[key] || null,
      stats: () => ({}),
    },
  });
  const result = await runtime.rebuildHistory();
  assert.equal(result.basis[A], 'feed');
  assert.equal(result.basis[B], 'daily:2026-09-16');
  assert.deepEqual(result.disagreements, [{ key: A, feed: 101, daily: 100, dailyDate: '2026-09-16' }]);
});

test("a feed row from another day is not used as the base", async () => {
  const runtime = runtimeAt(ist('09:40'), {
    store: {
      get: (key) => (key === A
        ? { ltp: 110, previous_close: 55, effective_timestamp: new Date(ist('15:29', '2026-09-16')).toISOString() }
        : null),
      stats: () => ({}),
    },
  });
  const result = await runtime.rebuildHistory();
  assert.equal(result.basis[A], 'daily:2026-09-16');
});

test('a failed fetch is recorded, and without candles nothing is rebuilt', async () => {
  const runtime = runtimeAt(ist('09:40'), {
    fetchIntradayCandles: async () => { throw new Error('Upstox HTTP 429'); },
  });
  const result = await runtime.rebuildHistory();
  assert.equal(result.status, 'no_candles');
  assert.equal(result.errors.length, 3);
  assert.equal(runtime.history().length, 0);
  assert.equal((await runtimeAt(0, { fetchIntradayCandles: null }).rebuildHistory()).status, 'not_configured');
});

test("the runtime's corporate-action exclusions reach the rebuilt minutes", async () => {
  const runtime = runtimeAt(ist('09:20'), { coverageFloor: 0.5 });
  runtime.priceBreaks = { BBB: { priceBreak: true, reason: 'BONUS' } };
  await runtime.rebuildHistory();
  const last = runtime.history().at(-1);
  assert.deepEqual(last.index.priceBreak.map((one) => one.symbol), ['BBB']);
  assert.equal(last.index.return_pp, 10);
});
