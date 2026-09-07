/**
 * Recover US tickers for holdings wearing a foreign venue's symbol.
 *
 *   node server/scripts/recoverVenueTickers.mjs            # dry run
 *   node server/scripts/recoverVenueTickers.mjs --apply
 *
 * The audit found 193 tickers - $622bn of holdings - that are not US symbols
 * at all. They come from preferredFigiCandidate preferring a US listing but
 * not requiring one: a CUSIP OpenFIGI has no US line for takes whichever
 * venue it does have, and European venues name their lines by currency. So
 * Honeywell is HONGBP, Lam Research LRCXEUR, Carnival CCL1EUR.
 *
 * Prices are the smaller half of the damage. The screener and consensus
 * tables key on ticker, so HONGBP and HON are two different companies and
 * Honeywell's institutional ownership is split between them.
 *
 * Written to security_identifier_history, not to institutional_holdings.
 * Ingestion deletes and re-inserts a filing's holdings from XML, which
 * carries no ticker, so a correction written onto the holding itself lasts
 * until that filing is next collected and no longer.
 *
 * Every recovery is checked against the SEC's own company name before it is
 * proposed. No vendor calls.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { recoverTicker } from '../services/venueTicker.js';
import { conflictingOwner, proposedWindow } from '../services/mappingWindow.js';

const APPLY = process.argv.includes('--apply');
const SEC_UA = (process.env.SEC_USER_AGENT || 'AGI Institutional Research research@agarwalglobalinvestments.com').trim();

if (!getSupabaseAdminCredentials()) {
  console.error('[venue] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
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

// ---- the SEC's own ticker -> company name ---------------------------------

const resp = await fetch('https://www.sec.gov/files/company_tickers.json', { headers: { 'User-Agent': SEC_UA } });
if (!resp.ok) throw new Error(`company_tickers.json: HTTP ${resp.status}`);
const secByTicker = new Map();
for (const entry of Object.values(await resp.json())) {
  const ticker = String(entry.ticker || '').toUpperCase();
  if (ticker) secByTicker.set(ticker, String(entry.title || ''));
}
console.log(`[venue] SEC lists ${secByTicker.size.toLocaleString()} tickers`);

// ---- holdings wearing a non-US symbol -------------------------------------

const US_SHAPE = /^[A-Z]{1,5}(-[A-Z])?$/;
const holdings = await all(() => client
  .from('institutional_holdings')
  .select('cusip,ticker,issuer_name,report_date,value_usd')
  .not('ticker', 'is', null)
  .is('put_call', null)
  .order('cusip'));

const suspect = new Map();
for (const h of holdings) {
  const t = String(h.ticker).toUpperCase();
  if (US_SHAPE.test(t)) continue;
  const id = `${h.cusip}|${t}`;
  const cur = suspect.get(id) || { cusip: h.cusip, ticker: t, issuer_name: h.issuer_name, rows: 0, value: 0, earliest: h.report_date, latest: h.report_date };
  cur.rows += 1;
  cur.value += Number(h.value_usd) || 0;
  if (h.report_date < cur.earliest) cur.earliest = h.report_date;
  if (h.report_date > cur.latest) cur.latest = h.report_date;
  if (!cur.issuer_name && h.issuer_name) cur.issuer_name = h.issuer_name;
  suspect.set(id, cur);
}
console.log(`[venue] ${suspect.size} (cusip, non-US ticker) pairs to examine`);

// ---- propose --------------------------------------------------------------

const recovered = [];
const refused = [];
for (const s of suspect.values()) {
  const r = recoverTicker(s.ticker, s.issuer_name, secByTicker);
  if (r.ticker) recovered.push({ ...s, to: r.ticker });
  else refused.push({ ...s, reason: r.reason });
}

const sum = (list) => list.reduce((a, x) => a + x.value, 0);
console.log('');
console.log(`[venue] recovered ${recovered.length}  ($${(sum(recovered) / 1e9).toFixed(1)}bn)`);
console.log(`[venue] refused   ${refused.length}  ($${(sum(refused) / 1e9).toFixed(1)}bn)`);

console.log('');
console.log('[venue] recoveries, largest first:');
for (const r of recovered.sort((a, b) => b.value - a.value).slice(0, 40)) {
  console.log(`  ${r.ticker.padEnd(12)} -> ${r.to.padEnd(6)}  $${(r.value / 1e9).toFixed(2)}bn  ${r.cusip}  ${String(r.issuer_name || '').slice(0, 40)}`);
}

console.log('');
console.log('[venue] refused, largest first (these stay unresolved):');
for (const r of refused.sort((a, b) => b.value - a.value).slice(0, 25)) {
  console.log(`  ${r.ticker.padEnd(12)} $${(r.value / 1e9).toFixed(2)}bn  ${String(r.issuer_name || '(no name)').slice(0, 34).padEnd(34)} ${r.reason}`);
}

if (!APPLY) {
  console.log('');
  console.log('[venue] DRY RUN - nothing written. Re-run with --apply.');
  process.exit(0);
}

// ---- write ----------------------------------------------------------------

// A ticker already claimed over the same dates is not taken. Ownership is a
// question about a period, not about a ticker: the resolver picks the mapping
// valid at a date, so one symbol moving from an old CUSIP to a new one after
// a corporate action is the model working, not a collision. What must not
// happen is two CUSIPs claiming one ticker over the same stretch - Carnival
// Corp and Carnival plc trade together as CCL and CUK, and giving CCL to both
// would put one company's price on the other's position.
const existing = await all(() => client
  .from('security_identifier_history')
  .select('cusip,ticker,valid_from,valid_to')
  .not('ticker', 'is', null)
  .order('cusip'));
const ownersOf = new Map();
for (const row of existing) {
  const t = String(row.ticker).toUpperCase();
  if (!ownersOf.has(t)) ownersOf.set(t, []);
  ownersOf.get(t).push(row);
}

const latestReportDate = holdings.reduce((a, h) => (h.report_date > a ? h.report_date : a), '');

const writes = [];
const conflicts = [];
for (const r of recovered) {
  // Bounded to the dates actually held. An open-ended claim would run to the
  // end of time and block whichever security takes the symbol over next.
  const window = proposedWindow(r, latestReportDate);
  const owner = conflictingOwner(ownersOf.get(r.to), r.cusip, window);
  if (owner) { conflicts.push({ ...r, owner, window }); continue; }
  writes.push({
    cusip: r.cusip,
    ticker: r.to,
    issuer_name: r.issuer_name || null,
    valid_from: window.from,
    valid_to: window.to,
    security_key: r.cusip,
    source: 'venue_symbol_recovery',
    manually_verified: false,
    updated_at: new Date().toISOString(),
  });
}

if (conflicts.length) {
  console.log('');
  console.log(`[venue] ${conflicts.length} skipped - another CUSIP holds the ticker over the same dates:`);
  for (const c of conflicts.slice(0, 25)) {
    console.log(`  ${c.ticker.padEnd(10)} -> ${c.to.padEnd(6)} ours ${c.cusip} wants ${c.window.from}..${c.window.to || 'open'};`
      + ` ${c.owner.cusip} holds ${c.owner.valid_from}..${c.owner.valid_to || 'open'}`);
  }
}

let written = 0;
for (let i = 0; i < writes.length; i += 500) {
  const chunk = writes.slice(i, i + 500);
  const { error } = await client.from('security_identifier_history').upsert(chunk, { onConflict: 'cusip,valid_from' });
  if (error) throw new Error(`upsert: ${error.message}`);
  written += chunk.length;
}
console.log('');
console.log(`[venue] wrote ${written} mappings to security_identifier_history.`);

// The mapping alone changes nothing that reads holdings. Ingestion attaches
// tickers from this table when a filing is collected, but the rows already
// stored keep whatever they were written with - so the screener still shows
// HONGBP, and the price backfill still skips it as a foreign venue code. The
// correction has to be applied to the holdings that exist.
//
// matchTickerFile and propagateChainTickers do the same update guarded by
// .is('ticker', null), because they fill blanks. This one replaces a value
// that is present and wrong, so the guard is the wrong ticker itself: only
// rows carrying that exact venue code under that exact CUSIP are touched.
let patched = 0;
for (const r of recovered) {
  if (!writes.some((w) => w.cusip === r.cusip && w.ticker === r.to)) continue;
  const { error, count } = await client
    .from('institutional_holdings')
    .update({ ticker: r.to }, { count: 'exact' })
    .eq('cusip', r.cusip)
    .eq('ticker', r.ticker);
  if (error) throw new Error(`holdings update ${r.ticker}: ${error.message}`);
  patched += count || 0;
}
console.log(`[venue] corrected ${patched.toLocaleString()} holding rows.`);
console.log('[venue] Run the price backfill again to price them.');
