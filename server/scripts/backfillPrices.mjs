/**
 * Daily price history for the securities we hold.
 *
 *   node server/scripts/backfillPrices.mjs                 # dry run
 *   node server/scripts/backfillPrices.mjs --limit 25      # dry run, 25 symbols
 *   node server/scripts/backfillPrices.mjs --apply
 *   node server/scripts/backfillPrices.mjs --apply --limit 25
 *   node server/scripts/backfillPrices.mjs --apply --symbols AAPL,MSFT
 *
 * Source is Yahoo's chart endpoint - one request returns a symbol's whole
 * history, so this is roughly one request per ticker rather than per quarter.
 *
 * Two things about the data are worth knowing before reading further. Yahoo's
 * `close` is retroactively split-adjusted, so it is not what the share traded
 * at on the day and must not be multiplied by a 13F share count; `adjclose`
 * is adjusted for dividends too and is what a return is computed from. Both
 * are stored under names that say which is which.
 *
 * The run is resumable: a symbol whose stored history already reaches the run
 * date is skipped, so an interrupted backfill continues instead of restarting.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { fetchDailyHistory } from '../providers/yahooDailyHistory.js';
import { planFetches, priceRows, abortReason, coverageProblem } from '../services/pricePlan.js';
import { listingStatus } from '../services/dailyBars.js';

const APPLY = process.argv.includes('--apply');
const SOURCE = 'yahoo-chart-v8';
const CONCURRENCY = 3;
const PAUSE_MS = 250;

const argOf = (flag) => {
  const i = process.argv.indexOf(flag);
  return i >= 0 ? process.argv[i + 1] : null;
};
const LIMIT = Number(argOf('--limit')) || null;
const ONLY = (argOf('--symbols') || '').split(',').map((s) => s.trim().toUpperCase()).filter(Boolean);

if (!getSupabaseAdminCredentials()) {
  console.error('[prices] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();
const asOf = new Date().toISOString().slice(0, 10);
const sourceAsOf = new Date().toISOString();

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

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- what we hold ---------------------------------------------------------

console.log('[prices] reading holdings...');
const holdings = await all(() => client
  .from('institutional_holdings')
  .select('cusip,ticker,report_date')
  .not('ticker', 'is', null)
  .is('put_call', null)
  .order('cusip'));
console.log(`[prices] ${holdings.length.toLocaleString()} priced-instrument holding rows`);

console.log('[prices] reading identity chain...');
const chain = await all(() => client.from('sec_13f_identity_chain').select('cusip,security_key').order('cusip'));
const keyByCusip = new Map(chain.map((r) => [r.cusip, r.security_key]));

// Collapse to one row per (security_key, ticker) with the earliest date held.
const seen = new Map();
for (const h of holdings) {
  const key = keyByCusip.get(h.cusip) || h.cusip;
  if (!key) continue;
  const id = `${key}|${h.ticker}`;
  const prev = seen.get(id);
  if (!prev) {
    seen.set(id, { security_key: key, ticker: h.ticker, first_report_date: h.report_date, last_report_date: h.report_date });
    continue;
  }
  if (h.report_date && h.report_date < prev.first_report_date) prev.first_report_date = h.report_date;
  if (h.report_date && h.report_date > prev.last_report_date) prev.last_report_date = h.report_date;
}
console.log(`[prices] ${seen.size.toLocaleString()} distinct (security_key, ticker) pairs`);

// ---- what we already have -------------------------------------------------

// Only the recent window is read. Asking which tickers have a row in the last
// ten days answers the freshness question exactly, and reads a few thousand
// rows instead of paging the whole price table to compute a max per ticker.
const recentFrom = new Date(Date.now() - 10 * 86_400_000).toISOString().slice(0, 10);
console.log(`[prices] reading stored prices since ${recentFrom}...`);
const recent = await all(() => client
  .from('institutional_security_prices')
  .select('ticker,price_date')
  .gte('price_date', recentFrom)
  .order('ticker'));
const freshness = new Map();
for (const r of recent) {
  const cur = freshness.get(r.ticker);
  if (!cur || r.price_date > cur) freshness.set(r.ticker, r.price_date);
}
console.log(`[prices] ${freshness.size.toLocaleString()} symbols already current`);

// ---- the plan -------------------------------------------------------------

let { plans, skipped } = planFetches([...seen.values()], { asOf, freshness });
if (ONLY.length) plans = plans.filter((p) => ONLY.includes(p.symbol));
if (LIMIT) plans = plans.slice(0, LIMIT);

console.log('');
console.log(`[prices] ${plans.length.toLocaleString()} symbols to fetch`);
console.log(`[prices]   skipped: ${skipped.unusableTicker} unusable ticker, ${skipped.alreadyFresh} already current`);
if (plans.length) {
  console.log(`[prices]   earliest start: ${plans.reduce((a, p) => (p.from < a ? p.from : a), plans[0].from)}`);
  console.log(`[prices]   sample: ${plans.slice(0, 6).map((p) => `${p.symbol}@${p.from}`).join(', ')}`);
}

if (!APPLY) {
  console.log('');
  console.log('[prices] DRY RUN - fetching 3 symbols to show what would be written.');
  for (const plan of plans.slice(0, 3)) {
    const res = await fetchDailyHistory(plan.symbol, { from: plan.from, to: plan.to });
    const bad = res.status === 'ok' ? coverageProblem(plan, res.bars) : null;
    const rows = res.status === 'ok' && !bad
      ? priceRows(plan, res.bars, { source: SOURCE, listingStatus: listingStatus(res.bars, asOf), sourceAsOf })
      : [];
    console.log(`  ${plan.symbol.padEnd(8)} ${res.status.padEnd(10)} ${String(res.bars.length).padStart(5)} bars -> ${rows.length} rows  ${bad || res.detail || ''}`);
    if (rows.length) console.log(`    first: ${JSON.stringify(rows[0])}`);
    await sleep(PAUSE_MS);
  }
  const perSymbol = 1900;
  console.log('');
  console.log(`[prices] estimate: ~${(plans.length * perSymbol).toLocaleString()} rows across ${plans.length.toLocaleString()} requests`);
  console.log('[prices] no writes. Re-run with --apply.');
  process.exit(0);
}

// ---- the run --------------------------------------------------------------

const tally = {
  ok: 0, empty: 0, notFound: 0, failed: 0, throttled: 0, reassigned: 0, rows: 0,
  // Measured only over securities still held, so a wave of delistings cannot
  // be mistaken for a broken ticker mapping.
  live: { done: 0, notFound: 0 },
};
const problems = [];
let aborted = null;
let cursor = 0;

async function writeRows(rows) {
  for (let i = 0; i < rows.length; i += 1000) {
    const chunk = rows.slice(i, i + 1000);
    const { error } = await client
      .from('institutional_security_prices')
      .upsert(chunk, { onConflict: 'security_key,price_date,source' });
    if (error) throw new Error(`upsert: ${error.message}`);
  }
}

async function worker() {
  for (;;) {
    if (aborted) return;
    const plan = plans[cursor++];
    if (!plan) return;

    let res = await fetchDailyHistory(plan.symbol, { from: plan.from, to: plan.to });
    // One backoff on a throttle. A second refusal is counted, not hammered.
    if (res.status === 'throttled') {
      tally.throttled += 1;
      await sleep(5_000);
      res = await fetchDailyHistory(plan.symbol, { from: plan.from, to: plan.to });
    }

    if (res.status === 'ok') {
      // A ticker outlives its company: FB now serves an unrelated firm's
      // history starting 2025. Writing that against a 2019 Facebook holding
      // would be a fabricated price series, so it is refused, not stored.
      const badCoverage = coverageProblem(plan, res.bars);
      if (badCoverage) {
        tally.reassigned += 1;
        problems.push(`${plan.symbol}: REJECTED - ${badCoverage}`);
      } else {
        const status = listingStatus(res.bars, asOf);
        const rows = priceRows(plan, res.bars, { source: SOURCE, listingStatus: status, sourceAsOf });
        await writeRows(rows);
        tally.ok += 1;
        tally.rows += rows.length;
        if (status !== 'active') problems.push(`${plan.symbol}: last bar ${res.bars.at(-1).price_date} (${status})`);
      }
    } else if (res.status === 'empty') {
      tally.empty += 1;
      problems.push(`${plan.symbol}: no bars in window`);
    } else if (res.status === 'not_found') {
      tally.notFound += 1;
      problems.push(`${plan.symbol}: unknown to Yahoo`);
    } else {
      tally.failed += 1;
      problems.push(`${plan.symbol}: ${res.detail}`);
    }

    if (plan.heldNow) {
      tally.live.done += 1;
      if (res.status === 'not_found') tally.live.notFound += 1;
    }

    const done = tally.ok + tally.empty + tally.notFound + tally.failed;
    if (done % 100 === 0) {
      console.log(`[prices] ${done}/${plans.length}  ok=${tally.ok} empty=${tally.empty} unknown=${tally.notFound} failed=${tally.failed} rows=${tally.rows.toLocaleString()}`);
    }
    const reason = abortReason(tally);
    if (reason) { aborted = reason; return; }
    await sleep(PAUSE_MS);
  }
}

console.log('');
console.log(`[prices] APPLY - fetching ${plans.length.toLocaleString()} symbols at concurrency ${CONCURRENCY}`);
await Promise.all(Array.from({ length: CONCURRENCY }, worker));

console.log('');
console.log('[prices] ---- result ----');
console.log(`[prices] ok        ${tally.ok}`);
console.log(`[prices] empty     ${tally.empty}`);
console.log(`[prices] unknown   ${tally.notFound}`);
console.log(`[prices] failed    ${tally.failed}`);
console.log(`[prices] throttled ${tally.throttled}`);
console.log(`[prices] rejected  ${tally.reassigned}  (ticker reassigned to another company)`);
console.log(`[prices] of currently-held symbols: ${tally.live.done - tally.live.notFound}/${tally.live.done} found`);
console.log(`[prices] rows written ${tally.rows.toLocaleString()}`);
if (problems.length) {
  console.log('');
  console.log(`[prices] ${problems.length} symbols need a look (first 40):`);
  for (const p of problems.slice(0, 40)) console.log(`  ${p}`);
}
if (aborted) {
  console.log('');
  console.error(`[prices] ABORTED: ${aborted}`);
  console.error('[prices] The history written so far is partial. Fix the cause before re-running.');
  process.exit(1);
}
