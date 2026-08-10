import { API_ORIGIN } from '@/config';

const BASE = API_ORIGIN || '';

async function intelligenceFetch(path, { method = 'GET', body, timeoutMs = 45_000 } = {}) {
  if (!BASE) {
    throw new Error('API origin is not configured. Set VITE_API_URL to the Render backend.');
  }
  const url = `${BASE}/api/intelligence${path}`;
  let resp;
  try {
    resp = await fetch(url, {
      method,
      credentials: 'include',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err) {
    const name = err?.name || '';
    if (name === 'TimeoutError' || name === 'AbortError' || /timed out|aborted/i.test(String(err?.message || ''))) {
      throw new Error(
        `Release Health / intelligence request timed out after ${Math.round(timeoutMs / 1000)}s (${path}). ` +
          'The intelligence engine may be cold-starting or busy — wait a moment and retry.'
      );
    }
    throw err;
  }
  const contentType = resp.headers.get('content-type') || '';
  const text = await resp.text().catch(() => '');
  if (!contentType.includes('application/json') || text.trim().startsWith('<')) {
    throw new Error(
      `Intelligence API returned HTML instead of JSON for ${path}. Check VITE_API_URL points at Render, not the website.`
    );
  }
  if (!resp.ok) {
    let detail = text.slice(0, 160);
    try {
      const parsed = text ? JSON.parse(text) : null;
      const raw = typeof parsed?.raw === 'string' ? parsed.raw : '';
      if (raw.trim().startsWith('<')) {
        detail =
          parsed?.error ||
          parsed?.detail ||
          'Upstream intelligence engine returned an HTML error page (often a Render 502 during redeploy). Retry in a minute.';
      } else {
        detail =
          parsed?.error ||
          parsed?.detail ||
          parsed?.message ||
          detail;
      }
    } catch {
      /* keep truncated text */
    }
    throw new Error(`Intelligence API error (${resp.status}) ${String(detail).slice(0, 220)}`);
  }
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`Intelligence API invalid JSON for ${path}`);
  }
}

export const getIntelligenceHealth = () => intelligenceFetch('/health');
export const createResearchRun = (payload) => intelligenceFetch('/research/runs', { method: 'POST', body: payload });
export const getResearchRun = (runId) => intelligenceFetch(`/research/runs/${encodeURIComponent(runId)}`);
export const listResearchRuns = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return intelligenceFetch(`/research/runs${qs ? `?${qs}` : ''}`);
};

/** KF1 Knowledge Foundation */
export const getKfHealth = () => intelligenceFetch('/kf/health');
export const getKfCoverage = () => intelligenceFetch('/kf/coverage');
export const seedKf = () => intelligenceFetch('/kf/seed', { method: 'POST', body: {} });
export const rebuildKf = () => intelligenceFetch('/kf/rebuild', { method: 'POST', body: {} });
export const searchKf = (q, limit = 12) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/kf/search?${qs}`);
};
export const listKfCompanies = () => intelligenceFetch('/kf/companies');
export const listKfSectors = () => intelligenceFetch('/kf/sectors');
export const listKfThemes = () => intelligenceFetch('/kf/themes');
export const listKfMacros = () => intelligenceFetch('/kf/macros');
export const listKfPredictions = () => intelligenceFetch('/kf/predictions');
export const listKfExtracts = () => intelligenceFetch('/kf/extracts');

/** KCV1 Knowledge Corpus */
export const getKcHealth = () => intelligenceFetch('/kc/health');
export const getKcMetrics = () => intelligenceFetch('/kc/metrics');
export const getKcDashboard = () => intelligenceFetch('/kc/dashboard');
export const populateKc = (rebuildKip = true) =>
  intelligenceFetch(`/kc/populate?rebuild_kip=${rebuildKip ? 'true' : 'false'}`, {
    method: 'POST',
    body: {},
  });
export const ensureKcUniverse = () => intelligenceFetch('/kc/universe', { method: 'POST', body: {} });
export const getKcGaps = () => intelligenceFetch('/kc/gaps');
export const getKcLearning = () => intelligenceFetch('/kc/learning');
export const getKcQuality = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return intelligenceFetch(`/kc/quality${qs ? `?${qs}` : ''}`);
};
export const consultKc = (q, limit = 8) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/kc/consult?${qs}`);
};

/** AOI v1 Open Intelligence */
export const getAoiHealth = () => intelligenceFetch('/aoi/health');
export const getAoiDashboard = () => intelligenceFetch('/aoi/dashboard');
export const seedAoiRegistry = () => intelligenceFetch('/aoi/registry/seed', { method: 'POST', body: {} });
export const runAoiCycle = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null)
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/aoi/run${qs ? `?${qs}` : ''}`, { method: 'POST', body: {} });
};
export const listAoiCompanies = (universe = 'nifty_50') => {
  const qs = new URLSearchParams({ universe }).toString();
  return intelligenceFetch(`/aoi/companies?${qs}`);
};
export const getAoiCompany = (key) => intelligenceFetch(`/aoi/company/${encodeURIComponent(key)}`);
export const searchAoi = (q, limit = 20) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/aoi/search?${qs}`);
};
export const consultAoi = (q, limit = 8) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/aoi/consult?${qs}`);
};
export const getAoiConnectors = () => intelligenceFetch('/aoi/connectors');
export const getAoiScheduler = () => intelligenceFetch('/aoi/scheduler');
export const getAoiGaps = () => intelligenceFetch('/aoi/gaps');
export const getAoiLearning = () => intelligenceFetch('/aoi/learning');

/** EVE v1 Evidence & Verification */
export const getEveHealth = () => intelligenceFetch('/eve/health');
export const getEveDashboard = () => intelligenceFetch('/eve/dashboard');
export const listEveEvidence = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/eve/evidence${qs ? `?${qs}` : ''}`);
};
export const getEveEvidence = (id) => intelligenceFetch(`/eve/evidence/${encodeURIComponent(id)}`);
export const getEveCompany = (key) => intelligenceFetch(`/eve/company/${encodeURIComponent(key)}`);
export const getEveConflicts = (status = 'open') => {
  const qs = new URLSearchParams({ status }).toString();
  return intelligenceFetch(`/eve/conflicts?${qs}`);
};
export const getEveTimeline = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/eve/timeline${qs ? `?${qs}` : ''}`);
};
export const getEveTrust = () => intelligenceFetch('/eve/trust');
export const getEveSources = () => intelligenceFetch('/eve/source');
export const getEveVerification = () => intelligenceFetch('/eve/verification');
export const runEveVerification = () => intelligenceFetch('/eve/verification/run', { method: 'POST', body: {} });
export const searchEve = (q, limit = 20) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/eve/search?${qs}`);
};
export const consultEve = (q, limit = 8) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/eve/consult?${qs}`);
};
export const getEveAudit = (limit = 50) => {
  const qs = new URLSearchParams({ limit: String(limit) }).toString();
  return intelligenceFetch(`/eve/audit?${qs}`);
};

/** IIE v1 Investment Intelligence */
export const getIieHealth = () => intelligenceFetch('/iie/health');
export const getIieDashboard = () => intelligenceFetch('/iie/dashboard');
export const analyseIieCompany = (key) => {
  const qs = new URLSearchParams({ key }).toString();
  return intelligenceFetch(`/iie/analyse?${qs}`, { method: 'POST', body: {} });
};
export const runIieBatch = (limit = 20) => {
  const qs = new URLSearchParams({ limit: String(limit) }).toString();
  return intelligenceFetch(`/iie/batch?${qs}`, { method: 'POST', body: {} });
};
export const getIieCompany = (key) => intelligenceFetch(`/iie/company/${encodeURIComponent(key)}`);
export const getIieSectors = () => intelligenceFetch('/iie/sector');
export const getIieSector = (id) => intelligenceFetch(`/iie/sector/${encodeURIComponent(id)}`);
export const getIieThemes = () => intelligenceFetch('/iie/theme');
export const getIieTheme = (id) => intelligenceFetch(`/iie/theme/${encodeURIComponent(id)}`);
export const getIieThesis = (key) => intelligenceFetch(`/iie/thesis/${encodeURIComponent(key)}`);
export const getIieScenario = (key) => intelligenceFetch(`/iie/scenario/${encodeURIComponent(key)}`);
export const getIieCatalysts = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/iie/catalysts${qs ? `?${qs}` : ''}`);
};
export const getIieRisks = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/iie/risks${qs ? `?${qs}` : ''}`);
};
export const getIieOpportunities = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/iie/opportunities${qs ? `?${qs}` : ''}`);
};
export const compareIie = (companies, dimensions) => {
  const qs = new URLSearchParams({ companies: Array.isArray(companies) ? companies.join(',') : companies });
  if (dimensions) qs.set('dimensions', Array.isArray(dimensions) ? dimensions.join(',') : dimensions);
  return intelligenceFetch(`/iie/compare?${qs}`);
};
export const getIieMonitor = (key) => intelligenceFetch(`/iie/monitor/${encodeURIComponent(key)}`);
export const getIieDna = (key) => intelligenceFetch(`/iie/dna/${encodeURIComponent(key)}`);
export const getIieMacro = (event) => {
  const qs = new URLSearchParams({ event }).toString();
  return intelligenceFetch(`/iie/macro?${qs}`);
};
export const getIieEvolution = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/iie/evolution${qs ? `?${qs}` : ''}`);
};
export const searchIie = (q, limit = 20) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/iie/search?${qs}`);
};
export const consultIie = (q, limit = 8) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/iie/consult?${qs}`);
};

/** FAA v1 Finance Acquisition Agent — gather public docs, feed FRE */
export const getFaaHealth = () => intelligenceFetch('/faa/health');
export const getFaaDashboard = () => intelligenceFetch('/faa/dashboard');
export const discoverFaa = (q, limit = 40) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/faa/discover?${qs}`);
};
export const acquireFaa = (q, limit = 24) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/faa/acquire?${qs}`, { method: 'POST', body: {} });
};
export const getFaaConnectors = () => intelligenceFetch('/faa/connectors');
export const getFaaScheduler = () => intelligenceFetch('/faa/scheduler');
export const runFaaJobs = () => intelligenceFetch('/faa/jobs', { method: 'POST', body: {} });
export const consultFaa = (q, limit = 8) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/faa/consult?${qs}`);
};

/** FRE v1 Finance Retrieval Engine — evidence only, never answers */
export const getFreHealth = () => intelligenceFetch('/fre/health');
export const getFreDashboard = () => intelligenceFetch('/fre/dashboard');
export const queryFre = (q, params = {}) => {
  const qs = new URLSearchParams({
    q,
    ...Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    ),
  }).toString();
  return intelligenceFetch(`/fre/query?${qs}`);
};
export const searchFre = (q, params = {}) => {
  const qs = new URLSearchParams({
    q,
    ...Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    ),
  }).toString();
  return intelligenceFetch(`/fre/search?${qs}`);
};
export const getFreCompany = (key, limit = 20) => {
  const qs = new URLSearchParams({ limit: String(limit) }).toString();
  return intelligenceFetch(`/fre/company/${encodeURIComponent(key)}?${qs}`);
};
export const getFreDocument = (id) => intelligenceFetch(`/fre/document/${encodeURIComponent(id)}`);
export const getFreEvidence = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/fre/evidence${qs ? `?${qs}` : ''}`);
};
export const getFreTimeline = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/fre/timeline${qs ? `?${qs}` : ''}`);
};
export const getFreNews = (limit = 20) => {
  const qs = new URLSearchParams({ limit: String(limit) }).toString();
  return intelligenceFetch(`/fre/news?${qs}`);
};
export const getFreGraph = (entity) => {
  const qs = entity ? new URLSearchParams({ entity }).toString() : '';
  return intelligenceFetch(`/fre/graph${qs ? `?${qs}` : ''}`);
};
export const ingestFre = (payload) => intelligenceFetch('/fre/ingest', { method: 'POST', body: payload || {} });
export const runFreJobs = () => intelligenceFetch('/fre/jobs', { method: 'POST', body: {} });
export const consultFre = (q, limit = 8) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/fre/consult?${qs}`);
};
export const getFreScheduler = () => intelligenceFetch('/fre/scheduler');

/** FLE v1 Forecasting & Learning */
export const getFleHealth = () => intelligenceFetch('/fle/health');
export const getFleDashboard = () => intelligenceFetch('/fle/dashboard');
export const listFleForecasts = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/fle/forecast${qs ? `?${qs}` : ''}`);
};
export const createFleForecast = (payload) =>
  intelligenceFetch('/fle/forecast', { method: 'POST', body: payload || {} });
export const getFleForecast = (id) => intelligenceFetch(`/fle/forecast/${encodeURIComponent(id)}`);
export const resolveFleForecast = (id, payload) =>
  intelligenceFetch(`/fle/forecast/${encodeURIComponent(id)}/resolve`, {
    method: 'POST',
    body: payload || {},
  });
export const versionFleForecast = (id, payload) =>
  intelligenceFetch(`/fle/forecast/${encodeURIComponent(id)}/version`, {
    method: 'POST',
    body: payload || {},
  });
export const compareFleForecast = (id) => intelligenceFetch(`/fle/compare/${encodeURIComponent(id)}`);
export const getFleCompany = (key) => intelligenceFetch(`/fle/company/${encodeURIComponent(key)}`);
export const getFleOutcomes = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/fle/outcomes${qs ? `?${qs}` : ''}`);
};
export const getFleLearning = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/fle/learning${qs ? `?${qs}` : ''}`);
};
export const getFleCalibration = () => intelligenceFetch('/fle/calibration');
export const getFleScenarios = (id) => intelligenceFetch(`/fle/scenarios/${encodeURIComponent(id)}`);
export const getFleAccuracy = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/fle/accuracy${qs ? `?${qs}` : ''}`);
};
export const getFleHistory = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/fle/history${qs ? `?${qs}` : ''}`);
};
export const generateFleForecasts = (key) => {
  const qs = new URLSearchParams({ key }).toString();
  return intelligenceFetch(`/fle/generate?${qs}`, { method: 'POST', body: {} });
};
export const runFleBatch = (limit = 20) => {
  const qs = new URLSearchParams({ limit: String(limit) }).toString();
  return intelligenceFetch(`/fle/batch?${qs}`, { method: 'POST', body: {} });
};
export const runFleJobs = () => intelligenceFetch('/fle/jobs', { method: 'POST', body: {} });
export const searchFle = (q, limit = 20) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/fle/search?${qs}`);
};
export const consultFle = (q, limit = 8) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/fle/consult?${qs}`);
};

/** MEE v1 Market Event Engine */
export const getMeeHealth = () => intelligenceFetch('/mee/health');
export const getMeeDashboard = () => intelligenceFetch('/mee/dashboard');
export const listMeeEvents = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/mee/events${qs ? `?${qs}` : ''}`);
};
export const createMeeEvent = (payload) =>
  intelligenceFetch('/mee/events', { method: 'POST', body: payload || {} });
export const getMeeEvent = (id) => intelligenceFetch(`/mee/events/${encodeURIComponent(id)}`);
export const verifyMeeEvent = (id) =>
  intelligenceFetch(`/mee/events/${encodeURIComponent(id)}/verify`, { method: 'POST', body: {} });
export const versionMeeEvent = (id, payload) =>
  intelligenceFetch(`/mee/events/${encodeURIComponent(id)}/version`, {
    method: 'POST',
    body: payload || {},
  });
export const getMeeCompany = (key) => intelligenceFetch(`/mee/company/${encodeURIComponent(key)}`);
export const getMeeSector = (id) => intelligenceFetch(`/mee/sector/${encodeURIComponent(id)}`);
export const getMeeTheme = (id) => intelligenceFetch(`/mee/theme/${encodeURIComponent(id)}`);
export const getMeeTimeline = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/mee/timeline${qs ? `?${qs}` : ''}`);
};
export const getMeeImpact = (id) => intelligenceFetch(`/mee/impact/${encodeURIComponent(id)}`);
export const getMeeRelationships = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/mee/relationships${qs ? `?${qs}` : ''}`);
};
export const getMeeHistory = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/mee/history${qs ? `?${qs}` : ''}`);
};
export const getMeeSimilar = (id, limit = 8) => {
  const qs = new URLSearchParams({ limit: String(limit) }).toString();
  return intelligenceFetch(`/mee/similar/${encodeURIComponent(id)}?${qs}`);
};
export const runMeeCycle = (limit = 40) => {
  const qs = new URLSearchParams({ limit: String(limit) }).toString();
  return intelligenceFetch(`/mee/cycle?${qs}`, { method: 'POST', body: {} });
};
export const searchMee = (q, limit = 20) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/mee/search?${qs}`);
};
export const consultMee = (q, limit = 8) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/mee/consult?${qs}`);
};

/** CAE v1 Context Assembly */
export const getCaeHealth = () => intelligenceFetch('/cae/health');
export const getCaeDashboard = () => intelligenceFetch('/cae/dashboard');
export const getCaeContext = (q, params = {}) => {
  const qs = new URLSearchParams({
    q,
    ...Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    ),
  }).toString();
  return intelligenceFetch(`/cae/context?${qs}`);
};
export const getCaeQueryPlan = (q, ticker) => {
  const qs = new URLSearchParams({ q });
  if (ticker) qs.set('ticker', ticker);
  return intelligenceFetch(`/cae/query-plan?${qs}`);
};
export const getCaeRetrieval = (q, ticker) => {
  const qs = new URLSearchParams({ q });
  if (ticker) qs.set('ticker', ticker);
  return intelligenceFetch(`/cae/retrieval?${qs}`);
};
export const getCaeCache = () => intelligenceFetch('/cae/cache');
export const clearCaeCache = () => intelligenceFetch('/cae/cache/clear', { method: 'POST', body: {} });
export const getCaeMetrics = () => intelligenceFetch('/cae/metrics');
export const explainCaePackage = (id) => intelligenceFetch(`/cae/explain/${encodeURIComponent(id)}`);
export const getCaePackage = (id) => intelligenceFetch(`/cae/package/${encodeURIComponent(id)}`);
export const searchCae = (q, limit = 20) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/cae/search?${qs}`);
};

/** IB v1 Intelligence Bus */
export const getIbHealth = () => intelligenceFetch('/ib/health');
export const getIbDashboard = () => intelligenceFetch('/ib/dashboard');
export const getIbEvents = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/ib/events${qs ? `?${qs}` : ''}`);
};
export const publishIbEvent = (body = {}) =>
  intelligenceFetch('/ib/publish', { method: 'POST', body });
export const getIbSubscriptions = () => intelligenceFetch('/ib/subscriptions');
export const createIbSubscription = (body = {}) =>
  intelligenceFetch('/ib/subscriptions', { method: 'POST', body });
export const replayIbEvents = (body = {}) =>
  intelligenceFetch('/ib/replay', { method: 'POST', body });
export const getIbHistory = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/ib/history${qs ? `?${qs}` : ''}`);
};
export const getIbMetrics = () => intelligenceFetch('/ib/metrics');
export const getIbTraces = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/ib/traces${qs ? `?${qs}` : ''}`);
};
export const getIbDeadLetter = (limit = 50) => {
  const qs = new URLSearchParams({ limit: String(limit) }).toString();
  return intelligenceFetch(`/ib/dead-letter?${qs}`);
};
export const resolveIbDeadLetter = (id) =>
  intelligenceFetch(`/ib/dead-letter/${encodeURIComponent(id)}/resolve`, {
    method: 'POST',
    body: {},
  });
