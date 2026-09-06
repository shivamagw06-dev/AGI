import { Router } from 'express';
import {
  getInstitutionalAdmin,
  getRepairStatus,
  getInstitutionalFund,
  getInstitutionalOverview,
  getInstitutionalStock,
  markInstitutionalAlert,
  previewInstitutionalImport,
  publishInstitutionalImport,
  refreshInstitutionalFilings,
  saveSecurityMapping,
  updateInstitutionalManager,
} from '../services/institutionalHoldingsService.js';
import {
  clearInstitutionalDecisionIntelligenceCache,
  getInstitutionalDecisionIntelligence,
} from '../services/institutionalDecisionIntelligenceService.js';
import {
  createInstitutionalGroup, createInstitutionalWatchlist, getInstitutionalResearchAdmin,
  getInstitutionalResearchLayer, getInstitutionalWorkspace, markPersonalizedAlert,
  refreshInstitutionalResearchLayer, reviewInstitutionalBrief, runInstitutionalBacktest,
} from '../services/institutionalResearchLayerService.js';
import {
  clearScreenerCache, evaluateFundPerformance, getAccumulationHeatMap,
  getCombinedHoldings, screenStocks,
} from '../services/institutionalScreenerService.js';
import { clearSecuritySearchCache, searchSecurities, warmSecuritySearchIndex } from '../services/institutionalSecuritySearch.js';

async function requireAdmin(req, res, next) {
  try {
    const token = String(req.headers.authorization || '').replace(/^Bearer\s+/i, '');
    const url = String(process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '').replace(/\/$/, '');
    const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '');
    if (!token || !url || !key) return res.status(401).json({ error: 'Unauthorized' });
    const response = await fetch(`${url}/auth/v1/user`, { headers: { apikey: key, Authorization: `Bearer ${token}` } });
    const user = await response.json();
    const ids = [process.env.ADMIN_ID, process.env.VITE_ADMIN_ID, 'c56e4d07-273c-49c9-86a5-a4445e687ece'].filter(Boolean);
    const emails = [...String(process.env.ADMIN_EMAILS || '').split(','), ...String(process.env.VITE_ADMIN_EMAILS || '').split(',')].map((value) => value.trim().toLowerCase()).filter(Boolean);
    if (!response.ok || (!ids.includes(user.id) && !emails.includes(String(user.email || '').toLowerCase()))) return res.status(403).json({ error: 'Admin access required' });
    req.adminUser = user;
    return next();
  } catch {
    return res.status(401).json({ error: 'Authorization failed' });
  }
}

async function requireUser(req, res, next) {
  try {
    const token = String(req.headers.authorization || '').replace(/^Bearer\s+/i, '');
    const url = String(process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '').replace(/\/$/, '');
    const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '');
    if (!token || !url || !key) return res.status(401).json({ error: 'Sign in to use your institutional workspace.' });
    const response = await fetch(`${url}/auth/v1/user`, { headers: { apikey: key, Authorization: `Bearer ${token}` } });
    const user = await response.json();
    if (!response.ok || !user?.id) return res.status(401).json({ error: 'Your session has expired. Sign in again.' });
    req.authUser = user;
    return next();
  } catch { return res.status(401).json({ error: 'Authorization failed' }); }
}

function sendError(res, error, status = 503) {
  return res.status(status).json({ error: error?.message || 'Institutional Holdings request failed' });
}

const OVERVIEW_CACHE_TTL_MS = Math.max(
  30_000,
  Number(process.env.INSTITUTIONAL_OVERVIEW_CACHE_TTL_MS || 5 * 60_000),
);

let overviewCache = null;
let overviewCacheExpiresAt = 0;
let overviewRefreshPromise = null;

async function refreshOverviewCache() {
  if (overviewRefreshPromise) return overviewRefreshPromise;

  overviewRefreshPromise = getInstitutionalOverview()
    .then((data) => {
      overviewCache = data;
      overviewCacheExpiresAt = Date.now() + OVERVIEW_CACHE_TTL_MS;
      return data;
    })
    .finally(() => {
      overviewRefreshPromise = null;
    });

  return overviewRefreshPromise;
}

async function getCachedInstitutionalOverview() {
  const isFresh = overviewCache && Date.now() < overviewCacheExpiresAt;
  if (isFresh) return { data: overviewCache, cacheStatus: 'HIT' };

  if (overviewCache) {
    void refreshOverviewCache().catch((error) => {
      console.warn('[institutional-holdings] Background overview refresh failed:', error?.message || error);
    });
    return { data: overviewCache, cacheStatus: 'STALE' };
  }

  return { data: await refreshOverviewCache(), cacheStatus: 'MISS' };
}

