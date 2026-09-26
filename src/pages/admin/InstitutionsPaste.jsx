import { useState } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '@/lib/supabaseClient';
import { API_ORIGIN } from '@/config';
import { tableClipboard } from '@/lib/institutionsClipboard';
import './insiderTradesPaste.css';
export default function InstitutionsPaste(){
 const [category,setCategory]=useState('individual');
 const [country,setCountry]=useState('IN'),[text,setText]=useState(''),[asOf,setAsOf]=useState(''),[checked,setChecked]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[result,setResult]=useState(null);
 function reset(){setChecked(null);setResult(null);setError('');}
 async function call(operation){setBusy(true);setError('');setResult(null);try{
  const {data}=await supabase.auth.getSession();if(!data?.session?.access_token)throw Error('Sign in with your administrator account.');
  const response=await fetch(`${API_ORIGIN || ''}/api/intelligence/institutions/${operation}`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${data.session.access_token}`},body:JSON.stringify({text,country,category,asOf:asOf||null})});
  const payload=await response.json();if(!response.ok||!payload.ok)throw Error(payload.errors?.join('\n')||payload.error||payload.detail||'Import failed.');
  if(operation==='preview')setChecked(payload);else{setResult(payload);setChecked(null);}
 }catch(e){setError(e.message);setChecked(null);}finally{setBusy(false);}}
 return <main className="itp"><header><Link to="/admin/investor-mappings">Investor identity review & BSE filings →</Link><h1>Institutions — paste & publish</h1><p>Copy the complete table including headers from your source, Excel or Sheets. Check it, then publish to update the website immediately.</p></header>
 <div className="itp-bar"><label>Investor category <select disabled={busy} value={category} onChange={e=>{setCategory(e.target.value);setText('');reset();}}><option value="individual">Existing investor directory</option><option value="institutional">Institutional investors</option></select></label><label>Market <select disabled={busy} value={country} onChange={e=>{setCountry(e.target.value);setText('');reset();}}><option value="IN">India · ₹ crore (Cr)</option><option value="US">USA · $ million (M)</option></select></label><label>Valuation date (optional) <input type="date" disabled={busy} value={asOf} onChange={e=>{setAsOf(e.target.value);reset();}}/></label></div>
 <div className="itp-help"><p>Columns: Superstar · Portfolio Value* (change) · #Of Stocks · Sector Preference · Quarterly Net Worth · Top Holdings · Recently bought · Recently sold.</p><p>Both screenshot formats are supported. Portfolio value examples: India “334,805.84 Cr ↓ -5.62%”; USA “313,025.25 M ↑ 2.29%”. Tab-separated, CSV and Markdown tables work. Copy the actual table, not a screenshot. Graph images do not contain transferable quarterly figures; missing history stays blank.</p><p><strong>Publish replaces the entire {country==='IN'?'India':'USA'} {category==='institutional'?' institutional':''} table.</strong> Paste all investors you want shown for this market. Other markets and categories are unchanged.</p></div>
 {error&&<div className="itp-error" role="alert" style={{whiteSpace:'pre-wrap'}}>{error}</div>}
 {result&&<div className="itp-ok" role="status">Published {result.row_count} investors. <Link to={`/institutions?country=${country}&category=${category}`} target="_blank">View the updated page ↗</Link></div>}
 <textarea className="itp-paste" rows={14} aria-label="Institution table" disabled={busy} value={text} onChange={e=>{setText(e.target.value);reset();}} onPaste={e=>{const rich=e.clipboardData.getData('text/html');if(rich){const converted=tableClipboard(rich);if(converted){e.preventDefault();setText(converted);reset();}}}} placeholder="Paste your complete table here, including its header row."/>
 <div className="itp-bar"><button className="itp-ghost" disabled={busy||!text.trim()} onClick={()=>call('preview')}>{busy?'Working…':'Check table'}</button><button className="itp-go" disabled={busy||!checked?.ok} onClick={()=>call('publish')}>Publish {country==='IN'?'India':'USA'} table</button></div>
 {checked&&<section className="itp-check"><h2>{checked.row_count} investors · {checked.currency} {checked.unit}</h2><p>{checked.duplicate_rows} exact duplicates removed. Review all parsed rows before publishing.</p><div className="itp-scroll"><table><thead><tr>{['Investor','Portfolio value','Change','Stocks','Sectors','Quarterly net worth','Top holdings','Recently bought','Recently sold'].map(x=><th key={x}>{x}</th>)}</tr></thead><tbody>{checked.rows.map(r=><tr key={r.name}><td>{r.name}</td><td>{r.value.toLocaleString()} {checked.unit}</td><td>{r.change==null?'—':`${r.change}%`}</td><td>{r.stocks}</td><td>{r.sectors.map(x=>x.label).join('; ')}</td><td>{r.quarterlyNetWorth||'Not supplied'}</td><td>{r.holdings.map(x=>x.label).join('; ')}</td><td>{r.bought.map(x=>x.label).join('; ')||'—'}</td><td>{r.sold.map(x=>x.label).join('; ')||'—'}</td></tr>)}</tbody></table></div></section>}
 </main>;
}
