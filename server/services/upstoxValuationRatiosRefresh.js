/**
 * Upstox key-ratios → warehouse.valuation_ratios via intelligence engine.
 * Resolves ISIN from company_master; never uses ticker for the Upstox call.
 */

function engineConfig() {
  let baseUrl = (process.env.AGIB_INTELLIGENCE_ENGINE_URL || process.env.INTELLIGENCE_ENGINE_URL || '').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) baseUrl = `https://${baseUrl}`;
  const token = (process.env.AGIB_SERVICE_TOKEN || process.env.INTELLIGENCE_ENGINE_TOKEN || '').trim();
  return { baseUrl, token };
}

async function engineFetch(path, { method = 'GET', body = null, timeoutMs = 120_000 } = {}) {
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

/**
 * Load companies with ISINs from warehouse company_master.
 */
export async function loadIsinUniverse({ limit = 500 } = {}) {
  const result = await engineFetch(
    `/v1/warehouse/tab/company_master?limit=${Math.max(1, Number(limit) || 500)}`
  );
  const rows = result.data?.rows || result.data?.data || [];
  return Array.isArray(rows) ? rows : [];
}

function pickIsinCompanies(rows, { limit = 200 } = {}) {
  const out = [];
  const seen = new Set();
  // Warehouse read order is not an update policy. Keep the eligible universe
  // deterministic before applying the daily rotation below.
  const ordered = [...(rows || [])].sort((a, b) => (
    String(a?.symbol || '').localeCompare(String(b?.symbol || ''))
  ));
  for (const row of ordered) {
    const symbol = String(row.symbol || '').trim().toUpperCase();
    const isin = String(row.isin || '').trim().toUpperCase();
    if (!symbol || !isin || seen.has(isin)) continue;
    if (!/^IN[A-Z0-9]{10}$/.test(isin) && !/^INE[A-Z0-9]{9}$/.test(isin)) continue;
    seen.add(isin);
    out.push({
      symbol,
      isin,
      company_id: row.company_id || symbol,
      instrument_key: row.instrument_key || `NSE_EQ|${isin}`,
      sector: row.sector || null,
    });
    if (out.length >= limit) break;
  }
  return out;
}

/**
 * Select a different contiguous batch on each calendar day.
 *
 * A fixed `slice(0, limit)` quietly leaves most of a large universe stale.
 * This is deliberately deterministic: operators can reproduce which names
 * were due on a given day, while all eligible names receive equal coverage
 * over a complete rotation. Explicit symbol requests bypass this policy.
 */
export function selectDailyRotation(rows, { limit = 200, now = new Date() } = {}) {
  const universe = pickIsinCompanies(rows, { limit: Math.max(1, rows?.length || 1) });
  const batchSize = Math.max(1, Math.min(Number(limit) || 1, universe.length));
  if (!universe.length) {
    return { companies: [], universeSize: 0, offset: 0, batchSize };
  }

  const stamp = now instanceof Date ? now : new Date(now);
  const day = Number.isFinite(stamp.getTime())
    ? Math.floor(Date.UTC(stamp.getUTCFullYear(), stamp.getUTCMonth(), stamp.getUTCDate()) / 86_400_000)
    : 0;
  const offset = (day * batchSize) % universe.length;
  const rotated = [...universe.slice(offset), ...universe.slice(0, offset)];
  return {
    companies: rotated.slice(0, batchSize),
    universeSize: universe.length,
    offset,
    batchSize,
  };
}

/**
 * Fetch Upstox key-ratios for a company list and ingest into warehouse.
 */
export async function refreshUpstoxValuationRatios({
  limit = Number(process.env.UPSTOX_VALUATION_BATCH || 80),
  concurrency = Number(process.env.UPSTOX_VALUATION_CONCURRENCY || 4),
  symbols = null,
  backfillIsins = true,
} = {}) {
  const { getFundamentals, isUpstoxConfigured } = await import('../providers/upstox.js');
  if (!isUpstoxConfigured()) {
    return { ok: false, status: 503, error: 'upstox_not_configured' };
  }

  let isinBackfill = null;
  let companies = [];
  let selection = null;
  if (Array.isArray(symbols) && symbols.length) {
    // Resolve ISINs for explicit symbols from warehouse master.
    let all = await loadIsinUniverse({ limit: 5000 });
    if (backfillIsins && !pickIsinCompanies(all, { limit: 1 }).length) {
      const { backfillCompanyIsins } = await import('./companyIsinBackfill.js');
      isinBackfill = await backfillCompanyIsins({ dryRun: false });
      all = await loadIsinUniverse({ limit: 5000 });
    }
    const want = new Set(symbols.map((s) => String(s).toUpperCase()));
    companies = pickIsinCompanies(all.filter((r) => want.has(String(r.symbol || '').toUpperCase())), {
      limit: symbols.length,
    });
  } else {
    let all = await loadIsinUniverse({ limit: Math.max(limit * 5, 5000) });
    if (backfillIsins && !pickIsinCompanies(all, { limit: 1 }).length) {
      const { backfillCompanyIsins } = await import('./companyIsinBackfill.js');
      isinBackfill = await backfillCompanyIsins({ dryRun: false });
      all = await loadIsinUniverse({ limit: Math.max(limit * 5, 5000) });
    }
    selection = selectDailyRotation(all, { limit });
    companies = selection.companies;
  }

  if (!companies.length) {
    return {
      ok: false,
      status: 404,
      error: 'no_isin_universe',
      fetched: 0,
      ingested: 0,
      isin_backfill: isinBackfill,
      hint: 'Run POST /api/market/company-isin/backfill then retry. Upstox key-ratios require ISIN.',
    };
  }

  const reportedDate = new Date().toISOString().slice(0, 10);
  const batch = [];
  const errors = [];
  let cursor = 0;

  async function worker() {
    while (cursor < companies.length) {
      const idx = cursor;
      cursor += 1;
      const company = companies[idx];
      try {
        const json = await getFundamentals(company.isin, 'key-ratios');
        batch.push({
          symbol: company.symbol,
          isin: company.isin,
          company_id: company.company_id,
          instrument_key: company.instrument_key,
          reported_date: reportedDate,
          data: json?.data || json,
        });
      } catch (err) {
        errors.push({
          symbol: company.symbol,
          isin: company.isin,
          error: err?.message || String(err),
          status: err?.status || null,
        });
      }
    }
  }

  const workers = Array.from({ length: Math.max(1, concurrency) }, () => worker());
  await Promise.all(workers);

  if (!batch.length) {
    // Every getFundamentals call threw — usually rate-limit / auth, not "no ratios".
    const rateLimited = errors.some(
      (e) => e.status === 429 || /too many request/i.test(String(e.error || '')),
    );
    const authFailed = errors.some(
      (e) => e.status === 401 || e.status === 403
        || /unauthorized|forbidden|access.token/i.test(String(e.error || '')),
    );
    return {
      ok: false,
      status: rateLimited ? 429 : authFailed ? 401 : 502,
      error: rateLimited
        ? 'upstox_rate_limited'
        : authFailed
          ? 'upstox_auth_failed'
          : 'upstox_key_ratios_fetch_failed',
      // Legacy alias — bootstrap logs previously showed this for 429 batches.
      legacy_error: 'upstox_key_ratios_empty',
      attempted: companies.length,
      fetched: 0,
      failed: errors.length,
      errors: errors.slice(0, 20),
      hint: rateLimited
        ? 'Upstox HTTP 429 on the whole batch. Slow the bootstrap (pause↑ / concurrency↓). Existing warehouse.valuation_ratios rows are intact.'
        : authFailed
          ? 'Upstox rejected the access token. Refresh UPSTOX_ACCESS_TOKEN.'
          : 'No key-ratios fetched for this batch. Inspect errors[]; warehouse data already ingested is intact.',
    };
  }

  const ingest = await engineFetch('/v1/valuation-ratios/ingest', {
    method: 'POST',
    body: {
      companies: batch,
      actor: 'upstox_valuation_ratios_refresh',
      sync_valuation: true,
    },
    timeoutMs: 180_000,
  });

  if (ingest.ok) {
    return {
      ok: true,
      status: ingest.status,
      attempted: companies.length,
      fetched: batch.length,
      failed: errors.length,
      errors: errors.slice(0, 20),
      warehouse: ingest.data,
      isin_backfill: isinBackfill,
      selection,
      path: 'valuation_ratios_ingest',
      error: null,
    };
  }

  // Fallback: warehouse import+commit (works when ingest route crashes on older engines).
  const rows = flattenKeyRatioRows(batch);
  const fallback = rows.length ? await warehouseImportValuationRatios(rows) : null;

  return {
    ok: !!fallback?.ok,
    status: fallback?.ok ? 200 : ingest.status,
    attempted: companies.length,
    fetched: batch.length,
    failed: errors.length,
    errors: errors.slice(0, 20),
    warehouse: fallback || ingest.data,
    isin_backfill: isinBackfill,
    selection,
    path: fallback?.ok ? 'warehouse_import_fallback' : 'valuation_ratios_ingest',
    error: fallback?.ok ? null : ingest.data?.error || `ingest_http_${ingest.status}`,
  };
}

const RATIO_MAP = {
  'p/e': 'pe',
  pe: 'pe',
  'p/b': 'pb',
  pb: 'pb',
  roa: 'roa',
  roe: 'roe',
  roce: 'roce',
  'ev/ebitda': 'ev_ebitda',
  ev_ebitda: 'ev_ebitda',
  evebitda: 'ev_ebitda',
};

function num(value) {
  if (value == null || typeof value === 'boolean') return null;
  const text = String(value).trim().replace(/,/g, '').replace(/%/g, '');
  if (!text || /^(na|n\/a|-|null|none)$/i.test(text)) return null;
  const n = Number(text);
  return Number.isFinite(n) ? n : null;
}

/** Flatten Upstox key-ratios company batches into warehouse.valuation_ratios rows. */
export function flattenKeyRatioRows(companies) {
  const out = [];
  const reportedDate = new Date().toISOString().slice(0, 10);
  for (const company of companies || []) {
    const symbol = String(company.symbol || '').trim().toUpperCase();
    const isin = String(company.isin || '').trim().toUpperCase();
    if (!symbol || !isin) continue;
    const snapshotId = `upstox-${reportedDate}-${symbol}-${Math.random().toString(16).slice(2, 10)}`;
    let entries = company.data;
    if (entries && !Array.isArray(entries) && typeof entries === 'object') {
      entries = Object.entries(entries).map(([name, block]) => (
        block && typeof block === 'object'
          ? { name, company_value: block.company_value ?? block.value, sector_value: block.sector_value ?? block.sector }
          : { name, company_value: block, sector_value: null }
      ));
    }
    for (const item of Array.isArray(entries) ? entries : []) {
      const mapped = RATIO_MAP[String(item?.name || '').trim().toLowerCase()];
      const companyValue = num(item?.company_value);
      if (!mapped || companyValue == null) continue;
      const sectorValue = num(item?.sector_value);
      out.push({
        company_id: company.company_id || symbol,
        symbol,
        isin,
        instrument_key: company.instrument_key || `NSE_EQ|${isin}`,
        ratio_name: mapped,
        company_value: companyValue,
        sector_value: sectorValue,
        reported_date: company.reported_date || reportedDate,
        snapshot_id: snapshotId,
        provider: 'upstox',
        provider_version: 'v2/fundamentals/key-ratios',
        confidence: 0.9,
        dqiv_status: 'passed',
        source: 'upstox',
      });
    }
  }
  return out;
}

async function warehouseImportValuationRatios(rows) {
  const staged = await engineFetch('/v1/warehouse/tab/valuation_ratios/import', {
    method: 'POST',
    body: { rows, actor: 'upstox_valuation_ratios_refresh', source: 'upstox' },
    timeoutMs: 180_000,
  });
  if (!staged.ok || !staged.data?.import_id) {
    return { ok: false, error: staged.data?.error || 'stage_import_failed', staged: staged.data };
  }
  const committed = await engineFetch(`/v1/warehouse/import/${staged.data.import_id}/commit`, {
    method: 'POST',
    body: { actor: 'upstox_valuation_ratios_refresh' },
    timeoutMs: 180_000,
  });
  return {
    ok: committed.ok,
    import_id: staged.data.import_id,
    staged: staged.data,
    committed: committed.data,
    error: committed.ok ? null : committed.data?.error || 'commit_failed',
  };
}
