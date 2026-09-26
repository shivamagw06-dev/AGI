import { useMemo, useState } from 'react';
import { Helmet } from 'react-helmet';
import { useSearchParams } from 'react-router-dom';
import { indiaInvestors, usaInvestors } from '@/data/richKids';
import './richKids.css';

function Entries({ items, tone = '' }) {
 return items.length ? <ul className={`rk-entries ${tone}`}>{items.map(item => <li key={item.url}><a href={item.url} target="_blank" rel="noopener noreferrer">{item.label}<span className="rk-external" aria-hidden="true"> ↗</span></a></li>)}</ul> : <span className="rk-muted">—</span>;
}
export default function RichKidsPage() {
 const [params, setParams] = useSearchParams();
 const country = params.get('country') === 'US' ? 'US' : 'IN';
 const [query,setQuery] = useState('');
 const [sort,setSort] = useState('value');
 const investors = country === 'IN' ? indiaInvestors : usaInvestors;
 const rows = useMemo(() => investors.filter(row => [row.name,...row.sectors.map(x=>x.label),...row.holdings.map(x=>x.label)].join(' ').toLowerCase().includes(query.trim().toLowerCase())).sort((a,b)=>sort==='name'?a.name.localeCompare(b.name):sort==='stocks'?b.stocks-a.stocks:b.value-a.value),[investors,query,sort]);
 const choose = code => {setParams({country:code});setQuery('');};
 const keyboardTab = event => {if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const next=event.key==='Home'?'IN':event.key==='End'?'US':country==='IN'?'US':'IN';choose(next);document.getElementById(`rk-tab-${next}`)?.focus();}};
 return <main className="rk-page">
  <Helmet><title>Rich Kids — Investor Portfolios | AGI</title><meta name="description" content="Explore prominent investor portfolios, sector preferences, top holdings and reported portfolio changes across India and the USA." /></Helmet>
  <header className="rk-hero"><div className="rk-container"><p className="rk-eyebrow">AGI / INVESTOR PORTFOLIOS</p><h1>Rich Kids<span>Follow the portfolios.</span></h1><p className="rk-intro">The names, the holdings and the moves. Explore where prominent investors have their capital invested.</p><div className="rk-hero-meta"><span>INDIA & USA</span><span>HOLDINGS · SECTORS · REPORTED CHANGES</span></div></div></header>
  <div className="rk-container">
   <div className="rk-tabs" role="tablist" aria-label="Investor market" onKeyDown={keyboardTab}>{[['IN','India'],['US','USA']].map(([code,label])=><button id={`rk-tab-${code}`} key={code} role="tab" aria-selected={country===code} aria-controls="rk-panel" tabIndex={country===code?0:-1} onClick={()=>choose(code)}>{label}<span>{code==='IN'?indiaInvestors.length:'Coming soon'}</span></button>)}</div>
   <section id="rk-panel" role="tabpanel" aria-labelledby={`rk-tab-${country}`} tabIndex={0}>
    <div className="rk-section-title"><div><p className="rk-eyebrow">{country==='IN'?'INDIA / INR CRORE':'USA / USD'}</p><h2>{country==='IN'?'Inside the portfolios.':'The USA investor watch.'}</h2></div><span className="rk-snapshot">{country==='IN'?'Supplied snapshot · valuation date not provided':'Coverage pending'}</span></div>
    {investors.length ? <>
     <div className="rk-toolbar"><label>Find an investor, holding or sector<input type="search" placeholder="Try Rekha, Titan or Healthcare" value={query} onChange={e=>setQuery(e.target.value)} /></label><label>Sort by<select value={sort} onChange={e=>setSort(e.target.value)}><option value="value">Portfolio value: highest first</option><option value="stocks">Number of stocks: highest first</option><option value="name">Investor name: A–Z</option></select></label><p aria-live="polite">{rows.length} of {investors.length} investors</p></div>
     <p className="rk-table-hint">Scroll across to explore all columns. Names and holdings link to their supplied sources.</p>
     <div className="rk-table-wrap" role="region" aria-label="Investor portfolio comparison" tabIndex={0}><table><caption className="rk-sr-only">Indian investor portfolios from the supplied snapshot. Currency: INR crore.</caption><thead><tr>{['Superstar','Portfolio Value* (change)','# of Stocks','Sector Preference','Quarterly Net Worth','Top Holdings','Recently bought','Recently sold'].map(label=><th key={label} scope="col">{label}</th>)}</tr></thead><tbody>{rows.map(row=><tr key={row.name}>
      <th scope="row"><a href={row.url} target="_blank" rel="noopener noreferrer">{row.name}<span className="rk-external" aria-hidden="true"> ↗</span></a></th>
      <td className="rk-number"><strong>₹{row.value.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})} Cr</strong><span className={row.change>=0?'rk-positive':'rk-negative'}>{row.change>0?'+':''}{row.change}%</span></td><td className="rk-count">{row.stocks}</td><td><Entries items={row.sectors}/></td><td><span className="rk-muted">Not supplied</span></td><td><Entries items={row.holdings}/></td><td><Entries items={row.bought} tone="rk-positive"/></td><td><Entries items={row.sold} tone="rk-negative"/></td>
     </tr>)}</tbody></table>{!rows.length&&<div className="rk-no-results"><h3>No matching investors</h3><p>Try a different name, sector or holding.</p><button onClick={()=>setQuery('')}>Clear search</button></div>}</div>
     <aside className="rk-notes"><h3>How to read this table</h3><p>* Portfolio value reflects the supplied listed-shareholding figures, not personal net worth. Change periods and valuation dates were not supplied. “Recently bought” and “Recently sold” retain the source labels and percentages; these are not verified trade executions or investment returns.</p><p>Quarterly net-worth history was not supplied. A dash means no entry was provided, not necessarily no activity. Figures are reproduced from the supplied snapshot and may not reconcile across columns. Family and associate portfolios can overlap; their values should not be added together.</p><p>Source: supplied Trendlyne table. Open an investor or holding link for its source page. This page is not a live price feed.</p></aside>
    </> : <div className="rk-empty"><span className="rk-empty-mark" aria-hidden="true">US</span><h3>USA portfolios are coming next.</h3><p>Investor entries have not been published for this market yet. Once available, they will appear here with holdings, sector preferences and reported changes.</p><button onClick={()=>choose('IN')}>Explore India portfolios <span aria-hidden="true">→</span></button></div>}
   </section>
  </div>
 </main>;
}
