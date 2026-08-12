import assert from 'node:assert/strict';
import test from 'node:test';
import { attachGrowwDerivatives } from './growwLiveAlphaFeed.js';

test('maps the nearest unexpired Groww future to each Live Alpha member', async () => {
  const prior = process.env.GROWW_ACCESS_TOKEN;
  process.env.GROWW_ACCESS_TOKEN = 'test-token';
  const csv = [
    'exchange,exchange_token,trading_symbol,groww_symbol,name,instrument_type,segment,series,isin,underlying_symbol,underlying_exchange_token,expiry_date,strike_price,lot_size,tick_size,freeze_quantity,is_reserved,buy_allowed,sell_allowed,internal_trading_symbol,is_intraday',
    'NSE,101,ABC26AUGFUT,NSE-ABC-25Aug26-FUT,,FUT,FNO,,,ABC,1,2099-08-25,0,1,0.05,1,0,1,1,ABC26AUGFUT,1',
    'NSE,102,ABC26SEPFUT,NSE-ABC-29Sep26-FUT,,FUT,FNO,,,ABC,1,2099-09-29,0,1,0.05,1,0,1,1,ABC26SEPFUT,1',
  ].join('\n');
  try {
    const universe = await attachGrowwDerivatives({ members: [{ symbol: 'ABC' }, { symbol: 'NOFUT' }] }, {
      fetchImpl: async () => ({ ok: true, text: async () => csv }),
    });
    assert.equal(universe.members[0].growwDerivativeInstrumentKey, 'GROWW_FNO|101');
    assert.equal(universe.members[0].growwDerivativeTradingSymbol, 'ABC26AUGFUT');
    assert.equal(universe.growwDerivativeResolution.resolved, 1);
    assert.equal(universe.growwDerivativeResolution.missing, 1);
  } finally {
    if (prior === undefined) delete process.env.GROWW_ACCESS_TOKEN; else process.env.GROWW_ACCESS_TOKEN = prior;
  }
});