export const getIbSchema = (eventType) => {
  const qs = new URLSearchParams();
  if (eventType) qs.set('event_type', eventType);
  const s = qs.toString();
  return intelligenceFetch(`/ib/schema${s ? `?${s}` : ''}`);
};
export const runIbDemoChain = (companySymbol = 'INFY') => {
  const qs = new URLSearchParams({ company_symbol: companySymbol }).toString();
  return intelligenceFetch(`/ib/demo-chain?${qs}`, { method: 'POST', body: {} });
};

/** VE v1 Valuation Engine */
export const getVeHealth = () => intelligenceFetch('/ve/health');
export const getVeDashboard = () => intelligenceFetch('/ve/dashboard');
export const getVeCompany = (key, params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/ve/company/${encodeURIComponent(key)}${qs ? `?${qs}` : ''}`);
};
export const getVeModel = (model, key, marketPrice) => {
  const qs = new URLSearchParams({ model, key });
  if (marketPrice != null) qs.set('market_price', String(marketPrice));
  return intelligenceFetch(`/ve/model?${qs}`);
};
export const getVeHistory = (key, limit = 50) => {
  const qs = new URLSearchParams({ key, limit: String(limit) }).toString();
  return intelligenceFetch(`/ve/history?${qs}`);
};
export const getVeScenarios = (key) => {
  const qs = new URLSearchParams({ key }).toString();
  return intelligenceFetch(`/ve/scenarios?${qs}`);
};
export const getVeCompare = (key, peers) => {
  const qs = new URLSearchParams({ key });
  if (peers) qs.set('peers', Array.isArray(peers) ? peers.join(',') : String(peers));
  return intelligenceFetch(`/ve/compare?${qs}`);
};
export const getVeSensitivity = (key) => {
  const qs = new URLSearchParams({ key }).toString();
  return intelligenceFetch(`/ve/sensitivity?${qs}`);
};
export const searchVe = (q, limit = 20) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/ve/search?${qs}`);
};
export const consultVe = (q, limit = 8) => {
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return intelligenceFetch(`/ve/consult?${qs}`);
};
export const valueVeCompany = (body = {}) =>
  intelligenceFetch('/ve/value', { method: 'POST', body });
export const getVeValuation = (id) =>
  intelligenceFetch(`/ve/valuation/${encodeURIComponent(id)}`);

/** FIML v1 — Financial Intelligence Model Library */
export const getFimlHealth = () => intelligenceFetch('/fiml/health');
export const getFimlDashboard = () => intelligenceFetch('/fiml/dashboard');
export const getFimlModels = () => intelligenceFetch('/fiml/models');
export const getFimlIndustries = () => intelligenceFetch('/fiml/industries');
export const getFimlMetrics = () => intelligenceFetch('/fiml/metrics');
export const getFimlGraph = () => intelligenceFetch('/fiml/graph');
export const searchFiml = (q, domain, limit = 20) => {
  const qs = new URLSearchParams({ q, limit: String(limit) });
  if (domain) qs.set('domain', domain);
  return intelligenceFetch(`/fiml/search?${qs}`);
};
export const analyseFiml = (domain, body = {}) =>
  intelligenceFetch(`/fiml/analyse/${encodeURIComponent(domain)}`, { method: 'POST', body });
export const scoreFiml = (domain, body = {}) =>
  intelligenceFetch(`/fiml/score/${encodeURIComponent(domain)}`, { method: 'POST', body });
export const explainFiml = (domain, body = {}) =>
  intelligenceFetch(`/fiml/explain/${encodeURIComponent(domain)}`, { method: 'POST', body });
export const compareFiml = (domain, body = {}) =>
  intelligenceFetch(`/fiml/compare/${encodeURIComponent(domain)}`, { method: 'POST', body });
export const bundleFiml = (body = {}) =>
  intelligenceFetch('/fiml/bundle', { method: 'POST', body });
export const consumerFiml = (engine, body = {}) =>
  intelligenceFetch(`/fiml/consumer/${encodeURIComponent(engine)}`, { method: 'POST', body });

/** AGI Finance Academy v1.1 — institutional multi-course curriculum library */
export const getAcademyHealth = () => intelligenceFetch('/academy/health');
export const getAcademyDashboard = () => intelligenceFetch('/academy/dashboard');
export const getAcademyCourses = () => intelligenceFetch('/academy/courses');
export const getAcademyCourse = (courseId) => {
  const qs = new URLSearchParams();
  if (courseId) qs.set('course_id', courseId);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/academy/course${suffix}`);
};
export const getAcademyConcepts = (tag, courseId) => {
  const qs = new URLSearchParams();
  if (tag) qs.set('tag', tag);
  if (courseId) qs.set('course_id', courseId);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/academy/concepts${suffix}`);
};
export const getAcademyConcept = (id) =>
  intelligenceFetch(`/academy/concepts/${encodeURIComponent(id)}`);
export const teachAcademyConcept = (id) =>
  intelligenceFetch(`/academy/teach/${encodeURIComponent(id)}`);
export const getAcademyGraph = (courseId) => {
  const qs = new URLSearchParams();
  if (courseId) qs.set('course_id', courseId);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/academy/graph${suffix}`);
};
export const getAcademyCausalModels = () => intelligenceFetch('/academy/causal-models');
export const getAcademyMentalModels = () => intelligenceFetch('/academy/mental-models');
export const getAcademyQuality = (courseId) => {
  const qs = new URLSearchParams();
  if (courseId) qs.set('course_id', courseId);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/academy/quality${suffix}`);
};
export const getAcademyProvenance = () => intelligenceFetch('/academy/provenance');
export const getAcademyExams = (courseId) => {
  const qs = new URLSearchParams();
  if (courseId) qs.set('course_id', courseId);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/academy/exams${suffix}`);
};
export const getAcademyExamAnswer = (id) =>
  intelligenceFetch(`/academy/exams/${encodeURIComponent(id)}`);
export const getAcademyCompletion = (courseId) => {
  const qs = new URLSearchParams();
  if (courseId) qs.set('course_id', courseId);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/academy/completion${suffix}`);
};
export const getAcademyRedFlags = () => intelligenceFetch('/academy/red-flags');
export const getAcademyAccounting = () => intelligenceFetch('/academy/accounting');
export const getAcademyCorporateFinance = () => intelligenceFetch('/academy/corporate-finance');
export const scoreAcademyEarningsQuality = (body = {}) =>
  intelligenceFetch('/academy/earnings-quality', { method: 'POST', body });
export const scoreAcademyRedFlags = (body = {}) =>
  intelligenceFetch('/academy/red-flags/score', { method: 'POST', body });
export const searchAcademy = (q, limit = 20, courseId) => {
  const qs = new URLSearchParams({ q, limit: String(limit) });
  if (courseId) qs.set('course_id', courseId);
  return intelligenceFetch(`/academy/search?${qs}`);
};
export const consumerAcademy = (engine, body = {}) =>
  intelligenceFetch(`/academy/consumer/${encodeURIComponent(engine)}`, { method: 'POST', body });
export const getAcademyProduction = () => intelligenceFetch('/academy/production');
export const getAcademyProductionAb = (question) => {
  const qs = question ? `?question=${encodeURIComponent(question)}` : '';
  return intelligenceFetch(`/academy/production/ab${qs}`);
};
export const getAcademyProductionQualityGates = () =>
  intelligenceFetch('/academy/production/quality-gates');
export const packageAcademyProduction = (query, engine = 'cae', ticker) => {
  const qs = new URLSearchParams({ query: query || '', engine });
  if (ticker) qs.set('ticker', ticker);
  return intelligenceFetch(`/academy/production/package?${qs}`, { method: 'POST', body: {} });
};
export const getAcademyBooksHealth = () => intelligenceFetch('/academy/books/health');
export const getAcademyBooksDashboard = () => intelligenceFetch('/academy/books/dashboard');
export const getAcademyBooksQualityGates = () => intelligenceFetch('/academy/books/quality-gates');
export const getAcademyBooksGraph = () => intelligenceFetch('/academy/books/graph');
export const ingestAcademyBook = (body = {}) =>
  intelligenceFetch('/academy/books/ingest', { method: 'POST', body });
export const packageAcademyBooks = (query, ticker) => {
  const qs = new URLSearchParams({ query: query || '' });
  if (ticker) qs.set('ticker', ticker);
  return intelligenceFetch(`/academy/books/package?${qs}`, { method: 'POST', body: {} });
};
export const attachAcademyBooksKf = () =>
  intelligenceFetch('/academy/books/attach-kf', { method: 'POST', body: {} });
export const getAcademyBooksLibrary = () => intelligenceFetch('/academy/books/library');
export const getAcademyBooksIngestionReport = () =>
  intelligenceFetch('/academy/books/ingestion-report');
export const ingestAcademyBooksLibrary = (body = {}) =>
  intelligenceFetch('/academy/books/ingest-library', { method: 'POST', body });

/** CMS article learning — bulk read uploaded articles into KIP/KF/KC with learning dates */
export const learnCmsArticles = (body = {}) =>
  intelligenceFetch('/cms/learn-articles', { method: 'POST', body });
export const getCmsLearningStatus = (days = 14) =>
  intelligenceFetch(`/cms/learning-status?days=${encodeURIComponent(String(days))}`);
export const getCmsLearningSummary = (days = 5) =>
  intelligenceFetch(`/cms/learning-summary?days=${encodeURIComponent(String(days))}`);
export const getSifHealth = () => intelligenceFetch('/sif/health');
export const getSifDashboard = () => intelligenceFetch('/sif/dashboard');
export const getSifFrameworks = () => intelligenceFetch('/sif/frameworks');
export const getSifFramework = (sectorId) =>
  intelligenceFetch(`/sif/frameworks/${encodeURIComponent(sectorId)}`);
export const getSifQualityGates = () => intelligenceFetch('/sif/quality-gates');
export const analyseSif = (query, ticker, engine = 'ask_agi') => {
  const qs = new URLSearchParams({ query: query || '', engine });
  if (ticker) qs.set('ticker', ticker);
  return intelligenceFetch(`/sif/analyse?${qs}`, { method: 'POST', body: {} });
};
export const getLeoHealth = () => intelligenceFetch('/leo/health');
export const getLeoDashboard = () => intelligenceFetch('/leo/dashboard');
export const getLeoQualityGates = () => intelligenceFetch('/leo/quality-gates');
export const getLeoDossier = (ticker) =>
  intelligenceFetch(`/leo/dossier/${encodeURIComponent(ticker)}`);
export const packageLeo = (query, ticker, engine = 'ask_agi') => {
  const qs = new URLSearchParams({ query: query || '', engine });
  if (ticker) qs.set('ticker', ticker);
  return intelligenceFetch(`/leo/package?${qs}`, { method: 'POST', body: {} });
};
export const getCidHealth = () => intelligenceFetch('/company-dossier/health');
export const getCidDashboard = () => intelligenceFetch('/company-dossier');
export const getCidQualityGates = () => intelligenceFetch('/company-dossier/quality-gates');
export const getCompanyDossier = (ticker) =>
  intelligenceFetch(`/company-dossier/${encodeURIComponent(ticker)}`);
export const getCompanyDossierTimeline = (ticker, limit = 100) =>
  intelligenceFetch(`/company-dossier/${encodeURIComponent(ticker)}/timeline?limit=${limit}`);
export const getCompanyDossierCoverage = (ticker) =>
  intelligenceFetch(`/company-dossier/${encodeURIComponent(ticker)}/coverage`);
export const getCompanyDossierValuation = (ticker) =>
  intelligenceFetch(`/company-dossier/${encodeURIComponent(ticker)}/valuation`);
export const getCompanyDossierRisk = (ticker) =>
  intelligenceFetch(`/company-dossier/${encodeURIComponent(ticker)}/risk`);
export const getCompanyDossierForecast = (ticker) =>
  intelligenceFetch(`/company-dossier/${encodeURIComponent(ticker)}/forecast`);
export const getCompanyDossierDocuments = (ticker) =>
  intelligenceFetch(`/company-dossier/${encodeURIComponent(ticker)}/documents`);
export const getYfpHealth = () => intelligenceFetch('/yfp/health');
export const getYfpDashboard = () => intelligenceFetch('/yfp/dashboard');
export const getYfpQualityGates = () => intelligenceFetch('/yfp/quality-gates');
export const searchYfp = (q, limit = 8) =>
  intelligenceFetch(`/yfp/search?q=${encodeURIComponent(q || '')}&limit=${limit}`);
export const enrichYfp = (ticker) =>
  intelligenceFetch(`/yfp/enrich/${encodeURIComponent(ticker)}`, { method: 'POST', body: {} });
export const getDvcHealth = () => intelligenceFetch('/dvc/health');
export const getDvcDashboard = () => intelligenceFetch('/dvc/dashboard');
export const getDvcQualityGates = () => intelligenceFetch('/dvc/quality-gates');
export const getDvcMetrics = () => intelligenceFetch('/dvc/metrics');
export const getDvcCompany = (ticker) =>
  intelligenceFetch(`/dvc/company/${encodeURIComponent(ticker)}`);
export const getDvcConflicts = (limit = 40, severity) => {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (severity) qs.set('severity', severity);
  return intelligenceFetch(`/dvc/conflicts?${qs}`);
};
export const validateDvc = (ticker) =>
  intelligenceFetch(`/dvc/validate/${encodeURIComponent(ticker)}`, { method: 'POST', body: {} });
export const enrichDvc = (ticker) =>
  intelligenceFetch(`/dvc/enrich/${encodeURIComponent(ticker)}`, { method: 'POST', body: {} });
export const getEcpHealth = () => intelligenceFetch('/ecp/health');
export const getEcpDashboard = () => intelligenceFetch('/ecp/dashboard');
export const getEcpQualityGates = () => intelligenceFetch('/ecp/quality-gates');
export const getEcpReports = (limit = 30) =>
  intelligenceFetch(`/ecp/reports?limit=${limit}`);
export const getEcpReport = (ticker) =>
  intelligenceFetch(`/ecp/report/${encodeURIComponent(ticker)}`);
export const completeEcp = (ticker, q = 'Should I buy?') => {
  const qs = new URLSearchParams({
    ticker: ticker || '',
    q: q || 'Should I buy?',
  });
  return intelligenceFetch(`/ecp/complete?${qs}`, { method: 'POST', body: {} });
};

/** Knowledge Factory — Decision Coverage / HD / ISI / IMI */
export const getKnowledgeFactoryDailyHealth = () =>
  intelligenceFetch('/knowledge-factory/daily-health', { timeoutMs: 120_000 });
export const getKnowledgeFactoryDecisionCoverage = () =>
  intelligenceFetch('/knowledge-factory/decision-coverage', { timeoutMs: 90_000 });
export const getHistoricalDepthDashboard = () =>
  intelligenceFetch('/knowledge-factory/historical-depth', { timeoutMs: 120_000 });
export const runHistoricalDepth = () =>
  intelligenceFetch('/knowledge-factory/historical-depth/run', { method: 'POST', body: {}, timeoutMs: 180_000 });
export const getSectorIntelligenceDashboard = () =>
  intelligenceFetch('/knowledge-factory/sector-intelligence', { timeoutMs: 120_000 });
export const runSectorIntelligence = () =>
  intelligenceFetch('/knowledge-factory/sector-intelligence/run', { method: 'POST', body: {}, timeoutMs: 180_000 });
export const getMacroIntelligenceDashboard = () =>
  intelligenceFetch('/knowledge-factory/macro-intelligence', { timeoutMs: 120_000 });
export const runMacroIntelligence = () =>
  intelligenceFetch('/knowledge-factory/macro-intelligence/run', { method: 'POST', body: {}, timeoutMs: 180_000 });

/** Institutional Decision Quality (observability) */
export const getDecisionQualityHealth = () =>
  intelligenceFetch('/decision-quality/health', { timeoutMs: 30_000 });
export const getDecisionQualityDashboard = () =>
  intelligenceFetch('/decision-quality/dashboard', { timeoutMs: 120_000 });
export const runDecisionQuality = () =>
  intelligenceFetch('/decision-quality/run', { method: 'POST', body: {}, timeoutMs: 120_000 });
export const getDecisionQualityHall = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return intelligenceFetch(`/decision-quality/hall${qs ? `?${qs}` : ''}`, { timeoutMs: 60_000 });
};
export const getDecisionQualityCalibration = () =>
  intelligenceFetch('/decision-quality/calibration', { timeoutMs: 60_000 });

/** AGIB v1.2 — Institutional Universe Intelligence (soft registry) */
export const getUniverseIntelligenceHealth = () =>
  intelligenceFetch('/universe-intelligence/health', { timeoutMs: 30_000 });
export const getUniverseIntelligenceDashboard = (universeId = 'NIFTY_500') =>
  intelligenceFetch(
    `/universe-intelligence/dashboard?universe_id=${encodeURIComponent(universeId)}`,
    { timeoutMs: 180_000 }
  );
export const runUniverseIntelligence = (body = {}) =>
  intelligenceFetch('/universe-intelligence/run', {
    method: 'POST',
    body: body || {},
    timeoutMs: 300_000,
  });
export const getUniverseIntelligenceIci = (ticker) =>
  intelligenceFetch(`/universe-intelligence/ici/${encodeURIComponent(ticker)}`, {
    timeoutMs: 60_000,
  });

/** AGIB v2.0 — Unified Institutional Knowledge Stack (Sprints 1–7) */
export const getInstitutionalKnowledgeHealth = () =>
  intelligenceFetch('/institutional-knowledge/health', { timeoutMs: 30_000 });
export const getInstitutionalKnowledgeDashboard = (ensure = false) =>
  intelligenceFetch(`/institutional-knowledge/dashboard${ensure ? '?ensure=true' : ''}`, {
    timeoutMs: 180_000,
  });
export const runInstitutionalKnowledgeStack = (body = {}) =>
  intelligenceFetch('/institutional-knowledge/run', {
    method: 'POST',
    body: body || {},
    timeoutMs: 600_000,
  });
export const getInstitutionalKnowledgeCompany = (ticker) =>
  intelligenceFetch(`/institutional-knowledge/company/${encodeURIComponent(ticker)}`, {
    timeoutMs: 120_000,
  });
export const getCompanyIntelligenceDashboard = () =>
  intelligenceFetch('/company-intelligence/dashboard', { timeoutMs: 120_000 });
export const getRelationshipDashboard = () =>
  intelligenceFetch('/relationship/dashboard', { timeoutMs: 120_000 });
export const getAlternativeDataDashboard = () =>
  intelligenceFetch('/alternative-data/dashboard', { timeoutMs: 120_000 });
export const getExpectationsDashboard = () =>
  intelligenceFetch('/expectations/dashboard', { timeoutMs: 120_000 });
export const getIndustryDashboard = () =>
  intelligenceFetch('/industry/dashboard', { timeoutMs: 120_000 });
export const getGovernmentDashboard = () =>
  intelligenceFetch('/government/dashboard', { timeoutMs: 120_000 });

/** Mission Control V1 — snapshot-backed ops cockpit (HTTP never rebuilds) */
export const getMissionControlHealth = () =>
  intelligenceFetch('/mission-control/health', { timeoutMs: 15_000 });
