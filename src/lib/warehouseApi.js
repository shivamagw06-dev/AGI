import { API_ORIGIN } from '@/config';

const BASE = API_ORIGIN || '';

let currentActor = 'admin';

/** The workspace names who is making every change; the server records it. */
export function setWarehouseActor(actor) {
  currentActor = String(actor || 'admin').slice(0, 200);
}

export function getWarehouseActor() {
  return currentActor;
}

async function warehouseFetch(path, { method = 'GET', body, timeoutMs = 60_000 } = {}) {
  if (!BASE) {
    throw new Error('API origin is not configured. Set VITE_API_URL to the backend.');
  }
  const url = `${BASE}/api/intelligence/warehouse${path}`;
  const headers = { 'X-AGI-Actor': currentActor };
  if (body) headers['Content-Type'] = 'application/json';

  let resp;
  try {
    resp = await fetch(url, {
      method,
      credentials: 'include',
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err) {
    const name = err?.name || '';
    if (name === 'TimeoutError' || name === 'AbortError') {
      throw new Error(
        `Warehouse request timed out after ${Math.round(timeoutMs / 1000)}s (${path}).`,
      );
    }
    throw err;
  }

  const text = await resp.text().catch(() => '');
  if (text.trim().startsWith('<')) {
    throw new Error(`Warehouse API returned HTML for ${path}. Check VITE_API_URL.`);
  }
  if (!resp.ok) {
    throw new Error(`Warehouse API error (${resp.status}) ${text.slice(0, 200)}`);
  }
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`Warehouse API invalid JSON for ${path}`);
  }
}

const qs = (params = {}) => {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== '',
  );
  if (!entries.length) return '';
  return `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()}`;
};

const tabPath = (tabId) => `/tab/${encodeURIComponent(tabId)}`;

/* Workbook + health */
export const getWarehouseHealth = () => warehouseFetch('/health');
export const getWorkbook = () => warehouseFetch('/workbook');
export const getWarehouseStats = () => warehouseFetch('/stats');
export const getWarehouseWhoami = () => warehouseFetch('/whoami');
export const getWarehouseCoverage = () => warehouseFetch('/coverage');

/* Sheets */
export const getSheet = (tabId, params = {}) => {
  const { filters, ...rest } = params;
  const query = { ...rest };
  if (filters && Object.keys(filters).length) query.filters = JSON.stringify(filters);
  return warehouseFetch(`${tabPath(tabId)}${qs(query)}`, { timeoutMs: 90_000 });
};
export const getTabSchema = (tabId) => warehouseFetch(`${tabPath(tabId)}/schema`);
export const getWarehouseRow = (tabId, rowId) =>
  warehouseFetch(`${tabPath(tabId)}/row/${encodeURIComponent(rowId)}`);

/* Editing */
export const editCells = (tabId, edits, { reason, recalculate = true } = {}) =>
  warehouseFetch(`${tabPath(tabId)}/edit`, {
    method: 'POST',
    body: { edits, reason, recalculate, actor: currentActor },
    timeoutMs: 120_000,
  });
export const createRow = (tabId, values) =>
  warehouseFetch(`${tabPath(tabId)}/row`, {
    method: 'POST',
    body: { values, actor: currentActor },
  });
export const clearOverride = (tabId, rowId, column) =>
  warehouseFetch(`${tabPath(tabId)}/clear-override`, {
    method: 'POST',
    body: { row_id: rowId, column, actor: currentActor },
  });
export const deleteRows = (tabId, rowIds, reason) =>
  warehouseFetch(`${tabPath(tabId)}/delete`, {
    method: 'POST',
    body: { row_ids: rowIds, reason, actor: currentActor },
  });
export const publishTab = (tabId) =>
  warehouseFetch(`${tabPath(tabId)}/publish`, { method: 'POST', body: { actor: currentActor } });

/* Import / export */
export const mapHeaders = (tabId, headers) =>
  warehouseFetch(`${tabPath(tabId)}/map-headers`, { method: 'POST', body: { headers } });
