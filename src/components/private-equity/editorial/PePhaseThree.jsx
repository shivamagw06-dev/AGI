import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, BarChart3, Database, ShieldCheck } from 'lucide-react';
import API_ORIGIN from '@/config';
const BASE=API_ORIGIN||'';
const money=v=>v==null?'—':'₹'+(Number(v)>=1000?(Number(v)/1000).toFixed(1)+'B':Number(v).toLocaleString('en-IN')+'M');
export default function PePhaseThree(){
 const[data,setData]=useState(null),[error,setError]=useState(null);
 useEffect(()=>{fetch(BASE+'/api/pe/intelligence').then(r=>{if(!r.ok)throw Error('API '+r.status);return r.json()}).then(setData).catch(e=>setError(e.message))},[]);
 if(error)return <div className="pm-error">{error}</div>;
 if(!data)return <div className="pm-loading">Building evidence-controlled intelligence...</div>;
 const max=Math.max(...data.timeline.map(x=>x.count),1);
 return <div className="pm3"><section className="pm3-contract"><ShieldCheck/><div><small>Private Markets evidence contract</small><h2>Observed facts first. Interpretation second.</h2><p>Every result distinguishes observed, calculated, screened, interpreted and unknown evidence.</p></div><span>{data.provenance.recordCount} records<br/>through {data.provenance.effectiveDate||'—'}</span></section>
 <div className="pm3-kpis"><article><BarChart3/><small>Valuation coverage</small><strong>{data.valuation.coverage}%</strong><p>{data.valuation.disclosed} deals with pre/post-money evidence</p></article><article><Activity/><small>Observed window</small><strong>{data.timeline.length} days</strong><p>Historical activity, not a market-wide estimate</p></article><article><Database/><small>Change events</small><strong>{data.monitoring.events}</strong><p>Canonical changes recorded since import</p></article></div>
 <section className="pm3-panel"><header><div><small>Historical activity</small><h2>Observed deal cadence</h2></div><span>All transaction domains shown separately</span></header><div className="pm3-timeline">{data.timeline.map(x=><div key={x.date}><i style={{height:Math.max(5,x.count/max*100)+'%'}}/><b>{x.count}</b><small>{x.date.slice(5)}</small></div>)}</div></section>
 <section className="pm3-panel"><header><div><small>Valuation intelligence</small><h2>Disclosed private-market valuations</h2></div><span>{data.valuation.coverage}% coverage</span></header>{data.valuation.rows.length?<div className="pm3-valuations">{data.valuation.rows.map(r=><article key={r.id}><div><strong>{r.company}</strong><small>{r.transactionType} · {r.date}</small></div><dl><div><dt>Deal value</dt><dd>{money(r.dealValue)}</dd></div><div><dt>Pre-money</dt><dd>{money(r.preMoney)}</dd></div><div><dt>Post-money</dt><dd>{money(r.postMoney)}</dd></div></dl></article>)}</div>:<p className="pm3-empty">No disclosed valuation records in the selected evidence window.</p>}</section>
 <section className="pm3-withheld"><AlertTriangle/><div><small>Buyer-target matching</small><h2>Withheld: insufficient mandate evidence</h2><p>Investor sector mandate and target-criteria coverage are below the required 70%. Historical transactions alone cannot establish current interest, so AGI does not publish a match ranking.</p></div><dl><div><dt>Geography</dt><dd>{data.matching.geographyCoverage}%</dd></div><div><dt>Sector mandate</dt><dd>{data.matching.sectorCoverage}%</dd></div><div><dt>Target criteria</dt><dd>{data.matching.criteriaCoverage}%</dd></div></dl></section>
 </div>
}
