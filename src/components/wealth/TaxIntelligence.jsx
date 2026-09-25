import { useMemo, useState } from 'react';
import { BLANK_TAX_CASE, scanTaxOpportunities } from '@/lib/taxOpportunity';
import { EVIDENCE_CATEGORIES, parseEvidenceCsv, mapEvidenceCsv, parseUpstoxFundOrders, reconcileTaxEvidence, restoreTaxReview } from '@/lib/taxEvidence';
import { housePropertySchedule } from '@/lib/taxProperty';
const money = n => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(n);
const FIELDS = [
  ['salary','Salary/pension after eligible allowances, before standard deduction (₹)'],
  ['depositInterest','Annual FD / eligible deposit interest (₹)'],
  ['savingsInterest','Annual savings-account interest (₹)'],
  ['eligible80c','Eligible 80C/80CCC/80CCD(1) paid in the year (₹)'],
  ['eligibleNps','Additional personal NPS paid, excluding the 80C amount (₹)'],
  ['eligible80d','Health premium potentially eligible under 80D (₹)'],
];
const TYPES = [
  ['hasRental','Rental property or hotel-related income'],['hasGains','Shares, funds, property or other capital gains'],
  ['hasBusiness','Business or professional income'],['hasForeign','Foreign income or overseas assets'],
  ['otherIncome','Dividends, losses or other special income'],
];
const download = (name,value) => {const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
export default function TaxIntelligence({ people=[] }) {
  const [form,setForm] = useState({...BLANK_TAX_CASE});
  const [ownerId,setOwnerId] = useState('');
  const [evidence,setEvidence] = useState([]), [staged,setStaged] = useState(null), [importError,setImportError] = useState('');
  const [mapping,setMapping] = useState({amount:'',credit:'',category:'',reference:'',date:'',defaultCategory:'salary',source:''});
  const [property,setProperty] = useState({rent:'',municipal:'',interest:'',confirmedHouseProperty:false});
  const update = (key,value) => setForm(previous=>({...previous,[key]:value}));
  const reconciled = useMemo(()=>reconcileTaxEvidence(evidence,ownerId||'session',form.year,form),[evidence,ownerId,form]);
  const scoped = evidence.filter(r=>r.ownerId===(ownerId||'session')&&r.year===form.year);
  const blockedByEvidence = scoped.length>0 && (reconciled.unmatched>0 || reconciled.warnings.length>0 ||
    reconciled.comparisons.some(c=>c.status==='difference') || reconciled.missingCategories.length>0);
  const effectiveForm={...form,recordsConfirmed:form.recordsConfirmed&&!blockedByEvidence,
    hasRental:form.hasRental||reconciled.missingCategories.includes('rent'),
    hasBusiness:form.hasBusiness||reconciled.missingCategories.includes('business'),
    hasGains:form.hasGains||reconciled.missingCategories.includes('capital_gains')||scoped.some(r=>r.category==='investment'&&r.transactionType==='SELL'&&r.status==='COMPLETED'),
    otherIncome:form.otherIncome||reconciled.missingCategories.some(c=>['dividend','other'].includes(c))};
  const result = useMemo(()=>{try{return {value:scanTaxOpportunities(effectiveForm)};}catch(e){return {error:e.message};}},[form,reconciled,blockedByEvidence,scoped]);
  const report = result.value;
  const propertyResult=useMemo(()=>{if(!form.hasRental)return null;try{return {value:housePropertySchedule(property)};}catch(e){return {error:e.message};}},[form.hasRental,property]);
  const importFile = async (file,kind) => {
    setImportError('');setStaged(null);
    try {
      if(file.size>2_000_000)throw new Error('Choose a file smaller than 2 MB.');
      const raw=await file.text();
      if(kind==='orders'){
        const orders=parseUpstoxFundOrders(raw,{ownerId:ownerId||'session',year:form.year,batchId:crypto.randomUUID()});
        if(evidence.length+orders.length>1000)throw new Error('Evidence limit: 1,000 records.');
        setEvidence(previous=>[...previous,...orders]);
      }else {setStaged(parseEvidenceCsv(raw));setMapping({amount:'',credit:'',category:'',reference:'',date:'',defaultCategory:'salary',source:file.name.slice(0,120)});}
    }catch(e){setImportError(e.message);}
  };
  const addCsv = () => {
    try {
      const rows=mapEvidenceCsv(staged,{...mapping,ownerId:ownerId||'session',year:form.year,batchId:crypto.randomUUID()});
      if(evidence.length+rows.length>1000)throw new Error('Evidence limit: 1,000 records.');
      setEvidence(previous=>[...previous,...rows]);setStaged(null);setImportError('');
    }catch(e){setImportError(e.message);}
  };
  const switchOwner = next => {setOwnerId(next);setForm({...BLANK_TAX_CASE});setStaged(null);setProperty({rent:'',municipal:'',interest:'',confirmedHouseProperty:false});};
  const exportReport = () => download(`agi-tax-review-${form.year}.json`,{version:1,createdAt:new Date().toISOString(),owner:people.find(p=>p.id===ownerId)?.name||'Unassigned session case',
    year:form.year,legalBasis:form.year==='2026-27'?'Income Tax Act 2025; Form 168':'Income Tax Act 1961; AIS / 26AS',
    case:form,propertyInputs:property,propertySchedule:propertyResult?.value||null,reconciliation:reconciled,review:report,evidence:scoped,
    limitations:'Unverified records and investment orders do not establish taxable income, gain or deductible expense. No return has been filed. Current-year tax calculation and complex income require separate verification.'});
  return <div className="wi-tax-intelligence">
    <div className="wi-section-title"><div><p className="wi-eyebrow">AGI TAX INTELLIGENCE · EVIDENCE WORKSPACE</p><h3>Build a defensible tax review</h3></div><div className="wi-actions"><button className="wi-button" onClick={exportReport}>Download tax review</button><label className="wi-button">Open tax review<input className="wi-file" type="file" accept=".json,application/json" onChange={async e=>{const f=e.target.files?.[0];if(f)try{const restored=restoreTaxReview(await f.text(),ownerId||'session');setForm(restored.form);setEvidence(restored.evidence);setStaged(null);setProperty(restored.property);setImportError('Recheck imported rows and eligibility before using an estimate.');}catch(err){setImportError(err.message);}e.target.value='';}} /></label><button className="wi-button" onClick={()=>{setForm({...BLANK_TAX_CASE});setEvidence([]);setStaged(null);setImportError('');setProperty({rent:'',municipal:'',interest:'',confirmedHouseProperty:false});}}>Clear session</button></div></div>
    <p className="wi-note">One resident individual and one income year at a time. Files stay in this page session; use Download tax review to save your work. Imports are evidence for review, not automatically accepted taxable income or a filed return.</p>
    {!!people.length && <label className="wi-field"><span>Legal owner for this case and imports</span><select value={ownerId} onChange={e=>switchOwner(e.target.value)}><option value="">Separate unnamed session case</option>{people.filter(p=>p.entity==='individual').map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>}
    <div className="wi-input-grid wi-three">
      <label className="wi-field"><span>Income year</span><select value={form.year} onChange={e=>update('year',e.target.value)}><option value="2026-27">Tax Year 2026–27 · planning</option><option value="2025-26">FY 2025–26 / AY 2026–27 · claim review</option></select></label>
      <label className="wi-field"><span>Age at end of income year</span><input type="number" min="18" max="120" value={form.age} onChange={e=>update('age',e.target.value)} placeholder="Age" /></label>
      {FIELDS.map(([key,label])=><label className="wi-field" key={key}><span>{label}</span><input type="number" min="0" step="0.01" value={form[key]} onChange={e=>update(key,e.target.value)} placeholder="Enter 0 if none" /></label>)}
    </div>
    <p className="wi-note">Deduction amounts refer to payments made in the selected year. FY 2025–26 is already over; a payment made today cannot be added to that year's claim. Leave unknown amounts blank. The health premium is flagged for review and excluded from the numerical estimate.</p>
    <div className="wi-input-grid wi-three">{TYPES.map(([key,label])=><label className="wi-tax-check" key={key}><input type="checkbox" checked={form[key]} onChange={e=>update(key,e.target.checked)} /> {label}</label>)}</div>
    <div className="wi-tax-confirm"><label className="wi-tax-check"><input type="checkbox" checked={form.recordsConfirmed} onChange={e=>update('recordsConfirmed',e.target.checked)} /> I checked entered income against source records and {form.year==='2025-26'?'AIS/26AS':'Form 168 and relevant tax records'}; all other income is declared above.</label><label className="wi-tax-check"><input type="checkbox" checked={form.claimsConfirmed} onChange={e=>update('claimsConfirmed',e.target.checked)} /> Entered deduction payments were eligible, made in this income year and are not counted twice.</label></div>
    <section className="wi-tax-evidence" aria-label="Tax evidence imports">
      <h4>Import and reconcile evidence</h4>
      <p className="wi-note">Upload a CSV and map its columns yourself. Use the {form.year==='2025-26'?'AIS export, 26AS, bank, payroll or broker statements':'Form 168 export, bank, payroll or broker statements'} where available. Keep the original documents for verification. Unsupported PDF layouts need manual transcription into CSV. Upstox orders require a user-provided JSON export; AGI does not request your broker token here.</p>
      <div className="wi-actions"><label className="wi-button">Choose evidence CSV<input className="wi-file" type="file" accept=".csv,text/csv" onChange={async e=>{if(e.target.files?.[0])await importFile(e.target.files[0],'csv');e.target.value='';}} /></label><label className="wi-button">Choose Upstox MF orders JSON<input className="wi-file" type="file" accept=".json,application/json" onChange={async e=>{if(e.target.files?.[0])await importFile(e.target.files[0],'orders');e.target.value='';}} /></label></div>
      {staged&&<div className="wi-notice"><strong>Map {staged.rows.length} CSV rows · {form.year} · {people.find(p=>p.id===ownerId)?.name||'unnamed case'}</strong><p>Columns: {staged.headers.join(' · ')}. No rows enter the review until you confirm the mapping.</p><div className="wi-input-grid wi-three">
        <label className="wi-field"><span>Source description</span><input maxLength={120} value={mapping.source} onChange={e=>setMapping({...mapping,source:e.target.value})} /></label>
        <label className="wi-field"><span>Default category</span><select value={mapping.defaultCategory} onChange={e=>setMapping({...mapping,defaultCategory:e.target.value})}>{Object.entries(EVIDENCE_CATEGORIES).filter(([k])=>k!=='investment').map(([k,v])=><option key={k} value={k}>{v} ({k})</option>)}</select></label>
        {['amount','credit','category','reference','date'].map(key=><label key={key} className="wi-field"><span>{key==='amount'?'Income / transaction amount':key==='credit'?'TDS / payment amount':key==='category'?'Category code (optional)':key==='reference'?'Reference (optional)':'Date YYYY-MM-DD (optional)'}</span><select value={mapping[key]} onChange={e=>setMapping({...mapping,[key]:e.target.value})}><option value="">None</option>{staged.headers.map((h,i)=><option key={i} value={String(i)}>{h} · column {i+1}</option>)}</select></label>)}
      </div><p>Preview: {staged.rows.slice(0,2).map(r=>r.join(' / ')).join(' · ')}</p><button className="wi-button wi-primary" onClick={addCsv}>Add mapped records for review</button> <button className="wi-button" onClick={()=>setStaged(null)}>Cancel</button></div>}
      {importError&&<p className="wi-error" role="alert">{importError}</p>}
      {scoped.length>0&&<><div className="wi-metrics"><div><span>Evidence rows</span><strong>{scoped.length}</strong></div><div><span>Need review</span><strong>{reconciled.unmatched}</strong></div><div><span>Investment orders</span><strong>{reconciled.investmentOrders}</strong></div></div>
        <div className="wi-tax-comparisons">{reconciled.comparisons.map(c=><div className="wi-notice" key={c.category}><strong>{EVIDENCE_CATEGORIES[c.category]} · {c.status}</strong><p>Entered {c.declared==null?'—':money(c.declared)} · Imported {c.evidence==null?'—':money(c.evidence)}</p></div>)}</div>
        {reconciled.missingCategories.length>0&&<p className="wi-error">Imported {reconciled.missingCategories.map(k=>EVIDENCE_CATEGORIES[k]).join(', ')}: classify these income sources in the case above. A narrow regime estimate cannot include them automatically.</p>}
        {reconciled.warnings.map(w=><p className="wi-error" key={w}>{w}</p>)}
        <div className="wi-tax-records">{scoped.slice(0,150).map(r=><div key={r.id}><label className="wi-tax-check"><input type="checkbox" checked={r.reviewed} onChange={e=>setEvidence(previous=>previous.map(item=>item.id===r.id?{...item,reviewed:e.target.checked}:item))} />Reviewed</label><span>{r.source} · {EVIDENCE_CATEGORIES[r.category]} · {money(r.amount)}{r.credit?` · credit ${money(r.credit)}`:''} · {r.date||'undated'}{r.description?` · ${r.description}`:''}{r.status?` · ${r.status}`:''}</span><button className="wi-text-button" onClick={()=>setEvidence(previous=>previous.filter(item=>item.id!==r.id))}>Remove</button>{r.note&&<small>{r.note}</small>}</div>)}</div>{scoped.length>150&&<p className="wi-note">Showing first 150 records; all {scoped.length} appear in the downloaded review.</p>}
      </>}
    </section>
    {form.hasRental&&<section className="wi-tax-evidence"><h4>Single let-out property schedule</h4><p className="wi-note">Enter one owner's annual amounts for one qualifying property. This schedule is kept separate from the whole-return regime estimate. Hotel services and mixed/composite letting need a different income classification.</p>
      <div className="wi-input-grid wi-three">{[['rent','Annual rent / annual value (₹)'],['municipal','Municipal tax actually paid by owner (₹)'],['interest','Eligible loan interest (₹)']].map(([k,label])=><label className="wi-field" key={k}><span>{label}</span><input type="number" min="0" step="0.01" value={property[k]} onChange={e=>setProperty({...property,[k]:e.target.value})} placeholder="Enter 0 if none" /></label>)}</div>
      <label className="wi-tax-check"><input type="checkbox" checked={property.confirmedHouseProperty} onChange={e=>setProperty({...property,confirmedHouseProperty:e.target.checked})} /> Confirm this is ordinary let-out house property and the amounts relate to this owner's share.</label>
      {propertyResult?.value&&<p className="wi-notice">Net annual value {money(propertyResult.value.netAnnualValue)} · 30% standard deduction {money(propertyResult.value.standardDeduction)} · Provisional property income {money(propertyResult.value.propertyIncome)}. {propertyResult.value.note} <a className="wi-link" href="https://www.incometaxindia.gov.in/hi/w/income-from-house-property" target="_blank" rel="noopener noreferrer">Official source ↗</a></p>}
      {propertyResult?.error&&<p className="wi-note">{propertyResult.error}</p>}
    </section>}
    {result.error && <p className="wi-error" role="alert">{result.error}</p>}
    {report && <>
      {blockedByEvidence&&<p className="wi-error">Resolve imported record differences, possible duplicates, unreviewed rows and other income before using a numerical regime comparison.</p>}
      {report.comparison ? <><div className="wi-metrics"><div><span>Old regime estimate</span><strong>{money(report.comparison.old)}</strong></div><div><span>New regime estimate</span><strong>{money(report.comparison.new)}</strong></div><div><span>Difference to verify</span><strong>{money(report.comparison.difference)}</strong></div><div><span>Effect of documented 80C/NPS claims</span><strong>{money(report.comparison.documentedClaimEffect)}</strong></div></div><p className="wi-note">{report.comparison.lower === 'equal' ? 'Same estimated liability.' : `${report.comparison.lower === 'old' ? 'Old' : 'New'} regime is lower on these inputs.`} Documented-claim effect compares the best regime with and without the *already paid* 80C/NPS amounts; it is not a recommendation to make a new investment. Taxable ordinary income: old {money(report.comparison.oldTaxable)}, new {money(report.comparison.newTaxable)}. These are estimates pending professional verification of eligibility, income classification and the underlying tax rule.</p></> : <p className="wi-notice">{report.blockedReason} {report.missing.length ? `To complete this case: ${report.missing.join(' · ')}.` : ''}</p>}
      <h4>Prioritised review queue</h4>
      <div className="wi-tax-cards">{report.cards.map(c=><article className="wi-notice" key={c.id}><strong>{c.title}</strong><p>{c.detail}</p><small>Check: {c.evidence} · <a className="wi-link" href={c.source} target="_blank" rel="noopener noreferrer">Official source ↗</a></small></article>)}</div>
    </>}
  </div>;
}
