import test from 'node:test';
import assert from 'node:assert/strict';
import { emptyWorkspace } from './wealthPlanning.js';
import { validateReviewPack, createReviewPack, renderReviewReport } from './wealthReviewPack.js';
const now=Date.parse('2026-09-24T12:00:00Z');
const plan={capital:1000000,years:5,fdRate:7,incomeTax:30,inflation:5,reinvest:true};
const asset={id:'a',label:'Example',kind:'equity',growth:5,incomeYield:0,entryCost:0,exitCost:0,annualCost:0,gainsTax:12.5};
const input=()=>({version:'agi-review-pack-v2',workspace:emptyWorkspace(),comparison:{plan:{...plan},assets:[{...asset}]}});
test('review pack normalizes inputs and recomputes all results instead of trusting saved totals',()=>{
 const raw=input();raw.comparison.plan.secret='discard';raw.comparison.assets[0].secret='discard';raw.comparison.results=[{netWealth:999999999999}];
 const r=validateReviewPack(raw,now);assert.equal(r.plan.secret,undefined);assert.equal(r.assets[0].secret,undefined);
 const rebuilt=createReviewPack(r.workspace,r.plan,r.assets,now);assert.notEqual(rebuilt.comparison.results[0].netWealth,999999999999);
 assert.equal(validateReviewPack(rebuilt,now).assets[0].label,'Example');
});
test('nested objects, duplicate ids, reserved benchmark id and nonboolean reinvestment fail before state changes',()=>{
 for(const mutate of [r=>r.comparison.assets[0].observed={id:'q',source:'AMFI',asOf:{bad:true},price:100},r=>r.comparison.assets[0].property='text',r=>r.comparison.assets.push({...asset}),r=>r.comparison.assets[0].id='fd',r=>r.comparison.plan.reinvest='false',r=>r.comparison.plan.capital=[100],r=>r.comparison.assets[0].incomeYield=[],r=>r.workspace.people=[{id:'p',name:{bad:true}}]]){const r=input();mutate(r);assert.throws(()=>validateReviewPack(r,now));}
});
test('report is offline and escapes client text rather than executing it',()=>{
 const raw=input();raw.comparison.assets[0].label='<script>alert("test")</script>';
 const html=renderReviewReport(raw,now);
 assert.ok(html.includes('&lt;script&gt;'));assert.ok(!html.includes('<script>'));assert.ok(!html.includes('<img'));assert.ok(html.includes("default-src 'none'"));assert.ok(html.includes('@media print'));assert.ok(html.includes('Professional review pending'));assert.ok(html.includes('No records supplied.'));
});
test('duplicate saved observations and impossible calendar dates are rejected',()=>{
 const r=input(), q={id:'equity:TEST',name:'TEST',assetClass:'equity',price:100,asOf:'2026-09-24',source:'Test'};
 r.workspace.watchlist=[q,q];assert.throws(()=>validateReviewPack(r,now),/duplicate/);
 r.workspace.watchlist=[{...q,asOf:'2026-02-31'}];assert.throws(()=>validateReviewPack(r,now),/invalid/);
});
