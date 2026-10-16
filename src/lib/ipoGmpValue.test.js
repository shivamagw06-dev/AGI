import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hasGmpNumber } from './ipoGmpValue.js';
test('GMP accepts premiums above 100, negatives and zero; missing stays missing',()=>{
 for(const v of [130,500,-20,0,'130',1200]) assert.equal(hasGmpNumber(v),true);
 for(const v of [null,undefined,'',' ',NaN,Infinity,'pending']) assert.equal(hasGmpNumber(v),false);
});
