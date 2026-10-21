import test from 'node:test';
import assert from 'node:assert/strict';
import {MOMENTUM_HEADERS,parseMomentumTables} from './manualMomentumScreener.js';
const header=MOMENTUM_HEADERS.join(',');
const row=['Example Ltd','','500001','EXAMPLE','INE123A01011','Industrial','Industrials',123.45,1000,81.72,0,-1,-3.04,123.45];
const parse=(r=row)=>parseMomentumTables([header+'\n'+r.join(',')]);
test('preserves negative returns, zero volume and BSE-only securities; computes percentage-point outperformance',()=>{
 const [r]=parse();assert.equal(r.weekChange,-1);assert.equal(r.volume,0);assert.equal(r.nseCode,'');assert.equal(r.relativeWeekChange,2.04);assert.equal(r.repeatedPrice,undefined);
});
test('rejects inconsistent prices and invalid numerical fields',()=>{
 for(const [i,v,re] of [[13,124,/prices must match/],[10,-1,/volume/],[9,101,/between 0 and 100/],[11,'',/required/],[12,'NaN',/number/]]){const r=[...row];r[i]=v;assert.throws(()=>parse(r),re);}
});
test('rejects duplicate securities and incomplete headers',()=>{
 assert.throws(()=>parseMomentumTables([header+'\n'+row.join(',')+'\n'+row.join(',')]),/Duplicate/);
 assert.throws(()=>parseMomentumTables(['Stock,Price\nTest,123']),/14-column/);
});
