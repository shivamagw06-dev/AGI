import test from 'node:test';
import assert from 'node:assert/strict';
import { distribution, median, percentile, runScreen, stageThree, stageTwo } from './aiEnablersScreen.js';

const member = (symbol, fields = {}) => ({ symbol, ...fields });

test('the median of an even set is the midpoint of the middle two', () => {
  assert.equal(median([1, 2, 3, 4]), 2.5);
  assert.equal(median([3, 1, 2]), 2);
  assert.equal(median([]), null);
});

test('percentiles report the spread, and ignore holes', () => {
  const values = [10, 20, 30, 40, null, undefined, 50];
  assert.equal(percentile(values, 50), 30);
  assert.equal(percentile(values, 100), 50);
});

test('a distribution counts what is missing instead of hiding it', () => {
  const rows = [{ v: 1 }, { v: 3 }, { v: null }, { v: 'x' }];
  const spread = distribution(rows, (one) => one.v);
  assert.equal(spread.count, 2);
  assert.equal(spread.missing, 2);
  assert.equal(spread.median, 2);
});

test('stage 2 separates failing from unscreenable', () => {
  // The distinction the whole file exists for. BBB is too small - we know it
  // fails. CCC has no turnover history - we do not know anything about it,
  // and calling that a failure would be a claim we cannot support.
  const result = stageTwo([
    member('AAA', { freeFloatMarketCap: 5_000, medianDailyTurnover: 100 }),
    member('BBB', { freeFloatMarketCap: 10, medianDailyTurnover: 100 }),
    member('CCC', { freeFloatMarketCap: 5_000 }),
  ], { minFreeFloatMarketCap: 1_000, minMedianDailyTurnover: 50 });

  assert.deepEqual(result.passed.map((one) => one.symbol), ['AAA']);
  assert.deepEqual(result.failed.map((one) => one.symbol), ['BBB']);
  assert.deepEqual(result.failed[0].reasons, ['BELOW_SIZE_FLOOR']);
  assert.deepEqual(result.unscreened, [{ symbol: 'CCC', reason: 'NO_TURNOVER_HISTORY' }]);
});

test('stage 2 reports the distribution whether or not a threshold was set', () => {
  // A screen with no thresholds still has to say what it saw, because that is
  // how the thresholds get chosen the first time.
  const result = stageTwo([
    member('AAA', { freeFloatMarketCap: 1_000, medianDailyTurnover: 10 }),
    member('BBB', { freeFloatMarketCap: 3_000, medianDailyTurnover: 30 }),
  ]);
  assert.equal(result.applied, false);
  assert.deepEqual(result.passed.map((one) => one.symbol), ['AAA', 'BBB']);
  assert.equal(result.distributions.freeFloatMarketCap.median, 2_000);
  assert.equal(result.distributions.medianDailyTurnover.max, 30);
});

test('stage 2 can screen against the universe median instead of a constant', () => {
  const result = stageTwo([
    member('AAA', { freeFloatMarketCap: 1_000, medianDailyTurnover: 10 }),
    member('BBB', { freeFloatMarketCap: 2_000, medianDailyTurnover: 20 }),
    member('CCC', { freeFloatMarketCap: 3_000, medianDailyTurnover: 30 }),
  ], { relativeTo: 'median' });
  assert.equal(result.thresholds.freeFloatMarketCap, 2_000);
  assert.deepEqual(result.passed.map((one) => one.symbol), ['BBB', 'CCC']);
});

test('stage 3 admits on any one test, not all four', () => {
  // A company building through R&D and a company building through capex are
  // both building. Requiring both screens for a financing style.
  const result = stageThree([
    member('AAA', { capexToSales: 0.30, rndToSales: 0.01 }),
    member('BBB', { capexToSales: 0.01, rndToSales: 0.30 }),
  ], { thresholds: { capexToSales: 0.1, rndToSales: 0.1, revenueCagr3y: null, capexGrowth: null } });
  assert.deepEqual(result.passed.map((one) => one.symbol), ['AAA', 'BBB']);
  assert.deepEqual(result.passed[0].met, ['capexToSales']);
  assert.deepEqual(result.passed[1].met, ['rndToSales']);
});