export const getMissionControlDashboard = () =>
  intelligenceFetch('/mission-control/dashboard', { timeoutMs: 30_000 });
export const getMissionControlAgentMap = () =>
  intelligenceFetch('/mission-control/agent-map', { timeoutMs: 15_000 });
export const getIntelligenceMapSnapshot = () =>
  intelligenceFetch('/mission-control/intelligence-map', { timeoutMs: 15_000 });
export const getInstitutionalIntelligenceSnapshot = () =>
  intelligenceFetch('/mission-control/institutional-intelligence', { timeoutMs: 15_000 });
export const getContinuousGatherLearnHealth = () =>
  intelligenceFetch('/continuous-gather-learn/health', { timeoutMs: 30_000 });
export const getContinuousGatherLearnDashboard = () =>
  intelligenceFetch('/continuous-gather-learn/dashboard', { timeoutMs: 60_000 });
export const runContinuousGatherLearn = (body = {}) =>
  intelligenceFetch('/continuous-gather-learn/run', {
    method: 'POST',
    body,
    timeoutMs: 300_000,
  });
export const getMissionControlQualityGates = () =>
  intelligenceFetch('/mission-control/quality-gates', { timeoutMs: 15_000 });
export const getMissionControlAskObservability = (limit = 25) =>
  intelligenceFetch(`/mission-control/ask-observability?limit=${limit}`, { timeoutMs: 15_000 });
export const getMissionControlReport = () =>
  intelligenceFetch('/mission-control/report', { timeoutMs: 30_000 });
export const rebuildMissionControlSnapshot = (body = {}) =>
  intelligenceFetch('/mission-control/rebuild', {
    method: 'POST',
    body,
    timeoutMs: 15_000,
  });
export const acknowledgeMissionControlAlert = (alertId) =>
  intelligenceFetch('/mission-control/acknowledge', {
    method: 'POST',
    body: { alert_id: alertId },
    timeoutMs: 30_000,
  });

/** Soft public/admin live inventory — never throws to callers if wrapped. */
export const getIntelligenceLiveStatus = () => intelligenceFetch('/live-status');
export const getIntelligenceStack = () => intelligenceFetch('/system/intelligence-stack');
export const getIiexHealth = () => intelligenceFetch('/iiex/health');
export const getMkfiHealth = () => intelligenceFetch('/mkfi/health');

/** Investment Office V1 — executive operating cockpit */
export const getInvestmentOfficeHealth = () => intelligenceFetch('/investment-office/health');
export const getInvestmentOfficeDashboard = () => intelligenceFetch('/investment-office/dashboard');
export const getInvestmentOfficeQualityGates = () =>
  intelligenceFetch('/investment-office/quality-gates');
export const getInvestmentOfficeCompany = (ticker, params = {}) => {
  const q = new URLSearchParams();
  if (params.question) q.set('question', params.question);
  if (params.package_type) q.set('package_type', params.package_type);
  const qs = q.toString();
  return intelligenceFetch(
    `/investment-office/company/${encodeURIComponent(ticker)}${qs ? `?${qs}` : ''}`
  );
};
export const postInvestmentOfficeQuery = (body) =>
  intelligenceFetch('/investment-office/query', {
    method: 'POST',
    body: body || {},
  });
export const packageInvestmentOffice = (query = '', ticker) =>
  intelligenceFetch('/investment-office/package', {
    method: 'POST',
    body: { query, ticker },
  });

/** AGI V1.3.1 — Morning Office reads precomputed snapshot (fast). Refresh is async. */
const IO_SNAPSHOT_TIMEOUT_MS = 30_000;
export const getInvestmentOfficeOverview = () =>
  intelligenceFetch('/investment-office/overview', { timeoutMs: IO_SNAPSHOT_TIMEOUT_MS });
export const getInvestmentOfficeMorningOffice = () =>
  intelligenceFetch('/investment-office/morning-office', { timeoutMs: IO_SNAPSHOT_TIMEOUT_MS });
export const getInvestmentOfficeDailyBrief = () =>
  intelligenceFetch('/investment-office/daily-brief', { timeoutMs: IO_SNAPSHOT_TIMEOUT_MS });
export const getInvestmentOfficeResearchQueue = () =>
  intelligenceFetch('/investment-office/research-queue', { timeoutMs: IO_SNAPSHOT_TIMEOUT_MS });
export const getInvestmentOfficeOpportunities = () =>
  intelligenceFetch('/investment-office/opportunities', { timeoutMs: IO_SNAPSHOT_TIMEOUT_MS });
export const getInvestmentOfficeMarketSummary = () =>
  intelligenceFetch('/investment-office/market-summary', { timeoutMs: IO_SNAPSHOT_TIMEOUT_MS });
export const getInvestmentOfficeMacro = () =>
  intelligenceFetch('/investment-office/macro', { timeoutMs: IO_SNAPSHOT_TIMEOUT_MS });
export const getInvestmentOfficeCalendar = () =>
  intelligenceFetch('/investment-office/calendar', { timeoutMs: IO_SNAPSHOT_TIMEOUT_MS });
export const getInvestmentOfficePortfolioMonitor = () =>
  intelligenceFetch('/investment-office/portfolio-monitor', { timeoutMs: IO_SNAPSHOT_TIMEOUT_MS });
export const getInvestmentOfficeSectorMonitor = () =>
  intelligenceFetch('/investment-office/sector-monitor', { timeoutMs: IO_SNAPSHOT_TIMEOUT_MS });
export const getInvestmentOfficeMetrics = () =>
  intelligenceFetch('/investment-office/metrics', { timeoutMs: IO_SNAPSHOT_TIMEOUT_MS });
export const getInvestmentOfficeSnapshot = () =>
  intelligenceFetch('/investment-office/snapshot', { timeoutMs: 15_000 });
export const getInvestmentOfficeSystemHealth = () =>
  intelligenceFetch('/investment-office/system-health', { timeoutMs: 15_000 });
export const refreshInvestmentOfficeMorning = (body = {}) =>
  intelligenceFetch('/investment-office/refresh', {
    method: 'POST',
    body: body || {},
    timeoutMs: 60_000,
  });
export const generateInvestmentOfficeMorningBrief = (body = {}) =>
  intelligenceFetch('/investment-office/generate-morning-brief', {
    method: 'POST',
    body: body || {},
    timeoutMs: 60_000,
  });

/** CIO-01 — Comparative Intelligence Office */
export const getComparativeIntelligenceHealth = () =>
  intelligenceFetch('/comparative-intelligence/health');
export const getComparativeIntelligenceDashboard = () =>
  intelligenceFetch('/comparative-intelligence/dashboard');
export const postComparativeIntelligenceCompare = (body) =>
  intelligenceFetch('/comparative-intelligence/compare', {
    method: 'POST',
    body: body || {},
  });
export const postComparativeIntelligenceQuery = (body) =>
  intelligenceFetch('/comparative-intelligence/query', {
    method: 'POST',
    body: body || {},
  });

/** Office SDK — shared application office contract */
export const getOfficeSdkHealth = () => intelligenceFetch('/office-sdk/health');
export const getOfficeSdkDashboard = () => intelligenceFetch('/office-sdk/dashboard');
export const getOfficeSdkCatalog = () => intelligenceFetch('/office-sdk/catalog');
export const getOfficeSdkDomains = () => intelligenceFetch('/office-sdk/domains');
export const postOfficeSdkInvoke = (body) =>
  intelligenceFetch('/office-sdk/invoke', {
    method: 'POST',
    body: body || {},
  });

/** PO-01 — Portfolio Office (canonical state; /portfolio-office avoids IPO /portfolio collision) */
export const getPortfolioOfficeHealth = () => intelligenceFetch('/portfolio-office/health');
export const getPortfolioOfficeDashboard = () => intelligenceFetch('/portfolio-office/dashboard');
export const getPortfolioOfficePortfolio = (portfolioId) =>
  intelligenceFetch(`/portfolio-office/${encodeURIComponent(portfolioId)}`);
export const getPortfolioOfficeHoldings = (portfolioId) =>
  intelligenceFetch(`/portfolio-office/${encodeURIComponent(portfolioId)}/holdings`);
export const getPortfolioOfficeExposures = (portfolioId) =>
  intelligenceFetch(`/portfolio-office/${encodeURIComponent(portfolioId)}/exposures`);
export const getPortfolioOfficeQuality = (portfolioId) =>
  intelligenceFetch(`/portfolio-office/${encodeURIComponent(portfolioId)}/quality`);
export const getPortfolioOfficeConcentration = (portfolioId) =>
  intelligenceFetch(`/portfolio-office/${encodeURIComponent(portfolioId)}/concentration`);
export const createPortfolioOfficePortfolio = (body) =>
  intelligenceFetch('/portfolio-office', {
    method: 'POST',
    body: body || {},
  });
export const createPortfolioOfficeSnapshot = (portfolioId, body = {}) =>
  intelligenceFetch(`/portfolio-office/${encodeURIComponent(portfolioId)}/snapshot`, {
    method: 'POST',
    body: body || {},
  });

/** PEB-01 — Platform Event Bus */
export const getPlatformEventBusHealth = () => intelligenceFetch('/platform/events/health');
export const getPlatformEvents = (limit = 50) =>
  intelligenceFetch(`/platform/events?limit=${encodeURIComponent(limit)}`);
export const getPlatformEventTypes = () => intelligenceFetch('/platform/events/types');
export const getPlatformEventStatistics = () =>
  intelligenceFetch('/platform/events/statistics');

/** WO-01 — Watchlist Office */
export const getWatchlistOfficeHealth = () => intelligenceFetch('/watchlist-office/health');
export const getWatchlistOfficeDashboard = () => intelligenceFetch('/watchlist-office/dashboard');
export const getWatchlistOfficeWatchlist = (watchlistId) =>
  intelligenceFetch(`/watchlist-office/${encodeURIComponent(watchlistId)}`);
export const getWatchlistOfficeQueue = (watchlistId) =>
  intelligenceFetch(`/watchlist-office/${encodeURIComponent(watchlistId)}/queue`);
export const createWatchlistOfficeWatchlist = (body) =>
  intelligenceFetch('/watchlist-office', { method: 'POST', body: body || {} });
export const addWatchlistOfficeCompany = (watchlistId, body) =>
  intelligenceFetch(`/watchlist-office/${encodeURIComponent(watchlistId)}/companies`, {
    method: 'POST',
    body: body || {},
  });
export const removeWatchlistOfficeCompany = (watchlistId, ticker) =>
  intelligenceFetch(
    `/watchlist-office/${encodeURIComponent(watchlistId)}/companies/${encodeURIComponent(ticker)}`,
    { method: 'DELETE' }
  );
export const patchWatchlistOfficeCompany = (watchlistId, ticker, body = {}) =>
  intelligenceFetch(
    `/watchlist-office/${encodeURIComponent(watchlistId)}/companies/${encodeURIComponent(ticker)}`,
    { method: 'PATCH', body: body || {} }
  );

/** CW-01 — Company Workspace (primary company UX; presentation only) */
export const getCompanyWorkspaceHealth = () => intelligenceFetch('/company-workspace/health');
export const getCompanyWorkspaceDashboard = () =>
  intelligenceFetch('/company-workspace/dashboard');
export const getCompanyWorkspace = (ticker, params = {}) => {
  const qs = new URLSearchParams();
  if (params.q) qs.set('q', String(params.q));
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/company-workspace/${encodeURIComponent(ticker)}${suffix}`);
};
export const getCompanyWorkspaceTimeline = (ticker, params = {}) => {
  const qs = new URLSearchParams();
  if (params.event_type) qs.set('event_type', String(params.event_type));
  if (params.source) qs.set('source', String(params.source));
  if (params.q) qs.set('q', String(params.q));
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(
    `/company-workspace/${encodeURIComponent(ticker)}/timeline${suffix}`
  );
};
export const getCompanyWorkspaceResearch = (ticker) =>
  intelligenceFetch(`/company-workspace/${encodeURIComponent(ticker)}/research`);
export const getCompanyWorkspaceEvidence = (ticker, params = {}) => {
  const qs = new URLSearchParams();
  if (params.q) qs.set('q', String(params.q));
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(
    `/company-workspace/${encodeURIComponent(ticker)}/evidence${suffix}`
  );
};
export const searchCompanyWorkspace = (ticker, q, scope = 'all') => {
  const qs = new URLSearchParams({ q: String(q || ''), scope: String(scope || 'all') });
  return intelligenceFetch(
    `/company-workspace/${encodeURIComponent(ticker)}/search?${qs}`
  );
};

/** IST-01 — Institutional Stress Tests (orchestration exams; no single-module pass) */
export const getInstitutionalStressTestsHealth = () =>
  intelligenceFetch('/institutional-stress-tests/health');
export const getInstitutionalStressTestsDashboard = () =>
  intelligenceFetch('/institutional-stress-tests/dashboard');
export const runInstitutionalStressTest = (body = {}) =>
  intelligenceFetch('/institutional-stress-tests/run', { method: 'POST', body: body || {} });
export const runInstitutionalStressTestRaw = (body = {}) =>
  intelligenceFetch('/institutional-stress-tests/run-raw', { method: 'POST', body: body || {} });
export const getInstitutionalStressTestReport = (caseId = 'IST-01') => {
  const qs = new URLSearchParams({ case_id: String(caseId || 'IST-01') });
  return intelligenceFetch(`/institutional-stress-tests/report?${qs}`);
};

/** E2E-01 — Institutional Product Experience Validation */
export const getProductExperienceHealth = () => intelligenceFetch('/product-experience/health');
export const getProductExperienceDashboard = () =>
  intelligenceFetch('/product-experience/dashboard');
export const getProductExperienceReport = () => intelligenceFetch('/product-experience/report');
export const runProductExperienceValidation = (body = {}) =>
  intelligenceFetch('/product-experience/run', { method: 'POST', body: body || {} });

/** RH-01 — AGI Release Health (single release gate) */
export const getReleaseHealthHealth = () =>
  intelligenceFetch('/release-health/health', { timeoutMs: 30_000 });
export const getReleaseHealthDashboard = (refresh = false) => {
  const qs = refresh ? '?refresh=true' : '';
  // Dashboard GET is snapshot/lightweight; keep under cold-start budget.
  return intelligenceFetch(`/release-health/dashboard${qs}`, { timeoutMs: 60_000 });
};
export const runReleaseHealth = (body = {}) =>
  intelligenceFetch('/release-health/run', {
    method: 'POST',
    body: body || {},
    // Full gate (IST+IBS+E2E) can take a few minutes on a cold Render dyno.
    timeoutMs: 300_000,
  });

/** IRE-02 — Institutional Reporting Engine + Reason Composer (deterministic; no LLM) */
export const getInstitutionalReportHealth = () =>
  intelligenceFetch('/report/health', { timeoutMs: 30_000 });
export const composeInstitutionalCompanyReport = (body = {}) =>
  intelligenceFetch('/report/company', { method: 'POST', body: body || {}, timeoutMs: 60_000 });
export const getInstitutionalCompanyReport = (ticker, { includeReasons = true } = {}) => {
  const qs = includeReasons ? '?include_reasons=true' : '?include_reasons=false';
  return intelligenceFetch(`/report/company/${encodeURIComponent(ticker)}${qs}`, {
    timeoutMs: 60_000,
  });
};

/** IDS-01 — Institutional Decision System (owns recommendation; no LLM) */
export const getInstitutionalDecisionHealth = () =>
  intelligenceFetch('/decision/health', { timeoutMs: 30_000 });
export const composeInstitutionalDecision = (body = {}) =>
  intelligenceFetch('/decision/company', { method: 'POST', body: body || {}, timeoutMs: 60_000 });
export const getInstitutionalDecision = (
  ticker,
  { includeHistory = false, includeCalibration = true, includeDrift = true } = {}
) => {
  const qs = new URLSearchParams();
  if (includeHistory) qs.set('include_history', 'true');
  if (includeCalibration) qs.set('include_calibration', 'true');
  if (includeDrift) qs.set('include_drift', 'true');
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/decision/company/${encodeURIComponent(ticker)}${suffix}`, {
    timeoutMs: 60_000,
  });
};

/** IDS-02 — Decision Calibration & Explainability */
export const getInstitutionalCalibrationHealth = () =>
  intelligenceFetch('/calibration/health', { timeoutMs: 30_000 });
export const composeInstitutionalCalibration = (body = {}) =>
  intelligenceFetch('/calibration/company', { method: 'POST', body: body || {}, timeoutMs: 60_000 });
export const getInstitutionalCalibration = (
  ticker,
  { includeCalibration = true, includeDrift = true } = {}
) => {
  const qs = new URLSearchParams();
  if (includeCalibration) qs.set('include_calibration', 'true');
  if (includeDrift) qs.set('include_drift', 'true');
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/calibration/company/${encodeURIComponent(ticker)}${suffix}`, {
    timeoutMs: 60_000,
  });
};

/** KG-01 — Institutional Knowledge Graph (single-company) */
export const getInstitutionalGraphHealth = () =>
  intelligenceFetch('/graph/health', { timeoutMs: 30_000 });
export const composeInstitutionalGraph = (body = {}) =>
  intelligenceFetch('/graph/company', { method: 'POST', body: body || {}, timeoutMs: 60_000 });
export const getInstitutionalGraph = (
  ticker,
  { includePaths = true, includeInference = true } = {}
) => {
  const qs = new URLSearchParams();
  if (includePaths) qs.set('include_paths', 'true');
  if (includeInference) qs.set('include_inference', 'true');
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/graph/company/${encodeURIComponent(ticker)}${suffix}`, {
    timeoutMs: 60_000,
  });
};

/** PKG-01 / Phase 4.1 PO-01 — Portfolio Knowledge Graph */
export const getPortfolioGraphHealth = () =>
  intelligenceFetch('/portfolio-graph/health', { timeoutMs: 30_000 });
export const composePortfolioGraph = (body = {}) =>
  intelligenceFetch('/portfolio-graph', { method: 'POST', body: body || {}, timeoutMs: 60_000 });
export const getPortfolioGraph = (portfolioId = 'agi-core-equity', { includeCompanyGraphs = true } = {}) => {
  const qs = new URLSearchParams();
  if (includeCompanyGraphs) qs.set('include_company_graphs', 'true');
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/portfolio-graph/${encodeURIComponent(portfolioId)}${suffix}`, {
    timeoutMs: 60_000,
  });
};
export const getInstitutionalPortfolioObject = (portfolioId = 'agi-core-equity') =>
  intelligenceFetch(`/portfolio-graph/${encodeURIComponent(portfolioId)}/portfolio`, {
    timeoutMs: 60_000,
  });

/** CIO-01 — Institutional Portfolio Decision System */
export const getPortfolioDecisionHealth = () =>
  intelligenceFetch('/portfolio-decision/health', { timeoutMs: 30_000 });
export const composePortfolioDecision = (body = {}) =>
  intelligenceFetch('/portfolio-decision', { method: 'POST', body: body || {}, timeoutMs: 60_000 });
export const getPortfolioDecision = (
  portfolioId = 'agi-core-equity',
  { refresh = true, includeHistory = false } = {}
) => {
  const qs = new URLSearchParams();
  if (refresh) qs.set('refresh', 'true');
  if (includeHistory) qs.set('include_history', 'true');
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/portfolio-decision/${encodeURIComponent(portfolioId)}${suffix}`, {
    timeoutMs: 60_000,
  });
};

