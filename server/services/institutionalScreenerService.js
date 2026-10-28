/**
 * Combined holdings, stock screener, accumulation heat map and fund performance
 * evaluator, over the 51 tracked managers.
 *
 * All four answer questions about what the tracked managers filed. None of them
 * invent a number: every field here is either read from institutional_holdings
 * or computed from two filed positions, and where a computation cannot be made
 * the field is null with a stated reason rather than zero.
 *
 * Three of the four deliberately need no price data. Combined holdings, the
 * screener and the heat map are share-count and reported-value arithmetic over
 * filings, so they work today. Only the performance evaluator depends on
 * institutional_security_prices, and it reports its own coverage rather than
 * quietly ranking managers on partial data.
 *
 * Written independently from SEC filing structure and AGI's own tables. The
 * questions overlap with what other 13F products answer, because the questions
 * follow from the filings; the scoring, wording and shape here are ours.
 */

import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { coverageFor, blockersFor, disclosuresFor } from './coverageGate.js';

// PostgREST caps a page at 1000 rows and says nothing when it truncates. Every
// read here pages explicitly: a screener silently built on the first thousand
// holdings would rank the alphabet, not the market.
const PAGE = 1000;
const MAX_ROWS = 200_000;

// Every view here pages the whole holdings table, so an uncached endpoint
// would re-read tens of thousands of rows per request. 13F data changes when a
// filing lands, not by the second, so five minutes is generous freshness and a
// large saving.
const CACHE_TTL_MS = 5 * 60_000;
const cache = new Map();

async function cached(key, build) {
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < CACHE_TTL_MS) return hit.value;
  // Share the in-flight promise, so ten simultaneous requests on a cold cache
  // do one read rather than ten.
  if (hit?.pending) return hit.pending;
  const pending = build().then(
    (value) => { cache.set(key, { at: Date.now(), value }); return value; },
    (error) => { cache.delete(key); throw error; },
  );
  cache.set(key, { at: Date.now(), pending });
  return pending;
}

/** Called after an import or refresh, so the next read sees new filings. */
export function clearScreenerCache() {
  cache.clear();
}

function client() {
  const db = createSupabaseAdmin();
  if (!db) {
    const error = new Error('Supabase admin credentials are not configured.');
    error.code = 'SUPABASE_UNCONFIGURED';
    throw error;
  }
  return db;
}

async function pageAll(build) {
  const rows = [];
  for (let from = 0; from < MAX_ROWS; from += PAGE) {
    const { data, error } = await build().range(from, from + PAGE - 1);
    if (error) throw new Error(error.message);
    if (!data?.length) break;
    rows.push(...data);
    if (data.length < PAGE) break;
  }
  return rows;
}

