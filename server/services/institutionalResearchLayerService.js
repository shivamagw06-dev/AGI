import crypto from 'node:crypto';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { scheduleSecRequest } from './secRateLimiter.js';
import { getRepairStatus } from './institutionalHoldingsService.js';
import { firstTradableSession, sessionsFromPrices, periodReturn as pitPeriodReturn, benchmarkReturn, orderByAcceptance } from './pointInTime.js';
import { fetchDailyHistory } from '../providers/yahooDailyHistory.js';
import { listingStatus } from './dailyBars.js';
import { coverageProblem } from './pricePlan.js';
import { coverageProfile, backtestBlockers } from './backtestCoverage.js';
import { parseFormFour, rawDocumentPath } from './formFour.js';

const SEC_DATA = 'https://data.sec.gov';
const SEC_ARCHIVES = 'https://www.sec.gov/Archives/edgar/data';
const BENCHMARKS = ['SPY', 'QQQ'];
const DAY_MS = 86_400_000;
let automationStarted = false;

function db() {
  const client = createSupabaseAdmin();
  if (!client) throw new Error('Institutional research database is not configured.');
  return client;
}
const number = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
const dateOnly = (value) => { const date = value ? new Date(value) : null; return date && !Number.isNaN(date.getTime()) ? date.toISOString().slice(0, 10) : null; };
const tickerOf = (row = {}) => String(row.ticker || row.mapped_ticker || '').trim().toUpperCase();
const keyOf = (row = {}) => String(row.security_key || row.cusip || tickerOf(row) || row.issuer_name || '').trim().toUpperCase();
const valueOf = (row = {}) => number(row.value_usd || row.reported_value_usd || row.market_value_usd || row.reported_value || row.value);
const sharesOf = (row = {}) => number(row.shares || row.share_count || row.ssh_prnamt || row.quantity);

async function sourceJson(url) {
  const response = await scheduleSecRequest(() => fetch(url, { headers: { Accept: 'application/json', 'User-Agent': process.env.SEC_USER_AGENT || 'Agarwal Global Investments research@agarwalglobalinvestments.com' }, signal: AbortSignal.timeout(30_000) }));
  if (!response.ok) throw new Error(`Source request failed (${response.status})`);
  return response.json();
}

/**
 * A filing document, as text.
 *
 * Same limiter and user agent as the JSON path - EDGAR counts every request
 * against one address whatever it is asking for.
 */
async function sourceText(url) {
  const response = await scheduleSecRequest(() => fetch(url, {
    headers: {
      Accept: 'application/xml, text/xml, text/plain, */*',
      'User-Agent': process.env.SEC_USER_AGENT || 'Agarwal Global Investments research@agarwalglobalinvestments.com',
    },
    signal: AbortSignal.timeout(30_000),
  }));
  if (!response.ok) throw new Error(`Document request failed (${response.status})`);
  return response.text();
}

async function tickerMap() {
  const payload = await sourceJson('https://www.sec.gov/files/company_tickers.json');
  return new Map(Object.values(payload || {}).map((row) => [String(row.ticker || '').toUpperCase(), { cik: String(row.cik_str || '').padStart(10, '0'), title: row.title }]));
}
const submission = (cik) => sourceJson(`${SEC_DATA}/submissions/CIK${String(cik).padStart(10, '0')}.json`);

function recentFilings(payload = {}) {
  const recent = payload.filings?.recent || {};
  return Array.from({ length: recent.form?.length || 0 }, (_, index) => ({
    accession: recent.accessionNumber?.[index], form: recent.form?.[index],
    filedAt: recent.acceptanceDateTime?.[index] || recent.filingDate?.[index],
    reportDate: recent.reportDate?.[index] || null, document: recent.primaryDocument?.[index] || '',
  }));
}

function classifySic(code, description) {
  const sic = number(code);
  const ranges = [
    [100, 999, 'Natural Resources', 'Agriculture & Forestry'], [1000, 1499, 'Energy & Materials', 'Mining'],
    [1500, 1799, 'Industrials', 'Construction'], [2000, 2399, 'Consumer Staples', 'Food, Beverage & Textiles'],
    [2400, 2799, 'Materials', 'Manufacturing & Paper'], [2800, 2899, 'Health Care', 'Chemicals & Pharmaceuticals'],
    [2900, 2999, 'Energy', 'Petroleum'], [3000, 3999, 'Industrials', 'Industrial Manufacturing'],
    [4000, 4799, 'Industrials', 'Transportation'], [4800, 4899, 'Communication Services', 'Telecommunications'],
    [4900, 4999, 'Utilities', 'Utilities'], [5000, 5199, 'Industrials', 'Wholesale Trade'],
    [5200, 5999, 'Consumer Discretionary', 'Retail'], [6000, 6499, 'Financials', 'Banking & Credit'],
    [6500, 6799, 'Real Estate', 'Real Estate & Investment Vehicles'], [7000, 7999, 'Consumer Discretionary', 'Services & Leisure'],
    [8000, 8099, 'Health Care', 'Health Services'], [8100, 8999, 'Industrials', 'Professional Services'],
  ];
  const match = ranges.find(([from, to]) => sic >= from && sic <= to);
  return { sector: match?.[2] || 'Unclassified', industry: description || match?.[3] || 'Unclassified' };
}

