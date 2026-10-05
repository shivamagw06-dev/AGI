import assert from 'node:assert/strict';
import test from 'node:test';
import { attachGrowwDerivatives, normalizeExchangeTimestamp, normalizeSpreadBps } from './growwLiveAlphaFeed.js';

test('rejects inverted Groww depth instead of persisting a negative spread', () => {
  assert.equal(normalizeSpreadBps(1193.1, 1123.7), null);
  assert.equal(normalizeSpreadBps(100, 101), 99.5025);
});

test('normalizes Groww exchange timestamps to milliseconds', () => {
  assert.equal(normalizeExchangeTimestamp(1_786_517_820), 1_786_517_820_000);
  assert.equal(normalizeExchangeTimestamp(1_786_517_820_000), 1_786_517_820_000);
  assert.equal(normalizeExchangeTimestamp(null), null);
});

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

test('Groww publishes each small batch immediately and stops outside the session', async () => {
 const { GrowwLiveAlphaFeed } = await import('./growwLiveAlphaFeed.js');
 const calls=[], batches=[]; let open=true;
 const feed=new GrowwLiveAlphaFeed({universe:{benchmarkKey:'NSE_INDEX|Nifty 50',members:[1,2,3,4].map(n=>({symbol:`S${n}`,instrumentKey:`NSE_EQ|${n}`}))},
  marketOpen:()=>open, sleep:async()=>{}, indices:async()=>[],
  quote:async(_exchange,_segment,symbol)=>{calls.push(symbol);return {last_price:100,last_trade_time:Date.now()};},
  onBatch:async batch=>batches.push({count:batch.snapshots.length,requested:calls.length})});
 feed.stopped=false;await feed.poll();assert.deepEqual(batches,[{count:3,requested:3},{count:1,requested:4}]);
 open=false;await feed.poll();assert.equal(calls.length,4);assert.equal(feed.status().status,'market_closed');
 feed.stop();open=true;await feed.poll();assert.equal(calls.length,4);
});
