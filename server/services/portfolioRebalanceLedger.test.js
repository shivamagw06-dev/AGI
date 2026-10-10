import test from 'node:test';
import assert from 'node:assert/strict';
import {validateSchedule,ledgerView,createRebalanceLedger} from './portfolioRebalanceLedger.js';
const p={id:'x',name:'Example',market:'usa',category:'Test',asOf:'2026-10-05',holdings:[{name:'A',symbol:'A',weight:100}],cashWeight:0};
const request={effectiveDate:'2026-10-07',feeBps:0,reason:'Replace due to review',target:p};
test('reject backdates, impossible dates, weekends, bad costs and missing reason',()=>{
 const now=new Date('2026-10-06T13:00:00Z');assert.equal(validateSchedule(p,request,now).effectiveDate,'2026-10-07');
 for(const patch of [{effectiveDate:'2026-10-06'},{effectiveDate:'2026-10-03'},{effectiveDate:'2026-10-10'},{effectiveDate:'2026-02-30'},{feeBps:-1},{feeBps:Infinity},{reason:''}])assert.throws(()=>validateSchedule(p,{...request,...patch},now));
});
test('Conviction categories validated and duplicate stocks across sleeves are aggregated',()=>{
 const portfolio={...p,conviction:true,categories:[{name:'X',weight:50},{name:'Y',weight:50}]};const target={...p,categories:[{name:'X',holdings:p.holdings},{name:'Y',holdings:p.holdings}]};
 const r=validateSchedule(portfolio,{...request,target},new Date('2026-10-06T13:00Z'));assert.equal(r.target.holdings.length,1);assert.equal(r.target.holdings[0].weight,100);
 assert.throws(()=>validateSchedule(portfolio,{...request,target:{...target,categories:[target.categories[0],target.categories[0]]}},new Date('2026-10-06T13:00Z')));
});
test('public ledger hides administrator identity',()=>{
 const row={portfolio_id:'x',revision:1,document:{portfolio:p,basis:'test',startedAt:'2026-10-05',lastDate:'2026-10-05',history:[{date:'2026-10-05',nav:100}],events:[{type:'scheduled',requestedBy:'private-user',actor:'private-user'}],categories:[],account:{holdings:[]}}};const v=ledgerView(row);assert.equal(v.events[0].requestedBy,undefined);assert.equal(v.events[0].actor,undefined);assert.equal(v.nav,100);
});
test('CAS write rejects stale revisions and duplicate requests',async()=>{
 const row={portfolio_id:'x',revision:5,document:{portfolio:p,history:[],events:[],pending:{id:'exists'}}};const client={from(){return {select(){return this;},eq(){return this;},maybeSingle:async()=>({data:row})};}};
 const ledger=createRebalanceLedger({client});await assert.rejects(ledger.schedule('x',{...request,ledgerRevision:4},'admin'),/Reload/);await assert.rejects(ledger.schedule('x',{...request,ledgerRevision:5},'admin'),/already pending/);
});
test('new routes enforce admin access for writes and private ledgers',async()=>{
 const {default:express}=await import('express');const {default:createRouter}=await import('../routes/portfolioCatalog.js');let writes=0;
 const row={portfolio_id:'private',revision:1,document:{portfolio:{...p,visibility:'admin'},history:[],events:[],categories:[],account:{holdings:[]}}};
 const app=express();app.use(express.json());app.use(createRouter({ledger:()=>({get:async()=>row,list:async()=>[row],schedule:async()=>{writes++;return row;}}),admin:(req,res,next)=>{if(req.get('authorization')!=='Bearer admin')return res.sendStatus(403);req.strategyLabActor={id:'admin'};next();}}));
 const server=app.listen(0);await new Promise(r=>server.once('listening',r));const base=`http://127.0.0.1:${server.address().port}`;
 try{for(const path of ['/private/ledger','/admin/ledger-catalog'])assert.equal((await fetch(base+path)).status,403);assert.equal((await fetch(base+'/x/rebalance',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status,403);assert.equal(writes,0);assert.equal((await fetch(base+'/private/ledger',{headers:{Authorization:'Bearer admin'}})).status,200);}finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});
