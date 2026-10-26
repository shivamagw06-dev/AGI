import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { entityType, holdingCoverage, ownershipComparison, researchKey } from '../../src/lib/institutionResearch.js';
const root = path.resolve(import.meta.dirname, '../..');
const dir = path.join(root, 'src/data/investorProfiles');
const index = JSON.parse(fs.readFileSync(path.join(dir, 'index.json')));
const mappings = JSON.parse(fs.readFileSync(path.join(dir, 'priceMappings.json')));
const profiles = index.map(entry => { const file=path.join(dir,'holdings',`${entry.country.toLowerCase()}-${entry.slug}.json`); return fs.existsSync(file) ? {...JSON.parse(fs.readFileSync(file)), category:entry.category || 'individual'} : null; }).filter(Boolean);
const summaries = {}, stocks = new Map();
for (const p of profiles) {
  const coverage=holdingCoverage(p), entity=entityType(p.name,p.category);
  const key=p.country.toLowerCase()+'-'+p.slug;
  const fingerprint=crypto.createHash('sha256').update(JSON.stringify([p.reportPeriod ?? null,p.rows.map(r=>['stock','quantity','security','cusip'].map(k=>r[k] ?? null))])).digest('hex');
  summaries[key]={fingerprint,sourceLimited:!!p.sourceLimited,retrievalComplete:p.retrievalComplete===true,sourceReportedCount:p.sourceReportedCount??null,name:p.name,country:p.country,slug:p.slug,category:p.category,entityType:entity,reportPeriod:p.reportPeriod,retrievedAt:p.retrievedAt,sourceUrl:p.sourceUrl,stocks:coverage.current.length,historical:coverage.historical.length,total:coverage.total,value:null,change:null,sectors:[],holdings:coverage.current.slice(0,3).map(r=>({label:r.stock})),bought:[],sold:[]};
  if(p.country!=='IN')continue;
  // Group aggregates never become independent investor votes. Only directly named fund/insurer entities enter the breadth count.
  for (const r of coverage.current) {
    const compare=ownershipComparison(p,r);
    if (!compare.comparable) continue;
    const symbol=mappings.IN[r.stock]?.symbol;
    const k=(symbol || researchKey(r.stock))+'|'+p.reportPeriod;
    if (!stocks.has(k)) stocks.set(k,{key:k,stock:r.stock,symbol,country:'IN',owners:[]});
    const counted=['Fund / investment entity','Insurer'].includes(entity);
    stocks.get(k).owners.push({name:p.name,slug:p.slug,entityType:entity,counted,sourceUrl:p.sourceUrl,retrievedAt:p.retrievedAt,...compare});
  }
}
const stockRows=[...stocks.values()].map(s=>({...s,periods:[...new Set(s.owners.map(x=>x.period))],increased:s.owners.filter(x=>x.counted&&x.status==='Reported stake increased').length,reduced:s.owners.filter(x=>x.counted&&x.status==='Reported stake reduced').length,uncertain:s.owners.filter(x=>x.counted&&x.status==='Within source rounding').length,groupsExcluded:s.owners.filter(x=>!x.counted).length})).sort((a,b)=>b.increased+b.reduced-a.increased-a.reduced||a.stock.localeCompare(b.stock));
const data={schemaVersion:1,sourceThrough:profiles.map(p=>p.retrievedAt).sort().at(-1),summaries,stocks:stockRows};
data.version=crypto.createHash('sha256').update(JSON.stringify(data)).digest('hex').slice(0,16);
fs.writeFileSync(path.join(root,'src/data/institutionResearch.json'),JSON.stringify(data));
console.log({profiles:profiles.length,stocks:stockRows.length,version:data.version});
