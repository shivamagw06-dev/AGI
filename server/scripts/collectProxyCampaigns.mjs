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
import { isProxyContestForm, parseFilingHeader, campaignsFrom, campaignDirection } from '../services/proxyCampaign.js';

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

/**
 * The header for one filing, wherever EDGAR keeps it.
 *
 * The archive directory is created under the CIK that filed of record, which
 * for a solicitation is often the target rather than the activist - 90 of 258
 * headers returned 404 under the manager's own CIK. Full-text search names
 * every party on a filing, so a 404 is answered by asking who else is on it
 * and looking there.
 */
async function filingHeader(accession, managerCik) {
  const bare = accession.replace(/-/g, '');
  const at = (cik) => `https://www.sec.gov/Archives/edgar/data/${digits(cik).replace(/^0+/, '')}/${bare}/${accession}-index-headers.html`;
  try {
    return { text: await secGet(at(managerCik), 'text/html'), url: at(managerCik) };
  } catch (first) {
    if (!/HTTP 404/.test(first.message)) throw first;
  }
  const search = await secGet(
    `https://efts.sec.gov/LATEST/search-index?q=%22%22&ciks=${digits(managerCik).padStart(10, '0')}`
    + `&forms=&dateRange=&hits=1&accession_number=${accession}`,
    'application/json',
  ).catch(() => null);
  const parties = search?.hits?.hits?.[0]?._source?.ciks || [];
  for (const cik of parties) {
    if (digits(cik) === digits(managerCik)) continue;
    try {
      return { text: await secGet(at(cik), 'text/html'), url: at(cik) };
    } catch (error) {
      if (!/HTTP 404/.test(error.message)) throw error;
    }
  }
  throw new Error('no archive directory found under any party CIK');
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
  // Filings that name the manager as the target rather than the filer. Not a
  // campaign it ran, and worth seeing separately rather than dropped silently.
  const against = [];
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
      try {
        const found = await filingHeader(filing.accession_number, manager.cik);
        const header = parseFilingHeader(found.text);
        // EDGAR lists every filing that names a CIK, as filer or as subject,
        // and for an operating company that is mostly the latter. Recording
        // those would have Berkshire campaigning against its own board.
        const direction = campaignDirection(header, manager.cik);
        if (direction !== 'by_manager') {
          against.push(`${manager.display_name} <- ${header.filedBy?.name || 'unknown filer'} (${filing.form_type}, ${filing.filed_at})`);
          continue;
        }
        rows.push({
          manager_id: manager.id,
          accession_number: filing.accession_number,
          form_type: filing.form_type,
          filed_at: header.filedAt || filing.filed_at,
          subject_cik: header.subject.cik,
          subject_name: header.subject.name,
          source_url: found.url.replace(/[^/]+$/, ''),
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

  if (against.length) {
    console.log(`\n[proxy] ${against.length} filing(s) name a manager as the target, not the filer:\n`);
    for (const line of against.slice(0, 15)) console.log(`  ${line}`);
    if (against.length > 15) console.log(`  ... and ${against.length - 15} more`);
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
