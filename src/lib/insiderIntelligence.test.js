import test from 'node:test';
import assert from 'node:assert/strict';
import {buildIntelligence,filingKind,filingKey,newWatchlistFilings,sourceLink,number} from './insiderIntelligence.js';
const row=(extra={})=>({company_name:'Example',symbol:'EX',person:'A',reported_on:'2026-09-20',action:'Acquisition',mode:'Market Purchase',is_open_market:'true',value:100,quantity:10,regime:'insider',...extra});
test('clusters count names, not repeat filings; unrelatedness is not assumed',()=>{
 const c=buildIntelligence([row(),row(),row({person:'B'}),row({person:'C'}),row({person:' A ',quantity:20})],'2026-09-26')[0];
 assert.equal(c.buyers,3);assert.equal(c.buys.length,4);assert.equal(c.buyValue,400);assert.match(c.signals[0].detail,/not been verified/);
});
test('30-day signals are anchored to today, not last available buying date',()=>{
 const c=buildIntelligence(['A','B','C'].map(person=>row({person,reported_on:'2026-05-01'})),'2026-09-26')[0];assert.equal(c.signals.length,0);assert.equal(c.rows.length,3);
});
test('reporting windows do not overlap and future or takeover filings are excluded',()=>{
 const c=buildIntelligence([row({reported_on:'2026-08-28'}),row({reported_on:'2026-08-27'}),row({reported_on:'2026-09-27'}),row({regime:'sast'})],'2026-09-26')[0];assert.equal(c.buys.length,1);assert.equal(c.priorBuys,1);assert.equal(c.rows.length,2);
});
test('invocations, releases, block deals and grants do not masquerade as conviction buying',()=>{
 assert.equal(filingKind(row({mode:'Market Sale'})),'Conflicting market classification');
 assert.equal(filingKind(row({action:'Invoke',mode:'Market Sale'})),'pledge invocation');
 assert.equal(filingKind(row({mode:'Revocation Of Pledge'})),'pledge release');
 assert.equal(filingKind(row({mode:'Block Deal',is_open_market:'false'})),'block deal');
 const c=buildIntelligence([row({mode:'ESOP',is_open_market:'false'})],'2026-09-26')[0];assert.equal(c.buyers,0);
});
test('watchlist detects new or changed evidence, not already saved rows or other companies',()=>{
 const first=row(),next=row({quantity:25}),other=row({company_name:'Other'});
 const saved={example:{company:'Example',seen:[filingKey(first)]}};
 const alerts=newWatchlistFilings(buildIntelligence([first,next,other],'2026-09-26'),saved);assert.equal(alerts.length,1);assert.equal(alerts[0].row.quantity,25);
});
test('missing value is not zero and only safe source links are emitted',()=>{
 assert.equal(number(''),null);assert.equal(number(null),null);assert.equal(number(0),0);
 assert.equal(sourceLink({source_url:'javascript:alert(1)'}),null);assert.equal(sourceLink({source_url:'https://www.nseindia.com/filing'}),'https://www.nseindia.com/filing');
 const c=buildIntelligence([row({value:null})],'2026-09-26')[0];assert.equal(c.valued,0);
});
test('US planned trades and derivative transactions do not become conviction signals',()=>{
 const c=buildIntelligence([row({country:'US',transaction_code:'P',trade_id:'1',planned:'true'}),row({country:'US',transaction_code:'P',trade_id:'2',derivative:'true'}),row({country:'US',transaction_code:'P',trade_id:'3',planned:'unknown',derivative:'false'})],'2026-09-26')[0];
 assert.equal(c.buys.length,1);assert.equal(c.rows.length,3);assert.equal(c.signals[0].title,'Purchase disclosed');
});
