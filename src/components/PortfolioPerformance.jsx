import { useEffect, useMemo, useState } from 'react';
import { HORIZONS, holdingReturn, portfolioReturn } from '@/lib/portfolioHistory';
const format = value => `${value>=0?'+':''}${value.toFixed(2)}%`;
const label = m => m===12?'1 year':`${m} month${m===1?'':'s'}`;
export default function PortfolioPerformance({portfolio}) {
  const [data,setData]=useState(null),[error,setError]=useState(''),[period,setPeriod]=useState(12);
  useEffect(()=>{const c=new AbortController();fetch('/data/portfolio-history.json',{signal:c.signal,cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('History snapshot is unavailable');return r.json();}).then(d=>{if(d.schemaVersion!==1)throw Error('Unsupported history snapshot');setData(d);}).catch(e=>{if(e.name!=='AbortError')setError(e.message);});return()=>c.abort();},[]);
  const results=useMemo(()=>data?HORIZONS.map(m=>portfolioReturn(data,portfolio,m)):[],[data,portfolio]);
  if(portfolio.market!=='usa')return null;
  if(error)return <section className="pf-performance"><h3>Historical simulation</h3><p role="alert">{error}. No return is estimated.</p></section>;
  if(!data)return <section className="pf-performance" aria-busy="true"><p>Loading historical prices…</p></section>;
  const active=results.find(r=>r.months===period);
  const stale=Date.now()-Date.parse(`${data.asOf}T00:00:00Z`)>7*86400000;
  return <section className="pf-performance" aria-labelledby="pf-performance-title">
    <span className="pf-eyebrow">YAHOO FINANCE · DAILY ADJUSTED CLOSE · USD</span>
    <h2 id="pf-performance-title">What if you had invested earlier?</h2>
    <p>These backtested returns show what would have happened if you had invested in the current stocks, at their current weights, 1, 3, 6 or 12 months ago and held them without rebalancing. <strong>Changing the allocation recalculates these historical comparisons.</strong> They are separate from performance since launch.</p>
    <p className="pf-footnote">Prices through {data.asOf} · allocation dated {portfolio.asOf} · generated {data.generatedAt.slice(0,10)}. Dividend/split adjustments are supplied by Yahoo; no trading fees, investor taxes, management fees or INR currency conversion. Snapshot refresh is manual.</p>
    {stale&&<p className="pf-warning">This price snapshot is more than seven days old. Results end on {data.asOf}, not today.</p>}
    <div className="pf-return-grid">{results.map(r=><button key={r.months} aria-pressed={period===r.months} className={`pf-return-card ${period===r.months?'active':''}`} onClick={()=>setPeriod(r.months)}><span>{label(r.months)}</span><strong>{r.reason?(r.isNew?'New':'Unavailable'):format(r.returnPct)}</strong><small>{r.start||'—'} → {r.end||'—'}</small><small>{r.covered.toFixed(2)}% weight has complete history</small></button>)}</div>
    {active.reason?<div className="pf-warning"><strong>{active.isNew?'New listing: more history is needed for this period':active.reason}.</strong><p>Missing securities are not treated as cash and known holdings are not scaled up. Individual returns below remain available where supported.</p></div>:<>
      <div className="pf-curve-meta"><span>Growth of 100: <strong>{(active.curve.at(-1).value*100).toFixed(2)}</strong></span><span>Maximum daily drawdown: <strong>{active.maxDrawdownPct.toFixed(2)}%</strong></span></div>
      <PerformanceCurve points={active.curve}/>
      {active.roundingNormalised&&<p className="pf-footnote">Disclosed weights sum to {active.total.toFixed(2)}%. This rounding difference (≤0.05 percentage points) is normalised to 100% for the simulation.</p>}
    </>}
    <details className="pf-price-details"><summary>Stock-by-stock returns and data coverage ({portfolio.holdings.length} holdings)</summary><div className="pf-price-table"><table><thead><tr><th>Holding / matched ticker</th><th>Weight</th>{HORIZONS.map(m=><th key={m}>{label(m)}</th>)}</tr></thead><tbody>{portfolio.holdings.map((h,i)=>{
      const cells=HORIZONS.map(m=>holdingReturn(data,h,m));const symbol=cells[0].symbol;
      return <tr key={`${h.name}-${i}`}><td><strong>{h.name}</strong><br/>{symbol?<a href={`https://finance.yahoo.com/quote/${encodeURIComponent(symbol)}/history/`} target="_blank" rel="noreferrer">{symbol} · Yahoo ↗</a>:<small>Mapping needs review</small>}</td><td>{h.weight.toFixed(2)}%</td>{cells.map((c,j)=><td key={j}>{c.reason?<small title={c.reason}>{c.isNew?'New':'—'}<br/>{c.reason}</small>:<span>{format(c.returnPct)}</span>}</td>)}</tr>;
    })}</tbody></table></div></details>
    <details><summary>Calculation method and limitations</summary><p>This is a hypothetical backtest, not actual investor returns. Selecting current holdings with knowledge of the past introduces hindsight and survivorship bias.</p><p>Return = sum of initial weight × (ending adjusted close / starting adjusted close − 1). We use the last US trading day on or before the calendar-month boundary, with the same dates for every holding. The chart applies those initial weights to each daily price ratio. Dividends are represented through Yahoo’s adjusted-price series; no separate cash dividend is added.</p><p>Full-period history is required for every positive-weight holding. IPOs, missing sessions, ambiguous share classes, non-USD series and incomplete allocations withhold the portfolio result. Candidate research names are excluded until assigned weights. Adjusted prices and corporate actions have not been independently reconciled. Daily-close drawdown can miss intraday losses. A historical simulation of current holdings does not show the return an investor actually earned.</p><a href="https://in.help.yahoo.com/kb/adjusted-close-sln28256.html" target="_blank" rel="noreferrer">Yahoo’s adjusted-close methodology ↗</a></details>
    <p><a href="/research/portfolio-performance.html" target="_blank" rel="noreferrer">Compare all 26 portfolio simulations ↗</a></p>
    <p><a href="/data/portfolio-history.json" download="AGI-portfolio-daily-history.json">Download all captured daily prices and mapping evidence (JSON)</a></p>
  </section>;
}
function PerformanceCurve({points}) {
  const values=points.map(p=>p.value*100),low=Math.min(100,...values),high=Math.max(100,...values),range=high-low||1;
  const path=values.map((v,i)=>`${i?'L':'M'} ${(20+i/(values.length-1||1)*760).toFixed(2)} ${(180-(v-low)/range*155).toFixed(2)}`).join(' ');
  return <figure className="pf-performance-chart"><svg viewBox="0 0 800 210" role="img" aria-label={`Simulated growth of 100 from ${points[0].date} to ${points.at(-1).date}; final ${(points.at(-1).value*100).toFixed(2)}`}><title>Current-allocation historical simulation</title><line x1="20" x2="780" y1={180-(100-low)/range*155} y2={180-(100-low)/range*155} stroke="#b3c4c8" strokeDasharray="4 4"/><path d={path} fill="none" stroke="#176b61" strokeWidth="3"/><text x="20" y="16">{high.toFixed(1)}</text><text x="20" y="201">{points[0].date}</text><text x="780" y="201" textAnchor="end">{points.at(-1).date}</text></svg><figcaption>Daily value, starting at 100. Range {low.toFixed(2)}–{high.toFixed(2)}.</figcaption></figure>;
}