test('stage 3 screens a company on the inputs it has, not the ones it lacks', () => {
  const result = stageThree([
    member('AAA', { capexToSales: 0.30 }),
    member('BBB', {}),
  ], { thresholds: { capexToSales: 0.1 } });
  assert.deepEqual(result.passed.map((one) => one.symbol), ['AAA']);
  assert.deepEqual(result.unscreened, [{ symbol: 'BBB', reason: 'NO_INTENSITY_INPUTS' }]);
});

test('an unscreened member does not advance to stage 3', () => {
  // Not knowing whether something is tradable is not knowing that it is. If
  // gaps advanced, a hole in the data would become a member of the index.
  const screen = runScreen([
    member('AAA', { freeFloatMarketCap: 5_000, medianDailyTurnover: 100, capexToSales: 0.3 }),
    member('GAP', { capexToSales: 0.9 }),
  ], {
    stage2: { minFreeFloatMarketCap: 1_000, minMedianDailyTurnover: 50 },
    stage3: { thresholds: { capexToSales: 0.1 } },
  });
  assert.deepEqual(screen.admitted, ['AAA']);
  assert.deepEqual(screen.stage2.unscreened, [{ symbol: 'GAP', reason: 'NO_FREE_FLOAT_MARKET_CAP' }]);
  assert.equal(screen.stage3.passed.length, 1);
});

test('the funnel reports what each stage removed', () => {
  const screen = runScreen([
    member('PASS', { freeFloatMarketCap: 5_000, medianDailyTurnover: 100, capexToSales: 0.9 }),
    member('SMALL', { freeFloatMarketCap: 10, medianDailyTurnover: 100, capexToSales: 0.9 }),
    member('IDLE', { freeFloatMarketCap: 5_000, medianDailyTurnover: 100, capexToSales: 0.01 }),
    member('GAP', {}),
  ], {
    stage2: { minFreeFloatMarketCap: 1_000, minMedianDailyTurnover: 50 },
    stage3: { thresholds: { capexToSales: 0.5 } },
  });
  assert.deepEqual(screen.funnel, [
    { stage: 'universe', count: 4 },
    { stage: 'stage2_size_tradability', count: 2, failed: 1, unscreened: 1 },
    { stage: 'stage3_investment_intensity', count: 1, failed: 1, unscreened: 0 },
  ]);
  assert.deepEqual(screen.admitted, ['PASS']);
});

test('an explicit null is not a zero, in any stage', () => {
  // Number(null) === 0. A member whose free float is null would be screened
  // as a zero-cap company and marked FAILED, when the truth is that we do not
  // know. An absent key gives NaN and behaves; JSON from a database carries
  // the null.
  const two = stageTwo([
    member('NULLCAP', { freeFloatMarketCap: null, medianDailyTurnover: 100 }),
    member('EMPTY', { freeFloatMarketCap: '', medianDailyTurnover: 100 }),
  ], { minFreeFloatMarketCap: 1_000, minMedianDailyTurnover: 50 });
  assert.equal(two.failed.length, 0);
  assert.deepEqual(two.unscreened.map((one) => one.reason),
    ['NO_FREE_FLOAT_MARKET_CAP', 'NO_FREE_FLOAT_MARKET_CAP']);

  // And in stage 3, a null capex ratio must not count as a real 0.0 that
  // fails the test - it must leave the company unscreened.
  const three = stageThree([member('AAA', { capexToSales: null, rndToSales: null })],
    { thresholds: { capexToSales: 0.1 } });
  assert.deepEqual(three.unscreened, [{ symbol: 'AAA', reason: 'NO_INTENSITY_INPUTS' }]);
});

test('a distribution counts nulls as missing, not as zeros', () => {
  const spread = distribution([{ v: 10 }, { v: null }, { v: 30 }], (one) => one.v);
  assert.equal(spread.count, 2);
  assert.equal(spread.missing, 1);
  assert.equal(spread.min, 10);      // not 0
  assert.equal(spread.median, 20);
});
