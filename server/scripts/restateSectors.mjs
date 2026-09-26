/**
 * Re-derive every stored sector from its stored SIC code.
 *
 *   node server/scripts/restateSectors.mjs
 *   node server/scripts/restateSectors.mjs --apply
 *
 * The sector map gained a technology sector; the seventy rows written by the
 * map without one did not. The nightly queue would never have found them: it
 * measures how long ago a row was written, and those were written four days
 * ago. They are also, by construction, the largest positions in the book -
 * the old code classified the first sixty securities in holdings order, which
 * is a list of mega-caps - so Nvidia, Apple, Broadcom and Tesla sat in
 * Industrials and made it the largest sector on the chart at 29.6%.
 *
 * No SEC traffic. sic_code is stored on every row and the sector is a pure
 * function of it, so this is a read, a local computation and a write.
 *
 * Only `sector` changes. `industry` holds EDGAR's own description of the
 * registrant where there is one, which is better than any label of ours; and
 * a row whose SIC code cannot be read or is not covered is left exactly as it
 * is, rather than being downgraded to Unclassified on a missing input.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { paged } from '../services/institutionalResearchLayerService.js';
import { classifySic } from '../services/sicSectors.js';
import { restatements, restated, movementSummary } from '../services/sectorRestatement.js';

const APPLY = process.argv.includes('--apply');
const CHUNK = 500;

if (!getSupabaseAdminCredentials()) {
  console.error('[restate] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

async function main() {
  console.log(`[restate] mode: ${APPLY ? 'APPLY - this writes' : 'dry run - nothing is written'}`);

  const rows = await paged(
    () => client.from('institutional_security_classifications').select('*').order('security_key').order('valid_from'),
    { label: 'classifications' },
  );
  console.log(`[restate] ${rows.length.toLocaleString()} classification row(s) read  (${elapsed()}s)`);

  const changes = restatements(rows, classifySic);
  console.log(`[restate] ${changes.length.toLocaleString()} row(s) would change sector`);
  for (const { move, count } of movementSummary(changes)) {
    console.log(`[restate]   ${String(count).padStart(5)}  ${move}`);
  }
  // Named, because these are the ones whose weight actually moves the chart
  // and the ones a reader would notice being wrong.
  const notable = changes.filter((c) => ['NVDA', 'AAPL', 'MSFT', 'AVGO', 'TSLA', 'AMD', 'GOOGL', 'META', 'AMZN'].includes(String(c.row.ticker || '').toUpperCase()));
  for (const { row, from, to } of notable) console.log(`[restate]   ${row.ticker}: ${from} -> ${to}  (SIC ${row.sic_code})`);

  if (!APPLY) {
    console.log('[restate] dry run only. Re-run with --apply to write.');
    return;
  }

  const writes = changes.map(restated);
  let written = 0;
  for (let index = 0; index < writes.length; index += CHUNK) {
    const { error } = await client.from('institutional_security_classifications')
      .upsert(writes.slice(index, index + CHUNK), { onConflict: 'security_key,valid_from,source' });
    if (error) throw new Error(`writing at ${index}: ${error.message}`);
    written += Math.min(CHUNK, writes.length - index);
  }
  console.log(`[restate] ${written.toLocaleString()} row(s) restated in ${elapsed()}s`);
}

main().catch((error) => {
  console.error(`[restate] ${error.message}`);
  process.exit(1);
});
