import { useEffect, useState } from 'react';
import { ArrowLeft, Building2, Database, MapPin, Search, ShieldCheck } from 'lucide-react';
const BASE=import.meta.env.VITE_API_URL||window?.API_URL||'';
const load=async path=>{const r=await fetch(BASE+path);if(!r.ok)throw new Error('Private Markets API '+r.status);return r.json()};
const show=v=>v==null||v===''||v==='-'?'Not disclosed':String(v);
const fields={
 lbo:[['Debt / EBITDA','Total Debt/EBITDA [LTM]'],['Debt / Capital','Total Debt/Capital % [Latest Annual]'],['EBITDA growth rule','[EBITDA Growth >5%, 5Y] Left Side']],
 distressed:[['Debt / EBITDA','Total Debt/EBITDA [LTM]'],['Coverage','(EBITDA-CAPEX) / Interest Exp. [LTM]'],['Credit rating','S&P Entity Credit Rating - Issuer Credit Rating - Local Currency LT [Latest] (Rating)']],
 sale_divestment:[['Industry','Primary Industry'],['Recent development','Key Developments by Type -  [Last 3 Months]'],['Current investors','Current and Pending Investors']]
};
export function OpportunityIntelligence(){
 const[type,setType]=useState('lbo'),[search,setSearch]=useState(''),[rows,setRows]=useState([]),[busy,setBusy]=useState(true);
 useEffect(()=>{let live=true;setBusy(true);load('/api/pe/opportunities?type='+type+'&search='+encodeURIComponent(search)).then(d=>{if(live){setRows(d.opportunities||[]);setBusy(false)}}).catch(()=>live&&setBusy(false));return()=>{live=false}},[type,search]);
 const keys=fields[type].slice(0,2).map(x=>x[1]),coverage=rows.length?rows.filter(r=>keys.every(k=>r.observedMetrics?.[k]!=null&&r.observedMetrics[k]!=='')).length/rows.length:0;
 return <div className="pm2"><div className="pm2-controls"><div>{[['lbo','LBO candidates'],['sale_divestment','Sale / divestment'],['distressed','Distressed situations']].map(([id,label])=><button className={type===id?'active':''} onClick={()=>setType(id)} key={id}>{label}</button>)}</div><label><Search/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search opportunities"/></label></div><div className="pm2-summary"><strong>{rows.length}<small>filtered companies</small></strong><p><ShieldCheck/>Deterministic screens, not recommendations.</p></div>
 {coverage<.7&&<div className="pm2-insufficient"><Database/><p><b>Insufficient analytical coverage</b><br/>Required fields cover {Math.round(coverage*100)}%. Showing records instead of a misleading matrix.</p></div>}
 {busy?<div className="pm-loading">Loading evidence...</div>:<div className="pm2-grid">{rows.map(r=><article className="pm2-card" key={r.id}><header><h3>{r.companyName}</h3><span className={r.coverage>=.7?'good':''}>{Math.round(r.coverage*100)}% coverage</span></header><dl>{fields[type].map(([label,key])=><div key={key}><dt>{label}</dt><dd>{show(r.observedMetrics?.[key])}</dd></div>)}</dl><footer><MapPin/>{show(r.observedMetrics?.['Geographic Locations']||r.observedMetrics?.['Primary Address'])}</footer></article>)}</div>}</div>
}
export function InvestorIntelligence(){
 const[search,setSearch]=useState(''),[rows,setRows]=useState([]),[selected,setSelected]=useState(null);
 useEffect(()=>{let live=true;load('/api/pe/investors?search='+encodeURIComponent(search)).then(d=>live&&setRows(d.investors||[]));return()=>{live=false}},[search]);
 if(selected)return <div className="pm2-profile"><button onClick={()=>setSelected(null)}><ArrowLeft/>Investor directory</button><header><div><small>Observed investor profile</small><h2>{selected.name}</h2><p><MapPin/>{show(selected.geography)}</p></div><strong>{selected.transactions?.length||0}<small>parsed transactions</small></strong></header><section><h3>Observed transaction history</h3>{selected.transactions?.map(t=><article key={t.id}><time>{show(t.observedDate)}</time><div><b>{t.companyName}</b><p>{t.transactionDescription}</p></div></article>)}</section><p className="pm-notice"><ShieldCheck/>Historical activity does not imply current investor interest.</p></div>;
 return <div className="pm2"><div className="pm2-directory"><div><small>Global Investor Network</small><h2>{rows.length} observed financial buyers</h2></div><label><Search/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search investor or geography"/></label></div><div className="pm2-investors">{rows.map(r=><button key={r.id} onClick={()=>load('/api/pe/investors/'+r.id).then(setSelected)}><Building2/><span><b>{r.name}</b><small>{show(r.geography)}</small></span><strong>{r.recentTransactionCount}<small>recent</small></strong></button>)}</div></div>
}