function num(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

/** A holding's identity for cross-manager comparison. */
function securityKey(row) {
  return String(row.cusip || '').trim().toUpperCase() || null;
}

/** Latest report_date per manager, so every view compares like with like. */
function latestPeriodByManager(holdings) {
  const latest = new Map();
  for (const row of holdings) {
    const id = row.manager_id;
    const date = String(row.report_date || '');
    if (!id || !date) continue;
    if (!latest.has(id) || date > latest.get(id)) latest.set(id, date);
  }
  return latest;
}

async function loadManagers(db) {
  // Only tracked managers. An inactive one still has filings in the table, and
  // counting it would inflate ownership breadth with a manager the desk has
  // stopped following.
  const { data, error } = await db
    .from('institutional_managers')
    .select('id, slug, display_name')
    .eq('active', true);
  if (error) throw new Error(error.message);
  return new Map((data || []).map((m) => [m.id, m]));
}

/**
 * Holdings for the most recent filed period per manager, plus the period before
 * it, which is what every change figure below is computed from.
 */
async function loadRecentHoldings(db) {
  const rows = await pageAll(() => db
    .from('institutional_holdings')
    .select('manager_id, report_date, cusip, issuer_name, ticker, shares, value_usd, portfolio_weight, put_call')
    .order('report_date', { ascending: false }));

  const latest = latestPeriodByManager(rows);
  const priorByManager = new Map();
  for (const row of rows) {
    const id = row.manager_id;
    const date = String(row.report_date || '');
    if (!id || !date || date === latest.get(id)) continue;
    if (!priorByManager.has(id) || date > priorByManager.get(id)) priorByManager.set(id, date);
  }

  const current = rows.filter((r) => String(r.report_date) === latest.get(r.manager_id));
  const prior = rows.filter((r) => String(r.report_date) === priorByManager.get(r.manager_id));
  return { rows, current, prior, latest, priorByManager };
}

/** Shares held per (manager, security), for one snapshot. */
function sharesIndex(rows) {
  const index = new Map();
  for (const row of rows) {
    const key = securityKey(row);
    if (!key) continue;
    // Puts and calls are excluded: they are not a long equity position, and
    // counting them as one overstates both breadth and weight.
    if (row.put_call) continue;
    index.set(`${row.manager_id}|${key}`, num(row.shares));
  }
  return index;
}

// ---------------------------------------------------------------------------
// 1. Combined holdings — one portfolio from many managers
// ---------------------------------------------------------------------------

/**
 * Aggregate the tracked managers into a single portfolio.
 *
 * Weighted by reported value, because that is what the filings state. Share
 * counts are summed too, but they are only comparable within one security -
 * summing shares across securities means nothing, so nothing here does.
 */
async function getCombinedHoldingsUncached({ managerIds = null, limit = 100 } = {}) {
  const db = client();
  const managers = await loadManagers(db);
  const { current } = await loadRecentHoldings(db);

  const wanted = managerIds?.length ? new Set(managerIds) : null;
  const scoped = current.filter((r) => !r.put_call && (!wanted || wanted.has(r.manager_id)));

  const bySecurity = new Map();
  let totalValue = 0;
  for (const row of scoped) {
    const key = securityKey(row);
    if (!key) continue;
    const value = num(row.value_usd);
    totalValue += value;
    const entry = bySecurity.get(key) || {
      cusip: key,
      ticker: row.ticker || null,
      issuer_name: row.issuer_name || null,
      value_usd: 0,
      shares: 0,
      holders: new Set(),
    };
    entry.value_usd += value;
    entry.shares += num(row.shares);
    entry.holders.add(row.manager_id);
    // Prefer a resolved ticker if any holder has one; never invent it.
    if (!entry.ticker && row.ticker) entry.ticker = row.ticker;
    bySecurity.set(key, entry);
  }

  const positions = [...bySecurity.values()]
    .map((e) => ({
      cusip: e.cusip,
      ticker: e.ticker,
      issuer_name: e.issuer_name,
      value_usd: e.value_usd,
      shares: e.shares,
      holder_count: e.holders.size,
      holders: [...e.holders].map((id) => managers.get(id)?.display_name).filter(Boolean),
      combined_weight: totalValue > 0 ? e.value_usd / totalValue : null,
      ticker_resolved: Boolean(e.ticker),
    }))
    .sort((a, b) => b.value_usd - a.value_usd)
    .slice(0, Math.max(1, Math.min(Number(limit) || 100, 500)));

  return {
    ok: true,
    as_of: new Date().toISOString(),
    managers_included: wanted ? wanted.size : new Set(scoped.map((r) => r.manager_id)).size,
    positions_total: bySecurity.size,
    combined_value_usd: totalValue,
    positions,
    methodology:
      'Latest filed period per manager, weighted by reported value. Puts and calls excluded. '
      + 'Positions are aggregated on CUSIP, so a ticker change does not split a holding.',
    disclosure:
      'Built from delayed public 13F disclosure. Not live positioning and not investment advice.',
  };
}

// ---------------------------------------------------------------------------
// 2. Stock screener
// ---------------------------------------------------------------------------

/**
 * Screen securities on what the tracked managers did to them.
 *
 * Every filter is computed from two filed periods. There is no market data
 * here, so a security with no price coverage still screens correctly - which is
 * the point: ownership breadth is a filing fact, not a market fact.
 */
async function screenStocksUncached(filters = {}) {
  const db = client();
  const managers = await loadManagers(db);
  const { current, prior } = await loadRecentHoldings(db);

  const nowShares = sharesIndex(current);
  const wasShares = sharesIndex(prior);

  const bySecurity = new Map();
  for (const row of current) {
    if (row.put_call) continue;
    const key = securityKey(row);
    if (!key) continue;
    const entry = bySecurity.get(key) || {
      cusip: key,
      ticker: row.ticker || null,
      issuer_name: row.issuer_name || null,
      holders: 0,
      new_buyers: 0,
      increased: 0,
      reduced: 0,
      unchanged: 0,
      value_usd: 0,
      max_weight: 0,
      holder_names: [],
    };
    const before = wasShares.get(`${row.manager_id}|${key}`);
    const after = num(row.shares);
    entry.holders += 1;
    entry.value_usd += num(row.value_usd);
    entry.max_weight = Math.max(entry.max_weight, num(row.portfolio_weight));
    if (before === undefined) entry.new_buyers += 1;
    else if (after > before) entry.increased += 1;
    else if (after < before) entry.reduced += 1;
    else entry.unchanged += 1;
    const name = managers.get(row.manager_id)?.display_name;
    if (name) entry.holder_names.push(name);
    if (!entry.ticker && row.ticker) entry.ticker = row.ticker;
    bySecurity.set(key, entry);
  }

  // Exits: held in the prior period, absent from the current one.
  for (const [composite] of wasShares) {
    const [managerId, key] = composite.split('|');
    if (nowShares.has(composite)) continue;
    const entry = bySecurity.get(key);
    if (entry) entry.exits = (entry.exits || 0) + 1;
    else {
      const source = prior.find((r) => securityKey(r) === key);
      bySecurity.set(key, {
        cusip: key,
        ticker: source?.ticker || null,
        issuer_name: source?.issuer_name || null,
        holders: 0, new_buyers: 0, increased: 0, reduced: 0, unchanged: 0,
        exits: 1, value_usd: 0, max_weight: 0, holder_names: [],
      });
    }
    void managerId;
  }

  const {
    min_holders, min_new_buyers, min_increased, max_holders,
    has_exits, ticker_resolved, search, sort = 'holders', limit = 100,
  } = filters;

  const term = String(search || '').trim().toUpperCase();

  let rows = [...bySecurity.values()].map((e) => ({
    ...e,
    exits: e.exits || 0,
    net_buyers: (e.new_buyers || 0) + (e.increased || 0) - (e.reduced || 0) - (e.exits || 0),
    ticker_resolved: Boolean(e.ticker),
    holder_names: (e.holder_names || []).slice(0, 8),
  }));

  if (min_holders != null) rows = rows.filter((r) => r.holders >= Number(min_holders));
  if (max_holders != null) rows = rows.filter((r) => r.holders <= Number(max_holders));
  if (min_new_buyers != null) rows = rows.filter((r) => r.new_buyers >= Number(min_new_buyers));
  if (min_increased != null) rows = rows.filter((r) => r.increased >= Number(min_increased));
  if (has_exits === true || has_exits === 'true') rows = rows.filter((r) => r.exits > 0);
  if (ticker_resolved === true || ticker_resolved === 'true') rows = rows.filter((r) => r.ticker_resolved);
  if (term) {
    rows = rows.filter((r) =>
      String(r.ticker || '').toUpperCase().includes(term)
      || String(r.issuer_name || '').toUpperCase().includes(term)
      || r.cusip.includes(term));
  }

  const sorters = {
    holders: (a, b) => b.holders - a.holders,
    new_buyers: (a, b) => b.new_buyers - a.new_buyers,
    net_buyers: (a, b) => b.net_buyers - a.net_buyers,
    exits: (a, b) => b.exits - a.exits,
    value: (a, b) => b.value_usd - a.value_usd,
    concentration: (a, b) => b.max_weight - a.max_weight,
  };
  rows.sort(sorters[sort] || sorters.holders);

  const capped = rows.slice(0, Math.max(1, Math.min(Number(limit) || 100, 500)));

  return {
    ok: true,
    as_of: new Date().toISOString(),
    universe_size: bySecurity.size,
    matched: rows.length,
    returned: capped.length,
    filters_applied: filters,
    results: capped,
    methodology:
      'Latest filed period compared against the one before it, per manager. '
      + 'A new buyer had no position last period; an exit held one and no longer does. '
      + 'Puts and calls are excluded. Securities are keyed on CUSIP.',
    disclosure:
      'Built from delayed public 13F disclosure. Not live positioning and not investment advice.',
  };
}

// ---------------------------------------------------------------------------
// 3. Accumulation / reduction heat map
// ---------------------------------------------------------------------------

/**
 * Which securities the tracked managers are collectively adding to or leaving.
 *
 * Measured in holders and in share change, never in price. A stock can be
 * heavily accumulated and falling; conflating the two would make this a
 * performance chart wearing an ownership label.
 */
async function getAccumulationHeatMapUncached({ limit = 40 } = {}) {
  const db = client();
  const { current, prior } = await loadRecentHoldings(db);
  const nowShares = sharesIndex(current);
  const wasShares = sharesIndex(prior);

  const bySecurity = new Map();
  const touch = (key, seed) => {
    if (!bySecurity.has(key)) {
      bySecurity.set(key, {
        cusip: key,
        ticker: seed?.ticker || null,
        issuer_name: seed?.issuer_name || null,
        buyers: 0, sellers: 0, new_buyers: 0, exits: 0,
        shares_added: 0, shares_removed: 0, holders_now: 0,
      });
    }
    return bySecurity.get(key);
  };

  for (const row of current) {
    if (row.put_call) continue;
    const key = securityKey(row);
    if (!key) continue;
    const entry = touch(key, row);
    entry.holders_now += 1;
    if (!entry.ticker && row.ticker) entry.ticker = row.ticker;
    const before = wasShares.get(`${row.manager_id}|${key}`);
    const after = num(row.shares);
    if (before === undefined) { entry.new_buyers += 1; entry.buyers += 1; entry.shares_added += after; }
    else if (after > before) { entry.buyers += 1; entry.shares_added += after - before; }
    else if (after < before) { entry.sellers += 1; entry.shares_removed += before - after; }
  }

  for (const [composite, before] of wasShares) {
    if (nowShares.has(composite)) continue;
    const key = composite.split('|')[1];
    const seed = prior.find((r) => securityKey(r) === key);
    const entry = touch(key, seed);
    entry.exits += 1;
    entry.sellers += 1;
    entry.shares_removed += before;
  }

  const scored = [...bySecurity.values()].map((e) => {
    const active = e.buyers + e.sellers;
    return {
      ...e,
      // Breadth of agreement among managers who moved, from -1 to +1. Managers
      // who did nothing are excluded rather than counted as neutral, which
      // would let a widely-held-but-untouched stock look contested.
      net_breadth: active > 0 ? (e.buyers - e.sellers) / active : null,
      managers_active: active,
    };
  });

  const cap = Math.max(1, Math.min(Number(limit) || 40, 200));
  const ranked = (dir) => scored
    .filter((e) => e.managers_active > 0 && e.net_breadth !== null)
    .sort((a, b) => (dir === 'hot'
      ? b.net_breadth - a.net_breadth || b.managers_active - a.managers_active
      : a.net_breadth - b.net_breadth || b.managers_active - a.managers_active))
    .slice(0, cap);

  return {
    ok: true,
    as_of: new Date().toISOString(),
    universe_size: bySecurity.size,
    accumulating: ranked('hot'),
    reducing: ranked('cold'),
    methodology:
      'Net breadth is (buyers - sellers) / managers who moved, between -1 and +1. '
      + 'Managers who held a position unchanged are excluded from the denominator. '
      + 'Share changes are counts, not prices: this measures ownership, not performance.',
    disclosure:
      'Built from delayed public 13F disclosure. Not live positioning and not investment advice.',
  };
}

// ---------------------------------------------------------------------------
// 4. Fund performance evaluator
// ---------------------------------------------------------------------------

/**
 * Compare managers on what can actually be measured today.
 *
 * This is the one view that needs prices, so it states its own coverage per
 * manager and refuses to rank on data it does not have. A league table built
 * on 40% price coverage is a table of who happens to hold liquid US large caps.
 */
async function evaluateFundPerformanceUncached({ minPeriods = 3, minValueCoverage = 0.95 } = {}) {
  const db = client();
  const managers = await loadManagers(db);

  const periodRows = await pageAll(() => db
    .from('institutional_filings')
    .select('manager_id, report_date, filed_at, is_active, form_type')
    .eq('is_active', true));

  const periodsByManager = new Map();
  for (const row of periodRows) {
    if (!row.manager_id) continue;
    const set = periodsByManager.get(row.manager_id) || new Set();
    set.add(String(row.report_date));
    periodsByManager.set(row.manager_id, set);
  }

  const holdings = await pageAll(() => db
    .from('institutional_holdings')
    .select('manager_id, cusip, ticker, put_call, value_usd, report_date'));

  // The current book, not every position ever held. Coverage is a statement
  // about what the reader is being shown, and mixing in securities sold three
  // years ago describes a portfolio nobody holds.
  const latestByManager = new Map();
  for (const row of holdings) {
    if (row.put_call) continue;
    const seen = latestByManager.get(row.manager_id);
    if (!seen || String(row.report_date) > seen) latestByManager.set(row.manager_id, String(row.report_date));
  }

  const securitiesByManager = new Map();
  for (const row of holdings) {
    if (row.put_call) continue;
    if (String(row.report_date) !== latestByManager.get(row.manager_id)) continue;
    const key = securityKey(row);
    if (!key) continue;
    const list = securitiesByManager.get(row.manager_id) || [];
    list.push({ security_key: key, ticker: row.ticker || null, value_usd: row.value_usd });
    securitiesByManager.set(row.manager_id, list);
  }

  // Which symbols have prices, read from the fetch log rather than the price
  // rows. Asking the price table meant paging every row that has an adjusted
  // close to build a set of distinct tickers - fine at 73,000 rows, and 3.2
  // million after the backfill. The log holds one row per symbol and answers
  // the same question in a single page.
  const priced = new Set();
  const logRows = await pageAll(() => db
    .from('institutional_price_fetch_log')
    .select('ticker, status, bars'));
  for (const row of logRows) {
    if (!row.ticker || !(Number(row.bars) > 0)) continue;
    // A rejected symbol wrote no prices: its history belonged to a different
    // security, or was a single-bar stub.
    if (row.status === 'rejected' || row.status === 'empty' || row.status === 'not_found') continue;
    priced.add(String(row.ticker).toUpperCase());
  }

  const rows = [];
  for (const [id, manager] of managers) {
    const periods = periodsByManager.get(id)?.size || 0;
    const coverage = coverageFor(securitiesByManager.get(id) || [], priced);
    const blockers = blockersFor({ periods, coverage }, { minPeriods, minValueCoverage });

    rows.push({
      manager_id: id,
      slug: manager.slug,
      display_name: manager.display_name,
      filed_periods: periods,
      as_of: latestByManager.get(id) || null,
      ...coverage,
      evaluable: blockers.length === 0,
      blockers,
      // Facts the reader gets even when the manager clears the gate.
      disclosures: disclosuresFor(coverage),
    });
  }

  rows.sort((a, b) =>
    Number(b.evaluable) - Number(a.evaluable)
    || (b.value_coverage ?? -1) - (a.value_coverage ?? -1));

  const evaluable = rows.filter((r) => r.evaluable);
  return {
    ok: true,
    as_of: new Date().toISOString(),
    managers_total: rows.length,
    managers_evaluable: evaluable.length,
    gate: { min_periods: minPeriods, min_value_coverage: minValueCoverage },
    managers: rows,
    // Stated rather than implied. Zero evaluable managers is a real answer and
    // the page should say so instead of rendering an empty league table.
    note: evaluable.length === 0
      ? 'No manager currently clears the gate. Performance is withheld rather than shown on partial data; the blockers above say what each one needs.'
      : `${evaluable.length} of ${rows.length} managers clear the gate.`,
    methodology:
      'Coverage is measured on the most recent filed book, weighted by reported value: the share of '
      + 'that value held in securities with an adjusted price. A return is a value-weighted quantity, '
      + 'so the share of line items resolved is reported alongside but is not what the gate turns on - '
      + 'counting would weigh an odd-lot the same as a core position, and every 13F book contains a '
      + 'few securities that carry no ticker. Those are disclosed with their weight rather than used '
      + 'to withhold the whole manager. Puts and calls are excluded. A manager below the gate is '
      + 'listed with its blockers, never with a partial return.',
    disclosure:
      'Built from delayed public 13F disclosure. Not live positioning and not investment advice.',
  };
}

export const _internals = { securityKey, sharesIndex, latestPeriodByManager };


// ---------------------------------------------------------------------------
// Cached entry points. The uncached functions above stay pure so they can be
// exercised directly in a test without a warm cache changing the answer.
// ---------------------------------------------------------------------------

export const getCombinedHoldings = (opts = {}) =>
  cached(`combined:${JSON.stringify(opts)}`, () => getCombinedHoldingsUncached(opts));

export const screenStocks = (filters = {}) =>
  cached(`screener:${JSON.stringify(filters)}`, () => screenStocksUncached(filters));

export const getAccumulationHeatMap = (opts = {}) =>
  cached(`heatmap:${JSON.stringify(opts)}`, () => getAccumulationHeatMapUncached(opts));

export const evaluateFundPerformance = (opts = {}) =>
  cached(`performance:${JSON.stringify(opts)}`, () => evaluateFundPerformanceUncached(opts));
