import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {API_ORIGIN} from '@/config';
import {supabase} from '@/lib/supabaseClient';
import {IndiaPortfolioDetail} from '@/components/IndiaPortfolios';
import '../portfolios.css';
const pct=v=>v==null?'—':`${v>=0?'+':''}${v.toFixed(2)}%`;
export default function GrowthMomentum(){
 const [result,setResult]=useState(null),[error,setError]=useState('');
 useEffect(()=>{let active=true,controller;
  async function refresh(){controller?.abort();controller=new AbortController();try{
   const {data}=await supabase.auth.getSession();if(!active)return;if(!data.session)throw Error('Sign in as an administrator to view this experiment.');
   const response=await fetch(`${API_ORIGIN||''}/api/portfolios/admin/growth-momentum`,{headers:{Authorization:`Bearer ${data.session.access_token}`},cache:'no-store',signal:controller.signal});
   const body=await response.json();if(!response.ok)throw Error(body.error||'Administrator access required.');
   if(active){setResult(body);setError('');}
  }catch(e){if(active&&e.name!=='AbortError'){setError(e.message);setResult(null);}}}
  refresh();const timer=setInterval(refresh,60000);return()=>{active=false;controller?.abort();clearInterval(timer);};
 },[]);
 return <main className="agi-portfolios"><Link to="/admin/portfolios">← Portfolio administration</Link><header className="pf-heading"><div><span className="pf-eyebrow">ADMIN ONLY · FORWARD RESEARCH</span><h1>Growth + Momentum experiment</h1><p>50% Growth · 50% Momentum. No broker orders, automatic rebalancing or public listing.</p></div></header>
 {error&&<p role="alert" className="pf-warning">{error}</p>}
 {!result&&!error&&<p role="status">Loading private allocation…</p>}
 {result&&<><h2>Compare recorded performance</h2><p>Each portfolio uses its own recorded launch prices. Compare only matching dates; these are not historical backtests. Fees, dividends and corporate actions need separate review.</p><div className="pf-holdings" style={{overflowX:'auto'}}><table><thead><tr><th>Portfolio</th><th>Since launch</th><th>Recorded launch</th><th>Latest close date</th></tr></thead><tbody>{result.tracking.portfolios.map(t=><tr key={t.id}><td>{t.id==='in-growth-momentum-private'?'Growth + Momentum':t.id==='in-growth'?'Growth':'Momentum'}</td><td>{pct(t.returnPct)}</td><td>{t.startedAt?new Date(t.startedAt).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})+' IST':'Awaiting launch'}</td><td>{t.priceDate||'—'}</td></tr>)}</tbody></table></div>
 <details className="india-method"><summary>Source allocations and overlapping weights</summary><p>{result.portfolio.weightMethod}</p><p>{result.portfolio.sources.map(s=>`${s.name}: ${s.stockCount} stocks, revision ${s.revision}, dated ${s.asOf}`).join(' · ')}</p><div style={{overflowX:'auto'}}><table><thead><tr><th>Stock</th><th>Growth contribution</th><th>Momentum contribution</th><th>Total weight</th></tr></thead><tbody>{(result.tracking.portfolios.find(t=>t.id===result.portfolio.id)?.positions||result.portfolio.holdings).map(h=><tr key={h.symbol}><td>{h.symbol}</td><td>{(h.contributions?.find(c=>c.portfolioId==='in-growth')?.weight||0).toFixed(3)}%</td><td>{(h.contributions?.find(c=>c.portfolioId==='in-momentum')?.weight||0).toFixed(3)}%</td><td>{h.weight.toFixed(3)}%</td></tr>)}</tbody></table></div></details>
 <IndiaPortfolioDetail portfolio={result.portfolio} admin={false} trackingResult={{data:result.tracking,error:''}}/>
 </>}
 </main>;
}