/**
 * Daily prices for one symbol.
 *
 * This wrapped its own copy of the Yahoo call, and that copy had three faults
 * the shared one is tested against. It filled a missing adjusted close with
 * the raw close, which quietly mixes an unadjusted price into a series named
 * adjusted and makes every return spanning that day wrong. It dated bars by
 * their UTC calendar day, which is right for US equities only by luck of the
 * session falling mid-day UTC. And it asked for a fixed five-year window
 * regardless of how long the position had been held.
 */
async function adjustedPrices(ticker, { from } = {}) {
  const to = new Date().toISOString().slice(0, 10);
  const start = from || new Date(Date.now() - 5 * 365 * DAY_MS).toISOString().slice(0, 10);
  const res = await scheduleSecRequest(() => fetchDailyHistory(ticker, { from: start, to }));
  if (res.status !== 'ok') throw new Error(`Adjusted prices unavailable for ${ticker} (${res.detail || res.status})`);
  return { rows: res.bars, currency: res.currency || 'USD', listingStatus: listingStatus(res.bars, to) };
}

async function batches(client, table, rows, onConflict, size = 500) {
  for (let index = 0; index < rows.length; index += size) {
    const { error } = await client.from(table).upsert(rows.slice(index, index + size), { onConflict });
    if (error) throw error;
  }
}

async function core() {
  const client = db();
  const [{ data: managers, error: managerError }, { data: filings, error: filingError }] = await Promise.all([
    client.from('institutional_managers').select('*').order('display_name'),
    // is_active, deliberately.
    //
    // A superseded filing keeps its row: when an amendment restates a quarter,
    // the earlier version is marked inactive rather than deleted, so the record
    // of what was originally disclosed survives. Loading every filing therefore
    // loaded both versions of the same quarter and counted the restated
    // positions twice - once from the report the manager withdrew.
    //
    // Only same-quarter versions are deactivated, so this keeps the full
    // history across quarters and drops only what has been superseded.
    client.from('institutional_filings').select('*').eq('is_active', true).order('report_date', { ascending: false }).limit(1000),
  ]);
  if (managerError || filingError) throw managerError || filingError;
  const holdings = [];
  const ids = (filings || []).map((row) => row.id);
  for (let index = 0; index < ids.length; index += 100) {
    const { data, error } = await client.from('institutional_holdings').select('*').in('filing_id', ids.slice(index, index + 100));
    if (error) throw error;
    holdings.push(...(data || []));
  }
  return { client, managers: managers || [], filings: filings || [], holdings };
}

function filingMap(filings) {
  const unique = new Map();
  [...filings].sort((a, b) => String(b.accepted_at || b.filed_at || '').localeCompare(String(a.accepted_at || a.filed_at || ''))).forEach((filing) => {
    const key = `${filing.manager_id}:${filing.report_date}`;
    if (!unique.has(key)) unique.set(key, filing);
  });
  const result = new Map();
  unique.forEach((filing) => { const rows = result.get(filing.manager_id) || []; rows.push(filing); result.set(filing.manager_id, rows); });
  result.forEach((rows) => rows.sort((a, b) => String(b.report_date).localeCompare(String(a.report_date))));
  return result;
}

async function collectClassifications(client, holdings, companies, limit) {
  const securities = [...new Map(holdings.filter((row) => tickerOf(row)).map((row) => [keyOf(row), row])).values()].slice(0, limit);
  const output = [];
  for (const holding of securities) {
    const ticker = tickerOf(holding);
    const company = companies.get(ticker);
    if (!company) continue;
    try {
      const sec = await submission(company.cik);
      output.push({ security_key: keyOf(holding), cusip: holding.cusip || null, ticker, issuer_name: holding.issuer_name || company.title, issuer_cik: company.cik, sic_code: String(sec.sic || ''), ...classifySic(sec.sic, sec.sicDescription), valid_from: dateOnly(holding.report_date || holding.created_at) || dateOnly(new Date()), source: 'SEC submissions', source_url: `${SEC_DATA}/submissions/CIK${company.cik}.json`, source_as_of: new Date().toISOString(), confidence: sec.sic ? 0.95 : 0.5, updated_at: new Date().toISOString() });
    } catch (error) { console.warn(`[institutional-v3] classification ${ticker}: ${error.message}`); }
  }
  if (output.length) await batches(client, 'institutional_security_classifications', output, 'security_key,valid_from,source');
  return output.length;
}

