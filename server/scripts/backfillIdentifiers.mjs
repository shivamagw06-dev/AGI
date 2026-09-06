#!/usr/bin/env node
/**
 * Resolve CUSIPs to tickers, most valuable first.
 *
 * About ninety per cent of holdings rows carry no ticker. That is why the stock
 * search returns bare CUSIPs instead of TSM, why the screener stays behind
 * admin auth, and why price coverage is zero: a price cannot be fetched for a
 * security that has not been named.
 *
 * Enrichment already runs as a tail on every collection with a small limit,
 * which keeps a healthy table healthy and will never close a gap this size.
 * This is the same routine with the limit under the operator's control.
 *
 *   node server/scripts/backfillIdentifiers.mjs                # dry run
 *   node server/scripts/backfillIdentifiers.mjs --apply
 *   node server/scripts/backfillIdentifiers.mjs --apply --limit 2000
 *
 * Dry run is the default. It writes nothing and shows which securities would be
 * attempted, in the order they would be attempted, because a bulk write of
 * thousands of identifier mappings deserves to be read first.
 *
 * OpenFIGI is rate limited - 25 requests a minute without a key, far more with
 * one - so a large limit takes a while. OPENFIGI_API_KEY is optional and makes
 * it substantially faster.
 */

import { runIdentifierBackfill } from '../services/institutionalHoldingsService.js';

const args = process.argv.slice(2);
const flag = (name, fallback = null) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : fallback;
};
const APPLY = args.includes('--apply');
const LIMIT = Math.min(Math.max(Number(flag('limit', '500')) || 500, 1), 5000);

const missing = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY'].filter((k) => !process.env[k]);
if (missing.length) {
  console.error(`[identifiers] refusing to start: ${missing.join(' and ')} not set`);
  process.exit(78);
}
process.env.INSTITUTIONAL_AUTO_REFRESH = 'false';

const started = Date.now();
console.log(`[identifiers] mode=${APPLY ? 'APPLY' : 'DRY RUN'} limit=${LIMIT}`
  + `${process.env.OPENFIGI_API_KEY ? '' : '  (no OPENFIGI_API_KEY — throttled to 25 requests a minute)'}`);
if (!APPLY) console.log('[identifiers] nothing will be written. Re-run with --apply.');

try {
  const result = await runIdentifierBackfill({ limit: LIMIT, apply: APPLY });

  const pct = (c) => `${c.mapped_rows.toLocaleString()}/${c.total_rows.toLocaleString()} rows (${c.mapped_pct}%)`;
  console.log(`\n[identifiers] coverage before: ${pct(result.coverage_before)}`);

  if (!result.applied) {
    console.log(`[identifiers] ${result.candidates} security(ies) would be attempted, highest disclosed value first:\n`);
    for (const row of result.sample) {
      console.log(`  ${row.cusip}  ${String(row.issuer_name || '—').slice(0, 38).padEnd(38)}`
        + `  $${(row.disclosed_value_usd / 1e6).toFixed(1)}M`
        + `  ${row.reported_by} manager(s)`
        + `  seen from ${row.observed_from || '?'}`);
    }
    if (result.candidates > result.sample.length) {
      console.log(`  ... and ${result.candidates - result.sample.length} more`);
    }
    console.log('\n[identifiers] re-run with --apply to resolve these.');
  } else {
    console.log(`[identifiers] coverage after:  ${pct(result.coverage_after)}`);
    const gained = result.coverage_after.mapped_rows - result.coverage_before.mapped_rows;
    console.log(`[identifiers] rows newly mapped: ${gained.toLocaleString()}`);
    console.log(`[identifiers] attempted ${result.attempted}, mapped ${result.mapped}, unresolved ${result.unresolved}`);
    for (const problem of result.errors || []) console.warn(`[identifiers] ${problem}`);
    if (result.unresolved) {
      console.log(`[identifiers] ${result.unresolved} could not be resolved. Those are usually private`
        + ' placements, funds, or securities OpenFIGI has no listing for, and they stay unmapped'
        + ' rather than being guessed at.');
    }
  }

  console.log(`[identifiers] elapsed ${((Date.now() - started) / 1000).toFixed(1)}s\n`);
  process.exit(0);
} catch (error) {
  console.error(`[identifiers] failed after ${((Date.now() - started) / 1000).toFixed(1)}s: ${error?.message || error}`);
  process.exit(1);
}
