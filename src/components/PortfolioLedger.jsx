import MobileDisclosure from '@/components/mobile/MobileDisclosure';
import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {API_ORIGIN} from '@/config';
import {supabase} from '@/lib/supabaseClient';
import {PriceChart} from './IndiaPortfolios';
export function usePortfolioLedger(id){
 const [state,setState]=useState({data:null,error:''});
 useEffect(()=>{let active=true;const c=new AbortController();async function run(){try{const {data:auth}=await supabase.auth.getSession();const r=await fetch(`${API_ORIGIN||''}/api/portfolios/${id}/ledger`,{headers:auth.session?{Authorization:`Bearer ${auth.session.access_token}`}:{},cache:'no-store',signal:c.signal});const d=await r.json();if(!r.ok)throw Error(d.error||'Tracking unavailable');if(active)setState({data:d,error:''});}catch(e){if(active&&e.name!=='AbortError')setState(s=>({...s,error:e.message}));}}run();const t=setInterval(run,300000);return()=>{active=false;c.abort();clearInterval(t);};},[id]);return state;
}
const pct=n=>n==null?'—':`${n>=0?'+':''}${n.toFixed(2)}%`;
export default function PortfolioLedger({portfolio:p,admin=false}){
 const {data:d,error}=usePortfolioLedger(p.id);
 return <section className="pf-performance india-portfolios"><span className="pf-eyebrow">DATED ALLOCATIONS · CONTINUOUS MODEL RECORD</span><h2>Portfolio performance and rebalances</h2>{error&&<p className="pf-warning">{error}. Existing historical charts remain separately labelled below.</p>}{d&&<>
 <p>{p.market==='usa'?'History before ledger activation is a frozen retrospective simulation from 15 September. Later allocations apply only at their recorded effective close.':'Launch history is preserved. Later allocations apply only at their recorded effective close.'} Model performance, not broker executions.</p>
 <div className="india-metrics"><div><span>Continuous model return</span><strong>{pct(d.returnPct)}</strong></div><div><span>Portfolio index</span><strong>{d.nav?.toFixed(2)||'—'}</strong></div><div><span>Latest complete prices</span><strong>{d.priceDate}</strong></div></div>
 <PriceChart title="Continuous portfolio performance" currency={p.market==='usa'?'USD':'INR'} points={[...(p.market==='india'?[{date:d.startedAt,value:100}]:[]),...d.history.map(h=>({date:h.date+(p.market==='india'?'T10:30:00Z':'T20:00:00Z'),value:h.nav}))]}/>
 {d.pending&&<p className="pf-warning">Pending rebalance: {d.pending.effectiveDate} close · {d.pending.reason}. Current holdings remain in effect until complete prices are recorded. Missing prices or a non-trading date keep the request pending.</p>}
 {admin&&<MobileDisclosure title="Manage portfolio"><Link className="pf-button" to={`/admin/portfolio-rebalances?edit=${p.id}`}>Schedule rebalance →</Link></MobileDisclosure>}
 <details><summary>Rebalance history and preserved allocations</summary>{d.events.map((e,i)=><article key={i}><h3>{e.type} · {e.effectiveDate||e.recordedAt?.slice(0,10)}</h3><p>{e.reason} {e.type==='rebalance'?`Before ${e.preNav.toFixed(4)} · cost ${e.cost.toFixed(4)} · after ${e.postNav.toFixed(4)} index points`:''}</p>{(e.target||e.portfolio)&&<table><thead><tr><th>Stock</th><th>Target weight</th></tr></thead><tbody>{(e.target||e.portfolio).holdings.map(h=><tr key={h.symbol}><td>{h.name} ({h.symbol})</td><td>{h.weight.toFixed(3)}%</td></tr>)}</tbody></table>}{e.trades&&<table><thead><tr><th>Symbol</th><th>Model unit change</th><th>Price basis</th></tr></thead><tbody>{e.trades.map(t=><tr key={t.symbol}><td>{t.symbol}</td><td>{t.units.toFixed(6)}</td><td>{t.price.toFixed(4)}</td></tr>)}</tbody></table>}</article>)}</details>
 <p>{d.basis}. Rebalance costs are disclosed per event; taxes and short-borrow costs are excluded. No real orders. Category portfolios rebalance within their existing sleeves, retaining each category’s accumulated gains and losses.</p>
 </>}</section>;
}
