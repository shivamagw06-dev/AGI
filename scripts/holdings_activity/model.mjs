import { entityType, ownershipComparison, percentage, periodKey, researchKey } from '../../src/lib/institutionResearch.js';
export function periodDate(value) {
 const s=String(value||'');
 if(/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
 const q=s.match(/^(\d{4}) Q([1-4])$/);const k=q?`${q[1]}-${String(Number(q[2])*3).padStart(2,'0')}`:periodKey(s);
 if(!k)return null;
 const [y,m]=k.split('-').map(Number);return new Date(Date.UTC(y,m,0)).toISOString().slice(0,10);
}
export function indiaActivity(profile,row) {
 const compare=ownershipComparison(profile,row),date=periodDate(row.reportPeriod||profile.reportPeriod),priorDate=periodDate(profile.periods?.[1]?.replace(/\s*%$/,''));
 const chronological=date&&priorDate&&priorDate<date;
 if(compare.comparable&&chronological)return {status:compare.status==='Reported stake increased'?'increased':compare.status==='Reported stake reduced'?'reduced':'rounding',before:compare.prior,after:compare.latest,delta:compare.delta,uncertainty:compare.uncertainty,date,priorDate,unit:'ownership'};
 return {status:'unavailable',before:null,after:percentage(row.history?.[0])?.value??null,date,priorDate:chronological?priorDate:null,unit:'ownership',reason:compare.comparable?'Reporting dates do not support a chronological comparison.':compare.status};
}
export function secActivities(manager) {
 const current=manager.status==='SEC table checked';
 const comparable=current&&manager.comparisonStatus?.startsWith('Reported quantities compared')&&manager.prior?.period&&manager.prior.period<manager.latest?.period&&!manager.comparisonError;
 const changes=new Map((manager.changes||[]).map(c=>[c.cusip,c]));
 const holdings=new Map((manager.holdings||[]).map(h=>[h.cusip,h]));
 const keys=new Set([...holdings.keys(),...(comparable?[...changes.keys()]:[])]);
 return [...keys].map(cusip=>{
  const h=holdings.get(cusip),c=comparable?changes.get(cusip):null;
  let status=!comparable?'unavailable':c?.identityReview?'identity-review':c?.status==='New disclosure'?'new':c?.status==='Absent in newer table'?'absent':c?.quantityChange>0?'increased':c?.quantityChange<0?'reduced':'unchanged';
  return {cusip,stock:h?.issuer||c?.issuer,securityClass:h?.securityClass||c?.securityClass,status,unit:'shares',before:comparable?(c?.priorQuantity??h?.quantity):null,after:c?.quantity??h?.quantity??null,changePct:c?.quantityChangePct??null,date:manager.latest?.period||null,priorDate:manager.prior?.period||null,...(!comparable?{reason:manager.comparisonError||(!current?'Historical or notice-filer record; not a current comparison.':'Comparable prior filing is unavailable.')}:{}),...(status==='identity-review'?{reason:'Security identity/class wording changed. Direction withheld pending review.'}:{})};
 });
}
export function makeLibrary({profiles,sec,mappings}) {
 const managers={},stocks=new Map(),aliases=new Map(),symbolCusips=new Map(),secBySlug=new Map(sec.managers.map(m=>[m.slug,m]));
 for(const [cusip,v] of Object.entries(mappings.CUSIP||{})){if(!symbolCusips.has(v.symbol))symbolCusips.set(v.symbol,[]);symbolCusips.get(v.symbol).push(cusip);}
 const add=(country,id,stock,symbol,securityClass,row)=>{
  const k=country+':'+id;
  if(!stocks.has(k))stocks.set(k,{id:k,country,stock,symbol:symbol||null,securityClass:securityClass||null,changes:[]});
  const s=stocks.get(k);
  // Exact manager/security identity only. Do not merge fuzzy company or investor names.
  if(!s.changes.some(c=>c.managerId===row.managerId))s.changes.push(row);
 };
 for(const m of sec.managers){
  const id='sec:'+m.cik;aliases.set(m.slug,id);
  managers[id]={name:m.name,type:m.managerType,country:'US',evidence:'SEC information tables',checkedAt:String(m.checkedAt||sec.checkedAt).slice(0,10),source:m.latest?.tableSources?.[0]||m.latest?.sourceUrl,sourceParts:m.latest?.tableSources||[],priorSource:m.prior?.tableSources?.[0]||m.prior?.sourceUrl,priorSourceParts:m.prior?.tableSources||[],filedAt:m.latest?.filedAt?.slice(0,10),scope:m.status,comparisonError:m.comparisonError||null};
  for(const row of secActivities(m)){const symbol=mappings.CUSIP?.[row.cusip]?.symbol;add('US','cusip:'+row.cusip,row.stock,symbol,row.securityClass,{...row,managerId:id});}
 }
 let inputRows=0,representedBySecRows=0;
 for(const p of profiles){
  inputRows+=p.rows.length;
  if(p.country==='US'&&p.managerSlug&&aliases.has(p.managerSlug)&&(secBySlug.get(p.managerSlug)?.holdings?.length||secBySlug.get(p.managerSlug)?.changes?.length)){representedBySecRows+=p.rows.length;continue;}
  const id='profile:'+p.country+':'+p.slug;
  managers[id]={name:p.name,type:entityType(p.name,p.category),country:p.country,evidence:p.sourceLabel||'Saved disclosure source',checkedAt:p.retrievedAt,source:p.sourceUrl,profileSlug:p.slug,scope:p.coverageLabel||'Saved disclosure',sourceLimited:!!p.sourceLimited};
  for(const r of p.rows){
   if(p.country==='IN'){
    const symbol=mappings.IN?.[r.stock]?.symbol;
    add('IN',symbol||'name:'+researchKey(r.stock),r.stock,symbol,null,{...indiaActivity(p,r),managerId:id});
   }else{
    const match=String(r.sourceUrl||'').match(/\/ownership\/\d+\/([^/]+)\//),symbol=match?.[1]||mappings.CUSIP?.[r.cusip]?.symbol;
    const candidates=symbolCusips.get(symbol)||[];
    const cusip=r.cusip||(candidates.length===1?candidates[0]:null);
    const key=cusip?'cusip:'+cusip:match?'source-symbol:'+symbol:'source-name:'+researchKey(r.stock);
    const quantity=Number(String(r.quantity||'').replaceAll(',',''));
    add('US',key,r.stock,symbol,r.security,{managerId:id,status:'unavailable',before:null,after:Number.isFinite(quantity)&&String(r.quantity||'').trim()?quantity:null,unit:'shares',date:periodDate(p.reportPeriod),priorDate:null,reason:'Comparable dated prior holdings are not available. Source NEW/change labels are not treated as purchases or sales.',...(r.sourceUrl?{source:r.sourceUrl}:{})});
   }
  }
 }
 return {managers,stocks:[...stocks.values()].sort((a,b)=>a.stock.localeCompare(b.stock)||a.id.localeCompare(b.id)),coverage:{profiles:profiles.length,profileRows:inputRows,profileRowsUnderSecScope:representedBySecRows,secFilers:sec.managers.length,secCheckedAt:sec.checkedAt.slice(0,10)}};
}
