import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { makeLibrary } from './model.mjs';
const root=path.resolve(import.meta.dirname,'../..'),read=p=>JSON.parse(fs.readFileSync(path.join(root,p)));
const profiles=read('src/data/investorProfiles/index.json').map(e=>{const f=`src/data/investorProfiles/holdings/${e.country.toLowerCase()}-${e.slug}.json`;return fs.existsSync(path.join(root,f))?{...read(f),category:e.category||'individual'}:null;}).filter(Boolean);
const sec=JSON.parse(gunzipSync(fs.readFileSync(path.join(root,'scripts/holdings_activity/sec-snapshot.json.gz'))));
const library=makeLibrary({profiles,sec,mappings:read('src/data/investorProfiles/priceMappings.json')});
const out=path.join(root,'public/data/holdings-activity');fs.mkdirSync(out,{recursive:true});
const hash=s=>crypto.createHash('sha256').update(s).digest('hex').slice(0,16);
const write=(prefix,value)=>{const text=JSON.stringify(value),file=`${prefix}.${hash(text)}.json`;fs.writeFileSync(path.join(out,file),text+'\n');return file;};
const files=new Set(['manifest.json']),countries={};
for(const country of ['IN','US']){
 const stocks=library.stocks.filter(s=>s.country===country),buckets=new Map(),index=[];
 for(const s of stocks){const bucket=hash(s.id).slice(0,2);if(!buckets.has(bucket))buckets.set(bucket,{});buckets.get(bucket)[s.id]=s;}
 const chunks=new Map([...buckets].map(([bucket,rows])=>{const file=write(country.toLowerCase()+'-'+bucket,rows);files.add(file);return [bucket,file];}));
 for(const s of stocks){const counts={},statusIds={};for(const c of s.changes){counts[c.status]=(counts[c.status]||0)+1;(statusIds[c.status]||=[]).push(c.managerId);}index.push({id:s.id,stock:s.stock,symbol:s.symbol,securityClass:s.securityClass,counts,statusIds,managerIds:s.changes.map(c=>c.managerId),periods:[...new Set(s.changes.map(c=>c.date).filter(Boolean))].sort(),chunk:chunks.get(hash(s.id).slice(0,2))});}
 const file=write(country.toLowerCase()+'-index',index);files.add(file);
 const counts={};for(const s of stocks)for(const c of s.changes)counts[c.status]=(counts[c.status]||0)+1;
 countries[country]={profileCheckedThrough:profiles.filter(p=>p.country===country).map(p=>p.retrievedAt).filter(Boolean).sort().at(-1),index:file,stocks:stocks.length,rows:stocks.reduce((n,s)=>n+s.changes.length,0),counts};
}
const manifest={schemaVersion:2,coverage:library.coverage,profileCheckedThrough:profiles.map(p=>p.retrievedAt).filter(Boolean).sort().at(-1),countries,managers:library.managers};
fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(manifest)+'\n');
// Only this generator's prior content-addressed outputs are disposable.
for(const file of fs.readdirSync(out))if(/^(in|us)-(index|[a-f0-9]{2})\.[a-f0-9]{16}\.json$/.test(file)&&!files.has(file))fs.unlinkSync(path.join(out,file));
console.log(JSON.stringify({holdingsActivity:countries,coverage:library.coverage}));
