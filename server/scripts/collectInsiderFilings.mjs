/**
 * Form 4 insider filings for the securities we hold.
 *
 *   node server/scripts/collectInsiderFilings.mjs                  # dry run
 *   node server/scripts/collectInsiderFilings.mjs --limit 25       # dry run, 25
 *   node server/scripts/collectInsiderFilings.mjs --apply
 *   node server/scripts/collectInsiderFilings.mjs --apply --max-minutes 40
 *
 * The research layer already collects these, but from inside a refresh that
 * covers fifty tickers of the four thousand eight hundred held - enough to
 * prove the shape, not enough for the feature to exist. This does what the
 * price backfill does: covers the universe, incrementally, and records what it
 * did so the next run continues rather than restarts.
 *
 * Cost is bounded by two things. A ticker scanned within the last week is
 * skipped, because a Form 4 arrives within two business days of the trade and
 * a daily sweep of everything wastes most of its requests. And a filing whose
 * accession is already stored is never fetched again, so an issuer that has
 * filed nothing costs one index request and no documents.
 */
import { hostname } from 'node:os';
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { scheduleSecRequest } from '../services/secRateLimiter.js';
import { parseFormFour, rawDocumentPath } from '../services/formFour.js';
import { planScans, newFilings, abortReason } from '../services/insiderScanPlan.js';

const APPLY = process.argv.includes('--apply');
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const LIMIT = Number(argOf('--limit')) || null;
const MAX_MINUTES = Number(argOf('--max-minutes')) || 40;
const MAX_AGE_DAYS = Number(argOf('--max-age-days') ?? 7);
const PER_ISSUER = Number(argOf('--per-issuer')) || 40;

const SEC_ROOT = 'https://www.sec.gov';
const SEC_DATA = 'https://data.sec.gov';
const UA = (process.env.SEC_USER_AGENT || 'AGI Institutional Research research@agarwalglobalinvestments.com').trim();

