import React,{useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {supabase} from '@/lib/supabaseClient';
import {API_ORIGIN} from '@/config';
async function request(path='',body){
 const {data}=await supabase.auth.getSession();if(!data.session)throw Error('Admin sign-in required');
 const r=await fetch(`${API_ORIGIN||''}/api/intelligence/research-refresh${path}`,{method:body?'POST':'GET',headers:{Authorization:`Bearer ${data.session.access_token}`,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
 const d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');return d;
}
const stamp=s=>s?new Date(s).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})+' IST':'—';
export default function ResearchRefresh(){
 const [data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function load(){try{setData(await request());setError('');}catch(e){setError(e.message);}}
 useEffect(()=>{load();},[]);
 async function action(path,body){setBusy(true);setError('');try{await request(path,body);await load();}catch(e){setError(e.message);}finally{setBusy(false);}}
 return <main className="agi-portfolios pf-editor"><h1>Research update agent</h1><p>Server-run reviews every 15 days. No ChatGPT session is required once the data source and schedule are connected.</p><Link to="/admin/portfolios">Portfolios</Link> · <Link to="/admin/portfolio-rebalances">Dated rebalances</Link>
 {error&&<p role="alert">{error}</p>}{data&&<>
 <section><h2>Connection and schedule</h2><p><strong>Trendlyne source: {data.sourceConfigured?'Configured — see last run for validation':'Not connected'}</strong></p><p>Schedule: {data.state.enabled?'Enabled':'Paused'} · Next eligible check: {stamp(data.state.next_due_at)}</p><p>Five screeners and investor directories can publish after validation. Individual holding-detail imports are not connected. Portfolios receive eligibility reports only; allocations do not change automatically.</p>
 {!data.sourceConfigured&&<p>One-time setup required: an approved automated Trendlyne export feed must be configured on the server. A signed-in desktop browser is not a server connection.</p>}
 <button disabled={busy||!data.sourceConfigured&&!data.state.enabled} onClick={()=>action('/schedule',{enabled:!data.state.enabled})}>{data.state.enabled?'Pause schedule':'Enable 15-day schedule'}</button> <button disabled={busy} onClick={()=>action('/run',{})}>{busy?'Checking…':'Run check now'}</button> <button disabled={busy} onClick={load}>Refresh status</button></section>
 <h2>Run reports</h2>{!data.runs.length&&<p>No run has completed yet.</p>}{data.runs.map(run=><details key={run.id}><summary>{stamp(run.started_at)} · {run.status==='complete'?'Data refresh complete; portfolio/detail limitations remain':run.status}</summary>
 {(run.report.blockers||[]).map((b,i)=><p key={i}>{b}</p>)}
 <div style={{overflowX:'auto'}}><table><thead><tr><th>Dataset</th><th>Status</th><th>Source date</th><th>Rows</th><th>Added / removed</th></tr></thead><tbody>{(run.report.publications||[]).map(p=><tr key={p.name}><td>{p.name}</td><td>{p.status}</td><td>{p.asOf}</td><td>{p.rowCount}</td><td>{p.added?.length??'—'} / {p.removed?.length??'—'}</td></tr>)}</tbody></table></div>
 {(run.report.portfolioReviews||[]).map(p=><details key={p.id}><summary>{p.name} — {p.holdings.length} holdings reviewed</summary><div style={{overflowX:'auto'}}><table><thead><tr><th>Stock</th><th>Target %</th><th>Outcome</th><th>Reasons</th></tr></thead><tbody>{p.holdings.map(h=><tr key={h.symbol}><td>{h.symbol}</td><td>{Number(h.weight).toFixed(2)}</td><td>{h.status}</td><td>{[...(h.failures||[]),...h.reasons].join('; ')}</td></tr>)}</tbody></table></div></details>)}
 <button onClick={()=>{const blob=new Blob([JSON.stringify(run.report,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`research-update-${run.id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}}>Download report</button></details>)}
 </>}</main>;
}