export const stageImport = (tabId, payload) =>
  warehouseFetch(`${tabPath(tabId)}/import`, {
    method: 'POST',
    body: { ...payload, actor: currentActor },
    timeoutMs: 300_000,
  });
export const commitImport = (importId) =>
  warehouseFetch(`/import/${encodeURIComponent(importId)}/commit`, {
    method: 'POST',
    body: { actor: currentActor },
    timeoutMs: 300_000,
  });
export const listImports = (params = {}) => warehouseFetch(`/imports${qs(params)}`);
export const exportTab = (tabId, params = {}) =>
  warehouseFetch(`${tabPath(tabId)}/export${qs(params)}`, { timeoutMs: 180_000 });

/* Versions + audit */
export const getRowHistory = (tabId, rowId, column) =>
  warehouseFetch(`${tabPath(tabId)}/row/${encodeURIComponent(rowId)}/history${qs({ column })}`);
export const compareVersions = (tabId, rowId, versionA, versionB) =>
  warehouseFetch(
    `${tabPath(tabId)}/row/${encodeURIComponent(rowId)}/compare${qs({
      version_a: versionA,
      version_b: versionB,
    })}`,
  );
export const restoreVersion = (tabId, rowId, version) =>
  warehouseFetch(`${tabPath(tabId)}/row/${encodeURIComponent(rowId)}/restore`, {
    method: 'POST',
    body: { version, actor: currentActor },
  });
export const getAuditLog = (params = {}) => warehouseFetch(`/audit${qs(params)}`);

/* Operations */
export const validateWarehouse = (params = {}) =>
  warehouseFetch(`/validate${qs(params)}`, { timeoutMs: 180_000 });
export const runRefresh = (payload = {}) =>
  warehouseFetch('/refresh', {
    method: 'POST',
    body: { ...payload, actor: currentActor },
    timeoutMs: 900_000,
  });
export const listRefreshRuns = (limit = 10) => warehouseFetch(`/refresh-runs${qs({ limit })}`);
export const getSchedulerStatus = () => warehouseFetch('/scheduler');
export const recalculate = (payload = {}) =>
  warehouseFetch('/recalculate', {
    method: 'POST',
    body: { ...payload, actor: currentActor },
    timeoutMs: 600_000,
  });

/* Historical backfill (Phase 7.1a) */
export const runBackfill = (payload = {}) =>
  warehouseFetch('/backfill', {
    method: 'POST',
    body: { ...payload, actor: currentActor },
    timeoutMs: 900_000,
  });
export const getBackfillStatus = () => warehouseFetch('/backfill/status');
export const getBackfillJobs = (limit = 10) => warehouseFetch(`/backfill/jobs${qs({ limit })}`);
export const getHistoricalCoverage = (top = 25) =>
  warehouseFetch(`/historical-coverage${qs({ top })}`, { timeoutMs: 180_000 });

/* Historical reads — served from the warehouse, never from a collector */
const historyFetch = (path, params = {}) => {
  const url = `${BASE}/api/intelligence/history${path}${qs(params)}`;
  return fetch(url, { credentials: 'include', headers: { 'X-AGI-Actor': currentActor } }).then(
    async (resp) => {
      const text = await resp.text().catch(() => '');
      if (!resp.ok) throw new Error(`History API error (${resp.status}) ${text.slice(0, 200)}`);
      return text ? JSON.parse(text) : null;
    },
  );
};

export const getCompanyHistory = (symbol, params = {}) =>
  historyFetch(`/company/${encodeURIComponent(symbol)}`, params);
export const getSeries = (symbol, metric, params = {}) =>
  historyFetch(`/series/${encodeURIComponent(symbol)}/${encodeURIComponent(metric)}`, params);
export const getAsAt = (symbol, on) => historyFetch(`/as-at/${encodeURIComponent(symbol)}`, { on });
export const getHistoryTable = (tabId, params = {}) =>
  historyFetch(`/table/${encodeURIComponent(tabId)}`, params);
export const compareHistory = (symbols, metric, window = '5y') =>
  historyFetch('/compare', { symbols: symbols.join(','), metric, window });
