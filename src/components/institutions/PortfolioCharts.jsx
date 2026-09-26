import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { investorPath } from '@/lib/investorProfiles';
import { portfolioChartData } from './chartData';
import './portfolioCharts.css';
const colors = ['#173c58','#337b8b','#c59a50','#7e7195','#92aaa8','#c8d0d6'];
export default function PortfolioCharts({investors, country}) {
 const [direction, setDirection] = useState('gainers');
 const data = useMemo(()=>portfolioChartData(investors),[investors]);
 const movers = [...data.changes].sort((a,b)=>direction==='gainers'?b.change-a.change:a.change-b.change).slice(0,5);
 const max = Math.max(1,...movers.map(x=>Math.abs(x.change)));
 let offset = 0;
 const slices = data.sectors.map((x,i)=>{const start=offset;offset+=x.count/data.sectorCount*100;return `${colors[i]} ${start}% ${offset}%`;});
 return <section className="portfolio-charts" aria-label={`${country==='IN'?'India':'USA'} portfolio charts`}>
  <article className="portfolio-chart"><header><h2>Reported portfolio change</h2><select aria-label="Rank portfolio changes" value={direction} onChange={e=>setDirection(e.target.value)}><option value="gainers">Highest</option><option value="decliners">Lowest</option></select></header><p>Source-reported change · periods may differ</p>
   {movers.length?<ol className="chart-bars">{movers.map(x=><li key={x.name}><div><Link to={investorPath(country,x.name)}>{x.name}</Link><strong className={x.change<0?'is-negative':'is-positive'}>{x.change>0?'+':''}{x.change.toLocaleString('en-US',{maximumFractionDigits:2})}%</strong></div><div className="chart-track"><span className={x.change<0?'is-negative':'is-positive'} style={{width:`${Math.abs(x.change)/max*100}%`}}/></div></li>)}</ol>:<p className="chart-empty">No reported changes available.</p>}
   <footer>Snapshot comparison, not investment returns. Multi-quarter value history has not been supplied.</footer>
  </article>
  <article className="portfolio-chart"><header><h2>Most reported additions</h2><span>Investor count</span></header><p>Stocks appearing in the supplied additions lists</p>
   {data.additions.length?<ol className="chart-bars">{data.additions.map(x=><li key={x.key}><div><span title={x.name}>{x.name}</span><strong>{x.count}</strong></div><div className="chart-track"><span style={{width:`${x.count/data.additions[0].count*100}%`}}/></div></li>)}</ol>:<p className="chart-empty">No additions supplied for this market.</p>}
   <footer>Each investor counts once per stock. Lists may be incomplete; family and associate portfolios may overlap.</footer>
  </article>
  <article className="portfolio-chart"><header><h2>Leading sector preferences</h2><span>{data.sectorCount} portfolios</span></header><p>Largest supplied sector for each investor</p>
   {data.sectorCount?<div className="chart-sector-layout"><div className="chart-donut" role="img" aria-label={data.sectors.map(x=>`${x.name}: ${x.count} portfolios`).join('; ')} style={{background:`conic-gradient(${slices.join(',')})`}}><div><strong>{data.sectorCount}</strong><span>portfolios</span></div></div><ul className="chart-legend">{data.sectors.map((x,i)=><li key={x.name}><i style={{background:colors[i]}}/><span>{x.name}</span><strong title={`${x.count} portfolios`}>{(x.count/data.sectorCount*100).toFixed(1)}%</strong></li>)}</ul></div>:<p className="chart-empty">No sector percentages supplied.</p>}
   <footer>Share of portfolios with a known leading sector, not a combined asset allocation. {investors.length-data.sectorCount} without sector data.</footer>
  </article>
 </section>;
}