if (!getSupabaseAdminCredentials()) {
  console.error('[insider] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const overCeiling = () => Date.now() - started > MAX_MINUTES * 60_000;

async function secJson(url) {
  const r = await scheduleSecRequest(() => fetch(url, { headers: { Accept: 'application/json', 'User-Agent': UA }, signal: AbortSignal.timeout(30_000) }));
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
async function secText(url) {
  const r = await scheduleSecRequest(() => fetch(url, { headers: { Accept: 'application/xml, text/xml, */*', 'User-Agent': UA }, signal: AbortSignal.timeout(30_000) }));
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.text();
}

async function all(build, page = 1000) {
  const rows = [];
  for (let from = 0; ; from += page) {
    const { data, error } = await build().range(from, from + page - 1);
    if (error) throw new Error(error.message);
    rows.push(...(data || []));
    if (!data || data.length < page) break;
    if (rows.length > 3_000_000) throw new Error('refusing to page past 3m rows');
  }
  return rows;
}

console.log(`[insider] mode=${APPLY ? 'APPLY' : 'DRY RUN'} ceiling=${MAX_MINUTES}m max-age=${MAX_AGE_DAYS}d per-issuer=${PER_ISSUER}`);

// ---- what we hold, and who those tickers are ------------------------------

const holdings = await all(() => client
  .from('institutional_holdings').select('ticker').not('ticker', 'is', null).is('put_call', null).order('ticker'));
const tickers = [...new Set(holdings.map((r) => String(r.ticker).toUpperCase()))];
console.log(`[insider] distinct held tickers: ${tickers.length.toLocaleString()}`);

const companyPayload = await secJson(`${SEC_ROOT}/files/company_tickers.json`);
const companies = new Map(Object.values(companyPayload || {})
  .map((row) => [String(row.ticker || '').toUpperCase(), { cik: String(row.cik_str || '').padStart(10, '0'), title: row.title }]));

const logRows = await all(() => client.from('institutional_insider_scan_log').select('ticker,scanned_at').order('ticker'));
const scannedAt = new Map(logRows.map((r) => [r.ticker, String(r.scanned_at || '').slice(0, 10)]));
console.log(`[insider] previously scanned: ${scannedAt.size.toLocaleString()}`);

const asOf = new Date().toISOString().slice(0, 10);
let { plans, skipped } = planScans(tickers, { companies, scannedAt, asOf, maxAgeDays: MAX_AGE_DAYS });
if (LIMIT) {
  const step = Math.max(1, Math.floor(plans.length / LIMIT));
  const spread = [];
  for (let i = 0; i < plans.length && spread.length < LIMIT; i += step) spread.push(plans[i]);
  plans = spread;
}

console.log('');
console.log(`[insider] ${plans.length.toLocaleString()} issuers to scan`);
console.log(`[insider]   skipped: ${skipped.noCik} no SEC CIK, ${skipped.recentlyScanned} scanned within ${MAX_AGE_DAYS} days`);
if (plans.length) console.log(`[insider]   sample: ${plans.slice(0, 6).map((p) => p.ticker).join(', ')}`);

if (!APPLY) {
  console.log('');
  console.log('[insider] DRY RUN - reading 3 issuers to show what would be stored.');
  for (const plan of plans.slice(0, 3)) {
    try {
      const subs = await secJson(`${SEC_DATA}/submissions/CIK${plan.cik}.json`);
      const recent = subs?.filings?.recent || {};
      const rows = (recent.form || []).map((form, i) => ({
        form, accession: recent.accessionNumber?.[i], filedAt: recent.filingDate?.[i],
        reportDate: recent.reportDate?.[i], document: recent.primaryDocument?.[i] || '',
      }));
      const fresh = newFilings(rows, new Set(), { limit: PER_ISSUER });
      console.log(`  ${plan.ticker.padEnd(8)} ${String(fresh.length).padStart(3)} Form 4 filing(s) in the recent index`);
      if (fresh[0]) {
        const url = `${SEC_ROOT}/Archives/edgar/data/${String(plan.cik).replace(/^0+/, '')}/${fresh[0].accession.replaceAll('-', '')}/${rawDocumentPath(fresh[0].document)}`;
        const parsed = parseFormFour(await secText(url));
        const t = parsed?.transactions?.[0];
        console.log(`    newest: ${parsed?.owners?.[0]?.name || '(no owner)'} — ${t ? `${t.code_label}, ${t.shares} shares, discretionary=${t.discretionary}` : 'no transactions'}${parsed?.planned ? ', pre-arranged' : ''}`);
      }
    } catch (error) { console.log(`  ${plan.ticker.padEnd(8)} failed: ${error.message}`); }
  }
  console.log('');
  console.log(`[insider] estimate: ${plans.length.toLocaleString()} index requests plus one per new filing.`);
  console.log('[insider] no writes. Re-run with --apply.');
  process.exit(0);
}

// ---- the run --------------------------------------------------------------

const known = new Set((await all(() => client
  .from('institutional_external_filings').select('accession_number').eq('event_type', 'insider_transaction').order('accession_number')))
  .map((r) => r.accession_number));
console.log(`[insider] filings already stored: ${known.size.toLocaleString()}`);
console.log('');
console.log(`[insider] APPLY - scanning ${plans.length.toLocaleString()} issuers`);

const tally = { scanned: 0, noFilings: 0, parsed: 0, unreadable: 0, written: 0, indexFailed: 0 };
const problems = [];
let aborted = null;

for (const plan of plans) {
  if (overCeiling()) { aborted = `reached the ${MAX_MINUTES}-minute ceiling`; break; }
  const reason = abortReason(tally);
  if (reason) { aborted = reason; break; }

  let rows = [];
  try {
    const subs = await secJson(`${SEC_DATA}/submissions/CIK${plan.cik}.json`);
    const recent = subs?.filings?.recent || {};
    rows = (recent.form || []).map((form, i) => ({
      form, accession: recent.accessionNumber?.[i], filedAt: recent.filingDate?.[i],
      reportDate: recent.reportDate?.[i], document: recent.primaryDocument?.[i] || '',
    }));
  } catch (error) {
    tally.indexFailed += 1;
    problems.push(`${plan.ticker}: index ${error.message}`);
    continue;
  }

  const fresh = newFilings(rows, known, { limit: PER_ISSUER });
  tally.scanned += 1;
  if (!fresh.length) {
    tally.noFilings += 1;
    await noteScan(plan, { seen: rows.filter((r) => /^4(\/A)?$/.test(r.form || '')).length, fresh: 0, parsed: 0, status: 'no_new_filings' });
    continue;
  }

  const output = [];
  let parsedHere = 0;
  for (const row of fresh) {
    if (overCeiling()) break;
    // The raw XML, not the XSL-rendered view primaryDocument names.
    const url = `${SEC_ROOT}/Archives/edgar/data/${String(plan.cik).replace(/^0+/, '')}/${row.accession.replaceAll('-', '')}/${rawDocumentPath(row.document)}`;
    let parsed = null;
    try {
      parsed = parseFormFour(await secText(url));
    } catch (error) {
      problems.push(`${plan.ticker} ${row.accession}: ${error.message}`);
    }
    if (parsed) { tally.parsed += 1; parsedHere += 1; } else { tally.unreadable += 1; }
    output.push({
      accession_number: row.accession,
      issuer_cik: plan.cik,
      ticker: plan.ticker,
      form_type: row.form,
      event_type: 'insider_transaction',
      filed_at: row.filedAt,
      report_date: row.reportDate,
      source_url: url,
      // A document that would not parse still records that the filing exists.
      // Dropping both would report an absence nobody observed.
      parsed_data: parsed ? { primary_document: row.document, ...parsed } : { primary_document: row.document, parse_status: 'unread' },
    });
    known.add(row.accession);
  }

  if (output.length) {
    for (let i = 0; i < output.length; i += 200) {
      const { error } = await client.from('institutional_external_filings')
        .upsert(output.slice(i, i + 200), { onConflict: 'accession_number' });
      if (error) throw new Error(`upsert ${plan.ticker}: ${error.message}`);
    }
    tally.written += output.length;
  }
  await noteScan(plan, { seen: rows.filter((r) => /^4(\/A)?$/.test(r.form || '')).length, fresh: fresh.length, parsed: parsedHere, status: 'scanned' });

  if (tally.scanned % 100 === 0) {
    console.log(`[insider] ${tally.scanned}/${plans.length}  written=${tally.written} parsed=${tally.parsed} unreadable=${tally.unreadable} ${elapsed()}s`);
  }
}

async function noteScan(plan, { seen, fresh, parsed, status, detail = null }) {
  const { error } = await client.from('institutional_insider_scan_log').upsert({
    ticker: plan.ticker, cik: plan.cik, scanned_at: new Date().toISOString(),
    filings_seen: seen, filings_new: fresh, filings_parsed: parsed, status, detail,
  }, { onConflict: 'ticker' });
  // The log is how the next run continues; failing to write it costs a repeat
  // scan, not correctness, so it warns rather than stopping the crawl.
  if (error) console.warn(`[insider] scan log ${plan.ticker}: ${error.message}`);
}

console.log('');
console.log('[insider] ---- result ----');
console.log(`[insider] issuers scanned   ${tally.scanned}`);
console.log(`[insider]   with no new     ${tally.noFilings}`);
console.log(`[insider]   index failed    ${tally.indexFailed}`);
console.log(`[insider] filings written   ${tally.written}`);
console.log(`[insider]   parsed          ${tally.parsed}`);
console.log(`[insider]   unreadable      ${tally.unreadable}`);
console.log(`[insider] elapsed ${elapsed()}s on ${hostname()}`);
if (problems.length) {
  console.log('');
  console.log(`[insider] ${problems.length} problem(s) (first 20):`);
  for (const p of problems.slice(0, 20)) console.log(`  ${p}`);
}
if (aborted) {
  console.log('');
  console.error(`[insider] STOPPED: ${aborted}`);
  console.error('[insider] The scan log records what was covered; re-running continues from there.');
  process.exit(1);
}
