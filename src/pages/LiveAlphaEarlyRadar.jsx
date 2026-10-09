import { useEffect, useState } from 'react';
import API_ORIGIN from '@/config';
const price = n => Number.isFinite(n) ? n.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '—';
const time = v => v ? new Date(v).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false }) : '—';
const labels = { watch: 'Early watch', triggered: 'Triggered', confirmed: 'Follow-through', failed: 'Failed', extended: 'Extended', expired: 'Expired' };
export default function LiveAlphaEarlyRadar() {
  const [data, setData] = useState(null), [error, setError] = useState(''), [filter, setFilter] = useState('all');
  useEffect(() => {
    let cancelled = false, busy = false;
    const load = async () => {
      if (busy || document.hidden) return;
      busy = true;
      try {
        const response = await fetch(`${API_ORIGIN}/api/market/live-alpha/early-radar`);
        if (!response.ok) throw new Error('Setup radar unavailable');
        const body = await response.json(); if (!cancelled) { setData(body); setError(''); }
      } catch (e) { if (!cancelled) setError(e.message); } finally { busy = false; }
    };
    load(); const timer = setInterval(load, 15000); document.addEventListener('visibilitychange', load);
    return () => { cancelled = true; clearInterval(timer); document.removeEventListener('visibilitychange', load); };
  }, []);
  const historical = data && (!data.market_open || data.stale || error);
  const rows = (data?.rows || []).filter(r => filter === 'all' || r.stage === filter).sort((a,b) => Date.parse(b.updated_at)-Date.parse(a.updated_at));
  return <section className="la-panel la-radar"><div className="la-section-head"><span className="la-eyebrow">DEVELOPING SETUPS · EXPERIMENTAL</span><h2>Watch the setup. Track the trigger.</h2><p>Early watch identifies a developing setup. Triggered means a frozen price level was crossed. Follow-through and failure remain visible, with the original trigger price.</p><p>{historical ? 'Historical / unavailable — not current alerts.' : data ? 'Evaluates every 30 seconds from the existing stream; screen checks every 15 seconds.' : 'Loading setup radar…'} Last evaluation: {time(data?.evaluated_at)} IST.</p></div>
    {error && <p className="la-error">{error}</p>}{data?.storage_error && <p className="la-error">{data.storage_error}</p>}
    <div className="la-radar-steps"><div><strong>01 · Early watch</strong><p>Near a 15-minute range boundary, with participation and relative strength.</p></div><div><strong>02 · Triggered</strong><p>Level crossed; first trigger price and time are frozen.</p></div><div><strong>03 · Review outcome</strong><p>Follow-through, failed breakout or expiry. Extended moves are flagged.</p></div></div>
    <div className="la-toolbar"><label>Stage <select value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All stages</option>{Object.entries(labels).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><span>{data?.coverage?.eligible ?? 0} setup-ready this scan · {data?.coverage?.checked ?? 0} checked</span></div>
    <div className="la-table-wrap"><table><thead><tr>{['Stock / direction','Stage','Frozen level ₹','First trigger ₹ / time','Latest sampled price ₹','Since trigger %','Why'].map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{rows.map(r=><tr key={r.symbol}><td><strong>{r.symbol}</strong><small>{r.direction}</small></td><td><span className={`la-tag la-tag--${r.stage==='failed'?'negative':r.stage==='confirmed'?'positive':'muted'}`}>{labels[r.stage]}</span>{(historical||r.quote_stale)&&<small>Historical / stale</small>}</td><td>{price(r.level)}</td><td>{price(r.trigger_price)}{r.trigger_at && <small>{time(r.trigger_at)} IST</small>}<small>First seen {time(r.started_at)} IST</small></td><td>{price(r.current_price)}<small>{time(r.quote_at)} IST</small></td><td>{price(r.return_pct)}<small>Directional · before costs</small></td><td>{r.reason}</td></tr>)}{!rows.length&&<tr><td colSpan={7}>No recorded setups in this stage. Missing inputs do not count as a neutral signal.</td></tr>}</tbody></table></div>
    <details className="la-health"><summary>Recent stage history ({data?.events?.length || 0})</summary><div className="la-table-wrap"><table><thead><tr><th>Time IST</th><th>Stock</th><th>Stage</th><th>Price ₹</th><th>Reason</th></tr></thead><tbody>{(data?.events || []).map((e,i)=><tr key={`${e.symbol}-${e.event_at}-${i}`}><td>{time(e.event_at)}</td><td>{e.symbol}</td><td>{labels[e.stage]}</td><td>{price(e.current_price)}</td><td>{e.reason}</td></tr>)}</tbody></table></div></details>
    <details className="la-health"><summary>Readiness, rules and evidence</summary><p>{data?.note} Levels use prior minute samples, not full candle highs/lows. A setup can trigger without an earlier watch; it is not backdated. No target prices or broker orders.</p><p>{data?.retention_note} Storage: {data?.checkpoint_storage || 'unknown'}.</p>{Object.entries(data?.coverage?.blocked||{}).map(([k,v])=><p key={k}>{k}: {v} stocks</p>)}<p>Watch: within 0.2% of level, volume pace ≥1.2× prior pace, relative move ≥0.1 percentage points. Trigger: ≥0.08% beyond level, pace ≥1.5×, relative move ≥0.2 points. Beyond 0.6% is extended. Failed: 0.15% back through level. Watch expires after 10 minutes; triggered observation ends after one hour. Thresholds are experimental and unvalidated.</p></details>
  </section>;
}