async function collectPrices(client, holdings, limit) {
  // Keyed by the security, not by the symbol. This wrote the ticker into
  // security_key, which made the price table the one place that column meant
  // something different from everywhere else, and left two identifiers
  // sharing a ticker indistinguishable.
  const byTicker = new Map();
  for (const holding of holdings) {
    const ticker = tickerOf(holding);
    if (!ticker) continue;
    const entry = byTicker.get(ticker) || { ticker, type: 'equity', key: keyOf(holding), earliestHeld: null };
    const held = dateOnly(holding.report_date);
    if (held && (!entry.earliestHeld || held < entry.earliestHeld)) entry.earliestHeld = held;
    byTicker.set(ticker, entry);
  }
  const targets = [...byTicker.values()].slice(0, limit);
  // A benchmark is its own identity; there is no holding to derive a key from.
  targets.push(...BENCHMARKS.map((ticker) => ({ ticker, type: 'benchmark', key: ticker, earliestHeld: null })));

  let count = 0;
  for (const target of targets) {
    try {
      const from = target.earliestHeld
        ? new Date(Date.parse(target.earliestHeld) - 120 * DAY_MS).toISOString().slice(0, 10)
        : undefined;
      const series = await adjustedPrices(target.ticker, { from });
      // A ticker outlives its company - FB now serves an unrelated firm's
      // history. Writing that against an older holding would fabricate prices.
      const reassigned = coverageProblem({ symbol: target.ticker, earliestHeld: target.earliestHeld }, series.rows);
      if (reassigned) { console.warn(`[institutional-v3] prices ${target.ticker}: rejected - ${reassigned}`); continue; }
      const rows = series.rows.map((row) => ({ price_date: row.price_date, close: row.close, adjusted_close: row.adjusted_close, security_key: target.key, ticker: target.ticker, security_type: target.type, currency: series.currency, listing_status: series.listingStatus, source: 'Yahoo Finance chart', source_as_of: new Date().toISOString() }));
      await batches(client, 'institutional_security_prices', rows, 'security_key,price_date,source');
      count += rows.length;
    } catch (error) { console.warn(`[institutional-v3] prices ${target.ticker}: ${error.message}`); }
  }
  return count;
}

function archiveUrl(cik, row) {
  return `${SEC_ARCHIVES}/${String(cik).replace(/^0+/, '')}/${String(row.accession).replaceAll('-', '')}/${row.document}`;
}

async function collectExternalFilings(client, managers, holdings, companies, limit) {
  const output = [];
  for (const manager of managers.filter((row) => row.cik).slice(0, limit)) {
    try {
      const filings = recentFilings(await submission(manager.cik)).filter((row) => /^(SC 13D|SC 13G)/.test(row.form || '')).slice(0, 20);
      filings.forEach((row) => output.push({ accession_number: row.accession, manager_id: manager.id, filer_cik: String(manager.cik).padStart(10, '0'), form_type: row.form, event_type: row.form.startsWith('SC 13D') ? 'activist_ownership' : 'beneficial_ownership', filed_at: row.filedAt, report_date: row.reportDate, source_url: archiveUrl(manager.cik, row), parsed_data: { primary_document: row.document } }));
    } catch (error) { console.warn(`[institutional-v3] ownership scan ${manager.display_name}: ${error.message}`); }
  }
  for (const ticker of [...new Set(holdings.map(tickerOf).filter(Boolean))].slice(0, limit)) {
    const company = companies.get(ticker);
    if (!company) continue;
    try {
      const filings = recentFilings(await submission(company.cik)).filter((row) => /^4(\/A)?$/.test(row.form || '')).slice(0, 10);
      // Read, not just indexed. Storing the accession number alone records
      // that a filing happened and nothing about what it said - no shares, no
      // price, no insider, and no way to tell a discretionary purchase from
      // shares withheld to pay tax on a vesting grant.
      for (const row of filings) {
        // The index entry keeps the document EDGAR names; the parser is given
        // the raw XML, since primaryDocument points at the rendered HTML view.
        const url = archiveUrl(company.cik, row);
        const xmlUrl = archiveUrl(company.cik, { ...row, document: rawDocumentPath(row.document) });
        let parsed = null;
        try {
          const xml = await sourceText(xmlUrl);
          parsed = parseFormFour(xml);
        } catch (error) {
          // A document that will not parse is still a filing that happened.
          // Recording the index entry without it is better than dropping both.
          console.warn(`[institutional-v3] Form 4 parse ${ticker} ${row.accession}: ${error.message}`);
        }
        output.push({
          accession_number: row.accession,
          issuer_cik: company.cik,
          ticker,
          form_type: row.form,
          event_type: 'insider_transaction',
          filed_at: row.filedAt,
          report_date: row.reportDate,
          source_url: url,
          parsed_data: parsed
            ? { primary_document: row.document, ...parsed }
            : { primary_document: row.document, parse_status: 'unread' },
        });
      }
    } catch (error) { console.warn(`[institutional-v3] Form 4 scan ${ticker}: ${error.message}`); }
  }
  if (output.length) await batches(client, 'institutional_external_filings', output, 'accession_number');
  return output.length;
}

