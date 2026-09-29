const when=value=>value?new Date(value).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'}):'Not yet available';
export default function NiftyNewsMonitor({news,names}){
 const stale=!news?.last_success_at||Date.now()-new Date(news.last_success_at).getTime()>180000;
 const unavailable=stale||news?.status==='unavailable';
 return <section className="np-method" aria-label="Shared news monitor">
  <p className="np-eyebrow">NEWS MONITOR · OBSERVATION ONLY</p>
  <h2>{unavailable?'News unavailable — coverage unknown':news.would_pause?'Potential news risk — would pause new entries':'No recent headline rule matches'}</h2>
  <p>This monitor records what a news filter would flag across all eleven strategies. It does not change entries, exits or the scheduled-event calendar. Matches are keyword-based research labels, not verified impact assessments.</p>
  <p>Last successful refresh: {when(news?.last_success_at)} IST · Refresh: every minute during market hours · {news?.instrument_count??0} stocks</p>
  <small>{news?.universe||'Waiting for constituent coverage'} · News source: Upstox · Rules: {news?.rule_version||'Pending'}</small>
  {news?.error&&<p className="np-warning">{news.error}</p>}
  {!unavailable&&news?.would_pause&&<p className="np-warning">Suggested pause until {when(news.until)} IST. Paper trading continues under its existing rules.</p>}
  <details><summary>Latest headlines ({news?.articles?.length??0} shown)</summary>
   {unavailable&&<p>Any headlines below are retained evidence, not confirmation of current coverage.</p>}
   {!news?.articles?.length?<p>No articles received yet. This does not establish that there is no market risk.</p>:<div className="np-scroll"><table><thead><tr><th>Headline / affected stocks</th><th>Published / first received (IST)</th><th>Research label</th></tr></thead><tbody>{news.articles.map(a=><tr key={a.id}><td><a href={a.url} target="_blank" rel="noreferrer">{a.heading}</a><small>{a.symbols.join(', ')}</small></td><td>{when(a.published_at)}<small>Received {when(a.first_seen_at)}</small></td><td>{a.reasons.join(', ')||'No rule match'}{a.pause_until&&<small>Window ends {when(a.pause_until)}</small>}</td></tr>)}</tbody></table></div>}
  </details>
  <details><summary>News assessments and entry observations ({news?.observations?.length??0} recent)</summary>
   <p>Entries are logged with the news available at that moment. “Would pause” is a proposed filter, not a blocked trade or an alternative backtest. Records are retained for 30 days; the latest 30 are shown.</p>
   {!news?.observations?.length?<p>Waiting for new strategy candidates or paper entries after the monitor starts.</p>:<div className="np-scroll"><table><thead><tr><th>Time (IST)</th><th>Strategy / event</th><th>News assessment</th></tr></thead><tbody>{news.observations.map((o,i)=><tr key={i}><td>{when(o.at)}</td><td>{o.agent==='all'?'All strategies':names[o.agent]||o.agent}<small>{o.kind==='paper_entry'?'Paper entry':o.kind==='news_review'?'News assessment':'Candidate'}</small></td><td>{o.would_pause===null?'Unknown — news unavailable':o.would_pause?'Would pause':'No matching pause rule'}{o.headlines?.map(a=><small key={a.id}>{a.heading}</small>)}</td></tr>)}</tbody></table></div>}
  </details>
  <small>A proposed pause lasts 30 minutes from publication, never from delayed discovery. Headlines older than that cannot start a fresh pause. No historical news has been injected into past backtests.</small>
 </section>;
}
