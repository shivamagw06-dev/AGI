import assert from 'node:assert/strict';
import test from 'node:test';
import { createOutcomeRepository, publishedBefore, settleDueLiveAlphaOutcomes, settleOutcome } from './liveAlphaOutcomeSettlement.js';

const SIGNAL_AT = '2026-09-17T04:30:00.000Z'; // 10:00 IST
const DUE_AT = '2026-09-17T04:45:00.000Z'; // 15m later

function outcome(overrides = {}) {
  return {
    id: 'o1', signal_id: 's1', horizon: '15m', due_at: DUE_AT, attempt_count: 0,
    price_at_signal: 100, nifty_at_signal: 25000, sector_at_signal: 50000, estimated_cost_bps: 0,
    signal: {
      symbol: 'ABC', instrument_key: 'NSE_EQ|ABC', direction: 'positive', beta: 1,
      factor_values: { sector_instrument_key: 'NSE_INDEX|Nifty IT' },
      run: { as_of: SIGNAL_AT },
    },
    ...overrides,
  };
}

/** Prices by key and instant; anything unlisted has no candles. */
function bookOf(prices) {
  return {
    async priceAt(key, at) {
      const price = prices[`${key}@${new Date(at).toISOString()}`];
      return price == null ? { price: null, reason: 'no_candles' } : { price, candle_end: new Date(at).toISOString() };
    },
  };
}

const market = bookOf({
  [`NSE_EQ|ABC@${SIGNAL_AT}`]: 100.2, [`NSE_EQ|ABC@${DUE_AT}`]: 102,
  [`NSE_INDEX|Nifty 50@${SIGNAL_AT}`]: 25000, [`NSE_INDEX|Nifty 50@${DUE_AT}`]: 25250,
  [`NSE_INDEX|Nifty IT@${SIGNAL_AT}`]: 50000, [`NSE_INDEX|Nifty IT@${DUE_AT}`]: 50500,
});
const universeBySymbol = new Map();

test('settles a row from the stored anchors and the candle at its due time', async () => {
  const { outcome: result, row } = await settleOutcome(outcome(), { book: market, universeBySymbol });
  assert.equal(result, 'completed');
  assert.equal(row.status, 'completed');
  assert.equal(row.future_price, 102);
  assert.equal(row.stock_return_pct, 2);
  assert.equal(row.market_return_pct, 1);
  assert.equal(row.sector_adjusted_alpha_pct, 1);
  assert.equal(row.positive_outcome, true);
  assert.equal(row.attempt_count, 1);
  assert.ok(!('direction_multiplier' in row), 'only table columns are written');
});

test('a weekend signal is missed, never priced', async () => {
  const saturday = outcome({ signal: { ...outcome().signal, run: { as_of: '2026-09-19T05:00:00.000Z' } } });
  const { outcome: result, row } = await settleOutcome(saturday, { book: market, universeBySymbol });
  assert.equal(result, 'missed');
  assert.equal(row.last_error, 'signal_outside_session');
  assert.equal(row.future_price, null);
});

test('an anchor that is not the market price at the signal minute is missed', async () => {
  const { row } = await settleOutcome(outcome({ sector_at_signal: 49000 }), { book: market, universeBySymbol });
  assert.equal(row.last_error, 'sector_anchor_mismatch');
});

test('missing history is retried, then missed on the third attempt', async () => {
  const noStock = bookOf({});
  const first = await settleOutcome(outcome(), { book: noStock, universeBySymbol });
  assert.equal(first.outcome, 'deferred');
  assert.equal(first.row.status, 'pending');
  assert.equal(first.row.attempt_count, 1);
  const third = await settleOutcome(outcome({ attempt_count: 2 }), { book: noStock, universeBySymbol });
  assert.equal(third.outcome, 'missed');
  assert.equal(third.row.last_error, 'stock_no_candles');
});