async function createBriefs(client, managers, filings, holdings) {
  const byManager = filingMap(filings);
  const byFiling = new Map();
  holdings.forEach((row) => { const rows = byFiling.get(row.filing_id) || []; rows.push(row); byFiling.set(row.filing_id, rows); });
  const output = [];
  managers.forEach((manager) => {
    const [latest, prior] = byManager.get(manager.id) || [];
    if (!latest) return;
    const current = byFiling.get(latest.id) || [];
    const previous = byFiling.get(prior?.id) || [];
    const priorMap = new Map(previous.map((row) => [keyOf(row), row]));
    const currentMap = new Map(current.map((row) => [keyOf(row), row]));
    const ranked = [...current].sort((a, b) => valueOf(b) - valueOf(a));
    const total = ranked.reduce((sum, row) => sum + valueOf(row), 0);
    const top10 = total ? ranked.slice(0, 10).reduce((sum, row) => sum + valueOf(row), 0) / total : 0;
    const added = ranked.filter((row) => !priorMap.has(keyOf(row)));
    const increased = ranked.filter((row) => priorMap.has(keyOf(row)) && sharesOf(row) > sharesOf(priorMap.get(keyOf(row))));
    const exited = previous.filter((row) => !currentMap.has(keyOf(row)));
    const largest = tickerOf(ranked[0]) || ranked[0]?.issuer_name || 'not available';
    output.push({ manager_id: manager.id, filing_id: latest.id, status: 'pending_review', headline: `${manager.display_name}: ${added.length} new positions and ${exited.length} exits`, summary: `${manager.display_name} reported ${current.length} long 13F positions for ${latest.report_date}. The top ten represented ${(top10 * 100).toFixed(1)}% of disclosed value. The filing shows ${added.length} new positions, ${increased.length} increases and ${exited.length} exits versus the prior comparable quarter. ${largest} was the largest disclosed position.`, key_points: [{ label: 'Top-ten concentration', value: top10 }, { label: 'New positions', value: added.length }, { label: 'Increases', value: increased.length }, { label: 'Exits', value: exited.length }], evidence: { filing_id: latest.id, accession_number: latest.accession_number, report_date: latest.report_date, accepted_at: latest.accepted_at || latest.filed_at, largest_holding: largest, generated_from: '13F holdings comparison' }, generated_at: new Date().toISOString() });
  });
  const { data: reviewed } = await client.from('institutional_intelligence_briefs').select('manager_id,filing_id,status').neq('status', 'pending_review');
  const locked = new Set((reviewed || []).map((row) => `${row.manager_id}:${row.filing_id}`));
  const write = output.filter((row) => !locked.has(`${row.manager_id}:${row.filing_id}`));
  if (write.length) await batches(client, 'institutional_intelligence_briefs', write, 'manager_id,filing_id');
  return write.length;
}

async function createAlerts(client) {
  const [{ data: lists }, { data: items }, { data: events }] = await Promise.all([
    client.from('institutional_watchlists').select('id,user_id'), client.from('institutional_watchlist_items').select('*'),
    client.from('institutional_external_filings').select('*').order('filed_at', { ascending: false }).limit(500),
  ]);
  const owner = new Map((lists || []).map((row) => [row.id, row.user_id]));
  const alerts = [];
  (items || []).forEach((item) => {
    const ticker = String(item.ticker || item.security_key || '').toUpperCase();
    (events || []).filter((event) => ticker && String(event.ticker || '').toUpperCase() === ticker).slice(0, 5).forEach((event) => alerts.push({ user_id: owner.get(item.watchlist_id), event_key: `${event.accession_number}:${ticker}`, title: `${event.form_type} filed for ${ticker}`, body: `${ticker} has a new ${event.event_type.replaceAll('_', ' ')} disclosure.`, severity: event.event_type === 'activist_ownership' ? 'important' : 'info', evidence: { source_url: event.source_url, filed_at: event.filed_at } }));
  });
  const valid = alerts.filter((row) => row.user_id);
  if (valid.length) await batches(client, 'institutional_personalized_alerts', valid, 'user_id,event_key');
  return valid.length;
}

