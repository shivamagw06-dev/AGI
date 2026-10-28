import {readFile, stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateEnvelope, dateOnly} from '../services/researchRefreshPolicy.js';

const allowed = new Set(['trendlyne.com','www.trendlyne.com','us.trendlyne.com']);
export function sourceUrl(value) {
 const u=new URL(value);
 if(u.protocol!=='https:'||!allowed.has(u.hostname)||u.username||u.password||u.port)throw Error('BROWSER_SOURCE_INVALID');
 return u.href;
}
export function validateManifest(m) {
 if(m?.version!==1||m.verified!==true||!Array.isArray(m.datasets)||m.datasets.length<7||m.datasets.length>200)throw Error('BROWSER_MAPPING_REQUIRED: verify saved pages and table selectors');
 const ids=new Set();
 for(const d of m.datasets){
  if(!/^[a-z0-9:-]+$/.test(d.id)||ids.has(d.id))throw Error('BROWSER_MAPPING_INVALID');ids.add(d.id);sourceUrl(d.url);
  if(!['screener','institution_directory'].includes(d.kind))throw Error('BROWSER_DATASET_UNSUPPORTED');
  for(const key of ['tableSelector','dateSelector','countSelector','readySelector'])if(typeof d[key]!=='string'||!d[key])throw Error('BROWSER_MAPPING_INVALID');
  if(typeof d.datePattern!=='string'||!d.datePattern.startsWith('^')||!d.datePattern.endsWith('$')||typeof d.countPattern!=='string'||!d.countPattern.startsWith('^')||!d.countPattern.endsWith('$'))throw Error('BROWSER_METADATA_PATTERN_REQUIRED');
  new RegExp(d.datePattern);new RegExp(d.countPattern);
  if(!Array.isArray(d.headers)||!d.headers.length||d.headers.some(h=>typeof h!=='string'))throw Error('BROWSER_HEADERS_REQUIRED');
  if(!Number.isInteger(d.keyColumn)||d.keyColumn<0||d.keyColumn>=d.headers.length)throw Error('BROWSER_KEY_REQUIRED');
  if(!d.nextSelector&&d.singlePage!==true)throw Error('BROWSER_PAGINATION_REQUIRED');
 }
 return m;
}
export function assembleDataset(d, pages, dateText, countText) {
 const asOf=dateOnly(new RegExp(d.datePattern).exec(dateText)?.[1]);
 const count=new RegExp(d.countPattern).exec(countText)?.[1];
 if(!count||!/^\d[\d,]*$/.test(count))throw Error('BROWSER_COUNT_INVALID');
 const expectedRows=Number(count.replaceAll(',',''));
 if(!Number.isInteger(expectedRows)||expectedRows<1||expectedRows>5000)throw Error('BROWSER_COUNT_INVALID');
 const keys=new Set(), rows=[];
 for(const p of pages){
  if(JSON.stringify(p.headers)!==JSON.stringify(d.headers))throw Error('BROWSER_SCHEMA_CHANGED');
  for(const row of p.rows){
   const key=row[d.keyColumn]?.trim();
   if(row.length!==d.headers.length||!key||keys.has(key))throw Error('BROWSER_DUPLICATE_OR_INVALID_ROW');
   keys.add(key);rows.push(row);
  }
 }
 if(rows.length!==expectedRows)throw Error('BROWSER_INCOMPLETE_PAGINATION');
 const csv=[d.headers,...rows].map(r=>r.map(v=>'"'+String(v).replaceAll('"','""')+'"').join(',')).join('\n');
 const base={asOf,complete:true,expectedRows,sourceUrl:d.url,sourceHash:createHash('sha256').update(csv).digest('hex')};
 return d.kind==='screener'?{...base,slug:d.id,tables:[csv]}:{...base,country:d.country,category:d.category,text:csv};
}
async function pageGuard(page, d) {
 sourceUrl(page.url());
 if(/\/(login|accounts\/login|signin)(\/|\?|$)/i.test(new URL(page.url()).pathname))throw Error('BROWSER_LOGIN_REQUIRED');
 for(const selector of ['input[type="password"]','iframe[src*="recaptcha"]','iframe[src*="hcaptcha"]','[id="challenge-running"]']){
  if(await page.locator(selector).first().isVisible())throw Error('BROWSER_LOGIN_OR_CHALLENGE_REQUIRED');
 }
 if(!await page.locator(d.readySelector).isVisible())throw Error('BROWSER_PAGE_NOT_READY');
}
export async function collectDataset(page,d) {
 const response=await page.goto(d.url,{waitUntil:'domcontentloaded',timeout:45000});
 if(response?.status()===429)throw Error('BROWSER_RATE_LIMITED');
 if(response&&response.status()>=400)throw Error('BROWSER_SOURCE_UNAVAILABLE');
 await pageGuard(page,d);
 const dateText=(await page.locator(d.dateSelector).innerText()).trim();
 const countText=(await page.locator(d.countSelector).innerText()).trim();
 const pages=[], fingerprints=new Set();
 for(let n=0;n<100;n++){
  await pageGuard(page,d);
  if((await page.locator(d.dateSelector).innerText()).trim()!==dateText||(await page.locator(d.countSelector).innerText()).trim()!==countText)throw Error('BROWSER_DATA_CHANGED_DURING_COLLECTION');
  const snapshot=await page.locator(d.tableSelector).evaluate(table=>({headers:Array.from(table.querySelectorAll('thead th')).map(x=>x.innerText.trim()),rows:Array.from(table.querySelectorAll('tbody tr')).map(r=>Array.from(r.querySelectorAll('td')).map(x=>x.innerText.trim()))}));
  const fingerprint=JSON.stringify(snapshot);
  if(fingerprints.has(fingerprint))throw Error('BROWSER_REPEATED_PAGE');fingerprints.add(fingerprint);pages.push(snapshot);
  if(d.singlePage===true)break;
  const next=page.locator(d.nextSelector);
  if(await next.count()!==1)throw Error('BROWSER_PAGINATION_CHANGED');
  if(await next.isDisabled()||await next.getAttribute('aria-disabled')==='true')break;
  if(n===99)throw Error('BROWSER_PAGE_LIMIT');
  await next.click();
  // Wait for table contents, not an arbitrary delay or network idleness.
  await page.waitForFunction(({selector,previous})=>{const t=document.querySelector(selector);if(!t)return false;const v={headers:Array.from(t.querySelectorAll('thead th')).map(x=>x.innerText.trim()),rows:Array.from(t.querySelectorAll('tbody tr')).map(r=>Array.from(r.querySelectorAll('td')).map(x=>x.innerText.trim()))};return JSON.stringify(v)!==previous;},{selector:d.tableSelector,previous:fingerprint},{timeout:15000});
 }
 return assembleDataset(d,pages,dateText,countText);
}
export function browserConfigured(env=process.env){return Boolean(env.TRENDLYNE_BROWSER_MANIFEST_PATH&&env.TRENDLYNE_BROWSER_STATE_PATH);}
export async function collectTrendlyneBrowser({env=process.env,launch,now=()=>new Date()}={}) {
 if(!browserConfigured(env))throw Error('BROWSER_SETUP_REQUIRED: configure manifest and dedicated login session');
 const manifest=validateManifest(JSON.parse(await readFile(env.TRENDLYNE_BROWSER_MANIFEST_PATH,'utf8')));
 const permission=await stat(env.TRENDLYNE_BROWSER_STATE_PATH);
 if((permission.mode&0o077)!==0)throw Error('BROWSER_SESSION_PERMISSIONS: restrict session file to owner');
 // Never read personal browser profiles or print session contents.
 let state;
 try{state=JSON.parse(await readFile(env.TRENDLYNE_BROWSER_STATE_PATH,'utf8'));}catch{throw Error('BROWSER_SESSION_INVALID');}
 if(!state||!Array.isArray(state.cookies)||state.cookies.some(c=>!allowed.has(c.domain.replace(/^\./,'')))||!Array.isArray(state.origins)||state.origins.some(o=>!allowed.has(new URL(o.origin).hostname)))throw Error('BROWSER_SESSION_SCOPE_INVALID');
 const chromium=launch?null:(await import('playwright')).chromium;
 const browser=await (launch||(()=>chromium.launch({headless:true})) )();
 let deadline;
 try{
  const work=async()=>{
   const context=await browser.newContext({storageState:state,acceptDownloads:false,serviceWorkers:'block'});
   context.setDefaultTimeout(15000);
   await context.route('**/*',route=>{
    const request=route.request();
    // Prevent navigation to arbitrary sites with the authenticated context.
    if(request.isNavigationRequest()){try{sourceUrl(request.url());}catch{return route.abort();}}
    return route.continue();
   });
   const page=await context.newPage();const bundle={version:1,provider:'trendlyne',complete:true,collectedAt:now().toISOString(),screeners:[],institutions:[]};
   for(const d of manifest.datasets){
    const result=await collectDataset(page,d);
    bundle[d.kind==='screener'?'screeners':'institutions'].push(result);
   }
   return validateEnvelope(bundle,now());
  };
  return await Promise.race([work(),new Promise((_,reject)=>{deadline=setTimeout(()=>reject(Error('BROWSER_COLLECTION_TIMEOUT')),10*60000);})]);
 }catch(e){
  // Browser errors may embed URLs, page contents or credentials. Only controlled codes leave this adapter.
  if(/^BROWSER_[A-Z_]+(?::[^\n]*)?$/.test(e.message))throw e;
  throw Error('BROWSER_COLLECTION_FAILED: check session and verified page mappings; no data published');
 }finally{clearTimeout(deadline);await browser.close();}
}
