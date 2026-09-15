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
// Ask again for symbols a previous run refused as reassigned. They are skipped
// by default because the answer cannot change, but a ticker can be reassigned
// back, and a holdings correction can move the date a position is held from.
const FORCE_REASSIGNED = process.argv.includes('--retry-reassigned');

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
// One row per security and ticker with the dates held, aggregated in the
// database. This used to page every holdings row through PostgREST and reduce
// them here; at 2.62M rows that stopped working - `canceling statement due to
// statement timeout` - and the answer it wanted was only ever a few thousand
// rows. The identity chain is joined in the same pass, so a reassigned CUSIP
// still resolves to one security_key without a second full table in memory.
console.log('[prices] reading price targets...');
// Paged. PostgREST caps a response at a thousand rows, and a set-returning
// function is no exception - the first run of this returned exactly 1,000 of
// 5,136 targets and reported it as the whole universe. Nothing errored: the
// backfill would have fetched a fifth of the symbols and called itself done.
const targets = [];
for (let from = 0; ; from += 1000) {
  const { data, error } = await client.rpc('institutional_price_targets').range(from, from + 999);
  if (error) throw new Error(`reading price targets: ${error.message}`);
  targets.push(...(data || []));
  if (!data || data.length < 1000) break;
  if (targets.length > 100_000) throw new Error('refusing to page past 100k price targets');
}
if (!targets.length) throw new Error('no price targets returned; refusing to run against nothing');
console.log(`[prices] ${targets.length.toLocaleString()} price target row(s)`);

const seen = new Map();
for (const row of targets) {
  const key = String(row.security_key || '').trim();
  if (!key || !row.ticker) continue;
  // Still keyed on both. One security can be held under more than one ticker
  // across a decade of filings, and each needs its own price history.
  seen.set(`${key}|${row.ticker}`, {
    security_key: key,
    ticker: row.ticker,
    first_report_date: row.first_report_date,
    last_report_date: row.last_report_date,
  });
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
  .select('ticker,fetched_at,status')
  .order('ticker'));
const freshness = new Map();
// Symbols the last fetch refused as reassigned. Asking again cannot help: the
// ticker belongs to another company now, and its history will not grow
// backwards into the years the position was held.
const reassigned = new Set();
for (const r of logRows) {
  freshness.set(r.ticker, String(r.fetched_at || '').slice(0, 10));
  if (r.status === 'rejected') reassigned.add(r.ticker);
}
console.log(`[prices] ${freshness.size.toLocaleString()} symbols in the fetch log`);

// Where each symbol's stored history begins, so the plan can tell a symbol
// that is current from one that is complete. The fetch log records when a
// symbol was last asked for and nothing about how far back the answer went,
// which is how twenty-nine symbols came to block forty-four of fifty-one
// managers while every one of them looked up to date.
const coverage = new Map();
try {
  // Paged, and ordered, because an RPC is capped at a thousand rows exactly as
  // a select is. Unpaged this returned the alphabetically first thousand
  // tickers and reported them as the whole table - so every symbol past the
  // letter C had no coverage entry, no gap was detected for it, and the
  // twenty-nine that prompted this work were all missed. The run then looked
  // successful: twenty-eight symbols due, none of them the ones asked about.
  const coverageRows = await all(() => client.rpc('institutional_price_coverage')
    .select('ticker,first_date')
    // Ordered, because paging without a total order lets rows move between
    // pages - some read twice, others not at all.
    .order('ticker'));
  for (const row of coverageRows) coverage.set(row.ticker, String(row.first_date || '').slice(0, 10));
  console.log(`[prices] ${coverage.size.toLocaleString()} symbols have stored price history`);
} catch (error) {
  // Not fatal. Without it the plan behaves exactly as it did before, which is
  // worse but not wrong, and a missing migration should not stop a backfill.
  console.warn(`[prices] coverage unavailable, planning on freshness alone: ${error.message}`);
}

// ---- the plan -------------------------------------------------------------

let { plans, skipped, foreignVenueSymbols } = planFetches([...seen.values()], {
  asOf, freshness, coverage, reassigned: FORCE_REASSIGNED ? null : reassigned,
  windowDays: WINDOW_DAYS, maxAgeDays: MAX_AGE_DAYS,
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
// Reported separately from the plan count, because it is the reason a symbol
// that looks current is being asked for again.
if (skipped.coverageGap) console.log(`[prices]   ${skipped.coverageGap} due because stored history starts after the security was first held`);
// Counted, not listed. They are a standing fact about the book rather than
// news, and repeating ten names every run is what makes a report unread.
if (skipped.reassigned) console.log(`[prices]   ${skipped.reassigned} not asked for: a previous fetch found the ticker now belongs to another company (--retry-reassigned to ask again)`);
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