export async function refreshInstitutionalResearchLayer({ classificationLimit = 60, priceLimit = 60, filingLimit = 50 } = {}) {
  const { client, managers, filings, holdings } = await core();
  const companies = await tickerMap();
  const classifications = await collectClassifications(client, holdings, companies, classificationLimit);
  const prices = await collectPrices(client, holdings, priceLimit);
  const external = await collectExternalFilings(client, managers, holdings, companies, filingLimit);
  const briefs = await createBriefs(client, managers, filings, holdings);
  const alerts = await createAlerts(client);
  return { status: 'complete', classifications, price_rows: prices, external_filings: external, briefs_created_or_refreshed: briefs, personalized_alerts: alerts, refreshed_at: new Date().toISOString() };
}

function sectorRotation(holdings, filings, classifications) {
  const classes = new Map();
  [...classifications].sort((a, b) => String(b.valid_from).localeCompare(String(a.valid_from))).forEach((row) => { if (!classes.has(row.security_key)) classes.set(row.security_key, row); });
  const current = new Set(); const previous = new Set();
  filingMap(filings).forEach((rows) => { if (rows[0]) current.add(rows[0].id); if (rows[1]) previous.add(rows[1].id); });
  const totals = { current: 0, previous: 0 }; const sectors = new Map();
  holdings.forEach((row) => {
    const side = current.has(row.filing_id) ? 'current' : previous.has(row.filing_id) ? 'previous' : null;
    if (!side) return;
    const value = valueOf(row); totals[side] += value;
    const sector = classes.get(keyOf(row))?.sector || 'Unclassified';
    const bucket = sectors.get(sector) || { sector, current: 0, previous: 0 }; bucket[side] += value; sectors.set(sector, bucket);
  });
  return [...sectors.values()].map((row) => ({ sector: row.sector, current_weight: totals.current ? row.current / totals.current : 0, previous_weight: totals.previous ? row.previous / totals.previous : 0, weight_change: (totals.current ? row.current / totals.current : 0) - (totals.previous ? row.previous / totals.previous : 0) })).sort((a, b) => b.weight_change - a.weight_change);
}

export async function getInstitutionalResearchLayer() {
  try {
    const { client, managers, filings, holdings } = await core();
    const [{ data: classifications, error: cError }, { data: events, error: eError }, { data: briefs, error: bError }, { data: backtests, error: tError }] = await Promise.all([
      client.from('institutional_security_classifications').select('*').order('valid_from', { ascending: false }).limit(5000),
      client.from('institutional_external_filings').select('*').order('filed_at', { ascending: false }).limit(100),
      client.from('institutional_intelligence_briefs').select('*, institutional_managers(display_name,slug)').in('status', ['approved', 'published']).order('generated_at', { ascending: false }).limit(30),
      client.from('institutional_backtest_runs').select('*, institutional_managers(display_name,slug)').order('generated_at', { ascending: false }).limit(30),
    ]);
    if (cError || eError || bError || tError) throw cError || eError || bError || tError;
    const history = filingMap(filings);
    // Sector rotation aggregates disclosed weights across quarters, so it
    // reads the same gate consensus does.
    const dataIntegrity = await getRepairStatus();
    return { status: 'ready', data_integrity: dataIntegrity, generated_at: new Date().toISOString(), readiness: { managers_tracked: managers.length, managers_with_12_quarters: [...history.values()].filter((rows) => rows.length >= 12).length, classifications: classifications?.length || 0, external_filings: events?.length || 0, approved_briefs: briefs?.length || 0, methodology: 'Entry is the first US trading session strictly after SEC acceptance, read in US Eastern. Positions without an adjusted close at both ends of a period are excluded and reported, never re-weighted. A position is priced from its adjusted closes, refreshed daily; a manager whose book cannot be priced in full is reported with its coverage rather than ranked on part of it.' }, sector_rotation: sectorRotation(holdings, filings, classifications || []), filing_events: events || [], approved_briefs: briefs || [], backtests: backtests || [], managers: managers.map(({ id, slug, display_name }) => ({ id, slug, display_name })) };
  } catch (error) {
    if (/institutional_(security_classifications|external_filings|intelligence_briefs|backtest_runs)/i.test(error.message || '')) return { status: 'setup_required', message: 'Apply the Institutional Intelligence V3 database migration, then run the first research refresh.' };
    throw error;
  }
}

// The previous price lookup and period-return helper lived here. They matched
// prices with `price_date >= date`, which selected the acceptance day's own
// close, and divided the result by coverage, which re-weighted the priced
// survivors to 100%. Both are replaced by pointInTime.js. Deleted rather than
// left unused, so neither can be called again by accident.

/**
 * Everything one backtest needs, and nothing else.
 *
 * This used to call core(), which loads every manager's filings and holdings
 * and then throws away all but one. That was wasteful at nine hundred thousand
 * holdings rows and wrong at 2.6 million, because core() truncates twice
 * without saying so: it caps filings at a thousand when there are now about
 * eighteen hundred active, and its holdings read is unpaged, so PostgREST's
 * thousand-row ceiling returns a thousand rows per batch of a hundred filings
 * instead of the hundred and thirty thousand they hold.
 *
 * Neither truncation errors. The backtest would have run on a slice of one
 * manager's book and reported a return for it.
 *
 * Loading per manager is bounded by construction - one fund's filings, and the
 * holdings that belong to them - so it stays correct however large the table
 * gets.
 */
