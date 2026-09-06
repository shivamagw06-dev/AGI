#!/usr/bin/env node
/**
 * Find filings whose stored values look scaled the wrong way.
 *
 * Read-only. It changes nothing and is meant to be run before deciding whether
 * anything needs changing.
 *
 * Two of the three ingest paths keyed the dollars-vs-thousands rule to the
 * report date instead of the filing date, so any filing they wrote for a
 * quarter ending before 3 January 2023 but filed after it - Q4-2022, and any
 * amendment to an older quarter filed since - was multiplied by 1000. The SEC
 * collection path was correct, so the exposure is limited to filings that came
 * through the CMS import or the accession-import screen.
 *
 * The test is arithmetic rather than provenance: value divided by shares is an
 * implied per-share price, and a portfolio whose median implied price is under
 * a dollar is not priced in dollars. That catches mis-scaling however it got
 * there, including filings this audit does not know the history of.
 *
 *   node server/scripts/auditValueScale.mjs [--json]
 */

import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { valueScaleFor, detectScaleMismatch } from '../services/valueScale.js';

const asJson = process.argv.includes('--json');
const missing = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY'].filter((k) => !process.env[k]);
if (missing.length) {
  console.error(`[value-scale] refusing to start: ${missing.join(' and ')} not set`);
  process.exit(78);
}
process.env.INSTITUTIONAL_AUTO_REFRESH = 'false';

const db = createSupabaseAdmin();

const { data: filings, error } = await db
  .from('institutional_filings')
  .select('id,accession_number,form_type,report_date,filed_at,total_value_usd,holdings_count,institutional_managers(slug,display_name,value_scale_override)')
  .order('report_date', { ascending: false });
if (error) { console.error(`[value-scale] ${error.message}`); process.exit(1); }

const suspect = [];
for (const filing of filings || []) {
  const { data: rows } = await db
    .from('institutional_holdings')
    .select('shares,value_usd,put_call,cusip,issuer_name')
    .eq('filing_id', filing.id)
    .limit(1000);
  if (!rows?.length) continue;

  const expected = valueScaleFor({
    acceptedAt: filing.filed_at,
    reportDate: filing.report_date,
    override: filing.institutional_managers?.value_scale_override,
  });
  const mismatch = detectScaleMismatch(rows, expected.scale);
  if (!mismatch) continue;

  suspect.push({
    accession: filing.accession_number,
    manager: filing.institutional_managers?.slug || 'unknown',
    report_date: filing.report_date,
    filed_at: filing.filed_at,
    form_type: filing.form_type,
    expected_scale: expected.scale,
    expected_basis: expected.basis,
    suspected_scale: mismatch.suspected,
    median_implied_price: Number(mismatch.median.toFixed(4)),
    reason: mismatch.reason,
    stored_total_usd: filing.total_value_usd,
    positions: rows.length,
  });
}

if (asJson) {
  console.log(JSON.stringify({ examined: filings?.length || 0, suspect }, null, 2));
} else {
  console.log(`\n  Value-scale audit — ${filings?.length || 0} filing(s) examined\n`);
  if (!suspect.length) {
    console.log('  No filing shows an implied per-share price inconsistent with its applied scale.\n');
  } else {
    for (const row of suspect) {
      console.log(`  ${row.manager}  ${row.report_date}  ${row.accession}  (${row.form_type})`);
      console.log(`      filed ${String(row.filed_at).slice(0, 10)} — rule says scale ${row.expected_scale} (${row.expected_basis})`);
      console.log(`      median implied price $${row.median_implied_price} — ${row.reason}`);
      console.log(`      stored total: $${Number(row.stored_total_usd || 0).toLocaleString()}`);
    }
    console.log(`\n  ${suspect.length} filing(s) look mis-scaled. Re-ingesting them from SEC corrects the values.\n`);
  }
}
process.exit(suspect.length ? 1 : 0);
