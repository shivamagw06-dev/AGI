// Evidence-led research prompts, never investment scores or inferred independence.
const text = value => String(value ?? '').trim();
const key = value => text(value).toLowerCase().replace(/\s+/g, ' ');
export const number = value => value === null || value === undefined || text(value) === '' ? null : Number.isFinite(Number(value)) ? Number(value) : null;
export const companyKey = row => key(row.company_name);
export const filingKey = row => JSON.stringify([row.company_name,row.person,row.reported_on,row.period,row.action,row.mode,row.quantity,row.value].map(text));
export function filingKind(row) {
 const description = `${row.action || ''} ${row.mode || ''}`;
 if (/invok|invocation/i.test(description)) return 'pledge invocation';
 if (/revoke|revocation|release/i.test(description)) return 'pledge release';
 if (/pledge/i.test(description)) return 'pledge creation';
 const action = key(row.action);
 if (String(row.is_open_market) === 'true') {
  if ((/market sale/i.test(row.mode)&&['acquisition','purchase','buy'].includes(action))||(/market purchase/i.test(row.mode)&&['disposal','sale','sell'].includes(action))) return 'Conflicting market classification';
  if (['acquisition','purchase','buy'].includes(action)) return 'market purchase';
  if (['disposal','sale','sell'].includes(action)) return 'market sale';
 }
 if (/block deal/i.test(description)) return 'block deal';
 return 'other transfer / allotment';
}
export function sourceLink(row) {try {const url=new URL(row.source_url);return url.protocol==='https:' ? url.href : null;} catch {return null;}}
export function buildIntelligence(rows, asOf = new Date().toISOString().slice(0,10)) {
 const end = Date.parse(`${asOf}T00:00:00Z`);
 if (!Number.isFinite(end)) return [];
 const cutoff = new Date(end-29*86400000).toISOString().slice(0,10);
 const previous = new Date(end-59*86400000).toISOString().slice(0,10);
 const companies = new Map(), seen = new Set();
 for (const row of rows || []) {
  if (!row.company_name || !/^\d{4}-\d{2}-\d{2}$/.test(row.reported_on || '') || row.reported_on > asOf || /sast/i.test(`${row.regime} ${row.regulation}`)) continue;
  const identity=filingKey(row);if(seen.has(identity))continue;seen.add(identity);
  const id=companyKey(row);
  if(!companies.has(id))companies.set(id,{id,company:row.company_name,symbol:row.symbol||null,rows:[]});
  companies.get(id).rows.push({...row,kind:filingKind(row)});
 }
 return [...companies.values()].map(company=>{
  const sorted=company.rows.sort((a,b)=>b.reported_on.localeCompare(a.reported_on));
  const recent=sorted.filter(row=>row.reported_on>=cutoff);
  const prior=sorted.filter(row=>row.reported_on>=previous&&row.reported_on<cutoff);
  const buys=recent.filter(row=>row.kind==='market purchase');
  const sells=recent.filter(row=>row.kind==='market sale');
  const buyers=new Set(buys.map(row=>key(row.person)).filter(Boolean)).size;
  const days=new Set(buys.map(row=>row.reported_on)).size;
  const valued=buys.filter(row=>number(row.value)>0);
  const buyValue=valued.reduce((sum,row)=>sum+number(row.value),0);
  const invocations=recent.filter(row=>row.kind==='pledge invocation');
  const promoterSales=sells.filter(row=>/promoter/i.test(row.category||''));
  const material=recent.filter(row=>['market purchase','market sale','block deal'].includes(row.kind)&&number(row.traded_pct)>=1);
  const signals=[];
  if(invocations.length)signals.push({kind:'risk',title:'Pledge invocation',detail:`${invocations.length} invocation disclosure${invocations.length===1?'':'s'} in the last 30 days. Review lender enforcement and remaining encumbrance.`});
  if(buyers>=3)signals.push({kind:'buying',title:'Multiple-buyer activity',detail:`${buyers} named buyers across ${buys.length} open-market purchase filings. Related-party connections have not been verified.`});
  if(days>=3)signals.push({kind:'buying',title:'Repeated purchase disclosures',detail:`Open-market purchases disclosed on ${days} separate days. These are reporting dates, not necessarily distinct trading days.`});
  if(promoterSales.length)signals.push({kind:'selling',title:'Promoter market sales',detail:`${promoterSales.length} promoter sale filing${promoterSales.length===1?'':'s'}. Check holding changes and the disclosed purpose before interpreting motive.`});
  if(material.length)signals.push({kind:'size',title:'Large reported ownership movement',detail:`${material.length} market or block-deal filing${material.length===1?'':'s'} each report at least 1% of company equity traded. This is a screening threshold, not a recommendation.`});
  if(!signals.length&&buys.length)signals.push({kind:'buying',title:'Open-market purchase observed',detail:`${buys.length} purchase filing${buys.length===1?'':'s'} in 30 days. Compare the amount with the buyer’s existing stake.`});
  return {...company,rows:sorted,recent,prior,buys,sells,buyers,buyValue,valued:valued.length,signals,latest:sorted[0]?.reported_on,cutoff,asOf,priorBuys:prior.filter(row=>row.kind==='market purchase').length,priorSells:prior.filter(row=>row.kind==='market sale').length,linked:recent.filter(sourceLink).length};
 }).sort((a,b)=>Number(b.signals.some(s=>s.kind==='risk'))-Number(a.signals.some(s=>s.kind==='risk'))||Number(b.buyers>=3)-Number(a.buyers>=3)||b.latest.localeCompare(a.latest)||a.company.localeCompare(b.company));
}
export function newWatchlistFilings(companies, watchlist) {
 return companies.flatMap(company=>{
  const saved=watchlist[company.id];if(!saved)return [];
  const known=new Set(saved.seen||[]);
  return company.rows.filter(row=>!known.has(filingKey(row))).map(row=>({company:company.company,id:company.id,row,kind:row.kind}));
 });
}
