import PortfolioLedger from '@/components/PortfolioLedger';
import USPortfolioTracking from '@/components/USPortfolioTracking';
import CompanyLogo, {HoldingLogos} from '@/components/CompanyLogo';
import IndiaPortfolios, {IndiaPortfolioDetail} from '@/components/IndiaPortfolios';
import ConvictionPortfolio from '@/components/ConvictionPortfolio';
import { useEffect, useState } from 'react';
import { Link, NavLink, useParams } from 'react-router-dom';
import { ArrowUpRight, Globe2, Layers3 } from 'lucide-react';
import { API_ORIGIN } from '@/config';
import { useAuth } from '@/contexts/AuthContext';
import { isAdmin } from '@/lib/adminAuth';
import './portfolios.css';
import PortfolioResearch from '@/components/PortfolioResearch';
import PortfolioPerformance from '@/components/PortfolioPerformance';
import PortfolioExplorer from '@/components/PortfolioExplorer';

export default function Portfolios() {
  const { market, id } = useParams();
  const { user } = useAuth();
  const [rows,setRows] = useState([]), [loading,setLoading] = useState(true), [error,setError] = useState('');
  useEffect(() => { const controller = new AbortController();
    fetch(`${API_ORIGIN || ''}/api/portfolios`, {signal:controller.signal,cache:'no-store'}).then(async r => {const d=await r.json();if(!r.ok)throw new Error(d.error);return d;}).then(d=>setRows(d.portfolios)).catch(e=>{if(e.name!=='AbortError')setError(e.message);}).finally(()=>setLoading(false));
    return ()=>controller.abort();
  },[]);
  const marketRows=rows.filter(p=>p.market===market);
  const selected=marketRows.find(p=>p.id===id);
  const admin=isAdmin(user);
  return <main className="agi-portfolios pf-wide">
    <header className="pf-hero"><div><span className="pf-eyebrow">AGI / PORTFOLIO LIBRARY</span><h1>Portfolios<span>.</span></h1><p>Explore an investment idea. Look inside every allocation.</p></div>{admin&&(!market||id)&&<Link className="pf-button" to="/admin/portfolios">Manage portfolios <ArrowUpRight size={16}/></Link>}</header>
    <nav className="pf-tabs" aria-label="Portfolio markets"><NavLink end to="/portfolios">Overview</NavLink><NavLink to="/portfolios/india">India</NavLink><NavLink to="/portfolios/usa">USA</NavLink></nav>
    {error&&<p role="alert" className="pf-warning">{error} <button onClick={()=>window.location.reload()}>Retry</button></p>}
    {!market ? <><div className="pf-markets">{[['india','India','Build your Indian equity strategies.'],['usa','USA','Explore thematic, multi-asset and investor-inspired portfolios.']].map(([key,name,desc])=><Link key={key} to={`/portfolios/${key}`} className="pf-market"><div className="pf-market-top"><span className="pf-market-code">{key==='india'?'IN / INR':'US / USD'}</span><Globe2 size={24}/></div><h2>{name} <ArrowUpRight/></h2><p>{desc}</p><div className="pf-market-tags">{(key==='india'?['Factor strategies','Conviction baskets','Daily tracking']:['Megatrends','Multi-asset','Thematic ideas']).map(tag=><span key={tag}>{tag}</span>)}</div><HoldingLogos market={key} holdings={rows.find(p=>p.id===(key==='india'?'in-preferred':'us-top10'))?.holdings||[]}/><strong>{loading?'Loading…':`${rows.filter(p=>p.market===key).length} portfolios`}</strong></Link>)}</div><div className="pf-overview-guide"><div><span>01 / DISCOVER</span><h3>Find your investment approach</h3><p>Explore factors, themes and research baskets across two markets.</p></div><div><span>02 / LOOK INSIDE</span><h3>Know what you own</h3><p>Inspect every company, its allocation and the portfolio methodology.</p></div><div><span>03 / FOLLOW</span><h3>Track the evidence</h3><p>Review dated prices and returns with their calculation assumptions.</p></div></div><p className="pf-footnote">Research allocations for exploration. No broker orders are placed from this page.</p></> : !['india','usa'].includes(market) ? <p>Market not found. <Link to="/portfolios">Back to portfolios</Link></p> : loading ? <p role="status">Loading portfolios…</p> : id ? selected ? (market==='india'?(selected.conviction?<ConvictionPortfolio portfolio={selected} admin={admin}/>:<IndiaPortfolioDetail portfolio={selected} admin={admin}/>):<PortfolioDetail portfolio={selected} admin={admin}/>) : <p>Portfolio not found. <Link to={`/portfolios/${market}`}>Back to list</Link></p> : (market==='india'?<IndiaPortfolios portfolios={marketRows} admin={admin}/>:<PortfolioExplorer key={market} portfolios={marketRows} market={market} admin={admin}/>) }
  </main>;
}
function PortfolioDetail({portfolio:p,admin}) {
  const total=p.holdings.reduce((a,h)=>a+h.weight,0);
  return <section><Link className="pf-back" to={`/portfolios/${p.market}`}>← All {p.market==='usa'?'USA':'India'} portfolios</Link><div className="pf-heading"><div><span className="pf-eyebrow">{p.category} / {p.customized?'AGI CUSTOM':'REFERENCE SNAPSHOT'}</span><h2>{p.name}</h2><p>{p.description}</p></div>{admin&&<Link className="pf-button" to={`/admin/portfolios?edit=${p.id}`}>Edit holdings</Link>}</div><PortfolioLedger portfolio={p} admin={admin}/><details><summary>Current-allocation historical simulation</summary><USPortfolioTracking portfolio={p}/></details><div className="pf-detail-grid"><div className="pf-holdings"><h3>Portfolio allocation</h3><table><thead><tr><th>Stock / instrument</th><th>Symbol</th><th>Weight</th></tr></thead><tbody>{p.holdings.map((h,i)=><tr key={i}><td><div className="pf-company-cell"><CompanyLogo market="usa" symbol={h.symbol} name={h.name}/><strong>{h.name}</strong></div><div className="pf-bar"><i style={{width:`${h.weight}%`}}/></div></td><td>{h.symbol||'Unverified'}</td><td>{h.weight.toFixed(2)}%</td></tr>)}</tbody></table></div><aside className="pf-summary"><span className="pf-eyebrow">ALLOCATION NOTES</span><h3>{p.holdings.length} holdings</h3><p>Allocation date<br/><strong>{p.asOf}</strong></p><p>Disclosed weight<br/><strong>{total.toFixed(2)}%</strong></p>{p.incomplete&&<p className="pf-warning">{Math.max(0,100-total).toFixed(2)}% is unallocated or undisclosed. This is not a complete portfolio; weights have not been rescaled.</p>}<p>Symbols marked unverified need instrument matching before use. These allocations are not linked to execution or automatic rebalancing.</p>{p.sourceUrl&&<details><summary>Allocation source</summary><p>{p.customized?(p.id==='us-top10'?'Original library reference (current allocation selected by AGI)':'Originally based on'):'Source'}: <a href={p.sourceUrl} target="_blank" rel="noreferrer">{p.sourceName} ↗</a><br/>Captured {p.sourceAsOf||p.asOf}</p></details>}<p>Historical simulations below use current allocations; they are not this portfolio’s actual track record.</p></aside></div><PortfolioPerformance portfolio={p}/><PortfolioResearch portfolio={p}/></section>;
}
