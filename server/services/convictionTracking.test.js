import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {convictionView} from './convictionTracking.js';
import {makeBaseline,createIndiaTracker} from './indiaPortfolioTracking.js';
import {createPortfolioStore} from './portfolioCatalog.js';
const portfolios=JSON.parse(readFileSync(new URL('../data/indiaConvictionPortfolios.json',import.meta.url)));
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-9,`${a} != ${b}`);
const now=new Date('2026-10-05T04:00:00Z');
test('source counts, identities, overlaps and exact allocations reconcile',()=>{
 assert.deepEqual(portfolios.map(p=>p.holdings.length),[71,56]);
 assert.deepEqual(portfolios.map(p=>p.categories.map(c=>c.holdings.length)),[[19,18,7,19,17,17],[14,7,17,11,22,16]]);
 assert.equal(new Set(portfolios.flatMap(p=>p.holdings.map(h=>h.symbol))).size,100);
 for(const p of portfolios){
  near(p.holdings.reduce((s,h)=>s+h.weight,0),100);
  near(p.categories.reduce((s,c)=>s+c.weight,0),100);
  for(const c of p.categories){near(c.holdings.reduce((s,h)=>s+h.weight,0),100);assert.ok(c.holdings.every(h=>p.direction==='long'?h.score>0:h.score<0));}
  for(const h of p.holdings){assert.ok(h.instrumentKey.startsWith('NSE_EQ|'));near(h.weight,p.categories.reduce((s,c)=>s+(c.holdings.find(x=>x.symbol===h.symbol)?.weight||0)*c.weight/100,0));}
 }
});
test('long and theoretical short category sums equal combined return; no renormalization of missing data',()=>{
 for(const p of portfolios){
  const quotes=Object.fromEntries(p.holdings.map(h=>[h.symbol,{price:100,time:now.toISOString(),instrumentKey:h.instrumentKey}]));
  const base=makeBaseline(p,quotes,now);assert.ok(base);assert.deepEqual(base.categories,p.categories);
  const prices=Object.fromEntries(p.holdings.map((h,i)=>[h.symbol,{price:80+i,instrumentKey:h.instrumentKey}]));
  const nav=base.holdings.reduce((s,h)=>s+h.weight*prices[h.symbol].price/100,0);
  const t={history:[{date:'2026-10-05',nav}],positions:[]};
  const result=convictionView(p,base,[{session_date:'2026-10-05',prices}],t);
  near(result.returnPct,result.categories.reduce((s,c)=>s+c.returnPct*c.weight/100,0));
  near(result.returnPct,(p.direction==='short'?-1:1)*(nav-100));
  delete prices[p.categories[0].holdings[0].symbol];
  assert.equal(convictionView(p,base,[{session_date:'2026-10-05',prices}],{history:[],positions:[]}).categories[0].nav,null);
 }
});
test('short price rises lose money, decline profits; losses not capped and no prelaunch returns',()=>{
 const p=portfolios[1];
 assert.ok(convictionView(p,null,[],{history:[],positions:[]}).categories.every(c=>c.returnPct===null));
 const r=convictionView(p,null,[],{history:[{date:'2026-10-05',nav:80},{date:'2026-10-06',nav:250}],positions:[{returnPct:150}]});
 assert.equal(r.history[0].nav,120);assert.equal(r.nav,-50);assert.equal(r.returnPct,-150);assert.equal(r.positions[0].strategyReturnPct,-150);
});
test('fresh quote with changed identity cannot establish baseline',()=>{
 const p=portfolios[0],q=Object.fromEntries(p.holdings.map(h=>[h.symbol,{price:100,time:now.toISOString(),instrumentKey:h.instrumentKey}]));
 q[p.holdings[0].symbol].instrumentKey='changed';assert.equal(makeBaseline(p,q,now),null);
});
test('flat editor cannot change linked category weights',async()=>{
 await assert.rejects(()=>createPortfolioStore({}).save('in-conviction-long',{},'admin'),/category rebalance/);
});
