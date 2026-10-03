import test from 'node:test';
import assert from 'node:assert/strict';
import {evidence} from './providerCoverage.js';
import {growwTimestamp,getHistoricalCandleRange} from '../providers/groww.js';
test('candle evidence rejects malformed OHLC and does not call empty responses success',()=>{
 assert.equal(evidence([]).status,'empty');
 assert.equal(evidence([[1700000000,100,99,98,101]]).status,'invalid');
 assert.equal(evidence([[1700000000,null,105,98,101]]).status,'invalid');
 assert.equal(evidence([[1700000000,100,105,98,101,20,0]]).has_oi,true);
});
test('Groww naive timestamps are IST regardless of server timezone',()=>{
 assert.equal(growwTimestamp('2026-09-30T09:15:00'),Date.parse('2026-09-30T03:45:00Z')/1000);
});
test('new historical endpoint chunks requests, deduplicates boundaries and preserves legacy epoch timestamps',async()=>{
 const old=globalThis.fetch,token=process.env.GROWW_ACCESS_TOKEN;process.env.GROWW_ACCESS_TOKEN='test';const calls=[];
 globalThis.fetch=async(url)=>{calls.push(new URL(url));return {ok:true,json:async()=>({status:'SUCCESS',payload:{candles:[['2026-09-01T09:15:00',100,102,99,101,20,0]]}})};};
 try{
  const rows=await getHistoricalCandleRange('NSE','CASH','NIFTY',new Date('2026-08-20'),new Date('2026-09-30'),1);
  assert.equal(calls.length,2);assert.equal(calls[0].pathname,'/v1/historical/candles');assert.equal(calls[0].searchParams.get('groww_symbol'),'NSE-NIFTY');assert.equal(rows.length,1);assert.equal(typeof rows[0][0],'number');
  await assert.rejects(getHistoricalCandleRange('NSE','FNO','NIFTY26FUT',new Date('2026-08-20'),new Date('2026-09-30'),1),/canonical/);
 }finally{globalThis.fetch=old;if(token===undefined)delete process.env.GROWW_ACCESS_TOKEN;else process.env.GROWW_ACCESS_TOKEN=token;}
});

test('audit coalesces jobs, stores bounded samples and leaves streaming unverified',async()=>{
 const fs=await import('node:fs/promises');const os=await import('node:os');const path=await import('node:path');
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'coverage-test-'));
 const prior={fetch:globalThis.fetch,g:process.env.GROWW_ACCESS_TOKEN,u:process.env.UPSTOX_ACCESS_TOKEN,d:process.env.PROVIDER_COVERAGE_DIR};
 process.env.GROWW_ACCESS_TOKEN='test';process.env.UPSTOX_ACCESS_TOKEN='test';process.env.PROVIDER_COVERAGE_DIR=dir;
 globalThis.fetch=async(input)=>{
  const url=new URL(input);let data;
  if(url.pathname.includes('historical/candles'))data={candles:[['2026-09-30T09:15:00',100,102,99,101,10,0]]};
  else if(url.pathname.includes('historical-candle'))data={candles:[['2026-09-30T09:15:00+05:30',100,102,99,101,10,0]]};
  else if(url.pathname.endsWith('/expiries'))data=url.hostname.includes('groww')?{expiries:[]}:[];
  else if(url.pathname.endsWith('/contract'))data=[];
  else if(url.pathname.endsWith('/quote'))data={last_price:100};
  else if(url.pathname.endsWith('/quotes'))data={'NSE_INDEX:Nifty 50':{last_price:100}};
  else data={};
  return {ok:true,json:async()=>url.hostname.includes('groww')?{status:'SUCCESS',payload:data}:{status:'success',data}};
 };
 try {
  const {startCoverageAudit,coverageStatus}=await import('./providerCoverage.js');
  assert.equal(startCoverageAudit().started,true);assert.equal(startCoverageAudit().started,false);
  let status;for(let i=0;i<200;i++){status=await coverageStatus();if(!status.running)break;await new Promise(r=>setTimeout(r,5));}
  assert.equal(status.running,false);assert.ok(status.report.finished_at);
  assert.equal(status.report.providers.groww.spot_quote.recorded,true);
  assert.equal(status.report.providers.groww.stream.status,'not_tested');
  assert.equal(status.report.providers.upstox.expiries.status,'empty');
  assert.equal((await fs.stat(path.join(dir,'groww-spot_quote.json'))).mode&0o777,0o600);
 }finally{
  globalThis.fetch=prior.fetch;for(const[k,v]of [['GROWW_ACCESS_TOKEN',prior.g],['UPSTOX_ACCESS_TOKEN',prior.u],['PROVIDER_COVERAGE_DIR',prior.d]]){if(v===undefined)delete process.env[k];else process.env[k]=v;}
  await fs.rm(dir,{recursive:true,force:true});
 }
});
