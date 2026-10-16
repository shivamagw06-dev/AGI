import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet';
import { Link, useSearchParams, useLocation, useNavigate } from 'react-router-dom';
import { usaInstitutionalInvestors } from '@/data/usInstitutionalInvestors';
import { indiaInstitutionalInvestors } from '@/data/institutionalInvestors';
import { indiaInvestors, usaInvestors } from '@/data/richKids';
import './richKids.css';
import PortfolioCharts from '@/components/institutions/PortfolioCharts';
import InvestorSelector from '@/components/institutions/InvestorSelector';
import { useInvestorValuations, valuationMoney, valuationTime, valuationStale } from '@/lib/investorValuations';
import { investorSlug } from '@/lib/investorProfiles';
import { investorPath } from '@/lib/investorProfiles';
import { API_ORIGIN } from '@/config';

function Entries({ items, tone = '' }) {
 return items.length ? <ul className={`rk-entries ${tone}`}>{items.map(item => <li key={`${item.url || ""}:${item.label}`}>{item.label}</li>)}</ul> : <span className="rk-muted">—</span>;
}
export default function InstitutionsPage() {
 const [params, setParams] = useSearchParams();
 const country = params.get('country') === 'US' ? 'US' : 'IN';
 const category=params.get('category')==='institutional'?'institutional':'individual';
 const selectionKey=category==='individual'?country:`${country}-institutional`;
 const valuations = useInvestorValuations();
 const [selections,setSelections] = useState(()=>{try{const saved=JSON.parse(localStorage.getItem('agi-investor-selections')||'{}');return Object.fromEntries(['IN','US','IN-institutional','US-institutional'].map(code=>[code,Array.isArray(saved?.[code])?saved[code].filter(x=>typeof x==='string'):[]]));}catch{return {IN:[],US:[]};}});
 useEffect(()=>{try{localStorage.setItem('agi-investor-selections',JSON.stringify(selections));}catch{/* Storage may be unavailable in private browsing. */}},[selections]);
 const selected=selections[selectionKey]||[];
 const changeSelection=names=>setSelections(previous=>({...previous,[selectionKey]:names}));
 const [query,setQuery] = useState('');
 const [sort,setSort] = useState('value');
 const location=useLocation(),navigate=useNavigate();
 const [snapshot,setSnapshot]=useState(null),[error,setError]=useState(''),[refresh,setRefresh]=useState(0);
 useEffect(()=>{if(location.pathname==='/rich-kids')navigate(`/institutions${location.search}`,{replace:true});},[location.pathname,location.search,navigate]);
 useEffect(()=>{let stopped=false;const controller=new AbortController();setError('');
  async function load(){try{const response=await fetch(`${API_ORIGIN || ''}/api/intelligence/institutions?country=${country}&category=${category}`,{signal:AbortSignal.any([controller.signal,AbortSignal.timeout(30000)]),cache:'no-store'});if(!response.ok)throw Error('Could not load the published table. Please retry.');const data=await response.json();if(!stopped){setSnapshot(data);setError('');}}catch(e){if(!stopped&&e.name!=='AbortError')setError(e.message);}}
  load();const interval=setInterval(()=>{if(!document.hidden)load();},60000);return()=>{stopped=true;controller.abort();clearInterval(interval);};
 },[country,category,refresh]);
 const current=snapshot?.country===country&&(snapshot.category||'individual')===category?snapshot:null;
 const investors = current ? (current.published?current.rows:category==='institutional'?(country==='IN'?indiaInstitutionalInvestors:usaInstitutionalInvestors):country==='IN'?indiaInvestors:usaInvestors) : [];
 const currency=country==='IN'?'₹':'$',unit=country==='IN'?'Cr':'M';
 const chosenInvestors=useMemo(()=>selected.length?investors.filter(row=>selected.includes(row.name)):investors,[investors,selected]);
 const rows = useMemo(() => chosenInvestors.filter(row => [row.name,...row.sectors.map(x=>x.label),...row.holdings.map(x=>x.label)].join(' ').toLowerCase().includes(query.trim().toLowerCase())).sort((a,b)=>sort==='name'?a.name.localeCompare(b.name):sort==='stocks'?b.stocks-a.stocks:b.value-a.value),[chosenInvestors,query,sort]);
 const hasQuarterlyHistory = investors.some(row => row.quarterlyNetWorth && row.quarterlyNetWorth !== 'Not supplied');
 const choose = code => {setParams({country:code,category});setQuery('');};
 const keyboardTab = event => {if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const next=event.key==='Home'?'IN':event.key==='End'?'US':country==='IN'?'US':'IN';choose(next);document.getElementById(`rk-tab-${next}`)?.focus();}};
 return <main className="rk-page institutions-directory">
  <Helmet><title>Institutions — Investor Portfolios | AGI</title><meta name="description" content="Explore prominent investor portfolios, sector preferences, top holdings and reported portfolio changes across India and the USA." /></Helmet>
  <header className="institutions-header rk-container"><div><p className="institutions-kicker">RESEARCH / OWNERSHIP</p><h1>Institutions</h1><p>Disclosed portfolios of leading investors across India and the United States.</p></div><div className="institutions-edition"><span>PORTFOLIO MONITOR</span><strong>{country === 'IN' ? 'India' : 'United States'}</strong><span>{country === 'IN' ? 'Values in INR crore' : 'Values in USD million'}</span></div></header>
  <div className="rk-container">
   <div className="rk-tabs" role="tablist" aria-label="Investor market" onKeyDown={keyboardTab}>{[['IN','India'],['US','USA']].map(([code,label])=><button id={`rk-tab-${code}`} key={code} role="tab" aria-selected={country===code} aria-controls="rk-panel" tabIndex={country===code?0:-1} onClick={()=>choose(code)}>{label}<span>{code==='IN'?'INR':'USD'}</span></button>)}</div>
   <div className="institution-category" aria-label="Investor category">{[['individual','Investor directory'],['institutional','Institutional investors']].map(([code,label])=><button key={code} aria-pressed={category===code} onClick={()=>{setParams({country,category:code});setQuery('');}}>{label}</button>)}</div>
   <section id="rk-panel" role="tabpanel" aria-labelledby={`rk-tab-${country}`} tabIndex={0}>
    <div className="institutions-status"><p><span className={`institutions-status-dot ${valuationStale(valuations) ? 'is-stale' : ''}`} aria-hidden="true"/>{valuations ? `Prices refreshed ${valuationTime(valuations.updatedAt)}${valuationStale(valuations) ? ' · refresh overdue' : ''}` : 'Price refresh pending'}<span className="institutions-schedule">Daily refresh · 2:00 AM IST</span></p><button className="rk-refresh" onClick={()=>setRefresh(x=>x+1)}>↻ Refresh table</button></div>
    {error?<div className="rk-empty" role="alert">{error}</div>:!current?<p role="status">Loading published portfolios…</p>:investors.length ? <>
     {category==='institutional'&&!current.published&&<p className="rk-table-hint">{country==='IN'?'100 institutions from the supplied list. The source directory contains 124 entries; the remaining 24 were not supplied.':'16 institutions from the supplied US list, matched to public sources.'} Summary valuation date was not supplied.</p>}
     <InvestorSelector key={`${country}-${category}`} investors={investors} selected={selected} onChange={changeSelection} />
     <PortfolioCharts investors={rows} country={country} linkProfiles />
     <div className="rk-toolbar"><label>Search portfolios<input type="search" placeholder="Investor, company or sector…" value={query} onChange={e=>setQuery(e.target.value)} /></label><label>Sort by<select value={sort} onChange={e=>setSort(e.target.value)}><option value="value">Reported value: high to low</option><option value="stocks">Stock count: high to low</option><option value="name">Investor name: A–Z</option></select></label><p aria-live="polite">{rows.length} of {investors.length} investors</p></div>
     <p className="rk-table-hint">{category==='institutional'?'Select an institution for sourced holdings and coverage details. Daily estimates appear after eligible positions are priced; summary and holdings dates may differ.':'Select an investor to view holdings. Daily estimates exclude unpriced positions; partial totals are marked.'}</p>
     <div className="rk-table-wrap" role="region" aria-label="Investor portfolio comparison" tabIndex={0}><table><caption className="rk-sr-only">{country==='IN'?'Indian':'US'} investor portfolios. Currency: {country==='IN'?'INR crore':'USD million'}.</caption><thead><tr>{['Investor','Reported value','Daily estimate','Stocks','Sector exposure',...(hasQuarterlyHistory ? ['Quarterly history'] : []),'Top holdings','Reported additions','Reported reductions'].map(label=><th key={label} scope="col">{label}</th>)}</tr></thead><tbody>{rows.map(row=>{const valuation=valuations?.profiles?.[`${country.toLowerCase()}-${investorSlug(row.name)}`]; return <tr key={row.name}>
      <th scope="row"><Link to={investorPath(country,row.name)}>{row.name}<span className="rk-external" aria-hidden="true"> →</span></Link></th>
      <td className="rk-number"><strong>{currency}{row.value.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})} {unit}</strong><span className={row.change>=0?'rk-positive':'rk-negative'}>{row.change==null?'Not supplied':`${row.change>0?'+':''}${row.change}%`}</span></td><td className="rk-number">{valuation?.pricedCount ? <><strong>{valuationMoney(valuation.value,country)}</strong><span>{valuation.pricedCount}/{valuation.rowCount} priced{valuation.pricedCount < valuation.rowCount ? ' · partial' : ''}</span><span className="institutions-period">{valuation.reportPeriod}</span>{valuation.dayChangePct != null && <span className={valuation.dayChangePct >= 0 ? 'rk-positive' : 'rk-negative'}>{valuation.dayChangePct > 0 ? '+' : ''}{valuation.dayChangePct.toFixed(2)}% price movement</span>}</> : <span className="rk-muted">Not priced</span>}</td><td className="rk-count">{row.stocks}</td><td><Entries items={row.sectors}/></td>{hasQuarterlyHistory && <td><span className="rk-muted">{row.quarterlyNetWorth || '—'}</span></td>}<td><Entries items={row.holdings}/></td><td><Entries items={row.bought} tone="rk-positive"/></td><td><Entries items={row.sold} tone="rk-negative"/></td>
     </tr>;})}</tbody></table>{!rows.length&&<div className="rk-no-results"><h3>No matching investors</h3><p>Try a different search or investor selection.</p><button onClick={()=>{setQuery('');changeSelection([]);}}>Reset filters</button></div>}</div>
     <details className="rk-notes"><summary>Methodology</summary><p className="rk-snapshot">{current?.published ? `Directory updated ${valuationTime(current.updatedAt)} · ${current.asOf ? `Valuation date ${current.asOf}` : 'Source valuation date not supplied'}` : 'Supplied directory snapshot'}</p><p>* Portfolio value reflects the supplied listed-shareholding figures, not personal net worth. Change periods are as reported by the source; the valuation date is shown above when supplied. “Recently bought” and “Recently sold” retain the source labels and percentages; these are not verified trade executions or investment returns.</p><p>Quarterly history is shown only when supplied as text or figures; copied graph images are not reconstructed. A dash means no entry was provided, not necessarily no activity. Figures are reproduced from the supplied snapshot and may not reconcile across columns. Family and associate portfolios can overlap; their values should not be added together.</p><p>Administrator-published portfolio snapshots. Tables update after publication and refresh every minute while this page is visible; this is not a live price feed.</p></details>
    </> : <div className="rk-empty"><span className="rk-empty-mark" aria-hidden="true">{country}</span><h3>{category==='institutional'?'Institutional portfolios are ready for import.':'Portfolios are coming next.'}</h3><p>Investor entries have not been published for this market and category yet. Once available, they will appear here with holdings, sector preferences and reported changes.</p><button onClick={()=>choose('IN')}>Explore India portfolios <span aria-hidden="true">→</span></button></div>}
   </section>
  </div>
 </main>;
}
