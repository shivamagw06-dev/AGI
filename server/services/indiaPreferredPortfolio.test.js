import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {INDIA_IDS,makeBaseline,valueBaseline} from './indiaPortfolioTracking.js';
import {validatePortfolio} from './portfolioCatalog.js';
const p=JSON.parse(readFileSync(new URL('../data/indiaPreferredPortfolio.json',import.meta.url)));
test('Preferred is fully allocated, tracked and supports all 17 launch positions',()=>{
 validatePortfolio(p);assert.ok(INDIA_IDS.includes(p.id));assert.equal(p.holdings.length,17);
 assert.equal(p.holdings.reduce((s,h)=>s+Math.round(h.weight*100),0),10000);
 assert.equal(new Set(p.holdings.map(h=>h.instrumentKey)).size,17);
 const now=new Date('2026-10-05T03:46:00Z');
 const quotes=Object.fromEntries(p.holdings.map(h=>[h.symbol,{price:100,time:now.toISOString(),instrumentKey:h.instrumentKey}]));
 const base=makeBaseline({...p,revision:1},quotes,now);assert.equal(base.holdings.length,17);
 assert.ok(Math.abs(valueBaseline(base,quotes,now).nav-100)<1e-10);
 delete quotes.LENSKART;assert.equal(makeBaseline(p,quotes,now),null);
});
