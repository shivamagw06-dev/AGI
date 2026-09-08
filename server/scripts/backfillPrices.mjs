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
// A refresh tops up recent sessions for everything held; a backfill builds the
// history once. Same script because the plan, the guards and the fetch log are
// the same - only the window and the staleness threshold differ.
const REFRESH = process.argv.includes('--refresh');
const WINDOW_DAYS = Number(argOf('--window-days')) || (REFRESH ? 10 : null);
const MAX_AGE_DAYS = argOf('--max-age-days') !== null
  ? Number(argOf('--max-age-days'))
  : (REFRESH ? 0 : 4);
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

console.log(`[prices] mode=${REFRESH ? `refresh (last ${WINDOW_DAYS} days)` : 'backfill (full history)'} max-age=${MAX_AGE_DAYS}d`);
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

// Freshness comes from the fetch log: one row per symbol, saying when it was
// last asked for and how that went.
//
// Two earlier versions of this read the price rows instead. Asking which
// tickers had a bar in the last ten days answered a different question, and
// answered it wrong for the symbols it mattered for - a delisted name whose
// history ends in July can never have a recent bar, so it never counted as
// done. Asking which rows were written recently answered the right question
// but did not scale, and got worse the more the backfill succeeded: every row
// it writes carries the run's timestamp, so a full pass leaves several million
// rows matching and the client pages through all of them to derive one date
// per symbol.
//
// The log also records the outcomes that write no prices at all - a symbol
// Yahoo does not know, a single-bar stub - which the price rows could not
// represent, so those were refetched on every run forever.
console.log('[prices] reading the fetch log...');
const logRows = await all(() => client
  .from('institutional_price_fetch_log')
  .select('ticker,fetched_at')
  .order('ticker'));
const freshness = new Map();
for (const r of logRows) freshness.set(r.ticker, String(r.fetched_at || '').slice(0, 10));
console.log(`[prices] ${freshness.size.toLocaleString()} symbols in the fetch log`);

// ---- the plan -------------------------------------------------------------

let { plans, skipped, foreignVenueSymbols } = planFetches([...seen.values()], {
  asOf, freshness, windowDays: WINDOW_DAYS, maxAgeDays: MAX_AGE_DAYS,
});
if (ONLY.length) plans = plans.filter((p) => ONLY.includes(p.symbol));
if (LIMIT) {
  // Spread across the run, not taken from the front. Symbols are sorted, and
  // digit-leading venue codes sort first, so `--limit 25` took twenty-five
  // pieces of junk: every one was unknown to Yahoo, nothing was written, and
  // the smoke test said nothing at all about the other 4,962 symbols. A
  // sample meant to answer "is this working" has to look like the run.
  const step = Math.max(1, Math.floor(plans.length / LIMIT));
  const spread = [];
  for (let i = 0; i < plans.length && spread.length < LIMIT; i += step) spread.push(plans[i]);
  plans = spread;
}

console.log('');
console.log(`[prices] ${plans.length.toLocaleString()} symbols to fetch`);
console.log(`[prices]   skipped: ${skipped.unusableTicker} unusable ticker, ${skipped.foreignVenue} foreign venue code, ${skipped.alreadyFresh} already fetched`);
if (foreignVenueSymbols.length) {
  console.log(`[prices]   foreign venue codes not asked for: ${foreignVenueSymbols.slice(0, 12).join(', ')}${foreignVenueSymbols.length > 12 ? ` (+${foreignVenueSymbols.length - 12} more)` : ''}`);
  console.log('[prices]   run recoverVenueTickers.mjs to map these back to their US tickers');
}
if (plans.length) {
  console.log(`[prices]   earliest start: ${plans.reduce((a, p) => (p.from < a ? p.from : a), plans[0].from)}`);
  console.log(`[prices]   sample: ${plans.slice(0, 6).map((p) => `${p.symbol}@${p.from}`).join(', ')}`);
}

