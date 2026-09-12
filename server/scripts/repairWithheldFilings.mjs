#!/usr/bin/env node
/**
 * Clear filings whose information table was withheld but was stored as a
 * holding anyway.
 *
 * Norges Bank files under a standing request for confidential treatment: a
 * schema-valid placeholder on the due date - one entry, issuer "NA", CUSIP
 * 000000000, zero value, zero shares - and the real book as a 13F-HR/A a year
 * later. The placeholder was ingested as a position, so two quarters read as
 * one-name portfolios against a manager median of 2,108, and the quarter after
 * each of them read as 100% turnover against a book of one.
 *
 * Ingestion no longer stores these. This clears the ones already stored, by
 * re-fetching each filing and putting it back through the same ingestFiling
 * that collection uses - not through a second implementation that could drift
 * from the first.
 *
 *   node server/scripts/repairWithheldFilings.mjs            # dry run (default)
 *   node server/scripts/repairWithheldFilings.mjs --apply    # write changes
 *   node server/scripts/repairWithheldFilings.mjs --manager norges-bank
 *
 * Dry run is the default because this deletes holdings. What it deletes is
 * only ever a placeholder row - the re-ingest stores nothing for a withheld
 * filing, and a filing that turns out to carry real positions is re-ingested
 * with them intact - but the report is worth reading before the write.
 *
 * The holdings themselves are not recoverable here and this does not pretend
 * otherwise. They are not public yet. Norges Bank's Q3 2025 amendment is due
 * around 2026-11-13 and Q1 2026's around 2027-05-11, on the twelve-month
 * cadence every prior quarter has followed; ordinary collection will pick them
 * up when they are filed.
 */

import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { reingestFiling, rebuildInstitutionalSignals } from '../services/institutionalHoldingsService.js';
import { isPlaceholderRow } from '../services/confidentialTreatment.js';

const args = process.argv.slice(2);
const flag = (name, fallback = null) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : fallback;
};
const APPLY = args.includes('--apply');
const MANAGER = flag('manager');

const missing = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY'].filter((k) => !process.env[k]);
if (missing.length) {
  console.error(`[withheld] refusing to start: ${missing.join(' and ')} not set`);
  process.exit(78);
}
// This process is the deliberate caller; nothing else should crawl.
process.env.INSTITUTIONAL_AUTO_REFRESH = 'false';

const db = createSupabaseAdmin();

console.log(`[withheld] mode=${APPLY ? 'APPLY' : 'DRY RUN'}${MANAGER ? `  manager=${MANAGER}` : ''}`);
if (!APPLY) console.log('[withheld] nothing will be written. Re-run with --apply to make these changes.');

/**
 * Find the filings that stored a placeholder instead of a book.
 *
 * Candidates come from institutional_filings, which holds a few thousand rows,
 * rather than from institutional_holdings, which holds millions.
 *
 * The first version swept the holdings table directly for `cusip like '0000%'`
 * and for nameless issuers. Neither filter can use an index - a prefix LIKE is
 * not indexable under the default collation and issuer_name has no index at
 * all - so each was a sequential scan of every holding we store, and .range()
 * paging turns that into one such scan per page. It timed out before returning
 * a single row.
 *
 * A withheld filing stores exactly one row, so filings with a handful of
 * stored holdings are the entire candidate set. That is the "how small is the
 * book" test, which was rejected as a *decision* rule and rightly so - but it
 * is not being used as one. isPlaceholderRow still decides, so Alphabet's
 * genuine two-position 2016 filings and Durable Capital's three-position first
 * filing are fetched here and correctly rejected below.
 */
const PLACEHOLDER_MAX_ROWS = 5;

async function placeholderFilings() {
  const seen = new Map();
  const PAGE = 1000;

  const candidates = [];
  for (let from = 0; ; from += PAGE) {
    const { data, error } = await db
      .from('institutional_filings')
      .select('id')
      .lte('holdings_count', PLACEHOLDER_MAX_ROWS)
      .order('id')
      .range(from, from + PAGE - 1);
    if (error) throw new Error(error.message);
    candidates.push(...(data || []).map((row) => row.id));
    // Paged deliberately, and ordered: an unbounded PostgREST select stops at
    // 1,000 rows and says nothing about the ones it did not return, and an
    // unordered one lets rows move between pages.
    if (!data || data.length < PAGE) break;
  }

  for (const filingId of candidates) {
    // Reached through filing_id, which is the indexed path into this table.
    const { data, error } = await db
      .from('institutional_holdings')
      .select('id,filing_id,cusip,issuer_name,value_usd,shares')
      .eq('filing_id', filingId)
      .limit(PLACEHOLDER_MAX_ROWS + 1);
    if (error) throw new Error(error.message);
    const rows = data || [];
    if (!rows.length) continue;
    // Every stored row has to be a placeholder. A filing carrying one
    // placeholder beside real positions is a different problem, and this
    // clears the whole filing - which would throw the real ones away.
    if (!rows.every(isPlaceholderRow)) continue;
    seen.set(filingId, new Set(rows.map((row) => row.id)));
  }
  return seen;
}

const byFiling = await placeholderFilings();
if (!byFiling.size) {
  console.log('[withheld] no stored placeholder holdings found. Nothing to repair.');
  process.exit(0);
}

const { data: filings, error } = await db
  .from('institutional_filings')
  .select('id,accession_number,report_date,form_type,holdings_count,is_active,manager_id,institutional_managers(slug,display_name)')
  .in('id', [...byFiling.keys()])
  .order('report_date', { ascending: true });
if (error) throw new Error(error.message);

const targets = (filings || []).filter(
  (f) => !MANAGER || f.institutional_managers?.slug === MANAGER,
);

console.log(`[withheld] ${targets.length} filing(s) hold a placeholder row\n`);
const totals = { repaired: 0, wouldRepair: 0, failed: 0 };

for (const filing of targets) {
  const slug = filing.institutional_managers?.slug || filing.manager_id;
  const label = `  ${slug}  ${filing.report_date}  ${filing.form_type}  ${filing.accession_number}`;
  const placeholders = byFiling.get(filing.id)?.size || 0;

  if (!APPLY) {
    totals.wouldRepair += 1;
    console.log(`${label}  stored=${filing.holdings_count} placeholder=${placeholders} active=${filing.is_active}`
      + '  -> would clear holdings and deactivate');
    continue;
  }

  try {
    const result = await reingestFiling(filing.id);
    totals.repaired += 1;
    const declared = result.declared_holdings_count;
    console.log(`${label}  ${result.status}`
      + `  removed=${result.removed ?? 0}  holdings=${result.holdings}`
      + (declared ? `  declared=${declared.toLocaleString('en-US')}` : ''));
  } catch (err) {
    totals.failed += 1;
    console.error(`${label}  FAILED: ${err.message}`);
  }
}

// Signals are materialised from holdings, so they are stale the moment
// holdings change. Only after a write, and only if one succeeded.
if (APPLY && totals.repaired) {
  console.log('\n[withheld] rebuilding signals');
  try {
    await rebuildInstitutionalSignals();
  } catch (err) {
    console.error(`[withheld] signal rebuild failed: ${err.message}`);
    totals.failed += 1;
  }
}

console.log(`\n[withheld] ${APPLY ? `repaired=${totals.repaired}` : `would repair=${totals.wouldRepair}`}  failed=${totals.failed}`);
process.exit(totals.failed ? 1 : 0);
