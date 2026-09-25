import {useEffect,useMemo,useRef,useState} from 'react';
import {useSearchParams} from 'react-router-dom';
import {insiderActivity} from '@/lib/insiderTradingApi';
import {buildIntelligence,filingKey,newWatchlistFilings,number,sourceLink} from '@/lib/insiderIntelligence';
import './intelligenceDesk.css';
const STORAGE='agi-insider-watchlist-v1';
const money=value=>value==null?'Not disclosed':new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(value);
const count=value=>Number(value||0).toLocaleString('en-IN');
function readSaved(){try{const saved=JSON.parse(localStorage.getItem(STORAGE)||'{}');return saved&&typeof saved==='object'&&!Array.isArray(saved)?Object.fromEntries(Object.entries(saved).filter(([,v])=>v&&Array.isArray(v.seen)&&typeof v.company==='string')):{};}catch{return {};}}
export default function IntelligenceDesk(){
 const[feed,setFeed]=useState(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[refresh,setRefresh]=useState(0),[checked,setChecked]=useState(null);
 const[saved,setSaved]=useState(readSaved),[storageError,setStorageError]=useState(''),[query,setQuery]=useState(''),[onlySaved,setOnlySaved]=useState(false),[type,setType]=useState('highlights'),[page,setPage]=useState(1);
 const[params,setParams]=useSearchParams();const heading=useRef(null);const selected=params.get('company');
 useEffect(()=>{const controller=new AbortController();let active=true;setLoading(true);
  insiderActivity({regime:'insider'},{signal:controller.signal}).then(body=>{
   if(!active)return;
   if(body.source!=='warehouse'||!Array.isArray(body.trades))throw Error('Verified-format company intelligence is temporarily unavailable. Please refresh shortly.');
   setFeed(body);setError('');setChecked(new Date());
  }).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});
  return()=>{active=false;controller.abort();};
 },[refresh]);
 useEffect(()=>{const resume=()=>{if(document.visibilityState==='visible')setRefresh(n=>n+1);};const timer=setInterval(resume,300000);document.addEventListener('visibilitychange',resume);return()=>{clearInterval(timer);document.removeEventListener('visibilitychange',resume);};},[]);
 const asOf=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata'}).format(new Date());
 const companies=useMemo(()=>buildIntelligence(feed?.trades,asOf),[feed,asOf]);
 const company=companies.find(c=>c.id===selected);
 const alerts=useMemo(()=>newWatchlistFilings(companies,saved),[companies,saved]);
 const filtered=companies.filter(c=>(!onlySaved||saved[c.id])&&(!query||`${c.company} ${c.symbol||''}`.toLowerCase().includes(query.toLowerCase()))&&(type==='all'||type==='highlights'&&c.signals.length>0||c.signals.some(s=>s.kind===type)));
 const pages=Math.max(1,Math.ceil(filtered.length/8));const currentPage=Math.min(page,pages);
 useEffect(()=>{setPage(1);},[query,onlySaved,type]);
 useEffect(()=>{if(company)heading.current?.focus();},[selected,!!company]);
 function persist(next){setSaved(next);try{localStorage.setItem(STORAGE,JSON.stringify(next));setStorageError('');}catch{setStorageError('Browser storage is unavailable. Your watchlist will last only for this visit.');}}
 function toggle(c){const next={...saved};if(next[c.id])delete next[c.id];else next[c.id]={company:c.company,seen:c.rows.map(filingKey)};persist(next);}
 function open(c){setParams(p=>{const next=new URLSearchParams(p);if(c)next.set('company',c.id);else next.delete('company');return next;});}
 function acknowledge(){const next={...saved};for(const c of companies)if(next[c.id])next[c.id]={...next[c.id],seen:c.rows.map(filingKey)};persist(next);}
 return <section className="ii-desk" aria-label="Insider research intelligence">
  <header className="ii-heading"><div><span className="ii-eyebrow">RESEARCH INTELLIGENCE</span><h2>What deserves a closer look?</h2><p>Evidence from the last 30 calendar days · {asOf} (India). Company research prompts, with the filings behind them.</p></div><button className="ii-button" disabled={loading} onClick={()=>setRefresh(n=>n+1)}>{loading?'Checking filings…':'Refresh intelligence'}</button></header>
  <div className="ii-status"><span>Source: imported Trendlyne disclosures</span><span>Latest filing: {feed?.stats?.latestDate||'—'}</span><span>{checked?`Checked ${checked.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}`:'Waiting for data'}</span></div>
  <p className="ii-caveat">Observed coverage only; this feed may be incomplete and is limited to 5,000 imported rows. Reporting dates can differ from trade dates. Buyer independence and original filings have not been verified.</p>
  {error&&<p className="ii-warning" role="alert">{error}{feed?' Showing the last successful response.':''}</p>}
  {storageError&&<p className="ii-warning" role="status">{storageError}</p>}
  <details className="ii-watch"><summary>My watchlist · {Object.keys(saved).length} companies · {alerts.length} new or changed filings</summary><p>Saved in this browser. Checks every five minutes while this page is visible and whenever you return or refresh. No email or background notifications.</p>
   <div className="ii-watch-names">{Object.entries(saved).map(([id,entry])=><span key={id}><button onClick={()=>open({id})}>{entry.company}</button><button aria-label={`Remove ${entry.company} from watchlist`} onClick={()=>{const next={...saved};delete next[id];persist(next);}}>×</button></span>)}</div>
   {alerts.length?<><ul>{alerts.slice(0,20).map((alert,i)=><li key={filingKey(alert.row)+i}><button onClick={()=>open({id:alert.id})}>{alert.company}</button> · {alert.kind} · {alert.row.reported_on} · {alert.row.person}</li>)}</ul>{alerts.length>20&&<p>Showing 20 of {alerts.length} updates. Open each company for its full evidence.</p>}<button className="ii-button" onClick={acknowledge}>Mark all as reviewed</button></>:<p>No unseen filings in the currently available feed. This does not establish that no trading occurred.</p>}
  </details>
  {selected&&!company&&!loading&&<p className="ii-warning">This company is not present in the available feed. <button onClick={()=>open(null)}>Return to all companies</button></p>}
  {company&&<CompanyDetail key={company.id} company={company} heading={heading} close={()=>open(null)} saved={!!saved[company.id]} toggle={()=>toggle(company)}/>}
  <div className="ii-filters"><label>Find a company<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Company or ticker"/></label><label>Research focus<select value={type} onChange={e=>setType(e.target.value)}><option value="highlights">Highlighted activity</option><option value="all">All companies</option><option value="buying">Buying activity</option><option value="selling">Promoter selling</option><option value="risk">Pledge invocation</option><option value="size">Large ownership movements</option></select></label><label className="ii-checkbox"><input type="checkbox" checked={onlySaved} onChange={e=>{setOnlySaved(e.target.checked);if(e.target.checked)setType('all');}}/>My watchlist only</label></div>
  <p className="ii-caption">{filtered.length} companies · Invocation events first, then multiple-buyer activity, then latest disclosure. No predictive score.</p>
  <div className="ii-cards">{filtered.slice((currentPage-1)*8,currentPage*8).map(c=><article key={c.id} className="ii-card"><div className="ii-card-top"><span>{c.symbol||'Ticker not mapped'}</span><button className="ii-save" aria-pressed={!!saved[c.id]} onClick={()=>toggle(c)}>{saved[c.id]?'★ Saved':'☆ Watch'}</button></div><h3><button onClick={()=>open(c)}>{c.company}</button></h3><span className={`ii-tag ${c.signals[0]?.kind||''}`}>{c.signals[0]?.title||'No highlighted signal in 30 days'}</span><p>{c.signals[0]?.detail||'Review the transaction history below. Absence of a signal is not evidence of absence of trading.'}</p><div className="ii-metrics"><span><b>{c.buyers}</b>named buyers</span><span><b>{c.buys.length} / {c.sells.length}</b>buy / sell filings</span></div><small>Stated purchase value: {c.valued?money(c.buyValue):'Not disclosed'} · value on {c.valued}/{c.buys.length} purchases</small><footer><span>Latest {c.latest}</span><button onClick={()=>open(c)}>Why this matters →</button></footer></article>)}</div>
  {!loading&&!filtered.length&&<p className="ii-empty">No companies match these filters.</p>}
  <div className="ii-pagination"><button className="ii-button" disabled={currentPage===1} onClick={()=>setPage(currentPage-1)}>Previous</button><span>Page {currentPage} of {pages}</span><button className="ii-button" disabled={currentPage===pages} onClick={()=>setPage(currentPage+1)}>Next</button></div>
 </section>;
}
function CompanyDetail({company:c,heading,close,saved,toggle}){
 const[page,setPage]=useState(1);const pages=Math.max(1,Math.ceil(c.rows.length/20));const current=Math.min(page,pages);
 return <section className="ii-detail" aria-label={`${c.company} research detail`}><header><div><span className="ii-eyebrow">COMPANY EVIDENCE</span><h2 ref={heading} tabIndex={-1}>{c.company}</h2><p>{c.symbol||'Ticker not mapped'} · Share this view using the current page URL.</p></div><div><button className="ii-button" onClick={toggle}>{saved?'Remove from watchlist':'Add to watchlist'}</button><button className="ii-button" onClick={close}>Close detail</button></div></header>
  <h3>Why this matters</h3>{c.signals.length?c.signals.map(s=><div className="ii-reason" key={s.title}><b>{s.title}</b><p>{s.detail}</p></div>):<p>No qualifying signal in the last 30 days. Earlier disclosures remain available below.</p>}
  <div className="ii-context"><div><h3>Activity comparison</h3><table><thead><tr><th>Observed filings</th><th>Last 30 days</th><th>Previous 30 days</th></tr></thead><tbody><tr><th>Market purchases</th><td>{c.buys.length}</td><td>{c.priorBuys}</td></tr><tr><th>Market sales</th><td>{c.sells.length}</td><td>{c.priorSells}</td></tr></tbody></table><p>Window ends {c.asOf}. Zeros mean no matching imported records; coverage is not established as complete. This is not an unusual-activity score.</p></div><div><h3>Before drawing a conclusion</h3><ul><li>Check whether named buyers are connected or acting together.</li><li>Read original disclosures for purpose, holding changes and transaction dates.</li><li>Compare with company results, announcements and valuation.</li></ul><p>Price performance, valuations and historical insider hit rates are not connected. No return forecast is implied.</p></div></div>
  <h3>Supporting disclosures · {c.rows.length}</h3><p className="ii-caption">{c.linked} of {c.recent.length} recent rows include an original-source link. Unlinked rows remain imported evidence, not independently verified filings. Ownership percentage is the percentage of company equity reported as traded.</p>
  <div className="ii-table"><table><thead><tr><th>Reported / trade period</th><th>Person / role</th><th>Transaction</th><th>Shares / stated value</th><th>Company equity traded</th><th>Evidence</th></tr></thead><tbody>{c.rows.slice((current-1)*20,current*20).map(row=><tr key={filingKey(row)}><td>{row.reported_on}<small>{row.period||'Trade period not provided'}</small></td><td>{row.person||'Name not provided'}<small>{row.category||'Role not provided'}</small></td><td>{row.kind}<small>{row.mode} · {row.action}</small></td><td>{number(row.quantity)==null?'—':count(row.quantity)}<small>{money(number(row.value))}</small></td><td>{number(row.traded_pct)==null?'Not disclosed':`${number(row.traded_pct)}%`}</td><td>{sourceLink(row)?<a href={sourceLink(row)} target="_blank" rel="noopener noreferrer">Open disclosure ↗</a>:<span>Source document unavailable</span>}</td></tr>)}</tbody></table></div>
  <div className="ii-pagination"><button className="ii-button" disabled={current===1} onClick={()=>setPage(current-1)}>Previous filings</button><span>{current} / {pages}</span><button className="ii-button" disabled={current===pages} onClick={()=>setPage(current+1)}>Next filings</button></div>
 </section>;
}
