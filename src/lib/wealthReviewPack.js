import { validateWorkspace, RECORD_SCHEMAS } from './wealthWorkspace.js';
import { validatePlan, validateAsset, compareScenarios, MODEL_VERSION } from './wealthScenario.js';
import { householdSummary, monitoringAlerts, number, date, safeUrl, maturityLadder, propertySummary } from './wealthPlanning.js';
import { estimateOrdinaryTax, TAX_RULE } from './wealthTax.js';
const CLASSES = ['equity','mutual_fund','property','fixed_income','commodity','alternative'];
const text = (value, label, max = 1000) => {
  if (typeof value !== 'string' || value.length > max) throw new Error(`Invalid ${label}.`);
  return value;
};
const object = (value, label) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`Invalid ${label}.`);
  return value;
};
function normalizeScenario(raw, now) {
  object(raw, 'scenario');
  const id = text(raw.id, 'scenario identifier', 120), label = text(raw.label, 'scenario name', 160);
  if (!/^[a-zA-Z0-9:_-]+$/.test(id) || !label.trim() || !CLASSES.includes(raw.kind)) throw new Error('Invalid scenario.');
  const values = validateAsset(raw), result = { id, label, kind:raw.kind };
  for (const key of ['growth','incomeYield','entryCost','exitCost','annualCost','gainsTax']) result[key] = values[key];
  if (raw.property != null) {
    object(raw.property, 'property evidence');
    result.property = Object.fromEntries(['location','askingPrice','source','date','priceType','documents'].map(key => [key,text(raw.property[key] ?? '',`property ${key}`,1000)]));
    if (result.property.askingPrice !== '') number(result.property.askingPrice,'Property price',1);
    if (result.property.date && date(result.property.date) > now) throw new Error('Property evidence is future-dated.');
    if (!['asking','registered','guidance','estimate'].includes(result.property.priceType)) throw new Error('Invalid property price type.');
  }
  if (raw.observed != null) {
    object(raw.observed, 'market observation');
    const asOf = raw.observed.asOf == null ? null : text(raw.observed.asOf,'observation date',40);
    if (asOf && (!Number.isFinite(Date.parse(asOf)) || Date.parse(asOf) > now + 86400000)) throw new Error('Invalid observation date.');
    result.observed = { id:text(raw.observed.id,'observation identifier',120), price:raw.observed.price == null ? null : number(raw.observed.price,'Observed price'), asOf,
      source:raw.observed.source == null ? null : text(raw.observed.source,'observation source',200), status:text(raw.observed.status ?? 'unavailable','observation status',40) };
  }
  return result;
}
export function validateReviewPack(raw, now = Date.now()) {
  object(raw, 'review pack');
  if (raw.version !== 'agi-review-pack-v2') throw new Error('Unsupported review pack.');
  const workspace = validateWorkspace(raw.workspace,now);
  object(raw.comparison,'comparison'); object(raw.comparison.plan,'comparison assumptions');
  if (typeof raw.comparison.plan.reinvest !== 'boolean') throw new Error('Reinvestment must be true or false.');
  const plan = validatePlan(raw.comparison.plan);
  if (!Array.isArray(raw.comparison.assets) || raw.comparison.assets.length > 4) throw new Error('Compare up to four alternatives.');
  const ids = new Set(['fd']);
  const assets = raw.comparison.assets.map(rawAsset => { const a=normalizeScenario(rawAsset,now); if(ids.has(a.id))throw new Error('Duplicate scenario identifier.'); ids.add(a.id);return a; });
  return { workspace, plan, assets };
}
export function createReviewPack(workspace, plan, assets, now = Date.now()) {
  const clean = validateReviewPack({version:'agi-review-pack-v2',workspace,comparison:{plan,assets}},now);
  return {version:'agi-review-pack-v2',generatedAt:new Date(now).toISOString(),workspace:clean.workspace,
    comparison:{plan:clean.plan,assets:clean.assets,results:compareScenarios(clean.plan,clean.assets),model:MODEL_VERSION},
    household:householdSummary(clean.workspace),alerts:monitoringAlerts(clean.workspace,now),
    tax:clean.workspace.people.map(p=>{try{return {ownerId:p.id,...estimateOrdinaryTax(p)};}catch(e){return {ownerId:p.id,status:'review_required',total:null,reasons:[e.message]};}}),
    rule:TAX_RULE,reviewStatus:'Professional review pending. Supplied evidence is not independently verified.'};
}
const escape = value => String(value ?? '—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = value => value == null ? 'Not calculated' : new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(value);
const table = (headers, rows) => `<div class="table"><table><thead><tr>${headers.map(h=>`<th>${escape(h)}</th>`).join('')}</tr></thead><tbody>${rows.length ? rows.map(row=>`<tr>${row.map(v=>`<td>${escape(v)}</td>`).join('')}</tr>`).join('') : `<tr><td colspan="${headers.length}">No records supplied.</td></tr>`}</tbody></table></div>`;
/** Offline, script-free report. All saved calculations are ignored and recalculated. */
export function renderReviewReport(raw, now = Date.now()) {
  const clean=validateReviewPack(raw,now), pack=createReviewPack(clean.workspace,clean.plan,clean.assets,now), w=pack.workspace;
  const owner = id => w.people.find(p=>p.id===id)?.name || id;
  const records = Object.entries(RECORD_SCHEMAS).map(([kind,fields])=>`<section><h2>${escape({people:'Taxpayer inputs',holdings:'Assets and income',funds:'Fund disclosures',properties:'Property evidence',bonds:'Fixed-income terms',events:'Review actions'}[kind])}</h2>${w[kind].map(row=>`<article><h3>${escape(row.name)}</h3><dl>${fields.map(f=>`<dt>${escape(f.label)}</dt><dd>${escape(f.key==='ownerId'?owner(row[f.key]):row[f.key])}</dd>`).join('')}</dl></article>`).join('') || '<p>No records supplied.</p>'}</section>`).join('');
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><meta name="referrer" content="no-referrer"><title>AGI Wealth Review Report</title><style>
body{font:16px/1.5 system-ui,sans-serif;color:#17304a;background:#fff;max-width:1100px;margin:32px auto;padding:0 24px}h1{font-size:30px}h2{border-bottom:2px solid #204b70;padding-bottom:8px;margin-top:32px}h3{font-size:18px}p,dd{overflow-wrap:anywhere}small{color:#53677b}.notice{padding:16px;background:#edf3f8;border-left:3px solid #204b70}.table{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #cdd8e3;padding:9px;text-align:left;vertical-align:top}th{background:#edf3f8}article{border:1px solid #cdd8e3;padding:16px;margin:16px 0;break-inside:avoid}dl{display:grid;grid-template-columns:minmax(180px,1fr) 2fr;gap:8px 20px}dt{font-weight:600}dd{margin:0;white-space:pre-wrap}.signoff{height:70px;border-bottom:1px solid #879bab}@media(max-width:600px){dl{grid-template-columns:1fr}dd{margin-bottom:12px}}@media print{body{margin:0;padding:0;font-size:11pt}.table{overflow:visible}table{font-size:9pt}thead{display:table-header-group}tr{break-inside:avoid}h2,h3{break-after:avoid}.print-note{display:none}@page{size:A4;margin:16mm}}
</style></head><body><header><small>AGARWAL GLOBAL INVESTMENTS</small><h1>Wealth review report</h1><p>Prepared ${escape(pack.generatedAt)} · ${escape(MODEL_VERSION)}</p><p class="notice">${escape(pack.reviewStatus)} This file contains private financial information. Share only with your intended reviewer.</p><p class="print-note">Open your browser’s Print command to print this report or save it as PDF. No external resources or scripts are loaded.</p></header>
<section><h2>Household overview</h2>${table(['Recorded assets','Recorded debt','Net worth','Annual gross cash income','Annual spending','Reserve target'],[[money(pack.household.assets),money(pack.household.debt),money(pack.household.netWorth),money(pack.household.grossIncome),money(pack.household.annualSpending),money(pack.household.reserveTarget)]])}<p>Gross cash income is not taxable or spendable income. Ownership shares are entered by the client.</p></section>
<section><h2>After-tax scenarios</h2>${table(['Assumption','Value'],Object.entries(pack.comparison.plan))}${table(['Scenario','First-year net income','Net exit wealth','Total assumed tax','Costs','Difference vs FD'],pack.comparison.results.map(r=>[r.label,money(r.firstYearNetIncome),money(r.netWealth),money(r.totalTax),money(r.totalCosts),money(r.vsFd)]))}${table(['Scenario','Growth %','Cash yield %','Entry %','Exit %','Holding cost %','Exit tax %'],pack.comparison.assets.map(a=>[a.label,a.growth,a.incomeYield,a.entryCost,a.exitCost,a.annualCost,a.gainsTax]))}<p>Rates and returns are assumptions, not forecasts. Income is annual; positive cash may be reinvested at the assumed after-tax FD rate. The model excludes financing, loss credits, exemptions and indexation; entry costs are included in assumed tax basis. Negative cash needs external funding.</p>${table(['Scenario','External cash shortfall'],pack.comparison.results.filter(r=>r.cashShortfall>0).map(r=>[r.label,money(r.cashShortfall)]))}</section>
<section><h2>Scenario evidence</h2>${table(['Scenario','Property / reference','Evidence date','Source','Status'],pack.comparison.assets.filter(a=>a.property||a.observed).map(a=>[a.label,a.property?.location||a.observed?.id,a.property?.date||a.observed?.asOf,a.property?.source||a.observed?.source,a.property?.documents||a.observed?.status]))}</section>
<section><h2>Fixed-income maturity ladder</h2>${table(['Calendar year','Gross coupons','Returned principal','Assumed tax','Net receipts'],maturityLadder(w.bonds).map(r=>[r.year,money(r.coupon),money(r.principal),money(r.tax),money(r.net)]))}<p>Scheduled payments assume no default or early redemption. Principal repayments are not investment income.</p></section>
<section><h2>Property comparable summary</h2>${table(['Location','Type','Evidence category','Count','Median ₹ / sq ft'],propertySummary(w.properties,now).map(r=>[r.location,r.propertyType,r.priceType,r.count,money(r.median)]))}<p>Unadjusted supplied comparables; differences in property mix do not establish appreciation.</p></section>
<section><h2>Tax estimates requiring review</h2>${table(['Owner','Status','Estimated total','Confirmed credits','Balance / (excess credits)','Review notes'],pack.tax.map(t=>[owner(t.ownerId),t.status,money(t.total),money(t.credits),money(t.balance),t.reasons?.join(' ')]))}<p>Rule: ${escape(TAX_RULE.id)}. FY ${escape(TAX_RULE.financialYear)} / AY ${escape(TAX_RULE.assessmentYear)} only. Current-year and special-income cases may be unsupported. Professional review is pending.</p><p>Primary source: ${escape(safeUrl(TAX_RULE.source))}</p></section>
<section><h2>Review queue</h2>${table(['Action','Detail'],pack.alerts.map(a=>[a.title,a.detail]))}</section>${records}
<section><h2>Saved market observations</h2>${table(['Investment','Price / NAV','As of','Source'],w.watchlist.map(r=>[r.name,money(r.price),r.asOf,r.source]))}<p>These are saved observations, not refreshed live prices.</p></section>
<section><h2>Reviewer sign-off</h2><p>Confirm ownership, source of funds, residency, regime eligibility, deductions, special income, losses and tax credits. Confirm investment evidence, product access, title/use restrictions and transaction costs separately. This document does not establish tax or investment approval.</p><p>Reviewer name, review date and unresolved items:</p><div class="signoff"></div></section></body></html>`;
}
