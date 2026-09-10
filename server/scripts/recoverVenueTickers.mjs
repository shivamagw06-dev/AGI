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
import { namesByTicker } from '../services/issuerTickerRegistry.js';
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

// What tickers meant in the past, from SEC bulk Form 345 submissions. The live
// register answers for a live holding and cannot answer for a past one, and a
// decade of 13F holdings is mostly past ones. Consulted only where the live
// register has nothing.
const registryRows = [];
for (let from = 0; ; from += 1000) {
  const { data, error } = await client
    .from('sec_issuer_tickers')
    .select('ticker,issuer_name,first_seen,last_seen')
    .order('ticker').order('first_seen')
    .range(from, from + 999);
  // Absent is a degraded run, not a failed one: without it the behaviour is
  // exactly what it was before the table existed.
  if (error) { console.warn(`[venue] historical registry unavailable: ${error.message}`); break; }
  registryRows.push(...(data || []));
  if (!data || data.length < 1000) break;
}
const registry = namesByTicker(registryRows);
console.log(`[venue] past filings name ${registry.size.toLocaleString()} ticker(s) across ${registryRows.length.toLocaleString()} issuer/ticker pair(s)`);

// ---- holdings wearing a non-US symbol -------------------------------------

// Found in the database, not by paging the whole table.
//
// This read every holdings row - 2.6 million, about two thousand six hundred
// requests - to keep the two hundred whose ticker is not US-shaped. The same
// read had already stopped working in the price backfill with `canceling
// statement due to statement timeout`, and the pattern being matched is one
// the database can apply while it scans.
const suspect = new Map();
for (let from = 0; ; from += 1000) {
  const { data, error } = await client
    .rpc('institutional_venue_ticker_candidates').range(from, from + 999);
  if (error) throw new Error(`reading venue candidates: ${error.message}`);
  for (const row of data || []) {
    suspect.set(`${row.cusip}|${row.ticker}`, {
      cusip: row.cusip,
      ticker: row.ticker,
      issuer_name: row.issuer_name,
      rows: Number(row.rows) || 0,
      value: Number(row.value) || 0,
      earliest: row.earliest,
      latest: row.latest,
    });
  }
  if (!data || data.length < 1000) break;
}
console.log(`[venue] ${suspect.size} (cusip, non-US ticker) pairs to examine`);

// ---- propose --------------------------------------------------------------

const recovered = [];
const refused = [];
for (const s of suspect.values()) {
  // The window is the holding's own dates, so a ticker that changed hands
  // resolves to whoever owned it while this position was held.
  const r = recoverTicker(s.ticker, s.issuer_name, secByTicker, {
    registry,
    window: { earliest: s.earliest, latest: s.latest },
  });
  if (r.ticker) recovered.push({ ...s, to: r.ticker, via: r.via, weak: Boolean(r.weak) });
  else refused.push({ ...s, reason: r.reason });
}

const sum = (list) => list.reduce((a, x) => a + x.value, 0);
console.log('');
console.log(`[venue] recovered ${recovered.length}  ($${(sum(recovered) / 1e9).toFixed(1)}bn)`);
console.log(`[venue] refused   ${refused.length}  ($${(sum(refused) / 1e9).toFixed(1)}bn)`);
const weak = recovered.filter((r) => r.weak);
if (weak.length) console.log(`[venue] of the recoveries, ${weak.length} rest on a single word  ($${(sum(weak) / 1e9).toFixed(1)}bn)`);

console.log('');
console.log('[venue] recoveries, largest first:');
for (const r of recovered.sort((a, b) => b.value - a.value).slice(0, 40)) {
  console.log(`  ${r.ticker.padEnd(12)} -> ${r.to.padEnd(6)}  $${(r.value / 1e9).toFixed(2)}bn  ${r.cusip}  ${String(r.issuer_name || '').slice(0, 40)}`);
}

if (weak.length) {
  // Listed apart from the rest because the evidence is thinner, not because
  // the answer is wrong. One word carried the whole match - distinctive for
  // SKECHERS, generic for GOLD, and identical in shape either way. NEW GOLD
  // INC CDA reduces to GOLD/CDA because NEW is dropped as filer noise, and a
  // registry name reducing to GOLD alone matches it; New Gold trades as NGD.
  console.log('');
  console.log('[venue] recoveries resting on one word - read these before applying:');
  for (const r of [...weak].sort((a, b) => b.value - a.value)) {
    console.log(`  ${r.ticker.padEnd(12)} -> ${String(r.to).padEnd(6)}  $${(r.value / 1e9).toFixed(2)}bn  ${String(r.issuer_name || '').slice(0, 40)}`);
  }
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

// The newest report date in the whole table, not the newest among the
// candidates. It decides whether a mapping stays open-ended, and if no
// venue-coded holding happens to be current then the newest of those is older
// than the corpus - so the candidate matching it would be read as still held
// and written as an open-ended claim on a symbol nobody holds any more,
// blocking whichever security takes it over next.
//
// Asked of institutional_filings, not institutional_holdings. The holdings
// table has 2.6M rows and no index on report_date alone, so even `order by
// report_date desc limit 1` exceeds the statement timeout - the third query
// today that was fine at the old size and is not at this one.
//
// Filings carry the same as-of date in about two thousand rows. Where the two
// differ they differ safely: a filing whose table could not be parsed has a
// report_date and no holdings, so the filings maximum can only be newer, and a
// newer as-of date closes windows rather than leaving them open. An
// over-closed window is a mapping that stops early; an over-open one blocks
// whichever security takes the symbol over next.
const { data: newestRows, error: newestError } = await client
  .from('institutional_filings')
  .select('report_date')
  .eq('is_active', true)
  .order('report_date', { ascending: false })
  .limit(1);
if (newestError) throw new Error(`reading the newest report date: ${newestError.message}`);
const latestReportDate = newestRows?.[0]?.report_date || '';
if (!latestReportDate) throw new Error('no active filings found; refusing to propose windows against an unknown as-of date');

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
