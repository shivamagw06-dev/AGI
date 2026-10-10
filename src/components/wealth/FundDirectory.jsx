import { useEffect, useState } from 'react';
import { getWealthUniverse } from '@/lib/wealthIntelligenceApi';
const rupees = value => value == null ? 'Unavailable' : new Intl.NumberFormat('en-IN', {style:'currency',currency:'INR',maximumFractionDigits:4}).format(value);
export default function FundDirectory() {
  const [query,setQuery] = useState(''), [offset,setOffset] = useState(0), [refresh,setRefresh] = useState(0);
  const [data,setData] = useState(null), [loading,setLoading] = useState(true), [error,setError] = useState(''), [selected,setSelected] = useState([]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setData(null);
    const timer = setTimeout(async () => {
      try {
        const result = await getWealthUniverse({assetClass:'mutual_fund',q:query,offset,limit:20},controller.signal);
        if (!controller.signal.aborted) setData(result);
      } catch(e) { if (!controller.signal.aborted) setError(e.message); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    },300);
    return () => { clearTimeout(timer); controller.abort(); };
  },[query,offset,refresh]);
  const choose = row => setSelected(previous => previous.some(f=>f.id===row.id) ? previous.filter(f=>f.id!==row.id) : [...previous,row].slice(-2));
  return <div>
    <div className="wi-section-title"><h3>Fund directory</h3><button className="wi-button" disabled={loading} onClick={()=>setRefresh(v=>v+1)}>Refresh funds</button></div>
    <p className="wi-note">Automatically loaded scheme data. Select two funds to compare published details. NAV is dated and is not an intraday quote.</p>
    <label className="wi-field"><span>Search funds, AMC, category or ISIN</span><input value={query} maxLength={120} onChange={e=>{setQuery(e.target.value);setOffset(0);}} placeholder="Search Upstox mutual funds" /></label>
    {loading && <p role="status">Loading fund directory…</p>}
    {error && <p className="wi-error" role="alert">{error} Use Refresh funds to retry.</p>}
    {data && <>
      <p className="wi-note">{data.source.provider} · {data.total.toLocaleString()} matching schemes · {data.source.status}{data.source.fetchedAt ? ` · fetched ${new Date(data.source.fetchedAt).toLocaleString()}` : ''}{data.source.provider==='AMFI' ? ' · Upstox unavailable; showing AMFI fallback.' : ''}</p>
      {data.source.error && <p className="wi-error">{data.source.error}</p>}
      <div className="wi-table-wrap"><table><thead><tr>{['Fund / ISIN','Category / plan','Published NAV','NAV date / status','Compare'].map(t=><th key={t}>{t}</th>)}</tr></thead><tbody>{data.items.map(f=><tr key={f.id}><td>{f.name}<small>{f.isin || f.schemeCode}</small></td><td>{f.category || 'Unavailable'}<small>{f.plan || 'Plan not supplied'}</small></td><td>{rupees(f.price)}</td><td>{f.asOf || 'Unavailable'}<small>{f.status} · {f.navSource || f.source}</small></td><td><button className="wi-button" aria-pressed={selected.some(s=>s.id===f.id)} onClick={()=>choose(f)}>{selected.some(s=>s.id===f.id) ? 'Remove' : 'Compare'}</button></td></tr>)}</tbody></table></div>
      {!data.items.length && <p className="wi-empty">{data.source.status==='unavailable' ? 'Fund sources are unavailable. Retry shortly.' : 'No matching funds. Try another name or ISIN.'}</p>}
      <div className="wi-actions"><button className="wi-button" disabled={offset===0} onClick={()=>setOffset(v=>Math.max(0,v-20))}>Previous</button><span>{data.total ? offset+1 : 0}–{Math.min(offset+20,data.total)} of {data.total}</span><button className="wi-button" disabled={offset+20>=data.total} onClick={()=>setOffset(v=>v+20)}>Next</button></div>
    </>}
    {!!selected.length && <><h3>Selected fund details</h3><div className="wi-table-wrap"><table><thead><tr><th>Detail</th>{selected.map(f=><th key={f.id}>{f.name}<br/><button className="wi-text-button" onClick={()=>choose(f)}>Remove</button></th>)}</tr></thead><tbody>{[
      ['ISIN', f=>f.isin || 'Unavailable'], ['Category',f=>f.category || 'Unavailable'], ['Plan',f=>f.plan || 'Unavailable'],
      ['Published NAV',f=>rupees(f.price)], ['NAV date',f=>f.asOf || 'Unavailable'], ['NAV status',f=>f.status], ['Minimum investment',f=>rupees(f.minimumInvestment)],
      ['Purchases allowed',f=>f.purchaseAllowed==null ? 'Unavailable' : f.purchaseAllowed ? 'Yes' : 'No'],
      ['Expense ratio',()=>'Unavailable from this source'], ['Underlying portfolio / overlap',()=>'AMC disclosure required'],
      ['Scheme source',f=>f.source], ['NAV source',f=>f.navSource || f.source],
    ].map(([label,value])=><tr key={label}><td>{label}</td>{selected.map(f=><td key={f.id}>{value(f)}</td>)}</tr>)}</tbody></table></div><p className="wi-note">These are snapshots from when you selected each fund. Published NAV levels do not measure comparative performance. Add AMC disclosures below for portfolio overlap.</p></>}
  </div>;
}
