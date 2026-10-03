import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { barsFromChart, sessionDate, listingStatus } from '../services/dailyBars.js';

const aapl = JSON.parse(
  readFileSync(new URL('./fixtures/yahooAaplSplit.json', import.meta.url), 'utf8'),
);

test('reads a real payload into dated bars', () => {
  const bars = barsFromChart(aapl, { ticker: 'AAPL' });
  assert.equal(bars.length, 8);
  assert.equal(bars[0].price_date, '2020-08-26');
  assert.equal(bars[7].price_date, '2020-09-04');
  assert.equal(bars[0].currency, 'USD');
  assert.equal(bars[0].ticker, 'AAPL');
});

test('close is split-adjusted, so it is not the price the stock traded at', () => {
  // Apple closed at 499.23 on 2020-08-28, two sessions before its 4-for-1
  // split. Yahoo reports 124.81 - the price restated in post-split shares.
  // A position value built from a 13F share count and this number is wrong
  // by a factor of four, which is exactly the mistake the two named columns
  // exist to prevent. If this ever stops holding, the naming is a lie.
  const bars = barsFromChart(aapl, { ticker: 'AAPL' });
  const preSplit = bars.find((b) => b.price_date === '2020-08-28');
  assert.ok(Math.abs(preSplit.close - 124.8075) < 0.01);
  assert.ok(preSplit.close < 200, 'close is restated in post-split shares');
});

test('adjusted close differs from close, and is the lower of the two after dividends', () => {
  const bars = barsFromChart(aapl, { ticker: 'AAPL' });
  for (const bar of bars) {
    assert.notEqual(bar.adjusted_close, bar.close);
    assert.ok(bar.adjusted_close < bar.close);
  }
});

test('a session with no close is dropped, never carried forward', () => {
  // Yahoo emits null for halts and for days an exchange was shut. Carrying
  // the previous price forward invents an observation: it shows a stock
  // trading flat through a suspension in which it did not trade at all.
  const chart = {
    meta: { currency: 'USD', exchangeTimezoneName: 'America/New_York' },
    timestamp: [1598448600, 1598535000, 1598621400],
    indicators: {
      quote: [{ close: [10, null, 12] }],
      adjclose: [{ adjclose: [9, null, 11] }],
    },
  };
  const bars = barsFromChart(chart);
  assert.equal(bars.length, 2);
  assert.deepEqual(bars.map((b) => b.close), [10, 12]);
  assert.deepEqual(bars.map((b) => b.price_date), ['2020-08-26', '2020-08-28']);
});

test('a zero or negative close is an absence, not a price', () => {
  // Yahoo has been seen to emit 0 rather than null for some halted sessions.
  // Stored as a price it is catastrophic: the position is worth nothing, the
  // return into that day is -100%, and the return out of it is infinite.
  const chart = {
    meta: { currency: 'USD', exchangeTimezoneName: 'America/New_York' },
    timestamp: [1598448600, 1598535000, 1598621400],
    indicators: {
      quote: [{ close: [10, 0, -3] }],
      adjclose: [{ adjclose: [10, 0, -3] }],
    },
  };
  const bars = barsFromChart(chart);
  assert.equal(bars.length, 1);
  assert.equal(bars[0].close, 10);
});

test('an adjusted close of zero is null, not zero', () => {
  const chart = {
    meta: { currency: 'USD', exchangeTimezoneName: 'America/New_York' },
    timestamp: [1598448600],
    indicators: { quote: [{ close: [10] }], adjclose: [{ adjclose: [0] }] },
  };
  assert.equal(barsFromChart(chart)[0].adjusted_close, null);
});

test('a bar is dated by the exchange session, not by UTC', () => {
  // The NZX opens at 10:00 NZDT, which is 21:00 the previous day in UTC.
  // Reading the timestamp in UTC dates every session one day early. US
  // equities hide this bug because their open is safely mid-day UTC.
  const openUtc = Date.UTC(2024, 2, 4, 21, 0, 0) / 1000;
  assert.equal(sessionDate(openUtc, 'Pacific/Auckland'), '2024-03-05');
  assert.equal(sessionDate(openUtc, 'UTC'), '2024-03-04');

  const chart = {
    meta: { currency: 'NZD', exchangeTimezoneName: 'Pacific/Auckland' },
    timestamp: [openUtc],
    indicators: { quote: [{ close: [5] }], adjclose: [{ adjclose: [5] }] },
  };
  assert.equal(barsFromChart(chart)[0].price_date, '2024-03-05');
});

test('a repeated session date does not produce two rows for one day', () => {
  const chart = {
    meta: { currency: 'USD', exchangeTimezoneName: 'America/New_York' },
    timestamp: [1598448600, 1598452200],
    indicators: { quote: [{ close: [10, 11] }], adjclose: [{ adjclose: [10, 11] }] },
  };
  const bars = barsFromChart(chart);
  assert.equal(bars.length, 1);
  assert.equal(bars[0].close, 10, 'the first bar of the session is kept');
});

test('a missing adjusted close is null rather than silently the raw close', () => {
  const chart = {
    meta: { currency: 'USD', exchangeTimezoneName: 'America/New_York' },
    timestamp: [1598448600],
    indicators: { quote: [{ close: [10] }] },
  };
  assert.equal(barsFromChart(chart)[0].adjusted_close, null);
});

test('an empty or malformed payload yields no bars rather than throwing', () => {
  assert.deepEqual(barsFromChart(null), []);
  assert.deepEqual(barsFromChart({}), []);
  assert.deepEqual(barsFromChart({ timestamp: [] }), []);
});

test('a symbol whose history stopped is reported stale, not active', () => {
  // A delisted or renamed ticker keeps serving its old history. Without this
  // check it looks healthy and a position gets valued at a years-old price.
  const bars = [{ price_date: '2026-08-01' }];
  assert.equal(listingStatus(bars, '2026-09-07'), 'stale_or_delisted');
  assert.equal(listingStatus([{ price_date: '2026-09-05' }], '2026-09-07'), 'active');
  assert.equal(listingStatus([], '2026-09-07'), 'unknown');
});
