import { emptyWorkspace, number, date, safeUrl, householdSummary, parseFundHoldings, propertySummary, bondCashFlows, WORKSPACE_VERSION } from './wealthPlanning.js';
const field = (key, label, type = 'text', options) => ({ key, label, type, options });
export const RECORD_SCHEMAS = {
  people: [field('name', 'Person / entity name'), field('entity', 'Taxpayer type', 'select', ['individual','HUF','business']), field('residency', 'Residency', 'select', ['resident','nonresident','review']), field('age','Age at financial year end','number'), field('year','Income financial year','select',['2026-27','2025-26']), field('regime','Regime','select',['new','old']), field('taxable','CA-computed taxable ordinary income (₹)','number'), field('credits','Confirmed TDS + advance tax (₹)','number'), field('special','Income treatment','select',['review','none','capital gains / dividends / foreign income / losses'])],
  holdings: [field('name','Asset or income stream'), field('ownerId','Legal owner','owner'), field('kind','Asset class','select',['FD','cash','equity','mutual fund','property','bond','gold','business','REIT / InvIT','alternative','overseas','salary / pension']), field('value','Your ownership share of value (₹)','number'), field('debt','Your share of outstanding debt (₹)','number'), field('income','Your annual gross cash income (₹)','number'), field('location','Geography (optional)'), field('maturity','Maturity (optional)','date')],
  funds: [field('name','Scheme name and plan'), field('schemeCode','AMFI scheme code'), field('source','AMC disclosure URL','url'), field('asOf','Disclosure date','date'), field('expense','Annual expense ratio %','number'), field('risk','Disclosed risk category'), field('holdings','Disclosed holdings: ISIN or ticker,weight % per line','textarea')],
  properties: [field('name','Property / comparable'), field('location','City and micro-market'), field('propertyType','Property type','select',['land','apartment','commercial','industrial']), field('priceType','Price evidence','select',['asking','registered','guidance','estimate']), field('price','Whole-property value (₹)','number'), field('area','Area (sq ft)','number'), field('rent','Annual gross rent (₹)','number'), field('source','Evidence URL','url'), field('asOf','Evidence date','date'), field('stage','Infrastructure evidence stage','select',['not documented','announced','approved','funded','under construction','operational']), field('driver','Demand driver and evidence reference'), field('legal','Title / use / access review','select',['not reviewed','professional review pending','user reports review completed'])],
  bonds: [field('name','Deposit or security name'), field('issuer','Issuer / bank'), field('source','Term sheet or quote URL','url'), field('asOf','Quote date','date'), field('settlement','Settlement date','date'), field('maturity','Maturity date','date'), field('cost','All-in purchase price including accrued interest (₹)','number'), field('principal','Principal returned at maturity (₹)','number'), field('incomeTax','Effective tax on coupons % (assumption)','number'), field('gainTax','Effective tax on redemption gain % (assumption)','number'), field('credit','Credit rating and rating date / not rated'), field('coupons','Future coupon cash flows: YYYY-MM-DD,amount per line','textarea')],
  events: [field('name','Review action / regulation / catalyst'), field('due','Review due date','date'), field('source','Official or issuer source URL','url'), field('impact','Affected assets and what to review'), field('status','Review status','select',['pending','completed'])],
};
export function blankRecord(kind) {
  return Object.fromEntries([['id', crypto.randomUUID()], ...RECORD_SCHEMAS[kind].map(f => [f.key, f.type === 'select' ? f.options[0] : f.type === 'number' ? '0' : ''])]);
}
export function validateRecord(kind, raw, workspace, now = Date.now()) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error('Invalid record.');
  if (!Object.hasOwn(RECORD_SCHEMAS, kind)) throw new Error('Unsupported record type.');
  if (typeof raw.id !== 'string') throw new Error('Invalid record identifier.');
  const out = { id: raw.id };
  if (!/^[a-zA-Z0-9:_-]{1,120}$/.test(out.id)) throw new Error('Invalid record identifier.');
  for (const f of RECORD_SCHEMAS[kind] || []) {
    if (raw[f.key] != null && !['string','number'].includes(typeof raw[f.key])) throw new Error(`Invalid ${f.label}.`);
    const v = String(raw[f.key] ?? '');
    if (v.length > (f.type === 'textarea' ? 30000 : 1000)) throw new Error(`${f.label} is too long.`);
    const optional = f.label.includes('(optional)') || f.key === 'coupons';
    if (!v.trim() && !optional) throw new Error(`${f.label} is required.`);
    if (f.type === 'select' && !f.options.includes(v)) throw new Error(`Invalid ${f.label}.`);
    if (f.type === 'number') number(v, f.label);
    if (f.type === 'date' && v) date(v, f.label);
    if (f.type === 'url' && !safeUrl(v)) throw new Error(`${f.label} must be an HTTPS URL.`);
    out[f.key] = v.trim();
  }
  if (out.asOf && date(out.asOf) > now) throw new Error('Evidence date cannot be in the future.');
  if (kind === 'people') number(out.age, 'Age', 0, 120);
  if (kind === 'holdings' && !workspace.people.some(p => p.id === out.ownerId)) throw new Error('Choose an existing legal owner.');
  if (kind === 'funds') { if (!/^\d{4,8}$/.test(out.schemeCode)) throw new Error('Invalid AMFI scheme code.'); number(out.expense, 'Expense ratio', 0, 10); parseFundHoldings(out.holdings); }
  if (kind === 'properties') propertySummary([out], now);
  if (kind === 'bonds') bondCashFlows(out);
  return out;
}
export function validateWorkspace(raw, now = Date.now()) {
  if (!raw || raw.version !== WORKSPACE_VERSION) throw new Error('Unsupported wealth workspace version.');
  const out = emptyWorkspace();
  out.expenses = number(raw.expenses, 'Monthly spending'); out.reserveMonths = number(raw.reserveMonths, 'Reserve months', 0, 60);
  for (const kind of Object.keys(RECORD_SCHEMAS)) {
    if (!Array.isArray(raw[kind]) || raw[kind].length > 500) throw new Error(`Invalid ${kind} records (maximum 500).`);
    const ids = new Set();
    out[kind] = raw[kind].map(row => { const r = validateRecord(kind, row, out, now); if (ids.has(r.id)) throw new Error('Duplicate record identifier.'); ids.add(r.id); return r; });
  }
  if (!Array.isArray(raw.watchlist) || raw.watchlist.length > 100) throw new Error('Watchlist limit is 100.');
  const observationIds = new Set();
  out.watchlist = raw.watchlist.map(row => {
    if (!row || !['equity','mutual_fund'].includes(row.assetClass) || typeof row.id !== 'string' || typeof row.name !== 'string' || row.name.length > 500) throw new Error('Invalid saved observation.');
    if (!/^[a-zA-Z0-9:_.&-]{1,120}$/.test(row.id) || observationIds.has(row.id)) throw new Error('Invalid or duplicate observation identifier.');
    observationIds.add(row.id);
    if (row.asOf != null && typeof row.asOf !== 'string') throw new Error('Invalid observation date.');
    if (row.source != null && typeof row.source !== 'string') throw new Error('Invalid observation source.');
    const asOf = row.asOf == null ? null : row.asOf;
    if (asOf && /^\d{4}-\d{2}-\d{2}$/.test(asOf)) date(asOf);
    if (asOf && (!Number.isFinite(Date.parse(asOf)) || Date.parse(asOf) > now + 86400000)) throw new Error('Invalid observation date.');
    return { id: row.id.slice(0,120), name: row.name, assetClass: row.assetClass, asOf, price: row.price == null ? null : number(row.price, 'Price'), source: String(row.source || '').slice(0,200) };
  });
  householdSummary(out);
  return out;
}
