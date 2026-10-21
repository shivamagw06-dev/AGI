import {useState} from 'react';
import {ResponsiveContainer,LineChart,Line,XAxis,YAxis,CartesianGrid,Tooltip} from 'recharts';
const pct=v=>v==null?'—':`${v>=0?'+':''}${v.toFixed(2)}%`;
export default function FactorRetrospective({data}){
 const [selected,setSelected]=useState('');if(!data)return null;
 const stock=data.holdings.find(h=>h.symbol===selected)||data.holdings[0];
 const points=data.history.length?data.history:[];
 return <section className="factor-retrospective" aria-label="Current-holdings backtest from September 15">
 <span className="pf-eyebrow">CURRENT-HOLDINGS BACKTEST · 15 SEPTEMBER 2026</span>
 <h3>What if these 25 stocks had been held since 15 September?</h3>
 <p>The October selection is applied retrospectively: 4% in each stock at the 15 September close, then held without rebalancing. This uses later selection information and does not show what the strategy selected in September. Actual allocation tracking remains separate.</p>
 <div className="factor-stats"><div><span>Price return since 15 September</span><strong>{pct(data.returnPct)}</strong><small>Latest complete basket: {data.priceDate||'Awaiting prices'}</small></div><div><span>Maximum drawdown</span><strong>{data.maxDrawdown==null?'—':data.maxDrawdown.toFixed(2)+'%'}</strong><small>Daily closes, available observations</small></div><div><span>Price coverage</span><strong>{25-data.missingBaseline.length}/25</strong><small>Verified starting prices · {data.status==='complete'?'History complete':'Collection in progress'}</small></div></div>
 {points.length?<ResponsiveContainer width="100%" height={260}><LineChart data={points} accessibilityLayer><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="date" minTickGap={45}/><YAxis domain={['auto','auto']}/><Tooltip formatter={v=>[Number(v).toFixed(2),'Portfolio index']}/><Line dataKey="value" name="Current 25 · starts at 100" stroke="#147c73" dot={false} connectNulls={false} isAnimationActive={false}/></LineChart></ResponsiveContainer>:<p role="status">Collecting verified historical prices. A return will appear only when all 25 starting prices are available.</p>}
 <p><small>Upstox raw daily closing prices in INR; before dividends, trading costs and taxes. Corporate actions require review. Initial weights drift with prices. This backtest does not rewrite published portfolio performance.</small></p>
 {(data.missingBaseline.length>0||data.missingDates.length>0)&&<details><summary>Historical price coverage</summary>{data.missingBaseline.length>0&&<p>Missing 15 September prices: {data.missingBaseline.join(', ')}</p>}<p>Incomplete trading dates: {data.missingDates.join(', ')||'None'}. Missing prices are not estimated and missing stocks are not removed.</p></details>}
 <details><summary>Stock histories from 15 September</summary><label>Historical stock chart<select aria-label="Historical stock chart" value={stock?.symbol||''} onChange={e=>setSelected(e.target.value)}>{data.holdings.map(h=><option key={h.symbol} value={h.symbol}>{h.symbol}</option>)}</select></label><p>Starting close: {stock?.basePrice==null?'Unavailable':'₹'+stock.basePrice.toFixed(2)}</p>{stock?.history.length?<ResponsiveContainer width="100%" height={240}><LineChart data={stock.history} accessibilityLayer><XAxis dataKey="date" minTickGap={45}/><YAxis domain={['auto','auto']}/><Tooltip/><Line dataKey="price" name={stock.symbol} stroke="#bc7a35" dot={false} isAnimationActive={false}/></LineChart></ResponsiveContainer>:<p>Historical prices pending.</p>}</details>
 </section>;
}
