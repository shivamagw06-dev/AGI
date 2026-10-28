import {test} from 'node:test';
import assert from 'node:assert/strict';
import {sourceUrl,validateManifest,assembleDataset,collectDataset,collectTrendlyneBrowser} from './trendlyneBrowser.js';
const d={id:'momentum',kind:'screener',url:'https://trendlyne.com/stock-screeners/',headers:['Stock','Price'],keyColumn:0,datePattern:'^As of (\\d{4}-\\d{2}-\\d{2})$',countPattern:'^Total (\\d+)$',tableSelector:'#table',dateSelector:'#date',countSelector:'#count',readySelector:'#signedin',singlePage:true};
const page={headers:d.headers,rows:[['ABC','100'],['XYZ','200']]};
test('allow only Trendlyne HTTPS source URLs',()=>{assert.ok(sourceUrl(d.url));for(const u of ['http://trendlyne.com','https://trendlyne.com.evil.test','https://localhost','https://u:p@trendlyne.com','https://trendlyne.com:444'])assert.throws(()=>sourceUrl(u));});
test('unverified configuration cannot collect',()=>assert.throws(()=>validateManifest({version:1,verified:false,datasets:[]})));
test('actual source date and exact row count retained',()=>{const r=assembleDataset(d,[page],'As of 2026-10-15','Total 2');assert.equal(r.asOf,'2026-10-15');assert.equal(r.expectedRows,2);assert.match(r.tables[0],/ABC/);});
test('missing or ambiguous metadata is blocked',()=>{assert.throws(()=>assembleDataset(d,[page],'today','Total 2'));assert.throws(()=>assembleDataset(d,[page],'As of 2026-10-15','Showing 2 of 20'));});
test('truncation, changed headers and duplicate pages are blocked',()=>{assert.throws(()=>assembleDataset(d,[page],'As of 2026-10-15','Total 3'));assert.throws(()=>assembleDataset(d,[page,page],'As of 2026-10-15','Total 4'));assert.throws(()=>assembleDataset(d,[{...page,headers:['Other']}],'As of 2026-10-15','Total 2'));});
test('expired login stops before reading data',async()=>{let read=false;await assert.rejects(collectDataset({goto:async()=>({status:()=>200}),url:()=> 'https://trendlyne.com/accounts/login/',locator:()=>{read=true;}},d),/LOGIN_REQUIRED/);assert.equal(read,false);});
test('rate limits stop without retries',async()=>{await assert.rejects(collectDataset({goto:async()=>({status:()=>429})},d),/RATE_LIMITED/);});
test('missing session configuration blocks before launching',async()=>{let launched=false;await assert.rejects(collectTrendlyneBrowser({env:{},launch:()=>{launched=true;}}),/SETUP_REQUIRED/);assert.equal(launched,false);});
test('collects all pages using disabled next control and exact total',async()=>{
 let index=0;
 const fake={goto:async()=>({status:()=>200}),url:()=>d.url,waitForFunction:async()=>{},locator:s=>({
  first(){return this;},isVisible:async()=>s===d.readySelector,
  innerText:async()=>s===d.dateSelector?'As of 2026-10-15':'Total 2',
  evaluate:async()=>({headers:d.headers,rows:[page.rows[index]]}),
  count:async()=>1,isDisabled:async()=>index===1,getAttribute:async()=>null,click:async()=>{index++;}
 })};
 const result=await collectDataset(fake,{...d,singlePage:false,nextSelector:'#next'});
 assert.equal(result.expectedRows,2);assert.equal(index,1);assert.match(result.tables[0],/XYZ/);
});
