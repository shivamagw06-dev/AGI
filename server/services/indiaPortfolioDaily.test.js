import test from 'node:test';
import assert from 'node:assert/strict';
import {dailyDue,validDailyCandle,createIndiaDailyReader,dailyValuation,completedDates} from './indiaPortfolioDaily.js';
import {createIndiaTracker} from './indiaPortfolioTracking.js';
const at=new Date('2026-10-05T10:30:00Z');
const base={startedAt:'2026-10-05T03:46:00Z',cashWeight:2,holdings:[{symbol:'A',weight:48,basePrice:100,instrumentKey:'A'},{symbol:'B',weight:50,basePrice:200,instrumentKey:'B'}]};
const price=(n,key)=>({price:n,time:'2026-10-05T00:00:00+05:30',instrumentKey:key});
test('4 pm IST boundary, weekends, NSE holidays and bounded catch-up',()=>{
 assert.equal(dailyDue(new Date('2026-10-05T10:29:59Z')),false);
 assert.equal(dailyDue(at),true);
 assert.equal(dailyDue(new Date('2026-10-02T11:00:00Z')),false);
 assert.equal(dailyDue(new Date('2026-10-03T11:00:00Z')),false);
 assert.deepEqual(completedDates(at,'2026-10-05'),['2026-10-05']);
});
test('daily candles must belong to the requested session and have valid OHLC',()=>{
 const c=['2026-10-05T00:00:00+05:30',100,110,95,105,1000];
 assert.ok(validDailyCandle(c,'2026-10-05'));
 assert.equal(validDailyCandle(c,'2026-10-06'),false);
 assert.equal(validDailyCandle([...c.slice(0,4),111],'2026-10-05'),false);
 assert.equal(validDailyCandle(['bad',100,110,95,105],'2026-10-05'),false);
});
test('provider uses daily candles, throttles calls, rejects stale days and stops on rate limits',async()=>{
 const urls=[],sleeps=[];let count=0;
 const read=createIndiaDailyReader({now:()=>at,token:()=> 'test',pause:async n=>sleeps.push(n),fetcher:async url=>{urls.push(url);count++;return {ok:count!==3,status:count===3?429:200,json:async()=>({status:'success',data:{candles:[[count===2?'2026-10-04T00:00:00+05:30':'2026-10-05T00:00:00+05:30',100,110,95,105]]}})};}});
 const out=await read('2026-10-05',['A','B','C','D'].map(symbol=>({symbol,instrumentKey:symbol})));
 assert.deepEqual(Object.keys(out),['A']);assert.equal(urls.length,3);assert.match(urls[0],/intraday\/A\/days\/1$/);assert.equal(sleeps[0],300);
});
test('composite uses frozen units including cash and rejects incomplete/mismatched evidence',()=>{
 assert.equal(dailyValuation(base,{A:price(110,'A'),B:price(180,'B')}),99.8);
 assert.equal(dailyValuation(base,{A:price(110,'A')}),null);
 assert.equal(dailyValuation(base,{A:price(110,'wrong'),B:price(180,'B')}),null);
});
function storage(){
 const db={agi_india_portfolio_tracking:[{portfolio_id:'in-value',baseline:base}],agi_india_daily_prices:[],agi_india_portfolio_marks:[]};
 return {db,from(name){let rows=db[name];return {select(){return this;},order(){return this;},range(start,end){return Promise.resolve({data:rows.slice(start,end+1)});},async upsert(row){const match=rows.find(x=>x.session_date===row.session_date&&x.portfolio_id===row.portfolio_id);if(match)Object.assign(match,row);else rows.push(row);return {};}};}};
}
test('partial prices persist, only missing symbols retry, reads never fetch and successful days are idempotent',async()=>{
 const client=storage();let time=new Date('2026-10-05T10:29:00Z'),calls=[];
 const tracker=createIndiaTracker({client,now:()=>time,readQuotes:async()=>{throw Error('no launch fetch expected');},readDaily:async(date,instruments)=>{calls.push(instruments.map(x=>x.symbol));return calls.length===1?{A:price(110,'A')}:{B:price(180,'B')};}});
 const portfolios=[{id:'in-value',market:'india',holdings:base.holdings}];
 await tracker.collect(portfolios);assert.equal(calls.length,0);
 time=at;await tracker.collect(portfolios);assert.equal(client.db.agi_india_portfolio_marks.length,0);
 let response=await tracker.read(portfolios);assert.equal(response.portfolios[0].nav,null);assert.equal(response.portfolios[0].positions[0].history.length,1);
 await tracker.collect(portfolios);assert.deepEqual(calls,[['A','B'],['B']]);
 response=await tracker.read(portfolios);assert.equal(response.portfolios[0].nav,99.8);assert.ok(Math.abs(response.portfolios[0].returnPct+0.2)<1e-10);
 assert.equal(response.portfolios[0].history.length,1);assert.equal(response.portfolios[0].status,'daily_recorded');
 await tracker.collect(portfolios);assert.equal(calls.length,2);assert.equal(client.db.agi_india_portfolio_marks.length,1);
 assert.equal(base.holdings[0].basePrice,100);
});