async function backtestInputs(client, managerSlug, quarters) {
  const { data: managerRows, error: managerError } = await client
    .from('institutional_managers').select('*')
    .or(`slug.eq.${managerSlug},id.eq.${managerSlug}`).limit(1);
  if (managerError) throw managerError;
  const manager = managerRows?.[0];
  if (!manager) throw new Error('Tracked manager not found.');

  const { data: filings, error: filingError } = await client
    .from('institutional_filings').select('*')
    .eq('manager_id', manager.id).eq('is_active', true)
    .order('report_date', { ascending: false });
  if (filingError) throw filingError;

  // Ordered by when the market learned of each filing, not by the quarter it
  // covers. A 13F-HR/A for an older quarter is accepted after later quarters'
  // originals, so report_date order produced periods whose exit preceded their
  // entry - a negative holding period, compounded without complaint.
  const chosen = orderByAcceptance(filings || []).slice(-quarters);

  const holdings = [];
  for (const filing of chosen) {
    // Paged. One filing can hold five thousand positions - BlackRock reports
    // about 5,700 - and an unpaged read returns the first thousand of them,
    // which is a different portfolio with a plausible-looking return.
    for (let from = 0; ; from += 1000) {
      const { data, error } = await client.from('institutional_holdings')
        .select('*').eq('filing_id', filing.id).range(from, from + 999);
      if (error) throw error;
      holdings.push(...(data || []));
      if (!data || data.length < 1000) break;
      if (holdings.length > 500_000) throw new Error('refusing to page past 500k holdings for one backtest');
    }
  }
  return { manager, filings: chosen, holdings };
}

