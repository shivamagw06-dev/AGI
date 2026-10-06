import test from 'node:test';
import assert from 'node:assert/strict';
import {allocate,valueAccount,rebalanceAccount,advanceLedger} from './portfolioRebalanceMath.js';
const target=(symbol,weight=100)=>({holdings:[{symbol,name:symbol,weight}],cashWeight:100-weight});
const q=(a,b)=>({A:{price:a},B:{price:b}});
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);
test('replace stock preserves value and cumulative return',()=>{
 const a=allocate(target('A'),100,q(100,20));near(valueAccount(a,q(110,20)),110);
 const r=rebalanceAccount(a,target('B'),q(110,20),0);near(r.postNav,110);near(valueAccount(r.account,q(100,21)),115.5);near(r.cost,0);
});
test('cash and round trip trading costs reconcile',()=>{
 const a=allocate(target('A',60),100,q(100,20));near(a.cash,40);
 const r=rebalanceAccount(a,target('B',50),q(100,20),10);near(valueAccount(r.account,q(100,20)),r.preNav-r.cost);near(r.cost,r.traded*.001);assert.ok(r.cost>0);
});
test('short direction and short proceeds do not add equity',()=>{
 const a=allocate(target('A'),100,q(100,20),'short');near(a.cash,200);near(valueAccount(a,q(90,20)),110);
 const r=rebalanceAccount(a,target('B'),q(90,20),0,'short');near(valueAccount(r.account,q(90,18)),121);assert.ok(r.account.holdings[0].units<0);
});
test('missing prices and mismatched instruments are refused',()=>{
 const a=allocate(target('A'),100,q(100,20));assert.throws(()=>rebalanceAccount(a,target('B'),{A:{price:110}},0));
 assert.throws(()=>allocate({holdings:[{name:'A',symbol:'A',weight:100,instrumentKey:'x'}]},100,{A:{price:10,instrumentKey:'y'}}));
});
test('retries are idempotent, prior history survives, historical removal remains audited',()=>{
 const p=target('A'),s={account:allocate(p,100,q(100,20)),portfolio:p,history:[{date:'2026-10-05',nav:100}],events:[],lastDate:'2026-10-05',direction:'long',pending:{target:target('B'),effectiveDate:'2026-10-06',feeBps:0}};
 const r=advanceLedger(s,'2026-10-06',q(110,20),'now');assert.deepEqual(r.history[0],s.history[0]);assert.equal(s.pending.target.holdings[0].symbol,'B');near(r.history[1].nav,110);assert.equal(r.events[0].trades[0].symbol,'A');assert.deepEqual(advanceLedger(r,'2026-10-06',q(999,999),'later'),r);assert.throws(()=>advanceLedger(s,'2026-10-07',q(110,20),'later'));
});
test('category overlap totals reconcile after rebalance with costs',()=>{
 const prices=q(100,20),ca=allocate(target('A'),100,prices),cb=allocate(target('B'),100,prices);
 const combined={holdings:[{name:'A',symbol:'A',weight:50},{name:'B',symbol:'B',weight:50}]};
 const s={account:allocate(combined,100,prices),portfolio:combined,history:[],events:[],lastDate:'2026-10-05',direction:'long',categories:[{name:'X',weight:50,account:ca,history:[]},{name:'Y',weight:50,account:cb,history:[]}],pending:{target:{...target('B'),categories:[{name:'X',holdings:target('B').holdings},{name:'Y',holdings:target('B').holdings}]},effectiveDate:'2026-10-06',feeBps:10}};
 const r=advanceLedger(s,'2026-10-06',q(110,18),'now');near(valueAccount(r.account,q(110,18)),r.history[0].nav);near(r.categories.reduce((sum,c)=>sum+c.weight/100*c.history.at(-1).nav,0),r.history[0].nav);
});
