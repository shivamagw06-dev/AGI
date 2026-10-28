import assert from 'node:assert/strict';
import test from 'node:test';
import { growwExchangeSymbol, growwQuotePreviousClose, mergeGrowwIndexQuote, readGrowwLtpRow } from './sectorIndexGrowwFallback.js';

test('Groww index LTP uses the NSE_ exchange symbol, not the bare ticker', () => {
  assert.equal(growwExchangeSymbol('NSE_INDEX|Nifty 50'), 'NSE_NIFTY');
  assert.equal(growwExchangeSymbol('NSE_INDEX|Nifty Bank'), 'NSE_NIFTYBANK');
  assert.equal(growwExchangeSymbol('unknown'), null);
});

test('reads Groww LTP whether the payload is a number or a quote object', () => {
  assert.deepEqual(readGrowwLtpRow({ NSE_NIFTY: { ltp: 24178.85, previous_close: 24219 } }, 'NIFTY'), {
    ltp: 24178.85,
    previous_close: 24219,
  });
  assert.deepEqual(readGrowwLtpRow({ NIFTY: 24178.85 }, 'NIFTY'), {
    ltp: 24178.85,
    previous_close: null,
  });
  assert.equal(readGrowwLtpRow({ NSE_NIFTY: { ltp: 0 } }, 'NIFTY'), null);
});

test('fills previous close from OHLC when LTP is a bare number', () => {
  const quote = mergeGrowwIndexQuote(
    { NSE_NIFTY: 24178.85 },
    { NSE_NIFTY: { close: 24178.85, previous_close: 24219 } },
    'NIFTY',
  );
  assert.equal(quote.ltp, 24178.85);
  assert.equal(quote.previous_close, 24219);
});

test('Groww previous close is yesterday, not the session close', () => {
  assert.equal(growwQuotePreviousClose({ last_price: 100, previous_close: 98 }), 98);
  assert.equal(growwQuotePreviousClose({ last_price: 100, ohlc: { close: 100, previous_close: 98 } }), 98);
  assert.equal(growwQuotePreviousClose({ last_price: 100, ohlc: { close: 100 } }), null);
});
