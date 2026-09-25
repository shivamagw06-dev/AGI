import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseEvidenceCsv, mapEvidenceCsv, parseUpstoxFundOrders, reconcileTaxEvidence, restoreTaxReview } from './taxEvidence.js';
import { housePropertySchedule } from './taxProperty.js';

test('CSV import maps quoted values and keeps tax credit separate from taxable income',()=>{
  const parsed=parseEvidenceCsv('Kind,Amount,TDS,Ref,Date\r\ndeposit_interest,"1,25,000",12500,FD-1,2025-12-31\r\n');
  const rows=mapEvidenceCsv(parsed,{amount:'1',credit:'2',category:'0',reference:'3',date:'4',defaultCategory:'other',batchId:'a',source:'Bank',ownerId:'a',year:'2025-26'});
  assert.equal(rows[0].amount,125000);assert.equal(rows[0].credit,12500);
  const r=reconcileTaxEvidence(rows,'a','2025-26',{depositInterest:'125000'});
  assert.equal(r.totals.deposit_interest,125000);assert.equal(r.totals.tax_credit,12500);
  assert.equal(r.comparisons.find(x=>x.category==='deposit_interest').status,'matched');
  assert.equal(r.unmatched,1);
});
test('imports do not silently accept bad dates, negative values or duplicate evidence as independent facts',()=>{
  const parsed=parseEvidenceCsv('Income,Reference\n-120,FD-2');
  assert.throws(()=>mapEvidenceCsv(parsed,{amount:'0',reference:'1',defaultCategory:'deposit_interest',batchId:'b',ownerId:'a',year:'2025-26',source:'bank'}),/non-negative/);
  assert.throws(()=>parseEvidenceCsv('A,B\n"unterminated'),/Unclosed/);
  const one={id:'a',ownerId:'a',year:'2025-26',source:'AIS',category:'salary',amount:100000,credit:0,reference:'R1',reviewed:true};
  const two={...one,id:'b',source:'Form 16'};
  const r=reconcileTaxEvidence([one,two],'a','2025-26',{salary:'100000'});
  assert.equal(r.warnings.length,1);assert.equal(r.comparisons[0].status,'difference');
});
test('completed Upstox sell remains investment evidence, pending orders never become gains',()=>{
  const orders=parseUpstoxFundOrders(JSON.stringify({data:[
    {order_id:'a',transaction_type:'SELL',status:'COMPLETED',amount:1000,quantity:10,order_timestamp:'2025-06-02 12:00:00'},
    {order_id:'b',transaction_type:'BUY',status:'OPEN',amount:1000,quantity:0,order_timestamp:'2025-06-03 12:00:00'},
  ]}),{ownerId:'a',year:'2025-26',batchId:'x'});
  assert.equal(orders[0].status,'COMPLETED');assert.equal(orders[1].status,'OPEN');
  const summary=reconcileTaxEvidence(orders,'a','2025-26',{});
  assert.equal(summary.investmentOrders,2);assert.equal(summary.totals.capital_gains,undefined);
  assert.throws(()=>parseUpstoxFundOrders(JSON.stringify({data:[
    {order_id:'c',transaction_type:'BUY',status:'COMPLETED',amount:10,order_timestamp:'2026-06-01 12:00:00'}]}),
  {ownerId:'a',year:'2025-26',batchId:'x'}),/outside the selected income year/);
});
test('property schedule is only available after classification and keeps loss setoff outside the model',()=>{
  assert.throws(()=>housePropertySchedule({rent:'100000',municipal:'0',interest:'0'}),/Confirm/);
  const r=housePropertySchedule({rent:'1200000',municipal:'100000',interest:'300000',confirmedHouseProperty:true});
  assert.equal(r.netAnnualValue,1100000);assert.equal(r.standardDeduction,330000);assert.equal(r.propertyIncome,470000);
});
test('saved review restores cases without trusting confirmation or row review flags',()=>{
  const saved={version:1,year:'2025-26',case:{year:'2025-26',age:'66',salary:'0',depositInterest:'1000',savingsInterest:'0',
    eligible80c:'0',eligible80d:'0',eligibleNps:'0',hasRental:false,hasGains:false,hasBusiness:false,hasForeign:false,otherIncome:false,
    recordsConfirmed:true,claimsConfirmed:true},evidence:[{category:'deposit_interest',source:'Bank',reference:'1',
    date:'2025-07-01',amount:1000,credit:100,reviewed:true}]};
  const restored=restoreTaxReview(JSON.stringify(saved),'new-owner');
  assert.equal(restored.form.recordsConfirmed,false);
  assert.equal(restored.form.claimsConfirmed,false);
  assert.equal(restored.evidence[0].reviewed,false);
  assert.equal(restored.evidence[0].ownerId,'new-owner');
  assert.throws(()=>restoreTaxReview(JSON.stringify({...saved,evidence:[{...saved.evidence[0],credit:-1}]}),'owner'),/Invalid evidence/);
});
