/**
 * Phase 7.4E — Upstox Institutional Fundamentals Integration (UIFI).
 *
 * Node fetches Upstox; intelligence-engine normalises → DQIV → warehouse.
 * Products never call Upstox from this path.
 */

import { loadIsinUniverse } from './upstoxValuationRatiosRefresh.js';

const DATASETS = Object.freeze([
  'profile',
  'income-statement',
  'balance-sheet',
  'cash-flow',
  'share-holdings',
  'competitors',
  'corporate-actions',
]);

// The market universe intentionally contains more than operating companies.
// Keep that breadth for quotes and ETF research, but do not send funds to the
// company-financial-statement pipeline.  Upstox company statements are best
// used for listed operating companies (normally INE* ISINs).
const FUND_NAME_RE = /\b(ETF|EXCHANGE[ -]?TRADED|MUTUAL FUND|LIQUID FUND|INDEX FUND)\b/i;
const FUND_SYMBOL_RE = /(?:ETF|BEES|IETF|BETF|ADD|CASE|BETA|GOLD|SILVER|LIQUID)/i;

/**
 * Classify instruments without guessing from an ISIN alone.  The return is
 * carried through operator responses, making exclusions auditable.
 */
export function classifyInstrument(row = {}) {
  const declared = String(row.instrument_type || row.security_type || row.asset_type || '').trim().toUpperCase();
  if (declared === 'STOCK' || declared === 'EQUITY') return { type: 'STOCK', reason: 'declared_equity' };
  if (['ETF', 'FUND', 'MUTUAL_FUND', 'INDEX'].includes(declared)) return { type: declared === 'ETF' ? 'ETF' : 'FUND', reason: 'declared_non_company' };

  const isin = String(row.isin || '').trim().toUpperCase();
  const symbol = String(row.symbol || '').trim().toUpperCase();
  const name = String(row.company_name || row.legal_name || '').trim();
  if (isin.startsWith('INF')) return { type: 'FUND', reason: 'fund_isin' };
  if (FUND_NAME_RE.test(name) || FUND_SYMBOL_RE.test(symbol)) return { type: 'ETF', reason: 'fund_or_etf_name' };
  if (/^INE[A-Z0-9]{9}$/.test(isin)) return { type: 'STOCK', reason: 'equity_isin' };
  return { type: 'UNKNOWN', reason: 'unclassified_instrument' };
}

export function statementRequests({ annualOnly = false } = {}) {
  const annual = [
    ['income-statement', { type: 'consolidated', time_period: 'yearly', fs: true }],
    ['balance-sheet', { type: 'consolidated', time_period: 'yearly', fs: true }],
    ['cash-flow', { type: 'consolidated', time_period: 'yearly', fs: true }],
  ];
  if (annualOnly) return annual;
  // Upstox documents `time_period` for income statements only. Balance-sheet
  // and cash-flow full statements are annual, so do not manufacture quarterly
  // requests that can be ignored or rejected by the provider.
  return annual.concat([
    ['income-statement', { type: 'consolidated', time_period: 'quarterly', fs: false }],
  ]);
}

export function instrumentUniverseSummary(rows = []) {
  const counts = { STOCK: 0, ETF: 0, FUND: 0, UNKNOWN: 0 };
  for (const row of rows) counts[classifyInstrument(row).type] += 1;
  return counts;
}

function engineConfig() {
  let baseUrl = (process.env.AGIB_INTELLIGENCE_ENGINE_URL || process.env.INTELLIGENCE_ENGINE_URL || '').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) baseUrl = `https://${baseUrl}`;
  const token = (process.env.AGIB_SERVICE_TOKEN || process.env.INTELLIGENCE_ENGINE_TOKEN || '').trim();
  return { baseUrl, token };
}

async function engineFetch(path, { method = 'GET', body = null, timeoutMs = 180_000 } = {}) {
  const { baseUrl, token } = engineConfig();
  if (!baseUrl || !token) {
    return { ok: false, status: 503, data: { error: 'intelligence_engine_not_configured' } };
  }
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      'X-AGI-Intelligence-Token': token,
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: String(text || '').slice(0, 400) };
  }
  return { ok: response.ok, status: response.status, data };
}

export function pickIsinCompanies(rows, { limit = 40, symbols = null, offset = 0 } = {}) {
  const want = Array.isArray(symbols) && symbols.length
    ? new Set(symbols.map((s) => String(s).toUpperCase()))
    : null;
  const eligible = [];
  const seen = new Set();
  for (const row of rows || []) {
    const symbol = String(row.symbol || '').trim().toUpperCase();
    const isin = String(row.isin || '').trim().toUpperCase();
    if (!symbol || !isin || seen.has(isin)) continue;
    if (want && !want.has(symbol)) continue;
    const classification = classifyInstrument(row);
    if (classification.type !== 'STOCK') continue;
    seen.add(isin);
    eligible.push({
      symbol,
      isin,
      company_id: row.company_id || symbol,
      instrument_key: row.instrument_key || `NSE_EQ|${isin}`,
      sector: row.sector || null,
      industry: row.industry || null,
      instrument_type: classification.type,
      instrument_type_reason: classification.reason,
    });
  }
  // Explicit user selections must keep their requested order. Scheduled runs
  // rotate through the full universe instead of repeatedly refreshing the
  // first N symbols forever.
  if (want || eligible.length <= limit) return eligible.slice(0, limit);
  const start = Math.max(0, Number(offset) || 0) % eligible.length;
  return Array.from({ length: Math.min(limit, eligible.length) }, (_, index) =>
    eligible[(start + index) % eligible.length],
  );
}

