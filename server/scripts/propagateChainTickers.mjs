/**
 * Give unmapped identifiers the ticker their sibling already carries.
 *
 *   node scripts/propagateChainTickers.mjs            # dry run
 *   node scripts/propagateChainTickers.mjs --apply
 *
 * Enrichment expands a chain only from the mappings it resolved on that run,
 * so a security whose ticker was found last week is never joined to its other
 * identifier. 1,872 unmapped identifiers have a sibling carrying a ticker right
 * now. None of them is waiting on a vendor; the answer was bought already,
 * under a different number, and nothing went looking for it.
 *
 * No vendor calls are made here at all.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { proposeFromChains } from '../services/chainPropagation.js';

const APPLY = process.argv.includes('--apply');

if (!getSupabaseAdminCredentials()) {
  console.error('[chains] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();

/** Page through a table, because PostgREST caps a single response. */
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

console.log(`[chains] mode=${APPLY ? 'APPLY' : 'DRY RUN'}`);

// Every identifier our holdings carry, with the ticker if it has one and the
// earliest date it was filed. The earliest date is what a proposal is allowed
// to claim from - a mapping may not reach back before the evidence for it.
const holdings = await all(() => client
  .from('institutional_holdings')
  .select('cusip,ticker,report_date')
  .is('put_call', null)
  .order('cusip'));

const known = new Map();
const observedFrom = new Map();
const unmapped = new Set();
for (const row of holdings) {
  if (!row.cusip) continue;
  const date = String(row.report_date || '').slice(0, 10);
  if (date && (!observedFrom.has(row.cusip) || date < observedFrom.get(row.cusip))) {
    observedFrom.set(row.cusip, date);
  }
  if (row.ticker) known.set(row.cusip, row.ticker);
  else unmapped.add(row.cusip);
}
// An identifier with some rows resolved and some not is not unmapped; it is
// partly applied, and enrichment's own apply step covers that.
for (const cusip of known.keys()) unmapped.delete(cusip);

console.log(`[chains] identifiers in holdings: ${(known.size + unmapped.size).toLocaleString()}`
  + `  with a ticker: ${known.size.toLocaleString()}  without: ${unmapped.size.toLocaleString()}`);

const chain = await all(() => client.from('sec_13f_identity_chain').select('cusip,security_key').order('cusip'));
const keyByCusip = new Map();
const cusipsByKey = new Map();
for (const row of chain) {
  keyByCusip.set(row.cusip, row.security_key);
  if (!cusipsByKey.has(row.security_key)) cusipsByKey.set(row.security_key, []);
  cusipsByKey.get(row.security_key).push(row.cusip);
}
console.log(`[chains] chain rows: ${chain.length.toLocaleString()}, distinct securities: ${cusipsByKey.size.toLocaleString()}`);

const { proposals, conflicts } = proposeFromChains([...unmapped], { known, keyByCusip, cusipsByKey, observedFrom });

console.log(`\n[chains] identifiers resolvable from a sibling: ${proposals.length.toLocaleString()}`);
if (conflicts.length) {
  // Reported, never resolved by choosing. Two tickers in one chain means the
  // chain is wrong, and picking a side puts one company's ticker on another
  // company's holdings.
  console.warn(`[chains] ${conflicts.length} chain(s) carry more than one ticker and are left alone:`);
  for (const c of conflicts.slice(0, 10)) console.warn(`   ${c.cusip}  ${c.tickers.join(' / ')}`);
}
for (const p of proposals.slice(0, 12)) {
  console.log(`   ${p.cusip} -> ${p.ticker.padEnd(7)} from ${p.source.replace('chain:', '')}, claiming from ${p.valid_from}`);
}

if (!proposals.length) {
  console.log('\n[chains] nothing to propagate.');
  process.exit(0);
}
if (!APPLY) {
  console.log('\n[chains] dry run. Nothing written. Re-run with --apply.');
  process.exit(0);
}

console.log('\n[chains] writing mappings...');
const CHUNK = 200;
for (let i = 0; i < proposals.length; i += CHUNK) {
  const slice = proposals.slice(i, i + CHUNK).map((p) => ({ ...p, updated_at: new Date().toISOString() }));
  const { error } = await client.from('security_identifier_history').upsert(slice, { onConflict: 'cusip,valid_from' });
  if (error) throw new Error(`security_identifier_history ${i}-${i + slice.length}: ${error.message}`);
}

// Then apply them to the holdings, one statement per security.
//
// Writing the mapping table alone changes nothing anyone can see: every
// downstream reader takes institutional_holdings.ticker. A run once reported
// "mapped 209" while coverage sat unmoved, because the two numbers were
// measuring different tables.
console.log('[chains] applying to holdings...');
let applied = 0;
const failures = [];
for (const p of proposals) {
  const { error } = await client.from('institutional_holdings')
    .update({ ticker: p.ticker })
    .eq('cusip', p.cusip)
    .is('ticker', null)
    .gte('report_date', p.valid_from);
  if (error) failures.push(`${p.cusip}: ${error.message}`);
  else applied += 1;
  if (applied % 250 === 0) console.log(`[chains]   ${applied}/${proposals.length}`);
}
for (const failure of failures.slice(0, 10)) console.warn(`[chains] ${failure}`);
console.log(`[chains] done: ${proposals.length} mapping(s) written, applied to ${applied} security(ies).`);
process.exit(0);
