import assert from 'node:assert/strict';
import test from 'node:test';
import { growwExchangeSymbol, readGrowwLtpRow } from './sectorIndexGrowwFallback.js';

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
