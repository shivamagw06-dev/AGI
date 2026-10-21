/**
 * Build the historical ticker registry from SEC bulk Form 345 submissions.
 *
 *   node server/scripts/importSecIssuerTickers.mjs --from 2016q1 --to 2026q1
 *   node server/scripts/importSecIssuerTickers.mjs --from 2016q1 --to 2026q1 --apply
 *
 * company_tickers.json lists what is registered now, and it is sound - every
 * control name is in it. It simply cannot answer a question about the past,
 * and a decade of 13F holdings is mostly questions about the past. Activision,
 * Pioneer, Seagen, Splunk, WestRock, Marathon Oil, Discover and Electronic
 * Arts have all left it, and 191 venue-coded holdings worth $1.48tn are
 * refused because nothing can confirm a ticker that no longer exists.
 *
 * Every quarterly SUBMISSION.tsv names the issuer, its CIK and its symbol as
 * filed. The union across quarters is what each ticker meant while it meant
 * it.
 *
 * Unlike the insider import this applies no held-ticker filter, deliberately.
 * That filter is why the registry could not be built from what we already
 * store: holdings say MASI* and HO1, so every Form 4 for Masimo and Hologic
 * was skipped - the corroboration was missing for exactly the same reason the
 * recovery is needed.
 *
 * Only SUBMISSION.tsv is read. The transaction tables are the bulk of the
 * archive and none of it is needed here, so a decade costs a few thousand
 * rows.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { extract } from '../services/zipReader.js';
import { parseTsv, bulkDate } from '../services/insiderBulk.js';
import { issuerTickerPairs, mergePairs } from '../services/issuerTickerRegistry.js';

const APPLY = process.argv.includes('--apply');
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const CHUNK = 500;

const BASE = 'https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets';
const UA = (process.env.SEC_USER_AGENT || 'AGI Institutional Research research@agarwalglobalinvestments.com').trim();

if (!getSupabaseAdminCredentials()) {
  console.error('[registry] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

function quarterRange(from, to) {
  const parse = (text) => {
    const match = /^(\d{4})q([1-4])$/i.exec(String(text || '').trim());
    if (!match) throw new Error(`Not a quarter: ${text}. Use the form 2025q4.`);
    return { year: Number(match[1]), quarter: Number(match[2]) };
  };
  const start = parse(from);
  const end = parse(to);
  const out = [];
  let { year, quarter } = start;
  while (year < end.year || (year === end.year && quarter <= end.quarter)) {
    out.push(`${year}q${quarter}`);
    quarter += 1;
    if (quarter > 4) { quarter = 1; year += 1; }
    if (out.length > 200) throw new Error('More than 200 quarters requested; check the order of --from and --to.');
  }
  return out;
}

async function quarterPairs(quarter) {
  const response = await fetch(`${BASE}/${quarter}_form345.zip`, { headers: { 'User-Agent': UA } });
  if (response.status === 404) {
    // Expected for the current quarter, and for quarters before the SEC began
    // publishing these. Not an error and not a reason to stop the range.
    console.log(`[registry] ${quarter}: not published`);
    return [];
  }
  if (!response.ok) throw new Error(`${quarter}: HTTP ${response.status}`);

  const archive = Buffer.from(await response.arrayBuffer());
  const rows = parseTsv(extract(archive, 'SUBMISSION.tsv').toString('utf8'));
  const pairs = issuerTickerPairs(rows, { bulkDate });
  console.log(`[registry] ${quarter}: ${rows.length.toLocaleString()} submissions, ${pairs.length.toLocaleString()} issuer/ticker pair(s)  (${elapsed()}s)`);
  return pairs;
}

async function main() {
  const explicit = argOf('--quarters');
  const quarters = explicit
    ? explicit.split(',').map((q) => q.trim()).filter(Boolean)
    : quarterRange(argOf('--from') || '2016q1', argOf('--to') || '2026q1');

  console.log(`[registry] ${quarters.length} quarter(s): ${quarters[0]} .. ${quarters[quarters.length - 1]}`);
  console.log(`[registry] mode: ${APPLY ? 'APPLY - this writes' : 'dry run - nothing is written'}`);

  let pairs = [];
  const failed = [];
  for (const quarter of quarters) {
    try {
      pairs = mergePairs(pairs, await quarterPairs(quarter));
    } catch (error) {
      console.error(`[registry] ${quarter}: ${error.message}`);
      failed.push(quarter);
    }
  }

  const tickers = new Set(pairs.map((row) => row.ticker));
  const reused = [...tickers].filter((ticker) => pairs.filter((row) => row.ticker === ticker).length > 1);
  console.log('');
  console.log(`[registry] ${pairs.length.toLocaleString()} distinct issuer/ticker pair(s), ${tickers.size.toLocaleString()} ticker(s)`);
  // Reported because it is the fact the table exists for: a ticker with two
  // issuers is one a live registry would answer wrongly for a past holding.
  console.log(`[registry] ${reused.length.toLocaleString()} ticker(s) used by more than one issuer`);
  if (failed.length) console.log(`[registry] ${failed.length} quarter(s) failed: ${failed.join(', ')}`);

  if (!APPLY) {
    console.log('[registry] dry run only. Re-run with --apply to write.');
    return;
  }

  const rows = pairs.map((row) => ({ ...row, refreshed_at: new Date().toISOString() }));
  let written = 0;
  for (let index = 0; index < rows.length; index += CHUNK) {
    const { error } = await client.from('sec_issuer_tickers')
      .upsert(rows.slice(index, index + CHUNK), { onConflict: 'ticker,cik' });
    if (error) throw new Error(`writing the registry at ${index}: ${error.message}`);
    written += Math.min(CHUNK, rows.length - index);
  }
  console.log(`[registry] ${written.toLocaleString()} row(s) written in ${elapsed()}s`);
}

main().catch((error) => {
  console.error(`[registry] ${error.message}`);
  process.exit(1);
});
