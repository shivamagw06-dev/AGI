import test from 'node:test';
import assert from 'node:assert/strict';
import { assessInsurancePremium } from './taxHealth.js';
import { BLANK_TAX_CASE, scanTaxOpportunities } from './taxOpportunity.js';
import { taxDecisionBrief } from './taxDecisionEngine.js';

const caseInput={...BLANK_TAX_CASE,year:'2025-26',age:'35',salary:'1800000',depositInterest:'50000',savingsInterest:'10000',
  eligible80c:'150000',eligible80d:'0',eligibleNps:'50000',recordsConfirmed:true,claimsConfirmed:true};
const verified={selfPremium:'30000',parentPremium:'60000',selfAge:'35',parentAge:'65',nonCashPaid:true,eligibleRelationship:true,paidInYear:true,notDoubleClaimed:true};

test('insurance limits separately cap self/family and parent premiums after eligibility confirmation',()=>{
  const r=assessInsurancePremium(verified);
  assert.deepEqual([r.selfAllowed,r.parentAllowed,r.deduction],[25000,50000,75000]);
  assert.equal(assessInsurancePremium({...verified,selfAge:'60',parentAge:'58'}).deduction,55000);
  for(const changes of [{nonCashPaid:false},{paidInYear:false},{notDoubleClaimed:false},{eligibleRelationship:false},{parentAge:''},{parentPremium:''},{selfPremium:'-2'}])
    assert.throws(()=>assessInsurancePremium({...verified,...changes}));
});

test('health premium enters only a confirmed FY25–26 regime estimate, and benefit uses the lower regime',()=>{
  const deduction=assessInsurancePremium(verified).deduction;
  const without=scanTaxOpportunities(caseInput).comparison;
  assert.equal(scanTaxOpportunities({...caseInput,eligible80d:String(deduction)}).comparison,null);
  const form={...caseInput,eligible80d:String(deduction),healthValidated:true};
  const scan=scanTaxOpportunities(form),c=scan.comparison;
  assert.equal(c.oldTaxable,without.oldTaxable-deduction);
  assert.equal(c.newTaxable,without.newTaxable);
  const brief=taxDecisionBrief({form,scan});
  const health=brief.items.find(x=>x.id==='health');
  assert.equal(health.impact,Math.max(0,Math.min(without.old,c.new)-Math.min(c.old,c.new)));
  assert.match(health.detail,/included/);
});

test('case facts generate distinct questions and evidence blockers before unsupported amounts',()=>{
  const form={...caseInput,hasGains:true,hasBusiness:true,hasRental:true};
  const scan=scanTaxOpportunities(form);
  const brief=taxDecisionBrief({form,scan,reconciliation:{unmatched:2,warnings:['duplicate'],investmentOrders:1},
    context:{receivesHra:true,employerNps:true,donated:true,inheritedSale:true,hotel:true}});
  assert.equal(brief.items[0].id,'reconcile');
  assert.equal(brief.items.find(x=>x.id==='gains').impact,null);
  for(const id of ['hra','employer-nps','donation','gains','property','business','gst'])assert.ok(brief.items.some(x=>x.id===id),id);
});

test('current tax year never borrows the prior-year numerical rule package',()=>{
  const form={...caseInput,year:'2026-27',eligible80d:'0'};
  const scan=scanTaxOpportunities(form);
  const brief=taxDecisionBrief({form,scan,context:{receivesHra:true,parentCover:true}});
  assert.equal(scan.comparison,null);assert.equal(brief.numericCount,0);
  assert.ok(brief.items.some(x=>x.id==='section-123'));
  assert.throws(()=>taxDecisionBrief({form:{...form,year:'2025-26'},scan}),/same income year/);
});
