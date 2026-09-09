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
import { core, collectClassifications, paged } from '../services/institutionalResearchLayerService.js';

const APPLY = process.argv.includes('--apply');
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const LIMIT = Number(argOf('--limit') || 20_000);

if (!getSupabaseAdminCredentials()) {
  console.error('[classify] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}

const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

async function main() {
  console.log(`[classify] mode: ${APPLY ? 'APPLY - this writes' : 'dry run - nothing is written'}`);

  const { client, holdings } = await core();
  const distinct = new Set();
  for (const row of holdings) {
    const ticker = String(row.ticker || row.mapped_ticker || '').trim().toUpperCase();
    if (!ticker) continue;
    distinct.add(String(row.security_key || row.cusip || ticker).trim().toUpperCase());
  }
  console.log(`[classify] ${holdings.length.toLocaleString()} holdings, ${distinct.size.toLocaleString()} distinct securities with a ticker  (${elapsed()}s)`);

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
      securities: [...distinct].map((key) => ({ key })),
      classified, limit: LIMIT,
    });
    console.log(`[classify] ${queued.length.toLocaleString()} would be classified, at roughly ${(queued.length / 10 / 60).toFixed(1)} minute(s) against the SEC's ten-per-second limit`);
    console.log('[classify] dry run only. Re-run with --apply to write.');
    return;
  }

  const written = await collectClassifications(client, holdings, await tickerMapOnce(), LIMIT);
  const { count: after } = await client.from('institutional_security_classifications')
    .select('id', { count: 'exact', head: true });
  console.log(`[classify] ${written.toLocaleString()} classified this run; table went from ${Number(before || 0).toLocaleString()} to ${Number(after || 0).toLocaleString()} in ${elapsed()}s`);
  if (written === 0 && Number(before || 0) === Number(after || 0)) {
    console.log('[classify] nothing was outstanding, or every candidate is missing from company_tickers.json');
  }
}

// The SEC ticker file, fetched once. collectClassifications takes it as an
// argument so that the nightly job and this script share one copy rather than
// each pulling it per security.
async function tickerMapOnce() {
  const response = await fetch('https://www.sec.gov/files/company_tickers.json', {
    headers: { 'User-Agent': process.env.SEC_USER_AGENT || 'AGI Institutional Research research@agarwalglobalinvestments.com' },
  });
  if (!response.ok) throw new Error(`company_tickers.json: HTTP ${response.status}`);
  const payload = await response.json();
  return new Map(Object.values(payload || {}).map((row) => [String(row.ticker || '').toUpperCase(), { cik: String(row.cik_str || '').padStart(10, '0'), title: row.title }]));
}

main().catch((error) => {
  console.error(`[classify] ${error.message}`);
  process.exit(1);
});