function buildIsinMap(rows) {
  const map = {};
  for (const row of rows || []) {
    const isin = String(row.isin || '').trim().toUpperCase();
    const symbol = String(row.symbol || '').trim().toUpperCase();
    if (isin && symbol) map[isin] = symbol;
  }
  return map;
}

/**
 * Refresh one fundamentals dataset for a batch of ISIN-mapped companies.
 */
export async function refreshUpstoxFundamentals({
  dataset = 'profile',
  limit = Number(process.env.UIFI_BATCH || 40),
  concurrency = Number(process.env.UIFI_CONCURRENCY || 3),
  symbols = null,
  offset = 0,
  annualOnly = false,
} = {}) {
  const ds = String(dataset || '').trim().toLowerCase();
  if (!DATASETS.includes(ds) && ds !== 'statements') {
    return { ok: false, status: 400, error: `unsupported_dataset:${ds}`, datasets: DATASETS };
  }

  const { getFundamentals, getCompetitors, isUpstoxConfigured } = await import('../providers/upstox.js');
  if (!isUpstoxConfigured()) {
    return { ok: false, status: 503, error: 'upstox_not_configured' };
  }

  const universe = await loadIsinUniverse({ limit: Math.max(limit * 5, 5000) });
  const companies = pickIsinCompanies(universe, { limit, symbols, offset });
  if (!companies.length) {
    return { ok: false, status: 404, error: 'no_isin_universe', dataset: ds };
  }

  const isinMap = buildIsinMap(universe);
  const batch = [];
  const errors = [];
  let cursor = 0;

  async function worker() {
    while (cursor < companies.length) {
      const idx = cursor;
      cursor += 1;
      const company = companies[idx];
      try {
        if (ds === 'statements') {
          // The coverage backfill is deliberately annual-only: three bounded
          // requests per company, all with full line items.  Quarterly refresh
          // remains available for the post-close scheduler when required.
          const replies = await Promise.all(statementRequests({ annualOnly }).map(
            ([endpoint, params]) => getFundamentals(company.isin, endpoint, params),
          ));
          const [incomeY, balanceY, cashY, incomeQ] = replies;
          batch.push({
            symbol: company.symbol,
            isin: company.isin,
            company_id: company.company_id,
            instrument_key: company.instrument_key,
            dataset: 'statements',
            'income-statement': incomeY,
            'balance-sheet': balanceY,
            'cash-flow': cashY,
            reported_unit: 'crore',
            source: 'upstox',
          });
          if (!annualOnly) batch.push({
            symbol: company.symbol,
            isin: company.isin,
            company_id: company.company_id,
            instrument_key: company.instrument_key,
            dataset: 'statements',
            'income-statement': incomeQ,
            reported_unit: 'crore',
            source: 'upstox',
          });
        } else if (ds === 'competitors') {
          const key = company.instrument_key || `NSE_EQ|${company.isin}`;
          const json = await getCompetitors(key);
          batch.push({
            symbol: company.symbol,
            isin: company.isin,
            instrument_key: key,
            sector: company.sector,
            industry: company.industry,
            isin_map: isinMap,
            data: json?.data || json,
          });
        } else {
          const json = await getFundamentals(company.isin, ds);
          batch.push({
            symbol: company.symbol,
            isin: company.isin,
            company_id: company.company_id,
            instrument_key: company.instrument_key,
            data: json?.data || json,
            units_in: json?.data?.units_in,
          });
        }
      } catch (err) {
        errors.push({
          symbol: company.symbol,
          isin: company.isin,
          dataset: ds,
          error: err?.message || String(err),
          status: err?.status || null,
        });
      }
    }
  }

  await Promise.all(Array.from({ length: Math.max(1, concurrency) }, () => worker()));

  if (!batch.length) {
    return {
      ok: false,
      status: 502,
      error: 'upstox_fundamentals_empty',
      dataset: ds,
      attempted: companies.length,
      errors: errors.slice(0, 20),
    };
  }

  const ingestDataset = ds === 'statements' ? 'statements' : ds;
  const ingest = await engineFetch('/v1/upstox-fundamentals/ingest', {
    method: 'POST',
    body: {
      dataset: ingestDataset,
      companies: batch,
      actor: `uifi_${ingestDataset.replace(/-/g, '_')}`,
    },
  });

  return {
    ok: Boolean(ingest?.ok && ingest?.data?.ok !== false),
    status: ingest?.status,
    dataset: ds,
    attempted: companies.length,
    selection: {
      offset: Number(offset) || 0,
      universeSize: universe.length,
      instrument_types: instrumentUniverseSummary(universe),
      batchSize: companies.length,
      annual_only: Boolean(annualOnly),
      requests_per_company: annualOnly ? 3 : 4,
    },
    fetched: batch.length,
    errors: errors.slice(0, 20),
    ingest: ingest?.data || ingest,
  };
}

export async function getUifiCoverage() {
  const result = await engineFetch('/v1/upstox-fundamentals/coverage');
  return result.data || { ok: false, error: 'coverage_unavailable' };
}

export async function getUifiFailures() {
  const result = await engineFetch('/v1/upstox-fundamentals/failures');
  return result.data || { ok: false, error: 'failures_unavailable' };
}

export { DATASETS };
