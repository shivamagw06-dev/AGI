import assert from 'node:assert/strict';
import test from 'node:test';
import {
  STOCKS_BOARD_INSTRUMENTS,
  assembleInstrumentRow,
  closesFromChart,
  downsampleHistory,
  formatSessionTime,
  getStocksBoard,
  groupBoardRows,
  horizonReturn,
  pctReturn,
  previousSessionClose,
  resetStocksBoardCache,
  round,
} from './stocksBoardService.js';

function day(offset, value) {
  return { t: Date.parse('2026-08-25T00:00:00.000Z') + offset * 86_400_000, v: value };
}

function chartJson({ last = 110, previous = 100, timeZone = 'America/New_York', points, first = 90 } = {}) {
  const closes = points || Array.from({ length: 260 }, (_, i) => first + i * ((previous - first) / 258));
  closes[closes.length - 2] = previous;
  closes[closes.length - 1] = last;
  const start = Date.parse('2025-08-26T20:00:00.000Z') / 1000;
  const lastTs = Date.parse('2026-08-25T20:00:00.000Z') / 1000;
  const step = (lastTs - start) / (closes.length - 1);
  return {
    chart: {
      result: [{
        meta: {
          regularMarketPrice: last,
          chartPreviousClose: first,
          regularMarketTime: lastTs,
          exchangeTimezoneName: timeZone,
        },
        timestamp: closes.map((_, i) => Math.round(start + i * step)),
        indicators: { quote: [{ close: closes }] },
      }],
    },
  };
}

test('pctReturn withholds divide-by-zero and non-finite inputs', () => {
  assert.equal(pctReturn(110, 100), 10);
  assert.equal(pctReturn(110, 0), null);
  assert.equal(pctReturn(null, 100), null);
  assert.equal(round(null), null);
  assert.equal(round(18.319), 18.32);
});

test('previousSessionClose uses the prior daily bar on the same session day', () => {
  const closes = [
    { t: Date.parse('2026-08-24T20:00:00.000Z'), v: 100 },
    { t: Date.parse('2026-08-25T20:00:00.000Z'), v: 110 },
  ];
  assert.equal(previousSessionClose(closes, Date.parse('2026-08-25T20:15:00.000Z')), 100);
  assert.equal(previousSessionClose(closes, Date.parse('2026-08-26T13:00:00.000Z')), 110);
});

test('1M and 1Y use the close on or before the horizon and withhold short series', () => {
  const dense = Array.from({ length: 400 }, (_, i) => day(i - 399, 100 + i * 0.1));
  const last = dense.at(-1).v;
  assert.ok(Math.abs(horizonReturn(dense, last, 30, 15) - pctReturn(last, dense.at(-31).v)) < 1e-9);
  assert.ok(horizonReturn(dense, last, 365, 200) != null);

  const short = Array.from({ length: 40 }, (_, i) => day(i, 100 + i));
  assert.equal(horizonReturn(short, short.at(-1).v, 365, 200), null);
  assert.ok(horizonReturn(short, short.at(-1).v, 30, 15) != null);
});

test('assembleInstrumentRow ignores Yahoo 1y chartPreviousClose and uses the prior session', () => {
  const row = assembleInstrumentRow(
    { id: 'gspc', ticker: 'SPX', name: 'S&P 500', yahoo: '^GSPC', region: 'americas' },
    chartJson({ last: 7661.55, previous: 7637.13, first: 6425 })
  );
  assert.equal(row.available, true);
  assert.equal(row.last, 7661.55);
  assert.equal(row.change, 24.42);
  assert.equal(row.changePct, 0.32);
  assert.ok(row.monthPct != null);
  assert.ok(row.yearPct != null && row.yearPct !== 0);
  assert.ok(row.yearPct > 15);
  assert.match(row.timeLabel, /EDT|EST|GMT-4|GMT-5/);
  assert.ok(row.history.length > 2);
  assert.equal(row.history[0].t <= row.history.at(-1).t, true);
});

test('ETF proxies stay labelled and empty charts become unavailable rows', () => {
  const proxy = assembleInstrumentRow(
    {
      id: 'msci-apac',
      ticker: 'IPAC',
      name: 'MSCI Pacific',
      yahoo: 'IPAC',
      region: 'apac',
      proxy: true,
      proxyNote: 'ETF proxy',
    },
    chartJson({ last: 70, previous: 69 })
  );
  assert.equal(proxy.proxy, true);
  assert.equal(proxy.proxyNote, 'ETF proxy');

  const missing = assembleInstrumentRow(
    { id: 'topx', ticker: 'TPX', name: 'TOPIX', yahoo: '^TOPX', region: 'apac' },
    { chart: { result: [] } }
  );
  assert.equal(missing.available, false);
  assert.equal(missing.last, null);
  assert.equal(missing.reason, 'chart_empty');
});

test('downsample keeps endpoints and groupBoardRows preserves region order', () => {
  const points = Array.from({ length: 200 }, (_, i) => day(i, 100 + i));
  const history = downsampleHistory(points, 10);
  assert.equal(history.length, 10);
  assert.equal(history[0].v, 100);
  assert.equal(history.at(-1).v, 299);

  const grouped = groupBoardRows([
    { id: 'dji', region: 'americas' },
    { id: 'nsei', region: 'india' },
    { id: 'es', region: 'futures' },
  ]);
  assert.deepEqual(Object.keys(grouped.regions), ['futures', 'americas', 'emea', 'apac', 'india']);
  assert.equal(grouped.regions.americas.rows[0].id, 'dji');
});

test('closesFromChart drops null prints', () => {
  const points = closesFromChart({
    chart: { result: [{ timestamp: [1, 2, 3], indicators: { quote: [{ close: [10, null, 12] }] } }] },
  });
  assert.equal(points.length, 2);
  assert.equal(points[1].v, 12);
});

test('formatSessionTime falls back when the zone is unknown', () => {
  assert.equal(formatSessionTime(null), null);
  assert.match(formatSessionTime('2026-08-25T20:00:00.000Z', 'Not/AZone'), /UTC/);
});

test('getStocksBoard caches a successful snapshot and labels delayed Yahoo', async () => {
  resetStocksBoardCache();
  let hits = 0;
  const fetchFn = async (url) => {
    hits += 1;
    const yahoo = decodeURIComponent(String(url).split('/chart/')[1].split('?')[0]);
    const last = yahoo === '^NSEI' ? 25000 : 1000;
    return {
      ok: true,
      json: async () => chartJson({ last, previous: last - 10 }),
    };
  };

  const first = await getStocksBoard({ force: true, fetchFn });
  assert.equal(first.ok, true);
  assert.equal(first.delayed, true);
  assert.equal(first.cache, 'miss');
  assert.ok(first.available > 0);
  assert.ok(first.regions.india.rows.some((row) => row.id === 'nsei' && row.last === 25000));
  assert.ok(first.methodology.includes('Not Bloomberg'));

  const second = await getStocksBoard({ fetchFn });
  assert.equal(second.cache, 'hit');
  assert.equal(hits, STOCKS_BOARD_INSTRUMENTS.length);
  resetStocksBoardCache();
});