export const getSymbolCoverage = (symbol) =>
  historyFetch(`/coverage/${encodeURIComponent(symbol)}`);

/* Historical Intelligence Engine (Phase 7.2) */
const hieFetch = (path, params = {}) => {
  const url = `${BASE}/api/intelligence/historical-intelligence${path}${qs(params)}`;
  return fetch(url, { credentials: 'include', headers: { 'X-AGI-Actor': currentActor } }).then(
    async (resp) => {
      const text = await resp.text().catch(() => '');
      if (!resp.ok) throw new Error(`Historical API error (${resp.status}) ${text.slice(0, 200)}`);
      return text ? JSON.parse(text) : null;
    },
  );
};

export const getHieHealth = () => hieFetch('/health');
export const detectHistoricalIntent = (q) => hieFetch('/detect', { q });
export const askHistory = (question, symbol, peers) =>
  warehouseFetch('/../historical-intelligence/ask', {
    method: 'POST',
    body: { question, symbol, peers, actor: currentActor },
    timeoutMs: 180_000,
  });
export const getHistoryCoverage = (symbol, metric) =>
  hieFetch(`/coverage/${encodeURIComponent(symbol)}`, metric ? { metric } : {});
export const getCompanyHistoryCards = (symbol, metrics) =>
  hieFetch(`/company/${encodeURIComponent(symbol)}`, metrics ? { metrics: metrics.join(',') } : {});
export const getTrendAnalysis = (symbol, metric) =>
  hieFetch(`/trend/${encodeURIComponent(symbol)}/${encodeURIComponent(metric)}`);
export const getValuationHistory = (symbol, metric = 'pe') =>
  hieFetch(`/valuation/${encodeURIComponent(symbol)}`, { metric });
export const getValuationBands = (symbol, metric = 'pe') =>
  hieFetch(`/bands/${encodeURIComponent(symbol)}`, { metric });
export const getEventTimeline = (symbol, limit = 40) =>
  hieFetch(`/timeline/${encodeURIComponent(symbol)}`, { limit });
export const compareHistories = (symbols, metric = 'price') =>
  hieFetch('/compare', { symbols: symbols.join(','), metric });
export const getSectorHistory = (symbol, metric = 'pe') =>
  hieFetch(`/sector/${encodeURIComponent(symbol)}`, { metric });

/* Search */
export const searchWarehouse = (q, params = {}) => warehouseFetch(`/search${qs({ q, ...params })}`);
export const suggestCompanies = (prefix, limit = 10) =>
  warehouseFetch(`/suggest${qs({ prefix, limit })}`);
export const getCompanyView = (symbol, perTab = 25) =>
  warehouseFetch(`/company/${encodeURIComponent(symbol)}${qs({ per_tab: perTab })}`);

/* Phase 7.4F — Financial Warehouse Completion Programme (FWCP) */
async function fwcpFetch(path, opts = {}) {
  // /fwcp/* lives beside /warehouse/* on the intelligence BFF.
  if (!BASE) throw new Error('API origin is not configured. Set VITE_API_URL to the backend.');
  const url = `${BASE}/api/intelligence${path}`;
  const headers = { 'X-AGI-Actor': currentActor };
  if (opts.body) headers['Content-Type'] = 'application/json';
  const resp = await fetch(url, {
    method: opts.method || 'GET',
    credentials: 'include',
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    signal: AbortSignal.timeout(opts.timeoutMs || 60_000),
  });
  const text = await resp.text().catch(() => '');
  if (!resp.ok) throw new Error(`FWCP API error (${resp.status}) ${text.slice(0, 200)}`);
  return text ? JSON.parse(text) : null;
}

export const getFwcpHealth = () => fwcpFetch('/fwcp/health');
export const getFinancialCoverage = () =>
  warehouseFetch('/financial-coverage', { timeoutMs: 90_000 });
/** Phase 7.4F Step 0 — full financial warehouse coverage audit (read-only). */
export const getFinancialAudit = () =>
  warehouseFetch('/financial-audit', { timeoutMs: 180_000 });
