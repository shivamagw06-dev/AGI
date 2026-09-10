import { useEffect, useMemo, useState } from 'react';
import { Bell, Briefcase, CheckCircle2, FileSearch, Gauge, Layers3, Loader2, Play, Radar, ShieldCheck, Sparkles } from 'lucide-react';
import { createInstitutionalGroup, createInstitutionalWatchlist, getInstitutionalBacktest, getInstitutionalResearchLayer, getInstitutionalWorkspace, markInstitutionalPersonalizedAlert } from '@/lib/institutionalHoldingsApi';

const percent = (value, signed = false) => `${signed && Number(value) > 0 ? '+' : ''}${(Number(value || 0) * 100).toFixed(1)}%`;
const displayDate = (value) => { const date = value ? new Date(value) : null; return date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' }) : 'Timestamp unavailable'; };
function Metric({ label, value, note }) { return <div className="rounded-xl border border-white/10 bg-white/[0.035] p-4"><div className="text-[10px] font-bold uppercase tracking-[.18em] text-neutral-700">{label}</div><div className="mt-2 text-2xl font-semibold text-white">{value}</div>{note ? <div className="mt-1 text-xs text-neutral-700">{note}</div> : null}</div>; }
function Empty({ children }) { return <div className="rounded-xl border border-dashed border-white/10 p-8 text-center text-sm leading-6 text-neutral-700">{children}</div>; }

export default function InstitutionalResearchLayer() {
  const [data, setData] = useState(null); const [tab, setTab] = useState('rotation'); const [managerSlug, setManagerSlug] = useState('');
  const [workspace, setWorkspace] = useState(null); const [working, setWorking] = useState(''); const [message, setMessage] = useState('');
  const [backtest, setBacktest] = useState(null); const [backtestQuarters, setBacktestQuarters] = useState(20);
  const [groupName, setGroupName] = useState('High-conviction managers'); const [watchlistName, setWatchlistName] = useState('Institutional signals'); const [watchTickers, setWatchTickers] = useState('AAPL, MSFT, NVDA');
  const loadResearchLayer = () => {
    setWorking('research'); setMessage('');
    getInstitutionalResearchLayer()
      .then((payload) => { setData(payload); setManagerSlug(payload.managers?.[0]?.slug || ''); })
      .catch((error) => setMessage(error.message || 'Institutional research is temporarily unavailable.'))
      .finally(() => setWorking(''));
  };
  useEffect(() => { loadResearchLayer(); }, []);
  const movers = useMemo(() => (data?.sector_rotation || []).filter((row) => row.sector !== 'Unclassified'), [data]);
  /**
   * One row per manager, newest first.
   *
   * Stored runs arrive ordered by generated_at, and a manager accumulates one
   * per day and per strategy - so without this the list showed the same
   * manager several times and pushed others off the end. A run just computed
   * on this page takes precedence over anything stored for that manager.
   */
  const newestPerManager = useMemo(() => {
    const seen = new Map();
    for (const run of [...(backtest ? [backtest] : []), ...(data?.backtests || [])]) {
      const key = run.manager_id || run.institutional_managers?.slug || run.manager?.slug || run.id;
      if (!seen.has(key)) seen.set(key, run);
    }
    return [...seen.values()];
  }, [data, backtest]);
  /**
   * What the stated runs actually did, counted rather than asserted.
   *
   * The panel used to tell the reader that underperformance was the expected
   * result. Across fifty-one managers it is not: the spread runs from -58% to
   * +280% against SPY, and a claim contradicted by the numbers beside it
   * teaches the reader to discount both.
   */
  const spread = useMemo(() => {
    const excess = newestPerManager
      .filter((run) => run.status === 'calculated')
      .map((run) => Number(run.metrics?.excess_vs_spy))
      .filter((value) => Number.isFinite(value))
      .sort((a, b) => a - b);
    if (!excess.length) return null;
    return {
      count: excess.length,
      beat: excess.filter((value) => value > 0).length,
      worst: excess[0],
      best: excess[excess.length - 1],
      median: excess[Math.floor(excess.length / 2)],
    };
  }, [newestPerManager]);
  /**
   * Read this manager's run, computing it only if today has none.
   *
   * The GET endpoint serves the day's stored run and falls back to computing;
   * the admin POST forces a fresh one. This uses the read, so a signed-in
   * client cannot make the server price several hundred thousand rows by
   * holding down a button.
   */
  const runBacktest = async () => {
    if (!managerSlug) return;
    setWorking('backtest'); setMessage(''); setBacktest(null);
    try {
      setBacktest(await getInstitutionalBacktest(managerSlug, { quarters: backtestQuarters, topN: 10 }));
    } catch (error) {
      setMessage(error.message || 'The backtest could not be completed.');
    } finally { setWorking(''); }
  };
  const loadWorkspace = async () => { setWorking('workspace'); setMessage(''); try { setWorkspace(await getInstitutionalWorkspace()); } catch (error) { setMessage(error.message); } finally { setWorking(''); } };
  const tabs = [['rotation', 'Sector rotation', Layers3], ['performance', 'Performance lab', Gauge], ['filings', '13D/G + Form 4', FileSearch], ['briefs', 'Analyst briefs', Sparkles], ['workspace', 'My workspace', Briefcase]];
  if (!data) return <section className="mx-auto mt-8 flex max-w-[1760px] flex-col items-center justify-center rounded-2xl border border-neutral-200 bg-[#222222] p-16 text-center text-neutral-600">{working === 'research' ? <><Loader2 className="mb-3 h-5 w-5 animate-spin" /><span>Loading institutional research layer</span></> : <><div className="text-base font-semibold text-white">Institutional research is temporarily unavailable</div><div className="mt-2 max-w-xl text-sm">{message || 'The evidence service did not respond. Your existing holdings data remains available.'}</div><button type="button" onClick={loadResearchLayer} className="mt-5 rounded-xl bg-neutral-900 px-5 py-3 text-sm font-bold text-neutral-600">Retry research layer</button></>}</section>;
  return <section className="mx-auto mt-8 max-w-[1760px] overflow-hidden rounded-2xl border border-neutral-300/15 bg-[#222222] text-neutral-600 shadow-2xl shadow-slate-950/10">
    <div className="relative overflow-hidden border-b border-white/10 px-6 py-7 lg:px-8"><div className="absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(34,211,238,.08)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,.08)_1px,transparent_1px)] [background-size:32px_32px]" /><div className="relative flex flex-col justify-between gap-5 lg:flex-row lg:items-end"><div><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.28em] text-neutral-600"><Radar className="h-4 w-4" /> Institutional intelligence V3</div><h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">From disclosure to decision</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-600">Point-in-time classifications, filing-aware performance, ownership disclosures and analyst-controlled research in one evidence trail.</p></div><div className="flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-4 py-2 text-xs font-semibold text-emerald-300"><ShieldCheck className="h-4 w-4" /> No look-ahead methodology</div></div>
      <div className="relative mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5"><Metric label="Tracked managers" value={data.readiness?.managers_tracked || 0} /><Metric label="12-quarter ready" value={data.readiness?.managers_with_12_quarters || 0} note="Full history gate" /><Metric label="Classifications" value={data.readiness?.classifications || 0} /><Metric label="13D/G + Form 4" value={data.readiness?.external_filings || 0} /><Metric label="Approved briefs" value={data.readiness?.approved_briefs || 0} /></div></div>
    {data?.data_integrity && data.data_integrity.clean === false ? (
      <div className="border-b border-neutral-300/20 bg-neutral-900/[0.06] px-5 py-3">
        <span className="text-[10px] font-bold uppercase tracking-[.18em] text-neutral-600">Historical repair in progress</span>
        <p className="mt-1 max-w-3xl text-xs leading-5 text-neutral-600">{data.data_integrity.message}</p>
      </div>
    ) : null}
    <div className="flex gap-2 overflow-x-auto border-b border-white/10 px-5 py-3">{tabs.map(([key, label, Icon]) => <button key={key} type="button" onClick={() => { setTab(key); if (key === 'workspace' && !workspace) loadWorkspace(); }} className={`inline-flex shrink-0 items-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition ${tab === key ? 'bg-neutral-900 text-neutral-600' : 'text-neutral-600 hover:bg-white/5 hover:text-white'}`}><Icon className="h-4 w-4" />{label}</button>)}</div>
    {message ? <div className="mx-6 mt-5 rounded-xl border border-neutral-300/15 bg-neutral-900/5 px-4 py-3 text-sm text-neutral-600">{message}</div> : null}
    <div className="p-6 lg:p-8">{data.status === 'setup_required' ? <Empty>{data.message}</Empty> : null}
      {tab === 'rotation' && data.status === 'ready' ? <div className="grid gap-6 lg:grid-cols-[1.15fr_.85fr]"><div><div className="mb-4 flex items-center justify-between"><div><div className="text-[10px] font-bold uppercase tracking-[.2em] text-neutral-600">Aggregate positioning</div><h3 className="mt-1 text-xl font-semibold text-white">Sector rotation map</h3></div><span className="text-xs text-neutral-700">Latest vs prior disclosed quarter</span></div><div className="space-y-2">{movers.length ? movers.slice(0, 12).map((row) => <div key={row.sector} className="grid grid-cols-[minmax(130px,1fr)_90px_90px] items-center gap-3 rounded-xl border border-white/10 bg-white/[0.025] px-4 py-3 text-sm"><span className="font-medium text-neutral-600">{row.sector}</span><span className="text-right text-neutral-600">{percent(row.current_weight)}</span><span className={`text-right font-semibold ${row.weight_change >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>{percent(row.weight_change, true)}</span></div>) : <Empty>Sector intelligence appears as SEC classifications are collected.</Empty>}</div></div><div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"><div className="text-[10px] font-bold uppercase tracking-[.2em] text-neutral-600">Interpretation guardrail</div><h3 className="mt-2 text-xl font-semibold">What this signal means</h3><p className="mt-3 text-sm leading-6 text-neutral-600">This measures changes in disclosed 13F long-equity value. It is not live positioning and does not reveal shorts, cash, swaps or a manager's full portfolio.</p><div className="mt-5 rounded-xl bg-black/20 p-4 text-xs leading-5 text-neutral-700">{data.readiness?.methodology}</div></div></div> : null}
      {/* The backtester was withheld, not hidden, on two audit findings: it entered on
          the SEC acceptance date itself rather than the next tradable session, and
          adjusted-price coverage for the tracked managers was 0%. Both are now closed.
          Entry runs off firstTradableSession, strictly after the acceptance timestamp
          read in US Eastern, off a calendar derived from observed benchmark prices;
          eleven years of adjusted closes are loaded and average coverage on the tracked
          managers is 99.96%. A run that cannot meet the coverage floor still stores as
          not_calculable and is shown as its reasons rather than as a number - the point
          of the gate was never the gate, it was that no figure goes out that would be
          wrong in the direction that flatters the manager. */}
      {tab === 'performance' ? <div className="grid gap-6 lg:grid-cols-[1.15fr_.85fr]">
        <div>
          <div className="mb-4 flex items-center justify-between"><div><div className="text-[10px] font-bold uppercase tracking-[.2em] text-neutral-600">Filing-aware backtest</div><h3 className="mt-1 text-xl font-semibold text-white">What copying the disclosure would have returned</h3></div><span className="text-xs text-neutral-700">Net of costs, versus SPY and QQQ</span></div>
          <div className="mb-4 rounded-xl border border-white/10 bg-white/[0.035] p-4">
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex-1"><span className="block text-[10px] font-bold uppercase tracking-[.16em] text-neutral-700">Manager</span><select value={managerSlug} onChange={(event) => { setManagerSlug(event.target.value); setBacktest(null); }} className="mt-2 w-full rounded-xl border border-white/10 bg-[#222222] px-3 py-2.5 text-sm">{data.managers?.map((manager) => <option key={manager.id} value={manager.slug}>{manager.display_name}</option>)}</select></label>
              <label><span className="block text-[10px] font-bold uppercase tracking-[.16em] text-neutral-700">Quarters</span><select value={backtestQuarters} onChange={(event) => { setBacktestQuarters(Number(event.target.value)); setBacktest(null); }} className="mt-2 rounded-xl border border-white/10 bg-[#222222] px-3 py-2.5 text-sm">{[8, 12, 20, 28, 40].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
              <button type="button" onClick={runBacktest} disabled={working === 'backtest' || !managerSlug} className="inline-flex items-center gap-2 rounded-xl bg-neutral-900 px-5 py-2.5 text-sm font-bold text-neutral-600 disabled:opacity-50">{working === 'backtest' ? <><Loader2 className="h-4 w-4 animate-spin" /> Running</> : <><Play className="h-4 w-4" /> Run backtest</>}</button>
            </div>
            <p className="mt-3 text-xs leading-5 text-neutral-700">{working === 'backtest'
              ? 'Reading every disclosed position and its adjusted closes. A manager not run today can take several minutes; one already run today returns immediately.'
              : "Top 10 positions by disclosed value, rebalanced each quarter, entered on the first session after the filing became public. Today's run is reused if one exists."}</p>
          </div>
          <div className="space-y-3">{newestPerManager.map((run) => {
            const metrics = run.metrics || {};
            // Two shapes: a stored run arrives with the joined
            // institutional_managers, a freshly computed one with `manager`.
            const name = run.institutional_managers?.display_name || run.manager?.display_name || 'Manager';
            if (run.status !== 'calculated') {
              return <div key={run.id} className="rounded-xl border border-white/10 bg-white/[0.025] px-4 py-3 text-sm"><div className="flex items-center justify-between"><span className="font-medium text-white">{name}</span><span className="rounded-full border border-neutral-300/30 px-2 py-[2px] text-[9px] font-bold uppercase tracking-wider text-neutral-600/80">Not calculable</span></div><p className="mt-2 text-xs leading-5 text-neutral-700">{metrics.reason || 'This manager does not meet the evidence bar for a stated return.'}</p></div>;
            }
            const excess = Number(metrics.excess_vs_spy || 0);
            return <div key={run.id} className="rounded-xl border border-white/10 bg-white/[0.025] px-4 py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2"><span className="font-medium text-white">{name}</span><span className="text-xs text-neutral-700">{metrics.periods} quarters · {percent(metrics.average_coverage)} priced{run.from_cache === false ? ' · computed just now' : run.from_cache === true ? " · today's stored run" : ''}</span></div>
              <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div><div className="text-[10px] font-bold uppercase tracking-[.16em] text-neutral-700">Strategy</div><div className="mt-1 text-lg font-semibold text-white">{percent(metrics.total_return)}</div></div>
                <div><div className="text-[10px] font-bold uppercase tracking-[.16em] text-neutral-700">SPY</div><div className="mt-1 text-lg font-semibold text-neutral-600">{percent(metrics.spy_return)}</div></div>
                <div><div className="text-[10px] font-bold uppercase tracking-[.16em] text-neutral-700">QQQ</div><div className="mt-1 text-lg font-semibold text-neutral-600">{percent(metrics.qqq_return)}</div></div>
                <div><div className="text-[10px] font-bold uppercase tracking-[.16em] text-neutral-700">Excess vs SPY</div><div className={`mt-1 text-lg font-semibold ${excess >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>{percent(excess, true)}</div></div>
              </div>
              {Number(metrics.worst_period_coverage) < 1 ? <div className="mt-3 text-xs text-neutral-700">Thinnest quarter priced at {percent(metrics.worst_period_coverage)}{metrics.worst_coverage_period ? ` (${metrics.worst_coverage_period})` : ''}. Unpriced positions are excluded, never assumed flat.</div> : null}
            </div>;
          })}{!backtest && !data.backtests?.length ? <Empty>No backtest has been run yet. Choose a manager above and run one.</Empty> : null}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
          <div className="text-[10px] font-bold uppercase tracking-[.2em] text-neutral-600">Interpretation guardrail</div>
          <h3 className="mt-2 text-xl font-semibold">What the excess column is not</h3>
          <p className="mt-3 text-sm leading-6 text-neutral-600">A strategy that copies a 13F cannot beat the manager. The filing is public six weeks or more after the quarter it describes, and entry here is the first tradable session strictly after that public acceptance - so this measures what a follower could have had, not what the manager had.</p>
          <p className="mt-3 text-sm leading-6 text-neutral-600">It can, however, beat an index, and often does. Ten positions is concentrated, and ranking them by disclosed value selects whatever has appreciated most - a momentum tilt that belongs to the strategy rather than to the manager. A wide beat is that tilt meeting a strong market, not evidence of skill; a wide miss is a book that sat out the move, not evidence of its absence.</p>
          {spread ? <p className="mt-3 text-sm leading-6 text-neutral-600">Across the {spread.count} managers stated here, {spread.beat} beat SPY and {spread.count - spread.beat} did not, from {percent(spread.worst, true)} to {percent(spread.best, true)}, with a median of {percent(spread.median, true)}. Read where a manager sits in that spread rather than the sign of its number.</p> : null}
          <div className="mt-5 rounded-xl bg-black/20 p-4 text-xs leading-5 text-neutral-700">{data.readiness?.methodology}</div>
        </div>
      </div> : null}
      {tab === 'filings' ? <div>{data.filing_events?.length ? <div className="grid gap-3 md:grid-cols-2">{data.filing_events.slice(0, 20).map((event) => <a key={event.id} href={event.source_url} target="_blank" rel="noreferrer" className="rounded-xl border border-white/10 bg-white/[0.03] p-4 hover:border-neutral-300/30"><div className="flex justify-between"><span className="rounded-full bg-neutral-900/10 px-2 py-1 text-[10px] font-bold text-neutral-600">{event.form_type}</span><span className="text-xs text-neutral-700">{displayDate(event.filed_at)}</span></div><div className="mt-3 font-semibold">{event.ticker || event.event_type.replaceAll('_', ' ')}</div><div className="mt-1 text-xs capitalize text-neutral-700">{event.event_type.replaceAll('_', ' ')}</div></a>)}</div> : <Empty>Run the research refresh to collect 13D/G and Form 4 disclosures from SEC EDGAR.</Empty>}</div> : null}
      {tab === 'briefs' ? <div>{data.approved_briefs?.length ? <div className="grid gap-4 md:grid-cols-2">{data.approved_briefs.map((brief) => <article key={brief.id} className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.18em] text-emerald-300"><CheckCircle2 className="h-4 w-4" /> Analyst approved</div><h3 className="mt-3 text-lg font-semibold leading-6">{brief.headline}</h3><p className="mt-3 text-sm leading-6 text-neutral-600">{brief.summary}</p><p className="mt-4 text-xs text-neutral-700">Known after {displayDate(brief.evidence?.accepted_at)}</p></article>)}</div> : <Empty>Generated briefs stay private until an analyst approves every claim.</Empty>}</div> : null}
      {tab === 'workspace' ? <div className="grid gap-6 lg:grid-cols-2"><div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"><div className="text-[10px] font-bold uppercase tracking-[.2em] text-neutral-600">Saved fund groups</div><h3 className="mt-2 text-xl font-semibold">Compare managers you follow</h3><input value={groupName} onChange={(event) => setGroupName(event.target.value)} className="mt-5 w-full rounded-xl border border-white/10 bg-[#222222] px-3 py-3 text-sm" /><select value={managerSlug} onChange={(event) => setManagerSlug(event.target.value)} className="mt-3 w-full rounded-xl border border-white/10 bg-[#222222] px-3 py-3 text-sm">{data.managers?.map((manager) => <option key={manager.id} value={manager.slug}>{manager.display_name}</option>)}</select><button type="button" onClick={async () => { setWorking('group'); try { const id = data.managers.find((row) => row.slug === managerSlug)?.id; await createInstitutionalGroup({ name: groupName, managerIds: id ? [id] : [] }); await loadWorkspace(); setMessage('Fund group saved.'); } catch (error) { setMessage(error.message); setWorking(''); } }} className="mt-3 rounded-xl bg-neutral-900 px-4 py-3 text-sm font-bold text-neutral-600">Save group</button><div className="mt-5 space-y-2">{workspace?.groups?.map((group) => <div key={group.id} className="rounded-xl bg-black/20 px-4 py-3 text-sm">{group.name} <span className="text-neutral-700">· {group.institutional_manager_group_members?.length || 0} managers</span></div>)}</div></div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"><div className="text-[10px] font-bold uppercase tracking-[.2em] text-neutral-600">Watchlists and alerts</div><h3 className="mt-2 text-xl font-semibold">Get disclosure changes that matter</h3><input value={watchlistName} onChange={(event) => setWatchlistName(event.target.value)} className="mt-5 w-full rounded-xl border border-white/10 bg-[#222222] px-3 py-3 text-sm" /><input value={watchTickers} onChange={(event) => setWatchTickers(event.target.value)} className="mt-3 w-full rounded-xl border border-white/10 bg-[#222222] px-3 py-3 text-sm" /><button type="button" onClick={async () => { setWorking('watchlist'); try { await createInstitutionalWatchlist({ name: watchlistName, items: watchTickers.split(',').map((value) => value.trim()).filter(Boolean) }); await loadWorkspace(); setMessage('Watchlist saved.'); } catch (error) { setMessage(error.message); setWorking(''); } }} className="mt-3 rounded-xl bg-neutral-900 px-4 py-3 text-sm font-bold text-neutral-600">Save watchlist</button><div className="mt-5 space-y-2">{workspace?.alerts?.slice(0, 8).map((alert) => <button key={alert.id} type="button" onClick={async () => { await markInstitutionalPersonalizedAlert(alert.id); await loadWorkspace(); }} className="flex w-full items-start gap-3 rounded-xl bg-black/20 px-4 py-3 text-left"><Bell className={`mt-0.5 h-4 w-4 ${alert.is_read ? 'text-neutral-700' : 'text-neutral-600'}`} /><span><span className="block text-sm font-semibold">{alert.title}</span><span className="mt-1 block text-xs text-neutral-700">{alert.body}</span></span></button>)}</div>{!workspace && working !== 'workspace' ? <button type="button" onClick={loadWorkspace} className="mt-4 text-xs font-semibold text-neutral-600">Sign in and load my workspace</button> : null}</div></div> : null}
    </div>
  </section>;
}
