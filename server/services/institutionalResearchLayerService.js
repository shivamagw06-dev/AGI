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
import { classifySic } from './sicSectors.js';
import { classificationQueue } from './classificationQueue.js';
import { restatements, restated } from './sectorRestatement.js';
import { securityCandidates, partitionByIdentifiability } from './securityCandidates.js';
import { issuerDirectory, FUND_SECTOR, FUND_INDUSTRY } from './issuerDirectory.js';
import { filesAsFund } from './fundEvidence.js';
import { sectorByIssuer, sectorFromIssuer, checkDigitValid } from './cusipIssuer.js';
import { nameIndex, matchByName } from './issuerNameMatch.js';
import { resolveRegistrants } from './registrantNames.js';
import { namesByTicker, windowOverlaps } from './issuerTickerRegistry.js';

const SEC_DATA = 'https://data.sec.gov';
const SEC_ARCHIVES = 'https://www.sec.gov/Archives/edgar/data';
// Every registrant the SEC has assigned a CIK, name and number, one per line.
const SEC_CIK_LOOKUP = 'https://www.sec.gov/Archives/edgar/cik-lookup-data.txt';
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


/**
 * Every ticker the SEC publishes, across all three of its lists.
 *
 * company_tickers.json alone is operating companies, which is why the funds
 * that make up most of a large book's unclassified value were skipped in
 * silence. The exchange file is fetched because it is the only one of the
 * three that carries SPY, and the fund file because it carries the other
 * twenty-eight thousand.
 */
