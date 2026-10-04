import { useEffect, useMemo, useState } from 'react';
import API_ORIGIN from '@/config';
import { buildCanonicalSignals, interpretCanonicalSignal, LIVE_ALPHA_STRATEGIES } from '@/lib/liveAlphaSignalModel';
import { ENGINE_PLAIN, filterRadarRows, plainSignalDirection } from '@/lib/liveAlphaDashboardModel';
import './liveAlphaPage.css';
import LiveAlphaHistory from './LiveAlphaHistory';

const REFRESH_MS = 60_000;
const date = value => value && Number.isFinite(Date.parse(value)) ? `${new Date(value).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })} IST` : 'Not recorded';
const number = (v, digits = 2) => v !== null && v !== undefined && Number.isFinite(Number(v)) ? Number(v).toLocaleString('en-IN', { maximumFractionDigits: digits }) : '—';
const signed = v => v === null || v === undefined ? '—' : `${Number(v) > 0 ? '+' : ''}${number(v)}`;
const clean = row => row.signal_structure !== 'CONFLICTING';
const aligned = row => clean(row) && row.active.length >= 2;
async function readJson(response, label) {
  if (!response.ok) throw new Error(`${label} unavailable (${response.status})`);
  return response.json();
}
function Badge({ children, tone = 'muted' }) { return <span className={`la-tag la-tag--${tone}`}>{children}</span>; }
function Table({ headers, children }) { return <div className="la-tablewrap"><table className="la-table"><thead><tr>{headers.map(h => <th key={h}>{h}</th>)}</tr></thead><tbody>{children}</tbody></table></div>; }
function Metric({ label, value, sub }) { return <div className="la-metric"><span>{label}</span><strong>{value}</strong><small>{sub}</small></div>; }
export function StateBanner({ readiness, freshness, runtime, requestFailed = false }) {
  const feed = runtime?.feed || {};
  const failed = ['exhausted', 'auth_failed', 'failed'].includes(feed.status);
  const closed = runtime?.evaluation_status === 'market_closed';
  const live = !requestFailed && !closed && !failed && feed.status === 'connected' && freshness?.stale === false && readiness?.status === 'ready';
  return <div className={`la-banner ${failed || requestFailed ? 'la-banner--bad' : ''}`}>
    <div><Badge tone={live ? 'positive' : 'warning'}>{live ? 'Live research' : closed ? 'Market closed · historical signals' : 'Historical signals'}</Badge>
      <strong>{failed ? 'Feed recovery required' : live ? 'Receiving market data' : 'Check timestamps before using these readings'}</strong></div>
    <p>Latest evaluation: {date(freshness?.latest_successful_at)}. Feed: {feed.status || 'unknown'} · Provider: {runtime?.provider || 'unknown'}.</p>
    {failed && <p>{feed.last_error || 'Connection attempts failed.'} Recovery is attempted during the next market session; a successful connection is not yet confirmed.</p>}
    {runtime?.feed_fallback && <p>Backup feed: {runtime.feed_fallback.status}. Derivatives coverage may be unavailable on backup.</p>}
    {readiness?.status === 'persistence_degraded' && <p>Some engine results could not be stored. Affected engines: {(readiness.degraded_engines || []).join(', ')}.</p>}
  </div>;
}
export function SectorRotation({ groww }) {
  const rows = groww?.sectors || [];
  const run = groww?.runs?.find(r => r.strategy === 'agi_sector_rotation_v1');
  return <section className="la-panel"><div className="la-section-head"><h2>Sector rotation</h2><p>Scheduled daily-data model · Run: {date(run?.as_of)}. Relative change is versus Nifty, in percentage points.</p></div>
    <Table headers={['Rank', 'Sector', 'Score / 100', '20d return %', '20d relative pp', '60d relative pp', 'Rotation', 'Risk']}>
      {rows.map(r => <tr key={r.sector}><td>{r.rank}</td><td><strong>{r.sector}</strong></td><td>{number(r.score, 1)}</td><td>{signed(r.return_20d)}</td><td>{signed(r.relative_20d)}</td><td>{signed(r.relative_60d)}</td><td><Badge>{r.rotation}</Badge></td><td>{r.risk || '—'}</td></tr>)}
      {!rows.length && <tr><td colSpan={8}>No sector results available.</td></tr>}
    </Table><p className="la-note">A sector can lead Nifty while still losing value. This screen is separate from the intraday composite.</p></section>;
}
export function Shortlist({ rows, onSelect }) {
  const top = rows.filter(aligned).sort((a,b) => b.active.length-a.active.length || Math.abs(b.composite)-Math.abs(a.composite)).slice(0,12);
  return <section className="la-panel"><div className="la-section-head"><h2>Aligned signals</h2><p>Two or more engines pointing the same way in the same evaluation. Shared price and volume inputs mean these are not independent confirmations.</p></div>
    <Table headers={['Stock', 'Direction', 'Model score', 'Aligned engines', 'Signal time']}>
      {top.map(r => <tr key={r.symbol}><td><button className="la-stock-button" onClick={() => onSelect?.(r.symbol)}>{r.symbol}</button></td><td><Badge tone={r.composite > 0 ? 'positive' : 'negative'}>{plainSignalDirection(r).label}</Badge></td><td>{signed(r.composite)}</td><td>{r.active.map(s => ENGINE_PLAIN[s.engine]?.label || s.engine).join(' · ')}</td><td>{date(r.timestamp)}</td></tr>)}
      {!top.length && <tr><td colSpan={5}>No aligned multi-engine signals in this snapshot.</td></tr>}
    </Table></section>;
}
export function EquityOpportunities({ groww }) {
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const rows = (groww?.equities || []).filter(r => String(r.symbol).toUpperCase().includes(query.trim().toUpperCase()));
  const currentPage = Math.min(page, Math.max(0, Math.ceil(rows.length / 25) - 1));
  const run = groww?.runs?.find(r => r.strategy === 'agi_equity_opportunity_v1');
  return <section className="la-panel"><div className="la-section-head"><h2>Equity screen</h2><p>Scheduled daily-data model · Run: {date(run?.as_of)}. Scores rank the model’s observations, not expected returns.</p></div>
    <div className="la-toolbar"><input aria-label="Search equity screen" placeholder="Search stocks" value={query} onChange={e => { setQuery(e.target.value); setPage(0); }}/><span>{rows.length} stocks</span></div>
    <Table headers={['Rank', 'Stock', 'Last price ₹', 'Price time', 'Score / 100', '20d return %', '20d relative pp', '60d relative pp', 'Volume / avg', 'Risk']}>
      {rows.slice(currentPage*25, currentPage*25+25).map(r => <tr key={r.symbol}><td>{r.rank}</td><td><strong>{r.symbol}</strong></td><td>{number(r.price)}</td><td>{date(r.price_as_of)}</td><td>{number(r.score,1)}</td><td>{signed(r.return_20d)}</td><td>{signed(r.relative_20d)}</td><td>{signed(r.relative_60d)}</td><td>{number(r.volume_ratio)}× {!r.volume_confirmation && <small>Unconfirmed</small>}</td><td>{r.risk || '—'}</td></tr>)}
      {!rows.length && <tr><td colSpan={10}>No matching stocks.</td></tr>}
    </Table><Pager page={currentPage} total={rows.length} onChange={setPage}/></section>;
}
export function SignalRow({ row, expanded, onToggle }) {
  const view = interpretCanonicalSignal(row);
  const unverified = row.active.filter(s => s.liquidity_verified !== true || s.liquidity_ok !== true).length;
  const direction = plainSignalDirection(row);
  return <><tr className={expanded ? 'la-selected' : ''}>
    <td><button className="la-stock-button" aria-expanded={expanded} onClick={onToggle}>{expanded ? '−' : '+'} {row.symbol}</button><small>{row.sector}</small></td>
    <td><Badge tone={direction.key}>{direction.label}</Badge></td><td>{signed(row.composite)}</td>
    <td>{number(row.live_price)}<small>{date(row.price_as_of)}</small></td><td>{date(row.timestamp)}{row.excluded_components?.length > 0 && <small>{row.excluded_components.length} older components excluded</small>}</td>
    <td>{row.samples ? `${row.samples} minimum comparables` : 'Model only'}<small>Not validated</small></td>
    <td>{row.active.map(s => <span className="la-component" key={s.engine}>{ENGINE_PLAIN[s.engine]?.label}: {s.direction === 'positive' ? '↑' : '↓'}</span>)}</td>
    <td><Badge tone={unverified ? 'warning' : 'muted'}>{unverified ? `${unverified} unverified` : 'Spread checked'}</Badge></td>
  </tr>{expanded && <tr className="la-detail"><td colSpan={8}><div className="la-detail-grid"><div><h3>What the model sees</h3><p>{view.summary}</p><p>Price at signal: ₹{number(row.active[0]?.price_at_signal)}. Latest displayed price is a separate observation.</p></div><div><h3>Evidence and limitations</h3><p>{row.confidence_basis}</p><p>Model score is not a probability. Missing spread measurements remain unverified. Historical readings do not become fresh when this page refreshes.</p></div></div></td></tr>}</>;
}
function Pager({ page, total, onChange }) { return <div className="la-pager"><span>{total ? `${page*25+1}–${Math.min(total,page*25+25)} of ${total}` : '0 results'}</span><button disabled={page === 0} onClick={() => onChange(page-1)}>Previous</button><button disabled={(page+1)*25 >= total} onClick={() => onChange(page+1)}>Next</button></div>; }
function Evidence({ runtime }) {
  const [data, setData] = useState(null); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const load = async () => { setBusy(true); setError(''); try { setData(await readJson(await fetch(`${API_ORIGIN}/api/market/live-alpha/evidence`), 'Outcome evidence')); } catch(e) { setError(e.message); } finally { setBusy(false); } };
  const settlement = runtime?.outcome_settlement;
  return <section className="la-panel"><div className="la-section-head"><h2>Measured signal outcomes</h2><p>Forward price observations, not executed trades or a portfolio backtest. Signals can overlap. No win probability is inferred from the model score.</p><button disabled={busy} onClick={load}>{busy ? 'Loading…' : 'Load recorded outcomes'}</button></div>
    <p className="la-note">Settlement: {settlement?.status || 'unknown'} · Last check: {date(settlement?.last_run)}. {settlement?.last_error ? 'Latest settlement reported an error.' : ''}</p>
    {error && <p role="alert" className="la-error">{error}</p>}
    {data && <><p className="la-note">{data.scope} {data.truncated ? 'Sample limit reached; this is a partial history.' : ''} Refreshed: {date(data.generated_at)}.</p>
      <Table headers={['Engine', 'Horizon', 'Completed', 'Pending', 'Missed / invalid', 'Sessions', 'Mean directional return % after stored costs', 'Positive outcomes %', 'Stored costs bps']}>
        {data.rows.map(r => <tr key={`${r.engine}-${r.horizon}`}><td>{ENGINE_PLAIN[r.engine]?.label || r.engine}</td><td>{r.horizon}</td><td>{r.completed}</td><td>{r.pending}</td><td>{r.missed + r.invalid}</td><td>{r.sessions}</td><td>{signed(r.mean_net_directional_return_pct)}</td><td>{number(r.positive_outcome_pct)}</td><td>{r.minimum_cost_bps === null ? '—' : `${number(r.minimum_cost_bps)}–${number(r.maximum_cost_bps)}`}{r.minimum_cost_bps === 0 && <small>Includes zero-cost observations</small>}</td></tr>)}
        {!data.rows.length && <tr><td colSpan={9}>No recorded outcomes in this window. Performance is unverified.</td></tr>}
      </Table></>}
    <p className="la-note">A sample count alone does not validate a strategy. These results do not include an independently verified execution model, portfolio sizing or drawdown. Stored costs of zero mean costs were not modelled.</p></section>;
}
export default function LiveAlphaPage() {
  const [payload,setPayload] = useState({}); const [runtime,setRuntime] = useState(null);
  const [loading,setLoading] = useState(true); const [error,setError] = useState('');
  const [tab,setTab] = useState('Signals'); const [filter,setFilter] = useState('all');
  const [search,setSearch] = useState(''); const [open,setOpen] = useState(null); const [page,setPage] = useState(0);
  const [sort,setSort] = useState('strength'); const [refresh,setRefresh] = useState(0);
  useEffect(() => {
    let cancelled=false; let pending=false;
    const load = async () => { if (pending) return; pending=true; try {
      if (!API_ORIGIN) throw new Error('AGI backend origin is not configured.');
      const [workspace,status] = await Promise.all([
        fetch(`${API_ORIGIN}/api/market/live-alpha/workspace`).then(r=>readJson(r,'Research store')),
        fetch(`${API_ORIGIN}/api/market/live-alpha/status`).then(r=>readJson(r,'Feed status')),
      ]);
      if (!cancelled) { setPayload(workspace); setRuntime(status); setError(''); }
    } catch(e) { if (!cancelled) setError(e.message); } finally { pending=false; if (!cancelled) setLoading(false); } };
    document.title='Live Alpha | Agarwal Global Investments'; load(); const timer=setInterval(load,REFRESH_MS);
    return () => { cancelled=true; clearInterval(timer); };
  },[refresh]);
  const allRows=useMemo(()=>buildCanonicalSignals(payload.signals || [],payload.strategy_health || {}),[payload]);
  const snapshotAvailable=Array.isArray(payload.signals);
  const count=value=>snapshotAvailable ? value : '—';
  const directional=allRows.filter(r=>r.active.length);
  const shown=filterRadarRows(directional,filter,{search}).sort((a,b)=>sort==='symbol' ? a.symbol.localeCompare(b.symbol) : sort==='newest' ? Date.parse(b.timestamp)-Date.parse(a.timestamp) : Math.abs(b.composite)-Math.abs(a.composite));
  const currentPage=Math.min(page,Math.max(0,Math.ceil(shown.length/25)-1));
  if (loading) return <div className="la-page">Loading Live Alpha…</div>;
  return <main className="la-page"><header className="la-head"><div><span className="la-eyebrow">AGI / MARKET RESEARCH</span><h1>Live Alpha<span>.</span></h1><p>Understand the signal. Check the evidence.</p></div><button onClick={()=>setRefresh(v=>v+1)}>Refresh data ↻</button></header>
    {error && <p className="la-error" role="alert">{error}. Any displayed snapshot is retained history.</p>}
    <StateBanner readiness={payload.readiness} freshness={payload.freshness} runtime={runtime} requestFailed={Boolean(error)}/>
    <section className="la-metrics"><Metric label="Flagged stocks" value={count(directional.length)} sub={snapshotAvailable ? `of ${allRows.length} in stored snapshot` : 'Snapshot unavailable'}/><Metric label="Positive · no conflict" value={count(directional.filter(r=>clean(r)&&r.composite>0).length)}/><Metric label="Negative · no conflict" value={count(directional.filter(r=>clean(r)&&r.composite<0).length)}/><Metric label="Aligned engines" value={count(directional.filter(aligned).length)} sub="2+ same-direction components"/><Metric label="Conflicting signals" value={count(directional.filter(r=>!clean(r)).length)} sub="Opposing directions"/></section>
    <nav className="la-tabs" aria-label="Live Alpha views">{['Signals','Signal history','Sector rotation','Equity screen','Evidence'].map(t=><button key={t} className={tab===t?'is-active':''} aria-pressed={tab===t} onClick={()=>setTab(t)}>{t}</button>)}</nav>
    {tab==='Signals' && <><Shortlist rows={directional} onSelect={s=>{setSearch(s);setFilter('all');setPage(0);setOpen(s);}}/>
    <section className="la-panel"><div className="la-section-head"><h2>Stock signals</h2><p>Snapshot: {date(payload.freshness?.latest_successful_at)} · Expand a stock to inspect the reasoning.</p></div><div className="la-toolbar"><input aria-label="Search symbol or sector" placeholder="Search symbol or sector" value={search} onChange={e=>{setSearch(e.target.value);setPage(0);}}/><select aria-label="Filter signals" value={filter} onChange={e=>{setFilter(e.target.value);setPage(0);}}>{[['all','All signals'],['positive','Positive'],['negative','Negative'],['multi','Aligned'],['conflicting','Conflicting']].map(([v,l])=><option key={v} value={v}>{l}</option>)}</select><select aria-label="Sort signals" value={sort} onChange={e=>{setSort(e.target.value);setPage(0);}}><option value="strength">Model strength</option><option value="symbol">Stock A–Z</option><option value="newest">Newest signal</option></select></div>
    <Table headers={['Stock / sector','Direction','Score ±99','Last price ₹ / time','Signal time','Evidence','Engine directions','Liquidity']}>
      {shown.slice(currentPage*25,currentPage*25+25).map(row=><SignalRow key={row.symbol} row={row} expanded={open===row.symbol} onToggle={()=>setOpen(open===row.symbol?null:row.symbol)}/>)}
      {!shown.length && <tr><td colSpan={8}>No matching signals. Try another filter or search.</td></tr>}
    </Table><Pager page={currentPage} total={shown.length} onChange={setPage}/></section></>}
    {tab==='Signal history' && <LiveAlphaHistory latestSignalAt={payload.freshness?.latest_successful_at}/>}
    {tab==='Sector rotation' && <SectorRotation groww={payload.groww}/>}{tab==='Equity screen' && <EquityOpportunities groww={payload.groww}/>}{tab==='Evidence' && <Evidence runtime={runtime}/>}
    <details className="la-panel la-health"><summary>Engine coverage and health</summary><Table headers={['Engine','What it measures','Stored coverage','Directional signals','Status','Last evaluation']}>
      {LIVE_ALPHA_STRATEGIES.map(([key,label])=>{const h=payload.strategy_health?.[key];return <tr key={key}><td>{label}</td><td>{ENGINE_PLAIN[key]?.plain}</td><td>{h?.stored_signals ?? '—'} / {allRows.length}</td><td>{directional.filter(r=>r.active.some(s=>s.engine===key)).length}</td><td>{h?.status || 'unknown'}</td><td>{date(h?.latest_run_at)}</td></tr>;})}
    </Table><p className="la-note">Positioning covers only stocks with resolved derivative instruments. Missing coverage is not a neutral signal.</p></details>
    <footer className="la-foot">Research only · No orders or portfolio changes · Automatic page refresh every minute · All timestamps IST. Model scores are not expected returns or probabilities.</footer>
  </main>;
}
