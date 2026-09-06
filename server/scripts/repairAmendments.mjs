#!/usr/bin/env node
/**
 * Repair 13F amendments that were ingested under the broken classification.
 *
 * Fixing ingestion forward does nothing for what is already stored. Every
 * 13F-HR/A ingested before the fix took the merge branch, because the parser
 * searched for a tag SEC does not emit against a document that was never
 * downloaded. A restatement that removed a position left it in the portfolio,
 * and those phantom positions are in institutional_holdings now, feeding
 * consensus, sector weights and every other surface that reads them.
 *
 * The amendment's own holdings cannot be recovered from the stored rows -
 * they are the merged result - so each affected quarter is re-fetched from
 * EDGAR and re-ingested in acceptance order through the same ingestFiling that
 * collection uses. Reusing it, rather than writing a parallel repair path, is
 * deliberate: a second implementation would drift from the first, and then the
 * repair itself becomes something to distrust.
 *
 *   node server/scripts/repairAmendments.mjs                 # dry run (default)
 *   node server/scripts/repairAmendments.mjs --apply         # write changes
 *   node server/scripts/repairAmendments.mjs --manager slug  # one manager
 *
 * Dry run is the default because this rewrites holdings. It reports exactly
 * what would change, including which positions would be removed, by fetching
 * and parsing without writing.
 */

import crypto from 'node:crypto';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import {
  amendmentFilings, filingsForQuarter, holdingsForFiling,
  previewFilingRepair, reingestFiling, rebuildInstitutionalSignals,
  quarantineAmendment, getRepairStatus,
} from '../services/institutionalHoldingsService.js';
import { secLimiterStats } from '../services/secRateLimiter.js';

const args = process.argv.slice(2);
const flag = (name, fallback = null) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : fallback;
};
const APPLY = args.includes('--apply');
const MANAGER = flag('manager');
const LIMIT = Number(flag('limit', '0')) || 0;

const missing = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY'].filter((k) => !process.env[k]);
if (missing.length) {
  console.error(`[repair] refusing to start: ${missing.join(' and ')} not set`);
  process.exit(78);
}
// This process is the deliberate caller; nothing else should crawl.
process.env.INSTITUTIONAL_AUTO_REFRESH = 'false';

const db = createSupabaseAdmin();
const runId = crypto.randomUUID();
const started = Date.now();

console.log(`[repair] run ${runId}  mode=${APPLY ? 'APPLY' : 'DRY RUN'}${MANAGER ? `  manager=${MANAGER}` : ''}`);
if (!APPLY) console.log('[repair] nothing will be written. Re-run with --apply to make these changes.');

const record = async (row) => {
  const { error } = await db.from('institutional_amendment_repairs').insert({
    repair_run_id: runId, applied: APPLY, ...row,
  });
  if (error) console.warn(`[repair] could not record ${row.accession_number}: ${error.message}`);
};

/** Preserve the rows a repair is about to overwrite. */
const archive = async (filing, rows) => {
  if (!rows.length) return;
  const { error } = await db.from('institutional_holdings_archive').insert(
    rows.map((holding) => ({
      repair_run_id: runId,
      filing_id: filing.id,
      accession_number: filing.accession_number,
      manager_id: filing.manager_id,
      report_date: filing.report_date,
      holding,
    })),
  );
  if (error) throw new Error(`archive failed for ${filing.accession_number}: ${error.message}`);
};

let amendments = await amendmentFilings();
if (MANAGER) amendments = amendments.filter((f) => f.institutional_managers?.slug === MANAGER);
if (LIMIT) amendments = amendments.slice(0, LIMIT);

console.log(`[repair] ${amendments.length} amendment filing(s) on record\n`);

const totals = {
  examined: 0, reclassified: 0, repaired: 0, wouldRepair: 0,
  unchanged: 0, needsReview: 0, failed: 0, removed: 0, retained: 0,
};

