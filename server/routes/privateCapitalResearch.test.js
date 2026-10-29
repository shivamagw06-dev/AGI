import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import createRouter from './privateCapitalResearch.js';
import { getPrivateCapitalResearch } from '../services/privateCapitalResearch.js';
import { filterCompanies, researchStats, csvCell } from '../../src/lib/privateCapital.js';
const data=getPrivateCapitalResearch();
test('snapshot preserves the company universe, missing financials and audit fixes',()=>{
 assert.equal(data.companies.length,100);assert.equal(new Set(data.companies.map(c=>c.id)).size,100);
 assert.equal(data.transactions.length,21);assert.equal(data.comparables.length,18);
 const s=researchStats(data.companies);assert.equal(s.revenue,12);assert.equal(s.valuations,19);assert.equal(s.fundingDates,81);assert.equal(s.pipeline,14);
 assert.equal(data.secondary.filter(c=>c.valuationUsdM===null).length,10);
 assert.ok(data.secondary.every(c=>!('score' in c)&&!('rank' in c)));
 assert.ok(data.management.every(c=>!('score' in c)));
 assert.equal(data.comparables[0].coreEvEbitda,null);
 assert.equal(data.companies.find(c=>c.name==='Sarvam AI').raisedUsdM,66.1);
 assert.ok(data.companies.find(c=>c.name==='Sarvam AI').notes.length>0);
});
test('filters use the requested universe and exports neutralise spreadsheet formulas',()=>{
 assert.equal(filterCompanies(data.companies,{search:'Dreamplug'})[0].name,'CRED');
 assert.equal(filterCompanies(data.companies,{coverage:'financials'}).length,12);
 assert.equal(filterCompanies(data.companies,{status:'IPO watch'}).length,14);
 assert.deepEqual(filterCompanies(data.companies,{coverage:'saved',saved:['sarvam-ai']}).map(c=>c.name),['Sarvam AI']);
 assert.equal(csvCell('=HYPERLINK("x")'),'"\'=HYPERLINK(""x"")"');
});
async function request(t,billing,token){const app=express();app.use('/research',createRouter({billing}));const server=app.listen(0,'127.0.0.1');await new Promise(resolve=>server.on('listening',resolve));t.after(()=>new Promise(resolve=>server.close(resolve)));const res=await fetch(`http://127.0.0.1:${server.address().port}/research`,{headers:token?{Authorization:`Bearer ${token}`}:{}});return {res,body:await res.json()};}
const member={starts_at:'2026-01-01T00:00:00Z',expires_at:'2099-01-01T00:00:00Z'};
const billing=(extra={})=>({user:async()=>({id:'regular-research-reader'}),config:async()=>({enabled:true}),membership:async()=>member,...extra});
test('anonymous requests cannot retrieve paid research',async t=>{const {res,body}=await request(t,billing());assert.equal(res.status,401);assert.ok(!body.companies);assert.equal(res.headers.get('cache-control'),'private, no-store');});
test('expired memberships are rejected',async t=>{const {res,body}=await request(t,billing({membership:async()=>({...member,expires_at:'2020-01-01'})}),'test');assert.equal(res.status,402);assert.ok(!body.companies);});
test('verified members receive the research',async t=>{const {res,body}=await request(t,billing(),'test');assert.equal(res.status,200);assert.equal(body.companies.length,100);});
test('subscription errors fail closed',async t=>{const {res,body}=await request(t,billing({config:async()=>{throw Error('offline');}}),'test');assert.equal(res.status,503);assert.ok(!body.companies);});
test('invalid sessions do not leak research',async t=>{const {res}=await request(t,billing({user:async()=>{throw Error('bad token');}}),'test');assert.equal(res.status,401);});
