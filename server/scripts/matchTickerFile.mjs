/**
 * Resolve remaining identifiers against the SEC's own ticker file.
 *
 *   node scripts/matchTickerFile.mjs            # dry run
 *   node scripts/matchTickerFile.mjs --apply
 *
 * The last source available before the remainder is genuinely unresolvable.
 * OpenFIGI has already said no to most of these; the chains joined 42. What is
 * left is 11,729 identifiers, individually small and collectively 266,000 rows.
 *
 * This is the join that was unsafe with a plain company list, because an
 * issuer's name is identical across its stock, its preferred, its notes and its
 * options - matching on name alone produced WESTERN DIGITAL -> WDC for a
 * convertible note. It is safe here only because every candidate is first
 * required to be an identifier the SEC's own list calls equity.
 *
 * No vendor calls.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { indexTickerFile, proposeFromTickerFile } from '../services/tickerFileMatch.js';
import { normaliseIssuerName } from '../services/thirteenFList.js';

const APPLY = process.argv.includes('--apply');
const SEC_USER_AGENT = (process.env.SEC_USER_AGENT
  || 'AGI Institutional Research research@agarwalglobalinvestments.com').trim();

if (!getSupabaseAdminCredentials()) {
  console.error('[tickers] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
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
    if (rows.length > 2_000_000) break;
  }
  return rows;
}

console.log(`[tickers] mode=${APPLY ? 'APPLY' : 'DRY RUN'}`);

const response = await fetch('https://www.sec.gov/files/company_tickers.json',
  { headers: { 'User-Agent': SEC_USER_AGENT } });
if (!response.ok) throw new Error(`company_tickers.json: HTTP ${response.status}`);
const file = await response.json();
const { byName, ambiguous } = indexTickerFile(file, normaliseIssuerName);
console.log(`[tickers] ticker file: ${Object.keys(file).length.toLocaleString()} companies`
  + `, ${byName.size.toLocaleString()} usable names`
  + `, ${ambiguous.size.toLocaleString()} names mapping to more than one ticker (dropped)`);

const holdings = await all(() => client
  .from('institutional_holdings').select('cusip,ticker,report_date').is('put_call', null).order('cusip'));

const observedFrom = new Map();
const takenTickers = new Map();
const unmapped = new Set();
const mapped = new Set();
for (const row of holdings) {
  if (!row.cusip) continue;
  const date = String(row.report_date || '').slice(0, 10);
  if (date && (!observedFrom.has(row.cusip) || date < observedFrom.get(row.cusip))) observedFrom.set(row.cusip, date);
  if (row.ticker) { mapped.add(row.cusip); takenTickers.set(row.ticker, row.cusip); }
  else unmapped.add(row.cusip);
}
for (const cusip of mapped) unmapped.delete(cusip);
console.log(`[tickers] identifiers without a ticker: ${unmapped.size.toLocaleString()}`);

const securityRows = await all(() => client
  .from('sec_13f_securities').select('cusip,issuer_name,security_class').order('cusip'));
const securities = new Map(securityRows.map((row) => [row.cusip, row]));
console.log(`[tickers] SEC list rows: ${securities.size.toLocaleString()}`);

// The chain table is what separates a reverse split, where one ticker
// legitimately spans two identifiers, from two share classes, where it does
// not. A name cannot tell those apart.
const chainRows = await all(() => client.from('sec_13f_identity_chain').select('cusip,security_key').order('cusip'));
const keyByCusip = new Map(chainRows.map((row) => [row.cusip, row.security_key]));

const { proposals, skipped, collisions } = proposeFromTickerFile([...unmapped], {
  securities, byName, ambiguousNames: ambiguous, observedFrom, takenTickers, keyByCusip,
  normalise: normaliseIssuerName,
});

console.log(`\n[tickers] resolvable: ${proposals.length.toLocaleString()}`);
console.log('[tickers] not resolved:', Object.entries(skipped)
  .filter(([, v]) => v).map(([k, v]) => `${k} ${v.toLocaleString()}`).join(', '));
if (collisions.length) {
  console.warn(`\n[tickers] ${collisions.length} ticker(s) claimed by identifiers no chain links; all claims dropped:`);
  for (const c of collisions.slice(0, 10)) console.warn(`   ${c.ticker.padEnd(7)} ${c.cusips.join(' / ')}`);
}
for (const p of proposals.slice(0, 15)) {
  console.log(`   ${p.cusip} -> ${p.ticker.padEnd(7)} ${String(p.issuer_name).slice(0, 30).padEnd(32)} from ${p.valid_from}`);
}

if (!proposals.length) { console.log('\n[tickers] nothing to write.'); process.exit(0); }
if (!APPLY) { console.log('\n[tickers] dry run. Nothing written. Re-run with --apply.'); process.exit(0); }

console.log('\n[tickers] writing mappings...');
const CHUNK = 200;
for (let i = 0; i < proposals.length; i += CHUNK) {
  const slice = proposals.slice(i, i + CHUNK).map(({ issuer_name, ...rest }) => ({
    ...rest, issuer_name, updated_at: new Date().toISOString(),
  }));
  const { error } = await client.from('security_identifier_history').upsert(slice, { onConflict: 'cusip,valid_from' });
  if (error) throw new Error(`security_identifier_history ${i}-${i + slice.length}: ${error.message}`);
}

console.log('[tickers] applying to holdings...');
let applied = 0;
const failures = [];
for (const p of proposals) {
  const { error } = await client.from('institutional_holdings')
    .update({ ticker: p.ticker }).eq('cusip', p.cusip).is('ticker', null).gte('report_date', p.valid_from);
  if (error) failures.push(`${p.cusip}: ${error.message}`);
  else applied += 1;
  if (applied % 500 === 0) console.log(`[tickers]   ${applied}/${proposals.length}`);
}
for (const failure of failures.slice(0, 10)) console.warn(`[tickers] ${failure}`);
console.log(`[tickers] done: ${proposals.length} mapping(s) written, applied to ${applied} security(ies).`);
process.exit(0);