// Grouped by quarter: an amendment is only meaningful against the report it
// amends, and a quarter with two amendments must be replayed in order, once.
const quarters = new Map();
for (const filing of amendments) {
  const key = `${filing.manager_id}::${filing.report_date}`;
  if (!quarters.has(key)) quarters.set(key, filing);
}

for (const [, amendment] of quarters) {
  const slug = amendment.institutional_managers?.slug || amendment.manager_id;
  totals.examined += 1;

  try {
    const preview = await previewFilingRepair(amendment.id);
    const resolved = preview.classification.amendmentType;
    const previous = amendment.amendment_type || null;
    const reclassified = previous !== resolved;
    if (reclassified) totals.reclassified += 1;

    const before = await holdingsForFiling(amendment.id);
    const removed = preview.removed;
    const retained = preview.resultingRows.length;

    if (resolved === 'unknown') {
      totals.needsReview += 1;
      console.log(`  ${slug} ${amendment.report_date}  ${amendment.accession_number}  NEEDS REVIEW  (${preview.classification.reviewReason})`);

      // Recording that it needs review does not stop it counting. It was
      // ingested under the merge behaviour, so its rows are the merged result,
      // and while it stays active consensus and sector weights keep reading
      // them as though the amendment had been understood. The filing is
      // preserved; only is_active changes.
      if (APPLY) {
        try {
          const quarantine = await quarantineAmendment(amendment.id, preview.classification.reviewReason);
          console.log(`      excluded from derived signals${quarantine.reactivated ? '; prior version reactivated' : ''}`);
          if (quarantine.orphaned_quarter) {
            console.warn(`      WARNING: no other filing for this quarter, so ${amendment.report_date} now has no active report`);
          }
        } catch (quarantineError) {
          console.error(`      could not exclude it: ${quarantineError.message}`);
        }
      } else {
        console.log('      would be excluded from derived signals');
      }

      await record({
        filing_id: amendment.id, accession_number: amendment.accession_number,
        manager_slug: slug, report_date: amendment.report_date,
        previous_amendment_type: previous, resolved_amendment_type: resolved,
        reclassified, positions_before: before.length, positions_after: before.length,
        outcome: 'needs_review', needs_review: true,
      });
      continue;
    }

    // Nothing to do when the stored classification already matches and a
    // restatement would remove nothing.
    if (!reclassified && !removed.length) {
      totals.unchanged += 1;
      await record({
        filing_id: amendment.id, accession_number: amendment.accession_number,
        manager_slug: slug, report_date: amendment.report_date,
        previous_amendment_type: previous, resolved_amendment_type: resolved,
        reclassified: false, positions_before: before.length, positions_after: before.length,
        positions_retained: before.length, outcome: 'unchanged',
      });
      continue;
    }

    totals.removed += removed.length;
    totals.retained += retained;

    console.log(`  ${slug} ${amendment.report_date}  ${amendment.accession_number}`);
    console.log(`      ${previous || 'none'} -> ${resolved}${reclassified ? '  RECLASSIFIED' : ''}`);
    // The three numbers must agree. They did not: removals were computed
    // against a prior version the lookup never found, so the report said
    // "0 removed" while the row count visibly dropped by 257. Printing
    // contradictory numbers is worse than printing none - it invites someone
    // to trust the smaller one.
    const added = retained - (before.length - removed.length);
    const reconciles = before.length - removed.length + Math.max(0, added) === retained;
    console.log(`      positions ${before.length} -> ${retained}, ${removed.length} removed`
      + (added > 0 ? `, ${added} added` : ''));
    if (!reconciles) {
      console.warn(`      WARNING: counts do not reconcile (${before.length} - ${removed.length} + ${added} != ${retained}); treat this filing's figures as unverified`);
    }
    for (const row of removed.slice(0, 5)) {
      console.log(`        - ${row.cusip || '?'}  ${(row.issuer_name || '').slice(0, 40)}`);
    }
    if (removed.length > 5) console.log(`        ... and ${removed.length - 5} more`);

    if (!APPLY) {
      totals.wouldRepair += 1;
      await record({
        filing_id: amendment.id, accession_number: amendment.accession_number,
        manager_slug: slug, report_date: amendment.report_date,
        previous_amendment_type: previous, resolved_amendment_type: resolved,
        reclassified, positions_before: before.length, positions_after: retained,
        positions_removed: removed.length, positions_retained: retained,
        removed_positions: removed.slice(0, 200).map((r) => ({ cusip: r.cusip, issuer: r.issuer_name })),
        outcome: 'would_repair',
      });
      continue;
    }

    // Archive before overwriting: every filing for this quarter, since
    // re-ingesting the chain rewrites all of them.
    const chain = await filingsForQuarter(amendment.manager_id, amendment.report_date);
    for (const filing of chain) {
      await archive({ ...filing, manager_id: amendment.manager_id }, await holdingsForFiling(filing.id));
    }

    // Replay the quarter in acceptance order. The original re-establishes the
    // baseline, then each amendment applies under its real classification.
    for (const filing of chain) await reingestFiling(filing.id);

    const after = await holdingsForFiling(amendment.id);
    totals.repaired += 1;
    await record({
      filing_id: amendment.id, accession_number: amendment.accession_number,
      manager_slug: slug, report_date: amendment.report_date,
      previous_amendment_type: previous, resolved_amendment_type: resolved,
      reclassified, positions_before: before.length, positions_after: after.length,
      positions_removed: removed.length, positions_retained: after.length,
      removed_positions: removed.slice(0, 200).map((r) => ({ cusip: r.cusip, issuer: r.issuer_name })),
      outcome: 'repaired',
    });
  } catch (error) {
    totals.failed += 1;
    console.error(`  ${slug} ${amendment.report_date}  ${amendment.accession_number}  FAILED: ${error.message}`);
    await record({
      filing_id: amendment.id, accession_number: amendment.accession_number,
      manager_slug: slug, report_date: amendment.report_date,
      previous_amendment_type: amendment.amendment_type || null,
      outcome: 'failed', error: String(error.message).slice(0, 500),
    });
  }
}

