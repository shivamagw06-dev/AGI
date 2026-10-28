import { useEffect, useState } from 'react';
import { libraryRequest, screenerDate, recordedTime } from '@/lib/screenerLibraryApi';
import './screenerIntelligence.css';

export default function ScreenerIntelligence({ slug, snapshotId, historical=false }) {
  const [data,setData]=useState(null),[error,setError]=useState(''),[retry,setRetry]=useState(0);
  useEffect(()=>{
    let active=true,running=false;
    setData(null);setError('');
    const refresh=async()=>{
      if(running||document.hidden)return;
      running=true;
      try {
        const params=new URLSearchParams();if(snapshotId)params.set('snapshot',String(snapshotId));if(historical)params.set('historical','1');
        const next=await libraryRequest(`/${encodeURIComponent(slug)}/intelligence?${params}`);
        if(active){setData(next);setError('');}
      } catch(e){if(active)setError(e.message);} finally{running=false;}
    };
    refresh();const timer=setInterval(refresh,300000);document.addEventListener('visibilitychange',refresh);
    return()=>{active=false;clearInterval(timer);document.removeEventListener('visibilitychange',refresh);};
  },[slug,snapshotId,historical,retry]);
  return <section className="sci" aria-label="Screener intelligence">
    <header className="sci-header"><div><p className="sci-kicker">AGI / RESEARCH INTELLIGENCE</p><h2>Screener intelligence<span>.</span></h2><p>{data?.purpose||'Reading the published evidence…'}</p></div><span className={`sci-badge ${data?.ageDays>7?'sci-badge-old':''}`}>{data?historical?'Saved snapshot':data.ageDays>7?'Older snapshot':'Dated snapshot':'Updating'}</span></header>
    {error&&<p className="sci-error" role="alert">Intelligence could not be refreshed: {error}{data?' The last successful summary remains below.':''}<button type="button" onClick={()=>{setRetry(v=>v+1);}}>Retry</button></p>}
    {!data&&!error&&<p className="sci-loading" role="status">Calculating observations from the saved table…</p>}
    {data?.available===false&&<p>{data.reason}</p>}
    {data?.available&&<>
      <div className="sci-grid">
        {data.cards.slice(0,2).map(card=><article className="sci-card" key={card.label}><p className="sci-label">{card.label}</p><strong className="sci-value">{card.value}</strong><p>{card.detail}</p></article>)}
        <article className="sci-card sci-card-context"><p className="sci-label">Cross-screen context</p>{data.overlaps.length?<ul>{data.overlaps.map(item=><li key={item.slug}><span>{item.name}</span><b>{item.identified?`${item.identified} code/ISIN matches`:''}{item.identified&&item.provisional?' · ':''}{item.provisional?`${item.provisional} provisional name matches`:''}</b>{item.period&&<small>Ownership period: {screenerDate(item.period)}</small>}</li>)}</ul>:<><strong className="sci-value sci-value-small">{historical?'Saved view':'No comparable matches'}</strong><p>{historical?'Later publications are excluded from this view.':'No matches were established in available tables with the same data date.'}</p></>}</article>
        <article className="sci-card"><p className="sci-label">Data freshness</p><strong className="sci-value">{data.ageDays===0?'Today’s table':`${data.ageDays} days old`}</strong><p>Table date: {screenerDate(data.asOf)}.<br/>Summary checked: {recordedTime(data.generatedAt)}.</p><p className="sci-fine">A new calculation does not refresh source prices, filings or fundamentals.</p></article>
      </div>
      <div className="sci-change"><span className="sci-label">Since previous publication</span>{data.changes.available?<p><b>{data.changes.added} entered</b><span> · </span><b>{data.changes.removed} left</b><span> · compared with {screenerDate(data.changes.previousAsOf)}{data.changes.provisional?' · provisional name-based comparison':''}</span></p>:<p>{data.changes.reason}</p>}</div>
      <div className="sci-reading"><div><h3>How to read this</h3><p>{data.caution}</p></div><div><h3>Evidence checks</h3><ul>{data.evidence.map(text=><li key={text}>{text}</li>)}</ul></div></div>
      <details className="sci-method"><summary>Sources, method and coverage</summary><p>{data.note}</p><p>{data.overlapNote}</p><p>{data.performance}</p><p>All calculations use saved source values. Missing inputs are excluded and the valid-input count is shown. Medians describe this screened sample, not the whole market. No predictive score, target price or trade recommendation is generated.</p><p>Summary checks automatically every five minutes while this page is visible. The latest stock table also checks every five minutes. This summary stays pinned to the table currently shown; saved-history views keep their selected publication.</p><p>Snapshot {data.snapshotId} · recorded {recordedTime(data.recordedAt)}{data.sourceUrl&&<> · <a href={data.sourceUrl} target="_blank" rel="noopener noreferrer">Open table source ↗</a></>}</p></details>
    </>}
  </section>;
}