if (!APPLY) {
  console.log('');
  // Sampled across the run, not from the front. Taking the first three
  // sorted symbols showed only 07WA, 0C3 and 0VVB - digit-leading codes sort
  // first, so the sample was made entirely of the least typical names in the
  // set and said nothing about the health of the other 4,984.
  const step = Math.max(1, Math.floor(plans.length / 6));
  const sample = [];
  for (let i = 0; i < plans.length && sample.length < 6; i += step) sample.push(plans[i]);
  console.log(`[prices] DRY RUN - fetching ${sample.length} symbols spread across the run.`);
  for (const plan of sample) {
    const res = await fetchDailyHistory(plan.symbol, { from: plan.from, to: plan.to });
    const bad = res.status === 'ok' ? coverageProblem(plan, res.bars) : null;
    const rows = res.status === 'ok' && !bad
      ? priceRows(plan, res.bars, { source: SOURCE, listingStatus: listingStatus(res.bars, asOf), sourceAsOf })
      : [];
    console.log(`  ${plan.symbol.padEnd(8)} ${res.status.padEnd(10)} ${String(res.bars.length).padStart(5)} bars -> ${rows.length} rows  ${bad || res.detail || ''}`);
    if (rows.length) console.log(`    first: ${JSON.stringify(rows[0])}`);
    await sleep(PAUSE_MS);
  }
  // Estimated from each symbol's own span. A flat bars-per-symbol figure
  // assumed every name needed the full 2019-2026 history and overstated the
  // job by roughly double - most positions are only a few years old.
  const TRADING_DAYS_PER_YEAR = 252;
  let estimate = 0;
  for (const plan of plans) {
    const years = (Date.parse(plan.to) - Date.parse(plan.from)) / 31_557_600_000;
    estimate += Math.max(1, Math.round(years * TRADING_DAYS_PER_YEAR)) * plan.securityKeys.length;
  }
  console.log('');
  console.log(`[prices] estimate: ~${estimate.toLocaleString()} rows across ${plans.length.toLocaleString()} requests`);
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

// Recorded whatever the outcome, so a symbol that cannot be priced is not
// asked about again on the next run.
const fetchLog = [];
function noteFetch(symbol, status, bars, detail) {
  fetchLog.push({ ticker: symbol, fetched_at: new Date().toISOString(), status, bars: bars || 0, detail: detail || null });
}

async function flushLog() {
  // Taken from the front, not cleared at the end. Three workers keep appending
  // while this awaits, and emptying the array afterwards threw those entries
  // away: the first full run recorded 4,867 of 4,870 outcomes, and the three
  // it lost were asked for again on the next run. Harmless individually, but
  // the leak grows with concurrency and never settles.
  while (fetchLog.length) {
    const chunk = fetchLog.splice(0, 500);
    const { error } = await client
      .from('institutional_price_fetch_log')
      .upsert(chunk, { onConflict: 'ticker' });
    // Put them back rather than losing the outcomes to a failed write.
    if (error) { fetchLog.unshift(...chunk); throw new Error(`fetch log: ${error.message}`); }
  }
}

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
        noteFetch(plan.symbol, 'rejected', res.bars.length, badCoverage);
      } else {
        const status = listingStatus(res.bars, asOf);
        const rows = priceRows(plan, res.bars, { source: SOURCE, listingStatus: status, sourceAsOf });
        await writeRows(rows);
        tally.ok += 1;
        tally.rows += rows.length;
        noteFetch(plan.symbol, status, res.bars.length, null);
        if (status !== 'active') problems.push(`${plan.symbol}: last bar ${res.bars.at(-1).price_date} (${status})`);
      }
    } else if (res.status === 'empty') {
      tally.empty += 1;
      problems.push(`${plan.symbol}: no bars in window`);
      noteFetch(plan.symbol, 'empty', 0, 'no bars in window');
    } else if (res.status === 'not_found') {
      tally.notFound += 1;
      problems.push(`${plan.symbol}: unknown to Yahoo`);
      noteFetch(plan.symbol, 'not_found', 0, 'unknown to Yahoo');
    } else {
      // A transport failure is not recorded. It says nothing about the symbol,
      // and logging it would retire a name that simply needs asking again.
      tally.failed += 1;
      problems.push(`${plan.symbol}: ${res.detail}`);
    }
    if (fetchLog.length >= 200) await flushLog();

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
await flushLog();

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
