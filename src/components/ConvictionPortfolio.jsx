import CompanyLogo from './CompanyLogo';
import {useState} from 'react';
import {Link} from 'react-router-dom';
import {PriceChart,pointsFor,useIndiaTracking} from './IndiaPortfolios';
import './ConvictionPortfolio.css';
const pct=n=>n==null?'—':`${n>=0?'+':''}${n.toFixed(2)}%`;
const money=n=>n==null?'—':n.toLocaleString('en-IN',{style:'currency',currency:'INR'});
const status={scheduled:'Scheduled for Monday, 5 October 2026',awaiting_fresh_prices:'Waiting for a complete set of fresh launch quotes',start_missed:'Launch was not recorded. Administrator review required.',awaiting_daily:'Launch recorded. Waiting for daily closes.',daily_recorded:'Daily prices recorded',daily_pending:'Latest daily prices pending'};
export default function ConvictionPortfolio({portfolio:p}) {
 const {data,error}=useIndiaTracking(),[selected,setSelected]=useState('Total');
 const t=data?.portfolios.find(x=>x.id===p.id),short=p.direction==='short';
 const categories=t?.categories||p.categories,category=categories.find(c=>c.name===selected);
 const positions=t?.positions||p.holdings;
 const holdings=category?category.holdings.map(h=>({...positions.find(x=>x.symbol===h.symbol),...h})):positions;
 const chart=category?{startedAt:t?.startedAt,history:category.history}:t;
 return <section className="india-portfolios conviction">
  <Link to="/portfolios/india">← India portfolios</Link>
  <div className="pf-heading"><div><span className="pf-eyebrow">SIX FACTOR CATEGORIES · {short?'SHORT RESEARCH':'LONG RESEARCH'}</span><h2>{p.name}</h2><p>{p.description}</p></div><Link className="pf-button" to={`/portfolios/india/in-conviction-${short?'long':'short'}`}>View Conviction {short?'Long':'Short'} →</Link></div>
  <div className="pf-evidence-strip"><div><strong>{status[t?.status]||'Loading tracking status…'}</strong><span>Upstox daily prices · updates after 4 pm IST on trading days · {p.holdings.length} unique stocks</span><span>Actual launch: {t?.startedAt?new Date(t.startedAt).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})+' IST':'Not recorded yet'} · Last complete portfolio date: {t?.priceDate||'—'}</span></div></div>
  {error&&<p className="pf-warning" role="alert">{error}</p>}
  {short&&<p className="pf-warning"><strong>Theoretical short research.</strong> Measures the opposite of the fixed-weight stocks’ price movement against initial notional. Excludes borrowing costs, fees, dividends owed, margin and execution. No short trades are placed. Losses can exceed 100%; this is not a tradable fund return.</p>}
  <div className="india-metrics"><div><span>Total Conviction {short?'Short · theoretical':'Long'} return</span><strong>{pct(t?.returnPct)}</strong></div><div><span>{short?'Research index · can fall below zero':'Portfolio index · launch = 100'}</span><strong>{t?.nav==null?'—':t.nav.toFixed(2)}</strong></div><div><span>Category positions / unique stocks</span><strong>{p.categories.reduce((n,c)=>n+c.holdings.length,0)} / {p.holdings.length}</strong></div></div>
  <h3>Returns by category</h3><p>Each category receives exactly one-sixth of initial capital. Displayed weights are rounded; calculations use full precision.</p>
  <div className="conviction-categories">{categories.map(c=><button type="button" className={selected===c.name?'selected':''} onClick={()=>setSelected(c.name)} key={c.name} aria-pressed={selected===c.name}><strong>{c.name==='Low Vol'?'Low Volatility':c.name}</strong><span>{c.holdings.length} stocks · {c.weight.toFixed(2)}% allocation</span><b>{pct(c.returnPct)}</b><small>{c.priceDate?`Prices: ${c.priceDate}`:'Awaiting recorded prices'}</small></button>)}</div>
  <button type="button" className="pf-button" onClick={()=>setSelected('Total')} aria-pressed={selected==='Total'}>Show total Conviction</button>
  <PriceChart key={selected} title={`${selected==='Total'?'Total Conviction':selected}${short?' · theoretical short index':''}`} points={pointsFor(chart)}/>
  <h3>{selected==='Total'?'Combined holdings and factor overlap':`${selected} holdings and returns`}</h3>
  <p>{category?`Source definition: ${category.definition}. Weights below are within this category.`:'Common stocks stay in every category. Their category allocations are added below, and the total initial exposure sums to 100%.'}</p>
  <div className="pf-holdings" style={{overflowX:'auto'}}><table><thead><tr><th>Stock / NSE symbol</th><th>{category?'Source z-score':'Factor categories'}</th><th>{category?'Within category':'Combined weight'}</th><th>Launch price</th><th>Latest close</th><th>{short?'Theoretical short return':'Stock price return'}</th><th>Price date</th></tr></thead><tbody>{holdings.map(h=><tr key={h.symbol}><td><CompanyLogo symbol={h.symbol} name={h.name}/><strong>{h.name}</strong><br/>{h.symbol}</td><td>{category?h.score.toFixed(2):(h.factors||[]).join(', ')}</td><td>{h.weight.toFixed(3)}%</td><td>{money(h.basePrice)}</td><td>{money(h.price)}</td><td>{pct(h.strategyReturnPct)}</td><td>{h.priceDate||'—'}</td></tr>)}</tbody></table></div>
  <details className="india-method"><summary>Allocation, source and return methodology</summary><p>{p.weightMethod}</p><p>All categories share the portfolio launch timestamp. Each category return is the weighted sum of its constituent price returns. Total return is the sum of category returns multiplied by their initial allocations. Category values can appear when their prices are complete; the total requires all stocks. Do not combine category figures dated differently.</p><p>{short?'Short return = sum(weight × (1 − current price / launch price)). Initial gross short notional is 100%; sale proceeds are not reinvested. The displayed research index is 100 plus this percentage return.':'Long return = sum(weight × (current price / launch price − 1)). Fixed fractional units; no periodic rebalance.'} No fees, taxes or dividend adjustments. Corporate actions require review.</p><p>Source: {p.sourceName}. Cover date 1 September 2026; filename date 24 September 2026. Exact source observation date remains unconfirmed. These classifications are historical, not newly recomputed recommendations. The long and short portfolios deliberately preserve cross-factor conflicts. No orders are submitted.</p></details>
 </section>;
}