/** PRE-01 — Institutional Portfolio Risk Engine */
export const getPortfolioRiskHealth = () =>
  intelligenceFetch('/portfolio-risk/health', { timeoutMs: 30_000 });
export const composePortfolioRisk = (body = {}) =>
  intelligenceFetch('/portfolio-risk', { method: 'POST', body: body || {}, timeoutMs: 60_000 });
export const getPortfolioRisk = (
  portfolioId = 'agi-core-equity',
  { refresh = true, includeHistory = false } = {}
) => {
  const qs = new URLSearchParams();
  if (refresh) qs.set('refresh', 'true');
  if (includeHistory) qs.set('include_history', 'true');
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/portfolio-risk/${encodeURIComponent(portfolioId)}${suffix}`, {
    timeoutMs: 60_000,
  });
};

/** PCE-01 — Institutional Policy & Constraint Engine */
export const getPolicyHealth = () => intelligenceFetch('/policy/health', { timeoutMs: 30_000 });
export const checkPortfolioPolicy = (body = {}) =>
  intelligenceFetch('/policy/check', { method: 'POST', body: body || {}, timeoutMs: 60_000 });
export const getPortfolioPolicy = (
  portfolioId = 'agi-core-equity',
  { refresh = true, includeHistory = false, policy = 'family_office' } = {}
) => {
  const qs = new URLSearchParams();
  if (refresh) qs.set('refresh', 'true');
  if (includeHistory) qs.set('include_history', 'true');
  if (policy) qs.set('policy', policy);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/policy/${encodeURIComponent(portfolioId)}${suffix}`, {
    timeoutMs: 60_000,
  });
};

/** UAG-01 — Universal Ask AGI Orchestrator */
export const getOrchestratorHealth = () =>
  intelligenceFetch('/orchestrator/health', { timeoutMs: 30_000 });
export const universalAsk = (body = {}) =>
  intelligenceFetch('/ask', { method: 'POST', body: body || {}, timeoutMs: 90_000 });
export const universalAskStream = (body = {}) =>
  intelligenceFetch('/ask/stream', { method: 'POST', body: body || {}, timeoutMs: 90_000 });
export const getUniversalQuery = (queryId) =>
  intelligenceFetch(`/query/${encodeURIComponent(queryId)}`, { timeoutMs: 30_000 });

/** RW-01 — Institutional Research Workspace */
export const getResearchWorkspaceHealth = () =>
  intelligenceFetch('/workspace/health', { timeoutMs: 30_000 });
export const getResearchWorkspaceCompany = (ticker, { focus = 'overview' } = {}) => {
  const qs = new URLSearchParams();
  if (focus) qs.set('focus', focus);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(
    `/workspace/company/${encodeURIComponent(ticker)}${suffix}`,
    { timeoutMs: 60_000 }
  );
};
export const getResearchWorkspacePortfolio = (portfolioId = 'agi-core-equity', { focus = 'overview' } = {}) => {
  const qs = new URLSearchParams();
  if (focus) qs.set('focus', focus);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(
    `/workspace/portfolio/${encodeURIComponent(portfolioId)}${suffix}`,
    { timeoutMs: 60_000 }
  );
};
export const getResearchWorkspaceObject = (objectId, { objectType } = {}) => {
  const qs = new URLSearchParams();
  if (objectType) qs.set('object_type', objectType);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(
    `/workspace/object/${encodeURIComponent(objectId)}${suffix}`,
    { timeoutMs: 30_000 }
  );
};
export const getResearchWorkspaceTimeline = (contextId, { contextType = 'company' } = {}) => {
  const qs = new URLSearchParams();
  if (contextType) qs.set('context_type', contextType);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(
    `/workspace/timeline/${encodeURIComponent(contextId)}${suffix}`,
    { timeoutMs: 60_000 }
  );
};
export const searchResearchWorkspace = (query, { contextType = 'company', contextId = 'AXISBANK' } = {}) => {
  const qs = new URLSearchParams();
  qs.set('q', String(query || '').trim());
  qs.set('context_type', contextType);
  qs.set('context_id', contextId);
  return intelligenceFetch(`/workspace/search?${qs}`, { timeoutMs: 30_000 });
};
export const addResearchWorkspaceNote = (body = {}) =>
  intelligenceFetch('/workspace/notes', { method: 'POST', body: body || {}, timeoutMs: 30_000 });

/** CCI-01 — Cross-Company Intelligence */
export const getRelationshipsHealth = () =>
  intelligenceFetch('/relationships/health', { timeoutMs: 30_000 });
export const getCompanyRelationships = (ticker, { portfolioId = 'agi-core-equity' } = {}) => {
  const qs = new URLSearchParams();
  if (portfolioId) qs.set('portfolio_id', portfolioId);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(
    `/relationships/company/${encodeURIComponent(ticker)}${suffix}`,
    { timeoutMs: 60_000 }
  );
};
export const getSectorRelationships = (sector) =>
  intelligenceFetch(`/relationships/sector/${encodeURIComponent(sector)}`, { timeoutMs: 60_000 });
export const getMacroRelationships = (driver) =>
  intelligenceFetch(`/relationships/macro/${encodeURIComponent(driver)}`, { timeoutMs: 60_000 });
export const queryRelationships = (body = {}) =>
  intelligenceFetch('/relationships/query', { method: 'POST', body: body || {}, timeoutMs: 90_000 });
export const getSimilarCompanies = (ticker) =>
  intelligenceFetch(`/relationships/similar/${encodeURIComponent(ticker)}`, { timeoutMs: 30_000 });
export const getRelationshipClusters = () =>
  intelligenceFetch('/relationships/clusters', { timeoutMs: 30_000 });

/** PUB-01 — Publishing & Distribution */
export const getPublicationsHealth = () =>
  intelligenceFetch('/publications/health', { timeoutMs: 30_000 });
export const getPublicationTypes = () =>
  intelligenceFetch('/publications/types', { timeoutMs: 30_000 });
export const listPublications = ({ limit = 20 } = {}) => {
  const qs = new URLSearchParams();
  if (limit) qs.set('limit', String(limit));
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/publications${suffix}`, { timeoutMs: 30_000 });
};
export const generatePublication = (body = {}) =>
  intelligenceFetch('/publications/generate', { method: 'POST', body: body || {}, timeoutMs: 90_000 });
export const getPublication = (publicationId) =>
  intelligenceFetch(`/publications/${encodeURIComponent(publicationId)}`, { timeoutMs: 30_000 });
export const exportPublication = (body = {}) =>
  intelligenceFetch('/publications/export', { method: 'POST', body: body || {}, timeoutMs: 90_000 });

/** MPC-01 — Multi-Portfolio & Client Platform */
export const getPlatformHealth = () =>
  intelligenceFetch('/platform/health', { timeoutMs: 30_000 });
export const listPlatformPortfolios = () =>
  intelligenceFetch('/portfolios', { timeoutMs: 30_000 });
export const createPlatformPortfolio = (body = {}) =>
  intelligenceFetch('/portfolios', { method: 'POST', body: body || {}, timeoutMs: 30_000 });
export const listPlatformClients = () =>
  intelligenceFetch('/clients', { timeoutMs: 30_000 });
export const createPlatformClient = (body = {}) =>
  intelligenceFetch('/clients', { method: 'POST', body: body || {}, timeoutMs: 30_000 });
export const resolvePlatformWorkspace = (body = {}) =>
  intelligenceFetch('/workspaces/resolve', { method: 'POST', body: body || {}, timeoutMs: 30_000 });
export const getPlatformWorkspace = (workspaceId, params = {}) => {
  const qs = new URLSearchParams();
  if (params.portfolioId) qs.set('portfolio_id', params.portfolioId);
  if (params.clientId) qs.set('client_id', params.clientId);
  if (params.roleId) qs.set('role_id', params.roleId);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/workspaces/${encodeURIComponent(workspaceId)}${suffix}`, {
    timeoutMs: 30_000,
  });
};
export const setPlatformPermissions = (body = {}) =>
  intelligenceFetch('/permissions', { method: 'POST', body: body || {}, timeoutMs: 30_000 });
export const resolvePlatformContext = (body = {}) =>
  intelligenceFetch('/platform/context', { method: 'POST', body: body || {}, timeoutMs: 30_000 });
export const platformAsk = (body = {}) =>
  intelligenceFetch('/platform/ask', { method: 'POST', body: body || {}, timeoutMs: 90_000 });

/** PRP-01 — Performance & Scale */
export const getPerformanceHealth = () =>
  intelligenceFetch('/performance/health', { timeoutMs: 30_000 });
export const getPerformanceMetrics = () =>
  intelligenceFetch('/performance/metrics', { timeoutMs: 30_000 });
export const getPerformanceCache = () =>
  intelligenceFetch('/performance/cache', { timeoutMs: 30_000 });
export const getPerformanceQueue = () =>
  intelligenceFetch('/performance/queue', { timeoutMs: 30_000 });
export const listPerformanceJobs = (limit = 40) => {
  const qs = new URLSearchParams();
  if (limit) qs.set('limit', String(limit));
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/performance/jobs${suffix}`, { timeoutMs: 30_000 });
};
export const enqueuePerformanceJob = (body = {}) =>
  intelligenceFetch('/performance/jobs', { method: 'POST', body: body || {}, timeoutMs: 30_000 });
export const getPerformanceJob = (jobId) =>
  intelligenceFetch(`/performance/jobs/${encodeURIComponent(jobId)}`, { timeoutMs: 30_000 });
export const runGraphIncremental = (body = {}) =>
  intelligenceFetch('/performance/graph/incremental', {
    method: 'POST',
    body: body || {},
    timeoutMs: 30_000,
  });
export const runPerformanceParallel = (body = {}) =>
  intelligenceFetch('/performance/parallel', {
    method: 'POST',
    body: body || {},
    timeoutMs: 30_000,
  });

/** PRP-02 — Security & Governance */
export const getSecurityHealth = () =>
  intelligenceFetch('/security/health', { timeoutMs: 30_000 });
export const authLogin = (body = {}) =>
  intelligenceFetch('/auth/login', { method: 'POST', body: body || {}, timeoutMs: 30_000 });
export const authLogout = (body = {}) =>
  intelligenceFetch('/auth/logout', { method: 'POST', body: body || {}, timeoutMs: 30_000 });
export const authRefresh = (body = {}) =>
  intelligenceFetch('/auth/refresh', { method: 'POST', body: body || {}, timeoutMs: 30_000 });
export const getSecurityContext = (body = {}) =>
  intelligenceFetch('/security/context', { method: 'POST', body: body || {}, timeoutMs: 30_000 });
export const getSecurityAudit = (body = {}) =>
  intelligenceFetch('/security/audit', { method: 'POST', body: body || {}, timeoutMs: 30_000 });
export const createSecurityApiKey = (body = {}) =>
  intelligenceFetch('/security/api-keys', { method: 'POST', body: body || {}, timeoutMs: 30_000 });
export const revokeSecurityApiKey = (apiKeyId, body = {}) =>
  intelligenceFetch(`/security/api-keys/${encodeURIComponent(apiKeyId)}`, {
    method: 'DELETE',
    body: body || {},
    timeoutMs: 30_000,
  });
export const listSecurityRoles = () =>
  intelligenceFetch('/security/roles', { timeoutMs: 30_000 });
export const listSecurityPermissions = () =>
  intelligenceFetch('/security/permissions', { timeoutMs: 30_000 });
export const listSecurityTenants = () =>
  intelligenceFetch('/security/tenants', { timeoutMs: 30_000 });

/** PRP-03 — Observability & Operations */
export const getOpsHealth = () =>
  intelligenceFetch('/ops/health', { timeoutMs: 30_000 });
export const getObservabilityHealth = () =>
  intelligenceFetch('/observability/health', { timeoutMs: 30_000 });
export const getOpsMetrics = () =>
  intelligenceFetch('/ops/metrics', { timeoutMs: 30_000 });
export const getOpsTrace = (traceId) =>
  intelligenceFetch(`/ops/traces/${encodeURIComponent(traceId)}`, { timeoutMs: 30_000 });
export const getOpsServiceMap = () =>
  intelligenceFetch('/ops/service-map', { timeoutMs: 30_000 });
export const getOpsAlerts = () =>
  intelligenceFetch('/ops/alerts', { timeoutMs: 30_000 });
export const getOpsDependencies = () =>
  intelligenceFetch('/ops/dependencies', { timeoutMs: 30_000 });
export const getOpsLogs = (params = {}) => {
  const qs = new URLSearchParams();
  if (params.limit) qs.set('limit', String(params.limit));
  if (params.severity) qs.set('severity', params.severity);
  if (params.correlationId) qs.set('correlation_id', params.correlationId);
  if (params.component) qs.set('component', params.component);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/ops/logs${suffix}`, { timeoutMs: 30_000 });
};

/** RC-01 — Architecture Conformance */
export const getArchitectureHealth = () =>
  intelligenceFetch('/architecture/health', { timeoutMs: 30_000 });
export const runArchitectureConformance = (body = {}) =>
  intelligenceFetch('/architecture/conformance', {
    method: 'POST',
    body: body || {},
    timeoutMs: 90_000,
  });
export const getArchitectureConformance = (force = false) => {
  const qs = force ? '?force=true' : '';
  return intelligenceFetch(`/architecture/conformance${qs}`, { timeoutMs: 90_000 });
};
export const getArchitectureReport = () =>
  intelligenceFetch('/architecture/report', { timeoutMs: 90_000 });
export const getArchitectureViolations = () =>
  intelligenceFetch('/architecture/violations', { timeoutMs: 90_000 });

/** L-01 — Launch Phase */
export const getAcceptanceHealth = () =>
  intelligenceFetch('/acceptance/health', { timeoutMs: 30_000 });
export const runAcceptance = (body = {}) =>
  intelligenceFetch('/acceptance/run', {
    method: 'POST',
    body: body || {},
    timeoutMs: 180_000,
  });
export const getAcceptanceReport = () =>
  intelligenceFetch('/acceptance/report', { timeoutMs: 180_000 });
export const getAcceptanceCases = (limit = 500) =>
  intelligenceFetch(`/acceptance/cases?limit=${encodeURIComponent(limit)}`, {
    timeoutMs: 180_000,
  });
export const getAcceptancePhase = (phase) =>
  intelligenceFetch(`/acceptance/phase/${encodeURIComponent(phase)}`, { timeoutMs: 90_000 });
export const runAcceptancePhase = (phase, body = {}) =>
  intelligenceFetch(`/acceptance/phase/${encodeURIComponent(phase)}`, {
    method: 'POST',
    body: body || {},
    timeoutMs: 90_000,
  });
export const getAcceptanceDiagnostics = () =>
  intelligenceFetch('/acceptance/diagnostics', { timeoutMs: 30_000 });

/** IEP-01 — Institutional Evidence Platform (AGI v1.1) */
export const getIepHealth = () =>
  intelligenceFetch('/iep/health', { timeoutMs: 30_000 });
export const getIepStatus = () =>
  intelligenceFetch('/iep/status', { timeoutMs: 30_000 });
export const getIepResearchPack = (ticker) =>
  intelligenceFetch(`/iep/pack/${encodeURIComponent(ticker)}`, { timeoutMs: 90_000 });
export const getIepReadiness = (ticker) =>
  intelligenceFetch(`/iep/readiness/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });
export const getIepValidate = (ticker) =>
  intelligenceFetch(`/iep/validate/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });
export const orchestrateIep = (ticker, body = {}) =>
  intelligenceFetch(`/iep/orchestrate/${encodeURIComponent(ticker)}`, {
    method: 'POST',
    body: body || {},
    timeoutMs: 120_000,
  });
export const getIepRegistry = (ticker) =>
  intelligenceFetch(`/iep/registry/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });
export const getIepCanonical = (ticker) =>
  intelligenceFetch(`/iep/canonical/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });
export const getIepMemory = (ticker) =>
  intelligenceFetch(`/iep/memory/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });
export const getIepPhase1 = () =>
  intelligenceFetch('/iep/phase1', { timeoutMs: 180_000 });
export const getIepMetrics = () =>
  intelligenceFetch('/iep/metrics', { timeoutMs: 180_000 });
export const getIepCenter = () =>
  intelligenceFetch('/iep/center', { timeoutMs: 180_000 });
export const getIepWriterGate = (ticker) =>
  intelligenceFetch(`/iep/gates/writer/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });
export const getIepDecisionGate = (ticker, recommendation) =>
  intelligenceFetch(`/iep/gates/decision/${encodeURIComponent(ticker)}`, {
    method: 'POST',
    body: { recommendation },
    timeoutMs: 60_000,
  });
export const getIepPublishGate = (ticker) =>
  intelligenceFetch(`/iep/gates/publish/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });

/** IEP v1.1.1 — Knowledge OS + institutional company APIs */
export const getIepEntity = (query) =>
  intelligenceFetch(`/iep/entity/${encodeURIComponent(query)}`, { timeoutMs: 30_000 });
export const getIepTimeline = (ticker) =>
  intelligenceFetch(`/iep/timeline/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });
export const getIepGraph = (ticker) =>
  intelligenceFetch(`/iep/graph/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });
export const getIepEligibility = (ticker) =>
  intelligenceFetch(`/iep/eligibility/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });
export const getIepQuality = (ticker) =>
  intelligenceFetch(`/iep/quality/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });
export const getIepDomains = (ticker) =>
  intelligenceFetch(`/iep/domains/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });
export const getIepCoverage = (ticker) =>
  intelligenceFetch(`/iep/coverage/${encodeURIComponent(ticker)}`, { timeoutMs: 90_000 });
export const runIepLearn = (ticker, body = {}) =>
  intelligenceFetch(`/iep/learn/${encodeURIComponent(ticker)}`, {
    method: 'POST',
    body: body || {},
    timeoutMs: 120_000,
  });
export const getIepLifecycle = (ticker) =>
  intelligenceFetch(`/iep/lifecycle/${encodeURIComponent(ticker)}`, { timeoutMs: 30_000 });
export const getIepObservability = () =>
  intelligenceFetch('/iep/observability', { timeoutMs: 180_000 });
export const getIepCompany = (companyRef) =>
  intelligenceFetch(`/iep/company/${encodeURIComponent(companyRef)}`, { timeoutMs: 120_000 });
export const getIepCompanyResource = (companyRef, resource) =>
  intelligenceFetch(
    `/iep/company/${encodeURIComponent(companyRef)}/${encodeURIComponent(resource)}`,
    { timeoutMs: 120_000 }
  );

/** KIL-01 — Knowledge Integration Layer (AGI v1.1.2) */
export const getKilHealth = () =>
  intelligenceFetch('/iep/kil/health', { timeoutMs: 30_000 });
export const runKilIntegrate = (body = {}) =>
  intelligenceFetch('/iep/kil/integrate', {
    method: 'POST',
    body: body || {},
    timeoutMs: 180_000,
  });
export const runKilIntegrateCompany = (ticker, body = {}) =>
  intelligenceFetch(`/iep/kil/integrate/${encodeURIComponent(ticker)}`, {
    method: 'POST',
    body: body || {},
    timeoutMs: 120_000,
  });
export const getKnowledgeHealth = () =>
  intelligenceFetch('/iep/knowledge-health', { timeoutMs: 180_000 });
