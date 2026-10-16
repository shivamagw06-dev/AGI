/**
 * What are the tickers we hold, actually?
 *
 * The first price dry run planned 4,987 symbols and its first three were
 * 07WA, 0C3 and 0VVB - London IOB codes, not US tickers. They arrive because
 * preferredFigiCandidate prefers a US listing but does not require one, so a
 * CUSIP OpenFIGI has no US line for takes a foreign venue's symbol instead.
 *
 * A 13F security is US-exchange-traded by definition, so a foreign code is
 * always wrong there. It is worse than useless: a short foreign code can
 * collide with a real US symbol and price a position off another company.
 *
 * Read-only. Writes nothing.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { yahooSymbol } from '../services/pricePlan.js';

if (!getSupabaseAdminCredentials()) {
  console.error('[audit] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();

async function all(build, page = 1000) {
  const rows = [];
  for (let from = 0; ; from += page) {
    const { data, error } = await build().range(from, from + page - 1);
    if (error) throw new Error(error.message);
    rows.push(...(data || []));
    if (!data || data.length < page) break;
    if (rows.length > 3_000_000) throw new Error('refusing to page past 3m rows');
  }
  return rows;
}

// ---- the authoritative list of US-listed tickers --------------------------

const ua = (process.env.SEC_USER_AGENT || 'AGI Institutional Research research@agarwalglobalinvestments.com').trim();
const resp = await fetch('https://www.sec.gov/files/company_tickers.json', { headers: { 'User-Agent': ua } });
if (!resp.ok) throw new Error(`company_tickers.json: HTTP ${resp.status}`);
const secTickers = new Set(Object.values(await resp.json()).map((e) => String(e.ticker).toUpperCase()));
console.log(`[audit] SEC lists ${secTickers.size.toLocaleString()} currently-registered tickers`);

// ---- what we hold ---------------------------------------------------------

const holdings = await all(() => client
  .from('institutional_holdings')
  .select('cusip,ticker,report_date,value_usd')
  .not('ticker', 'is', null)
  .is('put_call', null)
  .order('cusip'));

const dates = holdings.map((h) => h.report_date).filter(Boolean).sort();
console.log(`[audit] ${holdings.length.toLocaleString()} priced holding rows`);
console.log(`[audit] report dates ${dates[0]} .. ${dates.at(-1)}`);

const quarters = new Map();
for (const h of holdings) quarters.set(h.report_date, (quarters.get(h.report_date) || 0) + 1);
console.log(`[audit] ${quarters.size} distinct report dates, earliest 6:`);
for (const d of [...quarters.keys()].sort().slice(0, 6)) console.log(`    ${d}  ${quarters.get(d).toLocaleString()} rows`);

// ---- ticker shape ---------------------------------------------------------

// A US ticker is 1-5 letters, optionally with a -X share-class suffix. Anything
// carrying a digit, or longer than that, did not come from a US listing.
const US_SHAPE = /^[A-Z]{1,5}(-[A-Z])?$/;

const stats = new Map();
for (const h of holdings) {
  const t = String(h.ticker).toUpperCase();
  const s = stats.get(t) || { rows: 0, value: 0, first: h.report_date, last: h.report_date };
  s.rows += 1;
  s.value += Number(h.value_usd) || 0;
  if (h.report_date < s.first) s.first = h.report_date;
  if (h.report_date > s.last) s.last = h.report_date;
  stats.set(t, s);
}

const buckets = {
  secListed: [], usShapeNotListed: [], nonUsShape: [], unusable: [],
};
for (const [t, s] of stats) {
  if (!yahooSymbol(t)) buckets.unusable.push([t, s]);
  else if (secTickers.has(t)) buckets.secListed.push([t, s]);
  else if (US_SHAPE.test(t)) buckets.usShapeNotListed.push([t, s]);
  else buckets.nonUsShape.push([t, s]);
}

const totalValue = [...stats.values()].reduce((a, s) => a + s.value, 0);
const totalRows = [...stats.values()].reduce((a, s) => a + s.rows, 0);
const show = (name, list, note) => {
  const rows = list.reduce((a, [, s]) => a + s.rows, 0);
  const value = list.reduce((a, [, s]) => a + s.value, 0);
  console.log(`  ${name.padEnd(26)} ${String(list.length).padStart(5)} tickers  ${String(rows).padStart(7)} rows (${(rows / totalRows * 100).toFixed(1)}%)  $${(value / 1e9).toFixed(1)}bn (${(value / totalValue * 100).toFixed(2)}%)  ${note}`);
};

console.log('');
console.log(`[audit] ${stats.size.toLocaleString()} distinct tickers held`);
show('on the SEC ticker list', buckets.secListed, 'US-listed operating companies');
// Not "likely delisted", which is what this said and what I reported from it.
// company_tickers.json lists operating-company filers, so an ETF (IVV, VOO,
// BND) and a foreign private issuer filing 20-F (SE) are both absent from it
// while trading normally. Checked against Yahoo: all of them price fine.
show('US shape, not SEC-listed', buckets.usShapeNotListed, 'ETFs, 20-F filers, and genuinely delisted names - mostly priceable');
show('not a US ticker shape', buckets.nonUsShape, 'WRONG - foreign venue code from OpenFIGI');
show('unusable', buckets.unusable, 'rejected before asking');

console.log('');
console.log('[audit] largest non-US-shape tickers by value held:');
for (const [t, s] of buckets.nonUsShape.sort((a, b) => b[1].value - a[1].value).slice(0, 25)) {
  console.log(`    ${t.padEnd(12)} $${(s.value / 1e9).toFixed(2)}bn  ${String(s.rows).padStart(5)} rows  ${s.first}..${s.last}`);
}

console.log('');
console.log('[audit] largest unusable tickers by value (rejected before asking):');
for (const [t, s2] of buckets.unusable.sort((a, b) => b[1].value - a[1].value).slice(0, 25)) {
  console.log(`    ${JSON.stringify(t).padEnd(18)} $${(s2.value / 1e9).toFixed(2)}bn  ${String(s2.rows).padStart(5)} rows  ${s2.first}..${s2.last}`);
}

console.log('');
console.log('[audit] largest US-shape-but-not-SEC-listed by value (mostly ETFs):');
for (const [t, s] of buckets.usShapeNotListed.sort((a, b) => b[1].value - a[1].value).slice(0, 20)) {
  console.log(`    ${t.padEnd(8)} $${(s.value / 1e9).toFixed(2)}bn  ${String(s.rows).padStart(5)} rows  ${s.first}..${s.last}`);
}

// ---- what is already in the price table -----------------------------------

const existing = await all(() => client
  .from('institutional_security_prices')
  .select('ticker,source,security_type,price_date')
  .order('ticker'), 1000);
console.log('');
console.log(`[audit] institutional_security_prices holds ${existing.length.toLocaleString()} rows`);
const bySource = new Map();
for (const r of existing) {
  const k = `${r.source} / ${r.security_type}`;
  const s = bySource.get(k) || { n: 0, tickers: new Set(), min: r.price_date, max: r.price_date };
  s.n += 1; s.tickers.add(r.ticker);
  if (r.price_date < s.min) s.min = r.price_date;
  if (r.price_date > s.max) s.max = r.price_date;
  bySource.set(k, s);
}
for (const [k, s] of bySource) {
  console.log(`    ${k.padEnd(34)} ${String(s.n).padStart(8)} rows  ${s.tickers.size} tickers  ${s.min}..${s.max}`);
}

// ---- the real size of the backfill ----------------------------------------

const TRADING_DAYS_PER_YEAR = 252;
let estimate = 0;
for (const [t, s] of [...buckets.secListed, ...buckets.usShapeNotListed]) {
  const years = (Date.parse(s.last) - Date.parse(s.first)) / 31_557_600_000 + 0.35;
  estimate += Math.max(1, Math.round(years * TRADING_DAYS_PER_YEAR));
}
console.log('');
console.log(`[audit] realistic backfill: ~${estimate.toLocaleString()} rows across ${(buckets.secListed.length + buckets.usShapeNotListed.length).toLocaleString()} US symbols`);
console.log('[audit] (the dry run said 9.5m because it assumed every symbol needs the full 2019-2026 span)');
