/** PDF-disclosed weights; ranking conventions are explicitly AGI research assumptions. */
export const RULES = {
 Momentum: {earningsRevision: .5, totalReturn12m: .25, totalReturn6m: .25},
 Value: {forwardEarningsYield: .25, sectorEarningsYield: .25, bookYield: .25, salesYield: .25},
 Growth: {epsGrowth3y: .25, expectedEpsGrowth: .25, earningsRisk: .25, salesGrowthFY2: .25},
 Quality: {roe: .5, earningsRisk: .5},
 'All-Weather': {Momentum: .3, Value: .3, Growth: .2, Quality: .2}
};
export const ASSUMPTIONS = 'AGI adaptation: midrank percentiles; sector-relative yield ranked within sector; lower earnings risk preferred; equal-weight deciles rounded down; ticker breaks score ties. EPS growth and earnings-risk inputs require a documented methodology. These choices are not fully disclosed in the PDF.';
const finite = v => typeof v === 'number' && Number.isFinite(v);
const date = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0,10)===v;
export function revision(row) {
 const p = row.eps;
 if (!p || !date(p.currentDate) || !date(p.priorDate) || !Array.isArray(p.current) || !Array.isArray(p.prior) || p.current.length !== 2 || p.prior.length !== 2) return null;
 const days = (Date.parse(p.currentDate)-Date.parse(p.priorDate))/86400000;
 if (days < 85 || days > 95 || p.current.some((x,i) => !x.fiscalYear || x.fiscalYear !== p.prior[i]?.fiscalYear || !finite(x.value) || !finite(p.prior[i]?.value) || p.prior[i].value <= 0)) return null;
 return p.current.reduce((a,x,i)=>a+(x.value/p.prior[i].value-1)*100,0)/2;
}
function percentile(rows,key,sector) {
 const pool = sector ? rows.filter(r=>r.sector===sector) : rows;
 return Object.fromEntries(pool.map(r=>{
  const value=r.metrics[key], less=pool.filter(x=>x.metrics[key]<value).length, equal=pool.filter(x=>x.metrics[key]===value).length;
  const p=pool.length===1?50:100*(less+(equal-1)/2)/(pool.length-1);
  return [r.symbol, key==='earningsRisk'?100-p:p];
 }));
}
export function buildFactors(input) {
 if (!input || !date(input.asOf) || !date(input.universeAsOf) || input.universeAsOf>input.asOf || !Array.isArray(input.universe) || input.universe.length!==500 || new Set(input.universe).size!==500 || input.universe.some(s=>typeof s!=='string'||!s.trim())) throw Error('Supply the dated, unique 500-stock NIFTY 500 membership list.');
 if (!input.universeSource || !Array.isArray(input.rows)) throw Error('Universe source and stock rows are required.');
 const seen=new Set();
 for(const r of input.rows){if(!input.universe.includes(r.symbol)||seen.has(r.symbol))throw Error(`Duplicate or out-of-universe stock: ${r.symbol}`);seen.add(r.symbol);}
 const diagnostics=[];
 const rows=input.universe.map(symbol=>{
  const r=input.rows.find(x=>x.symbol===symbol);
  if(!r||!date(r.observedAt)||r.observedAt>input.asOf||!r.source){diagnostics.push(`${symbol}: missing source or valid observation date`);return {symbol,metrics:{}};}
  const metrics={...r.metrics};
  // Never accept a revision from a different fiscal year or a later observation.
  metrics.earningsRevision = r.eps?.currentDate<=input.asOf ? revision(r) : null;
  metrics.sectorEarningsYield = r.sector ? metrics.forwardEarningsYield : null;
  if(!input.methodology?.earningsRisk)metrics.earningsRisk=null;
  if(!input.methodology?.expectedEpsGrowth)metrics.expectedEpsGrowth=null;
  if(!input.methodology?.epsGrowth3y)metrics.epsGrowth3y=null;
  return {...r,metrics};
 });
 const results={};
 for(const [name,weights] of Object.entries(RULES)){
  const composite=name==='All-Weather';
  const eligible=rows.filter(r=>Object.keys(weights).every(k=>composite ? results[k]?.scores?.some(x=>x.symbol===r.symbol) : finite(r.metrics[k])));
  const missing=rows.filter(r=>!eligible.includes(r)).map(r=>({symbol:r.symbol,fields:Object.keys(weights).filter(k=>composite?!results[k]?.scores?.some(x=>x.symbol===r.symbol):!finite(r.metrics[k]))}));
  // Complete universe required: missing coverage must not change the ranking population silently.
  if(missing.length){results[name]={status:'blocked',covered:eligible.length,missing,scores:[],long:[],short:[]};continue;}
  const ranks=Object.fromEntries(Object.keys(weights).map(k=>[k,composite?Object.fromEntries(results[k].scores.map(x=>[x.symbol,x.score])): k==='sectorEarningsYield'?Object.assign({},...[...new Set(rows.map(r=>r.sector))].map(s=>percentile(rows,k,s))):percentile(rows,k)]));
  const scores=rows.map(r=>({symbol:r.symbol,sector:r.sector,score:Object.entries(weights).reduce((a,[k,w])=>a+ranks[k][r.symbol]*w,0)})).sort((a,b)=>b.score-a.score||a.symbol.localeCompare(b.symbol));
  const n=Math.floor(scores.length/10), allocate=xs=>xs.map(r=>({...r,weight:100/n}));
  results[name]={status:'ready',covered:500,missing:[],scores,long:allocate(scores.slice(0,n)),short:allocate(scores.slice(-n))};
 }
 return {version:'agi-pdf-factors-v1',exactReplication:false,replicationGaps:['Normalisation not disclosed','Earnings-risk formula not disclosed','Growth formulas not fully disclosed','Source transaction-cost model not disclosed'],asOf:input.asOf,rebalance:'Monthly; proposals only',assumptions:ASSUMPTIONS,diagnostics,results};
}
export const TEMPLATE={asOf:'YYYY-MM-DD',universeAsOf:'YYYY-MM-DD',universeSource:'Dated NIFTY 500 constituent source',universe:[],methodology:{epsGrowth3y:'',expectedEpsGrowth:'',earningsRisk:''},rows:[{symbol:'EXAMPLE',sector:'Example sector',observedAt:'YYYY-MM-DD',source:'Trendlyne export/page reference',eps:{currentDate:'YYYY-MM-DD',priorDate:'YYYY-MM-DD',current:[{fiscalYear:'FY27',value:null},{fiscalYear:'FY28',value:null}],prior:[{fiscalYear:'FY27',value:null},{fiscalYear:'FY28',value:null}]},metrics:{totalReturn12m:null,totalReturn6m:null,forwardEarningsYield:null,bookYield:null,salesYield:null,epsGrowth3y:null,expectedEpsGrowth:null,earningsRisk:null,salesGrowthFY2:null,roe:null}}]};
