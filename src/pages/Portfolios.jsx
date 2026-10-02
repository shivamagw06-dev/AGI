import { useEffect, useState } from 'react';
import { Link, NavLink, useParams } from 'react-router-dom';
import { ArrowUpRight, Globe2, Layers3 } from 'lucide-react';
import { API_ORIGIN } from '@/config';
import { useAuth } from '@/contexts/AuthContext';
import { isAdmin } from '@/lib/adminAuth';
import './portfolios.css';
import PortfolioResearch from '@/components/PortfolioResearch';
import PortfolioPerformance from '@/components/PortfolioPerformance';

export default function Portfolios() {
  const { market, id } = useParams();
  const { user } = useAuth();
  const [rows,setRows] = useState([]), [loading,setLoading] = useState(true), [error,setError] = useState('');
  const [search,setSearch] = useState(''), [category,setCategory] = useState('All');
  useEffect(() => { const controller = new AbortController();
    fetch(`${API_ORIGIN || ''}/api/portfolios`, {signal:controller.signal,cache:'no-store'}).then(async r => {const d=await r.json();if(!r.ok)throw new Error(d.error);return d;}).then(d=>setRows(d.portfolios)).catch(e=>{if(e.name!=='AbortError')setError(e.message);}).finally(()=>setLoading(false));
    return ()=>controller.abort();
  },[]);
  useEffect(()=>{setCategory('All');setSearch('');},[market]);
  const marketRows=rows.filter(p=>p.market===market);
  const selected=marketRows.find(p=>p.id===id);
  const visible=marketRows.filter(p=>(category==='All'||p.category===category)&&`${p.name} ${p.holdings.map(h=>`${h.name} ${h.symbol}`).join(' ')}`.toLowerCase().includes(search.toLowerCase()));
  const admin=isAdmin(user);
  return <main className="agi-portfolios">
    <header className="pf-hero"><div><span className="pf-eyebrow">AGI / PORTFOLIO LIBRARY</span><h1>Portfolios<span>.</span></h1><p>Explore an investment idea. Look inside every allocation.</p></div>{admin&&<Link className="pf-button" to="/admin/portfolios">Manage portfolios <ArrowUpRight size={16}/></Link>}</header>
    <nav className="pf-tabs" aria-label="Portfolio markets"><NavLink end to="/portfolios">Overview</NavLink><NavLink to="/portfolios/india">India</NavLink><NavLink to="/portfolios/usa">USA</NavLink></nav>
    {error&&<p role="alert" className="pf-warning">{error} <button onClick={()=>window.location.reload()}>Retry</button></p>}
    {!market ? <><div className="pf-markets">{[['india','India','Build your Indian equity strategies.'],['usa','USA','Explore thematic, multi-asset and investor-inspired portfolios.']].map(([key,name,desc])=><Link key={key} to={`/portfolios/${key}`} className="pf-market"><Globe2 size={30}/><h2>{name} <ArrowUpRight/></h2><p>{desc}</p><strong>{loading?'Loading…':`${rows.filter(p=>p.market===key).length} portfolios`}</strong></Link>)}</div><p className="pf-footnote">Research allocations for exploration. No broker orders are placed from this page.</p></> : !['india','usa'].includes(market) ? <p>Market not found. <Link to="/portfolios">Back to portfolios</Link></p> : loading ? <p role="status">Loading portfolios…</p> : id ? selected ? <PortfolioDetail portfolio={selected} admin={admin}/> : <p>Portfolio not found. <Link to={`/portfolios/${market}`}>Back to list</Link></p> : <>
      <div className="pf-heading"><div><span className="pf-eyebrow">{market==='usa'?'UNITED STATES':'INDIA'}</span><h2>{market==='usa'?'A world of investment ideas.':'Your India investment desk.'}</h2></div><span>{marketRows.length} portfolios</span></div>
      {market==='usa'&&<p className="pf-footnote">Initial allocations captured from Vested on 2 October 2026. Independent AGI reference library; no affiliation implied. These are dated snapshots, not live holdings or AGI performance results.</p>}
      {marketRows.length>0&&<div className="pf-filters"><input aria-label="Search portfolios or holdings" placeholder="Search portfolios or holdings…" value={search} onChange={e=>setSearch(e.target.value)}/><select aria-label="Portfolio category" value={category} onChange={e=>setCategory(e.target.value)}>{['All',...new Set(marketRows.map(p=>p.category))].map(c=><option key={c}>{c}</option>)}</select></div>}
      <div className="pf-grid">{visible.map(p=><Link className="pf-card" to={`/portfolios/${market}/${p.id}`} key={p.id}><div className="pf-card-top"><Layers3 size={22}/><span>{p.category}</span><ArrowUpRight size={18}/></div><h3>{p.name}</h3><p>{p.description||p.holdings.slice(0,3).map(h=>h.name).join(' · ')}</p><div className="pf-card-meta"><b>{p.holdings.length} {p.incomplete?'disclosed ':''}holdings</b><span>{p.customized?'AGI custom':'Reference snapshot'}</span></div>{p.incomplete&&<small className="pf-warning">Incomplete allocation · undisclosed holdings excluded</small>}</Link>)}</div>
      {!visible.length&&!error&&<div className="pf-empty"><Layers3 size={32}/><h3>{marketRows.length?'No matching portfolios':'India portfolios are ready for your strategy.'}</h3><p>{marketRows.length?'Try another search or category.':'Add stocks and target weights from the admin editor.'}</p>{admin&&<Link className="pf-button" to="/admin/portfolios">Create a portfolio</Link>}</div>}
    </>}
  </main>;
}
function PortfolioDetail({portfolio:p,admin}) {
  const total=p.holdings.reduce((a,h)=>a+h.weight,0);
  return <section><Link className="pf-back" to={`/portfolios/${p.market}`}>← All {p.market==='usa'?'USA':'India'} portfolios</Link><div className="pf-heading"><div><span className="pf-eyebrow">{p.category} / {p.customized?'AGI CUSTOM':'REFERENCE SNAPSHOT'}</span><h2>{p.name}</h2><p>{p.description}</p></div>{admin&&<Link className="pf-button" to={`/admin/portfolios?edit=${p.id}`}>Edit holdings</Link>}</div><div className="pf-detail-grid"><div className="pf-holdings"><h3>Portfolio allocation</h3><table><thead><tr><th>Stock / instrument</th><th>Symbol</th><th>Weight</th></tr></thead><tbody>{p.holdings.map((h,i)=><tr key={i}><td><strong>{h.name}</strong><div className="pf-bar"><i style={{width:`${h.weight}%`}}/></div></td><td>{h.symbol||'Unverified'}</td><td>{h.weight.toFixed(2)}%</td></tr>)}</tbody></table></div><aside className="pf-summary"><span className="pf-eyebrow">ALLOCATION NOTES</span><h3>{p.holdings.length} holdings</h3><p>Allocation date<br/><strong>{p.asOf}</strong></p><p>Disclosed weight<br/><strong>{total.toFixed(2)}%</strong></p>{p.incomplete&&<p className="pf-warning">{Math.max(0,100-total).toFixed(2)}% is unallocated or undisclosed. This is not a complete portfolio; weights have not been rescaled.</p>}<p>Symbols marked unverified need instrument matching before use. These allocations are not linked to execution or automatic rebalancing.</p>{p.sourceUrl&&<p>{p.customized?'Originally based on':'Source'}: <a href={p.sourceUrl} target="_blank" rel="noreferrer">{p.sourceName} ↗</a><br/>Captured {p.sourceAsOf||p.asOf}</p>}<p>Historical simulations below use current allocations; they are not this portfolio’s actual track record.</p></aside></div><PortfolioPerformance portfolio={p}/><PortfolioResearch portfolio={p}/></section>;
}
