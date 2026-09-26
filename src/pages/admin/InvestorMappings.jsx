import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '@/lib/supabaseClient';
import { API_ORIGIN } from '@/config';
import './insiderTradesPaste.css';

const FEED='https://raw.githubusercontent.com/shivamagw06-dev/AGI/investor-valuation-data/investor-filings/latest.json';
const empty={profileId:'',holder:'',scope:'',bucket:'personal',validFrom:'',validTo:'',evidenceUrl:'',evidenceNote:''};
export default function InvestorMappings(){
 const [registry,setRegistry]=useState(null),[feed,setFeed]=useState(null),[form,setForm]=useState(empty),[query,setQuery]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 const [bse,setBse]=useState({xml:'',scripCode:'',period:'',sourceUrl:''});
 async function call(path,body){
  const {data}=await supabase.auth.getSession();
  if(!data?.session?.access_token)throw Error('Sign in with your administrator account.');
  const response=await fetch(`${API_ORIGIN||''}/api/intelligence/investor-mappings/${path}`,{method:body?'POST':'GET',headers:{Authorization:`Bearer ${data.session.access_token}`,...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});
  const result=await response.json();if(!response.ok||!result.ok)throw Error(result.detail||result.error||'Request failed.');return result;
 }
 async function load(){setError('');setBusy(true);try{
  const value=await call('review');setRegistry(value);
  const response=await fetch(FEED,{cache:'no-store'});if(!response.ok)throw Error('Review scan is temporarily unavailable.');setFeed(await response.json());
 }catch(e){setError(e.message);}finally{setBusy(false);}}
 useEffect(()=>{load();},[]);
 function field(k,v){setForm(f=>({...f,[k]:v}));setMessage('');}
 async function decide(status){setBusy(true);setError('');setMessage('');try{
  await call('review',{...form,status});setRegistry(await call('review'));setMessage(`Decision saved. The next daily scan will apply it. ${status==='approved'?'Only the specified legal name, dates and issuer scope are approved.':''}`);setForm(empty);
 }catch(e){setError(e.message);}finally{setBusy(false);}}
 async function importBse(){setBusy(true);setError('');setMessage('');try{
  const r=await call('bse',bse);setMessage(`Saved ${r.rows} named rows for ${r.stock}, as of ${r.period}. They will be matched on the next daily scan.`);setRegistry(await call('review'));
 }catch(e){setError(e.message);}finally{setBusy(false);}}
 const decisions=new Set((registry?.mappings||[]).map(r=>r.id));
 const candidates=(feed?.reviewCandidates||[]).filter(r=>!decisions.has(r.id)&&`${r.name} ${r.holder} ${r.stock}`.toLowerCase().includes(query.toLowerCase()));
 return <main className="itp"><header><h1>Investor identities & filing coverage</h1><p>Approve legal names and group membership with evidence. Suggestions never update public holdings until approved.</p><Link to="/admin/institutions-paste">← Investor table imports</Link></header>
 {error&&<p className="itp-error" role="alert">{error}</p>}{message&&<p className="itp-ok" role="status">{message}</p>}
 <div className="itp-bar"><button disabled={busy} onClick={load}>Refresh review queue</button><span>{registry?.mappings?.filter(m=>m.status==='approved').length||0} approved mappings · {candidates.length} pending suggestions</span></div>
 <section className="itp-help"><h2>Daily collection</h2><p>NSE filing checks run at 2 AM IST. Approved mappings apply to cached documents and new filings on the next run.</p><p><strong>BSE:</strong> {feed?.bseStatus?.message||'Connection status not available.'} {registry?.bseFilings?.length||0} original BSE documents imported.</p><p>Full BSE automation requires an authorised manifest feed configured on the scheduled collector. Until connected, original XBRL documents can be imported below; a successful NSE scan does not imply full BSE coverage.</p></section>
 <section><h2>Pending identity review</h2><label>Find an investor or shareholder <input type="search" value={query} onChange={e=>setQuery(e.target.value)}/></label><div className="itp-scroll"><table><thead><tr><th>Investor profile</th><th>Filed shareholder</th><th>Company / period</th><th>Reason</th><th>Review</th></tr></thead><tbody>{candidates.slice(0,100).map(r=><tr key={r.id}><td>{r.name}</td><td>{r.holder}</td><td>{r.stock}<br/>{r.period}</td><td>{r.reason}</td><td><button disabled={busy} onClick={()=>{setForm({...empty,profileId:r.profileId,holder:r.holder,scope:r.scope,validFrom:r.period,evidenceUrl:r.evidenceUrl});setMessage('Check the source and describe the identity or relationship before approving.');}}>Review</button></td></tr>)}</tbody></table></div><p>{candidates.length>100?'Showing the first 100; search to narrow the queue.':'No suggestion is treated as proof of identity.'}</p></section>
 <section className="itp-help"><h2>Mapping decision</h2><div className="itp-bar"><label>Investor <select value={form.profileId} onChange={e=>field('profileId',e.target.value)}><option value="">Choose investor</option>{registry?.directory?.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label><label>Full legal shareholder name <input value={form.holder} onChange={e=>field('holder',e.target.value)}/></label></div>
 <div className="itp-bar"><label>Issuer scope <input placeholder="ISIN, symbol, BSE code or *" value={form.scope} onChange={e=>field('scope',e.target.value)}/></label><label>Holding type <select value={form.bucket} onChange={e=>field('bucket',e.target.value)}><option value="personal">Personal direct</option><option value="family">Family / trust</option><option value="corporate">Corporate entity</option><option value="managed">Managed client / fund</option></select></label><label>Effective from <input type="date" value={form.validFrom} onChange={e=>field('validFrom',e.target.value)}/></label><label>Effective until (optional) <input type="date" value={form.validTo} onChange={e=>field('validTo',e.target.value)}/></label></div>
 <p>Use * only for an identity or membership verified across issuers. To replace an existing name or scope, revoke the old mapping first. Family affiliation does not establish ownership of every company with a similar name. Managed fund assets are not personal wealth or the parent bank’s own investments.</p>
 <label>Evidence URL <input type="url" style={{width:'100%'}} value={form.evidenceUrl} onChange={e=>field('evidenceUrl',e.target.value)}/></label>{form.evidenceUrl.startsWith('https://')&&<a href={form.evidenceUrl} target="_blank" rel="noopener noreferrer">Open evidence ↗</a>}
 <label>What does this evidence establish?<textarea rows={3} style={{width:'100%'}} value={form.evidenceNote} onChange={e=>field('evidenceNote',e.target.value)}/></label><div className="itp-bar"><button disabled={busy||!form.profileId} onClick={()=>decide('approved')}>Approve mapping</button><button disabled={busy||!form.profileId} onClick={()=>decide('rejected')}>Reject suggestion</button><button disabled={busy||!form.profileId} onClick={()=>decide('revoked')}>Revoke mapping</button></div></section>
 <details><summary>Existing decisions ({registry?.mappings?.length||0})</summary><div className="itp-scroll"><table><thead><tr><th>Investor</th><th>Shareholder</th><th>Scope / type</th><th>Status</th><th>Effective dates</th><th>Edit</th></tr></thead><tbody>{registry?.mappings?.map(m=><tr key={m.id}><td>{registry.directory.find(p=>p.id===m.profileId)?.name}</td><td>{m.holder}</td><td>{m.scope} · {m.bucket}</td><td>{m.status}</td><td>{m.validFrom} – {m.validTo||'ongoing'}</td><td><button disabled={busy} onClick={()=>setForm({...empty,...m})}>Review</button></td></tr>)}</tbody></table></div></details>
 <section className="itp-help"><h2>Import an original BSE XBRL document</h2><p>Use the original XML file, not a screenshot or a formatted spreadsheet. The issuer ISIN, BSE code, period and shareholder quantities are validated. Personal identifiers such as PAN are not retained.</p><div className="itp-bar"><label>BSE scrip code <input value={bse.scripCode} onChange={e=>setBse({...bse,scripCode:e.target.value})}/></label><label>Reporting period <input type="date" value={bse.period} onChange={e=>setBse({...bse,period:e.target.value})}/></label></div><label>Original public filing URL <input type="url" style={{width:'100%'}} value={bse.sourceUrl} onChange={e=>setBse({...bse,sourceUrl:e.target.value})}/></label><label>XML file <input type="file" accept=".xml,text/xml,application/xml" disabled={busy} onChange={async e=>{const f=e.target.files?.[0];if(!f)return;if(f.size>2000000){setError('Choose an XML file under 2 MB.');return;}setBse(v=>({...v,xml:''}));try{const xml=await f.text();setBse(v=>({...v,xml}));}catch{setError('Could not read this file.');}}}/></label><div className="itp-bar"><button disabled={busy||!bse.xml} onClick={importBse}>Validate and import original filing</button></div></section>
 </main>;
}
