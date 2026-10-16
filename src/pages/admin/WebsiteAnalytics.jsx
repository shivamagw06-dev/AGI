import {useEffect,useState} from 'react';
import {supabase} from '@/lib/supabaseClient';
import {API_ORIGIN} from '@/config';
import './websiteAnalytics.css';
const number=n=>Number(n||0).toLocaleString('en-IN');
function Ranking({title,rows=[]}){return <section className="wa-panel"><h2>{title}</h2>{rows.length?<table><thead><tr><th>Name</th><th>Page views</th></tr></thead><tbody>{rows.map(r=><tr key={r.label}><td>{r.label}</td><td>{number(r.views)}</td></tr>)}</tbody></table>:<p>No activity recorded in this period.</p>}</section>;}
export default function WebsiteAnalytics(){
 const [days,setDays]=useState(7),[data,setData]=useState(null),[error,setError]=useState(''),[retry,setRetry]=useState(0);
 useEffect(()=>{let active=true;const abort=new AbortController();setData(null);setError('');
  async function load(){try{const {data:auth}=await supabase.auth.getSession();if(!auth?.session?.access_token)throw Error('Sign in with your administrator account.');
   const r=await fetch(`${API_ORIGIN||''}/api/intelligence/website-analytics/summary?days=${days}`,{headers:{Authorization:`Bearer ${auth.session.access_token}`},cache:'no-store',signal:AbortSignal.any([abort.signal,AbortSignal.timeout(25000)])});
   const value=await r.json();if(!r.ok||!value.ok)throw Error(value.error||'Analytics could not load.');if(active){setData(value);setError('');}
  }catch(e){if(active)setError(e.message);}}
  load();const timer=setInterval(()=>{if(!document.hidden)load();},60000);return()=>{active=false;abort.abort();clearInterval(timer);};
 },[days,retry]);
 const max=Math.max(1,...(data?.daily||[]).map(d=>d.views));
 return <main className="wa"><header><div><p className="wa-kicker">AGI · ADMIN ONLY</p><h1>Website analytics</h1><p>Understand who arrives, what they read, and which tools they use.</p></div><div className="wa-controls"><label>Period<select value={days} onChange={e=>setDays(Number(e.target.value))}><option value={1}>Today</option><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option></select></label><button onClick={()=>setRetry(r=>r+1)}>Refresh</button></div></header>
 {error&&<p role="alert" className="wa-error">{error}{data?' Showing the last successful result.':''}</p>}
 {!data&&!error&&<p role="status">Loading website activity…</p>}
 {data&&<><p className="wa-meta">All dates use IST · Updated {new Date(data.updatedAt).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})}{data.trackingSince?` · First recorded event ${new Date(data.trackingSince).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})}`:' · Tracking is ready; waiting for the first visitor.'}</p>
 <div className="wa-metrics">{[['Visitors',data.visitors,'Unique anonymous browsers'],['Visits',data.visits,'Sessions after 30 minutes of inactivity'],['Page views',data.pageviews,'Public page openings'],['Repeat visitors',data.repeatVisitors,'Browsers with 2+ visits in this period'],['Sign-ups',data.signups,'Browser-reported completions'],['Model downloads',data.downloads,'Successful download actions']].map(([label,value,note])=><section key={label}><h2>{label}</h2><strong>{number(value)}</strong><p>{note}</p></section>)}</div>
 <section className="wa-panel"><div className="wa-trend-heading"><h2>Daily page views</h2><span>{number(data.active)} browsers viewed a page in the last 5 minutes</span></div>{!data.pageviews?<p>No page views yet. Counts start after tracking was installed; previous visits are not reconstructed.</p>:<div className="wa-chart" role="img" aria-label={`Daily page views over ${days} days. Exact figures are available below.`}>{data.daily.map(d=><div key={d.date} title={`${d.date}: ${d.views} views`}><span style={{height:`${Math.max(d.views?2:0,d.views/max*150)}px`}}/><small>{d.date.slice(5)}</small></div>)}</div>}<details><summary>View daily figures</summary><table><thead><tr><th>Date (IST)</th><th>Page views</th></tr></thead><tbody>{data.daily.map(d=><tr key={d.date}><td>{d.date}</td><td>{number(d.views)}</td></tr>)}</tbody></table></details></section>
 <div className="wa-grid"><Ranking title="Most-viewed pages" rows={data.pages}/><Ranking title="Traffic sources" rows={data.referrers}/><Ranking title="Devices" rows={data.devices}/></div>
 <footer>Visitor counts estimate browsers, not people. Clearing storage or using another device can count again. Privacy settings, blocked requests and basic bot filtering affect coverage. Sign-ups are browser-reported completion events, not an audited account total. Location is not collected. No activity from before installation is included.</footer></>}
 </main>;
}
