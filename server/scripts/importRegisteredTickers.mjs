#!/usr/bin/env node
/**
 * Load the SEC's current ticker register.
 *
 *   node server/scripts/importRegisteredTickers.mjs            # dry run
 *   node server/scripts/importRegisteredTickers.mjs --apply
 *
 * Two public files, no credentials: company_tickers.json lists operating
 * companies and company_tickers_exchange.json adds everything that lists on an
 * exchange, which is where the ETFs and trusts are. secDirectory already
 * fetches and merges them for the classifier, so this stores what that returns
 * rather than parsing the same files a second way.
 *
 * The point is narrow. sec_issuer_tickers is built from Form 3/4/5 and cannot
 * see a foreign private issuer, because Section 16 does not apply to one - so
 * CyberArk, Carnival plc, Bancolombia, WNS Holdings and Golden Ocean are all
 * absent from it while being perfectly real US-listed symbols. Being absent is
 * what marks them as venue codes, and being marked is what makes the price
 * backfill skip them, so nothing ever prices them and the absence never
 * resolves. This table breaks that loop.
 *
 * It answers one question - does the SEC list this symbol - and carries no
 * dates, because the register publishes none. Anything needing to know what a
 * ticker meant in 2019 reads sec_issuer_tickers, whose windows are real.
 *
 * Re-run whenever; it replaces what it finds by primary key.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { secDirectory } from '../services/institutionalResearchLayerService.js';

const APPLY = process.argv.includes('--apply');

if (!getSupabaseAdminCredentials()) {
  console.error('[registry] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();

async function main() {
  console.log(`[registry] mode=${APPLY ? 'APPLY' : 'DRY RUN'}`);
  const directory = await secDirectory();
  const rows = [...directory.entries()]
    .filter(([ticker]) => ticker)
    .map(([ticker, entry]) => ({
      ticker,
      cik: String(entry?.cik || ''),
      issuer_name: entry?.title || null,
      kind: entry?.kind === 'fund' ? 'fund' : 'company',
      refreshed_at: new Date().toISOString(),
    }))
    // A row with no CIK is not a registration; the column is not null and a
    // blank one would assert something the file did not say.
    .filter((row) => row.cik);

  const funds = rows.filter((row) => row.kind === 'fund').length;
  console.log(`[registry] ${rows.length.toLocaleString()} listed symbol(s): ${(rows.length - funds).toLocaleString()} company, ${funds.toLocaleString()} fund`);

  // The five this exists for, named so a run that quietly returns nothing is
  // visible as a failure rather than as an empty success.
  const WATCH = ['CYBR', 'CCL', 'CIB', 'WNS', 'GOGL'];
  const present = WATCH.filter((ticker) => directory.has(ticker));
  console.log(`[registry] foreign private issuers found: ${present.join(', ') || 'none'}`);
  if (present.length !== WATCH.length) {
    console.warn(`[registry] expected all of ${WATCH.join(', ')}; missing ${WATCH.filter((t) => !present.includes(t)).join(', ')}`);
  }

  if (!APPLY) {
    console.log('[registry] dry run only. Re-run with --apply to write.');
    return;
  }

  for (let index = 0; index < rows.length; index += 500) {
    const { error } = await client.from('sec_registered_tickers')
      .upsert(rows.slice(index, index + 500), { onConflict: 'ticker' });
    if (error) throw new Error(`writing at ${index}: ${error.message}`);
  }
  console.log(`[registry] ${rows.length.toLocaleString()} symbol(s) written`);
  console.log('[registry] re-run recoverVenueTickers.mjs; the loop these were stuck in is now open.');
}

main().catch((error) => {
  console.error(`[registry] ${error.message}`);
  process.exit(1);
});
