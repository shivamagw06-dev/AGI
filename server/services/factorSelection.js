import {retrospectiveView} from './factorRetrospective.js';
import {readFileSync} from 'node:fs';

const source=JSON.parse(readFileSync(new URL('../data/factorCandidates.json',import.meta.url),'utf8'));
const factors={'in-momentum':'Momentum','in-growth':'Growth','in-value':'Value','in-quality':'Quality','in-all-weather':'‘All-weather’ composite'};
export const FACTOR_SNAPSHOT='india-factors-2026-10-11-v1';
export const factorIds=Object.keys(factors);
export function factorCandidates(id){
 return source.filter(x=>x.factor===factors[id]).map((h,i)=>({name:h.verifiedName||h.name,symbol:h.symbol,instrumentKey:h.instrumentKey,sector:h.sector,rank:i+1,score:Number(h.score_pct),weight:i<25?4:0}));
}
for(const id of factorIds){const rows=factorCandidates(id);if(rows.length!==50||new Set(rows.map(h=>h.symbol)).size!==50||rows.some((h,i)=>!h.instrumentKey||!Number.isFinite(h.score)||(i&&h.score>rows[i-1].score)))throw Error(`Invalid factor snapshot ${id}`);}
export function isMain25(id,holdings){const main=factorCandidates(id).slice(0,25);return main.length===25&&holdings?.length===25&&main.every(h=>holdings.some(x=>x.symbol===h.symbol&&Math.abs(x.weight-4)<1e-8));}
export function factorTarget(portfolio){
 const rows=factorCandidates(portfolio.id);if(rows.length!==50)throw Error('No verified factor selection for this portfolio');
 return {...portfolio,holdings:rows.slice(0,25),cashWeight:0,incomplete:false,factorSelection:FACTOR_SNAPSHOT,
  description:`${factors[portfolio.id]}: first 25 stocks in the October 2026 published factor-score ordering, equal 4% target weights. The other 25 are tracked separately as reserves.`,
  weightMethod:'25 holdings at 4% target weight each at rebalance; weights drift between rebalances. Reserve stocks have 0% main-portfolio allocation.'};
}
const valid=(h,p)=>p?.price>0&&p.instrumentKey===h.instrumentKey;
export function selectionStart(document){
 // A matching active allocation alone is insufficient: require a dated execution event.
 const event=[...(document.events||[])].reverse().find(e=>e.type==='rebalance'&&e.target?.factorSelection===FACTOR_SNAPSHOT&&isMain25(document.portfolio.id,e.target.holdings));
 return document.portfolio.factorSelection===FACTOR_SNAPSHOT&&isMain25(document.portfolio.id,document.portfolio.holdings)?event?.effectiveDate||null:null;
}
export function factorSelectionView(row,quotes={},now=new Date()){
 const s=row.document,id=row.portfolio_id,candidates=factorCandidates(id),start=selectionStart(s);
 if(!candidates.length)return null;
 const observed=s.history.filter(h=>start&&h.date>=start).map(h=>({...h,prices:Object.assign({},h.prices,...(s.factorEvidence||[]).filter(e=>e.date===h.date).map(e=>e.prices))})).sort((a,b)=>a.date.localeCompare(b.date));
 const baseline=observed.find(h=>h.date===start);
 const complete=h=>candidates.every(c=>valid(c,h?.prices?.[c.symbol]));
 // All three comparison lines share the exact same complete baseline and dates.
 const comparison=complete(baseline)?observed.filter(complete).map(h=>{
  const values=candidates.map(c=>h.prices[c.symbol].price/baseline.prices[c.symbol].price*100);
  const mean=a=>a.reduce((x,y)=>x+y,0)/a.length;
  return {date:h.date,main:mean(values.slice(0,25)),reserve:mean(values.slice(25)),all:mean(values)};
 }):[];
 const positions=candidates.map(c=>{
  const history=observed.filter(h=>valid(c,h.prices?.[c.symbol])).map(h=>({date:h.date,price:h.prices[c.symbol].price}));
  const last=history.at(-1),base=valid(c,baseline?.prices?.[c.symbol])?baseline.prices[c.symbol].price:null;
  const q=quotes[c.symbol],age=now.getTime()-Date.parse(q?.time),fresh=valid(c,q)&&age>=0&&age<=120000;
  return {...c,basePrice:base,entryAt:start,price:last?.price??null,priceDate:last?.date??null,history,
   returnPct:base&&last?(last.price/base-1)*100:null,livePrice:fresh?q.price:null,quoteTime:fresh?q.time:null,
   liveReturnPct:fresh&&base?(q.price/base-1)*100:null};
 });
 const sectors={};for(const c of candidates.slice(0,25))sectors[c.sector]=(sectors[c.sector]||0)+4;
 const liveComplete=complete(baseline)&&positions.every(h=>h.livePrice!=null);
 const liveValues=liveComplete?positions.map(h=>100*h.livePrice/h.basePrice):[];
 const mean=a=>a.reduce((x,y)=>x+y,0)/a.length;
 const indicative=liveComplete?{main:mean(liveValues.slice(0,25)),reserve:mean(liveValues.slice(25)),all:mean(liveValues),oldestQuote:positions.map(h=>h.quoteTime).sort()[0],newestQuote:positions.map(h=>h.quoteTime).sort().at(-1)}:null;
 return {id,snapshot:FACTOR_SNAPSHOT,sourceDate:'2026-10-11',marketDataDate:'2026-10-08',sourcePage:source.find(h=>h.factor===factors[id])?.page,
  selectionBasis:'Published factor-score order; displayed source order breaks rounded-score ties. This is an October snapshot, not a fresh ranking.',
  active:!!start,startDate:start,positions,comparison,indicative,sectors,mainCount:25,reserveCount:25,
  retrospective:retrospectiveView(s.factorRetrospective,candidates,FACTOR_SNAPSHOT,now),
  comparisonStatus:!start?'awaiting_rebalance':!complete(baseline)?'missing_baseline_prices':'recorded',
  missingBaseline:start?candidates.filter(c=>!valid(c,baseline?.prices?.[c.symbol])).map(c=>c.symbol):[],
  missingDates:observed.filter(h=>!complete(h)).map(h=>h.date)};
}