// Signals are materialised from holdings, so they are stale the moment holdings
// change. Rebuilt once at the end rather than per filing.
if (APPLY && totals.repaired) {
  console.log('\n[repair] rebuilding signals from repaired holdings');
  try {
    await rebuildInstitutionalSignals();
    console.log('[repair] signals rebuilt');
  } catch (error) {
    console.error(`[repair] signal rebuild failed: ${error.message}`);
  }
}

const limiter = secLimiterStats();
console.log(`
[repair] ---- reconciliation ----
  run:                  ${runId}
  mode:                 ${APPLY ? 'APPLIED' : 'DRY RUN (nothing written)'}
  quarters examined:    ${totals.examined}
  reclassified:         ${totals.reclassified}
  ${APPLY ? 'repaired' : 'would repair'}:${APPLY ? '             ' : '         '}${APPLY ? totals.repaired : totals.wouldRepair}
  unchanged:            ${totals.unchanged}
  needs review:         ${totals.needsReview}
  failed:               ${totals.failed}
  positions removed:    ${totals.removed}
  positions retained:   ${totals.retained}
  sec requests:         ${limiter.requests} (throttled ${limiter.throttled})
  elapsed:              ${((Date.now() - started) / 1000).toFixed(1)}s
`);

// The gate every aggregate surface reads. Printed last so the run ends by
// saying whether the numbers can be published, not merely what it touched.
try {
  const gate = await getRepairStatus();
  console.log(`[repair] data integrity gate: ${gate.status}${gate.clean ? '' : ` — ${gate.message}`}`);
  if (!gate.clean) {
    console.log('[repair] consensus, sector rotation and change signals will show "historical repair in progress" until this clears.');
  }
} catch (error) {
  console.warn(`[repair] could not read the integrity gate: ${error.message}`);
}

if (!APPLY && (totals.wouldRepair || totals.needsReview)) {
  console.log('[repair] re-run with --apply to make these changes.');
}
process.exit(totals.failed ? 1 : 0);