export const getCoverageSummary = () =>
  warehouseFetch('/coverage/summary', { timeoutMs: 180_000 });
export const getCoverageBySector = () =>
  warehouseFetch('/coverage/sector', { timeoutMs: 180_000 });
export const getMissingFinancials = (limit = 200, classification) =>
  warehouseFetch(`/missing-financials${qs({ limit, classification })}`, { timeoutMs: 180_000 });
export const getCompanyFinancialCoverage = (symbol) =>
  warehouseFetch(`/company/${encodeURIComponent(symbol)}/coverage`);
export const getMissingStatements = (limit = 200) =>
  warehouseFetch(`/missing-statements${qs({ limit })}`, { timeoutMs: 90_000 });
export const getMissingShareCount = (limit = 200) =>
  warehouseFetch(`/missing-share-count${qs({ limit })}`, { timeoutMs: 90_000 });
export const getFwcpImportStatus = () => warehouseFetch('/import/status');
export const getFwcpImportBoard = () => warehouseFetch('/import/board', { timeoutMs: 90_000 });
export const postFwcpImportStart = (body = {}) =>
  warehouseFetch('/import/start', { method: 'POST', body });
export const postFwcpImportStop = () =>
  warehouseFetch('/import/stop', { method: 'POST', body: {} });
export const postFwcpImportResume = (body = {}) =>
  warehouseFetch('/import/resume', { method: 'POST', body });
export const postFwcpImportRetry = (body = {}) =>
  warehouseFetch('/import/retry', { method: 'POST', body, timeoutMs: 300_000 });
export const postFwcpImportRun = (body = {}) =>
  warehouseFetch('/import/run', { method: 'POST', body, timeoutMs: 300_000 });
export const getFwcpCapitalIq = () => warehouseFetch('/import/capital-iq');
export const postFwcpCapitalIq = (body = {}) =>
  warehouseFetch('/import/capital-iq', { method: 'POST', body, timeoutMs: 300_000 });
export const postSyncShareCount = (symbol) =>
  warehouseFetch(`/share-count/${encodeURIComponent(symbol)}/sync`, { method: 'POST', body: {} });

/* Phase 7.4F — Yahoo-first financial fill */
export const getYahooFillStatus = () =>
  warehouseFetch('/yahoo-fill/status', { timeoutMs: 180_000 });
export const getYahooFillBoard = () =>
  warehouseFetch('/yahoo-fill/board', { timeoutMs: 180_000 });
export const getYahooFillQueue = (limit = 200, includeThin = true) =>
  warehouseFetch(`/yahoo-fill/queue${qs({ limit, include_thin: includeThin })}`, { timeoutMs: 180_000 });
export const getYahooFillProbe = (symbol = 'RELIANCE') =>
  warehouseFetch(`/yahoo-fill/probe${qs({ symbol })}`, { timeoutMs: 120_000 });
export const getUpstoxFillQueue = (limit = 200, includeThin = true) =>
  warehouseFetch(`/upstox-fill/queue${qs({ limit, include_thin: includeThin })}`, { timeoutMs: 180_000 });
export const getUpstoxFillBoard = () =>
  warehouseFetch('/upstox-fill/board', { timeoutMs: 180_000 });
export const postYahooFillStart = (body = {}) =>
  warehouseFetch('/yahoo-fill/start', { method: 'POST', body });
export const postYahooFillStop = () =>
  warehouseFetch('/yahoo-fill/stop', { method: 'POST', body: {} });
export const postYahooFillResume = (body = {}) =>
  warehouseFetch('/yahoo-fill/resume', { method: 'POST', body });
export const postYahooFillRun = (body = {}) =>
  warehouseFetch('/yahoo-fill/run', { method: 'POST', body, timeoutMs: 600_000 });
export const postYahooFillCompany = (symbol) =>
  warehouseFetch(`/yahoo-fill/${encodeURIComponent(symbol)}`, { method: 'POST', body: {}, timeoutMs: 120_000 });
