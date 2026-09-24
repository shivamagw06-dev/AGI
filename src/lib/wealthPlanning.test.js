import test from 'node:test';
import assert from 'node:assert/strict';
import { emptyWorkspace, householdSummary, fundOverlap, propertySummary, bondCashFlows, maturityLadder, monitoringAlerts, parseFundHoldings, safeUrl } from './wealthPlanning.js';
import { validateWorkspace, validateRecord } from './wealthWorkspace.js';
import { estimateOrdinaryTax } from './wealthTax.js';
const now = Date.parse('2026-09-24T00:00:00Z');
const person = {id:'p1',name:'Example owner',entity:'individual',residency:'resident',age:'66',year:'2025-26',regime:'new',taxable:'10000000',credits:'100000',special:'none'};
const bond = {id:'b1',name:'Example bond',issuer:'Example issuer',source:'https://example.com/terms',asOf:'2026-09-24',settlement:'2026-09-24',maturity:'2027-09-24',cost:'100000',principal:'100000',incomeTax:'30',gainTax:'12.5',credit:'Not rated',coupons:'2027-09-24,10000'};
test('household preserves taxpayer separation and debt, spending and reserve arithmetic',()=>{
 const w=emptyWorkspace(); w.people=[person,{...person,id:'p2'}]; w.expenses=50000; w.reserveMonths=12;
 w.holdings=[{id:'h',name:'FD',ownerId:'p1',kind:'FD',value:1000000,debt:200000,income:70000},{id:'h2',name:'Rent',ownerId:'p2',kind:'property',value:2000000,debt:0,income:100000}];
 const r=householdSummary(w);assert.equal(r.netWorth,2800000);assert.equal(r.people[0].income,70000);assert.equal(r.people[1].income,100000);assert.equal(r.reserveTarget,600000);assert.equal(r.concentration[1].weight,200/3);
 assert.throws(()=>householdSummary({...w,people:[]}),/owner/);
});
test('overlap uses minimum weights and reports partial coverage and mismatched dates',()=>{
 const r=fundOverlap({holdings:'INE123,20\nINE456,30',asOf:'2026-08-31'},{holdings:'INE123,10\nINE789,40',asOf:'2026-07-31'});
 assert.equal(r.overlap,10);assert.equal(r.coverageA,50);assert.equal(r.partial,true);assert.equal(r.comparableDates,false);
 assert.throws(()=>parseFundHoldings('AA,60\nBB,50'),/100/);assert.throws(()=>parseFundHoldings('AA,20\nAA,20'),/Duplicate/);
});
test('property groups never combine asking and registered evidence or different property types',()=>{
 const common={location:'Example city',propertyType:'land',asOf:'2026-09-01',area:1000};
 const groups=propertySummary([{...common,priceType:'asking',price:1000000},{...common,priceType:'asking',price:2000000},{...common,priceType:'registered',price:800000},{...common,propertyType:'apartment',priceType:'asking',price:4000000}],now);
 assert.equal(groups.length,3);assert.equal(groups[0].median,1500);assert.equal(groups[1].median,800);
 assert.throws(()=>propertySummary([{...common,price:1000000,asOf:'2027-01-01'}],now),/future/);
});
test('fixed income uses actual dated flows and does not count redemption as coupon income',()=>{
 const r=bondCashFlows(bond);assert.equal(r.netReceipts,107000);assert.equal(r.totalTax,3000);assert.ok(Math.abs(r.afterTaxIrr-7)<.01);
 const ladder=maturityLadder([bond,{...bond,id:'b2'}]);assert.equal(ladder[0].principal,200000);assert.equal(ladder[0].coupon,20000);assert.equal(ladder[0].net,214000);
 assert.throws(()=>bondCashFlows({...bond,coupons:'2028-01-01,10000'}),/Coupon/);
 assert.throws(()=>bondCashFlows({...bond,maturity:'2026-09-24'}),/Maturity/);
});
test('discount redemption gain receives only explicitly assumed gain tax',()=>{
 const r=bondCashFlows({...bond,cost:'90000',coupons:'',gainTax:'20'});assert.equal(r.totalTax,2000);assert.equal(r.netReceipts,98000);
});
test('tax uses new regime rebate, relief and cessation of relief above the marginal band',()=>{
 assert.equal(estimateOrdinaryTax({...person,taxable:1200000}).total,0);
 assert.equal(estimateOrdinaryTax({...person,taxable:1201000}).total,1040);
 assert.equal(estimateOrdinaryTax({...person,taxable:2400000}).total,312000);
 assert.equal(estimateOrdinaryTax(person).total,2951520);
});
test('surcharge marginal relief caps the jump immediately above a threshold',()=>{
 const threshold=estimateOrdinaryTax({...person,taxable:5000000}), next=estimateOrdinaryTax({...person,taxable:5001000});
 assert.equal(next.total-threshold.total,1040);assert.ok(next.marginalRelief>0);
});
test('old regime age exemptions and rebate are distinct',()=>{
 assert.equal(estimateOrdinaryTax({...person,age:80,regime:'old',taxable:1000000}).total,104000);
 assert.equal(estimateOrdinaryTax({...person,age:30,regime:'old',taxable:1000000}).total,117000);
 assert.equal(estimateOrdinaryTax({...person,regime:'old',taxable:500000}).total,0);
});
test('unsupported year, entity, residency and special income never receive a fabricated tax amount',()=>{
 for(const patch of [{year:'2026-27'},{entity:'HUF'},{residency:'nonresident'},{special:'review'},{regime:'x'}]) assert.equal(estimateOrdinaryTax({...person,...patch}).total,null);
});
test('review pack roundtrip drops unknown fields and rejects ownership errors, unsafe URLs and oversize data',()=>{
 const w=emptyWorkspace();w.people=[person];w.bonds=[bond];w.secret='not retained';
 assert.equal(validateWorkspace(w,now).secret,undefined);assert.equal(validateWorkspace(w,now).bonds[0].name,bond.name);
 assert.throws(()=>validateWorkspace({...w,people:[person,person]},now),/Duplicate/);
 assert.throws(()=>validateWorkspace({...w,bonds:[{...bond,source:'javascript:alert(1)'}]},now),/HTTPS/);
 assert.throws(()=>validateWorkspace({...w,people:Array(501).fill(person)},now),/maximum/);
 assert.equal(safeUrl('https://user:pass@example.com'),null);
 assert.throws(()=>validateRecord('people',{...person,age:'NaN'},w,now),/Age/);
});
test('monitor detects due actions and stale quotes but suppresses completed actions',()=>{
 const w=emptyWorkspace();w.people=[person];w.events=[{id:'e',name:'Review',due:'2026-09-25',status:'pending'},{id:'done',name:'Done',due:'2026-09-25',status:'completed'}];
 w.watchlist=[{id:'eq',name:'Example equity',assetClass:'equity',asOf:'2026-09-23T00:00:00Z'}];w.bonds=[{...bond,asOf:'2026-09-01'}];
 const alerts=monitoringAlerts(w,now);assert.ok(alerts.some(x=>x.id==='event:e'));assert.ok(alerts.some(x=>x.id==='watch:eq'));assert.ok(alerts.some(x=>x.id==='stale:bond:b1'));assert.ok(!alerts.some(x=>x.id==='event:done'));
});
