import test from 'node:test';
import assert from 'node:assert/strict';

import { buildCanonicalSignals, confidenceBasis, confidenceLabel } from './liveAlphaSignalModel.js';


test('sample count never manufactures a validation claim', () => {
  assert.equal(confidenceLabel(80, 100), 'SAMPLE-RICH');
  assert.match(confidenceBasis(100), /not research validation/i);
});


test('canonical signals remain research-only after the sample threshold', () => {
  const rows = buildCanonicalSignals([
    {
      id: 'signal-1', symbol: 'TEST', engine: 'cross_sectional_momentum_v1',
      direction: 'positive', alpha_z: 2, signal_quality_score: 80,
      empirical_confidence_score: 80, comparable_observations: 100,
      as_of: '2026-08-23T09:30:00Z', liquidity_ok: true,
    },
  ]);
  assert.equal(rows[0].validation_status, 'SAMPLE THRESHOLD MET');
  assert.equal(rows[0].strategy_status, 'RESEARCH ONLY');
  assert.notEqual(rows[0].validation_status, 'RESEARCH VALIDATED');
});

test('mixed timestamps cannot create false agreement or borrow another components sample count', () => {
  const base = {symbol:'TEST', direction:'positive', alpha_z:2, signal_quality_score:90, liquidity_ok:true, as_of:'2026-10-01T09:55:00Z'};
  let [r] = buildCanonicalSignals([{...base,engine:'cross_sectional_momentum_v1',comparable_observations:200}, {...base,engine:'volume_liquidity_anomaly_v1',comparable_observations:0}]);
  assert.equal(r.samples,0);
  assert.equal(r.confidence,'MODEL-ONLY');
  assert.equal(r.input_data_status,'REVIEW REQUIRED');
  [r] = buildCanonicalSignals([{...base,engine:'cross_sectional_momentum_v1'}, {...base,engine:'volume_liquidity_anomaly_v1',as_of:'2026-10-01T09:50:00Z'}]);
  assert.equal(r.active.length,1);
  assert.equal(r.excluded_components.length,1);
});

test('signal reference remains fixed when the live quote advances', () => {
  const signal = {symbol:'TEST', engine:'cross_sectional_momentum_v1', direction:'positive', as_of:'2026-10-05T06:30:00Z', instrument_key:'NSE_EQ|TEST', price_at_signal:100, factor_values:{price_quote_at:'2026-10-05T06:29:59Z'}, live_price:101, price_as_of:'2026-10-05T06:31:00Z'};
  const [before] = buildCanonicalSignals([signal]);
  const [after] = buildCanonicalSignals([{...signal,live_price:105,price_as_of:'2026-10-05T06:35:00Z'}]);
  assert.equal(before.price_at_signal,100);
  assert.equal(after.price_at_signal,100);
  assert.equal(after.signal_price_as_of,'2026-10-05T06:29:59Z');
  assert.equal(after.live_price,105);
});

test('missing anchors cannot borrow older signals or current prices', () => {
  const base={symbol:'TEST',direction:'positive',engine:'cross_sectional_momentum_v1',as_of:'2026-10-05T06:30:00Z',live_price:110};
  const [row]=buildCanonicalSignals([base,{...base,engine:'volume_liquidity_anomaly_v1',as_of:'2026-10-05T06:25:00Z',price_at_signal:99}]);
  assert.equal(row.price_at_signal,null);
  assert.equal(row.signal_price_as_of,null);
});

test('cash anchor wins deterministically and future quote timestamps are not claimed', () => {
  const base={symbol:'TEST',direction:'positive',as_of:'2026-10-05T06:30:00Z'};
  const cash={...base,engine:'cross_sectional_momentum_v1',instrument_key:'NSE_EQ|TEST',price_at_signal:100,price_quote_at:'2026-10-05T06:31:00Z'};
  const derivative={...base,engine:'derivatives_positioning_v1',instrument_key:'NSE_FO|TEST',price_at_signal:102};
  for(const list of [[cash,derivative],[derivative,cash]]){
    const [row]=buildCanonicalSignals(list);
    assert.equal(row.price_at_signal,100);
    assert.equal(row.signal_price_as_of,null);
  }
});

test('aligned duplicate-strength components do not inflate the composite',()=>{
 const base={symbol:'TEST',as_of:'2026-10-08T05:00:00Z',direction:'positive',alpha_z:1,signal_quality_score:60};
 const one=buildCanonicalSignals([{...base,engine:'cross_sectional_momentum_v1'}])[0];
 const two=buildCanonicalSignals([{...base,engine:'cross_sectional_momentum_v1'},{...base,engine:'volume_liquidity_anomaly_v1'}])[0];
 assert.equal(one.composite,49);assert.equal(two.composite,49);assert.equal(two.model_version,'signal-composite-v2-mean');
});
