/**
 * Bound identifier mappings that claim a ticker from 1900.
 *
 *   node server/scripts/boundMappingWindows.mjs            # dry run
 *   node server/scripts/boundMappingWindows.mjs --apply
 *
 * The early identifier backfill wrote valid_from as 1900-01-01. The vendor was
 * answering what a CUSIP maps to now, and storing that as valid from 1900
 * asserts today's ticker applied to every filing ever made -
 * identifierBackfill.js says as much in its own comments.
 *
 * The practical cost is that an unbounded start claims the ticker for all
 * time, so no succession can take it afterwards. Ten venue-ticker recoveries
 * covering $279bn are refused because an incumbent holds their symbol from
 * 1900 to open, and the window check written for that case cannot help while
 * one side of the comparison is infinite.
 *
 * valid_from is part of the table's key, so moving it is an insert of the
 * corrected row followed by a delete of the placeholder - in that order, so a
 * failure between them leaves the security mapped twice rather than not at
 * all. Resolution takes the newest applicable mapping, so a brief duplicate
 * resolves the same way; a gap would not resolve at all.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { firstSeenByCusip, planBounds } from '../services/mappingBounds.js';

const APPLY = process.argv.includes('--apply');

if (!getSupabaseAdminCredentials()) {
  console.error('[bounds] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
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

console.log(`[bounds] mode=${APPLY ? 'APPLY' : 'DRY RUN'}`);

const mappings = await all(() => client
  .from('security_identifier_history')
  .select('*')
  .lte('valid_from', '1900-01-01')
  .order('cusip'));
console.log(`[bounds] mappings starting at or before 1900-01-01: ${mappings.length.toLocaleString()}`);
if (!mappings.length) { console.log('[bounds] nothing to bound.'); process.exit(0); }

const holdings = await all(() => client
  .from('institutional_holdings')
  .select('cusip,report_date')
  .order('cusip'));
console.log(`[bounds] holdings rows read: ${holdings.length.toLocaleString()}`);

const firstSeen = firstSeenByCusip(holdings);
const { plan, skipped } = planBounds(mappings, firstSeen);

console.log('');
console.log(`[bounds] to bound: ${plan.length.toLocaleString()}`);
console.log(`[bounds] left alone: ${skipped.neverObserved} never observed in holdings, ${skipped.alreadyBounded} already bounded, ${skipped.alreadyCorrect} already correct`);
console.log('');
console.log('[bounds] sample of what would change:');
for (const row of plan.slice(0, 20)) {
  console.log(`  ${row.mapping.cusip}  ${String(row.mapping.ticker || '(none)').padEnd(8)} ${row.was} -> ${row.from}`);
}

if (!APPLY) {
  console.log('');
  console.log('[bounds] DRY RUN - nothing written. Re-run with --apply.');
  process.exit(0);
}

// Insert corrected, then delete the placeholder. A failure between the two
// leaves the security mapped twice, which resolves the same way; a gap would
// leave it unmapped.
let written = 0;
let removed = 0;
for (let i = 0; i < plan.length; i += 200) {
  const slice = plan.slice(i, i + 200);
  // The id is destructured out, not set to undefined. A key that is present
  // with an undefined value still counts as a key, and the client fills the
  // gaps across a batch with explicit nulls - which defeats the column's
  // default and fails its not-null constraint. The column has to be absent
  // from every row for gen_random_uuid() to apply.
  const rows = slice.map(({ mapping, from }) => {
    const { id, ...rest } = mapping;
    return { ...rest, valid_from: from, updated_at: new Date().toISOString() };
  });
  const { error } = await client
    .from('security_identifier_history')
    .upsert(rows, { onConflict: 'cusip,valid_from' });
  if (error) throw new Error(`insert corrected: ${error.message}`);
  written += rows.length;

  for (const { mapping } of slice) {
    const { error: delError } = await client
      .from('security_identifier_history')
      .delete()
      .eq('cusip', mapping.cusip)
      .eq('valid_from', mapping.valid_from);
    if (delError) throw new Error(`delete placeholder ${mapping.cusip}: ${delError.message}`);
    removed += 1;
  }
  console.log(`[bounds] ${Math.min(i + 200, plan.length)}/${plan.length}`);
}

console.log('');
console.log(`[bounds] wrote ${written.toLocaleString()} bounded mapping(s), removed ${removed.toLocaleString()} placeholder(s).`);
console.log('[bounds] Re-run recoverVenueTickers.mjs to see what the bounded windows release.');
