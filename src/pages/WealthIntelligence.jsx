import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { Search, RefreshCw, Download, ArrowUpRight, Plus, X, Landmark, Building2, SlidersHorizontal } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { getWealthUniverse, getWealthResearch } from '@/lib/wealthIntelligenceApi';
import { MODEL_VERSION, compareScenarios, breakEvenGrowth } from '@/lib/wealthScenario';
import './wealthIntelligence.css';
import PlanningWorkspace from '@/components/wealth/PlanningWorkspace';
import { emptyWorkspace } from '@/lib/wealthPlanning';
import { createReviewPack, validateReviewPack, renderReviewReport } from '@/lib/wealthReviewPack';

const ASSET_CLASSES = [
  ['equity', 'Equities'], ['mutual_fund', 'Mutual funds'], ['property', 'Land & property'],
  ['fixed_income', 'FDs & bonds'], ['commodity', 'Gold & commodities'], ['alternative', 'Alternatives'],
];
const GAPS = {
  property: ['Property discovery awaits verified local data', 'Add a property quote below to model the purchase. Local transaction comparisons, title verification and an available-listing feed are still needed before AGI can identify specific land opportunities.'],
  fixed_income: ['Specific deposit and bond offerings are not connected yet', 'Compare a quoted yield in the scenario workbench. Issuer credit, maturity, redemption terms and executable price must be verified separately.'],
  commodity: ['Investable commodity products are not connected yet', 'Compare a gold or commodity holding using your own assumptions. Physical gold, ETFs and futures have different costs and risks.'],
  alternative: ['Private offerings and distribution data are not connected yet', 'Model a supplied opportunity, then verify eligibility, fees, cash distributions and lock-in from its offering documents.'],
};
const DEFAULT_PLAN = { capital: 10000000, years: 5, fdRate: 7, incomeTax: 30, inflation: 5, reinvest: true };
const BLANK_ASSET = { growth: 0, incomeYield: 0, entryCost: 0, exitCost: 0, annualCost: 0, gainsTax: 0 };
const FIELD_LABELS = [
  ['growth', 'Annual price growth %', -99, 100], ['incomeYield', 'Annual cash yield %', 0, 40],
  ['entryCost', 'Entry costs %', 0, 50], ['exitCost', 'Exit costs %', 0, 50],
  ['annualCost', 'Annual holding cost %', 0, 20], ['gainsTax', 'Effective exit gains tax %', 0, 60],
];
const COLORS = ['#142e4c', '#c26126', '#187b71', '#745cc1', '#b93858'];
const money = n => n == null || !Number.isFinite(n) ? '—' : new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);
const pct = n => n == null || !Number.isFinite(n) ? '—' : `${n.toFixed(2)}%`;
const compact = n => Math.abs(n) >= 1e7 ? `₹${(n / 1e7).toFixed(2)}cr` : `₹${(n / 1e5).toFixed(1)}L`;
function stamp(value) {
  if (!value || !Number.isFinite(Date.parse(value))) return 'Date unavailable';
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  return `${new Date(value).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })} IST`;
}
function NumberField({ label, value, onChange, min = 0, max, step = 'any' }) {
  return <label className="wi-field"><span>{label}</span><input type="number" value={value} min={min} max={max} step={step} onChange={e => onChange(e.target.value)} /></label>;
}

