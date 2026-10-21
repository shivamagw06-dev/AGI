import {useEffect,useState} from 'react';
import {getDailyResearch,refreshDailyResearch,importDailyResearch} from '@/lib/optionsLabAdminApi';
const pct=v=>v==null?'—':`${v.toFixed(2)}%`;
export default function NiftyDailyResearch(){
 const [data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[csv,setCsv]=useState('');
 const load=()=>getDailyResearch().then(setData);
 useEffect(()=>{let alive=true;getDailyResearch().then(x=>{if(alive)setData(x);}).catch(e=>{if(alive)setError(e.message);});return()=>{alive=false;};},[]);
 async function run(fn){setBusy(true);setError('');try{await fn();await load();}catch(e){setError(e.message);}finally{setBusy(false);}}
 return <section className="np-agent np-daily" aria-label="NSE daily research"><p className="np-eyebrow">DAILY HISTORY · FOUR DIRECTION STUDIES</p><h2>Nifty across longer horizons</h2>
 <p>Official NSE / NSE Indices daily OHLC. Separate from the eleven intraday agents. These are index-direction studies, not simulated options profits.</p>
 {error&&<p role="alert" className="np-error">{error}</p>}
 {!data?<p>{error?'History could not be loaded.':'Loading daily history…'}</p>:<><p><strong>{data.rows} daily observations</strong> · {data.first||'No history'} to {data.last||'—'} · Warm-up: {data.warmup_required} sessions.</p>
 <p>Daily EMA50: {data.ema50?.toFixed(2)??'Not enough history'} · Daily EMA200: {data.ema200?.toFixed(2)??'Not enough history'} · One full trading session per candle.</p>
 {data.missing_calendar_gaps?.length>0&&<p className="np-error">History contains gaps over seven calendar days. Calculations restart after the latest gap; earlier observations are excluded.</p>}
 <p>Comparison period: {data.test_start||'Waiting for history'} to {data.test_end||'—'} · {data.usable_rows} usable daily observations.</p><div className="np-scroll"><table><thead><tr><th>Strategy</th><th>Next-open signal</th><th>Tested intervals</th><th>Closed trades</th><th>Reference return</th><th>Double-cost return</th><th>Drawdown</th></tr></thead><tbody>{Object.entries(data.strategies).map(([k,s])=><tr key={k}><th>{s.name}<small>{s.rule}</small></th><td>{data.usable_rows<400?'Warming up':({1:'Long',0:'Flat','-1':'Short'})[s.latest_signal]}</td><td>{s.observations}</td><td>{s.closed_trades}</td><td>{pct(s.reference_return_pct)}</td><td>{pct(s.double_cost_return_pct)}</td><td>{pct(s.max_drawdown_pct)}</td></tr>)}</tbody></table></div>
 <p>Matched-period long index benchmark before costs: {pct(data.benchmark_return_pct)}. Open exposure remains marked at the last observed open. Signals shown are from the last available close; stale history is not a current trade instruction.</p><p>{data.method}</p></>}
 <button disabled={busy} onClick={()=>run(async()=>{})}>Reload results</button> <button disabled={busy} onClick={()=>run(refreshDailyResearch)}>{busy?'Working…':'Fetch previous day’s NSE report'}</button> <a href="https://www.niftyindices.com/reports/historical-data" target="_blank" rel="noreferrer">Official history download ↗</a>
 <details><summary>Import official Nifty 50 CSV</summary><p>Paste the official export including Date, Open, High, Low and Close. Existing conflicting dates are rejected. Automatic website polling is disabled; use official exports or an authorised feed.</p><textarea aria-label="Official daily history CSV" rows={5} value={csv} onChange={e=>setCsv(e.target.value)}/><button disabled={busy||!csv.trim()} onClick={()=>run(()=>importDailyResearch(csv))}>Import daily history</button></details>
 </section>;
}
