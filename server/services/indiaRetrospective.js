import {createHash} from 'node:crypto';
import {factorCandidates,FACTOR_SNAPSHOT} from './factorSelection.js';
import {retrospectiveView} from './factorRetrospective.js';
export function indiaHistorySpec(row){
 const p=row.document.portfolio;if(p.market!=='india')return null;
 const factors=factorCandidates(row.portfolio_id),factor=factors.length===50;
 const keys=new Map((row.document.account?.holdings||[]).map(h=>[h.symbol,h.instrumentKey]));
 const holdings=(factor?factors.slice(0,25):p.holdings).map(h=>({...h,instrumentKey:h.instrumentKey||keys.get(h.symbol)}));
 const candidates=factor?factors:holdings;
 const cashWeight=factor?0:Number(p.cashWeight||0),direction=p.direction==='short'?'short':'long';
 const hash=createHash('sha256').update(JSON.stringify({holdings:holdings.map(h=>[h.symbol,h.instrumentKey,h.weight]),cashWeight,direction,categories:p.categories})).digest('hex').slice(0,20);
 return {candidates,holdings,cashWeight,direction,categories:p.categories||[],selectionDate:factor?'2026-10-11':p.asOf,snapshot:factor?FACTOR_SNAPSHOT:'india-current-v1-'+hash,factor};
}
export function indiaRetrospectiveView(row,now=new Date()){
 const spec=indiaHistorySpec(row);if(!spec)return null;
 const view=retrospectiveView(row.document.factorRetrospective,spec.candidates,spec.snapshot,now,spec);
 const basket=(holdings,extra={})=>retrospectiveView(row.document.factorRetrospective,holdings,spec.snapshot,now,{...spec,holdings,cashWeight:0,...extra});
 return {...view,id:row.portfolio_id,name:row.document.portfolio.name,factor:spec.factor,
  reserve:spec.factor?basket(spec.candidates.slice(25).map(h=>({...h,weight:4})),{direction:'long'}):null,
  all50:spec.factor?basket(spec.candidates.map(h=>({...h,weight:2})),{direction:'long'}):null,
  categories:spec.categories.map(c=>({name:c.name,categoryWeight:c.weight,...basket(c.holdings.map(h=>({...h,instrumentKey:spec.candidates.find(x=>x.symbol===h.symbol)?.instrumentKey})))}))};
}