export async function secDirectory() {
  const [companies, exchange, funds] = await Promise.all([
    sourceJson('https://www.sec.gov/files/company_tickers.json'),
    // Neither of these is essential: without them the classifier falls back to
    // what it could already do, which is worse but not broken.
    sourceJson('https://www.sec.gov/files/company_tickers_exchange.json').catch((error) => {
      console.warn(`[institutional-v3] exchange ticker file: ${error.message}`);
      return null;
    }),
    sourceJson('https://www.sec.gov/files/company_tickers_mf.json').catch((error) => {
      console.warn(`[institutional-v3] fund ticker file: ${error.message}`);
      return null;
    }),
  ]);
  return issuerDirectory({ companies, exchange, funds });
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

/**
 * Page a query past PostgREST's thousand-row ceiling.
 *
 * The ceiling is silent: a query that would return five thousand rows returns
 * a thousand and reports success. Every read in this file that could exceed it
 * has to page, and every paged read needs a total order or rows move between
 * pages - some read twice, others not at all.
 */
export async function paged(build, { pageSize = 1000, maxRows = 200_000, label = 'query' } = {}) {
  const rows = [];
  for (let from = 0; from < maxRows; from += pageSize) {
    const { data, error } = await build().range(from, from + pageSize - 1);
    if (error) throw error;
    rows.push(...(data || []));
    if (!data || data.length < pageSize) return rows;
  }
  // Loudly, because the whole point of this helper is that a short answer must
  // not be able to pass for a complete one.
  throw new Error(`${label} exceeded its ${maxRows}-row ceiling; the result would have been incomplete`);
}

/**
 * The shared read behind the research layer.
 *
 * It used to truncate twice and say nothing. Filings were capped at a thousand
 * when about eighteen hundred are active, and they are ordered newest first -
 * so `managers_with_12_quarters` counted against a history missing its oldest
 * eight hundred filings. The holdings read was unpaged, so PostgREST returned a
 * thousand rows per batch of a hundred filings instead of the hundred and
 * thirty thousand they hold, and sector rotation was computed from roughly one
 * per cent of the book.
 *
 * The two are fixed differently, because they are needed differently.
 *
 * Filings are paged in full: the readiness count is about how deep each
 * manager's history is, and it cannot be answered from a truncated list.
 *
 * Holdings are loaded only for the filings something actually reads - the
 * newest few per manager. Sector rotation compares the current quarter with
 * the previous one and iterates past everything else; the briefs and the
 * classification, price and external-filing collectors all work from the most
 * recent book. Loading all 2.6M rows to use a hundred and thirty thousand of
 * them was not merely wasteful, it is more than this instance has memory for.
 */
export async function core({ quartersPerManager = 2, withHoldings = true } = {}) {
  const client = db();
  const [managers, filings] = await Promise.all([
    paged(() => client.from('institutional_managers').select('*').order('display_name'), { label: 'managers' }),
    // is_active, deliberately.
    //
    // A superseded filing keeps its row: when an amendment restates a quarter,
    // the earlier version is marked inactive rather than deleted, so the record
    // of what was originally disclosed survives. Loading every filing therefore
    // loaded both versions of the same quarter and counted the restated
    // positions twice - once from the report the manager withdrew.
    //
    // Ordered on report_date and then id, because paging needs a total order
    // and report dates repeat across fifty managers.
    paged(() => client.from('institutional_filings').select('*').eq('is_active', true)
      .order('report_date', { ascending: false }).order('id'), { label: 'filings' }),
  ]);

  const wanted = [];
  filingMap(filings).forEach((rows) => { wanted.push(...rows.slice(0, Math.max(1, quartersPerManager))); });
  const ids = wanted.map((row) => row.id);

  const holdings = [];
  // Skipped where the caller does not need them. Reading the newest two
  // filings of fifty managers is about a hundred and thirty thousand rows and
  // a hundred and thirty sequential requests - fifty seconds, measured, on a
  // page load. The refresh job needs them and can wait; the page does not.
  for (const id of (withHoldings ? ids : [])) {
    // One filing at a time, paged. A single filing can hold five thousand
    // positions - BlackRock reports about 5,700 - so even one exceeds the
    // ceiling, and batching a hundred of them into one `in` made that certain.
    holdings.push(...await paged(
      () => client.from('institutional_holdings').select('*').eq('filing_id', id).order('id'),
      { maxRows: 50_000, label: `holdings for filing ${id}` },
    ));
  }
  return { client, managers, filings, holdings };
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

/**
 * Re-derive stored sectors from stored SIC codes, where they disagree with
 * the current map. A no-op on a table that already agrees.
 */
async function restateStoredSectors(client) {
  const rows = await paged(
    () => client.from('institutional_security_classifications').select('*').order('security_key').order('valid_from'),
    { label: 'classifications to restate' },
  );
  const changes = restatements(rows, classifySic);
  if (!changes.length) return 0;
  await batches(client, 'institutional_security_classifications', changes.map(restated), 'security_key,valid_from,source');
  console.log(`[institutional-v3] ${changes.length} stored sector(s) restated against the current map`);
  return changes.length;
}

export async function collectClassifications(client, holdings, directory, limit) {
  // Every ticker each security has been filed under, largest security first.
  // The code this replaces kept one holding per security and let the last one
  // win, so a single filer's mangled symbol decided the identity of the whole
  // position - EXMOC for CUSIP 30231G102, which is Exxon Mobil, and $144.9bn
  // unclassified because of it.
  const all = securityCandidates(holdings);
  // Only those something could identify. Every lookup here is keyed on the
  // symbol, and a 13F reports a CUSIP with the ticker optional - about eight
  // thousand securities arrive without one. Queued anyway they would occupy
  // the largest-first slots for ever and the nightly job would classify
  // nothing, which is the stall the queue itself was written to fix.
  const { identifiable: distinct, unidentifiable } = partitionByIdentifiability(all);
  const classified = await paged(
    () => client.from('institutional_security_classifications').select('security_key,sector,source_as_of').order('security_key').order('source_as_of'),
    { label: 'existing classifications' },
  );
  const securities = classificationQueue({
    securities: distinct.map((row) => ({ key: row.key, row })),
    classified, limit,
  }).map((entry) => entry.row);
  await restateStoredSectors(client);

  // The historical registry, for tickers no current SEC list still carries.
  // Electronic Arts and the other names that have left company_tickers.json
  // since they were acquired are here and nowhere else.
  const registry = namesByTicker(await paged(
    () => client.from('sec_issuer_tickers').select('ticker,cik,issuer_name,first_seen,last_seen').order('ticker').order('cik'),
    { label: 'issuer ticker registry' },
  ).catch((error) => {
    console.warn(`[institutional-v3] issuer registry unavailable: ${error.message}`);
    return [];
  }));

  const blindValue = unidentifiable.reduce((sum, row) => sum + row.value_usd, 0);
  console.log(`[institutional-v3] ${all.length} securities, ${distinct.length} with a ticker, ${classified.length} classified, ${securities.length} queued`);
  if (unidentifiable.length) {
    // Reported, not hidden. Nothing available here can name a security filed
    // without a symbol, and a chart that silently omits them is worse than one
    // that says how much it cannot see.
    console.log(`[institutional-v3] ${unidentifiable.length} securities filed without a ticker, $${(blindValue / 1e9).toFixed(1)}bn, cannot be identified by symbol`);
  }

  const output = [];
  const unresolved = [];
  for (const security of securities) {
    const found = resolveIssuer(security, directory, registry);
    if (!found) { unresolved.push(security); continue; }

    const validFrom = dateOnly(security.latest) || dateOnly(new Date());
    const base = {
      security_key: security.key, cusip: security.cusip, ticker: found.ticker,
      issuer_name: security.issuer_name || found.title, issuer_cik: found.cik,
      valid_from: validFrom, source_as_of: new Date().toISOString(), updated_at: new Date().toISOString(),
    };

    // A fund needs no SIC lookup. Its own filings would say 6726, investment
    // offices, which this map reads as Financials - and calling an S&P 500
    // index fund a financials position is confidently wrong, which is worse
    // than leaving it unclassified. It also saves a request per fund.
    if (found.kind === 'fund') {
      output.push({ ...base, sic_code: null, sector: FUND_SECTOR, industry: FUND_INDUSTRY, source: 'SEC fund tickers', source_url: 'https://www.sec.gov/files/company_tickers_mf.json', confidence: 0.95 });
      continue;
    }

    try {
      output.push({ ...base, ...await sectorForCik(found.cik, found.kind), source: found.source });
    } catch (error) { console.warn(`[institutional-v3] classification ${found.ticker}: ${error.message}`); }
  }

  if (unresolved.length) {
    // Named rather than counted. A security nothing can identify is a gap in
    // the chart, and the largest of them are worth someone looking at.
    const worst = unresolved.slice(0, 5).map((s) => `${s.tickers[0] || s.key} (${s.issuer_name || 'unnamed'})`).join(', ');
    console.log(`[institutional-v3] ${unresolved.length} securities whose ticker named nothing, passed to the issuer and name tiers; largest: ${worst}`);
  }
  if (output.length) await batches(client, 'institutional_security_classifications', output, 'security_key,valid_from,source');

  // Securities whose ticker named nothing join the tickerless pipeline. EXMOC
  // is not a symbol any SEC list carries, but the holding says EXXON MOBIL
  // CORP and the name tier resolves that without difficulty - and $144.9bn was
  // sitting outside every sector because a failed symbol lookup was the end of
  // the road rather than the start of the next tier.
  const inferred = await classifyTickerless(client, [...unidentifiable, ...unresolved], directory, output);
  return output.length + inferred;
}

/**
 * Securities filed with a CUSIP and no ticker.
 *
 * Two tiers, in order of how much they can be trusted.
 *
 * The issuer first. A CUSIP is six characters of issuer and two of issue, so
 * an option on Apple - which filers write as 037833950 against Apple's real
 * 037833100, and which fails its own check digit - is still Apple. Where every
 * classified security of an issuer agrees on a sector, its unclassified issues
 * take it. Where they disagree, nothing is written.
 *
 * Then the name, which is the only tier here that could invent an answer and
 * is built to refuse: an exact match on every word, against exactly one
 * company. See issuerNameMatch for why the looser comparison used elsewhere is
 * unsafe without a symbol to corroborate it.
 *
 * Both write a source of their own, so an inferred sector can always be told
 * from one the SEC stated.
 */
async function classifyTickerless(client, securities, directory, justWritten = []) {
  if (!securities?.length) return 0;

  const stored = await paged(
    () => client.from('institutional_security_classifications').select('security_key,cusip,sector').order('security_key'),
    { label: 'classifications for issuer inference' },
  );
  const byIssuer = sectorByIssuer([...stored, ...justWritten]);
  const byName = nameIndex(directory);

  const output = [];
  const tally = { issuer: 0, name: 0, registrant: 0, refused: 0, derivative: 0 };
  const refused = [];
  for (const security of securities) {
    if (!checkDigitValid(security.key)) tally.derivative += 1;
    const validFrom = dateOnly(security.latest) || dateOnly(new Date());
    const base = {
      security_key: security.key, cusip: security.cusip, ticker: null,
      issuer_name: security.issuer_name, valid_from: validFrom,
      source_as_of: new Date().toISOString(), updated_at: new Date().toISOString(), sic_code: null,
    };

    const fromIssuer = sectorFromIssuer(security.key, byIssuer);
    if (fromIssuer) {
      tally.issuer += 1;
      output.push({ ...base, sector: fromIssuer, industry: 'Inferred from issuer', source: 'CUSIP issuer', source_url: null, confidence: 0.8 });
      continue;
    }

    const match = security.issuer_name ? matchByName(security.issuer_name, byName) : null;
    if (match) {
      try {
        // A name match yields a CIK, which is the thing that classifies. It
        // goes through the same lookup the ticker path uses; confidence is
        // lower because the name, not a symbol, is what identified it.
        const found = await sectorForCik(match.cik, match.kind);
        tally.name += 1;
        output.push({ ...base, ticker: match.ticker, issuer_cik: match.cik, ...found, confidence: Math.min(found.confidence, 0.75), source: 'SEC issuer name' });
        continue;
      } catch (error) { console.warn(`[institutional-v3] name match ${security.issuer_name}: ${error.message}`); }
    }
    refused.push(security);
  }

  // Last tier, and the only one that costs a forty-megabyte fetch, so it runs
  // once over everything the cheaper tiers refused rather than per security.
  // These are mostly fund trusts - TIDAL TRUST II, DIREXION SHARES ETF TRUST -
  // which have no ticker because the trust issues dozens of ETFs and the trust
  // is what the filer names.
  const byRegistrant = await registrantMatches(refused.map((s) => s.issuer_name).filter(Boolean))
    .catch((error) => { console.warn(`[institutional-v3] registrant list: ${error.message}`); return new Map(); });
  for (const security of refused) {
    const match = byRegistrant.get(security.issuer_name);
    if (!match) { tally.refused += 1; continue; }
    try {
      const found = await sectorForCik(match.cik, null);
      tally.registrant += 1;
      output.push({
        security_key: security.key, cusip: security.cusip, ticker: null,
        issuer_name: security.issuer_name, issuer_cik: match.cik,
        valid_from: dateOnly(security.latest) || dateOnly(new Date()),
        source_as_of: new Date().toISOString(), updated_at: new Date().toISOString(),
        ...found, confidence: Math.min(found.confidence, 0.7), source: 'SEC registrant name',
      });
    } catch (error) { console.warn(`[institutional-v3] registrant ${security.issuer_name}: ${error.message}`); tally.refused += 1; }
  }

  console.log(`[institutional-v3] tickerless: ${tally.issuer} by issuer, ${tally.name} by name, ${tally.registrant} by registrant, ${tally.refused} refused (${tally.derivative} carry an invalid check digit, so are filers' own option identifiers)`);
  if (output.length) await batches(client, 'institutional_security_classifications', output, 'security_key,valid_from,source');
  return output.length;
}

/**
 * Resolve issuer names against every registrant the SEC has assigned a CIK.
 *
 * Forty megabytes and a million lines, so it is streamed against the names
 * actually being asked about rather than indexed into memory - and fetched
 * only when there are names left that nothing cheaper could identify.
 */
async function registrantMatches(names) {
  if (!names.length) return new Map();
  const response = await scheduleSecRequest(() => fetch(SEC_CIK_LOOKUP, {
    headers: { 'User-Agent': process.env.SEC_USER_AGENT || 'Agarwal Global Investments research@agarwalglobalinvestments.com' },
    signal: AbortSignal.timeout(120_000),
  }));
  if (!response.ok) throw new Error(`cik-lookup-data.txt: HTTP ${response.status}`);
  // latin1: the file is not UTF-8 and a mis-decoded byte would corrupt the
  // name it appears in rather than failing loudly.
  const text = Buffer.from(await response.arrayBuffer()).toString('latin1');
  return resolveRegistrants(names, text.split('\n'));
}

/**
 * The sector a CIK implies, from the SEC's own record of it.
 *
 * One place, so the ticker path and the name-match path cannot drift into
 * classifying the same registrant differently.
 *
 * A trust gets no SIC code from EDGAR - SPY, QQQ and Vanguard Index Funds all
 * report an empty one - so the map correctly refuses to guess and returns
 * Unclassified. The forms it files say what the missing code would have, and
 * they are already in this payload.
 */
async function sectorForCik(cik, kind) {
  const url = `${SEC_DATA}/submissions/CIK${cik}.json`;
  // Known to be a fund from the SEC's own fund list; nothing a SIC lookup
  // could add, and one request saved per fund.
  if (kind === 'fund') return { sic_code: null, sector: FUND_SECTOR, industry: FUND_INDUSTRY, source_url: url, confidence: 0.95 };

  const sec = await submission(cik);
  const sic = String(sec.sic || '').trim();
  if (!sic && filesAsFund(sec)) return { sic_code: null, sector: FUND_SECTOR, industry: FUND_INDUSTRY, source_url: url, confidence: 0.9 };
  return { sic_code: sic, ...classifySic(sic, sec.sicDescription), source_url: url, confidence: sic ? 0.95 : 0.5 };
}

/**
 * Who a security belongs to, trying each ticker it has been filed under.
 *
 * The SEC's own lists first, in the order they are authoritative, then the
 * historical registry for names that have left them - acquired companies are
 * dropped from company_tickers.json but are still held at the quarter end
 * they were acquired in.
 *
 * The registry is only consulted where a ticker matches exactly one issuer
 * whose window overlaps the holding. A ticker that has belonged to two
 * companies cannot be resolved by symbol alone, and guessing would attribute
 * one company's position to another.
 */
export function resolveIssuer(security, directory, registry) {
  for (const ticker of security.tickers || []) {
    const live = directory?.get(ticker);
    if (live?.cik) return { ...live, ticker, source: live.kind === 'fund' ? 'SEC fund tickers' : 'SEC submissions' };
  }
  for (const ticker of security.tickers || []) {
    const entries = (registry?.get(ticker) || []).filter((entry) => windowOverlaps(entry, { earliest: security.earliest, latest: security.latest }));
    if (entries.length !== 1) continue;
    const [entry] = entries;
    return { cik: String(entry.cik || '').padStart(10, '0'), title: entry.issuer_name, kind: 'company', ticker, source: 'SEC issuer registry' };
  }
  return null;
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

async function collectExternalFilings(client, managers, holdings, directory, limit) {
  const output = [];
  for (const manager of managers.filter((row) => row.cik).slice(0, limit)) {
    try {
      const filings = recentFilings(await submission(manager.cik)).filter((row) => /^(SC 13D|SC 13G)/.test(row.form || '')).slice(0, 20);
      filings.forEach((row) => output.push({ accession_number: row.accession, manager_id: manager.id, filer_cik: String(manager.cik).padStart(10, '0'), form_type: row.form, event_type: row.form.startsWith('SC 13D') ? 'activist_ownership' : 'beneficial_ownership', filed_at: row.filedAt, report_date: row.reportDate, source_url: archiveUrl(manager.cik, row), parsed_data: { primary_document: row.document } }));
    } catch (error) { console.warn(`[institutional-v3] ownership scan ${manager.display_name}: ${error.message}`); }
  }
  for (const ticker of [...new Set(holdings.map(tickerOf).filter(Boolean))].slice(0, limit)) {
    const company = directory.get(ticker);
    // Funds are skipped: this scans for Form 4s, and a trust has no insiders
    // filing them. Before the directory carried funds at all they were skipped
    // by accident, through not being found; now it is deliberate.
    if (!company || company.kind === 'fund') continue;
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
  const directory = await secDirectory();
  const classifications = await collectClassifications(client, holdings, directory, classificationLimit);
  const prices = await collectPrices(client, holdings, priceLimit);
  const external = await collectExternalFilings(client, managers, holdings, directory, filingLimit);
  const briefs = await createBriefs(client, managers, filings, holdings);
  const alerts = await createAlerts(client);
  return { status: 'complete', classifications, price_rows: prices, external_filings: external, briefs_created_or_refreshed: briefs, personalized_alerts: alerts, refreshed_at: new Date().toISOString() };
}

export async function getInstitutionalResearchLayer() {
  try {
    // Without holdings. The only thing the page did with them was sector
    // rotation, and that now comes back from the database as the dozen rows it
    // always was rather than the hundred and thirty thousand it was computed
    // from.
    const { client, managers, filings } = await core({ withHoldings: false });
    const [{ data: rotation, error: rError }, { count: classificationCount, error: cError }, { data: events, error: eError }, { count: externalCount, error: xError }, { data: briefs, error: bError }, { data: backtests, error: tError }] = await Promise.all([
      client.rpc('institutional_sector_rotation'),
      client.from('institutional_security_classifications').select('id', { count: 'exact', head: true }),
      // Six columns, not *. The row carries a parsed_data jsonb holding the
      // whole parsed disclosure, and this page reads none of it - it renders a
      // form type, a ticker, an event type and a date, and only the newest
      // twenty of them.
      client.from('institutional_external_filings')
        .select('id,source_url,form_type,event_type,ticker,filed_at')
        .order('filed_at', { ascending: false }).limit(100),
      client.from('institutional_external_filings').select('id', { count: 'exact', head: true }),
      client.from('institutional_intelligence_briefs').select('*, institutional_managers(display_name,slug)').in('status', ['approved', 'published']).order('generated_at', { ascending: false }).limit(30),
      client.from('institutional_backtest_runs').select('*, institutional_managers(display_name,slug)').order('generated_at', { ascending: false }).limit(30),
    ]);
    if (cError || eError || xError || bError || tError) throw cError || eError || xError || bError || tError;
    // A failed rotation is an empty section, not a failed page. Everything
    // else on this surface stands on its own.
    if (rError) console.warn(`[research-layer] sector rotation: ${rError.message}`);
    const history = filingMap(filings);
    // Sector rotation aggregates disclosed weights across quarters, so it
    // reads the same gate consensus does.
    const dataIntegrity = await getRepairStatus();
    return { status: 'ready', data_integrity: dataIntegrity, generated_at: new Date().toISOString(), readiness: { managers_tracked: managers.length, managers_with_12_quarters: [...history.values()].filter((rows) => rows.length >= 12).length, classifications: classificationCount || 0, external_filings: externalCount || 0, approved_briefs: briefs?.length || 0, methodology: 'Entry is the first US trading session strictly after SEC acceptance, read in US Eastern. Positions without an adjusted close at both ends of a period are excluded and reported, never re-weighted. A position is priced from its adjusted closes, refreshed daily; a manager whose book cannot be priced in full is reported with its coverage rather than ranked on part of it.' }, sector_rotation: rotation || [], filing_events: events || [], approved_briefs: briefs || [], backtests: backtests || [], managers: managers.map(({ id, slug, display_name }) => ({ id, slug, display_name })) };
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
 * Whether a manager was named by id rather than by slug.
 *
 * A slug is the usual case and a uuid is what the admin surfaces pass, so both
 * have to work - but they cannot be tried together against a uuid column.
 */
export function isUuid(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(value || ''));
}

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
  // Matched on one column or the other, never both in an `or`. id is a uuid,
  // and Postgres rejects the whole clause when the value is not one:
  //
  //   invalid input syntax for type uuid: "berkshire-hathaway"
  //
  // The code this replaced compared in JavaScript, so it never met the
  // question of what the column's type would make of a slug.
  const lookup = client.from('institutional_managers').select('*');
  const { data: managerRows, error: managerError } = await (isUuid(managerSlug)
    ? lookup.eq('id', managerSlug)
    : lookup.eq('slug', managerSlug)).limit(1);
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
  // Paged, and ordered on both columns.
  //
  // This read a hundred tickers at a time with no range, so PostgREST's
  // thousand-row ceiling returned the earliest thousand rows across all of
  // them - roughly forty sessions each. Because the trading calendar is
  // derived from the benchmark's own prints, SPY arrived with two months of
  // history and every period was skipped for having no tradable session after
  // acceptance. Two identical runs then disagreed by a day, which is what a
  // cap boundary with no stable order looks like.
  //
  // Ordered by ticker and then date because paging needs a total order:
  // ordering by date alone leaves rows that share a date free to move between
  // pages, so some are read twice and others not at all.
  for (let index = 0; index < targets.length; index += 50) {
    const slice = targets.slice(index, index + 50);
    for (let from = 0; ; from += 1000) {
      // Matched on ticker, not on security_key. This asked for security_key
      // while passing tickers, which worked only because collectPrices wrote
      // the ticker into that column. The backfill writes the canonical
      // CUSIP-derived key there, as every other table means it, so the old
      // query would have matched none of its rows - the backtester would have
      // run on the handful of legacy symbols and silently ignored the rest.
      const { data, error } = await client.from('institutional_security_prices')
        .select('ticker,price_date,adjusted_close')
        .in('ticker', slice)
        .order('ticker')
        .order('price_date')
        .range(from, from + 999);
      if (error) throw error;
      (data || []).forEach((row) => { const rows = prices.get(row.ticker) || []; rows.push(row); prices.set(row.ticker, rows); });
      if (!data || data.length < 1000) break;
    }
  }

  // The trading calendar, derived from the benchmark's own price history rather
  // than a hardcoded holiday table. It is the one series expected to have a
  // print on every session, so it defines what "next tradable session" means -
  // correct for every year, including half-days and unscheduled closures, with
  // no list to maintain.
  const sessions = sessionsFromPrices(prices.get(BENCHMARKS[0]) || []);

  const byFiling = new Map(); managerHoldings.forEach((row) => { const rows = byFiling.get(row.filing_id) || []; rows.push(row); byFiling.set(row.filing_id, rows); });

  // Collapse filings the market learned of on the same day.
  //
  // A 13F-HR/A restating an older quarter is often accepted alongside a newer
  // quarter's original, so both resolve to the same first tradable session.
  // Each then opened its own period, and the earlier one began and ended on
  // that session - a zero-length holding period, correctly refused, but it
  // took the whole run with it: four of thirty-nine such periods left a
  // complete backtest reporting `not_calculable` and no return at all.
  //
  // Only one portfolio can be held from a given session. It is the one with
  // the latest report date, because that is the most current book the market
  // could act on that morning - an amendment to a quarter eighteen months gone
  // does not become the portfolio.
  const chain = [];
  for (const filing of managerFilings) {
    const session = firstTradableSession(filing.accepted_at || filing.filed_at, sessions);
    const previous = chain[chain.length - 1];
    if (previous && session && previous.session === session) {
      if (String(filing.report_date) > String(previous.filing.report_date)) {
        chain[chain.length - 1] = { filing, session };
      }
      continue;
    }
    chain.push({ filing, session });
  }
  const orderedFilings = chain.map((entry) => entry.filing);

  const periods = [];
  const skipped = [];
  const limit = Math.max(1, Math.min(50, number(topN) || 10));

  for (let index = 0; index < orderedFilings.length - 1; index += 1) {
    const filing = orderedFilings[index]; const next = orderedFilings[index + 1];

    // Entry is the first session strictly after public acceptance, read in US
    // Eastern. The previous code truncated the acceptance instant in UTC and
    // matched prices with '>=', so it entered at the acceptance day's own
    // close - a price struck before the filing was public.
    const entry = firstTradableSession(filing.accepted_at || filing.filed_at, sessions);
    const exit = firstTradableSession(next.accepted_at || next.filed_at, sessions);
    if (!entry || !exit) {
      // Named, because the calendar comes from the benchmark rather than from
      // the positions. The old wording - "within the price history" - was true
      // of a history it did not identify, and sent a reader looking at the
      // holdings' prices when the missing series was the ruler measuring them.
      skipped.push({
        report_date: filing.report_date,
        reason: `no tradable session after acceptance in the ${BENCHMARKS[0]} calendar`
          + `${sessions.length ? `, which runs ${sessions[0]} to ${sessions[sessions.length - 1]}` : ' (the benchmark has no prices at all)'}`,
      });
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

  // Depth is part of the strategy, not a detail of how it was run. Without it
  // a twelve-quarter and a forty-quarter test for one manager on one day share
  // a key and overwrite each other, and the stored row cannot say which it is.
  const strategyKey = `top_${topN}_q${depth}_${crypto.createHash('sha1').update(String(transactionCostBps)).digest('hex').slice(0, 6)}`;
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

/**
 * Today's stored run for these parameters, computing it once if absent.
 *
 * A backtest reads several hundred thousand price rows and takes the better
 * part of a minute on this instance, which is not something to put behind a
 * button a client can hold down. Runs are already persisted per manager, day
 * and strategy, so the first request of the day pays for it and the rest read
 * the row.
 *
 * Deliberately not a cache with its own expiry: the key is the date, so a run
 * is current by construction and yesterday's cannot be served as today's.
 */
export async function readOrRunBacktest({ managerSlug, topN = 10, transactionCostBps = 10, quarters = 12 } = {}) {
  if (!managerSlug) throw new Error('Choose a manager to run the backtest.');
  const depth = Math.max(2, Math.min(Number(quarters) || 12, 48));
  const limit = Math.max(1, Math.min(50, Number(topN) || 10));
  const client = db();

  const lookup = client.from('institutional_managers').select('id,slug,display_name');
  const { data: managerRows, error: managerError } = await (isUuid(managerSlug)
    ? lookup.eq('id', managerSlug)
    : lookup.eq('slug', managerSlug)).limit(1);
  if (managerError) throw managerError;
  const manager = managerRows?.[0];
  if (!manager) throw new Error('Tracked manager not found.');

  const strategyKey = `top_${limit}_q${depth}_${crypto.createHash('sha1').update(String(transactionCostBps)).digest('hex').slice(0, 6)}`;
  const { data: stored, error: storedError } = await client
    .from('institutional_backtest_runs').select('*')
    .eq('manager_id', manager.id)
    .eq('as_of_date', dateOnly(new Date()))
    .eq('strategy_key', strategyKey)
    .limit(1);
  // A failed lookup recomputes rather than failing. The run is the product;
  // the cache is an optimisation and must not be able to take it down.
  if (storedError) console.warn(`[research-layer] stored backtest lookup: ${storedError.message}`);
  if (stored?.[0]) {
    return { ...stored[0], manager: { display_name: manager.display_name, slug: manager.slug }, from_cache: true };
  }

  const run = await runInstitutionalBacktest({ managerSlug, topN: limit, transactionCostBps, quarters: depth });
  return { ...run, from_cache: false };
}