export const getKnowledgeConfidence = (ticker) =>
  intelligenceFetch(`/iep/knowledge-confidence/${encodeURIComponent(ticker)}`, {
    timeoutMs: 60_000,
  });
export const getCoverageState = (ticker) =>
  intelligenceFetch(`/iep/coverage-state/${encodeURIComponent(ticker)}`, { timeoutMs: 90_000 });
export const getKnowledgeSnapshots = () =>
  intelligenceFetch('/iep/snapshots', { timeoutMs: 30_000 });
export const getKilEvents = () =>
  intelligenceFetch('/iep/events', { timeoutMs: 30_000 });
export const orchestrateIepAsk = (ticker, body = {}) =>
  intelligenceFetch(`/iep/ask/${encodeURIComponent(ticker)}`, {
    method: 'POST',
    body: body || {},
    timeoutMs: 120_000,
  });
export const getIepExpansion = () =>
  intelligenceFetch('/iep/expansion', { timeoutMs: 120_000 });
export const enqueueNifty500Expansion = (body = {}) =>
  intelligenceFetch('/iep/expansion/nifty500', {
    method: 'POST',
    body: body || {},
    timeoutMs: 120_000,
  });

/** ICF-01 — Institutional Coverage Factory (companies → ICC / day) */
export const getIcfHealth = () =>
  intelligenceFetch('/icf/health', { timeoutMs: 30_000 });
export const getIcfStatus = () =>
  intelligenceFetch('/icf/status', { timeoutMs: 30_000 });
export const getIcfDashboard = (params = {}) => {
  const qs = new URLSearchParams();
  if (params.scope) qs.set('scope', params.scope);
  if (params.sample_limit != null) qs.set('sample_limit', String(params.sample_limit));
  const suffix = qs.toString() ? `?${qs.toString()}` : '';
  return intelligenceFetch(`/icf/dashboard${suffix}`, { timeoutMs: 180_000 });
};
export const getIcfScore = (ticker) =>
  intelligenceFetch(`/icf/score/${encodeURIComponent(ticker)}`, { timeoutMs: 90_000 });
export const getIcfIcc = (ticker) =>
  intelligenceFetch(`/icf/icc/${encodeURIComponent(ticker)}`, { timeoutMs: 90_000 });
export const getIcfPlan = (params = {}) => {
  const qs = new URLSearchParams();
  if (params.scope) qs.set('scope', params.scope);
  if (params.limit != null) qs.set('limit', String(params.limit));
  const suffix = qs.toString() ? `?${qs.toString()}` : '';
  return intelligenceFetch(`/icf/plan${suffix}`, { timeoutMs: 180_000 });
};
export const runIcfPlanDispatch = (body = {}) =>
  intelligenceFetch('/icf/plan-dispatch', {
    method: 'POST',
    body: body || {},
    timeoutMs: 180_000,
  });
export const runIcfTick = (body = {}) =>
  intelligenceFetch('/icf/tick', {
    method: 'POST',
    body: body || {},
    timeoutMs: 180_000,
  });
export const runIcfDispatch = (ticker, body = {}) =>
  intelligenceFetch(`/icf/dispatch/${encodeURIComponent(ticker)}`, {
    method: 'POST',
    body: body || {},
    timeoutMs: 180_000,
  });
export const getIcfScheduler = () =>
  intelligenceFetch('/icf/scheduler', { timeoutMs: 30_000 });

/** KOC V1.2 — Institutional Knowledge Mission Control (admin only) */
const kocQs = (params = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v != null && v !== '') qs.set(k, String(v));
  });
  const s = qs.toString();
  return s ? `?${s}` : '';
};
export const getKocHealth = () =>
  intelligenceFetch('/koc/health', { timeoutMs: 12_000 });
export const getKocStatus = () =>
  intelligenceFetch('/koc/status', { timeoutMs: 12_000 });
export const getKocOverview = (params = {}) =>
  intelligenceFetch(`/koc/overview${kocQs(params)}`, { timeoutMs: 50_000 });
export const getKocDesk = (params = {}) =>
  intelligenceFetch(`/koc/desk${kocQs(params)}`, { timeoutMs: 50_000 });
export const getKocSystemHealth = () =>
  intelligenceFetch('/koc/system-health', { timeoutMs: 25_000 });
export const getKocCoverage = (params = {}) =>
  intelligenceFetch(`/koc/coverage${kocQs(params)}`, { timeoutMs: 50_000 });
export const getKocMissingInbox = (params = {}) =>
  intelligenceFetch(`/koc/missing-inbox${kocQs(params)}`, { timeoutMs: 50_000 });
export const getKocMissingKnowledge = (params = {}) =>
  intelligenceFetch(`/koc/missing-knowledge${kocQs(params)}`, { timeoutMs: 50_000 });
export const getKocCompany = (ticker) =>
  intelligenceFetch(`/koc/company/${encodeURIComponent(ticker)}`, { timeoutMs: 60_000 });
export const getKocCollectors = () =>
  intelligenceFetch('/koc/collectors', { timeoutMs: 25_000 });
export const getKocEvidence = (params = {}) =>
  intelligenceFetch(`/koc/evidence${kocQs(params)}`, { timeoutMs: 50_000 });
export const getKocEvidenceDetail = (ticker, documentId) =>
  intelligenceFetch(
    `/koc/evidence/${encodeURIComponent(ticker)}/${encodeURIComponent(documentId)}`,
    { timeoutMs: 45_000 }
  );
export const getKocKnowledgeVersions = (params = {}) =>
  intelligenceFetch(`/koc/knowledge-versions${kocQs(params)}`, { timeoutMs: 20_000 });
export const getKocGapAi = (params = {}) =>
  intelligenceFetch(`/koc/gap-ai${kocQs(params)}`, { timeoutMs: 50_000 });
export const findKocMissingKnowledge = (ticker) =>
  intelligenceFetch(`/koc/gap-ai/${encodeURIComponent(ticker)}`, { timeoutMs: 45_000 });
export const searchKoc = (params = {}) =>
  intelligenceFetch(`/koc/search${kocQs(params)}`, { timeoutMs: 35_000 });
export const uploadKocKnowledge = (body = {}) =>
  intelligenceFetch('/koc/upload', {
    method: 'POST',
    body: body || {},
    timeoutMs: 180_000,
  });
/** V1.5 IUDF — bulk company-info sheet (Excel/CSV, one row per company) → IKT facts. */
export const uploadCompanySheet = (body = {}) =>
  intelligenceFetch('/institutional-knowledge-tables/upload-sheet', {
    method: 'POST',
    body: body || {},
    timeoutMs: 180_000,
  });
export const getKocQueue = (params = {}) =>
  intelligenceFetch(`/koc/queue${kocQs(params)}`, { timeoutMs: 20_000 });
export const getKocAudit = (params = {}) =>
  intelligenceFetch(`/koc/audit${kocQs(params)}`, { timeoutMs: 15_000 });
export const runKocAction = (body = {}) =>
  intelligenceFetch('/koc/action', {
    method: 'POST',
    body: body || {},
    timeoutMs: 180_000,
  });
export const runKocCgl = (body = {}) =>
  intelligenceFetch('/koc/run-cgl', { method: 'POST', body: body || {}, timeoutMs: 180_000 });
export const runKocKil = (body = {}) =>
  intelligenceFetch('/koc/run-kil', { method: 'POST', body: body || {}, timeoutMs: 180_000 });
export const runKocCoverage = (body = {}) =>
  intelligenceFetch('/koc/run-coverage', { method: 'POST', body: body || {}, timeoutMs: 180_000 });
export const runKocRepair = (body = {}) =>
  intelligenceFetch('/koc/repair', { method: 'POST', body: body || {}, timeoutMs: 180_000 });

export const getLaunchHealth = () =>
  intelligenceFetch('/launch/health', { timeoutMs: 30_000 });
export const getLaunchMetrics = () =>
  intelligenceFetch('/launch/metrics', { timeoutMs: 30_000 });
export const getLaunchFunnel = () =>
  intelligenceFetch('/launch/funnel', { timeoutMs: 30_000 });
export const trackLaunchEvent = (body = {}) =>
  intelligenceFetch('/launch/events', { method: 'POST', body: body || {}, timeoutMs: 20_000 });
export const trackLaunchJourney = (body = {}) =>
  intelligenceFetch('/launch/journey', { method: 'POST', body: body || {}, timeoutMs: 20_000 });
export const submitLaunchFeedback = (body = {}) =>
  intelligenceFetch('/launch/feedback', { method: 'POST', body: body || {}, timeoutMs: 20_000 });
export const getLaunchFeedback = (limit = 40) =>
  intelligenceFetch(`/launch/feedback?limit=${encodeURIComponent(limit)}`, { timeoutMs: 30_000 });
export const getLaunchFlags = () =>
  intelligenceFetch('/launch/flags', { timeoutMs: 20_000 });
export const setLaunchFlag = (body = {}) =>
  intelligenceFetch('/launch/flags', { method: 'POST', body: body || {}, timeoutMs: 20_000 });
export const getLaunchSla = () =>
  intelligenceFetch('/launch/sla', { timeoutMs: 30_000 });
export const getLaunchReport = () =>
  intelligenceFetch('/launch/report', { timeoutMs: 60_000 });

/** ICE-01 — Investment Committee Engine */
export const getCommitteeEngineHealth = () =>
  intelligenceFetch('/committee-engine/health', { timeoutMs: 30_000 });
export const reviewCommittee = (body = {}) =>
  intelligenceFetch('/committee/review', { method: 'POST', body: body || {}, timeoutMs: 90_000 });
export const getCommitteePending = () =>
  intelligenceFetch('/committee/pending', { timeoutMs: 30_000 });
export const getCommitteeResolution = (resolutionId) =>
  intelligenceFetch(`/committee/resolution/${encodeURIComponent(resolutionId)}`, {
    timeoutMs: 30_000,
  });
export const getCommitteePortfolio = (portfolioId = 'agi-core-equity', { refresh = true } = {}) => {
  const qs = new URLSearchParams();
  if (refresh) qs.set('refresh', 'true');
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/committee/portfolio/${encodeURIComponent(portfolioId)}${suffix}`, {
    timeoutMs: 90_000,
  });
};

/** FG-01 — Forecast & Scenario Graph */
export const getInstitutionalScenarioHealth = () =>
  intelligenceFetch('/scenario/health', { timeoutMs: 30_000 });
export const composeInstitutionalScenarios = (body = {}) =>
  intelligenceFetch('/scenario/company', { method: 'POST', body: body || {}, timeoutMs: 90_000 });
export const getInstitutionalScenarios = (
  ticker,
  { includeGraph = false, includePropagation = true } = {}
) => {
  const qs = new URLSearchParams();
  if (includeGraph) qs.set('include_graph', 'true');
  if (includePropagation) qs.set('include_propagation', 'true');
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/scenario/company/${encodeURIComponent(ticker)}${suffix}`, {
    timeoutMs: 90_000,
  });
};

/** IO-01 — Institutional Observation Engine (proactive monitoring) */
export const getInstitutionalObservationHealth = () =>
  intelligenceFetch('/observation/health', { timeoutMs: 30_000 });
export const composeInstitutionalObservation = (body = {}) =>
  intelligenceFetch('/observation/company', { method: 'POST', body: body || {}, timeoutMs: 60_000 });
export const getInstitutionalObservations = (
  ticker,
  { criticalOnly = false, includeDecisionChanges = true, refresh = false, inject = '' } = {}
) => {
  const qs = new URLSearchParams();
  if (criticalOnly) qs.set('critical_only', 'true');
  if (includeDecisionChanges) qs.set('include_decision_changes', 'true');
  if (refresh) qs.set('refresh', 'true');
  if (inject) qs.set('inject', String(inject));
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/observation/company/${encodeURIComponent(ticker)}${suffix}`, {
    timeoutMs: 60_000,
  });
};

/** IBS-01 — AGI Institutional Benchmark Suite */
export const getInstitutionalBenchmarksHealth = () =>
  intelligenceFetch('/institutional-benchmarks/health');
export const getInstitutionalBenchmarksDashboard = () =>
  intelligenceFetch('/institutional-benchmarks/dashboard');
export const listInstitutionalBenchmarks = (sector) => {
  const qs = new URLSearchParams();
  if (sector) qs.set('sector', String(sector));
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/institutional-benchmarks${suffix}`);
};
export const getInstitutionalBenchmark = (caseId, params = {}) => {
  const qs = new URLSearchParams();
  if (params.cutoff) qs.set('cutoff', String(params.cutoff));
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/institutional-benchmarks/${encodeURIComponent(caseId)}${suffix}`);
};
export const runInstitutionalBenchmark = (body = {}) =>
  intelligenceFetch('/institutional-benchmarks/run', { method: 'POST', body: body || {} });
export const runAllInstitutionalBenchmarks = (body = {}) =>
  intelligenceFetch('/institutional-benchmarks/run-all', { method: 'POST', body: body || {} });

/** AGI v4.0 Investment Office OS — Thesis → Decision → Portfolio → Monitoring → Learning */
export const getThesisHealth = () => intelligenceFetch('/thesis/health');
export const getThesisDashboard = () => intelligenceFetch('/thesis/dashboard');
export const listTheses = (body = {}) =>
  intelligenceFetch('/thesis/list', { method: 'POST', body });

export const getDecisionHealth = () => intelligenceFetch('/decision/health');
export const getDecisionDashboard = () => intelligenceFetch('/decision/dashboard');
export const listDecisions = (body = {}) =>
  intelligenceFetch('/decision/list', { method: 'POST', body });

export const getPortfolioIdeaHealth = () => intelligenceFetch('/portfolio/health');
export const getPortfolioIdeaDashboard = () => intelligenceFetch('/portfolio/dashboard');
export const listPortfolioIdeas = (body = {}) =>
  intelligenceFetch('/portfolio/list', { method: 'POST', body });
export const rankPortfolioIdeas = (body = {}) =>
  intelligenceFetch('/portfolio/ranking', { method: 'POST', body });

export const getMonitoringHealth = () => intelligenceFetch('/monitoring/health');
export const getMonitoringDashboard = () => intelligenceFetch('/monitoring/dashboard');
export const listMonitoringEvents = (body = {}) =>
  intelligenceFetch('/monitoring/list', { method: 'POST', body });
export const getMonitoringReviewQueue = (body = {}) =>
  intelligenceFetch('/monitoring/review-queue', { method: 'POST', body });

export const getLearningHealth = () => intelligenceFetch('/learning/health');
export const getLearningDashboard = () => intelligenceFetch('/learning/dashboard');
export const listLearnings = (body = {}) =>
  intelligenceFetch('/learning/list', { method: 'POST', body });

/** Company Monitoring System V1 — continuous living analyst */
export const getCompanyMonitorHealth = () => intelligenceFetch('/company-monitor/health');
export const getCompanyMonitorDashboard = () => intelligenceFetch('/company-monitor/dashboard');
export const getCompanyMonitorQualityGates = () =>
  intelligenceFetch('/company-monitor/quality-gates');
export const getCompanyMonitorChanges = (ticker, limit = 40) => {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (ticker) qs.set('ticker', ticker);
  return intelligenceFetch(`/company-monitor/changes?${qs}`);
};
export const getCompanyMonitorAlerts = (limit = 40) =>
  intelligenceFetch(`/company-monitor/alerts?limit=${limit}`);
export const getCompanyMonitorReviews = (limit = 40) =>
  intelligenceFetch(`/company-monitor/reviews?limit=${limit}`);
export const runCompanyMonitor = (ticker, query = '') =>
  intelligenceFetch('/company-monitor/run', {
    method: 'POST',
    body: { ticker, query: query || `Monitor ${ticker}` },
  });
export const runCompanyMonitorUniverse = (limit) =>
  intelligenceFetch('/company-monitor/run-universe', {
    method: 'POST',
    body: limit != null ? { limit } : {},
  });

/** Company Analysis Engine V1 — institutional company-specific reasoning (not Context Assembly) */
export const getCompanyAnalysisHealth = () => intelligenceFetch('/company-analysis/health');
export const getCompanyAnalysisDashboard = () => intelligenceFetch('/company-analysis/dashboard');
export const getCompanyAnalysisQualityGates = () =>
  intelligenceFetch('/company-analysis/quality-gates');
export const getCompanyAnalysisReports = (limit = 30) =>
  intelligenceFetch(`/company-analysis/reports?limit=${limit}`);
export const getCompanyAnalysisReport = (ticker) =>
  intelligenceFetch(`/company-analysis/report/${encodeURIComponent(ticker)}`);
export const analyseCompany = (ticker, query = 'Company analysis') =>
  intelligenceFetch('/company-analysis/analyse', {
    method: 'POST',
    body: { ticker, query },
  });

/** Institutional Analyst Framework V1 — specialist opinions → committee → CIO */
export const getInstitutionalAnalystsHealth = () =>
  intelligenceFetch('/institutional-analysts/health');
export const getInstitutionalAnalystsQualityGates = () =>
  intelligenceFetch('/institutional-analysts/quality-gates');

/** Investment Committee Intelligence V1 — deliberation / vote / minutes */
export const getInvestmentCommitteeHealth = () =>
  intelligenceFetch('/investment-committee/health');
export const getInvestmentCommitteeQualityGates = () =>
  intelligenceFetch('/investment-committee/quality-gates');
export const getInvestmentCommitteeTimeline = (ticker, limit = 20) =>
  intelligenceFetch(
    `/investment-committee/timeline/${encodeURIComponent(ticker)}?limit=${limit}`
  );
export const recordInvestmentCommitteeActuals = (ticker, actuals, meetingId) =>
  intelligenceFetch('/investment-committee/record-actuals', {
    method: 'POST',
    body: { ticker, actuals, meeting_id: meetingId },
  });

/** Institutional Research Writer V1 — publication writing after CIO */
export const getResearchWriterHealth = () => intelligenceFetch('/research-writer/health');
export const getResearchWriterQualityGates = () =>
  intelligenceFetch('/research-writer/quality-gates');

/** AGIB Intelligence Layer V2 — living dossier / thesis / forecast / ledger */
export const getAilHealth = () => intelligenceFetch('/ail/health');
export const getAilDashboard = () => intelligenceFetch('/ail/dashboard');
export const analyseAil = (q, ticker) => {
  const qs = new URLSearchParams({ q });
  if (ticker) qs.set('ticker', ticker);
  return intelligenceFetch(`/ail/analyse?${qs}`);
};
export const runAilMonitor = (watchlist = 'default') =>
  intelligenceFetch(`/ail/monitor/run?watchlist=${encodeURIComponent(watchlist)}`, {
    method: 'POST',
    body: {},
  });
export const getCompanyDossierAil = (ticker) =>
  intelligenceFetch(`/company/${encodeURIComponent(ticker)}/dossier`);
export const getCompanyTimelineAil = (ticker, limit = 100) =>
  intelligenceFetch(`/company/${encodeURIComponent(ticker)}/timeline?limit=${limit}`);
export const getCompanyEventsAil = (ticker, limit = 50) =>
  intelligenceFetch(`/company/${encodeURIComponent(ticker)}/events?limit=${limit}`);
export const getCompanyThesisAil = (ticker) =>
  intelligenceFetch(`/company/${encodeURIComponent(ticker)}/thesis`);
export const getCompanyForecastAil = (ticker) =>
  intelligenceFetch(`/company/${encodeURIComponent(ticker)}/forecast`);
export const getCompanyLedgerAil = (ticker) =>
  intelligenceFetch(`/company/${encodeURIComponent(ticker)}/ledger`);
export const getCompanyMonitorAil = (ticker) =>
  intelligenceFetch(`/company/${encodeURIComponent(ticker)}/monitor`);
export const getAilEvent = (id) => intelligenceFetch(`/event/${encodeURIComponent(id)}`);
export const getAilEvidence = (id) => intelligenceFetch(`/evidence/${encodeURIComponent(id)}`);

/** AGIB v3.2 IERE — Institutional Evidence Retrieval Engine */
export const getEvidenceHealth = () => intelligenceFetch('/evidence/health', { timeoutMs: 30_000 });
export const getEvidenceDashboard = () =>
  intelligenceFetch('/evidence/dashboard', { timeoutMs: 60_000 });
export const searchEvidence = (q, { ticker, asOf } = {}) => {
  const qs = new URLSearchParams({ q: String(q || '') });
  if (ticker) qs.set('ticker', ticker);
  if (asOf) qs.set('as_of', asOf);
  return intelligenceFetch(`/evidence/search?${qs}`, { timeoutMs: 90_000 });
};
export const getCompanyEvidence = (ticker, asOf) => {
  const qs = new URLSearchParams();
  if (asOf) qs.set('as_of', asOf);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/evidence/company/${encodeURIComponent(ticker)}${suffix}`, {
    timeoutMs: 90_000,
  });
};
export const getDocumentEvidence = (docId) =>
  intelligenceFetch(`/evidence/document/${encodeURIComponent(docId)}`, { timeoutMs: 60_000 });
