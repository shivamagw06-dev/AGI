import { describe, it, expect } from 'vitest';
import {
  cleanIsin, assetTypeOf, normaliseHolding, normaliseHoldings,
} from './normalise.js';

describe('ISIN is the identity, not the symbol', () => {
  it('accepts a valid ISIN and strips the I_ prefix', () => {
    expect(cleanIsin('INE002A01018')).toBe('INE002A01018');
    expect(cleanIsin('I_INE002A01018')).toBe('INE002A01018');
    expect(cleanIsin(' ine002a01018 ')).toBe('INE002A01018');
  });

  it('rejects anything that is not one', () => {
    expect(cleanIsin('RELIANCE')).toBeNull();
    expect(cleanIsin('')).toBeNull();
    expect(cleanIsin(null)).toBeNull();
  });

  it('refuses a row with neither ISIN nor scheme code', () => {
    // Keyed on a symbol, this row could be attached to the wrong company.
    const out = normaliseHolding({ tradingsymbol: 'RELIANCE', quantity: 10 },
      { broker: 'ZERODHA' });
    expect(out.ok).toBe(false);
    expect(out.reason).toBe('no_isin_or_scheme_code');
  });
});

describe('broker field mapping', () => {
  it('reads Upstox field names', () => {
    const out = normaliseHolding({
      isin: 'INE002A01018', trading_symbol: 'RELIANCE', company_name: 'Reliance Industries',
      exchange: 'NSE', quantity: 25, average_price: 2715.4, instrument_type: 'EQ',
    }, { broker: 'UPSTOX', asOf: '2026-09-03T06:30:00Z' });
    expect(out.ok).toBe(true);
    expect(out.holding).toMatchObject({
      assetType: 'EQUITY', isin: 'INE002A01018', symbol: 'RELIANCE',
      exchange: 'NSE', quantity: 25, averageCost: 2715.4,
      currency: 'INR', source: 'UPSTOX', asOf: '2026-09-03T06:30:00Z',
    });
  });

  it('reads Zerodha field names for the same holding', () => {
    const out = normaliseHolding({
      isin: 'INE002A01018', tradingsymbol: 'RELIANCE', exchange: 'NSE',
      quantity: 25, average_price: 2715.4, product: 'CNC',
    }, { broker: 'ZERODHA' });
    expect(out.ok).toBe(true);
    expect(out.holding.isin).toBe('INE002A01018');
    // CNC is a product, not an asset class.
    expect(out.holding.assetType).toBe('EQUITY');
  });

  it('reads Angel One field names', () => {
    const out = normaliseHolding({
      isin: 'INE002A01018', tradingsymbol: 'RELIANCE', exchange: 'NSE',
      quantity: 25, averageprice: 2715.4,
    }, { broker: 'ANGELONE' });
    expect(out.ok).toBe(true);
    expect(out.holding.averageCost).toBe(2715.4);
  });

  it('refuses a broker it has no mapping for', () => {
    const out = normaliseHolding({ isin: 'INE002A01018', quantity: 1 },
      { broker: 'GROWW' });
    expect(out.ok).toBe(false);
    expect(out.reason).toMatch(/unsupported_broker/);
  });
});

describe('asset types', () => {
  it('treats a scheme code as a mutual fund whatever the label says', () => {
    expect(assetTypeOf('EQ', { schemeCode: '119551' })).toBe('MUTUAL_FUND');
  });
  it('maps the labels brokers actually send', () => {
    expect(assetTypeOf('ETF')).toBe('ETF');
    expect(assetTypeOf('SGB')).toBe('BOND');
    expect(assetTypeOf('CNC')).toBe('EQUITY');
    expect(assetTypeOf(null, { exchange: 'MF' })).toBe('MUTUAL_FUND');
  });
});

describe('numbers', () => {
  it('keeps a missing average cost missing rather than zero', () => {
    // Zero reads as a free holding and produces an infinite return.
    const out = normaliseHolding({ isin: 'INE002A01018', quantity: 10, average_price: '' },
      { broker: 'UPSTOX' });
    expect(out.holding.averageCost).toBeNull();
  });

  it('accepts a zero quantity but not a missing one', () => {
    const zero = normaliseHolding({ isin: 'INE002A01018', quantity: 0 }, { broker: 'UPSTOX' });
    expect(zero.ok).toBe(true);
    const missing = normaliseHolding({ isin: 'INE002A01018' }, { broker: 'UPSTOX' });
    expect(missing.ok).toBe(false);
    expect(missing.reason).toBe('no_quantity');
  });

  it('parses grouped digits', () => {
    const out = normaliseHolding({ isin: 'INE002A01018', quantity: '1,250', average_price: '2,715.40' },
      { broker: 'UPSTOX' });
    expect(out.holding.quantity).toBe(1250);
    expect(out.holding.averageCost).toBe(2715.4);
  });
});

describe('unmatched rows are surfaced, never dropped', () => {
  it('returns rejects alongside the holdings', () => {
    const { holdings, unmatched, total } = normaliseHoldings([
      { isin: 'INE002A01018', quantity: 25, average_price: 2715.4 },
      { trading_symbol: 'MYSTERY', quantity: 5 },
      { isin: 'INE009A01021', quantity: 10 },
    ], { broker: 'UPSTOX' });
    expect(total).toBe(3);
    expect(holdings).toHaveLength(2);
    // A silently missing position is worse than a visible gap: the portfolio
    // still adds up and nobody notices it is short a holding.
    expect(unmatched).toHaveLength(1);
    expect(unmatched[0].reason).toBe('no_isin_or_scheme_code');
  });
});