export async function runInstitutionalBacktest({
  managerSlug, topN = 10, transactionCostBps = 10, quarters = 12,
} = {}) {
  if (!managerSlug) throw new Error('Choose a manager to run the backtest.');
  // Bounded at both ends. Fewer than two periods cannot produce a holding
  // period at all, and the ceiling is the depth of the price history rather
  // than of the filings - a quarter whose positions cannot be priced is
  // excluded and reported, so asking for more than the prices cover buys a
  // longer list of exclusions and no more test.
  const depth = Math.max(2, Math.min(Number(quarters) || 12, 48));
  const client = db();
  const { manager, filings: managerFilings, holdings: managerHoldings } =
    await backtestInputs(client, managerSlug, depth);
  const targets = [...new Set([...managerHoldings.map(tickerOf).filter(Boolean), ...BENCHMARKS])];
  const prices = new Map();
  for (let index = 0; index < targets.length; index += 100) {
    // Matched on ticker, not on security_key. This asked for security_key
    // while passing tickers, which worked only because collectPrices wrote
    // the ticker into that column. The backfill writes the canonical
    // CUSIP-derived key there, as every other table means it, so the old
    // query would have matched none of its rows - the backtester would have
    // run on the handful of legacy symbols and silently ignored the rest.
    const { data, error } = await client.from('institutional_security_prices').select('ticker,price_date,adjusted_close').in('ticker', targets.slice(index, index + 100)).order('price_date');
    if (error) throw error;
    (data || []).forEach((row) => { const rows = prices.get(row.ticker) || []; rows.push(row); prices.set(row.ticker, rows); });
  }

  // The trading calendar, derived from the benchmark's own price history rather
  // than a hardcoded holiday table. It is the one series expected to have a
  // print on every session, so it defines what "next tradable session" means -
  // correct for every year, including half-days and unscheduled closures, with
  // no list to maintain.
  const sessions = sessionsFromPrices(prices.get(BENCHMARKS[0]) || []);

  const byFiling = new Map(); managerHoldings.forEach((row) => { const rows = byFiling.get(row.filing_id) || []; rows.push(row); byFiling.set(row.filing_id, rows); });
  const periods = [];
  const skipped = [];
  const limit = Math.max(1, Math.min(50, number(topN) || 10));

  for (let index = 0; index < managerFilings.length - 1; index += 1) {
    const filing = managerFilings[index]; const next = managerFilings[index + 1];

    // Entry is the first session strictly after public acceptance, read in US
    // Eastern. The previous code truncated the acceptance instant in UTC and
    // matched prices with '>=', so it entered at the acceptance day's own
    // close - a price struck before the filing was public.
    const entry = firstTradableSession(filing.accepted_at || filing.filed_at, sessions);
    const exit = firstTradableSession(next.accepted_at || next.filed_at, sessions);
    if (!entry || !exit) {
      skipped.push({ report_date: filing.report_date, reason: 'no tradable session after acceptance within the price history' });
      continue;
    }
    if (!(exit > entry)) {
      skipped.push({ report_date: filing.report_date, reason: `exit ${exit} does not follow entry ${entry}` });
      continue;
    }

    const positions = [...(byFiling.get(filing.id) || [])]
      .filter((row) => tickerOf(row) && !row.put_call)
      .sort((a, b) => valueOf(b) - valueOf(a))
      .slice(0, limit);

    const portfolio = pitPeriodReturn({
      positions, prices, entryDate: entry, exitDate: exit,
      weightOf: valueOf, keyOf: tickerOf,
    });
    if (portfolio.value == null) {
      skipped.push({ report_date: filing.report_date, reason: 'no position in the period could be priced' });
      continue;
    }

    // A benchmark that was never measured must invalidate the comparison rather
    // than win it. Previously a missing series compounded to 0%, so the whole
    // strategy return was reported as excess over a benchmark that did not exist.
    const spy = benchmarkReturn(prices.get('SPY') || [], entry, exit);
    const qqq = benchmarkReturn(prices.get('QQQ') || [], entry, exit);

    periods.push({
      report_date: filing.report_date,
      known_at: filing.accepted_at || filing.filed_at,
      entry_date: entry,
      exit_date: exit,
      gross_return: portfolio.value,
      net_return: portfolio.value - number(transactionCostBps) / 10_000,
      spy_return: spy,
      qqq_return: qqq,
      price_coverage: portfolio.coverage,
      positions_priced: portfolio.priced,
      positions_excluded: portfolio.excluded,
    });
  }

  // Judged on the worst period, not the mean.
  //
  // A compounded return multiplies every period, so a single quarter at half
  // coverage carries its gap through every period after it. Twenty quarters at
  // 99% and one at 50% average to 96.7%, which cleared the old floor while
  // half of one quarter's book was assumed flat.
  //
  // The floor now matches the screener's. Both answer whether a manager's
  // performance can be stated, and two surfaces answering that at different
  // bars is how one of them ends up wrong.
  const profile = coverageProfile(periods);
  const coverage = profile.average;
  const benchmarkComplete = periods.length > 0 && periods.every((row) => row.spy_return != null);

  const blockers = backtestBlockers(profile, { periods: periods.length, benchmarkComplete, skipped });
  const status = blockers.length ? 'not_calculable' : 'calculated';
  // Every reason, not the first. An operator fixing one only to meet the next
  // learns the state one round trip at a time.
  const notCalculableReason = blockers.length ? blockers.join(' ') : null;

  const compound = (key) => periods.reduce((value, row) => row[key] == null ? value : value * (1 + row[key]), 1) - 1;
  const metrics = status === 'calculated'
    ? { total_return: compound('net_return'), spy_return: compound('spy_return'), qqq_return: compound('qqq_return'), excess_vs_spy: compound('net_return') - compound('spy_return'), periods: periods.length, average_coverage: coverage, worst_period_coverage: profile.worst, worst_coverage_period: profile.worstPeriod }
    : { reason: notCalculableReason, blockers, periods: periods.length, average_coverage: coverage, worst_period_coverage: profile.worst, worst_coverage_period: profile.worstPeriod, skipped };

  const strategyKey = `top_${topN}_${crypto.createHash('sha1').update(String(transactionCostBps)).digest('hex').slice(0, 6)}`;
  const payload = {
    manager_id: manager.id,
    as_of_date: dateOnly(new Date()),
    strategy_key: strategyKey,
    status,
    methodology: 'Entry is the first US trading session strictly after the SEC acceptance timestamp, read in US Eastern; the session calendar is derived from observed benchmark prices. Positions without an exact adjusted close at both ends are excluded and reported rather than re-weighted. A period whose benchmark cannot be priced makes the run not calculable.',
    periods,
    metrics,
    evidence: { periods, skipped, average_coverage: coverage, benchmark_complete: benchmarkComplete },
    generated_at: new Date().toISOString(),
  };
  const { data, error } = await client.from('institutional_backtest_runs').upsert(payload, { onConflict: 'manager_id,as_of_date,strategy_key' }).select().single();
  if (error) throw error;
  return { ...data, manager: { display_name: manager.display_name, slug: manager.slug } };
}

export async function getInstitutionalWorkspace(userId) {
  const client = db();
  const [{ data: groups, error: gError }, { data: watchlists, error: wError }, { data: alerts, error: aError }] = await Promise.all([
    client.from('institutional_manager_groups').select('*, institutional_manager_group_members(*, institutional_managers(id,slug,display_name))').eq('user_id', userId).order('created_at'),
    client.from('institutional_watchlists').select('*, institutional_watchlist_items(*)').eq('user_id', userId).order('created_at'),
    client.from('institutional_personalized_alerts').select('*').eq('user_id', userId).order('created_at', { ascending: false }).limit(100),
  ]);
  if (gError || wError || aError) throw gError || wError || aError;
  return { groups: groups || [], watchlists: watchlists || [], alerts: alerts || [] };
}

