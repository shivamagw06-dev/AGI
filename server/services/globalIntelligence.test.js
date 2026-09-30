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
