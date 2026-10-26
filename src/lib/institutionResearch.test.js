import test from 'node:test';
import assert from 'node:assert/strict';
import { ownershipComparison, holdingCoverage, snapshotMatches, entityType, periodKey } from './institutionResearch.js';
const p={kind:'india-disclosures',name:'Test Mutual Fund',reportPeriod:'Sep 2026',periods:['Sep 2026 HOLDING %','Jun 2026 %']};
const row=(a,b,period='Sep 2026')=>({stock:'Test',quantity:'100',history:[a,b],reportPeriod:period});
test('rounded changes cannot become certain investor votes',()=>{
 assert.equal(ownershipComparison(p,row('1.7%','1.6%')).status,'Within source rounding');
 assert.equal(ownershipComparison(p,row('1.69%','1.55%')).status,'Reported stake increased');
 assert.equal(ownershipComparison(p,row('2.32%','2.38%')).status,'Reported stake reduced');
});
test('new and historical disclosures cannot imply a purchase or sale',()=>{
 assert.equal(ownershipComparison(p,row('2%','-')).comparable,false);
 assert.equal(ownershipComparison(p,row('2%','1%','Jun 2026')).comparable,false);
 const c=holdingCoverage({...p,rows:[row('2%','1%'),row('-','2%'),row('2%','1%','Jun 2026')]});
 assert.equal(c.current.length,1);assert.equal(c.historical.length,2);
});
test('groups excluded, and cross-market caches rejected',()=>{
 assert.equal(entityType('SBI Group'),'Group / related entities');
 assert.equal(snapshotMatches({country:'US',category:'institutional',published:true,rows:[]},'IN','institutional'),false);
 assert.equal(snapshotMatches({country:'IN',published:true,rows:[]},'IN','individual'),true);
 assert.equal(snapshotMatches({country:'IN',published:false,rows:[]},'IN','individual'),false);
});

test('US date formats reconcile without turning undated rows current',()=>{
 assert.equal(periodKey('30 Jun 2026'),periodKey('2026-06-30'));
 const c=holdingCoverage({kind:'sec13f',reportPeriod:'30 Jun 2026',rows:[{quantity:'100',reportPeriod:'2026-06-30'}]});
 assert.equal(c.current.length,1);
 assert.equal(holdingCoverage({kind:'sec13f',reportPeriod:null,rows:[{quantity:'100'}]}).current.length,0);
});
