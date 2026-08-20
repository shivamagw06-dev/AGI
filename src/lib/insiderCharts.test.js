import assert from 'node:assert/strict';
import test from 'node:test';

import { flowChart, niceBound, shareBars, sparkline } from './insiderCharts.js';

const day = (date, buys, sells, cumulativeNet) => ({ date, buys, sells, cumulativeNet });

test('buys are drawn above the axis and sells below it', () => {
  // Drawn on the wrong side the chart still looks like a chart, so this is
  // asserted rather than eyeballed.
  const { bars, zeroY } = flowChart([day('2026-08-20', 5, 3, 2)]);
  const buy = bars.find((bar) => bar.kind === 'buy');
  const sell = bars.find((bar) => bar.kind === 'sell');
  assert.ok(buy.y + buy.height <= zeroY + 0.01, 'buy bar should end at the axis');
  assert.ok(sell.y >= zeroY - 0.01, 'sell bar should start at the axis');
});

test('a day with no filings on one side draws no bar for it', () => {
  const { bars } = flowChart([day('2026-08-20', 4, 0, 4)]);
  assert.deepEqual(bars.map((bar) => bar.kind), ['buy']);
});

test('the running total line stays inside the plot', () => {
  const days = [day('2026-08-18', 30, 0, 30), day('2026-08-19', 0, 90, -60)];
  const chart = flowChart(days, { height: 200, pad: 10 });
  const ys = chart.line.match(/[ML]([\d.]+) ([\d.]+)/g).map((part) => Number(part.split(' ')[1]));
  assert.ok(Math.min(...ys) >= 10, 'line must not clip above the plot');
  assert.ok(Math.max(...ys) <= 190, 'line must not clip below the plot');
});

test('daily bars and the running total do not share a scale', () => {
  // A window whose total climbs into the hundreds would flatten every daily bar
  // into the baseline if it did.
  const days = [day('2026-08-18', 6, 2, 4), day('2026-08-19', 5, 1, 200)];
  const chart = flowChart(days);
  assert.ok(chart.barBound < chart.netBound);
  assert.ok(chart.bars.every((bar) => bar.height > 1), 'daily bars stay visible');
});

test('no days gives an empty chart rather than a broken one', () => {
  assert.equal(flowChart([]).empty, true);
  assert.equal(flowChart(null).bars.length, 0);
});

test('bars stay wide enough to see across a long window', () => {
  const days = Array.from({ length: 180 }, (_, i) => day(`2026-0${1 + (i % 9)}-01`, 2, 1, i));
  assert.ok(flowChart(days).bars.every((bar) => bar.width >= 3));
});

test('axis bounds round to a number a reader can hold', () => {
  assert.equal(niceBound(7), 10);
  assert.equal(niceBound(23), 25);
  assert.equal(niceBound(0), 1);
});

test('a small category renders as small, not as absent', () => {
  const bars = shareBars([{ mode: 'Market', count: 996 }, { mode: 'Gift', count: 4 }]);
  assert.ok(bars[1].width > 0, 'a 0.4% slice still needs a sliver');
  assert.ok(bars[1].pct < 1);
});

test('share bars sum to the whole', () => {
  const bars = shareBars([{ count: 3 }, { count: 1 }]);
  assert.equal(Math.round(bars.reduce((sum, bar) => sum + bar.pct, 0)), 100);
});

test('a single reading draws no sparkline', () => {
  // One point is a dot, and a dot implies a trend that is not there.
  assert.equal(sparkline([5]), '');
  assert.ok(sparkline([1, 2, 3]).startsWith('M'));
});

test('a flat series still draws a line', () => {
  assert.ok(sparkline([4, 4, 4]).includes('L'));
});