test('a batch writes full-shape rows and stops at a failing history call', async () => {
  const saved = [];
  let calls = 0;
  const flaky = {
    async priceAt(key, at) {
      calls += 1;
      if (calls > 6) throw new Error('Upstox HTTP 429');
      return market.priceAt(key, at);
    },
  };
  const repository = { listDue: async () => [outcome(), outcome({ id: 'o2' })], save: async (rows) => saved.push(...rows) };
  const summary = await settleDueLiveAlphaOutcomes({ repository, book: flaky, universe: { members: [] }, now: new Date('2026-09-19T06:00:00Z') });
  assert.equal(summary.completed, 1);
  assert.match(summary.halted, /429/);
  assert.equal(saved.length, 1);
  assert.equal(new Set(saved.map((row) => Object.keys(row).join())).size, 1);
});

test('lists only rows due before today, oldest first', async () => {
  let query = '';
  const repository = createOutcomeRepository({ request: async (_table, options) => { query = decodeURIComponent(options.query); return []; } });
  await repository.listDue(publishedBefore(new Date('2026-09-19T06:00:00Z')), 500);
  assert.match(query, /due_at=lt\.2026-09-18T18:30:00\.000Z/);
  assert.match(query, /order=due_at\.asc/);
  assert.match(query, /status=eq\.pending/);
});

test('an old signal is benchmarked by its own sector label, not the symbol\'s current sector', async () => {
  // 10 Aug 2026: KOTAKBANK was BANK in the 20-stock universe. Its current
  // Nifty 500 sector is Financial Services, a different index.
  const asOf = '2026-08-10T04:59:04.339Z';
  const due = '2026-08-10T05:04:04.339Z';
  const row = outcome({
    due_at: due, price_at_signal: 2000, nifty_at_signal: 24590.65, sector_at_signal: 57697.7,
    signal: { symbol: 'KOTAKBANK', instrument_key: 'NSE_EQ|KOTAK', sector: 'BANK', direction: 'positive', beta: 1, factor_values: {}, run: { as_of: asOf } },
  });
  const book = bookOf({
    [`NSE_EQ|KOTAK@${asOf}`]: 2000, [`NSE_EQ|KOTAK@${due}`]: 2010,
    [`NSE_INDEX|Nifty 50@${asOf}`]: 24590, [`NSE_INDEX|Nifty 50@${due}`]: 24600,
    [`NSE_INDEX|Nifty Bank@${asOf}`]: 57695.35, [`NSE_INDEX|Nifty Bank@${due}`]: 57700,
  });
  const current = new Map([['KOTAKBANK', { symbol: 'KOTAKBANK', sectorInstrumentKey: 'NSE_INDEX|Nifty Fin Service' }]]);
  const { outcome: result, row: written } = await settleOutcome(row, { book, universeBySymbol: current });
  assert.equal(result, 'completed');
  assert.equal(written.future_sector, 57700);
});

test('a derivatives signal is priced from the stock, whose price is its anchor', async () => {
  const row = outcome({ signal: { ...outcome().signal, instrument_key: 'NSE_FO|54321' } });
  const members = new Map([['ABC', { symbol: 'ABC', instrumentKey: 'NSE_EQ|ABC', sectorInstrumentKey: 'NSE_INDEX|Nifty IT' }]]);
  assert.equal((await settleOutcome(row, { book: market, universeBySymbol: members })).outcome, 'completed');
  const unmapped = await settleOutcome(row, { book: market, universeBySymbol: new Map() });
  assert.equal(unmapped.row.last_error, 'instrument_not_mapped');
});

test('an unknown key is missed at once rather than retried', async () => {
  const refused = { async priceAt() { return { price: null, reason: 'invalid_instrument_key' }; } };
  const { outcome: result, row } = await settleOutcome(outcome(), { book: refused, universeBySymbol });
  assert.equal(result, 'missed');
  assert.equal(row.last_error, 'stock_invalid_instrument_key');
});
