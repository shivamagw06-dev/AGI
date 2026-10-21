import { readFile } from 'node:fs/promises';
import { getLiveAlphaMarketSnapshot, loadLiveAlphaUniverse } from './liveAlphaRuntime.js';
import { getUpstoxFunds } from '../providers/upstoxMutualFunds.js';
import { getAmfiNav } from '../providers/amfiNav.js';

export function normalizeWealthQuote(member, quote, now = Date.now()) {
  const number = raw => raw === null || raw === undefined || raw === '' ? null : Number.isFinite(Number(raw)) ? Number(raw) : null;
  const price = number(quote?.ltp), previous = number(quote?.previous_close);
  const asOf = quote?.effective_timestamp || quote?.exchange_timestamp || null;
  const age = asOf ? now - Date.parse(asOf) : NaN;
  const hasPrice = price > 0;
  const fresh = hasPrice && quote?.data_quality === 'PASS' && age >= -5000 && age <= 120_000;
  return {
    id: `equity:${member.symbol}`, symbol: member.symbol, name: member.name || member.symbol,
    sector: member.sector?.replaceAll('_', ' ') || null, assetClass: 'equity', currency: 'INR',
    price: hasPrice ? price : null, changePct: hasPrice && previous > 0 ? (price / previous - 1) * 100 : null,
    asOf, status: fresh ? 'live' : hasPrice ? 'stale' : 'unavailable',
    source: quote?.source || null, instrumentKey: member.instrumentKey,
    reasons: quote?.reason_codes || [], researchUrl: `/research/stocks/${encodeURIComponent(member.symbol)}`,
  };
}

let universePromise;
async function universe() {
  if (!universePromise) universePromise = Promise.all([
    loadLiveAlphaUniverse(), readFile(new URL('../../indices/Nifty500.csv', import.meta.url), 'utf8'),
  ]).then(([data, csv]) => {
    const names = new Map(csv.split(/\r?\n/).slice(1).map(line => { const c = line.split(','); return [c[2]?.trim(), c[0]?.trim()]; }));
    return data.members.map(member => ({ ...member, name: names.get(member.symbol) || member.symbol }));
  }).catch(error => { universePromise = null; throw error; });
  return universePromise;
}

export const WEALTH_COVERAGE = [
  { id: 'equity', label: 'Indian equities', cadence: 'Shared Upstox runtime', detail: 'Quotes and existing company research. Feed freshness is checked per security.' },
  { id: 'mutual_fund', label: 'Mutual funds', cadence: 'Daily NAV', detail: 'Upstox fund directory and published NAVs, with AMFI fallback. NAV alone does not establish expected returns or tax classification.' },
  { id: 'property', label: 'Land & property', cadence: 'Manual evidence', detail: 'Compare a property using your quote and costs. Verified listings and local transaction feeds are not connected.' },
  { id: 'fixed_income', label: 'FDs & bonds', cadence: 'Manual assumptions', detail: 'Income scenarios are available. Bank rate sheets and executable bond offerings are not connected.' },
  { id: 'commodity', label: 'Gold & commodities', cadence: 'Manual assumptions', detail: 'Scenario modelling available. This workspace has no verified investable commodity catalogue.' },
  { id: 'alternative', label: 'Private assets / REITs / InvITs', cadence: 'Manual assumptions', detail: 'Scenario modelling available. Product eligibility, distributions and offering documents still require verification.' },
];

export async function getWealthUniverse({ assetClass = 'equity', q = '', offset = 0, limit = 50 } = {}, deps = {}) {
  const now = deps.now?.() ?? Date.now();
  let rows, source;
  if (assetClass === 'mutual_fund') {
    const [funds, nav] = await Promise.all([
      deps.getFunds ? deps.getFunds() : deps.getNav ? Promise.resolve(null) : getUpstoxFunds(),
      (deps.getNav || getAmfiNav)(),
    ]);
    const provider = funds?.rows.length ? 'Upstox' : 'AMFI';
    const data = provider === 'Upstox' ? funds : nav;
    const byIsin = new Map(nav.rows.filter(row => row.isin).map(row => [row.isin, row]));
    rows = data.rows.map(original => {
      const amfi = provider === 'Upstox' ? byIsin.get(original.isin) : null;
      const row = amfi && (!original.asOf || amfi.asOf > original.asOf) ? {
        ...original, price:amfi.price, asOf:amfi.asOf, schemeCode:amfi.schemeCode,
        fundHouse:original.fundHouse || amfi.fundHouse, navSource:'AMFI', navSourceUrl:amfi.sourceUrl,
      } : { ...original, navSource:original.source || provider };
      const navStale = row.navSource === 'AMFI' ? nav.status === 'stale' : data.status === 'stale';
      const age = now - Date.parse(`${row.asOf}T00:00:00+05:30`);
      return { ...row, status: !row.price && provider === 'Upstox' ? 'unavailable' : navStale || !Number.isFinite(age) || age < -86_400_000 || age > 4 * 86_400_000 ? 'stale' : 'daily' };
    });
    source = { provider, status: data.status, fetchedAt: data.fetchedAt, error: data.error, navProvider: provider === 'Upstox' ? 'Upstox / AMFI' : 'AMFI' };
  } else {
    const members = await (deps.getUniverse || universe)();
    const snapshot = (deps.getSnapshot || getLiveAlphaMarketSnapshot)(members.map(row => row.symbol));
    rows = members.map(member => normalizeWealthQuote(member, snapshot.quotes?.[member.symbol], now));
    source = { provider: snapshot.provider, status: snapshot.status, observedAt: snapshot.observed_at, lastHeartbeat: snapshot.last_heartbeat };
  }
  const query = String(q).toLowerCase().trim();
  rows = rows.filter(row => `${row.name} ${row.symbol || ''} ${row.sector || ''} ${row.fundHouse || ''} ${row.category || ''} ${row.schemeCode || ''} ${row.isin || ''} ${row.plan || ''}`.toLowerCase().includes(query));
  rows.sort((a, b) => a.name.localeCompare(b.name));
  return { items: rows.slice(offset, offset + limit), total: rows.length, offset, limit, source,
    coverage: WEALTH_COVERAGE, generatedAt: new Date(now).toISOString(), researchOnly: true };
}
