const money=n=>n==null?'—':Number(n).toLocaleString('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2});
const labels={observed:'Recorded replay',unresolved:'Incomplete · open/unresolved',insufficient_data:'Not testable'};
export function parseReplayCalendar(text){
 const days={};
 for(const line of text.trim().split('\n').filter(Boolean)){
  const match=line.trim().match(/^(\d{4}-\d{2}-\d{2})\s+(CLEAR|\d{2}:\d{2}-\d{2}:\d{2})$/);
  if(!match)throw new Error('Use YYYY-MM-DD CLEAR or YYYY-MM-DD HH:MM-HH:MM, one per line.');
  const [,date,value]=match;
  if(days[date]?.clear || (days[date]&&value==='CLEAR'))throw new Error('Do not combine CLEAR with another entry for the same day.');
  const item=days[date]??{date,reviewed:true,windows:[],clear:false};
  if(value==='CLEAR')item.clear=true;
  else {const [a,b]=value.split('-');item.windows.push({start:`${date}T${a}:00+05:30`,end:`${date}T${b}:00+05:30`});}
  days[date]=item;
 }
 return Object.values(days).map(({clear,...item})=>item);
}
export function ReplayCalendar({text,setText,reviewed,setReviewed}){
 return <details className="np-method"><summary>Historical event calendar · optional research inputs</summary><p>Saved calendar reviews are used only from the time they were recorded. For older dates, supply reviews below. Missing dates remain unreviewed and block the seven research strategies. These inputs affect this replay only; they do not change the live calendar.</p><p>Use one line per date or blackout window, in IST. CLEAR means you checked that date and selected no blackout. Retrospective reviews are labelled in the results and are not point-in-time evidence.</p><label>Dated historical reviews<textarea aria-label="Historical event reviews" rows={4} value={text} onChange={e=>{setText(e.target.value);setReviewed(false);}} placeholder={'2026-09-25 CLEAR\n2026-09-28 09:15-10:00'}/></label><label><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/> I checked scheduled events for every date entered.</label></details>;
}
export default function NiftyReplayReport({result,job,names}){
 const running=['queued','running'].includes(job?.status);
 const c=result?.coverage;
 const rows=Object.entries(result?.agents||{});
 function download(){
  const headers=['Strategy','Evidence','Sampling seconds','Closed trades','Net P&L INR','Marked equity or contribution INR','Drawdown INR','Win rate %','Profit factor','Charges INR','Status'];
  const cell=value=>`"${String(value??'').replace(/"/g,'""')}"`;
  const csv=[headers,...rows.map(([k,a])=>[names[k]||k,a.evidence_status,a.replay_interval_seconds,a.closed_trades,a.net_pnl,a.equity,a.max_drawdown,a.win_rate,a.profit_factor,a.total_charges,a.status])].map(row=>row.map(cell).join(',')).join('\r\n');
  const url=URL.createObjectURL(new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8;'}));const link=document.createElement('a');link.href=url;link.download=`nifty-replay-${result.start}-${result.end}.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 return <section className="np-method" aria-label="All-strategy backtest results"><h2>All-strategy backtest results</h2>
 {job&&<p role="status">Replay #{job.id}: <strong>{job.status}</strong>{running?` · ${job.progress?.phase||'Starting worker'}${job.progress?.processed_frames?` · ${job.progress.processed_frames.toLocaleString()} frames processed`:''}`:''}{job.error?` · ${job.error}`:''}</p>}
 {running&&<p>The previous completed result stays visible while this run works. You can leave this page and return.</p>}
 {!c?<p>Run “Backtest all strategies” to compare all eleven agents and inspect data coverage. Older saved replays cover only the two legacy agents.</p>:<><p><strong>{result.start} to {result.end}</strong> · Completed {new Date(result.completed_at).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})} IST. Each original benchmark has its own ₹1 lakh; the seven research strategies share one separate ₹1 lakh. Different data intervals and cost models limit direct comparisons.</p>
 <div className="np-metrics"><div>15-minute archive<strong>{c.legacy_days} days</strong><small>{c.legacy_observations.toLocaleString()} observations · {c.legacy_quote_rows.toLocaleString()} option quotes</small></div><div>One-second archive<strong>{c.frames.toLocaleString()} frames</strong><small>{c.days.length} observed days · {c.warmup_frames.toLocaleString()} prior warm-up frames</small></div><div>Completed five-minute bars<strong>{c.complete_bars}</strong><small>{c.gaps_over_5s} intraday gaps over five seconds</small></div><div>Prior daily IV history<strong>{c.max_prior_iv_days} / 20 minimum</strong></div><div>Reviewed event dates observed<strong>{c.reviewed_days.length}</strong><small>{c.calendar_mode==='retrospective_admin_inputs'?'Includes retrospective admin inputs':'Recorded reviews, as known at the time'}</small></div><div>Fresh futures observations<strong>{c.futures_frames.toLocaleString()}</strong></div></div>
 {!c.frames&&<p className="np-warning">No one-second history exists in this range. The nine newer agents cannot be measured from the older 15-minute snapshots. Dashes mean not tested, not zero profit.</p>}
 <button onClick={download}>Download comparison CSV</button><div className="np-scroll"><table><thead><tr><th>Strategy / evidence</th><th>Sampling</th><th>Closed trades</th><th>Closed net P&amp;L</th><th>Drawdown</th><th>Win rate</th><th>Profit factor</th><th>Closed-trade charges</th></tr></thead><tbody>{rows.map(([key,a])=><tr key={key}><th>{names[key]||key}<small>{labels[a.evidence_status]||'Legacy replay'} · {a.status}</small></th><td>{a.replay_interval_seconds===1?'1 second':'15 minutes'}</td><td>{a.closed_trades??'—'}</td><td>{money(a.net_pnl)}</td><td>{money(a.max_drawdown)}</td><td>{a.win_rate==null?'—':`${a.win_rate}%`}</td><td>{a.profit_factor??'—'}</td><td>{money(a.total_charges)}</td></tr>)}</tbody></table></div>
 <details><summary>Replay assumptions and missing evidence</summary>{result.assumptions.map((x,i)=><p key={i}>{x}</p>)}<p>Without a complete exit, a last-known mark is not a realised return. Full trade journals appear below; at most the last 100 closed trades per strategy are displayed, while summary statistics include every closed trade.</p><p>Raw one-second frames are retained for fourteen days. Older 15-minute snapshots are not expanded into synthetic seconds. Historical OHLC candles do not supply the original bid/ask depth, option deltas and basket timing.</p></details></>}
 </section>;
}
