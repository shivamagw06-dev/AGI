/** Pure planning functions. No inferred ownership, live quotes or product suitability. */
export const WORKSPACE_VERSION = 'agi-wealth-v2';
export const DAY = 86400000;
export function number(value, label, min = 0, max = 1e12) {
  if (value === '' || value == null || typeof value === 'boolean') throw new Error(`${label} is required.`);
  const n = Number(value);
  if (!Number.isFinite(n) || n < min || n > max) throw new Error(`${label} must be between ${min} and ${max}.`);
  return n;
}
export function date(value, label = 'Date') {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) throw new Error(`${label} is required (YYYY-MM-DD).`);
  const n = Date.parse(`${value}T00:00:00Z`);
  if (!Number.isFinite(n) || new Date(n).toISOString().slice(0, 10) !== value) throw new Error(`${label} is invalid.`);
  return n;
}
export function safeUrl(value) {
  try { const u = new URL(value); return u.protocol === 'https:' && !u.username && !u.password ? u.href : null; } catch { return null; }
}
export function emptyWorkspace() {
  return { version: WORKSPACE_VERSION, people: [], holdings: [], funds: [], properties: [], bonds: [], events: [], watchlist: [], expenses: 0, reserveMonths: 12 };
}
export function householdSummary(workspace) {
  const people = workspace.people.map(p => ({ ...p, assets: 0, liabilities: 0, income: 0 }));
  const byId = new Map(people.map(p => [p.id, p]));
  const classes = Object.create(null), locations = Object.create(null);
  for (const h of workspace.holdings) {
    const owner = byId.get(h.ownerId);
    if (!owner) throw new Error(`Select the legal owner of ${h.name}.`);
    const value = number(h.value, 'Holding value'), debt = number(h.debt, 'Debt'), income = number(h.income, 'Annual gross cash income');
    owner.assets += value; owner.liabilities += debt; owner.income += income;
    classes[h.kind] = (classes[h.kind] || 0) + value;
    if (h.location) locations[h.location.trim().toLowerCase()] = (locations[h.location.trim().toLowerCase()] || 0) + value;
  }
  const assets = people.reduce((n, p) => n + p.assets, 0), debt = people.reduce((n, p) => n + p.liabilities, 0);
  const grossIncome = people.reduce((n, p) => n + p.income, 0);
  const expenses = number(workspace.expenses, 'Monthly spending'), months = number(workspace.reserveMonths, 'Reserve months', 0, 60);
  return { people, assets, debt, netWorth: assets - debt, grossIncome, annualSpending: expenses * 12,
    reserveTarget: expenses * months, classes, locations,
    concentration: Object.entries(classes).map(([kind, value]) => ({ kind, value, weight: assets ? 100 * value / assets : 0 })) };
}
export function parseFundHoldings(text) {
  const holdings = new Map();
  for (const line of String(text || '').split(/\r?\n/).filter(l => l.trim())) {
    const [rawId, rawWeight, ...extra] = line.split(',');
    const id = rawId.trim().toUpperCase();
    if (!/^[A-Z0-9._&-]{2,40}$/.test(id) || extra.length) throw new Error('Use one ISIN or ticker,weight percentage per line.');
    if (holdings.has(id)) throw new Error(`Duplicate holding: ${id}.`);
    holdings.set(id, number(rawWeight?.trim(), 'Holding weight', 0, 100));
  }
  const coverage = [...holdings.values()].reduce((n, x) => n + x, 0);
  if (coverage > 100.01) throw new Error('Holding weights exceed 100%.');
  return { holdings, coverage };
}
export function fundOverlap(a, b) {
  const x = parseFundHoldings(a.holdings), y = parseFundHoldings(b.holdings);
  const shared = [...x.holdings].filter(([id]) => y.holdings.has(id)).map(([id, weight]) => ({ id, overlap: Math.min(weight, y.holdings.get(id)) }));
  return { overlap: shared.reduce((n, row) => n + row.overlap, 0), coverageA: x.coverage, coverageB: y.coverage, shared,
    comparableDates: a.asOf === b.asOf, partial: x.coverage < 99 || y.coverage < 99 };
}
export function propertySummary(rows, now = Date.now()) {
  const groups = new Map();
  for (const row of rows) {
    const area = number(row.area, 'Area in sq ft', 1), price = number(row.price, 'Price', 1);
    const at = date(row.asOf); if (at > now) throw new Error('Property evidence cannot be future-dated.');
    const key = `${row.location.trim().toLowerCase()}|${row.propertyType}|${row.priceType}`;
    if (!groups.has(key)) groups.set(key, { location: row.location, propertyType: row.propertyType, priceType: row.priceType, rows: [] });
    groups.get(key).rows.push({ ...row, pricePerSqFt: price / area, stale: now - at > 180 * DAY });
  }
  return [...groups.values()].map(group => {
    const values = group.rows.map(r => r.pricePerSqFt).sort((a, b) => a - b), n = values.length;
    return { ...group, count: n, low: values[0], high: values[n - 1], median: (values[Math.floor((n - 1) / 2)] + values[Math.floor(n / 2)]) / 2 };
  });
}
/** Dated cash-flow IRR, unique root only for a single negative initial outflow. */
export function cashFlowIrr(flows) {
  if (flows.length < 2 || flows[0].amount >= 0 || flows.slice(1).some(f => f.amount < 0)) return null;
  const start = date(flows[0].date), timed = flows.map(f => ({ ...f, years: (date(f.date) - start) / (365.25 * DAY) }));
  if (timed.slice(1).some(f => f.years <= 0)) return null;
  const npv = rate => timed.reduce((n, f) => n + f.amount / (1 + rate) ** f.years, 0);
  let low = -0.999, high = 10;
  if (npv(low) < 0 || npv(high) > 0) return null;
  for (let i = 0; i < 100; i++) { const mid = (low + high) / 2; if (npv(mid) > 0) low = mid; else high = mid; }
  return (low + high) * 50;
}
export function bondCashFlows(row) {
  const settlement = date(row.settlement, 'Settlement date'), maturity = date(row.maturity, 'Maturity date');
  if (maturity <= settlement) throw new Error('Maturity must follow settlement.');
  const cost = number(row.cost, 'All-in settlement cost', 1), principal = number(row.principal, 'Redemption principal', 1);
  const incomeTax = number(row.incomeTax, 'Coupon tax assumption', 0, 60) / 100;
  const gainTax = number(row.gainTax, 'Redemption gain tax assumption', 0, 60) / 100;
  const coupons = new Map();
  for (const line of String(row.coupons || '').split(/\r?\n/).filter(x => x.trim())) {
    const [d, amount, ...extra] = line.split(',').map(x => x.trim()); const when = date(d, 'Coupon date');
    if (extra.length || when <= settlement || when > maturity) throw new Error('Coupon dates must follow settlement and be on or before maturity.');
    coupons.set(d, (coupons.get(d) || 0) + number(amount, 'Coupon amount', 0));
  }
  const taxOnGain = Math.max(0, principal - cost) * gainTax;
  const dates = [...new Set([...coupons.keys(), row.maturity])].sort();
  const schedule = dates.map(d => { const coupon = coupons.get(d) || 0, redemption = d === row.maturity ? principal : 0;
    const tax = coupon * incomeTax + (redemption ? taxOnGain : 0);
    return { date: d, coupon, redemption, tax, gross: coupon + redemption, net: coupon + redemption - tax }; });
  const flows = [{ date: row.settlement, amount: -cost }, ...schedule.map(r => ({ date: r.date, amount: r.net }))];
  return { schedule, invested: cost, netReceipts: schedule.reduce((n, r) => n + r.net, 0),
    totalTax: schedule.reduce((n, r) => n + r.tax, 0), afterTaxIrr: cashFlowIrr(flows) };
}
export function maturityLadder(bonds) {
  const buckets = new Map();
  for (const bond of bonds) for (const flow of bondCashFlows(bond).schedule) {
    const year = flow.date.slice(0, 4), bucket = buckets.get(year) || { year, coupon: 0, principal: 0, tax: 0, net: 0 };
    bucket.coupon += flow.coupon; bucket.principal += flow.redemption; bucket.tax += flow.tax; bucket.net += flow.net; buckets.set(year, bucket);
  }
  return [...buckets.values()].sort((a, b) => a.year.localeCompare(b.year));
}
export function monitoringAlerts(workspace, now = Date.now()) {
  const alerts = [];
  const add = (id, title, detail, severity = 'review') => alerts.push({ id, title, detail, severity });
  for (const row of workspace.holdings) if (row.maturity) {
    const days = Math.ceil((date(row.maturity) - now) / DAY);
    if (days <= 90) add(`maturity:${row.id}`, `${row.name}: ${days < 0 ? 'maturity date passed' : `matures in ${days} days`}`, 'Confirm proceeds, renewal instructions and upcoming spending before reinvesting.');
  }
  for (const [kind, rows, maxAge] of [['property', workspace.properties, 180], ['fund', workspace.funds, 60], ['bond', workspace.bonds, 7]]) {
    for (const row of rows) if (now - date(row.asOf) > maxAge * DAY) add(`stale:${kind}:${row.id}`, `${row.name}: evidence needs refreshing`, `${kind} evidence is older than ${maxAge} days; reconfirm before relying on it.`, 'stale');
  }
  for (const row of workspace.watchlist) {
    const age = row.asOf ? now - Date.parse(row.asOf.length === 10 ? `${row.asOf}T00:00:00Z` : row.asOf) : Infinity;
    if (!Number.isFinite(age) || age > (row.assetClass === 'equity' ? 120000 : 4 * DAY)) add(`watch:${row.id}`, `${row.name}: saved observation is stale`, 'Refresh the investment universe and save a new observation.');
  }
  for (const event of workspace.events) {
    const days = Math.ceil((date(event.due) - now) / DAY);
    if (event.status !== 'completed' && days <= 30) add(`event:${event.id}`, event.name, `${days < 0 ? 'Overdue' : `Due in ${days} days`} · ${event.impact || 'Review the linked evidence.'}`);
  }
  for (const c of householdSummary(workspace).concentration) if (c.weight > 50) add(`concentration:${c.kind}`, `${c.kind}: ${c.weight.toFixed(1)}% of recorded assets`, 'Review concentration alongside liquidity and household needs.');
  return alerts;
}
