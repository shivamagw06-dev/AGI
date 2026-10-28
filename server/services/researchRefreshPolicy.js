export const FACTORS = ['momentum','growth','value','quality','all-weather'];
export const SCREENERS = ['momentum','low-pe','piotroski','cash-flow','promoter-holdings'];
export function dateOnly(value) {
 if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value)||!Number.isFinite(Date.parse(value))||new Date(value).toISOString().slice(0,10)!==value)throw Error('Invalid source date');
 return value;
}
export function validateEnvelope(bundle,now=new Date()) {
 if(bundle?.version!==1||bundle.provider!=='trendlyne'||bundle.complete!==true)throw Error('A complete Trendlyne version-1 export is required');
 const collected=Date.parse(bundle.collectedAt);
 if(!Number.isFinite(collected)||collected>now.getTime()+300000||now-collected>3*86400000)throw Error('Source collection is stale or future-dated');
 if(!Array.isArray(bundle.screeners)||bundle.screeners.length!==5)throw Error('All five screener exports are required');
 if(new Set(bundle.screeners.map(s=>s.slug)).size!==5||bundle.screeners.some(s=>!SCREENERS.includes(s.slug)))throw Error('Duplicate or unknown screener');
 for(const s of bundle.screeners){
  dateOnly(s.asOf);
  if(Date.parse(s.asOf)>now.getTime()||now-Date.parse(s.asOf)>4*86400000)throw Error('Screener date is stale or future-dated');
  if(s.complete!==true||!Number.isInteger(s.expectedRows)||s.expectedRows<1||s.expectedRows>5000||!Array.isArray(s.tables)||s.tables.some(t=>typeof t!=='string'))throw Error('Incomplete screener pagination or table metadata');
 }
 if(!Array.isArray(bundle.institutions))throw Error('Institution coverage manifest is required');
 const seen=new Set();
 for(const s of bundle.institutions){
  if(!['IN','US'].includes(s.country)||!['individual','institutional'].includes(s.category))throw Error('Invalid institution scope');
  const key=s.country+':'+s.category;if(seen.has(key))throw Error('Duplicate institution scope');seen.add(key);
  dateOnly(s.asOf);
  if(Date.parse(s.asOf)>now.getTime()||s.complete!==true||!Number.isInteger(s.expectedRows)||s.expectedRows<1||typeof s.text!=='string')throw Error('Incomplete institution export');
 }
 // The two India categories are mandatory; USA can be included separately.
 if(!seen.has('IN:individual')||!seen.has('IN:institutional'))throw Error('Both India investor categories are required');
 return bundle;
}
const finite=v=>typeof v==='number'&&Number.isFinite(v);
export function reviewPortfolios(portfolios, input, now=new Date()) {
 const data=input?.rows||[];
 if(!Array.isArray(data)||data.length>10000)throw Error('Invalid factor input rows');
 const seen=new Set();for(const r of data){if(!r.symbol||seen.has(r.symbol))throw Error('Missing or duplicate factor symbol');seen.add(r.symbol);}
 const bySymbol=new Map(data.map(r=>[r.symbol,r]));
 return portfolios.filter(p=>FACTORS.some(f=>p.id==='in-'+f)).map(p=>({
  id:p.id,name:p.name,action:'review_only',holdings:p.holdings.map(h=>{
   if(h.symbol==='GOLDBEES')return {symbol:h.symbol,weight:h.weight,status:'retain_gold_sleeve',reasons:[]};
   const r=bySymbol.get(h.symbol),reasons=[];
   if(!r)return {symbol:h.symbol,weight:h.weight,status:'data_missing',reasons:['No current factor observation']};
   let fresh=false;try{fresh=Date.parse(dateOnly(r.asOf))<=now.getTime()&&now-Date.parse(r.asOf)<=4*86400000;}catch{}
   if(!fresh)reasons.push('Stale or invalid observation date');
   for(const field of ['marketCapCr','forwardEPS','forwardPE','estimateContributors'])if(!finite(r[field]))reasons.push('Missing '+field);
   if(r.corporateActionsVerified!==true)reasons.push('Per-share adjustment basis not verified');
   const failures=[];
   if(fresh&&finite(r.marketCapCr)&&r.marketCapCr<5000)failures.push('Market cap below Rs5,000 crore');
   if(fresh&&finite(r.forwardEPS)&&r.forwardEPS<=0)failures.push('Nonpositive forward earnings');
   if(fresh&&finite(r.forwardPE)&&(r.forwardPE<=0||r.forwardPE>100))failures.push('Forward PE outside 0–100');
   if(fresh&&finite(r.estimateContributors)&&r.estimateContributors<5)failures.push('Fewer than five verified estimate contributors');
   // Never infer original factor eligibility from a proxy shortlist or recommendation count.
   reasons.push('Original factor ranking not recomputed: earnings revisions and forecast dispersion need verified coverage');
   return {symbol:h.symbol,weight:h.weight,marketCapCr:r.marketCapCr??null,status:failures.length?'eligibility_review':'ranking_pending',failures,reasons};
  })
 }));
}
