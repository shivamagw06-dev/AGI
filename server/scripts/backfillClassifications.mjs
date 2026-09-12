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
import { core, collectClassifications, paged, secDirectory, resolveIssuer, registrantMatches } from '../services/institutionalResearchLayerService.js';
import { secLimiterStats } from '../services/secRateLimiter.js';
import { securityCandidates, partitionByIdentifiability } from '../services/securityCandidates.js';
import { namesByTicker } from '../services/issuerTickerRegistry.js';

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
  const all = securityCandidates(holdings);
  const { identifiable: distinct, unidentifiable } = partitionByIdentifiability(all);
  const blind = unidentifiable.reduce((sum, row) => sum + row.value_usd, 0);
  console.log(`[classify] ${holdings.length.toLocaleString()} holdings, ${all.length.toLocaleString()} securities, ${distinct.length.toLocaleString()} with a ticker  (${elapsed()}s)`);
  console.log(`[classify] ${unidentifiable.length.toLocaleString()} filed without a ticker ($${(blind / 1e9).toFixed(1)}bn) - no lookup here is keyed on anything else`);

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
      () => client.from('institutional_security_classifications').select('security_key,sector,source_as_of').order('security_key').order('source_as_of'),
      { label: 'existing classifications' },
    );
    const queued = classificationQueue({
      securities: distinct.map((row) => ({ key: row.key, row })),
      classified, limit: LIMIT,
    }).map((entry) => entry.row);

    // Resolved for real, not counted. The first version of this estimate
    // divided the queue length by a request rate, which was wrong twice over:
    // a fund resolves from a file with no SEC request at all, and a security
    // nothing can identify costs nothing either. Only companies cost time.
    const directory = await secDirectory();
    const registry = namesByTicker(await paged(
      () => client.from('sec_issuer_tickers').select('ticker,cik,issuer_name,first_seen,last_seen').order('ticker').order('cik'),
      { label: 'issuer registry' },
    ).catch(() => []));

    // The tickerless population, resolved the same two ways the apply will.
    const { sectorByIssuer, sectorFromIssuer, checkDigitValid } = await import('../services/cusipIssuer.js');
    const { nameIndex, matchByName } = await import('../services/issuerNameMatch.js');
    const byIssuer = sectorByIssuer(await paged(
      () => client.from('institutional_security_classifications').select('security_key,cusip,sector').order('security_key'),
      { label: 'classifications for issuer inference' },
    ));
    const byName = nameIndex(directory);
    const blindTally = { issuer: 0, name: 0, registrant: 0, refused: 0, derivative: 0 };
    const stillRefused = [];
    const blind = [...unidentifiable, ...queued.filter((s) => !resolveIssuer(s, directory, registry))];
    for (const security of blind) {
      if (!checkDigitValid(security.key)) blindTally.derivative += 1;
      if (sectorFromIssuer(security.key, byIssuer)) blindTally.issuer += 1;
      else if (security.issuer_name && matchByName(security.issuer_name, byName)) { blindTally.name += 1; }
      else stillRefused.push(security);
    }

    // The registrant tier, modelled the same way the apply runs it. Without
    // this the dry run reported three and a half thousand securities as
    // refused that the apply would in fact resolve, and an estimate of fifty
    // requests for a job that makes thousands - which is the one thing a dry
    // run exists not to do.
    const byRegistrant = await registrantMatches(stillRefused.map((s) => s.issuer_name).filter(Boolean))
      .catch((error) => { console.log(`[classify] registrant list unavailable: ${error.message}`); return new Map(); });
    for (const security of stillRefused) {
      if (byRegistrant.get(security.issuer_name)) blindTally.registrant += 1;
      else blindTally.refused += 1;
    }
    console.log(`[classify] ${blind.length.toLocaleString()} without a usable symbol (${unidentifiable.length.toLocaleString()} filed with no ticker, ${(blind.length - unidentifiable.length).toLocaleString()} whose ticker named nothing):`);
    console.log(`[classify]   ${String(blindTally.issuer).padStart(6)} resolved by CUSIP issuer, no SEC request`);
    console.log(`[classify]   ${String(blindTally.name).padStart(6)} matched by issuer name in the ticker files, one request each`);
    console.log(`[classify]   ${String(blindTally.registrant).padStart(6)} matched against the SEC registrant list, one request each`);
    console.log(`[classify]   ${String(blindTally.refused).padStart(6)} refused by all three`);
    console.log(`[classify]   ${String(blindTally.derivative).padStart(6)} carry an invalid check digit - filers' own option identifiers, not real CUSIPs`);

    const tally = { fund: 0, company: 0, registry: 0, unresolved: 0 };
    for (const security of queued) {
      const found = resolveIssuer(security, directory, registry);
      if (!found) tally.unresolved += 1;
      else if (found.kind === 'fund') tally.fund += 1;
      else if (found.source === 'SEC issuer registry') tally.registry += 1;
      else tally.company += 1;
    }
    const requests = tally.company + tally.registry + blindTally.name + blindTally.registrant;
    console.log(`[classify] ${queued.length.toLocaleString()} queued:`);
    console.log(`[classify]   ${String(tally.fund).padStart(6)} funds, resolved from the ticker file with no SEC request`);
    console.log(`[classify]   ${String(tally.company).padStart(6)} companies, one submissions request each`);
    console.log(`[classify]   ${String(tally.registry).padStart(6)} recovered through the historical issuer registry, one request each`);
    console.log(`[classify]   ${String(tally.unresolved).padStart(6)} unresolved by any list, no request and no row written`);
    console.log(`[classify] ${requests.toLocaleString()} request(s): at least ${(requests / (Number(secLimiterStats()?.max_requests_per_second) || 5) / 60).toFixed(0)} minute(s) at the limiter's ceiling, nearer ${(requests / OBSERVED_RPS / 60).toFixed(0)} at the rate a full run has sustained`);
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