export const getEvidenceGraph = (graphId) => {
  const qs = new URLSearchParams();
  if (graphId) qs.set('graph_id', graphId);
  const suffix = qs.toString() ? `?${qs}` : '';
  return intelligenceFetch(`/evidence/graph${suffix}`, { timeoutMs: 60_000 });
};
export const replayEvidence = (q, asOf, ticker) => {
  const qs = new URLSearchParams({ q: String(q || ''), as_of: String(asOf || '') });
  if (ticker) qs.set('ticker', ticker);
  return intelligenceFetch(`/evidence/replay?${qs}`, { timeoutMs: 90_000 });
};
export const getAilPrediction = (id) => intelligenceFetch(`/prediction/${encodeURIComponent(id)}`);

/** Institutional Intelligence Stack — FIL → FDI → MII → EIL → PIL */
export const getInstitutionalStackHealth = () => intelligenceFetch('/institutional-stack/health');
export const getInstitutionalStackDashboard = () => intelligenceFetch('/institutional-stack/dashboard');
export const getInstitutionalStackQualityGates = () =>
  intelligenceFetch('/institutional-stack/quality-gates');
export const getInstitutionalStackCompany = (ticker, analyst = 'committee') => {
  const qs = new URLSearchParams({ analyst }).toString();
  return intelligenceFetch(`/institutional-stack/company/${encodeURIComponent(ticker)}?${qs}`);
};
export const analyseInstitutionalStack = (ticker) =>
  intelligenceFetch('/institutional-stack/analyse', { method: 'POST', body: { ticker } });
export const bootstrapInstitutionalStack = (tickers) =>
  intelligenceFetch('/institutional-stack/bootstrap', {
    method: 'POST',
    body: tickers ? { tickers } : {},
  });
export const ingestInstitutionalStack = (payload) =>
  intelligenceFetch('/institutional-stack/ingest', { method: 'POST', body: payload || {} });

/** Evidence Intelligence Layer */
export const getEilHealth = () => intelligenceFetch('/academy/evidence/health');
export const getEilDashboard = () => intelligenceFetch('/academy/evidence/dashboard');
export const getEilQualityGates = () => intelligenceFetch('/academy/evidence/quality-gates');

/** Peer Intelligence Layer */
export const getPilHealth = () => intelligenceFetch('/peer-intelligence/health');
export const getPilDashboard = () => intelligenceFetch('/peer-intelligence/dashboard');
export const getPilQualityGates = () => intelligenceFetch('/peer-intelligence/quality-gates');
export const getPilCompany = (ticker) =>
  intelligenceFetch(`/peer-intelligence/company/${encodeURIComponent(ticker)}`);
export const analysePil = (ticker) =>
  intelligenceFetch('/peer-intelligence/analyse', { method: 'POST', body: { ticker } });

/** Filing Intelligence Layer */
export const getFilHealth = () => intelligenceFetch('/filing-intelligence/health');
export const getFilDashboard = () => intelligenceFetch('/filing-intelligence/dashboard');
export const getFilQualityGates = () => intelligenceFetch('/filing-intelligence/quality-gates');
export const getFilCompany = (ticker) =>
  intelligenceFetch(`/filing-intelligence/company/${encodeURIComponent(ticker)}`);
export const analyseFil = (ticker) =>
  intelligenceFetch('/filing-intelligence/analyse', { method: 'POST', body: { ticker } });
export const ingestFil = (payload) =>
  intelligenceFetch('/filing-intelligence/ingest', { method: 'POST', body: payload || {} });

/** Filing Diff Engine */
export const getFdiHealth = () => intelligenceFetch('/filing-diff/health');
export const getFdiDashboard = () => intelligenceFetch('/filing-diff/dashboard');
export const getFdiQualityGates = () => intelligenceFetch('/filing-diff/quality-gates');
export const getFdiCompany = (ticker) =>
  intelligenceFetch(`/filing-diff/company/${encodeURIComponent(ticker)}`);
export const analyseFdi = (ticker) =>
  intelligenceFetch('/filing-diff/analyse', { method: 'POST', body: { ticker } });

/** Management Intelligence Engine */
export const getMiiHealth = () => intelligenceFetch('/management-intelligence/health');
export const getMiiDashboard = () => intelligenceFetch('/management-intelligence/dashboard');
export const getMiiQualityGates = () => intelligenceFetch('/management-intelligence/quality-gates');
export const getMiiCompany = (ticker) =>
  intelligenceFetch(`/management-intelligence/company/${encodeURIComponent(ticker)}`);
export const getMiiGuidance = (ticker) =>
  intelligenceFetch(`/management-intelligence/guidance/${encodeURIComponent(ticker)}`);
export const analyseMii = (ticker) =>
  intelligenceFetch('/management-intelligence/analyse', { method: 'POST', body: { ticker } });

/** Financial Statements Engine + FDO (ops soft-wire) */
export const getFseHealth = () => intelligenceFetch('/financial-statements/health');
export const getFseDashboard = () => intelligenceFetch('/financial-statements/dashboard');
export const getFdoDashboard = (universe = 'gold') =>
  intelligenceFetch(`/financial-statements/fdo/dashboard?universe=${encodeURIComponent(universe)}`);
export const getFdoSchedule = (universe = 'gold') =>
  intelligenceFetch(`/financial-statements/fdo/schedule?universe=${encodeURIComponent(universe)}`);
export const getFdoAlerts = (universe = 'gold') =>
  intelligenceFetch(`/financial-statements/fdo/alerts?universe=${encodeURIComponent(universe)}`);
export const getFseCoverage = (universe = 'gold') =>
  intelligenceFetch(`/financial-statements/coverage?universe=${encodeURIComponent(universe)}`);
export const getFseCoverageCompany = (company) =>
  intelligenceFetch(`/financial-statements/coverage/${encodeURIComponent(company)}`);
export const getFseSourceHealth = () => intelligenceFetch('/financial-statements/source-health');
export const getFseCollectionHealth = () =>
  intelligenceFetch('/financial-statements/collection/health');
export const getFseSourceCoverage = () =>
  intelligenceFetch('/financial-statements/collection/source-coverage');
export const getFseSourceRegistry = () =>
  intelligenceFetch('/financial-statements/collection/source-registry');
export const getFseOrchestratorDashboard = () =>
  intelligenceFetch('/financial-statements/orchestrator/dashboard');
export const getFseWarehouseDashboard = () =>
  intelligenceFetch('/financial-statements/warehouse/dashboard');
export const getFseVerificationDashboard = () =>
  intelligenceFetch('/financial-statements/verification/dashboard');

/** FKB-01 — Institutional Financial Knowledge Base */
export const getFkbHealth = () => intelligenceFetch('/knowledge/health');
export const getFkbDashboard = () => intelligenceFetch('/knowledge/dashboard');
export const getFkbMetrics = () => intelligenceFetch('/knowledge/metrics');
export const getFkbRatios = () => intelligenceFetch('/knowledge/ratios');
export const getFkbRelationships = () => intelligenceFetch('/knowledge/relationships');
export const getFkbGlossary = () => intelligenceFetch('/knowledge/glossary');
export const getFkbThresholds = (sector) =>
  intelligenceFetch(
    sector
      ? `/knowledge/thresholds?sector=${encodeURIComponent(sector)}`
      : '/knowledge/thresholds'
  );

/** FIRE-01 — Financial Narrative & Trend Engine */
export const getFireHealth = () => intelligenceFetch('/financial-intelligence/health');
export const getFireDashboard = () => intelligenceFetch('/financial-intelligence/dashboard');
export const getFireCompany = (ticker) =>
  intelligenceFetch(`/financial-intelligence/company/${encodeURIComponent(ticker)}`);
export const getFireFindings = (ticker) =>
  intelligenceFetch(`/financial-intelligence/findings/${encodeURIComponent(ticker)}`);
export const getFireDrivers = (ticker) =>
  intelligenceFetch(`/financial-intelligence/company/${encodeURIComponent(ticker)}/drivers`);
export const getFireRelationships = (ticker) =>
  intelligenceFetch(`/financial-intelligence/company/${encodeURIComponent(ticker)}/relationships`);

/** FIRE-03 — Business & Management Intelligence */
export const getBusinessIntelligenceHealth = () =>
  intelligenceFetch('/business-intelligence/health');
export const getBusinessIntelligenceDashboard = () =>
  intelligenceFetch('/business-intelligence/dashboard');
export const getBusinessIntelligenceCompany = (ticker) =>
  intelligenceFetch(`/business-intelligence/company/${encodeURIComponent(ticker)}`);
export const getBusinessIntelligenceSegments = (ticker) =>
  intelligenceFetch(`/business-intelligence/company/${encodeURIComponent(ticker)}/segments`);
export const getBusinessIntelligenceStrategy = (ticker) =>
  intelligenceFetch(`/business-intelligence/company/${encodeURIComponent(ticker)}/strategy`);
export const getBusinessIntelligenceRisks = (ticker) =>
  intelligenceFetch(`/business-intelligence/company/${encodeURIComponent(ticker)}/risks`);
export const getBusinessIntelligenceGuidance = (ticker) =>
  intelligenceFetch(`/business-intelligence/company/${encodeURIComponent(ticker)}/guidance`);

/** FIRE-04 — Evidence Fusion Engine */
export const getEvidenceFusionHealth = () => intelligenceFetch('/evidence-fusion/health');
export const getEvidenceFusionDashboard = () => intelligenceFetch('/evidence-fusion/dashboard');
export const getEvidenceFusionCompany = (ticker) =>
  intelligenceFetch(`/evidence-fusion/company/${encodeURIComponent(ticker)}`);
export const getEvidenceFusionSupported = (ticker) =>
  intelligenceFetch(`/evidence-fusion/company/${encodeURIComponent(ticker)}/supported`);
export const getEvidenceFusionConflicts = (ticker) =>
  intelligenceFetch(`/evidence-fusion/company/${encodeURIComponent(ticker)}/conflicts`);
export const getEvidenceFusionAlignment = (ticker) =>
  intelligenceFetch(`/evidence-fusion/company/${encodeURIComponent(ticker)}/alignment`);

/** FIRE-05 — Management Execution & Temporal Evidence */
export const getManagementExecutionHealth = () =>
  intelligenceFetch('/management-execution/health');
export const getManagementExecutionDashboard = () =>
  intelligenceFetch('/management-execution/dashboard');
export const getManagementExecutionCompany = (ticker) =>
  intelligenceFetch(`/management-execution/company/${encodeURIComponent(ticker)}`);
export const getManagementExecutionTimeline = (ticker) =>
  intelligenceFetch(`/management-execution/company/${encodeURIComponent(ticker)}/timeline`);
export const getManagementExecutionScore = (ticker) =>
  intelligenceFetch(`/management-execution/company/${encodeURIComponent(ticker)}/score`);
export const getManagementExecutionObjectives = (ticker) =>
  intelligenceFetch(`/management-execution/company/${encodeURIComponent(ticker)}/objectives`);

/** FIRE-06 — Business Quality Engine */
export const getBusinessQualityHealth = () => intelligenceFetch('/business-quality/health');
export const getBusinessQualityDashboard = () => intelligenceFetch('/business-quality/dashboard');
export const getBusinessQualityCompany = (ticker) =>
  intelligenceFetch(`/business-quality/company/${encodeURIComponent(ticker)}`);
export const getBusinessQualityScore = (ticker) =>
  intelligenceFetch(`/business-quality/company/${encodeURIComponent(ticker)}/quality`);
export const getBusinessQualityPillars = (ticker) =>
  intelligenceFetch(`/business-quality/company/${encodeURIComponent(ticker)}/pillars`);

/** Accounting Intelligence Engine */
export const getAciHealth = () => intelligenceFetch('/accounting-intelligence/health');
export const getAciDashboard = () => intelligenceFetch('/accounting-intelligence/dashboard');
export const getAciQualityGates = () => intelligenceFetch('/accounting-intelligence/quality-gates');
export const getAciCompany = (ticker) =>
  intelligenceFetch(`/accounting-intelligence/company/${encodeURIComponent(ticker)}`);
export const getAciHistory = (ticker) =>
  intelligenceFetch(`/accounting-intelligence/history/${encodeURIComponent(ticker)}`);
export const analyseAci = (ticker) =>
  intelligenceFetch('/accounting-intelligence/analyse', { method: 'POST', body: { ticker } });

/** Portfolio Intelligence Office */
export const getPioHealth = () => intelligenceFetch('/portfolio-intelligence/health');
export const getPioDashboard = () => intelligenceFetch('/portfolio-intelligence/dashboard');
export const getPioQualityGates = () => intelligenceFetch('/portfolio-intelligence/quality-gates');
export const getPioPortfolio = (id) =>
  intelligenceFetch(`/portfolio-intelligence/portfolio/${encodeURIComponent(id)}`);
export const getPioPortfolioHealth = (id) =>
  intelligenceFetch(`/portfolio-intelligence/health/${encodeURIComponent(id)}`);
export const getPioScenarios = (id) =>
  intelligenceFetch(`/portfolio-intelligence/scenarios/${encodeURIComponent(id)}`);
export const analysePio = (payload = {}) =>
  intelligenceFetch('/portfolio-intelligence/analyse', { method: 'POST', body: payload || {} });

/** Causal Intelligence Graph */
export const getCigHealth = () => intelligenceFetch('/causal-intelligence/health');
export const getCigDashboard = () => intelligenceFetch('/causal-intelligence/dashboard');
export const getCigQualityGates = () => intelligenceFetch('/causal-intelligence/quality-gates');
export const getCigGraph = () => intelligenceFetch('/causal-intelligence/graph');
export const getCigCompany = (ticker) =>
  intelligenceFetch(`/causal-intelligence/company/${encodeURIComponent(ticker)}`);
export const getCigEvent = (event) =>
  intelligenceFetch(`/causal-intelligence/event/${encodeURIComponent(event)}`);
export const analyseCig = (payload = {}) =>
  intelligenceFetch('/causal-intelligence/analyse', { method: 'POST', body: payload || {} });

/** Legacy scenario Forecast Intelligence (/forecast/*) — not Phase 8.5 FIE */
export const getLegacyFieHealth = () => intelligenceFetch('/forecast/health');
export const getLegacyFieDashboard = () => intelligenceFetch('/forecast/dashboard');
export const getLegacyFieQualityGates = () => intelligenceFetch('/forecast/quality-gates');
export const getLegacyFieCompany = (ticker) =>
  intelligenceFetch(`/forecast/company/${encodeURIComponent(ticker)}`);
export const getLegacyFieScenarios = (ticker) =>
  intelligenceFetch(`/forecast/scenarios/${encodeURIComponent(ticker)}`);
export const getLegacyFieCatalysts = (ticker) =>
  intelligenceFetch(`/forecast/catalysts/${encodeURIComponent(ticker)}`);
export const analyseLegacyFie = (payload = {}) =>
  intelligenceFetch('/forecast/analyse', { method: 'POST', body: payload || {} });

/** Institutional Knowledge Graph */
export const getIkgHealth = () => intelligenceFetch('/knowledge-graph/health');
export const getIkgDashboard = () => intelligenceFetch('/knowledge-graph/dashboard');
export const getIkgQualityGates = () => intelligenceFetch('/knowledge-graph/quality-gates');
export const getIkgEntity = (id) =>
  intelligenceFetch(`/knowledge-graph/entity/${encodeURIComponent(id)}`);
export const getIkgCompany = (ticker) =>
  intelligenceFetch(`/knowledge-graph/company/${encodeURIComponent(ticker)}`);
export const getIkgRelationships = (id) =>
  intelligenceFetch(`/knowledge-graph/relationships/${encodeURIComponent(id)}`);
export const getIkgPath = (source, target) => {
  const qs = new URLSearchParams({ source: source || '', target: target || '' }).toString();
  return intelligenceFetch(`/knowledge-graph/path?${qs}`);
};
export const queryIkg = (payload = {}) =>
  intelligenceFetch('/knowledge-graph/query', { method: 'POST', body: payload || {} });

/** Institutional Learning & Memory Engine (ILM + MIE) */
export const getIlmHealth = () => intelligenceFetch('/ilm/health');
export const getIlmDashboard = () => intelligenceFetch('/ilm/dashboard');
export const getIlmQualityGates = () => intelligenceFetch('/ilm/quality-gates');
export const getIlmCompany = (ticker) =>
  intelligenceFetch(`/ilm/company/${encodeURIComponent(ticker)}`);
export const getIlmThesis = (ticker) =>
  intelligenceFetch(`/ilm/thesis/${encodeURIComponent(ticker)}`);
export const getIlmCommittee = (ticker) =>
  intelligenceFetch(`/ilm/committee/${encodeURIComponent(ticker)}`);
export const getIlmForecast = (ticker) =>
  intelligenceFetch(`/ilm/forecast/${encodeURIComponent(ticker)}`);
export const getIlmPortfolio = (portfolioId) =>
  intelligenceFetch(`/ilm/portfolio/${encodeURIComponent(portfolioId)}`);
export const updateIlmLearning = (payload = {}) =>
  intelligenceFetch('/ilm/learning/update', { method: 'POST', body: payload || {} });

/** Institutional Simulation & Strategy Lab (SSL) */
export const getSslHealth = () => intelligenceFetch('/simulation/health');
export const getSslDashboard = () => intelligenceFetch('/simulation/dashboard');
export const getSslQualityGates = () => intelligenceFetch('/simulation/quality-gates');
export const getSslScenarios = () => intelligenceFetch('/simulation/scenarios');
export const getSslHistory = (limit = 50) => {
  const qs = new URLSearchParams({ limit: String(limit) }).toString();
  return intelligenceFetch(`/simulation/history?${qs}`);
};
export const runSslSimulation = (payload = {}) =>
  intelligenceFetch('/simulation/run', { method: 'POST', body: payload || {} });
