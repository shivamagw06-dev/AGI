import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  cleanIsin, assetTypeOf, normaliseHolding, normaliseHoldings,
} from './normalise.js';

describe('ISIN is the identity, not the symbol', () => {
  test('accepts a valid ISIN and strips the I_ prefix', () => {
    assert.equal(cleanIsin('INE002A01018'), 'INE002A01018');
    assert.equal(cleanIsin('I_INE002A01018'), 'INE002A01018');
    assert.equal(cleanIsin(' ine002a01018 '), 'INE002A01018');
  });

  test('rejects anything that is not one', () => {
    assert.equal(cleanIsin('RELIANCE'), null);
    assert.equal(cleanIsin(''), null);
    assert.equal(cleanIsin(null), null);
  });

  test('refuses a row with neither ISIN nor scheme code', () => {
    // Keyed on a symbol, this row could be attached to the wrong company.
    const out = normaliseHolding({ tradingsymbol: 'RELIANCE', quantity: 10 },
      { broker: 'ZERODHA' });
    assert.equal(out.ok, false);
    assert.equal(out.reason, 'no_isin_or_scheme_code');
  });
});

describe('broker field mapping', () => {
  test('reads Upstox field names', () => {
    const out = normaliseHolding({
      isin: 'INE002A01018', trading_symbol: 'RELIANCE', company_name: 'Reliance Industries',
      exchange: 'NSE', quantity: 25, average_price: 2715.4, instrument_type: 'EQ',
    }, { broker: 'UPSTOX', asOf: '2026-09-03T06:30:00Z' });
    assert.equal(out.ok, true);
    // Field by field rather than deepEqual: the normalised holding carries
    // more than these, and asserting the whole object would fail whenever an
    // unrelated field is added. toMatchObject was a partial match and this
    // keeps that meaning.
    for (const [field, value] of Object.entries({
      assetType: 'EQUITY', isin: 'INE002A01018', symbol: 'RELIANCE',
      exchange: 'NSE', quantity: 25, averageCost: 2715.4,
      currency: 'INR', source: 'UPSTOX', asOf: '2026-09-03T06:30:00Z',
    })) {
      assert.deepEqual(out.holding[field], value, `holding.${field}`);
    }
  });

  test('reads Zerodha field names for the same holding', () => {
    const out = normaliseHolding({
      isin: 'INE002A01018', tradingsymbol: 'RELIANCE', exchange: 'NSE',
      quantity: 25, average_price: 2715.4, product: 'CNC',
    }, { broker: 'ZERODHA' });
    assert.equal(out.ok, true);
    assert.equal(out.holding.isin, 'INE002A01018');
    // CNC is a product, not an asset class.
    assert.equal(out.holding.assetType, 'EQUITY');
  });

  test('reads Angel One field names', () => {
    const out = normaliseHolding({
      isin: 'INE002A01018', tradingsymbol: 'RELIANCE', exchange: 'NSE',
      quantity: 25, averageprice: 2715.4,
    }, { broker: 'ANGELONE' });
    assert.equal(out.ok, true);
    assert.equal(out.holding.averageCost, 2715.4);
  });

  test('refuses a broker it has no mapping for', () => {
    const out = normaliseHolding({ isin: 'INE002A01018', quantity: 1 },
      { broker: 'GROWW' });
    assert.equal(out.ok, false);
    assert.match(out.reason, /unsupported_broker/);
  });
});

describe('asset types', () => {
  test('treats a scheme code as a mutual fund whatever the label says', () => {
    assert.equal(assetTypeOf('EQ', { schemeCode: '119551' }), 'MUTUAL_FUND');
  });
  test('maps the labels brokers actually send', () => {
    assert.equal(assetTypeOf('ETF'), 'ETF');
    assert.equal(assetTypeOf('SGB'), 'BOND');
    assert.equal(assetTypeOf('CNC'), 'EQUITY');
    assert.equal(assetTypeOf(null, { exchange: 'MF' }), 'MUTUAL_FUND');
  });
});

describe('numbers', () => {
  test('keeps a missing average cost missing rather than zero', () => {
    // Zero reads as a free holding and produces an infinite return.
    const out = normaliseHolding({ isin: 'INE002A01018', quantity: 10, average_price: '' },
      { broker: 'UPSTOX' });
    assert.equal(out.holding.averageCost, null);
  });

  test('accepts a zero quantity but not a missing one', () => {
    const zero = normaliseHolding({ isin: 'INE002A01018', quantity: 0 }, { broker: 'UPSTOX' });
    assert.equal(zero.ok, true);
    const missing = normaliseHolding({ isin: 'INE002A01018' }, { broker: 'UPSTOX' });
    assert.equal(missing.ok, false);
    assert.equal(missing.reason, 'no_quantity');
  });

  test('parses grouped digits', () => {
    const out = normaliseHolding({ isin: 'INE002A01018', quantity: '1,250', average_price: '2,715.40' },
      { broker: 'UPSTOX' });
    assert.equal(out.holding.quantity, 1250);
    assert.equal(out.holding.averageCost, 2715.4);
  });
});

describe('unmatched rows are surfaced, never dropped', () => {
  test('returns rejects alongside the holdings', () => {
    const { holdings, unmatched, total } = normaliseHoldings([
      { isin: 'INE002A01018', quantity: 25, average_price: 2715.4 },
      { trading_symbol: 'MYSTERY', quantity: 5 },
      { isin: 'INE009A01021', quantity: 10 },
    ], { broker: 'UPSTOX' });
    assert.equal(total, 3);
    assert.equal(holdings.length, 2);
    // A silently missing position is worse than a visible gap: the portfolio
    // still adds up and nobody notices it is short a holding.
    assert.equal(unmatched.length, 1);
    assert.equal(unmatched[0].reason, 'no_isin_or_scheme_code');
  });
});
