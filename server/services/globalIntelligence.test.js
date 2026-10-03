import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { normaliseFeed, eventHash, distanceKm, matchAssets, validateAsset, validateReview } from './globalIntelligence/model.js';
import { fetchJson } from './globalIntelligence/collector.js';
import createRouter from '../routes/globalIntelligence.js';
const quake={id:'one',geometry:{type:'Point',coordinates:[70,22]},properties:{title:'M5 event',time:1750000000000,updated:1750000000001,url:'https://earthquake.usgs.gov/earthquakes/eventpage/one',mag:5}};
test('USGS normalises real coordinates, timestamps and deduplicates IDs',()=>{
 const rows=normaliseFeed('usgs',{features:[quake,quake,{...quake,id:'bad',geometry:{type:'Point',coordinates:[181,null]}}]});
 assert.equal(rows.length,1);assert.equal(rows[0].latitude,22);assert.equal(rows[0].published_at,null);
 assert.equal(eventHash({...rows[0],last_seen_at:'tomorrow',source_updated_at:'later'}),rows[0].content_hash);
 assert.notEqual(eventHash({...rows[0],latitude:23}),rows[0].content_hash);
});
test('EONET selects the latest point; no geometry is not invented',()=>{
 const rows=normaliseFeed('eonet',{events:[{id:'fire',title:'Fire',categories:[{title:'Wildfires'}],geometry:[{type:'Point',coordinates:[10,20],date:'2026-09-01'},{type:'Point',coordinates:[11,21],date:'2026-09-02'}],sources:[{url:'javascript:alert(1)'}]},{id:'missing',title:'Unknown',geometry:{}}]});
 assert.equal(rows.length,1);assert.equal(rows[0].longitude,11);assert.equal(rows[0].source_updated_at,null);assert.match(rows[0].source_url,/eonet.gsfc/);
 assert.throws(()=>normaliseFeed('bad',{}));assert.throws(()=>normaliseFeed('usgs',{}));
});
test('proximity works across the date line and remains tentative',()=>{
 const a={latitude:0,longitude:179.9},b={id:'a',latitude:0,longitude:-179.9};
 assert.ok(distanceKm(a,b)<23);assert.equal(matchAssets(a,[b])[0].asset_id,'a');assert.match(matchAssets(a,[b])[0].basis,/not established/);
 assert.equal(matchAssets(a,[{...b,latitude:20}]).length,0);
});
test('review publication requires evidence and uncertainty; assets reject unsafe links',()=>{
 assert.throws(()=>validateReview({status:'published',assessment:'impact',content_hash:'a'.repeat(64)}));
 assert.equal(validateReview({status:'rejected',assessment:'insufficient evidence',content_hash:'a'.repeat(64)}).status,'rejected');
 assert.throws(()=>validateAsset({symbol:'TEST',company:'A',name:'B',sector:'C',relationship:'D',evidence_note:'E',location_precision:'area',confidence:'confirmed',latitude:0,longitude:0,source_url:'javascript:alert(1)'}));
});
test('fetch limits reject non-OK and malformed sources',async()=>{
 await assert.rejects(fetchJson('https://example.com',async()=>new Response('{}',{status:500})),/500/);
 await assert.rejects(fetchJson('https://example.com',async()=>new Response('not json')));
 await assert.rejects(fetchJson('https://example.com',async()=>new Response('x'.repeat(4000001))),/size limit/);
});
test('public read, protected writes, and watchlists use verified identity only',async()=>{
 let saved;
 const db=()=>({from:table=>({select:()=>({eq:()=>table==='gi_assets'?Promise.resolve({data:[{symbol:'NTPC'}]}):{maybeSingle:async()=>({data:{symbols:['NTPC']}})}}),upsert:async row=>{saved=row;return{data:null};}})});
 const app=express();app.use('/api',createRouter({database:db,snapshot:async()=>({events:[]}),verifiedUser:async req=>req.headers.authorization==='Bearer valid'?{id:'verified-user'}:null,requireAdmin:(req,res)=>res.status(403).json({error:'admin only'})}));
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const base=`http://127.0.0.1:${server.address().port}/api`;
 try{
 assert.equal((await fetch(base+'/snapshot')).status,200);
 assert.equal((await fetch(base+'/collect',{method:'POST'})).status,403);
 assert.equal((await fetch(base+'/admin')).status,403);
 assert.equal((await fetch(base+'/watchlist')).status,401);
 const response=await fetch(base+'/watchlist',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer valid'},body:JSON.stringify({user_id:'attacker',symbols:['NTPC']})});
 assert.equal(response.status,200);assert.equal(saved.user_id,'verified-user');
 assert.equal((await fetch(base+'/watchlist',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer valid'},body:JSON.stringify({symbols:['UNKNOWN']})})).status,400);
 }finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});

const {extractDocument,documentDiff,fetchDocument,DOCUMENTS}=await import('./globalIntelligence/documents.js');
const {buildInbox,validatePreferences}=await import('./globalIntelligence/workflows.js');
test('document parser ignores navigation/scripts, normalises HTML and rejects blocking pages',()=>{
 const body='<p>Company operates an aluminium refinery at the documented location. The current capacity and project disclosures are available in the official annual report.</p>';
 const a=extractDocument(`<title>Company</title><header>time 123</header><main>${body}<script>danger()</script></main>`);
 const b=extractDocument(`<title>Company</title><header>time 999</header><main>${body}<script>different()</script></main>`);
 assert.equal(a.hash,b.hash);assert.ok(!a.text.includes('danger'));assert.ok(!a.text.includes('999'));
 assert.throws(()=>extractDocument('<title>Access Denied</title><p>blocked</p>'),/blocking/);
 assert.throws(()=>extractDocument('<main>Loading…</main>'),/sufficient/);
 assert.deepEqual(documentDiff(null,a.text),{added:0,removed:0,added_excerpt:'',removed_excerpt:''});
 const diff=documentDiff('A\nB','A\nC');assert.equal(diff.added,1);assert.equal(diff.removed,1);assert.equal(diff.added_excerpt,'C');
});
test('official document fetch rejects arbitrary URLs, redirects, non-HTML and oversized responses',async()=>{
 let called=false;await assert.rejects(fetchDocument('https://127.0.0.1',async()=>{called=true;}),/allowlisted/);assert.equal(called,false);
 await assert.rejects(fetchDocument(DOCUMENTS[0].url,async(url,options)=>{assert.equal(options.redirect,'error');return new Response('moved',{status:302,headers:{'Content-Type':'text/html'}});}),/302/);
 await assert.rejects(fetchDocument(DOCUMENTS[0].url,async()=>new Response('{}',{headers:{'Content-Type':'application/json'}})),/HTML/);
 await assert.rejects(fetchDocument(DOCUMENTS[0].url,async()=>new Response('x'.repeat(2000001),{headers:{'Content-Type':'text/html'}})),/size limit/);
});
test('inbox isolates watched companies, excludes baselines/stale reviews and starts at opt-in',()=>{
 const now=Date.parse('2026-10-01T12:00:00Z'),at='2026-10-01T11:00:00Z';
 const preferences={enabled:true,enabled_at:'2026-10-01T10:00:00Z',observations:true,assessments:true,documents:true,last_read_at:'2026-10-01T10:30:00Z'};
 const event={id:'e',title:'Event',content_hash:'current',first_seen_at:at,matches:[{symbol:'NTPC'}],review:{status:'published',content_hash:'current',company_symbols:['NTPC'],reviewed_at:at}};
 const input={now,preferences,watch:['NTPC'],events:[event],monitors:[{id:'d',symbol:'NTPC',title:'Official page'}],versions:[{id:1,monitor_id:'d',baseline:true,captured_at:at},{id:2,monitor_id:'d',baseline:false,captured_at:at}]};
 assert.equal(buildInbox(input).length,3);assert.ok(buildInbox(input).every(i=>i.unread));
 assert.equal(buildInbox({...input,watch:['IOC']}).length,0);
 assert.equal(buildInbox({...input,preferences:{...preferences,enabled:false}}).length,0);
 assert.equal(buildInbox({...input,preferences:{...preferences,enabled_at:'2026-10-01T11:30:00Z'}}).length,0);
 assert.equal(buildInbox({...input,events:[{...event,review:{...event.review,content_hash:'old'}}]}).length,2);
 assert.equal(buildInbox({...input,preferences:{...preferences,last_read_at:at}}).filter(i=>i.unread).length,0);
 assert.throws(()=>validatePreferences({enabled:'yes'}));
 assert.throws(()=>validateReview({status:'rejected',assessment:'a',content_hash:'a'.repeat(64),company_symbols:['NTPC',123]}));
});
test('alerts and document writes require auth; preferences ignore spoofed ownership',async()=>{
 let saved;
 const db=()=>({rpc:async(name,row)=>{saved=row;return{data:{enabled:row.p_enabled}};}});
 const app=express();app.use('/api',createRouter({database:db,documents:async()=>({monitors:[],versions:[]}),verifiedUser:async req=>req.headers.authorization==='Bearer valid'?{id:'verified'}:null,requireAdmin:(req,res)=>res.status(403).json({error:'admin only'})}));
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const base=`http://127.0.0.1:${server.address().port}/api`;
 try{
 assert.equal((await fetch(base+'/alerts')).status,401);
 assert.equal((await fetch(base+'/admin/documents')).status,403);
 assert.equal((await fetch(base+'/admin/documents/collect',{method:'POST'})).status,403);
 assert.equal((await fetch(base+'/documents')).status,200);
 const options={method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer valid'}};
 assert.equal((await fetch(base+'/alerts',{...options,body:JSON.stringify({enabled:true,observations:false,assessments:true,documents:true,user_id:'attacker',enabled_at:'1900-01-01'})})).status,200);
 assert.equal(saved.p_user,'verified');assert.equal(saved.enabled_at,undefined);
 assert.equal((await fetch(base+'/alerts/read',{...options,body:JSON.stringify({through:'2099-01-01'})})).status,400);
 }finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});

test('spatial export separates observation and approximate company layers without private fields',async()=>{
 const {intelligenceGeoJSON}=await import('../../src/pages/intelligence/spatialExport.js');
 const result=intelligenceGeoJSON([{id:'event',latitude:22,longitude:70,title:'Observation',reviewer:'private'}],[{symbol:'NTPC',latitude:23,longitude:71,verified_by:'private',location_precision:'Approximate'}]);
 assert.deepEqual(result.features[0].geometry.coordinates,[70,22]);assert.equal(result.features[1].properties.layer,'company_area');assert.ok(!JSON.stringify(result).includes('private'));
});