export const runSslPortfolio = (payload = {}) =>
  intelligenceFetch('/simulation/portfolio', { method: 'POST', body: payload || {} });

/** Institutional Decision Engine V2 (final architectural component) */
export const getIdev2Health = () => intelligenceFetch('/decision-engine-v2/health');
export const getIdev2Dashboard = () => intelligenceFetch('/decision-engine-v2/dashboard');
export const getIdev2QualityGates = () => intelligenceFetch('/decision-engine-v2/quality-gates');
export const getIdev2FreezeReview = () => intelligenceFetch('/decision-engine-v2/freeze-review');
export const getIdev2Company = (ticker) =>
  intelligenceFetch(`/decision-engine-v2/company/${encodeURIComponent(ticker)}`);
export const getIdev2Audit = (auditId) =>
  intelligenceFetch(`/decision-engine-v2/audit/${encodeURIComponent(auditId)}`);
export const getIdev2Monitoring = (ticker) =>
  intelligenceFetch(`/decision-engine-v2/monitoring/${encodeURIComponent(ticker)}`);
export const analyseIdev2 = (payload = {}) =>
  intelligenceFetch('/decision-engine-v2/analyse', { method: 'POST', body: payload || {} });

/** Soft-wire probes for Intelligence Map — never throw; return status envelope. */
export async function probeIntelligencePath(path) {
  const started = performance.now();
  if (!BASE) {
    return {
      ok: false,
      status: 0,
      latency_ms: 0,
      data: null,
      error: 'API origin is not configured. Set VITE_API_URL to the Render backend.',
      path,
    };
  }
  try {
    const url = `${BASE}/api/intelligence${path}`;
    const resp = await fetch(url, {
      method: 'GET',
      credentials: 'include',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(20_000),
    });
    const text = await resp.text().catch(() => '');
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text.slice(0, 240) };
    }
    const latency_ms = Math.round(performance.now() - started);
    if (!resp.ok) {
      const detail =
        data?.error ||
        data?.detail ||
        data?.message ||
        (typeof data?.raw === 'string' ? data.raw : '') ||
        `HTTP ${resp.status}`;
      return {
        ok: false,
        status: resp.status,
        latency_ms,
        data,
        error: String(detail).slice(0, 280),
        path,
      };
    }
    return { ok: true, status: resp.status, latency_ms, data, error: null, path };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      latency_ms: Math.round(performance.now() - started),
      data: null,
      error: err?.message || String(err),
      path,
    };
  }
}

export const getAcsHealth = () => intelligenceFetch('/academy/certification/health');
export const getIrsHealth = () => intelligenceFetch('/academy/regression/health');
export const getIdev1Health = () => intelligenceFetch('/decision-engine/health');

/** RQ1 Research Ontology — Sprint 1 classify-only (no analysts / layers) */
export const getResearchOntologyHealth = () => intelligenceFetch('/research-ontology/health');
export const getResearchOntologyDashboard = () => intelligenceFetch('/research-ontology/dashboard');
export const getResearchOntologyConstitution = () =>
  intelligenceFetch('/research-ontology/constitution');
export const getResearchOntologyQualityGates = () =>
  intelligenceFetch('/research-ontology/quality-gates');
export const classifyResearchOntology = (question) =>
  intelligenceFetch('/research-ontology/classify', {
    method: 'POST',
    body: { question },
  });

/** RQ1 Entity Resolution Engine — Sprint 2 (never guess; IKG source of truth) */
export const getEntityResolutionHealth = () => intelligenceFetch('/entity-resolution/health');
export const getEntityResolutionDashboard = () => intelligenceFetch('/entity-resolution/dashboard');
export const getEntityResolutionConstitution = () =>
  intelligenceFetch('/entity-resolution/constitution');
export const getEntityResolutionQualityGates = () =>
  intelligenceFetch('/entity-resolution/quality-gates');
