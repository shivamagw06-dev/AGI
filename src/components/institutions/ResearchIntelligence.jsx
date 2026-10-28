import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import research from '@/data/institutionResearch.json';
import briefs from '../../../public/data/institution-briefs.json';
import './researchIntelligence.css';
const dataUrl='https://raw.githubusercontent.com/shivamagw06-dev/AGI/institution-research-data/institution-research/performance.json';
function usePerformance(){
 const [data,setData]=useState(null);
 useEffect(()=>{
  const c=new AbortController();let active=true,inFlight=false;
  async function load(){if(inFlight)return;inFlight=true;try{
   const r=await fetch(dataUrl,{signal:AbortSignal.any([c.signal,AbortSignal.timeout(15000)]),cache:'no-store'});
   if(!r.ok)throw Error();const d=await r.json();if(active&&d.schemaVersion===1)setData(d);
  }catch{/* Retain the last successful dated research results. */}finally{inFlight=false;}}
  load();const timer=setInterval(()=>{if(!document.hidden)load();},240000);
  return()=>{active=false;c.abort();clearInterval(timer);};
 },[]);return data;
}
const pct = x => Number.isFinite(x) ? `${x>0?'+':''}${x.toFixed(2)}%` : 'Pending';
export function ObservationPerformance({observation,performance}){
 const item=performance?.observations?.[observation.id];
 const [window,setWindow]=useState('all');
 const points=item?.series || [];
 const filtered=window==='all'||!points.length?points:points.filter(p=>p.date>=new Date(Date.parse(points.at(-1)?.date)-Number(window)*86400000).toISOString().slice(0,10));
 const paths=key=>filtered.map((p,i)=>`${i===0?'M':'L'}${8+(i/Math.max(filtered.length-1,1))*304},${96-((p[key]-min)/span)*80}`).join(' ');
 const values=filtered.flatMap(p=>[p.stockReturn,p.benchmarkReturn]).filter(Number.isFinite),min=Math.min(0,...values),span=Math.max(1,Math.max(0,...values)-min);
 return <section className="ir-performance"><strong>After AGI tracking registration</strong><p>{item ? `First observed publicly ${item.firstPublishedAt?.slice(0,10)} · baseline ${item.baselineDate || 'awaiting next completed session'}`:'Awaiting first public registration. No historical performance is implied.'}</p>
 {item?.baselineDate&&<><p>Latest common closing date: {points.at(-1)?.date || 'unavailable'} · data checked {performance.updatedAt?.slice(0,10) || 'date unavailable'}. These are recorded closing prices, not live quotes.</p>{item.status!=='Tracking adjusted closes'&&<p role="status">{item.status}. Previously recorded outcomes remain visible.</p>}<div className="ir-metrics"><span>Stock <b>{pct(points.at(-1)?.stockReturn)}</b></span><span>{observation.country==='IN'?'Nifty 50':'S&P 500'} <b>{pct(points.at(-1)?.benchmarkReturn)}</b></span><span>Difference <b>{Number.isFinite(points.at(-1)?.excessPp)?`${points.at(-1).excessPp.toFixed(2)} pp`:'Pending'}</b></span></div><label>Chart window <select value={window} onChange={e=>setWindow(e.target.value)}><option value="all">Since registration</option><option value="30">30 days</option><option value="90">90 days</option></select></label>{filtered.length>1?<svg viewBox="0 0 320 110" role="img" aria-label={`Cumulative stock return and benchmark return since ${item.baselineDate}`}><path d={paths('stockReturn')} stroke="#197c78" fill="none" strokeWidth="2"/><path d={paths('benchmarkReturn')} stroke="#5267a1" fill="none" strokeWidth="2"/></svg>:<p>Chart appears after two comparable closes.</p>}{filtered.length>1&&<small>{filtered[0].date} — {filtered.at(-1).date}</small>}<small>Green: stock · Blue: benchmark · All values remain rebased to the registration baseline. Adjusted closes, local currency, before costs and taxes. No short P&amp;L or manager performance.</small></>}
 </section>;
}
export default function ResearchIntelligence({country}){
 const [expanded,setExpanded]=useState(false);
 const [query,setQuery]=useState(''),[onlyFollowed,setOnlyFollowed]=useState(false),[followed,setFollowed]=useState(()=>{try{const d=JSON.parse(localStorage.getItem('agi-ownership-followed')||'[]');return Array.isArray(d)?d.filter(x=>typeof x==='string'):[];}catch{return [];}});
 const performance=usePerformance();
 const [seen,setSeen]=useState(()=>{try{return JSON.parse(localStorage.getItem('agi-ownership-seen')||'{}')||{};}catch{return {};}});
 const signature=s=>JSON.stringify(s.owners.map(o=>[o.slug,o.period,o.prior,o.latest,o.status]));
 const changed=research.stocks.filter(s=>followed.includes(s.key)&&seen[s.key]&&seen[s.key]!==signature(s));
 useEffect(()=>{try{localStorage.setItem('agi-ownership-seen',JSON.stringify(seen));}catch{}},[seen]);
 useEffect(()=>{try{localStorage.setItem('agi-ownership-followed',JSON.stringify(followed));}catch{}},[followed]);
 const stocks=useMemo(()=>research.stocks.filter(s=>s.country===country&&s.stock.toLowerCase().includes(query.toLowerCase())&&(!onlyFollowed||followed.includes(s.key))).slice(0,query||onlyFollowed||expanded?30:6),[country,query,onlyFollowed,followed,expanded]);
 return <section className="ir-section"><header><div><p className="institutions-kicker">OWNERSHIP RESEARCH</p><h2>What changed, and what it means</h2><p>Verified observations are separated from source-reported comparisons. Historical ownership is not a live buying signal.</p></div><span>Evidence reviewed {briefs.reviewedAt}</span></header>
 <div className="ir-briefs">{briefs.observations.filter(o=>o.country===country).map(o=><article key={o.id}><span className="ir-badge">{o.verification}</span><h3>{o.stock}: {o.title}</h3><p className="ir-period">{o.period}</p><p><b>Disclosed fact.</b> {o.fact}</p><p><b>AGI interpretation.</b> {o.interpretation}</p><p><b>Watch next.</b> {o.watch}</p><div className="ir-sources">{o.sources.map(s=><a key={s.url} href={s.url} target="_blank" rel="noreferrer">{s.label} ↗</a>)}</div><ObservationPerformance observation={o} performance={performance}/></article>)}</div>
 {country==='IN'&&<><h3>Compare covered ownership changes</h3><p>Same-quarter comparisons only. Values retain source rounding; small differences may be indistinguishable. Group, corporate and unresolved identities are shown separately, not counted as independent fund votes. These counts are not market-wide flows or primary-filing verification.</p><div className="rk-toolbar"><label>Find a company<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Company name"/></label><label><input type="checkbox" checked={onlyFollowed} onChange={e=>setOnlyFollowed(e.target.checked)}/> My followed stocks</label></div><p className="rk-table-hint">Following is saved on this browser. Open a stock to review updated disclosures; no email or push notifications are sent.</p>
 {changed.length>0&&<p className="ip-notice" role="status">{changed.length} followed companies have changed comparisons since your last saved view. <button onClick={()=>setSeen(prev=>({...prev,...Object.fromEntries(changed.map(s=>[s.key,signature(s)]))}))}>Mark reviewed</button></p>}
 <div className="ir-stock-grid">{stocks.map(s=><article key={s.key}><header><h3>{s.stock}</h3><button aria-pressed={followed.includes(s.key)} onClick={()=>{setFollowed(prev=>prev.includes(s.key)?prev.filter(k=>k!==s.key):[...prev,s.key]);setSeen(prev=>({...prev,[s.key]:signature(s)}));}}>{followed.includes(s.key)?'Following':'Follow'}</button></header><p>{s.periods.join(', ')} · source-reported comparison</p><div className="ir-metrics"><span>Increased <b>{s.increased}</b></span><span>Reduced <b>{s.reduced}</b></span><span>Within rounding <b>{s.uncertain}</b></span></div><p>{s.groupsExcluded} group / unresolved identities excluded from counts.</p><details><summary>Investors, periods and evidence ({s.owners.length})</summary>{s.owners.map((o,i)=><div key={o.slug+':'+i} className="ir-owner"><Link to={`/institutions/in/${o.slug}`}>{o.name}</Link><small>{o.entityType} · {o.counted?'Included in covered count':'Excluded from fund count'}</small><span>{o.priorPeriod}: {o.prior}% → {o.period}: {o.latest}%</span><span>{o.status} · {o.delta>0?'+':''}{o.delta.toFixed(2)} pp ±{o.uncertainty.toFixed(2)} pp rounding range</span><a href={o.sourceUrl} target="_blank" rel="noreferrer">Source checked {o.retrievedAt} ↗</a></div>)}</details></article>)}</div>{!stocks.length&&<p>No matching covered comparisons.</p>}{!query&&!onlyFollowed&&<button onClick={()=>setExpanded(x=>!x)}>{expanded?'Show fewer companies':'Show more companies'}</button>}<p>Showing {stocks.length} matching companies. Search to find another company. Sector positioning and investment recommendations require additional analysis.</p></>}
 </section>;
}
