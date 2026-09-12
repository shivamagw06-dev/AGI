#!/usr/bin/env node
/**
 * Collect the proxy contests each manager has run.
 *
 *   node server/scripts/collectProxyCampaigns.mjs            # dry run
 *   node server/scripts/collectProxyCampaigns.mjs --apply
 *   node server/scripts/collectProxyCampaigns.mjs --manager pershing-square
 *
 * Forty-four of the fifty managers file nothing with the SEC but position
 * tables and stake declarations. This collects the exception: a manager
 * soliciting against a board has to file what it sends to shareholders, and
 * those filings are public, indexed by CIK, and the only manager-authored
 * writing in EDGAR.
 *
 * It reads none of the writing. Each filing's header names the target and the
 * filer, which is enough to record the campaign, and the document itself stays
 * where it is - it is the manager's own words and its own copyright. Every row
 * carries a link so the argument can be read at the source.
 *
 * Two requests per manager plus one per campaign filing, all through the
 * shared SEC limiter. Resumable: a filing already stored is not re-fetched.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { scheduleSecRequest } from '../services/secRateLimiter.js';
import { paged } from '../services/institutionalResearchLayerService.js';
import { isProxyContestForm, parseFilingHeader, campaignsFrom } from '../services/proxyCampaign.js';

const APPLY = process.argv.includes('--apply');
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const ONLY = argOf('--manager');
const UA = process.env.SEC_USER_AGENT || 'AGI Institutional Research research@agarwalglobalinvestments.com';

if (!getSupabaseAdminCredentials()) {
  console.error('[proxy] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();

const digits = (value) => String(value || '').replace(/\D/g, '');

async function secGet(url, accept) {
  const response = await scheduleSecRequest(() => fetch(url, {
    headers: { Accept: accept, 'User-Agent': UA }, signal: AbortSignal.timeout(30_000),
  }));
  if (!response.ok) throw new Error(`HTTP ${response.status} for ${url}`);
  return accept === 'application/json' ? response.json() : response.text();
}

/** Campaign filings in a manager's EDGAR history, newest first. */
function campaignFilings(payload) {
  const recent = payload?.filings?.recent || {};
  const forms = recent.form || [];
  return forms.map((form, index) => ({
    form_type: String(form || '').toUpperCase(),
    accession_number: recent.accessionNumber?.[index],
    filed_at: recent.filingDate?.[index] || null,
  })).filter((row) => row.accession_number && isProxyContestForm(row.form_type));
}

async function main() {
  console.log(`[proxy] mode=${APPLY ? 'APPLY' : 'DRY RUN'}`);
  const managers = await paged(
    () => client.from('institutional_managers').select('id, slug, display_name, cik')
      .eq('active', true).order('display_name'),
    { label: 'managers' },
  );
  const wanted = ONLY ? managers.filter((row) => row.slug === ONLY) : managers;

  // Already stored, so an interrupted run continues rather than re-fetching.
  const stored = new Set((await paged(
    () => client.from('institutional_proxy_filings').select('accession_number'),
    { label: 'stored proxy filings' },
  )).map((row) => row.accession_number));
  console.log(`[proxy] ${managers.length} manager(s), ${stored.size} filing(s) already stored\n`);

  const rows = [];
  const skipped = [];
  for (const manager of wanted) {
    let filings = [];
    try {
      filings = campaignFilings(await secGet(
        `https://data.sec.gov/submissions/CIK${digits(manager.cik).padStart(10, '0')}.json`,
        'application/json',
      ));
    } catch (error) {
      skipped.push(`${manager.display_name}: ${error.message}`);
      continue;
    }
    if (!filings.length) continue;

    const fresh = filings.filter((row) => !stored.has(row.accession_number));
    console.log(`[proxy] ${manager.display_name.padEnd(32)} ${filings.length} campaign filing(s), ${fresh.length} new`);

    for (const filing of fresh) {
      const bare = filing.accession_number.replace(/-/g, '');
      const url = `https://www.sec.gov/Archives/edgar/data/${digits(manager.cik)}/${bare}/${filing.accession_number}-index-headers.html`;
      try {
        const header = parseFilingHeader(await secGet(url, 'text/html'));
        // A solicitation names its target. Without one there is no campaign to
        // record, and guessing which company was meant would invent a fight.
        if (!header.subject?.cik) {
          skipped.push(`${filing.accession_number}: no SUBJECT COMPANY in header`);
          continue;
        }
        rows.push({
          manager_id: manager.id,
          accession_number: filing.accession_number,
          form_type: filing.form_type,
          filed_at: header.filedAt || filing.filed_at,
          subject_cik: header.subject.cik,
          subject_name: header.subject.name,
          source_url: `https://www.sec.gov/Archives/edgar/data/${digits(manager.cik)}/${bare}/`,
        });
      } catch (error) {
        skipped.push(`${filing.accession_number}: ${error.message}`);
      }
    }
  }

  console.log(`\n[proxy] ${rows.length} new filing(s) read`);
  const campaigns = campaignsFrom(rows);
  if (campaigns.length) {
    const name = new Map(managers.map((row) => [row.id, row.display_name]));
    console.log('\n[proxy] campaigns, most-contested first:\n');
    for (const campaign of campaigns.slice(0, 40)) {
      console.log(`  ${String(name.get(campaign.manager_id)).slice(0, 26).padEnd(28)}`
        + `${String(campaign.subject_name).slice(0, 34).padEnd(36)}`
        + `${String(campaign.filings).padStart(3)} filing(s)  `
        + `${campaign.first_filed} .. ${campaign.last_filed}  ${campaign.forms.join(' ')}`);
    }
    if (campaigns.length > 40) console.log(`  ... and ${campaigns.length - 40} more`);
  }

  if (skipped.length) {
    console.log(`\n[proxy] ${skipped.length} skipped:`);
    for (const line of skipped.slice(0, 20)) console.log(`  ${line}`);
    if (skipped.length > 20) console.log(`  ... and ${skipped.length - 20} more`);
  }

  if (!APPLY) {
    console.log('\n[proxy] dry run only. Re-run with --apply to write.');
    return;
  }
  for (let index = 0; index < rows.length; index += 200) {
    const { error } = await client.from('institutional_proxy_filings')
      .upsert(rows.slice(index, index + 200), { onConflict: 'accession_number' });
    if (error) throw new Error(`writing at ${index}: ${error.message}`);
  }
  console.log(`\n[proxy] ${rows.length} filing(s) written across ${campaigns.length} campaign(s)`);
}

main().catch((error) => {
  console.error(`[proxy] ${error.message}`);
  process.exit(1);
});
