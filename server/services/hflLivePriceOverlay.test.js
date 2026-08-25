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
