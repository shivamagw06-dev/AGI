import { test } from 'node:test';
import assert from 'node:assert/strict';
import { unifiedHoldings } from './unifiedHoldings.js';
test('keeps existing valuation index and quantity when adding dated holder details', () => {
 const p={rows:[{stock:'Example',quantity:'100',history:['1%']}]};
 const out=unifiedHoldings(p,[{stock:'Example Limited',symbol:'EX',quantity:50,holder:'Family member'}],{Example:{symbol:'EX.NS'}});
 assert.equal(out.length,1);assert.equal(out[0].quantity,'100');assert.equal(out[0].snapshotIndex,0);assert.equal(out[0].disclosures.length,1);assert.equal(p.rows[0].disclosures,undefined);
});
test('multiple disclosed legal holders are not added together or priced from a snapshot',()=>{
 const out=unifiedHoldings({rows:[]},[{stock:'Other',symbol:'OTHER',quantity:50},{stock:'Other',symbol:'OTHER',quantity:60}]);
 assert.equal(out.length,1);assert.equal(out[0].quantity,'See holder details');assert.equal(out[0].snapshotIndex,undefined);assert.equal(out[0].disclosures.length,2);
});
