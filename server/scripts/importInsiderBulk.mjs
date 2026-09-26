/**
 * Import insider filings from the SEC's bulk Form 345 datasets.
 *
 *   node server/scripts/importInsiderBulk.mjs --from 2024q1 --to 2026q1
 *   node server/scripts/importInsiderBulk.mjs --from 2024q1 --to 2026q1 --apply
 *   node server/scripts/importInsiderBulk.mjs --quarters 2025q4 --apply --all-tickers
 *
 * The nightly EDGAR crawl asks one company at a time and downloads one filing
 * at a time. Against 5,125 issuers it needs ten nights to make a single pass,
 * and until today it had never completed one. The SEC publishes the same data
 * quarterly as flat files: one 8 MB download carries 36,422 filings and 59,679
 * transactions across every issuer, already structured, with the trading
 * symbol on the submission - so no CIK lookup, and none of the 797 tickers the
 * crawl skips for want of one.
 *
 * This does not replace the crawl. The bulk files stop at the last completed
 * quarter, so this covers history and the nightly job covers the current one.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { extract } from '../services/zipReader.js';
import { parseTsv, assembleFilings } from '../services/insiderBulk.js';

const APPLY = process.argv.includes('--apply');
const ALL_TICKERS = process.argv.includes('--all-tickers');
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const CHUNK = 500;

const BASE = 'https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets';
const UA = (process.env.SEC_USER_AGENT || 'AGI Institutional Research research@agarwalglobalinvestments.com').trim();

if (!getSupabaseAdminCredentials()) {
  console.error('[bulk] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

/** Expand --from/--to into the quarters between them, inclusive. */
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
    // A reversed range would otherwise spin until it exhausted memory.
    if (out.length > 200) throw new Error('More than 200 quarters requested; check the order of --from and --to.');
  }
  return out;
}

/** The tickers actually held, so history is not imported for the whole market. */
async function heldTickers() {
  const held = new Set();
  for (let page = 0; ; page += 1) {
    const { data, error } = await client
      .from('institutional_holdings')
      .select('ticker')
      .not('ticker', 'is', null)
      .range(page * 1000, page * 1000 + 999);
    if (error) throw new Error(`reading held tickers: ${error.message}`);
    for (const row of data || []) if (row.ticker) held.add(String(row.ticker).toUpperCase());
    if (!data || data.length < 1000) break;
  }
  return held;
}

async function importQuarter(quarter, tickers) {
  const url = `${BASE}/${quarter}_form345.zip`;
  const response = await fetch(url, { headers: { 'User-Agent': UA } });
  if (response.status === 404) {
    // Expected for the current quarter: the SEC publishes these after the
    // quarter closes. Not an error, and not a reason to stop the range.
    console.log(`[bulk] ${quarter}: not published yet`);
    return { filings: 0, written: 0 };
  }
  if (!response.ok) throw new Error(`${quarter}: HTTP ${response.status}`);

  const archive = Buffer.from(await response.arrayBuffer());
  const table = (name) => parseTsv(extract(archive, name).toString('utf8'));

  const { filings, skippedTicker, skippedForm } = assembleFilings({
    submissions: table('SUBMISSION.tsv'),
    owners: table('REPORTINGOWNER.tsv'),
    nonDeriv: table('NONDERIV_TRANS.tsv'),
    deriv: table('DERIV_TRANS.tsv'),
    tickers,
  });

  const size = (archive.length / 1048576).toFixed(1);
  console.log(
    `[bulk] ${quarter}: ${size} MB, ${filings.length.toLocaleString()} Form 4 filing(s) kept`
    + `${tickers ? `, ${skippedTicker.toLocaleString()} not held` : ''}`
    + `, ${skippedForm.toLocaleString()} not Form 4  (${elapsed()}s)`,
  );

  if (!APPLY || !filings.length) return { filings: filings.length, written: 0 };

  let written = 0;
  for (let i = 0; i < filings.length; i += CHUNK) {
    const { error } = await client
      .from('institutional_external_filings')
      .upsert(filings.slice(i, i + CHUNK), { onConflict: 'accession_number' });
    // One quarter failing must not take the range down: the others are
    // independent, and a partial import is resumable because the upsert is
    // keyed on accession.
    if (error) {
      console.error(`[bulk] ${quarter} write at ${i}: ${error.message}`);
      return { filings: filings.length, written, failed: true };
    }
    written += Math.min(CHUNK, filings.length - i);
  }
  return { filings: filings.length, written };
}

async function main() {
  const explicit = argOf('--quarters');
  const quarters = explicit
    ? explicit.split(',').map((q) => q.trim()).filter(Boolean)
    : quarterRange(argOf('--from') || '2024q1', argOf('--to') || '2026q1');

  const tickers = ALL_TICKERS ? null : await heldTickers();
  console.log(`[bulk] ${quarters.length} quarter(s): ${quarters[0]} .. ${quarters[quarters.length - 1]}`);
  console.log(`[bulk] scope: ${tickers ? `${tickers.size.toLocaleString()} held tickers` : 'every issuer'}`);
  console.log(`[bulk] mode: ${APPLY ? 'APPLY - this writes' : 'dry run - nothing is written'}`);

  let filings = 0;
  let written = 0;
  const failed = [];
  for (const quarter of quarters) {
    try {
      const result = await importQuarter(quarter, tickers);
      filings += result.filings;
      written += result.written;
      if (result.failed) failed.push(quarter);
    } catch (error) {
      console.error(`[bulk] ${quarter}: ${error.message}`);
      failed.push(quarter);
    }
  }

  console.log('');
  console.log(`[bulk] ${filings.toLocaleString()} filing(s) assembled, ${written.toLocaleString()} written in ${elapsed()}s`);
  if (failed.length) console.log(`[bulk] ${failed.length} quarter(s) failed: ${failed.join(', ')}`);
  if (!APPLY) console.log('[bulk] dry run only. Re-run with --apply to write.');
  // A range where every quarter failed is a failure, not a quiet success.
  if (failed.length === quarters.length && quarters.length) process.exitCode = 1;
}

main().catch((error) => {
  console.error(`[bulk] ${error.message}`);
  process.exit(1);
});