function rebuildOverviewCache() {
  overviewCacheExpiresAt = 0;
  clearInstitutionalDecisionIntelligenceCache();
  void refreshOverviewCache().catch((error) => {
    console.warn('[institutional-holdings] Overview cache rebuild failed:', error?.message || error);
  });
}

export default function createInstitutionalHoldingsRouter() {
  const router = Router();
  rebuildOverviewCache();
  // Built before the first query rather than during it.
  warmSecuritySearchIndex();
  // Public, and cheap: the index is built once every fifteen minutes and every
  // query is answered from memory. Deliberately not admin-gated - it is the
  // front door of the page, and it returns only issuer names and tickers that
  // are already printed on the page below it.
  router.get('/securities/search', async (req, res) => {
    try {
      const term = String(req.query.q || '').slice(0, 64);
      const limit = Math.min(Math.max(Number(req.query.limit) || 8, 1), 20);
      if (term.trim().length < 2) return res.json({ results: [] });
      return res.json({ results: await searchSecurities(term, limit) });
    } catch (error) {
      return sendError(res, error);
    }
  });

  router.get('/overview', async (_req, res) => {
    try {
      const { data, cacheStatus } = await getCachedInstitutionalOverview();

      // The integrity gate is never served from cache.
      //
      // Everything else in this payload measures filings that changed hours
      // ago, and five minutes of staleness costs nothing. The gate is a
      // different kind of statement: it says whether the numbers beside it can
      // be trusted right now. A cached one is wrong in both directions - it
      // kept reporting "historical repair in progress" for minutes after a
      // repair finished, and it would just as readily report a clean bill of
      // health after a repair had failed.
      //
      // Two small queries, so recomputing per request is cheap. If it cannot be
      // read, the cached value stands, which is the conservative direction:
      // getRepairStatus itself fails closed.
      let dataIntegrity = data?.data_integrity ?? null;
      try {
        dataIntegrity = await getRepairStatus();
      } catch (gateError) {
        console.warn('[institutional-holdings] live gate read failed:', gateError?.message || gateError);
      }

      res.set('Cache-Control', 'public, max-age=30, stale-while-revalidate=600');
      res.set('X-AGI-Overview-Cache', cacheStatus);
      return res.json({ ...data, data_integrity: dataIntegrity });
    } catch (error) {
      return sendError(res, error);
    }
  });
  router.get('/decision-intelligence', async (_req, res) => {
    try {
      const data = await getInstitutionalDecisionIntelligence();
      res.set('Cache-Control', 'public, max-age=60, stale-while-revalidate=600');
      return res.json(data);
    } catch (error) {
      return sendError(res, error);
    }
  });
  // Admin-only, deliberately, on two grounds.
  //
  // These are not client-ready: the audit found adjusted-price coverage at 0%
  // and 90.7% of holdings rows unresolved to a ticker, so anything these
  // return today describes a tenth of the universe while looking complete.
  //
  // And each pages the whole holdings table. Measured against production they
  // time out at 120s on 72,401 rows, which is exactly the anonymous full scan
  // this release exists to prevent. They stay behind auth until they are both
  // fast and backed by data worth showing.
  router.get('/combined-holdings', requireAdmin, async (req, res) => {
    try {
      const ids = String(req.query.managers || '').split(',').map((v) => v.trim()).filter(Boolean);
      return res.json(await getCombinedHoldings({
        managerIds: ids.length ? ids : null, limit: req.query.limit,
      }));
    } catch (error) { return sendError(res, error); }
  });

  router.get('/screener', requireAdmin, async (req, res) => {
    try {
      const q = req.query || {};
      return res.json(await screenStocks({
        min_holders: q.min_holders, max_holders: q.max_holders,
        min_new_buyers: q.min_new_buyers, min_increased: q.min_increased,
        has_exits: q.has_exits, ticker_resolved: q.ticker_resolved,
        search: q.search, sort: q.sort, limit: q.limit,
      }));
    } catch (error) { return sendError(res, error); }
  });

  router.get('/heat-map', requireAdmin, async (req, res) => {
    try { return res.json(await getAccumulationHeatMap({ limit: req.query.limit })); }
    catch (error) { return sendError(res, error); }
  });

  router.get('/fund-performance', requireAdmin, async (_req, res) => {
    try { return res.json(await evaluateFundPerformance({})); }
    catch (error) { return sendError(res, error); }
  });

  router.get('/research-layer', async (_req, res) => { try { return res.json(await getInstitutionalResearchLayer()); } catch (error) { return sendError(res, error); } });
  router.post('/backtests', requireAdmin, async (req, res) => { try { return res.json(await runInstitutionalBacktest(req.body || {})); } catch (error) { return sendError(res, error, 400); } });
  router.get('/workspace', requireUser, async (req, res) => { try { return res.json(await getInstitutionalWorkspace(req.authUser.id)); } catch (error) { return sendError(res, error); } });
  router.post('/workspace/groups', requireUser, async (req, res) => { try { return res.json(await createInstitutionalGroup(req.authUser.id, req.body || {})); } catch (error) { return sendError(res, error, 400); } });
  router.post('/workspace/watchlists', requireUser, async (req, res) => { try { return res.json(await createInstitutionalWatchlist(req.authUser.id, req.body || {})); } catch (error) { return sendError(res, error, 400); } });
  router.patch('/workspace/alerts/:id', requireUser, async (req, res) => { try { return res.json(await markPersonalizedAlert(req.authUser.id, req.params.id, req.body?.is_read !== false)); } catch (error) { return sendError(res, error, 400); } });
  router.get('/funds/:slug', async (req, res) => { try { const data = await getInstitutionalFund(req.params.slug); return data ? res.json(data) : res.status(404).json({ error: 'Tracked fund not found' }); } catch (error) { return sendError(res, error); } });
  router.get('/stocks/:key', async (req, res) => { try { const data = await getInstitutionalStock(req.params.key); return data ? res.json(data) : res.status(404).json({ error: 'No tracked fund currently holds this security' }); } catch (error) { return sendError(res, error); } });
  router.get('/admin', requireAdmin, async (_req, res) => { try { return res.json(await getInstitutionalAdmin()); } catch (error) { return sendError(res, error); } });
  router.post('/admin/imports/preview', requireAdmin, async (req, res) => { try { return res.json(await previewInstitutionalImport(req.body || {})); } catch (error) { return sendError(res, error, 400); } });
  router.post('/admin/imports/publish', requireAdmin, async (req, res) => { try { const data = await publishInstitutionalImport({ ...(req.body || {}), actor: req.adminUser?.email || 'admin' }); rebuildOverviewCache(); clearScreenerCache(); clearSecuritySearchCache(); return res.json(data); } catch (error) { return sendError(res, error, 400); } });
  router.post('/admin/refresh', requireAdmin, async (req, res) => { try { const data = await refreshInstitutionalFilings(req.body || {}); rebuildOverviewCache(); clearScreenerCache(); clearSecuritySearchCache(); return res.json(data); } catch (error) { return sendError(res, error, 400); } });
  router.post('/admin/security-mappings', requireAdmin, async (req, res) => { try { const data = await saveSecurityMapping({ ...req.body, actor: req.adminUser?.email || 'admin' }); rebuildOverviewCache(); clearScreenerCache(); clearSecuritySearchCache(); return res.json(data); } catch (error) { return sendError(res, error, 400); } });
  router.patch('/admin/managers/:id', requireAdmin, async (req, res) => { try { const data = await updateInstitutionalManager(req.params.id, req.body || {}, req.adminUser?.email || 'admin'); rebuildOverviewCache(); clearScreenerCache(); clearSecuritySearchCache(); return res.json(data); } catch (error) { return sendError(res, error, 400); } });
  router.patch('/admin/alerts/:id', requireAdmin, async (req, res) => { try { return res.json(await markInstitutionalAlert(req.params.id, req.body?.is_read !== false)); } catch (error) { return sendError(res, error, 400); } });
  router.get('/admin/research-layer', requireAdmin, async (_req, res) => { try { return res.json(await getInstitutionalResearchAdmin()); } catch (error) { return sendError(res, error); } });
  router.post('/admin/research-layer/refresh', requireAdmin, async (req, res) => { try { return res.json(await refreshInstitutionalResearchLayer(req.body || {})); } catch (error) { return sendError(res, error, 400); } });
  router.patch('/admin/research-layer/briefs/:id', requireAdmin, async (req, res) => { try { return res.json(await reviewInstitutionalBrief(req.params.id, { ...(req.body || {}), reviewer: req.adminUser?.email || 'admin' })); } catch (error) { return sendError(res, error, 400); } });
  return router;
}