export const resolveEntityResolution = (payload = {}) =>
  intelligenceFetch('/entity-resolution/resolve', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseEntityResolution = (payload = {}) =>
  intelligenceFetch('/entity-resolution/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** RQ1 Research Objective Engine — Sprint 3 (objective-driven research plan) */
export const getResearchObjectiveHealth = () => intelligenceFetch('/research-objective/health');
export const getResearchObjectiveDashboard = () =>
  intelligenceFetch('/research-objective/dashboard');
export const getResearchObjectiveConstitution = () =>
  intelligenceFetch('/research-objective/constitution');
export const getResearchObjectiveQualityGates = () =>
  intelligenceFetch('/research-objective/quality-gates');
export const planResearchObjective = (payload = {}) =>
  intelligenceFetch('/research-objective/plan', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseResearchObjective = (payload = {}) =>
  intelligenceFetch('/research-objective/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** RQ1 Context Intelligence Engine — Sprint 4 (surrounding institutional context) */
export const getContextIntelligenceHealth = () =>
  intelligenceFetch('/context-intelligence/health');
export const getContextIntelligenceDashboard = () =>
  intelligenceFetch('/context-intelligence/dashboard');
export const getContextIntelligenceConstitution = () =>
  intelligenceFetch('/context-intelligence/constitution');
export const getContextIntelligenceQualityGates = () =>
  intelligenceFetch('/context-intelligence/quality-gates');
export const enrichContextIntelligence = (payload = {}) =>
  intelligenceFetch('/context-intelligence/enrich', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseContextIntelligence = (payload = {}) =>
  intelligenceFetch('/context-intelligence/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** RQ1 Institutional Analyst Router — Sprint 5 (who participates, when, weights) */
export const getAnalystRouterHealth = () => intelligenceFetch('/analyst-router/health');
export const getAnalystRouterDashboard = () => intelligenceFetch('/analyst-router/dashboard');
export const getAnalystRouterConstitution = () =>
  intelligenceFetch('/analyst-router/constitution');
export const getAnalystRouterQualityGates = () =>
  intelligenceFetch('/analyst-router/quality-gates');
export const routeAnalystRouter = (payload = {}) =>
  intelligenceFetch('/analyst-router/route', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseAnalystRouter = (payload = {}) =>
  intelligenceFetch('/analyst-router/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** RQ1 Intelligence Layer Router — Sprint 6 (execution planner) */
export const getLayerRouterHealth = () => intelligenceFetch('/layer-router/health');
export const getLayerRouterDashboard = () => intelligenceFetch('/layer-router/dashboard');
export const getLayerRouterConstitution = () => intelligenceFetch('/layer-router/constitution');
export const getLayerRouterQualityGates = () => intelligenceFetch('/layer-router/quality-gates');
export const planLayerRouter = (payload = {}) =>
  intelligenceFetch('/layer-router/plan', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseLayerRouter = (payload = {}) =>
  intelligenceFetch('/layer-router/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** RQ2 Institutional Hypothesis Generation Engine — Sprint 1 (AFTER IREP) */
export const getAcquisitionPlannerHealth = () => intelligenceFetch('/acquisition-planner/health');
export const getAcquisitionPlannerDashboard = () => intelligenceFetch('/acquisition-planner/dashboard');
export const getAcquisitionPlannerConstitution = () => intelligenceFetch('/acquisition-planner/constitution');
export const getAcquisitionPlannerQualityGates = () => intelligenceFetch('/acquisition-planner/quality-gates');
export const planAcquisitionPlanner = (payload = {}) =>
  intelligenceFetch('/acquisition-planner/plan', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseAcquisitionPlanner = (payload = {}) =>
  intelligenceFetch('/acquisition-planner/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

export const getResearchBlueprintHealth = () => intelligenceFetch('/research-blueprint/health');
export const getResearchBlueprintDashboard = () => intelligenceFetch('/research-blueprint/dashboard');
export const getResearchBlueprintConstitution = () => intelligenceFetch('/research-blueprint/constitution');
export const getResearchBlueprintQualityGates = () => intelligenceFetch('/research-blueprint/quality-gates');
export const planResearchBlueprint = (payload = {}) =>
  intelligenceFetch('/research-blueprint/plan', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseResearchBlueprint = (payload = {}) =>
  intelligenceFetch('/research-blueprint/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

export const getValidationEngineHealth = () => intelligenceFetch('/validation-engine/health');
export const getValidationEngineDashboard = () => intelligenceFetch('/validation-engine/dashboard');
export const getValidationEngineConstitution = () => intelligenceFetch('/validation-engine/constitution');
export const getValidationEngineQualityGates = () => intelligenceFetch('/validation-engine/quality-gates');
export const validateValidationEngine = (payload = {}) =>
  intelligenceFetch('/validation-engine/validate', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseValidationEngine = (payload = {}) =>
  intelligenceFetch('/validation-engine/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

export const getResearchExecutionHealth = () => intelligenceFetch('/research-execution/health');
export const getResearchExecutionDashboard = () => intelligenceFetch('/research-execution/dashboard');
export const getResearchExecutionConstitution = () => intelligenceFetch('/research-execution/constitution');
export const getResearchExecutionQualityGates = () => intelligenceFetch('/research-execution/quality-gates');
export const buildResearchExecution = (payload = {}) =>
  intelligenceFetch('/research-execution/build', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const exportResearchExecution = (payload = {}) =>
  intelligenceFetch('/research-execution/export', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload, format: 'markdown' } : payload,
  });
export const diagnoseResearchExecution = (payload = {}) =>
  intelligenceFetch('/research-execution/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

export const getHypothesisEngineHealth = () => intelligenceFetch('/hypothesis-engine/health');
export const getHypothesisEngineDashboard = () => intelligenceFetch('/hypothesis-engine/dashboard');
export const getHypothesisEngineConstitution = () => intelligenceFetch('/hypothesis-engine/constitution');
export const getHypothesisEngineQualityGates = () => intelligenceFetch('/hypothesis-engine/quality-gates');
export const planHypothesisEngine = (payload = {}) =>
  intelligenceFetch('/hypothesis-engine/plan', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseHypothesisEngine = (payload = {}) =>
  intelligenceFetch('/hypothesis-engine/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** RQ2 Institutional Research Question Engine — Sprint 2 (AFTER IHG) */
export const getResearchQuestionsHealth = () => intelligenceFetch('/research-questions/health');
export const getResearchQuestionsDashboard = () => intelligenceFetch('/research-questions/dashboard');
export const getResearchQuestionsConstitution = () => intelligenceFetch('/research-questions/constitution');
export const getResearchQuestionsQualityGates = () => intelligenceFetch('/research-questions/quality-gates');
export const planResearchQuestions = (payload = {}) =>
  intelligenceFetch('/research-questions/plan', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseResearchQuestions = (payload = {}) =>
  intelligenceFetch('/research-questions/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** RQ2 Institutional Hypothesis Testing Engine — Sprint 4 (AFTER evidence planning) */
export const getHypothesisTestingHealth = () => intelligenceFetch('/hypothesis-testing/health');
export const getHypothesisTestingDashboard = () => intelligenceFetch('/hypothesis-testing/dashboard');
export const getHypothesisTestingConstitution = () => intelligenceFetch('/hypothesis-testing/constitution');
export const getHypothesisTestingQualityGates = () => intelligenceFetch('/hypothesis-testing/quality-gates');
export const planHypothesisTesting = (payload = {}) =>
  intelligenceFetch('/hypothesis-testing/plan', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseHypothesisTesting = (payload = {}) =>
  intelligenceFetch('/hypothesis-testing/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** RQ2 Bayesian Belief & Confidence Engine — Sprint 6 (AFTER falsification) */
export const getBeliefEngineHealth = () => intelligenceFetch('/belief-engine/health');
export const getBeliefEngineDashboard = () => intelligenceFetch('/belief-engine/dashboard');
export const getBeliefEngineConstitution = () => intelligenceFetch('/belief-engine/constitution');
export const getBeliefEngineQualityGates = () => intelligenceFetch('/belief-engine/quality-gates');
export const planBeliefEngine = (payload = {}) =>
  intelligenceFetch('/belief-engine/plan', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseBeliefEngine = (payload = {}) =>
  intelligenceFetch('/belief-engine/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** RQ2 Institutional Thesis Construction Engine — Sprint 7 (BEFORE Committee) */
export const getThesisEngineHealth = () => intelligenceFetch('/thesis-engine/health');
export const getThesisEngineDashboard = () => intelligenceFetch('/thesis-engine/dashboard');
export const getThesisEngineConstitution = () => intelligenceFetch('/thesis-engine/constitution');
export const getThesisEngineQualityGates = () => intelligenceFetch('/thesis-engine/quality-gates');
export const planThesisEngine = (payload = {}) =>
  intelligenceFetch('/thesis-engine/plan', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseThesisEngine = (payload = {}) =>
  intelligenceFetch('/thesis-engine/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** RQ2 Institutional Debate Engine — Sprint 8 (structured pre-Committee debate) */
export const getDebateEngineHealth = () => intelligenceFetch('/debate-engine/health');
export const getDebateEngineDashboard = () => intelligenceFetch('/debate-engine/dashboard');
export const getDebateEngineConstitution = () => intelligenceFetch('/debate-engine/constitution');
export const getDebateEngineQualityGates = () => intelligenceFetch('/debate-engine/quality-gates');
export const planDebateEngine = (payload = {}) =>
  intelligenceFetch('/debate-engine/plan', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseDebateEngine = (payload = {}) =>
  intelligenceFetch('/debate-engine/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** RQ2 Institutional Decision Readiness Engine — Sprint 9 */
export const getDecisionReadinessHealth = () => intelligenceFetch('/decision-readiness/health');
export const getDecisionReadinessDashboard = () => intelligenceFetch('/decision-readiness/dashboard');
export const getDecisionReadinessConstitution = () => intelligenceFetch('/decision-readiness/constitution');
export const getDecisionReadinessQualityGates = () => intelligenceFetch('/decision-readiness/quality-gates');
export const planDecisionReadiness = (payload = {}) =>
  intelligenceFetch('/decision-readiness/plan', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseDecisionReadiness = (payload = {}) =>
  intelligenceFetch('/decision-readiness/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** RQ2 Institutional Reasoning Audit Engine — Sprint 10 */
export const getReasoningAuditHealth = () => intelligenceFetch('/reasoning-audit/health');
export const getReasoningAuditDashboard = () => intelligenceFetch('/reasoning-audit/dashboard');
export const getReasoningAuditConstitution = () => intelligenceFetch('/reasoning-audit/constitution');
export const getReasoningAuditQualityGates = () => intelligenceFetch('/reasoning-audit/quality-gates');
export const planReasoningAudit = (payload = {}) =>
  intelligenceFetch('/reasoning-audit/plan', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });
export const diagnoseReasoningAudit = (payload = {}) =>
  intelligenceFetch('/reasoning-audit/diagnostics', {
    method: 'POST',
    body: typeof payload === 'string' ? { question: payload } : payload,
  });

/** Valuation Intelligence — Institutional Consensus Dashboard (Capital IQ) */
export const getValuationConsensusHealth = () => intelligenceFetch('/valuation-consensus/health');
export const getValuationConsensusAnalytics = () =>
  intelligenceFetch('/valuation-consensus/analytics');
export const getValuationConsensusRows = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/valuation-consensus/rows${qs ? `?${qs}` : ''}`);
};
export const getValuationConsensusCompany = (ticker) =>
  intelligenceFetch(`/valuation-consensus/company/${encodeURIComponent(ticker)}`);
export const previewValuationConsensusImport = (payload) =>
  intelligenceFetch('/valuation-consensus/import/preview', {
    method: 'POST',
    body: payload,
    timeoutMs: 300_000,
  });
export const validateValuationConsensusImport = (importId, actor) =>
  intelligenceFetch('/valuation-consensus/import/validate', {
    method: 'POST',
    body: { import_id: importId, actor },
    timeoutMs: 120_000,
  });
export const publishValuationConsensusImport = (importId, actor) =>
  intelligenceFetch('/valuation-consensus/import/publish', {
    method: 'POST',
    body: { import_id: importId, actor },
    timeoutMs: 180_000,
  });
export const rollbackValuationConsensus = (versionId, actor) =>
  intelligenceFetch('/valuation-consensus/import/rollback', {
    method: 'POST',
    body: { version_id: versionId, actor },
  });
export const listValuationConsensusImports = () => intelligenceFetch('/valuation-consensus/imports');
export const listValuationConsensusVersions = () =>
  intelligenceFetch('/valuation-consensus/versions');
export const exportValuationConsensusSnapshot = () =>
  intelligenceFetch('/valuation-consensus/export', { timeoutMs: 120_000 });
export const seedValuationConsensus = (payload = {}) =>
  intelligenceFetch('/valuation-consensus/seed', {
    method: 'POST',
    body: payload,
    timeoutMs: 300_000,
  });

/** Valuation Intelligence Terminal — Warehouse → Unified Valuation Engine */
export const getVtHealth = () =>
  intelligenceFetch('/valuation-engine/terminal/health', { timeoutMs: 12_000 });
export const getVtOverview = () => intelligenceFetch('/valuation-terminal/overview');
export const getVtSectors = () => intelligenceFetch('/valuation-terminal/sectors');
export const getVtSectorIntelligence = (sector) =>
  intelligenceFetch(`/valuation-terminal/sector/${encodeURIComponent(sector)}`);
export const getVtInsights = () => intelligenceFetch('/valuation-terminal/insights');
export const getVtCompanies = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(`/valuation-terminal/companies${qs ? `?${qs}` : ''}`);
};
export const getVtCompany = (ticker, params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(
    `/valuation-engine/terminal/company/${encodeURIComponent(ticker)}${qs ? `?${qs}` : ''}`,
    { timeoutMs: 90_000 },
  );
};
export const getVtExplain = (metric) =>
  intelligenceFetch(`/valuation-engine/terminal/explain/${encodeURIComponent(metric)}`);
export const searchVtCompanies = (q, limit = 12) => {
  const qs = new URLSearchParams({ q: q || '', limit: String(limit) }).toString();
  return intelligenceFetch(`/valuation-engine/terminal/search?${qs}`, { timeoutMs: 8_000 });
};
export const getVtSeries = (symbol, metric, window = '5Y') => {
  const qs = new URLSearchParams({ window: String(window) }).toString();
  return intelligenceFetch(
    `/valuation-engine/terminal/series/${encodeURIComponent(symbol)}/${encodeURIComponent(metric)}?${qs}`,
    { timeoutMs: 60_000 },
  );
};
/** Unified Valuation Engine (warehouse contract) — distinct from legacy /ve/* */
export const getUveCompany = (symbol) =>
  intelligenceFetch(`/valuation-engine/company/${encodeURIComponent(symbol)}`, { timeoutMs: 60_000 });
export const getUveHealth = () => intelligenceFetch('/valuation-engine/health');

/** Valuation Policy & Applicability Engine (VPAE) — Phase 8.2A */
export const getValuationPolicyHealth = () =>
  intelligenceFetch('/valuation-policy/health');
export const getValuationApplicability = (symbol) =>
  intelligenceFetch(`/valuation/applicability/${encodeURIComponent(symbol)}`, { timeoutMs: 60_000 });
export const getValuationModel = (symbol) =>
  intelligenceFetch(`/valuation/model/${encodeURIComponent(symbol)}`, { timeoutMs: 60_000 });
export const getValuationExplanation = (symbol) =>
  intelligenceFetch(`/valuation/explanation/${encodeURIComponent(symbol)}`, { timeoutMs: 60_000 });
export const getValuationCoverage = (symbol) =>
  intelligenceFetch(`/valuation/coverage/${encodeURIComponent(symbol)}`, { timeoutMs: 60_000 });
export const getValuationStatus = (symbol) =>
  intelligenceFetch(`/valuation/status/${encodeURIComponent(symbol)}`, { timeoutMs: 60_000 });
export const getValuationPolicyUniverse = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/valuation/universe${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
};

/** Institutional Coverage Health — five-layer coverage (VPAE-aligned) */
export const getCoverageHealthProbe = () =>
  intelligenceFetch('/valuation/coverage-health/health');
export const getCoverageHealth = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/valuation/coverage/health${qs ? `?${qs}` : ''}`, { timeoutMs: 180_000 });
};
export const getCoverageValuation = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/valuation/coverage/valuation${qs ? `?${qs}` : ''}`, { timeoutMs: 180_000 });
};
export const getCoverageMetrics = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/valuation/coverage/metrics${qs ? `?${qs}` : ''}`, { timeoutMs: 180_000 });
};
export const getCoverageResearch = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/valuation/coverage/research${qs ? `?${qs}` : ''}`, { timeoutMs: 180_000 });
};
export const getCoverageResidual = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/valuation/coverage/residual${qs ? `?${qs}` : ''}`, { timeoutMs: 180_000 });
};

/** Institutional Valuation Research Workspace v2 — warehouse → UVE / HVIE / VPAE */
const sveQs = (params = {}) =>
  new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();

export const getSveHealth = () => intelligenceFetch('/valuation/explorer/health');
export const getSveMarket = (params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(`/valuation/market${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
};
export const getSveSectors = (params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(`/valuation/sectors${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
};
export const getSveSector = (sector, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/sector/${encodeURIComponent(sector)}${qs ? `?${qs}` : ''}`,
    { timeoutMs: 120_000 },
  );
};
export const getSveSectorIndustries = (sector, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/sector/${encodeURIComponent(sector)}/industries${qs ? `?${qs}` : ''}`,
    { timeoutMs: 120_000 },
  );
};
export const getSveIndustry = (industry, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/industry/${encodeURIComponent(industry)}${qs ? `?${qs}` : ''}`,
    { timeoutMs: 120_000 },
  );
};
export const getSveSectorCompanies = (sector, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/sector/${encodeURIComponent(sector)}/companies${qs ? `?${qs}` : ''}`,
    { timeoutMs: 120_000 },
  );
};
export const getSveSectorLeaders = (sector, params = {}) =>
  intelligenceFetch(
    `/valuation/sector/${encodeURIComponent(sector)}/leaders?${sveQs(params)}`,
    { timeoutMs: 120_000 },
  );
export const getSveSectorHeatmap = (sector) =>
  intelligenceFetch(`/valuation/sector/${encodeURIComponent(sector)}/heatmap`, { timeoutMs: 120_000 });
export const getSveSectorResearch = (sector) =>
  intelligenceFetch(`/valuation/sector/${encodeURIComponent(sector)}/research`, { timeoutMs: 120_000 });
export const getSveSectorRotation = (sector, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/sector/${encodeURIComponent(sector)}/rotation${qs ? `?${qs}` : ''}`,
    { timeoutMs: 120_000 },
  );
};
export const getSveOpportunities = (params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(`/valuation/opportunities${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
};
export const getSvePremium = (params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(`/valuation/premium${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
};
export const getSveRerating = (params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(`/valuation/rerating${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
};
export const getSveCompany = (symbol, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/company/${encodeURIComponent(symbol)}${qs ? `?${qs}` : ''}`,
    { timeoutMs: 90_000 },
  );
};
export const getSveCompanyHistory = (symbol, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/company/${encodeURIComponent(symbol)}/history${qs ? `?${qs}` : ''}`,
    { timeoutMs: 90_000 },
  );
};

/** Valuation Attribution & Research Intelligence Engine (VARIE) v1.0 */
export const getVarieHealth = () => intelligenceFetch('/valuation/attribution/health');
export const getVarieCompany = (symbol, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/attribution/company/${encodeURIComponent(symbol)}${qs ? `?${qs}` : ''}`,
    { timeoutMs: 120_000 },
  );
};
export const getVarieSector = (sector, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/attribution/sector/${encodeURIComponent(sector)}${qs ? `?${qs}` : ''}`,
    { timeoutMs: 120_000 },
  );
};
export const getVarieIndustry = (industry, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/attribution/industry/${encodeURIComponent(industry)}${qs ? `?${qs}` : ''}`,
    { timeoutMs: 120_000 },
  );
};
export const getVarieMarket = (params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(`/valuation/attribution/market${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
};
export const getVariePeer = (symbol, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/attribution/peer/${encodeURIComponent(symbol)}${qs ? `?${qs}` : ''}`,
    { timeoutMs: 120_000 },
  );
};
export const getVarieHistory = (symbol, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/attribution/history/${encodeURIComponent(symbol)}${qs ? `?${qs}` : ''}`,
    { timeoutMs: 120_000 },
  );
};
export const getVarieTimeline = (symbol, params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(
    `/valuation/attribution/timeline/${encodeURIComponent(symbol)}${qs ? `?${qs}` : ''}`,
    { timeoutMs: 120_000 },
  );
};
export const getVarieOpportunities = (params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(`/valuation/attribution/opportunities${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
};
export const getVarieLeaders = (params = {}) => {
  const qs = sveQs(params);
  return intelligenceFetch(`/valuation/attribution/leaders${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
};

/** Historical Valuation Intelligence Engine (HVIE) — Phase 8.3 */
export const getHvieHealth = () => intelligenceFetch('/historical-valuation/health');
const hvieFetch = (path, params = {}, timeoutMs = 60_000) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`${path}${qs ? `?${qs}` : ''}`, { timeoutMs });
};
export const getHvieCompany = (symbol, params = {}) =>
  hvieFetch(`/historical-valuation/company/${encodeURIComponent(symbol)}`, params);
export const getHvieHistory = (symbol, params = {}) =>
  hvieFetch(`/historical-valuation/history/${encodeURIComponent(symbol)}`, params, 90_000);
export const getHvieStatistics = (symbol, params = {}) =>
  hvieFetch(`/historical-valuation/statistics/${encodeURIComponent(symbol)}`, params);
export const getHvieBands = (symbol, params = {}) =>
  hvieFetch(`/historical-valuation/bands/${encodeURIComponent(symbol)}`, params);
export const getHviePercentiles = (symbol, params = {}) =>
  hvieFetch(`/historical-valuation/percentiles/${encodeURIComponent(symbol)}`, params);
export const getHvieRegimes = (symbol, params = {}) =>
  hvieFetch(`/historical-valuation/regimes/${encodeURIComponent(symbol)}`, params);
export const getHvieRerating = (symbol, params = {}) =>
  hvieFetch(`/historical-valuation/rerating/${encodeURIComponent(symbol)}`, params);
export const getHvieCoverage = (symbol, params = {}) =>
  hvieFetch(`/historical-valuation/coverage/${encodeURIComponent(symbol)}`, params);
export const postHvieReconstruct = (symbol, body = {}) =>
  intelligenceFetch(`/historical-valuation/reconstruct/${encodeURIComponent(symbol)}`, {
    method: 'POST',
    body,
    timeoutMs: 180_000,
  });
export const getHvieCoverageDashboard = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/historical-valuation/coverage-dashboard${qs ? `?${qs}` : ''}`, {
    timeoutMs: 120_000,
  });
};
export const getHvieRuntimeStatus = () =>
  intelligenceFetch('/historical-valuation/runtime/status');
export const postHvieRuntimeRun = (body = {}) =>
  intelligenceFetch('/historical-valuation/runtime/run', {
    method: 'POST',
    body,
    timeoutMs: 180_000,
  });
export const postHvieRuntimeStart = () =>
  intelligenceFetch('/historical-valuation/runtime/start', { method: 'POST', body: {} });
export const postHvieRuntimeStop = () =>
  intelligenceFetch('/historical-valuation/runtime/stop', { method: 'POST', body: {} });

/** HVIE Universe Completion Programme (Phase 8.3A/B) */
export const getHvieUniverseHealth = () =>
  intelligenceFetch('/hvie/runtime/health', { timeoutMs: 60_000 });
export const getHvieUniverseStatus = () =>
  intelligenceFetch('/hvie/runtime/status', { timeoutMs: 90_000 });
export const getHvieUniverseBoard = () =>
  intelligenceFetch('/hvie/runtime/board', { timeoutMs: 90_000 });
export const getHvieUniverseCoverage = () =>
  intelligenceFetch('/hvie/runtime/coverage', { timeoutMs: 90_000 });
export const getHvieUniversePipeline = () =>
  intelligenceFetch('/hvie/runtime/pipeline', { timeoutMs: 90_000 });
export const getHvieUniverseSector = () =>
  intelligenceFetch('/hvie/runtime/sector', { timeoutMs: 90_000 });
export const getHvieUniverseIndustry = () =>
  intelligenceFetch('/hvie/runtime/industry', { timeoutMs: 90_000 });
export const getHvieUniverseMarket = () =>
  intelligenceFetch('/hvie/runtime/market', { timeoutMs: 60_000 });
export const getHvieUniverseFailures = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/hvie/runtime/failures${qs ? `?${qs}` : ''}`, { timeoutMs: 60_000 });
};
export const getHvieUniverseRetryQueue = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/hvie/runtime/retry${qs ? `?${qs}` : ''}`, { timeoutMs: 60_000 });
};
export const getHvieUniverseCompany = (symbol) =>
  intelligenceFetch(`/hvie/runtime/company/${encodeURIComponent(symbol)}`, { timeoutMs: 30_000 });
export const postHvieUniverseStart = () =>
  intelligenceFetch('/hvie/runtime/start', { method: 'POST', body: {} });
export const postHvieUniverseStop = () =>
  intelligenceFetch('/hvie/runtime/stop', { method: 'POST', body: {} });
export const postHvieUniverseResume = () =>
  intelligenceFetch('/hvie/runtime/resume', { method: 'POST', body: {} });
export const postHvieUniverseRun = (body = {}) =>
  intelligenceFetch('/hvie/runtime/run', { method: 'POST', body, timeoutMs: 300_000 });
export const postHvieUniverseRetry = (symbol) =>
  intelligenceFetch(`/hvie/runtime/retry/${encodeURIComponent(symbol)}`, {
    method: 'POST', body: {}, timeoutMs: 180_000,
  });
export const postHvieUniverseReconstruct = (symbol) =>
  intelligenceFetch(`/hvie/runtime/reconstruct/${encodeURIComponent(symbol)}`, {
    method: 'POST', body: {}, timeoutMs: 300_000,
  });

/** Research Intelligence Engine (Phase 8.4) */
export const getRieHealth = () => intelligenceFetch('/research/health');
export const getRieDashboard = () =>
  intelligenceFetch('/research/dashboard', { timeoutMs: 90_000 });
export const getRieCoverage = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/research/coverage${qs ? `?${qs}` : ''}`, { timeoutMs: 90_000 });
};
export const getRieCompany = (symbol) =>
  intelligenceFetch(`/research/company/${encodeURIComponent(symbol)}`, { timeoutMs: 180_000 });
export const getRieSection = (section, symbol) =>
  intelligenceFetch(`/research/${section}/${encodeURIComponent(symbol)}`, { timeoutMs: 90_000 });
export const getRieBusiness = (symbol) => getRieSection('business', symbol);
export const getRieFinancialQuality = (symbol) => getRieSection('financial-quality', symbol);
export const getRieGrowth = (symbol) => getRieSection('growth', symbol);
export const getRieProfitability = (symbol) => getRieSection('profitability', symbol);
export const getRieCapitalAllocation = (symbol) => getRieSection('capital-allocation', symbol);
export const getRieValuation = (symbol) => getRieSection('valuation', symbol);
export const getRieOwnership = (symbol) => getRieSection('ownership', symbol);
export const getRieRisk = (symbol) => getRieSection('risk', symbol);
export const getRieCatalysts = (symbol) => getRieSection('catalysts', symbol);
export const getRieMonitoring = (symbol) => getRieSection('monitoring', symbol);
export const getRieTimeline = (symbol) => getRieSection('timeline', symbol);
export const getRieConfidence = (symbol) =>
  intelligenceFetch(`/research/confidence/${encodeURIComponent(symbol)}`, { timeoutMs: 180_000 });

/** Forecast Intelligence Engine (Phase 8.5) — /fie/* */
export const getFieHealth = () => intelligenceFetch('/fie/health');
export const getFieDashboard = () =>
  intelligenceFetch('/fie/dashboard', { timeoutMs: 90_000 });
export const getFieBoard = () =>
  intelligenceFetch('/fie/runtime/board', { timeoutMs: 90_000 });
export const getFieCompany = (symbol) =>
  intelligenceFetch(`/fie/company/${encodeURIComponent(symbol)}`, { timeoutMs: 180_000 });
export const getFieModule = (module, symbol) =>
  intelligenceFetch(`/fie/${module}/${encodeURIComponent(symbol)}`, { timeoutMs: 90_000 });
export const postFieRuntimeStart = () =>
  intelligenceFetch('/fie/runtime/start', { method: 'POST', body: {} });
export const postFieRuntimeStop = () =>
  intelligenceFetch('/fie/runtime/stop', { method: 'POST', body: {} });
export const postFieRuntimeResume = () =>
  intelligenceFetch('/fie/runtime/resume', { method: 'POST', body: {} });
export const postFieRuntimeRun = (body = {}) =>
  intelligenceFetch('/fie/runtime/run', { method: 'POST', body, timeoutMs: 300_000 });

/** Macro Intelligence Engine (Phase 9.0) — /mie/* */
export const getMieHealth = () => intelligenceFetch('/mie/health');
export const getMieDashboard = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/mie/dashboard${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
};
export const getMiePack = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/mie/pack${qs ? `?${qs}` : ''}`, { timeoutMs: 180_000 });
};
// Read-only public snapshot. It never asks the engine to calculate a macro pack.
export const getMieSnapshot = (country = 'Global') =>
  intelligenceFetch(`/mie/snapshot?country=${encodeURIComponent(country)}`, {
    timeoutMs: 6_000,
  });


export const getMieBoard = () =>
  intelligenceFetch('/mie/runtime/board', { timeoutMs: 90_000 });
export const getMieModule = (module, params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(`/mie/${module}${qs ? `?${qs}` : ''}`, { timeoutMs: 90_000 });
};
export const getMieCompanyImpact = (symbol, params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== '')),
  ).toString();
  return intelligenceFetch(
    `/mie/company-impact/${encodeURIComponent(symbol)}${qs ? `?${qs}` : ''}`,
    { timeoutMs: 90_000 },
  );
};
export const postMieRuntimeStart = () =>
  intelligenceFetch('/mie/runtime/start', { method: 'POST', body: {} });
export const postMieRuntimeStop = () =>
  intelligenceFetch('/mie/runtime/stop', { method: 'POST', body: {} });
export const postMieRuntimeResume = () =>
  intelligenceFetch('/mie/runtime/resume', { method: 'POST', body: {} });
export const postMieRuntimeRun = (body = {}) =>
  intelligenceFetch('/mie/runtime/run', { method: 'POST', body, timeoutMs: 300_000 });

/** Phase 9.1 — Intelligence Fusion & Answer Composer (IFAC) */
export const getIfacHealth = () => intelligenceFetch('/ifac/health');
export const getIfacDashboard = () =>
  intelligenceFetch('/ifac/dashboard', { timeoutMs: 60_000 });
export const getIfacTemplates = () => intelligenceFetch('/ifac/templates');
export const getIfacRouting = () => intelligenceFetch('/ifac/routing');
export const getIfacConfidence = () => intelligenceFetch('/ifac/confidence');
export const getIfacDebug = (limit = 20) =>
  intelligenceFetch(`/ifac/debug?limit=${encodeURIComponent(limit)}`);
export const postIfacCompose = (body = {}) =>
  intelligenceFetch('/ifac/compose', { method: 'POST', body, timeoutMs: 120_000 });

export const getAqeHealth = () => intelligenceFetch('/aqe/health');
export const getAqeDashboard = () =>
  intelligenceFetch('/aqe/dashboard', { timeoutMs: 60_000 });
export const postAqeInspect = (body = {}) =>
  intelligenceFetch('/aqe/inspect', { method: 'POST', body, timeoutMs: 60_000 });
export const postAqeQualityGate = (body = {}) =>
  intelligenceFetch('/aqe/quality-gate', { method: 'POST', body, timeoutMs: 60_000 });

/** Market & Sector Intelligence Terminal v1.0 */
export const getMiHealth = () => intelligenceFetch('/market-intelligence/health');
export const getMiDashboard = () =>
  intelligenceFetch('/market-intelligence/dashboard', { timeoutMs: 60_000 });
export const getMiSector = (sector) =>
  intelligenceFetch(`/market-intelligence/sector/${encodeURIComponent(sector)}`, { timeoutMs: 60_000 });

/** Hedge Fund Strategy Lab */
export const getHflHealth = () =>
  intelligenceFetch('/hedge-fund-lab/health', { timeoutMs: 8_000 });
// Strategies/compare are served from Node static fallback when the engine is down.
export const getHflStrategies = () =>
  intelligenceFetch('/hedge-fund-lab/strategies', { timeoutMs: 10_000 });
export const getHflCompare = () =>
  intelligenceFetch('/hedge-fund-lab/compare', { timeoutMs: 10_000 });
export const getHflStrategy = (id) =>
  intelligenceFetch(`/hedge-fund-lab/strategy/${encodeURIComponent(id)}`, { timeoutMs: 10_000 });
export const hflCalculate = (kind, payload) =>
  intelligenceFetch(`/hedge-fund-lab/calculate/${encodeURIComponent(kind)}`, {
    method: 'POST',
    body: payload,
    timeoutMs: 15_000,
  });
export const hflBacktest = (strategyId, payload = {}) =>
  intelligenceFetch(`/hedge-fund-lab/backtest/${encodeURIComponent(strategyId)}`, {
    method: 'POST', body: payload, timeoutMs: 120_000,
  });
export const getHflRegime = () =>
  intelligenceFetch('/hedge-fund-lab/regime', { timeoutMs: 20_000 });
export const getHflTerminal = (params = {}) => {
  const qs = new URLSearchParams({
    limit: String(params.limit ?? 12),
    ...Object.fromEntries(
      Object.entries(params)
        .filter(([k, v]) => k !== 'limit' && v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)]),
    ),
  }).toString();
  return intelligenceFetch(`/hedge-fund-lab/terminal?${qs}`, { timeoutMs: 10_000 });
};
export const getHflOpportunity = (ticker) =>
  intelligenceFetch(`/hedge-fund-lab/opportunity/${encodeURIComponent(ticker)}`, { timeoutMs: 20_000 });
export const getHflScan = (strategy, params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries({ limit: 15, ...params })
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => [k, String(v)])
    )
  ).toString();
  return intelligenceFetch(
    `/hedge-fund-lab/scan/${encodeURIComponent(strategy)}${qs ? `?${qs}` : ''}`,
    { timeoutMs: 25_000 },
  );
};
