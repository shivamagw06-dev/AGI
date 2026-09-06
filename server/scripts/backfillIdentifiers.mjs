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
    console.log(`[identifiers] ${result.candidates} security(ies) would be attempted,`
      + ' ranked by value summed across every manager-quarter observed.');
    console.log('[identifiers] "latest" is the most recent quarter\'s disclosed value;'
      + ' "obs" is manager-quarter rows, which is why it exceeds the manager count.\n');
    for (const row of result.sample) {
      const m = (v) => `$${(v / 1e6).toFixed(0)}M`;
      console.log(`  ${row.cusip}  ${String(row.issuer_name || '—').slice(0, 34).padEnd(34)}`
        + `  ${m(row.latest_value_usd).padStart(9)} latest`
        + `  ${String(row.managers).padStart(3)} mgr`
        + `  ${String(row.observations).padStart(4)} obs`
        + `  since ${row.observed_from || '?'}`);
    }
    if (result.candidates > result.sample.length) {
      console.log(`  ... and ${result.candidates - result.sample.length} more`);
    }
    console.log('\n[identifiers] re-run with --apply to resolve these.');
  } else {
    console.log(`[identifiers] coverage after:  ${pct(result.coverage_after)}`);
    const gained = result.coverage_after.mapped_rows - result.coverage_before.mapped_rows;
    console.log(`[identifiers] rows newly mapped: ${gained.toLocaleString()}`);
    console.log(`[identifiers] attempted ${result.attempted}, resolved ${result.mapped},`
      + ` applied to holdings ${result.applied ?? 0}, unresolved ${result.unresolved}`
      + (result.skipped ? `, skipped ${result.skipped} malformed` : ''));
    if (result.mapped && !result.applied) {
      console.warn('[identifiers] mappings were written but none reached the holdings table,'
        + ' so nothing downstream will change. That is a fault, not a quiet success.');
    }
    for (const problem of result.errors || []) console.warn(`[identifiers] ${problem}`);
    if (result.unresolved) {
      // This used to read "those are usually private placements, funds, or
      // securities OpenFIGI has no listing for". It was wrong, and being
      // wrong confidently cost ten runs: the securities it described that way
      // were Chubb, Linde, Accenture, Spotify, ASML and Medtronic, failing
      // because they were asked with the wrong identifier scheme. The line now
      // reports the number and declines to explain it.
      console.log(`[identifiers] ${result.unresolved} were asked and returned no listing.`
        + ' They stay unmapped rather than being guessed at. What they are is not something'
        + ' this run knows - check the issuer names before assuming they are untradeable.');
    }
    if (result.attempted >= 20 && result.unresolved >= result.attempted * 0.8) {
      // The signature of a blocked window rather than a thin tail. Candidates
      // are ranked by disclosed value and a failure keeps its rank, so a
      // cohort that cannot resolve stays at the front of the queue and is
      // re-offered every run. Ten consecutive runs converged on attempted 148
      // and unresolved 147 before anyone looked at which securities they were.
      console.warn(`[identifiers] ${result.unresolved} of ${result.attempted} failed.`
        + ' A ratio this high usually means the same cohort is being retried, not that'
        + ' the tail has been reached. Look at what they are before running this again.');
    }
  }

  console.log(`[identifiers] elapsed ${((Date.now() - started) / 1000).toFixed(1)}s\n`);
  process.exit(0);
} catch (error) {
  console.error(`[identifiers] failed after ${((Date.now() - started) / 1000).toFixed(1)}s: ${error?.message || error}`);
  process.exit(1);
}
