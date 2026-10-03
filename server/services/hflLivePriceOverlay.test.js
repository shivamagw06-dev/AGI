import assert from 'node:assert/strict';
import test from 'node:test';
import { overlayPayloadWithPrices } from './hflLivePriceOverlay.js';

test('overlays LTP onto terminal card rows without changing the rank payload identity fields', () => {
  const prices = new Map([
    ['NSE_EQ|INE002A01018', { ltp: 1300.6, observed_at: '2026-08-25T07:00:00Z', source: 'live_alpha_store' }],
    ['RELIANCE', { ltp: 1300.6, observed_at: '2026-08-25T07:00:00Z', source: 'live_alpha_store' }],
  ]);
  const overlaid = overlayPayloadWithPrices({
    cards: [{
      scan: 'value',
      results: [{
        ticker: 'RELIANCE',
        instrument_key: 'NSE_EQ|INE002A01018',
        price: 1309.8,
        consensus: { target_price: 1600, upside: 22.16 },
      }],
    }],
  }, prices);
  const row = overlaid.cards[0].results[0];
  assert.equal(row.price, 1300.6);
  assert.equal(row.live_price, 1300.6);
  assert.equal(row.price_source, 'live_alpha_store');
  assert.equal(row.data_context.price_freshness, 'LIVE');
  assert.equal(row.consensus.upside, Number((((1600 / 1300.6) - 1) * 100).toFixed(2)));
});

test('leaves names without a live print on the snapshot price', () => {
  const overlaid = overlayPayloadWithPrices({
    research_queue: [{ ticker: 'AUTOIND', price: 96.15 }],
  }, new Map());
  assert.equal(overlaid.research_queue[0].price, 96.15);
});

test('recomputes upside from a row-level target when nested consensus is missing', () => {
  const overlaid = overlayPayloadWithPrices({
    cards: [{
      results: [{
        ticker: 'HDFCBANK',
        price: 700,
        target_price: 840,
      }],
    }],
  }, new Map([
    ['HDFCBANK', { ltp: 727.5, observed_at: '2026-08-25T12:00:00Z', source: 'live_market_snapshots' }],
  ]));
  const row = overlaid.cards[0].results[0];
  assert.equal(row.target_price, 840);
  assert.equal(row.consensus.target_price, 840);
  assert.equal(row.consensus_upside, Number((((840 / 727.5) - 1) * 100).toFixed(2)));
});

test('recomputes 1Y return from the year-ago close and live LTP', () => {
  const overlaid = overlayPayloadWithPrices({
    cards: [{
      results: [{
        ticker: 'SUNTECK',
        price: 307.6,
        return_1y: 23.1,
        consensus: { return_1y: 23.1, target_price: 435.93 },
        data_context: { return_1y_base_close: 393.65 },
      }],
    }],
  }, new Map([
    ['SUNTECK', { ltp: 314.85, observed_at: '2026-08-25T12:00:00Z', source: 'live_market_snapshots' }],
  ]));
  const row = overlaid.cards[0].results[0];
  const expected = Number((((314.85 / 393.65) - 1) * 100).toFixed(2));
  assert.equal(row.price, 314.85);
  assert.equal(row.return_1y, expected);
  assert.equal(row.consensus.return_1y, expected);
});

test('scales dividend yield from implied DPS and does not rewrite trailing PE', () => {
  const overlaid = overlayPayloadWithPrices({
    cards: [{
      results: [{
        ticker: 'ITC',
        price: 400,
        pe: 24.5,
        dividend_yield: 4,
        forward_eps: 25,
      }],
    }],
  }, new Map([
    ['ITC', { ltp: 500, observed_at: '2026-08-25T07:00:00Z', source: 'live_market_snapshots' }],
  ]));
  const row = overlaid.cards[0].results[0];
  assert.equal(row.dividend_yield, 3.2);
  assert.equal(row.forward_pe, 20);
  assert.equal(row.pe, 24.5);
});
