import FundDirectory from './FundDirectory';
import TaxIntelligence from './TaxIntelligence';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { householdSummary, fundOverlap, propertySummary, bondCashFlows, maturityLadder, monitoringAlerts, safeUrl } from '@/lib/wealthPlanning';
import { RECORD_SCHEMAS, blankRecord, validateRecord } from '@/lib/wealthWorkspace';
import { getWealthResearch } from '@/lib/wealthIntelligenceApi';
import { estimateOrdinaryTax, TAX_RULE } from '@/lib/wealthTax';
const money = value => value == null ? '—' : new Intl.NumberFormat('en-IN', { style:'currency', currency:'INR', maximumFractionDigits:0 }).format(value);
const percent = value => value == null ? '—' : `${value.toFixed(2)}%`;
const TITLES = { household:'Household', funds:'Fund research', properties:'Property evidence', bonds:'Fixed income', tax:'Tax review', monitor:'Monitoring' };
function Source({ url }) { const href = safeUrl(url); return href ? <a className="wi-link" href={href} target="_blank" rel="noopener noreferrer">Source ↗</a> : <span>No source</span>; }
function Table({ headers, children }) { return <div className="wi-table-wrap"><table><thead><tr>{headers.map(h => <th key={h}>{h}</th>)}</tr></thead><tbody>{children}</tbody></table></div>; }
function Metric({ label, value }) { return <div><span>{label}</span><strong>{value}</strong></div>; }
function Editor({ kind, draft, setDraft, onSave, onClose, people }) {
  return <form className="wi-draft" onSubmit={onSave}><h3>{draft.name ? `Edit ${draft.name}` : `Add ${kind === 'people' ? 'owner' : 'record'}`}</h3><div className="wi-input-grid wi-three">
    {RECORD_SCHEMAS[kind].map(f => <label className={`wi-field ${f.type === 'textarea' ? 'wi-wide' : ''}`} key={f.key}><span>{f.label}</span>
      {f.type === 'select' || f.type === 'owner' ? <select value={draft[f.key]} required onChange={e => setDraft({ ...draft, [f.key]:e.target.value })}>{f.type === 'owner' ? <><option value="">Select owner</option>{people.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</> : f.options.map(o => <option key={o} value={o}>{o}</option>)}</select>
        : f.type === 'textarea' ? <textarea rows={5} maxLength={30000} value={draft[f.key]} onChange={e => setDraft({ ...draft, [f.key]:e.target.value })} />
          : <input type={f.type} step="any" min={f.type === 'number' ? 0 : undefined} maxLength={1000} value={draft[f.key]} onChange={e => setDraft({ ...draft, [f.key]:e.target.value })} />}
    </label>)}
  </div><div className="wi-actions"><button className="wi-button wi-primary" type="submit">Save record</button><button className="wi-button" type="button" onClick={onClose}>Cancel</button></div></form>;
}
export default function PlanningWorkspace({ workspace, setWorkspace, onExport, onReport, onImport, onCompareProperty }) {
  const [tab, setTab] = useState('household'), [editor, setEditor] = useState(null), [draft, setDraft] = useState(null), [error, setError] = useState('');
  const [feed, setFeed] = useState(null), [feedLoading, setFeedLoading] = useState(false);
  const loadEvidence = async () => {
    setFeedLoading(true);
    try { setFeed(await getWealthResearch('evidence', AbortSignal.timeout(15000))); }
    catch(e) { setFeed({status:'unavailable',note:e.message,records:[]}); }
    finally { setFeedLoading(false); }
  };
  const addEvidence = item => {
    try {
      const row = validateRecord(item.kind, { ...item.record, id:crypto.randomUUID() }, workspace);
      if (workspace[item.kind].length >= 500) throw new Error('Record limit reached.');
      setWorkspace(w=>({...w,[item.kind]:[...w[item.kind],row]})); setError('');
      setFeed(f=>({...f,records:f.records.filter(x=>x!==item)}));
    } catch(e) {setError(e.message);}
  };
  const [now, setNow] = useState(Date.now), [fundA, setFundA] = useState(''), [fundB, setFundB] = useState('');
  const summary = useMemo(() => householdSummary(workspace), [workspace]);
  const alerts = useMemo(() => monitoringAlerts(workspace, now), [workspace, now]);
  const groups = useMemo(() => propertySummary(workspace.properties, now), [workspace.properties, now]);
  const ladder = useMemo(() => maturityLadder(workspace.bonds), [workspace.bonds]);
  const overlap = useMemo(() => {
    const a = workspace.funds.find(f => f.id === fundA), b = workspace.funds.find(f => f.id === fundB);
    return a && b && a.id !== b.id ? fundOverlap(a, b) : null;
  }, [workspace.funds, fundA, fundB]);
  const open = (kind, record) => { setEditor(kind); setDraft(record ? {...record} : blankRecord(kind)); setError(''); };
  const save = event => {
    event.preventDefault();
    try { if(workspace[editor].length >= 500 && !workspace[editor].some(x=>x.id===draft.id)) throw new Error('Record limit reached.'); const row = validateRecord(editor, draft, workspace); setWorkspace(w => ({ ...w, [editor]: w[editor].some(x => x.id === row.id) ? w[editor].map(x => x.id === row.id ? row : x) : [...w[editor], row] })); setDraft(null); setEditor(null); setError(''); }
    catch (e) { setError(e.message); }
  };
  const remove = (kind, id) => {
    if (kind === 'people' && workspace.holdings.some(h => h.ownerId === id)) { setError('Reassign or remove this owner’s holdings first.'); return; }
    setWorkspace(w => ({ ...w, [kind]: w[kind].filter(r => r.id !== id) }));
  };
  const actions = (kind, row) => <div className="wi-actions"><button className="wi-text-button" onClick={() => open(kind, row)}>Edit</button><button className="wi-text-button" onClick={() => remove(kind, row.id)}>Remove</button></div>;
  const add = (kind, label) => <button className="wi-button" onClick={() => open(kind)}>+ {label}</button>;
  return <section className="wi-panel" aria-labelledby="wi-planning-title">
    <div className="wi-section-title"><div><p className="wi-eyebrow">YOUR FINANCIAL WORKSPACE</p><h2 id="wi-planning-title">Plan, research and monitor</h2></div><div className="wi-actions"><button className="wi-button" onClick={()=>{try{onReport();setError('');}catch(e){setError(e.message);}}}>Download CA report</button><button className="wi-button" onClick={()=>{try{onExport();setError('');}catch(e){setError(e.message);}}}>Save editable pack</button><label className="wi-button">Open saved pack<input className="wi-file" type="file" accept="application/json,.json" onChange={async e => { const file = e.target.files?.[0]; if (file) { try { await onImport(file); setError(''); setEditor(null); setDraft(null); } catch (err) { setError(err.message); } } e.target.value = ''; }} /></label></div></div>
    <p className="wi-note">Private working session. Download a review pack to keep your records; refreshing or leaving this page clears them. The file contains financial information. No PAN or account numbers are needed.</p>
    <nav className="wi-tabs" aria-label="Planning modules">{Object.entries(TITLES).map(([key,label]) => <button key={key} className={tab === key ? 'active' : ''} aria-pressed={tab === key} onClick={() => {setTab(key); setEditor(null); setDraft(null); setError('');}}>{label}{key === 'monitor' && alerts.length ? ` (${alerts.length})` : ''}</button>)}</nav>
    {['funds','properties','bonds','monitor'].includes(tab) && <div className="wi-feed"><button className="wi-button" disabled={feedLoading} onClick={loadEvidence}>{feedLoading ? 'Loading sources…' : 'Check connected research sources'}</button>{feed && <><p className="wi-note">{feed.provider || 'Evidence feed'} · {feed.status} · {feed.note}</p>{feed.records?.filter(item=>item.kind === (tab === 'monitor' ? 'events' : tab)).map(item=><div className="wi-notice" key={`${item.kind}:${item.record.id}`}><strong>{item.record.name}</strong> · {item.record.asOf || item.record.due} · {item.stale ? 'Stale — reconfirm before use' : 'Provider evidence'} <Source url={item.record.source}/> <button className="wi-button" onClick={()=>addEvidence(item)}>Add to research book</button></div>)}</>}</div>}
    {error && <p className="wi-error" role="alert">{error}</p>}
    {editor && <Editor kind={editor} draft={draft} setDraft={setDraft} onSave={save} onClose={() => {setEditor(null);setDraft(null);}} people={workspace.people} />}
    {tab === 'household' && <>
      <div className="wi-metrics"><Metric label="Recorded net worth" value={money(summary.netWorth)} /><Metric label="Annual gross cash income" value={money(summary.grossIncome)} /><Metric label="Cash reserve target" value={money(summary.reserveTarget)} /></div>
      <div className="wi-input-grid wi-three"><label className="wi-field"><span>Monthly household spending (₹)</span><input type="number" min="0" value={workspace.expenses} onChange={e => { const n = Number(e.target.value); if(Number.isFinite(n) && n >= 0 && n <= 1e12) setWorkspace(w => ({...w,expenses:n})); }} /></label><label className="wi-field"><span>Months of spending to reserve</span><input type="number" min="0" max="60" value={workspace.reserveMonths} onChange={e => {const n=Number(e.target.value); if(Number.isFinite(n)&&n>=0&&n<=60)setWorkspace(w=>({...w,reserveMonths:n}));}} /></label></div>
      <div className="wi-actions">{add('people','Add legal owner')}{add('holdings','Add asset or income')}</div>
      <p className="wi-note">Enter only each owner’s share; split joint assets into separate records without double-counting. Gross income is not spendable income or taxable income. Loans shown here are balances; include debt payments in spending.</p>
      <Table headers={['Owner','Taxpayer / residency','Assets','Debt','Annual gross income','Actions']}>{summary.people.map(p=><tr key={p.id}><td>{p.name}</td><td>{p.entity} / {p.residency}</td><td>{money(p.assets)}</td><td>{money(p.liabilities)}</td><td>{money(p.income)}</td><td>{actions('people',p)}</td></tr>)}</Table>
      {!workspace.people.length && <p className="wi-empty">Add an owner to begin. Family income is never pooled into one tax calculation.</p>}
      <Table headers={['Asset / income','Owner','Class / geography','Value','Annual gross income','Maturity','Actions']}>{workspace.holdings.map(h=><tr key={h.id}><td>{h.name}</td><td>{workspace.people.find(p=>p.id===h.ownerId)?.name}</td><td>{h.kind}<small>{h.location}</small></td><td>{money(Number(h.value))}</td><td>{money(Number(h.income))}</td><td>{h.maturity || '—'}</td><td>{actions('holdings',h)}</td></tr>)}</Table>
      {!!summary.concentration.length && <div className="wi-allocation">{summary.concentration.map(c=><div key={c.kind}><span>{c.kind} · {percent(c.weight)}</span><progress max="100" value={c.weight} /></div>)}</div>}
    </>}
    {tab === 'funds' && <>
      <FundDirectory />
      <div className="wi-section-title"><h3>Disclosure-based fund comparison</h3>{add('funds','Add AMC disclosure')}</div>
      <p className="wi-note">Search Upstox funds above. Add dated AMC holdings and expenses here to compare underlying exposure. Use the same identifiers in both funds. A daily NAV does not supply holdings, fees or future returns.</p>
      <Table headers={['Fund / plan','Expense ratio','Risk','Disclosure','Actions']}>{workspace.funds.map(f=><tr key={f.id}><td>{f.name}<small>AMFI {f.schemeCode}</small></td><td>{percent(Number(f.expense))}</td><td>{f.risk}</td><td>{f.asOf}<br/><Source url={f.source}/></td><td>{actions('funds',f)}</td></tr>)}</Table>
      <div className="wi-input-grid wi-three">{[[fundA,setFundA,'First fund'],[fundB,setFundB,'Second fund']].map(([value,setter,label])=><label className="wi-field" key={label}><span>{label}</span><select value={value} onChange={e=>setter(e.target.value)}><option value="">Choose added disclosure</option>{workspace.funds.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></label>)}</div>
      {overlap && <div className="wi-property-result"><div><h3>{percent(overlap.overlap)} disclosed portfolio overlap</h3><p>Coverage: {percent(overlap.coverageA)} / {percent(overlap.coverageB)}. {overlap.partial ? 'Partial holdings: this is a lower bound, not total overlap.' : 'Based on supplied disclosure weights.'} {!overlap.comparableDates && 'Disclosure dates differ; changes between dates can distort the comparison.'}</p><p>{overlap.shared.map(r=>`${r.id}: ${percent(r.overlap)}`).join(' · ') || 'No matching identifiers in the supplied holdings.'}</p></div></div>}
      <p className="wi-note">Company financials and valuation are available through each equity’s Research link below and the <Link className="wi-link" to="/valuation-terminal">existing valuation terminal</Link>. Automated AMC disclosure ingestion and fund return histories need a licensed or permitted source.</p>
    </>}
    {tab === 'properties' && <>
      <div className="wi-section-title"><h3>Micro-market evidence book</h3>{add('properties','Add property evidence')}</div>
      <p className="wi-note">Start with locations you know: Haldwani, Almora or a selected NCR micro-market. These are research areas, not recommended investments. Evidence entered here is user-supplied, not an AGI-verified listing.</p>
      <Table headers={['Location / type','Evidence type','Records','₹ / sq ft range','Median ₹ / sq ft']}>{groups.map(g=><tr key={`${g.location}-${g.propertyType}-${g.priceType}`}><td>{g.location}<small>{g.propertyType}</small></td><td>{g.priceType}</td><td>{g.count}</td><td>{money(g.low)}–{money(g.high)}</td><td>{money(g.median)}</td></tr>)}</Table>
      <p className="wi-note">These are unadjusted comparable summaries. Changes in property mix are not appreciation. Asking, registered, guidance and estimated values are kept separate. Evidence older than 180 days triggers a review alert.</p>
      <Table headers={['Property','Price / area','Gross rental yield','Evidence','Catalyst / legal review','Actions']}>{workspace.properties.map(p=><tr key={p.id}><td>{p.name}<small>{p.location}</small></td><td>{money(Number(p.price))}<small>{p.area} sq ft · {p.priceType}</small></td><td>{percent(Number(p.rent)/Number(p.price)*100)}</td><td>{p.asOf}<br/><Source url={p.source}/></td><td>{p.stage}<small>{p.driver}</small><small>{p.legal}</small></td><td><button className="wi-button" onClick={()=>onCompareProperty(p)}>Compare with FD</button>{actions('properties',p)}</td></tr>)}</Table>
      {!workspace.properties.length && <p className="wi-empty">No property evidence added. Verified transaction and availability feeds are not yet connected.</p>}
    </>}
    {tab === 'bonds' && <>
      <div className="wi-section-title"><h3>Fixed-income cash flows and maturity ladder</h3>{add('bonds','Add quoted instrument')}</div>
      <p className="wi-note">Enter the actual payment schedule and all-in settlement cost. Returns assume every scheduled payment is made. Rate changes, default, early redemption and reinvestment are not forecast. Tax inputs are your effective-rate assumptions; discount and accrued-interest treatment need review.</p>
      <Table headers={['Instrument / issuer','Invested','Net future receipts','After-tax dated IRR','Quote / credit','Actions']}>{workspace.bonds.map(b=>{const r=bondCashFlows(b);return <tr key={b.id}><td>{b.name}<small>{b.issuer}</small></td><td>{money(r.invested)}</td><td>{money(r.netReceipts)}</td><td>{percent(r.afterTaxIrr)}</td><td>{b.asOf}<small>{b.credit}</small><Source url={b.source}/></td><td>{actions('bonds',b)}<details><summary>Payments</summary>{r.schedule.map(f=><p key={f.date}>{f.date}: {money(f.net)} net</p>)}</details></td></tr>;})}</Table>
      {!!ladder.length && <><h3 className="wi-subtitle">Calendar-year cash availability</h3><Table headers={['Year','Gross coupons','Returned principal','Assumed tax','Net receipts']}>{ladder.map(l=><tr key={l.year}><td>{l.year}</td><td>{money(l.coupon)}</td><td>{money(l.principal)}</td><td>{money(l.tax)}</td><td>{money(l.net)}</td></tr>)}</Table></>}
      {!workspace.bonds.length && <p className="wi-empty">No dated instruments yet. Executable dealer quotes and current bank rate feeds require a provider connection.</p>}
    </>}
    {tab === 'tax' && <>
      <TaxIntelligence people={workspace.people} />
      <h3>Owner-by-owner ordinary-income estimate</h3><p className="wi-note">Available rule: FY 2025–26 / AY 2026–27. Professional review pending. Current Tax Year 2026–27 is blocked until its own rule package is verified. Enter CA-computed taxable income after deductions for each regime separately; gross household income is not a substitute.</p>
      <Table headers={['Owner / year','Status','Tax estimate incl. cess','Credits','Balance / (excess credits)','Actions']}>{workspace.people.map(p=>{let r;try{r=estimateOrdinaryTax(p);}catch(e){r={total:null,reasons:[e.message]};}return <tr key={p.id}><td>{p.name}<small>{p.year} · {p.regime}</small></td><td>{r.total==null?'Review required':'Estimate · CA review pending'}<small>{r.reasons?.join(' ')}</small></td><td>{money(r.total)}</td><td>{money(r.credits)}</td><td>{money(r.balance)}</td><td>{actions('people',p)}{r.total!=null&&<details><summary>Calculation</summary><p>Slab tax {money(r.base)}; rebate {money(r.rebate)}; rebate relief {money(r.rebateRelief)}; surcharge {money(r.surcharge)}; surcharge relief {money(r.marginalRelief)}; cess {money(r.cess)}.</p></details>}</td></tr>;})}</Table>
      <p className="wi-note">Rule {TAX_RULE.id} · checked {TAX_RULE.checkedAt} · <Source url={TAX_RULE.source}/> · <a className="wi-link" href={TAX_RULE.transitionSource} target="_blank" rel="noopener noreferrer">New Act transition ↗</a></p>
      <details className="wi-method"><summary>CA review checklist</summary><p>Confirm ownership and source of funds, residency, income year, regime eligibility, taxable income heads, deductions, losses, special-rate income and tax credits. A property purchase does not cancel tax already earned on FD interest. Review capital-gain exemptions, clubbing, GST and business deductions separately; none are automatically applied here.</p></details>
    </>}
    {tab === 'monitor' && <>
      <div className="wi-section-title"><h3>Review queue</h3><div className="wi-actions">{add('events','Add dated review')}<button className="wi-button" onClick={()=>setNow(Date.now())}>Refresh alerts</button></div></div>
      <p className="wi-note">Evaluated when this workspace changes or you refresh alerts. This session does not send notifications or run background checks. Regulation and infrastructure reviews below use the sources you record.</p>
      <div className="wi-alert-list">{alerts.map(a=><div className={`wi-notice ${a.severity==='stale'?'wi-stale':''}`} key={a.id}><strong>{a.title}</strong><p>{a.detail}</p></div>)}</div>
      {!alerts.length && <p className="wi-empty">No alerts from the records currently entered. This does not mean every risk has been assessed.</p>}
      <Table headers={['Review action','Due','Affected decisions','Status / source','Actions']}>{workspace.events.map(e=><tr key={e.id}><td>{e.name}</td><td>{e.due}</td><td>{e.impact}</td><td>{e.status}<br/><Source url={e.source}/></td><td>{actions('events',e)}</td></tr>)}</Table>
      <h3 className="wi-subtitle">Saved market observations</h3><Table headers={['Investment','Saved price / NAV','As of','Source','Actions']}>{workspace.watchlist.map(w=><tr key={w.id}><td>{w.name}</td><td>{money(w.price)}</td><td>{w.asOf || 'Unavailable'}</td><td>{w.source || 'Unavailable'}</td><td><button className="wi-text-button" onClick={()=>remove('watchlist',w.id)}>Remove</button></td></tr>)}</Table>
    </>}
  </section>;
}
