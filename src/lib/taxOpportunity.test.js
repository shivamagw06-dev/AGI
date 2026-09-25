import test from 'node:test';
import assert from 'node:assert/strict';
import { scanTaxOpportunities, BLANK_TAX_CASE } from './taxOpportunity.js';
const base = {...BLANK_TAX_CASE,year:'2025-26',age:'35',salary:'1500000',depositInterest:'200000',savingsInterest:'10000',eligible80c:'150000',eligibleNps:'50000',eligible80d:'0',recordsConfirmed:true,claimsConfirmed:true};
test('verified narrow salary/interest case compares regimes, caps deductions and ranks actions',()=>{
  const r=scanTaxOpportunities(base);
  assert.equal(r.blockedReason,null);assert.equal(r.comparison.oldTaxable,1450000);
  assert.equal(r.comparison.newTaxable,1635000);assert.equal(r.comparison.oldDeductions,210000);
  assert.equal(r.cards[0].id,'ais');assert.equal(r.comparison.difference,Math.abs(r.comparison.old-r.comparison.new));
  assert.ok(r.cards.find(c=>c.id==='80c').detail.includes('2025–26'));
});
test('senior deposit deduction applies only to old regime on this year',()=>{
  const r=scanTaxOpportunities({...base,age:'66',salary:'0',savingsInterest:'0',depositInterest:'800000'});
  assert.equal(r.comparison.oldDeductions,250000);
  assert.equal(r.comparison.newTaxable,800000);
});
test('current year, rental, gains, business and unverified facts block numeric comparisons',()=>{
  for(const changes of [{year:'2026-27'},{hasRental:true},{hasGains:true},{hasBusiness:true},{recordsConfirmed:false},{claimsConfirmed:false},{eligible80d:'20000'}]) {
    const r=scanTaxOpportunities({...base,...changes});
    assert.equal(r.comparison,null,JSON.stringify(changes));
  }
  assert.ok(scanTaxOpportunities({...base,hasRental:true}).cards.some(c=>c.id==='gst'));
});
test('missing does not become zero and malformed or negative financial input is rejected',()=>{
  assert.equal(scanTaxOpportunities({...base,depositInterest:''}).comparison,null);
  for(const age of ['-1','121','bad']) assert.throws(()=>scanTaxOpportunities({...base,age}));
  for(const salary of ['-10','Infinity','100.123','1e99']) assert.throws(()=>scanTaxOpportunities({...base,salary}));
});
