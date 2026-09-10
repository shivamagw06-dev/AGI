/**
 * Classify every security in the current book, in one run.
 *
 *   node server/scripts/backfillClassifications.mjs
 *   node server/scripts/backfillClassifications.mjs --apply
 *   node server/scripts/backfillClassifications.mjs --apply --limit 500
 *
 * The nightly refresh classifies sixty securities and, until today, classified
 * the same sixty every night: it took the first sixty of holdings order, which
 * does not change between runs. The table held seventy rows and 58% of the
 * sector rotation chart read "Unclassified".
 *
 * The queue that replaced that slice makes progress - sixty new securities a
 * night - but a book of several thousand would take months to work through,
 * and the chart is wrong until it finishes. This does the whole backlog at
 * once, through the same SEC rate limiter the nightly path uses, and then the
 * nightly job only has to keep up with what changes.
 *
 * The universe is the securities in the two newest filings of every manager -
 * the same book the rotation chart aggregates. Classifying the full 47-quarter
 * history would be a hundred times the requests to answer a question nothing
 * on the site asks.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { core, collectClassifications, paged, secDirectory } from '../services/institutionalResearchLayerService.js';
import { secLimiterStats } from '../services/secRateLimiter.js';
import { securityCandidates } from '../services/securityCandidates.js';

const APPLY = process.argv.includes('--apply');
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const LIMIT = Number(argOf('--limit') || 20_000);
// Measured, not assumed: the 2026-09-10 backfill classified 4,161 securities
// in 1,350 seconds. The first version of this estimate divided by the SEC's
// published ten-per-second cap and promised eight minutes for a run that took
// twenty-two.
const OBSERVED_RPS = 3.1;

if (!getSupabaseAdminCredentials()) {
  console.error('[classify] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}

const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

async function main() {
  console.log(`[classify] mode: ${APPLY ? 'APPLY - this writes' : 'dry run - nothing is written'}`);

  const { client, holdings } = await core();
  const distinct = securityCandidates(holdings);
  console.log(`[classify] ${holdings.length.toLocaleString()} holdings, ${distinct.length.toLocaleString()} distinct securities  (${elapsed()}s)`);

  const { count: before } = await client.from('institutional_security_classifications')
    .select('id', { count: 'exact', head: true });
  console.log(`[classify] ${Number(before || 0).toLocaleString()} already classified`);

  if (!APPLY) {
    // The queue itself decides what is outstanding, and it is the same code
    // the nightly job runs. Reporting the count without writing is the whole
    // point of the dry run.
    const { classificationQueue } = await import('../services/classificationQueue.js');
    // Paged. A plain select stops at a thousand rows and reports success, and
    // a dry run that under-reports the backlog is worse than no dry run.
    const classified = await paged(
      () => client.from('institutional_security_classifications').select('security_key,source_as_of').order('security_key').order('source_as_of'),
      { label: 'existing classifications' },
    );
    const queued = classificationQueue({
      securities: distinct.map((row) => ({ key: row.key, row })),
      classified, limit: LIMIT,
    });
    // Two rates, because one of them was wrong by a factor of three. The
    // limiter's configured ceiling gives a floor on the time; the rate a full
    // run actually achieved gives the number to plan around. The gap is
    // network latency, which sits on top of the minimum spacing rather than
    // inside it - the limiter guarantees requests start no closer together
    // than the interval, not that they complete at that rate.
    const rps = Number(secLimiterStats()?.max_requests_per_second) || 5;
    const floor = queued.length / rps / 60;
    const observed = queued.length / OBSERVED_RPS / 60;
    console.log(`[classify] ${queued.length.toLocaleString()} would be classified: at least ${floor.toFixed(0)} minute(s) at the limiter's ${rps}/second ceiling, and nearer ${observed.toFixed(0)} at the ${OBSERVED_RPS}/second a full run has actually sustained`);
    console.log('[classify] dry run only. Re-run with --apply to write.');
    return;
  }

  const written = await collectClassifications(client, holdings, await secDirectory(), LIMIT);
  const { count: after } = await client.from('institutional_security_classifications')
    .select('id', { count: 'exact', head: true });
  console.log(`[classify] ${written.toLocaleString()} classified this run; table went from ${Number(before || 0).toLocaleString()} to ${Number(after || 0).toLocaleString()} in ${elapsed()}s`);
  if (written === 0 && Number(before || 0) === Number(after || 0)) {
    console.log('[classify] nothing was outstanding, or every candidate is missing from company_tickers.json');
  }
}


main().catch((error) => {
  console.error(`[classify] ${error.message}`);
  process.exit(1);
});
