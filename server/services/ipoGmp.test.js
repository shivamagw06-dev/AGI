import { test } from 'node:test';
import assert from 'node:assert/strict';
import { quoteFromXflot, matchXflot } from './ipoGmp.js';
const ipo = {symbol:'ABC', name:'ABC Limited', maxPrice:100};
const row = {symbol:'ABC', name:'ABC Limited', board:'MAINBOARD', status:'OPEN', lastGmp:20, priceMax:100};
const snapshot = records => ({ records, fetchedAt:new Date().toISOString() });
test('null and blank premiums are not zero; real zero and negative values survive', () => {
 for (const v of [null, undefined, '']) assert.equal(quoteFromXflot(ipo,snapshot([{...row,lastGmp:v}])),null);
 for (const v of [0,-10,20]) assert.equal(quoteFromXflot(ipo,snapshot([{...row,lastGmp:v}])).value,v);
});
test('does not attach similar names, SMEs or ambiguous records',()=>{
 assert.equal(matchXflot({...ipo,symbol:null,name:'ABC Healthcare'},[row]),null);
 assert.equal(matchXflot({...ipo,isSme:true},[row]),null);
 assert.equal(matchXflot(ipo,[row,row]),null);
});
test('mismatched issue prices flag dispute; record timestamp is not quote timestamp',()=>{
 const q=quoteFromXflot(ipo,snapshot([{...row,priceMax:200,updatedAt:'2026-10-01'}]));
 assert.equal(q.disputed,true); assert.equal(q.percentage,null); assert.equal(q.updatedAt,null);
});
test('failed refresh retains quote with stale flag',()=>{
 assert.equal(quoteFromXflot(ipo,{...snapshot([row]),unavailable:true}).stale,true);
});
