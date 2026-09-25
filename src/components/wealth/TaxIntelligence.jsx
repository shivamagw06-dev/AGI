import { useMemo, useState } from 'react';
import { BLANK_TAX_CASE, scanTaxOpportunities } from '@/lib/taxOpportunity';
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
export default function TaxIntelligence() {
  const [form,setForm] = useState({...BLANK_TAX_CASE});
  const update = (key,value) => setForm(previous=>({...previous,[key]:value}));
  const result = useMemo(()=>{try{return {value:scanTaxOpportunities(form)};}catch(e){return {error:e.message};}},[form]);
  const report = result.value;
  return <div className="wi-tax-intelligence">
    <div className="wi-section-title"><div><p className="wi-eyebrow">AGI TAX INTELLIGENCE · RESEARCH PREVIEW</p><h3>Find tax work worth reviewing</h3></div><button className="wi-button" onClick={()=>setForm({...BLANK_TAX_CASE})}>Clear case</button></div>
    <p className="wi-note">This scanner keeps entries in this page session. Enter one resident individual's income only. It flags applicable checks and shows a narrow FY 2025–26 ordinary-income regime estimate only when the information is complete. No tax return is filed here.</p>
    <div className="wi-input-grid wi-three">
      <label className="wi-field"><span>Income year</span><select value={form.year} onChange={e=>update('year',e.target.value)}><option value="2026-27">Tax Year 2026–27 · planning</option><option value="2025-26">FY 2025–26 / AY 2026–27 · claim review</option></select></label>
      <label className="wi-field"><span>Age at end of income year</span><input type="number" min="18" max="120" value={form.age} onChange={e=>update('age',e.target.value)} placeholder="Age" /></label>
      {FIELDS.map(([key,label])=><label className="wi-field" key={key}><span>{label}</span><input type="number" min="0" step="0.01" value={form[key]} onChange={e=>update(key,e.target.value)} placeholder="Enter 0 if none" /></label>)}
    </div>
    <p className="wi-note">Deduction amounts refer to payments made in the selected year. FY 2025–26 is already over; a payment made today cannot be added to that year's claim. Leave unknown amounts blank. The health premium is flagged for review and excluded from the numerical estimate.</p>
    <div className="wi-input-grid wi-three">{TYPES.map(([key,label])=><label className="wi-tax-check" key={key}><input type="checkbox" checked={form[key]} onChange={e=>update(key,e.target.checked)} /> {label}</label>)}</div>
    <div className="wi-tax-confirm"><label className="wi-tax-check"><input type="checkbox" checked={form.recordsConfirmed} onChange={e=>update('recordsConfirmed',e.target.checked)} /> I checked the entered income against Form 16, bank records and AIS/26AS; all other income is declared above.</label><label className="wi-tax-check"><input type="checkbox" checked={form.claimsConfirmed} onChange={e=>update('claimsConfirmed',e.target.checked)} /> Entered deduction payments were eligible, made in this income year and are not counted twice.</label></div>
    {result.error && <p className="wi-error" role="alert">{result.error}</p>}
    {report && <>
      {report.comparison ? <><div className="wi-metrics"><div><span>Old regime estimate</span><strong>{money(report.comparison.old)}</strong></div><div><span>New regime estimate</span><strong>{money(report.comparison.new)}</strong></div><div><span>Difference to verify</span><strong>{money(report.comparison.difference)}</strong></div></div><p className="wi-note">{report.comparison.lower === 'equal' ? 'Same estimated liability.' : `${report.comparison.lower === 'old' ? 'Old' : 'New'} regime is lower on these inputs.`} Taxable ordinary income: old {money(report.comparison.oldTaxable)}, new {money(report.comparison.newTaxable)}. These are estimates pending professional verification of eligibility, income classification and the underlying tax rule.</p></> : <p className="wi-notice">{report.blockedReason} {report.missing.length ? `To complete this case: ${report.missing.join(' · ')}.` : ''}</p>}
      <h4>Prioritised review queue</h4>
      <div className="wi-tax-cards">{report.cards.map(c=><article className="wi-notice" key={c.id}><strong>{c.title}</strong><p>{c.detail}</p><small>Check: {c.evidence} · <a className="wi-link" href={c.source} target="_blank" rel="noopener noreferrer">Official source ↗</a></small></article>)}</div>
    </>}
  </div>;
}