export default function WealthIntelligence() {
  const [workspace, setWorkspace] = useState(emptyWorkspace);
  const [research, setResearch] = useState(null);
  const [researchLoading, setResearchLoading] = useState(false);
  const [tab, setTab] = useState('equity');
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [plan, setPlan] = useState(DEFAULT_PLAN);
  const [assets, setAssets] = useState([]);
  const [draft, setDraft] = useState(null);
  const [notice, setNotice] = useState('');
  const [property, setProperty] = useState({ location: '', askingPrice: '', source: '', date: '', priceType: 'asking', documents: 'Not reviewed' });
  const connected = tab === 'equity' || tab === 'mutual_fund';

  useEffect(() => { const t = setTimeout(() => { setSearch(query); setOffset(0); }, 300); return () => clearTimeout(t); }, [query]);
  useEffect(() => {
    if (!connected) { setData(null); setLoading(false); setError(''); return undefined; }
    let cancelled = false, timer;
    const controller = new AbortController();
    setData(null); setLoading(true); setError('');
    const load = async () => {
      const timeout = setTimeout(() => controller.abort(), 25_000);
      try {
        const payload = await getWealthUniverse({ assetClass: tab, q: search, offset, limit: 25 }, controller.signal);
        if (!cancelled) { setData(payload); setError(''); }
      } catch (err) {
        if (!cancelled) { setData(null); setError(err.name === 'AbortError' ? 'Data request timed out. Refresh to retry.' : err.message); }
      } finally {
        clearTimeout(timeout);
        if (!cancelled) {
          setLoading(false);
          if (!controller.signal.aborted) timer = setTimeout(load, tab === 'equity' ? 30_000 : 300_000);
        }
      }
    };
    load();
    return () => { cancelled = true; clearTimeout(timer); controller.abort(); };
  }, [tab, search, offset, refresh, connected]);

  const model = useMemo(() => {
    try { return { rows: compareScenarios(plan, assets), error: null }; }
    catch (err) { return { rows: [], error: err.message }; }
  }, [plan, assets]);
  const chart = model.rows[0]?.path.map((point, i) => Object.fromEntries([
    ['year', point.year], ...model.rows.map(row => [row.id, row.path[i].netWealth]),
  ])) || [];
  const updatePlan = (key, value) => setPlan(prev => ({ ...prev, [key]: value }));
  const begin = (kind = tab, row = null) => {
    setNotice('');
    if (assets.length >= 4) { setNotice('Compare up to four alternatives at a time. Remove one to add another.'); return; }
    setProperty({ location: '', askingPrice: '', source: '', date: '', priceType: 'asking', documents: 'Not reviewed' });
    setDraft({ ...BLANK_ASSET, id: globalThis.crypto.randomUUID(), label: row?.name || '', kind,
      observed: row ? { id: row.id, price: row.price, asOf: row.asOf, source: row.source, status: row.status } : null });
    document.getElementById('wealth-workbench')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  const addDraft = event => {
    event.preventDefault();
    try {
      if (!draft.label.trim()) throw new Error('Name this scenario.');
      compareScenarios(plan, [draft]);
      const evidence = draft.kind === 'property' ? { ...property } : null;
      if (evidence?.askingPrice !== '' && !(Number(evidence.askingPrice) > 0)) throw new Error('Property price must be positive.');
      setAssets(prev => prev.some(a => a.id === draft.id)
        ? prev.map(a => a.id === draft.id ? { ...draft, property: evidence } : a)
        : [...prev, { ...draft, property: evidence }]);
      setDraft(null); setNotice('Scenario added using your assumptions. Market price is not a return forecast.');
    } catch (err) { setNotice(err.message); }
  };
  const exportPlan = () => {
    const body = { model: MODEL_VERSION, generatedAt: new Date().toISOString(), assumptions: plan, assets, results: model.rows,
      limitations: 'User-supplied effective tax rates; no statutory tax calculation, exemptions, indexation, financing or product suitability assessment. Income paid annually on opening asset value. Entry costs included in cost basis. Holding costs not tax deductible in this model. Cash reinvestment uses assumed after-tax FD rate; negative cash requires external funding.' };
    const url = URL.createObjectURL(new Blob([JSON.stringify(body, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = url; a.download = 'agi-wealth-comparison.json'; a.click(); URL.revokeObjectURL(url);
  };

  const loadResearch = async row => {
    setResearchLoading(true); setResearch(null);
    try { setResearch(await getWealthResearch(`research/${row.symbol}`, AbortSignal.timeout(15000))); }
    catch(e) { setResearch({status:'unavailable',reason:e.message,metrics:[]}); }
    finally { setResearchLoading(false); }
  };
  const downloadFile = (body, type, filename) => {
    const url = URL.createObjectURL(new Blob([body], { type }));
    const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const downloadReviewPack = () => downloadFile(JSON.stringify(createReviewPack(workspace, plan, assets), null, 2), 'application/json', 'agi-wealth-review-pack.json');
  const downloadReviewReport = () => downloadFile(renderReviewReport(createReviewPack(workspace, plan, assets)), 'text/html;charset=utf-8', 'agi-wealth-review-report.html');
  const importReviewPack = async file => {
    if (file.size > 2000000) throw new Error('Review pack exceeds 2 MB.');
    const { workspace: imported, plan: importedPlan, assets: importedAssets } = validateReviewPack(JSON.parse(await file.text()));
    setWorkspace(imported); setPlan(importedPlan); setAssets(importedAssets); setDraft(null); setNotice('Saved review pack opened. Results have been recalculated; refresh market observations separately.');
  };
  const saveObservation = row => {
    if (workspace.watchlist.length >= 100 && !workspace.watchlist.some(w=>w.id===row.id)) { setNotice('Watchlist limit is 100. Remove an observation first.'); return; }
    const entry = { id:row.id, name:row.name, assetClass:row.assetClass, price:row.price, asOf:row.asOf, source:row.source };
    setWorkspace(w=>({...w,watchlist:[...w.watchlist.filter(x=>x.id!==row.id),entry]}));
    setNotice(`${row.name} saved to Monitoring with its observation date.`);
  };
  const compareProperty = p => {
    if (assets.length >= 4) { setNotice('Remove a scenario before adding another property.'); return; }
    setPlan(prev=>({...prev,capital:Number(p.price)}));
    setDraft({...BLANK_ASSET,id:globalThis.crypto.randomUUID(),label:p.name,kind:'property',incomeYield:Number(p.rent)/Number(p.price)*100});
    setProperty({location:p.location,askingPrice:p.price,source:p.source,date:p.asOf,priceType:p.priceType,documents:p.legal});
    setNotice('Budget set to the quoted property price. Add purchase costs to the budget and enter return, holding-cost and tax assumptions before comparing.');
    document.getElementById('wealth-workbench')?.scrollIntoView({behavior:'smooth',block:'start'});
  };

  return <div className="wi-page">
    <Helmet><title>Wealth &amp; Opportunity Intelligence | AGI</title></Helmet>
    <div className="wi-shell">
      <header className="wi-header">
        <div><p className="wi-eyebrow">AGARWAL GLOBAL INVESTMENTS / WEALTH RESEARCH</p><h1>Wealth &amp; Opportunity Intelligence</h1><p>Explore investments. Compare income, costs and wealth after tax.</p></div>
        <Link className="wi-link" to="/portfolio">Your portfolio <ArrowUpRight size={16} /></Link>
      </header>

      <PlanningWorkspace workspace={workspace} setWorkspace={setWorkspace} onExport={downloadReviewPack} onReport={downloadReviewReport} onImport={importReviewPack} onCompareProperty={compareProperty} />
      <section className="wi-plan" aria-label="Comparison assumptions">
        <div className="wi-section-title"><h2><SlidersHorizontal size={18} /> Your comparison</h2><span>Illustrative starting inputs · edit for one owner</span></div>
        <div className="wi-input-grid">
          <NumberField label="Capital available (₹)" value={plan.capital} onChange={v => updatePlan('capital', v)} min={1} max={1e12} />
          <NumberField label="Holding period (years)" value={plan.years} onChange={v => updatePlan('years', v)} min={1} max={40} step={1} />
          <NumberField label="FD interest assumption %" value={plan.fdRate} onChange={v => updatePlan('fdRate', v)} max={30} />
          <NumberField label="Effective income tax %" value={plan.incomeTax} onChange={v => updatePlan('incomeTax', v)} max={60} />
          <NumberField label="Inflation assumption %" value={plan.inflation} onChange={v => updatePlan('inflation', v)} max={30} />
        </div>
        <div className="wi-plan-footer"><label><input type="checkbox" checked={plan.reinvest} onChange={e => updatePlan('reinvest', e.target.checked)} /> Reinvest net cash at the assumed after-tax FD rate</label><span>Inputs remain in this page until downloaded or cleared.</span></div>
      </section>

      {model.error ? <p className="wi-error" role="alert">{model.error}</p> : <div className="wi-metrics">
        <div><span>FD first-year income after tax</span><strong>{money(model.rows[0]?.firstYearNetIncome)}</strong></div>
        <div><span>FD wealth after {plan.years} years</span><strong>{money(model.rows[0]?.netWealth)}</strong></div>
        <div><span>FD wealth in today’s rupees</span><strong>{money(model.rows[0]?.realWealth)}</strong></div>
      </div>}

      <section className="wi-panel" aria-labelledby="wi-discover">
        <div className="wi-section-title"><div><p className="wi-eyebrow">01 / DISCOVER</p><h2 id="wi-discover">Investment universe</h2></div><button className="wi-button" disabled={loading || !connected} onClick={() => setRefresh(r => r + 1)}><RefreshCw size={15} /> Refresh</button></div>
        <div className="wi-tabs" aria-label="Asset class">{ASSET_CLASSES.map(([id, label]) => <button key={id} aria-pressed={tab === id} className={tab === id ? 'active' : ''} onClick={() => { setTab(id); setOffset(0); setQuery(''); setSearch(''); }}>{label}</button>)}</div>
        {connected ? <>
          <div className="wi-search-row"><label className="wi-search"><Search size={17} /><input aria-label="Search investment universe" placeholder={tab === 'equity' ? 'Search company, symbol or sector' : 'Search scheme, fund house or category'} value={query} onChange={e => setQuery(e.target.value)} /></label><span>{tab === 'equity' ? 'Shared market feed · 30-second refresh' : 'AMFI · published daily NAV'} · Alphabetical order</span></div>
          {loading ? <p className="wi-empty" role="status">Loading investment data…</p> : error ? <p className="wi-error" role="alert">{error}</p> : <>
            {data?.source?.error && <p className="wi-error">{data.source.error} Last available observations are labelled stale.</p>}
            <div className="wi-table-wrap"><table><thead><tr><th>Investment</th><th>{tab === 'equity' ? 'Sector' : 'Fund house'}</th><th>Price / NAV (₹)</th><th>{tab === 'equity' ? 'Day change' : 'Scheme code'}</th><th>Observation</th><th>Research</th></tr></thead><tbody>
              {data?.items?.map(row => <tr key={row.id}><td><strong>{row.name}</strong><small>{row.symbol || row.category}</small></td><td>{row.sector || row.fundHouse || '—'}</td><td>{row.price == null ? '—' : Number(row.price).toLocaleString('en-IN', { maximumFractionDigits: 4 })}</td><td>{tab === 'equity' ? pct(row.changePct) : row.schemeCode}</td><td><span className={`wi-badge wi-${row.status}`}>{({ live: 'Live', stale: 'Stale / last known', daily: 'Daily NAV', unavailable: 'Unavailable' })[row.status]}</span><small>{stamp(row.asOf)} · {row.source || 'No observation'}</small></td><td><div className="wi-row-actions">{row.researchUrl && <Link to={row.researchUrl}>Research <ArrowUpRight size={13} /></Link>}{tab === 'equity' && <button disabled={researchLoading} onClick={() => loadResearch(row)}>Financial snapshot</button>}<button onClick={() => begin(tab, row)}>Compare</button><button onClick={() => saveObservation(row)}>Save observation</button></div></td></tr>)}
              {!data?.items?.length && <tr><td colSpan={6}>No matching investments. Try another search.</td></tr>}
            </tbody></table></div>
            <div className="wi-pagination"><span>{data?.total || 0} matching investments · prices do not imply expected returns</span><div><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous</button><button disabled={offset + 25 >= (data?.total || 0)} onClick={() => setOffset(offset + 25)}>Next</button></div></div>
          </>}
        </> : <div className="wi-gap"><Building2 size={25} /><div><h3>{GAPS[tab][0]}</h3><p>{GAPS[tab][1]}</p><button className="wi-button" onClick={() => begin(tab)}><Plus size={15} /> {tab === 'property' ? 'Compare a property quote' : 'Add an investment scenario'}</button></div></div>}
      </section>

      {researchLoading && <p className="wi-notice" role="status">Loading stored company research…</p>}
      {research && <section className="wi-panel" aria-label="Company financial snapshot"><div className="wi-section-title"><h2>{research.name || research.symbol || 'Company research'}</h2><button className="wi-button" onClick={()=>setResearch(null)}>Close snapshot</button></div><p className="wi-note">{research.status} · {research.source || 'No source'} · Source as of {research.sourceAsOf || 'unavailable'} · Generated {stamp(research.generatedAt)}</p>{research.reason && <p className="wi-notice">{research.reason}</p>}<div className="wi-table-wrap"><table><thead><tr><th>Metric</th><th>Stored value</th><th>Reference position</th></tr></thead><tbody>{research.metrics?.map(m=><tr key={m.metric}><td>{m.metric.replaceAll('_',' ')}</td><td>{m.value}</td><td>{m.position || 'Not available'}</td></tr>)}</tbody></table></div><p className="wi-note">{research.caveat}</p>{research.symbol && <Link className="wi-link" to={`/research/stocks/${encodeURIComponent(research.symbol)}`}>Open full company research ↗</Link>}</section>}

      <section className="wi-panel" id="wealth-workbench" aria-labelledby="wi-compare">
        <div className="wi-section-title"><div><p className="wi-eyebrow">02 / COMPARE</p><h2 id="wi-compare">After-tax scenario workbench</h2></div><div className="wi-actions"><button className="wi-button" onClick={() => begin()}><Plus size={15} /> Add scenario</button><button className="wi-button" disabled={!!model.error} onClick={exportPlan}><Download size={15} /> Download comparison</button></div></div>
        <p className="wi-note">All return and tax inputs are assumptions. Enter effective rates inclusive of applicable surcharge and cess with your CA. Family income is not treated as one taxpayer. This is a scenario calculation, not a tax return or investment recommendation.</p>
        {notice && <p className="wi-notice" role="status">{notice}</p>}
        {draft && <form className="wi-draft" onSubmit={addDraft}>
          <div className="wi-section-title"><h3>New scenario</h3><button type="button" className="wi-icon-button" aria-label="Close scenario" onClick={() => setDraft(null)}><X size={18} /></button></div>
          <div className="wi-input-grid wi-three"><label className="wi-field"><span>Scenario name</span><input required maxLength={160} value={draft.label} onChange={e => setDraft({ ...draft, label: e.target.value })} /></label><label className="wi-field"><span>Asset class</span><select value={draft.kind} onChange={e => setDraft({ ...draft, kind: e.target.value })}>{ASSET_CLASSES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label></div>
          {draft.observed && <p className="wi-note">Reference observation: {money(draft.observed.price)} · {stamp(draft.observed.asOf)} · {draft.observed.source || 'Unavailable'}. Enter your scenario assumptions separately.</p>}
          <div className="wi-input-grid wi-three">{FIELD_LABELS.map(([key, label, min, max]) => <NumberField key={key} label={label} min={min} max={max} value={draft[key]} onChange={v => setDraft({ ...draft, [key]: v })} />)}</div>
          {draft.kind === 'property' && <fieldset className="wi-property"><legend>Property evidence — supplied by you</legend><div className="wi-input-grid wi-three">
            <label className="wi-field"><span>Location / property</span><input maxLength={200} value={property.location} onChange={e => setProperty({ ...property, location: e.target.value })} /></label>
            <NumberField label="Whole-property price (₹, optional)" value={property.askingPrice} onChange={v => setProperty({ ...property, askingPrice: v })} min={1} />
            <label className="wi-field"><span>Price evidence type</span><select value={property.priceType} onChange={e => setProperty({ ...property, priceType: e.target.value })}><option value="asking">Asking price</option><option value="registered">Registered transaction value</option><option value="guidance">Circle / guidance value</option><option value="estimate">User valuation estimate</option></select></label>
            <label className="wi-field"><span>Quote / source reference</span><input maxLength={500} value={property.source} onChange={e => setProperty({ ...property, source: e.target.value })} /></label>
            <label className="wi-field"><span>Evidence date</span><input type="date" max={new Date().toISOString().slice(0, 10)} value={property.date} onChange={e => setProperty({ ...property, date: e.target.value })} /></label>
            <label className="wi-field"><span>Document review status</span><select value={property.documents} onChange={e => setProperty({ ...property, documents: e.target.value })}><option>Not reviewed</option><option>Professional review pending</option><option>User reports professional review completed</option></select></label>
          </div><p className="wi-note">The model uses the capital budget above. A property quote is evidence, not an automatic change to your budget. Verify title, access, permitted use and purchase eligibility separately.</p></fieldset>}
          <p className="wi-note">Zero defaults are placeholders to edit. Growth excludes cash distributions; do not enter total return as price growth and count income twice.</p>
          <button className="wi-button wi-primary" type="submit">Add to comparison</button>
        </form>}
        {!assets.length && !draft && <div className="wi-empty"><Landmark size={24} /><h3>How much must an alternative earn to beat your FD?</h3><p>Add a property, fund, bond or other scenario to compare it with the same capital and holding period.</p></div>}
        {!!assets.length && !model.error && <>
          <div className="wi-chart" aria-label="Projected wealth after tax by year"><ResponsiveContainer width="100%" height={280}><LineChart data={chart} margin={{ top: 15, right: 25, bottom: 5, left: 10 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="year" tickFormatter={v => `Year ${v}`} /><YAxis tickFormatter={compact} width={85} /><Tooltip formatter={(v, name) => [money(v), name]} labelFormatter={v => `If sold at end of year ${v}`} />{model.rows.map((row, i) => <Line key={row.id} dataKey={row.id} name={row.label} stroke={COLORS[i]} strokeWidth={2} dot={false} />)}</LineChart></ResponsiveContainer></div>
          <div className="wi-table-wrap"><table><thead><tr><th>Scenario</th><th>First-year net income</th><th>Exit wealth after tax</th><th>Tax paid incl. exit</th><th>Total costs</th><th>Difference vs FD</th><th>Annualized wealth growth</th></tr></thead><tbody>{model.rows.map((row, i) => <tr key={row.id}><td><strong style={{ color: COLORS[i] }}>{row.label}</strong>{i > 0 && <div className="wi-actions"><button className="wi-text-button" onClick={() => { const asset = assets.find(a => a.id === row.id); setDraft({ ...asset }); if (asset.property) setProperty({ ...asset.property }); }}>Edit</button><button className="wi-text-button" onClick={() => { setAssets(prev => prev.filter(a => a.id !== row.id)); if (draft?.id === row.id) setDraft(null); }}>Remove</button></div>}</td><td>{money(row.firstYearNetIncome)}</td><td>{money(row.netWealth)}<small>{money(row.realWealth)} in today’s rupees</small></td><td>{money(row.totalTax)}</td><td>{money(row.totalCosts)}</td><td>{money(row.vsFd)}</td><td>{pct(row.annualized)}</td></tr>)}</tbody></table></div>
          {model.rows.filter(row => row.cashShortfall > 0).map(row => <p className="wi-error" key={row.id}>{row.label}: up to {money(row.cashShortfall)} of external cash is needed for holding costs. This reduces reported net wealth; financing costs are not modelled.</p>)}
          {assets.filter(a => a.kind === 'property').map(asset => {
            const threshold = breakEvenGrowth(plan, asset);
            const required = Number(asset.property?.askingPrice) * (1 + Number(asset.entryCost) / 100);
            return <div className="wi-property-result" key={asset.id}><Building2 size={22} /><div><h3>{asset.label}: {threshold == null ? 'no break-even found in the model range' : `${pct(threshold)} annual appreciation to match the FD`}</h3><p>This is a break-even calculation using your income, costs and tax assumptions; it is not an appreciation forecast.</p><small>{asset.property?.location || 'Location not supplied'} · {asset.property?.priceType || 'No'} price evidence · {asset.property?.date || 'Undated'} · {asset.property?.documents || 'Not reviewed'}</small>{required > 0 && <p>Whole-property acquisition estimate: {money(required)}. {required > Number(plan.capital) ? `Budget shortfall: ${money(required - Number(plan.capital))}. The model does not finance this purchase.` : 'Within the capital budget; the comparison still models the full budget.'}</p>}</div></div>;
          })}
        </>}
        <details className="wi-method"><summary>Calculation method and limits</summary><p>All scenarios start with the same total budget. Entry costs reduce the amount invested. Cash yield and annual costs use each year’s opening asset value. Price growth is applied annually. Positive cash either earns the assumed after-tax FD rate or remains uninvested. Uninvested cash is included in final wealth and is not assumed spent.</p><p>Exit wealth equals sale value minus selling costs, assumed tax on positive gains, plus accumulated cash. Cost basis includes all entry costs as a modelling assumption. Losses receive no tax credit. Holding costs receive no deduction. No tax slabs, allowances, indexation, exemptions, debt financing, variable rates or transaction timing are calculated. Annualized wealth growth is not a security’s quoted yield or an IRR with interim withdrawals.</p><p>Buying land may reduce future interest income; that does not reverse tax on interest already earned. Check current rules and the actual owner’s position with a CA. Product-specific taxation can differ materially from these simplified assumptions.</p></details>
      </section>
      <footer className="wi-footer"><span>Research and scenario analysis · No automatic investment execution</span><Link to="/portfolio">Open Portfolio Intelligence <ArrowUpRight size={14} /></Link></footer>
    </div>
  </div>;
}