export async function createInstitutionalGroup(userId, { name, managerIds = [] }) {
  if (!String(name || '').trim()) throw new Error('Group name is required.');
  const client = db();
  const { data: group, error } = await client.from('institutional_manager_groups').insert({ user_id: userId, name: String(name).trim() }).select().single();
  if (error) throw error;
  if (managerIds.length) { const { error: memberError } = await client.from('institutional_manager_group_members').insert([...new Set(managerIds)].map((managerId) => ({ group_id: group.id, manager_id: managerId }))); if (memberError) throw memberError; }
  return group;
}

export async function createInstitutionalWatchlist(userId, { name, items = [] }) {
  if (!String(name || '').trim()) throw new Error('Watchlist name is required.');
  const client = db();
  const { data: list, error } = await client.from('institutional_watchlists').insert({ user_id: userId, name: String(name).trim() }).select().single();
  if (error) throw error;
  const normalized = items.map((item) => typeof item === 'string' ? { security_key: item.toUpperCase(), ticker: item.toUpperCase() } : item).filter((item) => item.security_key || item.ticker);
  if (normalized.length) { const { error: itemError } = await client.from('institutional_watchlist_items').insert(normalized.map((item) => ({ watchlist_id: list.id, security_key: String(item.security_key || item.ticker).toUpperCase(), ticker: item.ticker ? String(item.ticker).toUpperCase() : null, issuer_name: item.issuer_name || null }))); if (itemError) throw itemError; }
  return list;
}

export async function markPersonalizedAlert(userId, alertId, isRead = true) {
  const client = db(); const { data, error } = await client.from('institutional_personalized_alerts').update({ is_read: isRead }).eq('id', alertId).eq('user_id', userId).select().single(); if (error) throw error; return data;
}

export async function getInstitutionalResearchAdmin() {
  const client = db();
  const [{ data: briefs, error: briefError }, { count: classifications, error: classError }, { count: prices, error: priceError }, { count: events, error: eventError }] = await Promise.all([
    client.from('institutional_intelligence_briefs').select('*, institutional_managers(display_name,slug), institutional_filings(report_date,accepted_at,accession_number)').order('generated_at', { ascending: false }).limit(100),
    client.from('institutional_security_classifications').select('*', { count: 'exact', head: true }), client.from('institutional_security_prices').select('*', { count: 'exact', head: true }), client.from('institutional_external_filings').select('*', { count: 'exact', head: true }),
  ]);
  if (briefError || classError || priceError || eventError) throw briefError || classError || priceError || eventError;
  return { briefs: briefs || [], coverage: { classifications: classifications || 0, price_rows: prices || 0, external_filings: events || 0 } };
}

export async function reviewInstitutionalBrief(id, { status, reviewerNotes, reviewer }) {
  if (!['approved', 'rejected', 'published', 'pending_review'].includes(status)) throw new Error('Invalid review status.');
  const client = db(); const { data, error } = await client.from('institutional_intelligence_briefs').update({ status, reviewer_notes: reviewerNotes || null, reviewed_by: reviewer || 'admin', reviewed_at: new Date().toISOString() }).eq('id', id).select().single(); if (error) throw error; return data;
}

// Opt-in, not opt-out.
//
// This used to default to on, so every deploy of the web process started an
// unthrottled SEC crawl 15 seconds later: 51 managers x 12 quarters of EDGAR
// requests from a dyno whose job is serving clients, with no rate limiter and
// no coordination between instances. Restart the service three times and three
// crawls run at once, against an endpoint whose Fair Access policy is 10
// requests a second and whose penalty is an IP block.
//
// Collection belongs in a scheduled worker with a real limiter. Until that
// exists, this runs only where someone has deliberately set the flag.
export function startInstitutionalResearchLayerAutomation() {
  if (automationStarted || process.env.NODE_ENV === 'test' || String(process.env.INSTITUTIONAL_RESEARCH_AUTOMATION_ENABLED || 'false').toLowerCase() !== 'true') return;
  automationStarted = true;
  const execute = () => refreshInstitutionalResearchLayer().catch((error) => console.error('[institutional-v3] automatic refresh failed:', error.message));
  const initial = setTimeout(execute, Math.max(60_000, number(process.env.INSTITUTIONAL_RESEARCH_INITIAL_DELAY_MS) || 7 * 60_000));
  const recurring = setInterval(execute, Math.max(6 * 60 * 60_000, number(process.env.INSTITUTIONAL_RESEARCH_INTERVAL_MS) || 24 * 60 * 60_000));
  initial.unref?.(); recurring.unref?.();
}
