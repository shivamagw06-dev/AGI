/**
 * AGI Intelligence Engine proxy — frontend never talks to Python directly.
 */

import { Router } from 'express';
import {
  buildRecentLearningSummary,
  cmsLearningStatus,
  learnCmsArticles,
  startCmsArticleLearningScheduler,
} from '../services/cmsArticleLearning.js';
import {
  approveIngestJob,
  enqueueCmsIngestJob,
  getIngestJob,
  getPipelineBlueprint,
  getStuckIngestJobs,
  getWorkerInfo,
  processIngestQueue,
  reclaimStalledJobs,
  replayIngestJob,
  startCmsIngestJobWorker,
} from '../services/cmsIngestJobs.js';
import {
  mergeApiStatus,
  probeMissionControlApis,
} from '../services/missionControlApiProbes.js';
import {
  buildKocDegradedAudit,
  buildKocDegradedHealth,
  buildKocDegradedOverview,
} from '../services/kocDegraded.js';
import {
  buildMiDegradedDashboard,
  buildMiDegradedSector,
} from '../services/miDegraded.js';
import {
  hflStaticCompare,
  hflStaticLibrary,
  hflStaticStrategy,
} from '../services/hflStaticLibrary.js';
import { getHflTerminalFromReadModel } from '../services/hflTerminalSnapshot.js';
import { getValuationCompanyPackFromReadModel } from '../services/valuationCompanyPackSnapshot.js';
import { requireStrategyLabAdmin } from '../services/strategyLabAdminAuth.js';
import { enrichStrategyLabWithLiveMarket } from '../services/strategyLabLiveMarket.js';
import { getResearchKnowledgeCard } from '../services/researchKnowledgeRegistry.js';
import { intelligenceLearningStatus } from '../services/intelligenceLearningWorker.js';

function engineConfig() {
  let baseUrl = (process.env.INTELLIGENCE_ENGINE_URL || 'http://127.0.0.1:8100').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) {
    baseUrl = `https://${baseUrl}`;
  }
  const token = (process.env.INTELLIGENCE_ENGINE_TOKEN || 'dev-intelligence-token').trim();
  return { baseUrl, token };
}

// Protect the web/API process when Render's engine is restarting or unhealthy.
// Without this guard, every page and scheduler can hold an upstream request for
// tens of seconds (or minutes), creating a thundering herd that prevents the
// engine from recovering. A successful engine response closes the circuit.
const ENGINE_FAILURE_THRESHOLD = 2;
const ENGINE_CIRCUIT_COOLDOWN_MS = 30_000;
const engineCircuit = { failures: 0, openUntil: 0, lastError: null };

function recordEngineSuccess() {
  engineCircuit.failures = 0;
  engineCircuit.openUntil = 0;
  engineCircuit.lastError = null;
}

function recordEngineFailure(error) {
  engineCircuit.failures += 1;
  engineCircuit.lastError = String(error?.message || error || 'engine request failed').slice(0, 240);
  if (engineCircuit.failures >= ENGINE_FAILURE_THRESHOLD) {
    engineCircuit.openUntil = Date.now() + ENGINE_CIRCUIT_COOLDOWN_MS;
  }
}

function circuitIsOpen(path) {
  // Let explicit health probes through so the circuit can recover naturally.
  return path !== '/v1/health' && Date.now() < engineCircuit.openUntil;
}

async function engineFetch(path, { method = 'GET', body = null, timeoutMs = 120_000, headers = null } = {}) {
  if (circuitIsOpen(path)) {
    const waitSeconds = Math.max(1, Math.ceil((engineCircuit.openUntil - Date.now()) / 1000));
    const error = new Error(`Intelligence engine is recovering; retry in about ${waitSeconds}s.`);
    error.code = 'ENGINE_CIRCUIT_OPEN';
    throw error;
  }
  const { baseUrl, token } = engineConfig();
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      method,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        'X-AGI-Intelligence-Token': token,
        ...(headers || {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(timeoutMs),
    });
    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      // Render/proxy outages often return HTML 502 pages. Never forward raw HTML
      // to the browser — Mission Control / Ask surface it as a confusing dump.
      const looksHtml = /^\s*</.test(text || '');
      data = looksHtml
        ? {
            error: 'intelligence_engine_html_error',
            detail:
              'Intelligence engine returned an HTML error page instead of JSON (often a Render 502 during redeploy). Retry shortly.',
            status: response.status,
            path,
          }
        : { raw: String(text || '').slice(0, 400) };
    }
    if (response.ok) recordEngineSuccess();
    else if (response.status >= 500) recordEngineFailure(new Error(`engine HTTP ${response.status}`));
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    recordEngineFailure(error);
    throw error;
  }
}

function proxyPost(path) {
  return async (req, res) => {
    try {
      const result = await engineFetch(path, { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  };
}

function proxyGet(pathBuilder) {
  return async (req, res) => {
    try {
      const path = typeof pathBuilder === 'function' ? pathBuilder(req) : pathBuilder;
      const result = await engineFetch(path);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  };
}

let companyMasterCache = { expiresAt: 0, rows: [] };

// The Hedge Fund terminal is derived from the warehouse and is safe to show
// briefly stale.  Keeping its last successful response prevents a slow or
// restarting engine from turning a normal page visit into a 45-second wait.
const HFL_TERMINAL_FRESH_MS = 5 * 60_000;
const HFL_TERMINAL_STALE_MS = 60 * 60_000;
const hflTerminalCache = new Map();

function readHflTerminalCache(key, { allowStale = false } = {}) {
  const hit = hflTerminalCache.get(key);
  if (!hit) return null;
  const age = Date.now() - hit.at;
  if (age <= HFL_TERMINAL_FRESH_MS || (allowStale && age <= HFL_TERMINAL_STALE_MS)) {
    return { data: hit.data, age, stale: age > HFL_TERMINAL_FRESH_MS };
  }
  return null;
}

function writeHflTerminalCache(key, data) {
  if (data && typeof data === 'object') hflTerminalCache.set(key, { data, at: Date.now() });
}

const MI_DASHBOARD_FRESH_MS = 5 * 60_000;
const MI_DASHBOARD_STALE_MS = 60 * 60_000;
let miDashboardCache = null;

function readMiDashboardCache({ allowStale = false } = {}) {
  if (!miDashboardCache) return null;
  const age = Date.now() - miDashboardCache.at;
  if (age <= MI_DASHBOARD_FRESH_MS || (allowStale && age <= MI_DASHBOARD_STALE_MS)) {
    return { data: miDashboardCache.data, age, stale: age > MI_DASHBOARD_FRESH_MS };
  }
  return null;
}

function writeMiDashboardCache(data) {
  if (data && typeof data === 'object' && data.ok) {
    miDashboardCache = { data, at: Date.now() };
  }
}

async function companyMatches(query, limit = 8) {
  const needle = String(query || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  if (!needle) return [];
  if (Date.now() > companyMasterCache.expiresAt) {
    const result = await engineFetch('/v1/warehouse/tab/company_master?limit=3000', { timeoutMs: 20_000 });
    if (!result.ok) throw new Error(result.data?.error || 'Company master is unavailable.');
    companyMasterCache = {
      expiresAt: Date.now() + 5 * 60_000,
      rows: (result.data?.rows || []).map((row) => ({
        symbol: String(row.symbol || row.company_id || '').toUpperCase(),
        company_name: row.company_name || row.legal_name || row.symbol || row.company_id,
      })).filter((row) => row.symbol),
    };
  }
  const clean = (value) => String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  const rank = (row) => {
    const symbol = clean(row.symbol); const name = clean(row.company_name);
    if (symbol === needle || name === needle) return 0;
    if (symbol.startsWith(needle)) return 1;
    if (name.startsWith(needle)) return 2;
    return 3;
  };
  return companyMasterCache.rows
    .filter((row) => clean(row.symbol).includes(needle) || clean(row.company_name).includes(needle))
    .sort((a, b) => rank(a) - rank(b) || a.company_name.localeCompare(b.company_name))
    .slice(0, limit);
}

export default function createIntelligenceRouter() {
  const router = Router();
  router.get('/learning/status', async (_req, res) => res.json(intelligenceLearningStatus()));

  // Soft daily CMS → KIP/KF/KC learner (IST learning_date calendar)
  startCmsArticleLearningScheduler(engineFetch);
  // Async CMS ingest job worker (HTTP enqueues; worker wakes engine + retries)
  startCmsIngestJobWorker(engineFetch);

  router.get('/health', async (_req, res) => {
    try {
      // Short probe — never leave Mission Control / KOC waiting on a dead engine.
      const result = await engineFetch('/v1/health', { timeoutMs: 8_000 });
      return res.status(result.ok ? 200 : 503).json({
        gateway: 'agi-node',
        engine: result.data,
        engineStatus: result.status,
        ok: result.ok,
      });
    } catch (error) {
      return res.status(503).json({
        gateway: 'agi-node',
        ok: false,
        degraded: true,
        error: error.message,
        hint: 'Start intelligence-engine on INTELLIGENCE_ENGINE_URL (default http://127.0.0.1:8100)',
      });
    }
  });

  // Company Financials admin view. Keep the intelligence-engine private behind
  // the Node gateway, consistent with the rest of the browser-facing API.
  router.get(
    '/company/statements/:symbol',
    proxyGet((req) => `/v1/company/statements/${encodeURIComponent(req.params.symbol)}`),
  );

  router.get('/company/resolve', async (req, res) => {
    const query = String(req.query.q || '').trim();
    if (!query) return res.status(400).json({ error: 'Enter a company name or NSE symbol.' });
    try {
      const [match] = await companyMatches(query, 1);
      if (!match) return res.status(404).json({ error: `No listed company found for “${query}”.` });
      return res.json({ ok: true, ...match });
    } catch (error) {
      return res.status(503).json({ error: 'Company search is temporarily unavailable.', detail: error.message });
    }
  });

  router.get('/company/search', async (req, res) => {
    const query = String(req.query.q || '').trim();
    if (query.length < 2) return res.json({ ok: true, results: [] });
    try {
      return res.json({ ok: true, results: await companyMatches(query, 8) });
    } catch (error) {
      return res.status(503).json({ error: 'Company search is temporarily unavailable.', detail: error.message });
    }
  });

  router.post('/research/runs', proxyPost('/v1/research/runs'));
  router.get('/research/runs', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/research/runs${qs ? `?${qs}` : ''}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  });
  router.get(
    '/research/runs/:runId',
    proxyGet((req) => `/v1/research/runs/${encodeURIComponent(req.params.runId)}`),
  );

  // Portfolio Office
  router.get('/portfolio/models', proxyGet('/v1/portfolio/models'));
  router.post('/portfolio/normalize', proxyPost('/v1/portfolio/normalize'));
  router.post('/portfolio/ingest', proxyPost('/v1/portfolio/ingest'));
  router.post('/portfolio/scenario', proxyPost('/v1/portfolio/scenario'));
  router.post('/portfolio/office', proxyPost('/v1/portfolio/office'));

  // Investment Office
  router.get('/investment-office/playbooks', proxyGet('/v1/investment-office/playbooks'));
  router.post('/investment-office/package', proxyPost('/v1/investment-office/package'));
  router.post('/investment-office/scenario', proxyPost('/v1/investment-office/scenario'));
  router.post('/investment-office/run', proxyPost('/v1/investment-office/run'));

  // System integration inventory (Macro / Sector / Market / Research stack)
  router.get('/system/intelligence-stack', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/system/intelligence-stack');
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  });

  router.post('/system/intelligence-stack/bootstrap', async (req, res) => {
    try {
      const result = await engineFetch('/v1/system/intelligence-stack/bootstrap', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  });

  // AGIB v4.0 — Research Intelligence Hub (research notes as Intelligence Objects)
  router.get('/rih/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/rih/health');
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  });

  router.get('/research/hub', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/research/hub${qs ? `?${qs}` : ''}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  });

  router.get('/research/hub/dashboard', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/research/hub/dashboard');
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  });

  router.post('/research/hub/run', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research/hub/run', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  });

  router.post('/research/hub/build', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research/hub/build', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  });

  router.get('/research/hub/:noteId/graph', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/research/hub/${encodeURIComponent(req.params.noteId)}/graph`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  });

  router.get('/research/hub/:noteId/history', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(
        `/v1/research/hub/${encodeURIComponent(req.params.noteId)}/history${qs ? `?${qs}` : ''}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  });

  router.get('/research/hub/:noteId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/research/hub/${encodeURIComponent(req.params.noteId)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence engine unavailable', detail: error.message });
    }
  });

  // CMS → KIP: enqueue only. Never wait on Render wake inside the request.
  router.post('/kip/ingest/agi', async (req, res) => {
    try {
      const job = await enqueueCmsIngestJob(req.body || {});
      return res.status(202).json({
        ...job,
        queued: true,
        pending: !job.completed,
        architecture: 'async_job_queue',
        poll: `/api/intelligence/cms/ingest-jobs/${job.job_id || job.id}`,
      });
    } catch (error) {
      const status = error?.status && Number(error.status) >= 400 ? Number(error.status) : 503;
      return res.status(status).json({
        error: status === 400 ? error.message : 'Intelligence ingest unavailable',
        detail: error.message,
        hint: 'Job queue could not accept the ingest. Draft remains safe in CMS.',
      });
    }
  });

  // Poll ingest job status (browser-friendly short requests).
  router.get('/cms/ingest-jobs/:jobId', async (req, res) => {
    try {
      const job = await getIngestJob(req.params.jobId);
      if (!job) {
        return res.status(404).json({ error: 'Ingest job not found', job_id: req.params.jobId });
      }
      return res.status(200).json(job);
    } catch (error) {
      return res.status(503).json({
        error: 'Unable to read ingest job',
        detail: error.message,
      });
    }
  });

  // Stuck-job monitor for ops / Mission Control soft wiring.
  router.get('/cms/ingest-jobs-stuck', async (req, res) => {
    try {
      const processingOlderThanMs = req.query.processing_ms
        ? Number(req.query.processing_ms)
        : undefined;
      const queuedOlderThanMs = req.query.queued_ms ? Number(req.query.queued_ms) : undefined;
      const result = await getStuckIngestJobs({ processingOlderThanMs, queuedOlderThanMs });
      return res.status(result.alert ? 200 : 200).json({
        ...result,
        worker: getWorkerInfo(),
      });
    } catch (error) {
      return res.status(503).json({
        error: 'Unable to scan stuck ingest jobs',
        detail: error.message,
      });
    }
  });

  // Manual tick / reclaim (useful after deploys or when using external worker health checks).
  router.post('/cms/ingest-jobs/tick', async (req, res) => {
    try {
      const reclaimed = await reclaimStalledJobs();
      const processed = await processIngestQueue();
      return res.status(200).json({
        ok: true,
        reclaimed,
        processed,
        worker: getWorkerInfo(),
      });
    } catch (error) {
      return res.status(503).json({
        error: 'Ingest worker tick failed',
        detail: error.message,
      });
    }
  });

  // Soft pipeline blueprint (existing AGIB layers only — no new engines).
  router.get('/cms/ingest-pipeline', (_req, res) => {
    return res.status(200).json({
      ok: true,
      worker: getWorkerInfo(),
      blueprint: getPipelineBlueprint(),
    });
  });

  router.get('/cms/knowledge-card/:articleId', async (req, res) => {
    try {
      const card = await getResearchKnowledgeCard(req.params.articleId);
      if (!card) return res.status(404).json({ error: 'knowledge_card_not_found' });
      return res.json({ ok: true, ...card });
    } catch (error) {
      return res.status(503).json({ error: 'knowledge_registry_unavailable', detail: error.message });
    }
  });

  // Replay terminal job with stored payload (optional new embedding_version).
  router.post('/cms/ingest-jobs/:jobId/replay', async (req, res) => {
    try {
      const body = req.body || {};
      const job = await replayIngestJob(req.params.jobId, {
        embeddingVersion: body.embedding_version || body.embeddingVersion || null,
        priority: body.priority ?? null,
      });
      return res.status(202).json({
        ...job,
        queued: true,
        architecture: 'async_job_queue',
        poll: `/api/intelligence/cms/ingest-jobs/${job.job_id || job.id}`,
      });
    } catch (error) {
      const status = error?.status && Number(error.status) >= 400 ? Number(error.status) : 503;
      return res.status(status).json({
        error: error.message || 'Replay failed',
        detail: error.message,
      });
    }
  });

  // Human approval gate for require_approval jobs.
  router.post('/cms/ingest-jobs/:jobId/approve', async (req, res) => {
    try {
      const job = await approveIngestJob(req.params.jobId, {
        approvedBy: req.body?.approved_by || req.body?.approvedBy || null,
      });
      return res.status(200).json(job);
    } catch (error) {
      const status = error?.status && Number(error.status) >= 400 ? Number(error.status) : 503;
      return res.status(status).json({
        error: error.message || 'Approve failed',
        detail: error.message,
      });
    }
  });

  // CMS bulk learn — read uploaded articles into KIP and stamp learning dates (daily).
  router.post('/cms/learn-articles', async (req, res) => {
    try {
      const body = req.body || {};
      const result = await learnCmsArticles({
        engineFetch,
        limit: body.limit,
        onlyUnlearned: Boolean(body.only_unlearned ?? body.onlyUnlearned),
        sinceDate: body.since_date || body.sinceDate || null,
        mode: body.mode || null,
        compound: body.compound !== false,
      });
      const status = result?.ok ? 200 : result?.skipped ? 503 : 500;
      return res.status(status).json(result);
    } catch (error) {
      return res.status(503).json({
        error: 'CMS article learning unavailable',
        detail: error.message,
      });
    }
  });

  router.get('/cms/learning-status', async (req, res) => {
    try {
      const days = req.query.days ? Number(req.query.days) : 14;
      const result = await cmsLearningStatus({ days });
      const status = result?.ok ? 200 : result?.skipped ? 503 : 500;
      return res.status(status).json(result);
    } catch (error) {
      return res.status(503).json({
        error: 'CMS learning status unavailable',
        detail: error.message,
      });
    }
  });

  router.get('/cms/learning-summary', async (req, res) => {
    try {
      const days = req.query.days ? Number(req.query.days) : 5;
      const result = await buildRecentLearningSummary({ engineFetch, days });
      return res.status(result?.ok ? 200 : 503).json(result);
    } catch (error) {
      return res.status(503).json({
        error: 'CMS learning summary unavailable',
        detail: error.message,
      });
    }
  });

  router.get('/kip/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/kip/health');
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'KIP unavailable', detail: error.message });
    }
  });

  router.get('/kip/integrity', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/kip/integrity${qs ? `?${qs}` : ''}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'KIP integrity unavailable', detail: error.message });
    }
  });

  router.get('/kip/verify/:documentId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/kip/verify/${encodeURIComponent(req.params.documentId)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'KIP verify unavailable', detail: error.message });
    }
  });

  router.post('/kip/snapshot/save', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/kip/snapshot/save', { method: 'POST', body: {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'KIP snapshot save unavailable', detail: error.message });
    }
  });

  // KF1 Knowledge Foundation — structured knowledge objects over KIP.
  const kfGet2 = (basePath) => async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const seg = encodeURIComponent(Object.values(req.params || {})[0] || '');
      const r = await engineFetch(`${basePath}/${seg}${qs ? `?${qs}` : ''}`);
      return res.status(r.status).json(r.data);
    } catch (error) {
      return res.status(503).json({ error: 'Engine unavailable', detail: error.message });
    }
  };

  const kfGet = (enginePath) => async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const suffix = qs ? `?${qs}` : '';
      const result = await engineFetch(`${enginePath}${suffix}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge Foundation unavailable', detail: error.message });
    }
  };

  const kfPost = (enginePath) => async (_req, res) => {
    try {
      const result = await engineFetch(enginePath, { method: 'POST', body: {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge Foundation unavailable', detail: error.message });
    }
  };

  router.get('/kf/health', kfGet('/v1/kf/health'));
  router.get('/kf/coverage', kfGet('/v1/kf/coverage'));
  router.post('/kf/seed', kfPost('/v1/kf/seed'));
  router.post('/kf/rebuild', kfPost('/v1/kf/rebuild'));
  router.get('/kf/search', kfGet('/v1/kf/search'));
  router.get('/kf/companies', kfGet('/v1/kf/companies'));
  router.get('/kf/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/kf/company/${encodeURIComponent(req.params.ticker)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge Foundation unavailable', detail: error.message });
    }
  });
  router.get('/kf/sectors', kfGet('/v1/kf/sectors'));
  router.get('/kf/sector/:sectorId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/kf/sector/${encodeURIComponent(req.params.sectorId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge Foundation unavailable', detail: error.message });
    }
  });
  router.get('/kf/themes', kfGet('/v1/kf/themes'));
  router.get('/kf/theme/:themeId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/kf/theme/${encodeURIComponent(req.params.themeId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge Foundation unavailable', detail: error.message });
    }
  });
  router.get('/kf/macros', kfGet('/v1/kf/macros'));
  router.get('/kf/macro/:macroId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/kf/macro/${encodeURIComponent(req.params.macroId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge Foundation unavailable', detail: error.message });
    }
  });
  router.get('/kf/predictions', kfGet('/v1/kf/predictions'));
  router.get('/kf/extracts', kfGet('/v1/kf/extracts'));

  // KCV1 Knowledge Corpus — populate/improve KF; no redesign.
  router.get('/kc/health', kfGet('/v1/kc/health'));
  router.get('/kc/metrics', kfGet('/v1/kc/metrics'));
  router.get('/kc/dashboard', kfGet('/v1/kc/dashboard'));
  router.post('/kc/populate', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/kc/populate${qs ? `?${qs}` : ''}`, {
        method: 'POST',
        body: {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge Corpus unavailable', detail: error.message });
    }
  });
  router.post('/kc/universe', kfPost('/v1/kc/universe'));
  router.get('/kc/gaps', kfGet('/v1/kc/gaps'));
  router.get('/kc/learning', kfGet('/v1/kc/learning'));
  router.get('/kc/quality', kfGet('/v1/kc/quality'));
  router.get('/kc/consult', kfGet('/v1/kc/consult'));

  // AOI v1 — Open Intelligence acquisition platform (no core redesign).
  router.get('/aoi/health', kfGet('/v1/aoi/health'));
  router.get('/aoi/dashboard', kfGet('/v1/aoi/dashboard'));
  router.post('/aoi/registry/seed', kfPost('/v1/aoi/registry/seed'));
  router.post('/aoi/run', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/aoi/run${qs ? `?${qs}` : ''}`, {
        method: 'POST',
        body: {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Open Intelligence unavailable', detail: error.message });
    }
  });
  router.get('/aoi/companies', kfGet('/v1/aoi/companies'));
  router.get('/aoi/company/:key', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/aoi/company/${encodeURIComponent(req.params.key)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Open Intelligence unavailable', detail: error.message });
    }
  });
  router.get('/aoi/search', kfGet('/v1/aoi/search'));
  router.get('/aoi/consult', kfGet('/v1/aoi/consult'));
  router.get('/aoi/connectors', kfGet('/v1/aoi/connectors'));
  router.get('/aoi/scheduler', kfGet('/v1/aoi/scheduler'));
  router.get('/aoi/gaps', kfGet('/v1/aoi/gaps'));
  router.get('/aoi/learning', kfGet('/v1/aoi/learning'));

  // EVE v1 — Evidence & Verification Engine (between AOI and KCV/KF).
  router.get('/eve/health', kfGet('/v1/eve/health'));
  router.get('/eve/dashboard', kfGet('/v1/eve/dashboard'));
  router.get('/eve/evidence', kfGet('/v1/eve/evidence'));
  router.get('/eve/evidence/:evidenceId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/eve/evidence/${encodeURIComponent(req.params.evidenceId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Evidence engine unavailable', detail: error.message });
    }
  });
  router.get('/eve/company/:key', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/eve/company/${encodeURIComponent(req.params.key)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Evidence engine unavailable', detail: error.message });
    }
  });
  router.get('/eve/conflicts', kfGet('/v1/eve/conflicts'));
  router.get('/eve/timeline', kfGet('/v1/eve/timeline'));
  router.get('/eve/trust', kfGet('/v1/eve/trust'));
  router.get('/eve/source', kfGet('/v1/eve/source'));
  router.get('/eve/verification', kfGet('/v1/eve/verification'));
  router.post('/eve/verification/run', kfPost('/v1/eve/verification/run'));
  router.get('/eve/search', kfGet('/v1/eve/search'));
  router.get('/eve/consult', kfGet('/v1/eve/consult'));
  router.get('/eve/audit', kfGet('/v1/eve/audit'));

  // IIE v1 — Investment Intelligence Engine (after EVE/KCV/KF, before reasoning).
  router.get('/iie/health', kfGet('/v1/iie/health'));
  router.get('/iie/dashboard', kfGet('/v1/iie/dashboard'));
  router.post('/iie/analyse', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/iie/analyse${qs ? `?${qs}` : ''}`, { method: 'POST', body: {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Investment intelligence unavailable', detail: error.message });
    }
  });
  router.post('/iie/batch', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/iie/batch${qs ? `?${qs}` : ''}`, { method: 'POST', body: {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Investment intelligence unavailable', detail: error.message });
    }
  });
  router.get('/iie/company/:key', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/iie/company/${encodeURIComponent(req.params.key)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Investment intelligence unavailable', detail: error.message });
    }
  });
  router.get('/iie/sector', kfGet('/v1/iie/sector'));
  router.get('/iie/sector/:sectorId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/iie/sector/${encodeURIComponent(req.params.sectorId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Investment intelligence unavailable', detail: error.message });
    }
  });
  router.get('/iie/theme', kfGet('/v1/iie/theme'));
  router.get('/iie/theme/:themeId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/iie/theme/${encodeURIComponent(req.params.themeId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Investment intelligence unavailable', detail: error.message });
    }
  });
  router.get('/iie/thesis/:key', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/iie/thesis/${encodeURIComponent(req.params.key)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Investment intelligence unavailable', detail: error.message });
    }
  });
  router.get('/iie/scenario/:key', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/iie/scenario/${encodeURIComponent(req.params.key)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Investment intelligence unavailable', detail: error.message });
    }
  });
  router.get('/iie/catalysts', kfGet('/v1/iie/catalysts'));
  router.get('/iie/risks', kfGet('/v1/iie/risks'));
  router.get('/iie/opportunities', kfGet('/v1/iie/opportunities'));
  router.get('/iie/compare', kfGet('/v1/iie/compare'));
  router.get('/iie/monitor/:key', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/iie/monitor/${encodeURIComponent(req.params.key)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Investment intelligence unavailable', detail: error.message });
    }
  });
  router.get('/iie/dna/:key', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/iie/dna/${encodeURIComponent(req.params.key)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Investment intelligence unavailable', detail: error.message });
    }
  });
  router.get('/iie/macro', kfGet('/v1/iie/macro'));
  router.get('/iie/evolution', kfGet('/v1/iie/evolution'));
  router.get('/iie/search', kfGet('/v1/iie/search'));
  router.get('/iie/consult', kfGet('/v1/iie/consult'));

  // FLE v1 — Forecasting & Learning Engine (after IIE, before reasoning).
  // FAA v1 — Finance Acquisition Agent (upstream live acquisition; feeds FRE).
  router.get('/faa/health', kfGet('/v1/faa/health'));
  router.get('/faa/dashboard', kfGet('/v1/faa/dashboard'));
  router.get('/faa/discover', kfGet('/v1/faa/discover'));
  router.get('/faa/connectors', kfGet('/v1/faa/connectors'));
  router.get('/faa/scheduler', kfGet('/v1/faa/scheduler'));
  router.get('/faa/consult', kfGet('/v1/faa/consult'));
  router.post('/faa/acquire', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/faa/acquire${qs ? `?${qs}` : ''}`, {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance acquisition agent unavailable', detail: error.message });
    }
  });
  router.post('/faa/jobs', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/faa/jobs', { method: 'POST', body: {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance acquisition agent unavailable', detail: error.message });
    }
  });

  // FRE v1 — Finance Retrieval Engine (evidence retrieval & rank; never answers).
  router.get('/fre/health', kfGet('/v1/fre/health'));
  router.get('/fre/dashboard', kfGet('/v1/fre/dashboard'));
  router.get('/fre/query', kfGet('/v1/fre/query'));
  router.get('/fre/search', kfGet('/v1/fre/search'));
  router.get('/fre/company/:key', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(
        `/v1/fre/company/${encodeURIComponent(req.params.key)}${qs ? `?${qs}` : ''}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance retrieval engine unavailable', detail: error.message });
    }
  });
  router.get('/fre/document/:documentId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/fre/document/${encodeURIComponent(req.params.documentId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance retrieval engine unavailable', detail: error.message });
    }
  });
  router.get('/fre/evidence', kfGet('/v1/fre/evidence'));
  router.get('/fre/timeline', kfGet('/v1/fre/timeline'));
  router.get('/fre/news', kfGet('/v1/fre/news'));
  router.get('/fre/graph', kfGet('/v1/fre/graph'));
  router.get('/fre/scheduler', kfGet('/v1/fre/scheduler'));
  router.get('/fre/consult', kfGet('/v1/fre/consult'));
  router.post('/fre/ingest', async (req, res) => {
    try {
      const result = await engineFetch('/v1/fre/ingest', { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance retrieval engine unavailable', detail: error.message });
    }
  });
  router.post('/fre/jobs', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/fre/jobs', { method: 'POST', body: {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance retrieval engine unavailable', detail: error.message });
    }
  });

  router.get('/fle/health', kfGet('/v1/fle/health'));
  router.get('/fle/dashboard', kfGet('/v1/fle/dashboard'));
  router.get('/fle/forecast', kfGet('/v1/fle/forecast'));
  router.post('/fle/forecast', async (req, res) => {
    try {
      const result = await engineFetch('/v1/fle/forecast', { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecasting engine unavailable', detail: error.message });
    }
  });
  router.get('/fle/forecast/:forecastId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/fle/forecast/${encodeURIComponent(req.params.forecastId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecasting engine unavailable', detail: error.message });
    }
  });
  router.post('/fle/forecast/:forecastId/resolve', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/fle/forecast/${encodeURIComponent(req.params.forecastId)}/resolve`,
        { method: 'POST', body: req.body || {} }
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecasting engine unavailable', detail: error.message });
    }
  });
  router.post('/fle/forecast/:forecastId/version', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/fle/forecast/${encodeURIComponent(req.params.forecastId)}/version`,
        { method: 'POST', body: req.body || {} }
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecasting engine unavailable', detail: error.message });
    }
  });
  router.get('/fle/compare/:forecastId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/fle/compare/${encodeURIComponent(req.params.forecastId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecasting engine unavailable', detail: error.message });
    }
  });
  router.get('/fle/company/:key', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/fle/company/${encodeURIComponent(req.params.key)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecasting engine unavailable', detail: error.message });
    }
  });
  router.get('/fle/outcomes', kfGet('/v1/fle/outcomes'));
  router.get('/fle/learning', kfGet('/v1/fle/learning'));
  router.get('/fle/calibration', kfGet('/v1/fle/calibration'));
  router.get('/fle/scenarios/:forecastId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/fle/scenarios/${encodeURIComponent(req.params.forecastId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecasting engine unavailable', detail: error.message });
    }
  });
  router.get('/fle/accuracy', kfGet('/v1/fle/accuracy'));
  router.get('/fle/history', kfGet('/v1/fle/history'));
  router.post('/fle/generate', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/fle/generate${qs ? `?${qs}` : ''}`, { method: 'POST', body: {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecasting engine unavailable', detail: error.message });
    }
  });
  router.post('/fle/batch', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/fle/batch${qs ? `?${qs}` : ''}`, { method: 'POST', body: {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecasting engine unavailable', detail: error.message });
    }
  });
  router.post('/fle/jobs', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/fle/jobs', { method: 'POST', body: {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecasting engine unavailable', detail: error.message });
    }
  });
  router.get('/fle/search', kfGet('/v1/fle/search'));
  router.get('/fle/consult', kfGet('/v1/fle/consult'));

  // MEE v1 — Market Event Engine (after FLE; event backbone).
  router.get('/mee/health', kfGet('/v1/mee/health'));
  router.get('/mee/dashboard', kfGet('/v1/mee/dashboard'));
  router.get('/mee/events', kfGet('/v1/mee/events'));
  router.post('/mee/events', async (req, res) => {
    try {
      const result = await engineFetch('/v1/mee/events', { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Market event engine unavailable', detail: error.message });
    }
  });
  router.get('/mee/events/:eventId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/mee/events/${encodeURIComponent(req.params.eventId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Market event engine unavailable', detail: error.message });
    }
  });
  router.post('/mee/events/:eventId/verify', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/mee/events/${encodeURIComponent(req.params.eventId)}/verify`,
        { method: 'POST', body: {} }
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Market event engine unavailable', detail: error.message });
    }
  });
  router.post('/mee/events/:eventId/version', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/mee/events/${encodeURIComponent(req.params.eventId)}/version`,
        { method: 'POST', body: req.body || {} }
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Market event engine unavailable', detail: error.message });
    }
  });
  router.get('/mee/company/:key', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/mee/company/${encodeURIComponent(req.params.key)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Market event engine unavailable', detail: error.message });
    }
  });
  router.get('/mee/sector/:sectorId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/mee/sector/${encodeURIComponent(req.params.sectorId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Market event engine unavailable', detail: error.message });
    }
  });
  router.get('/mee/theme/:themeId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/mee/theme/${encodeURIComponent(req.params.themeId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Market event engine unavailable', detail: error.message });
    }
  });
  router.get('/mee/timeline', kfGet('/v1/mee/timeline'));
  router.get('/mee/impact/:eventId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/mee/impact/${encodeURIComponent(req.params.eventId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Market event engine unavailable', detail: error.message });
    }
  });
  router.get('/mee/relationships', kfGet('/v1/mee/relationships'));
  router.get('/mee/history', kfGet('/v1/mee/history'));
  router.get('/mee/similar/:eventId', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(
        `/v1/mee/similar/${encodeURIComponent(req.params.eventId)}${qs ? `?${qs}` : ''}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Market event engine unavailable', detail: error.message });
    }
  });
  router.post('/mee/cycle', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/mee/cycle${qs ? `?${qs}` : ''}`, { method: 'POST', body: {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Market event engine unavailable', detail: error.message });
    }
  });
  router.get('/mee/search', kfGet('/v1/mee/search'));
  router.get('/mee/consult', kfGet('/v1/mee/consult'));

  // CAE v1 — Context Assembly Engine (Ask AGI orchestration gateway).
  router.get('/cae/health', kfGet('/v1/cae/health'));
  router.get('/cae/dashboard', kfGet('/v1/cae/dashboard'));
  router.get('/cae/context', kfGet('/v1/cae/context'));
  router.get('/cae/query-plan', kfGet('/v1/cae/query-plan'));
  router.get('/cae/retrieval', kfGet('/v1/cae/retrieval'));
  router.get('/cae/cache', kfGet('/v1/cae/cache'));
  router.post('/cae/cache/clear', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/cae/cache/clear', { method: 'POST', body: {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Context assembly unavailable', detail: error.message });
    }
  });
  router.get('/cae/metrics', kfGet('/v1/cae/metrics'));
  router.get('/cae/explain/:packageId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/cae/explain/${encodeURIComponent(req.params.packageId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Context assembly unavailable', detail: error.message });
    }
  });
  router.get('/cae/package/:packageId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/cae/package/${encodeURIComponent(req.params.packageId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Context assembly unavailable', detail: error.message });
    }
  });
  router.get('/cae/search', kfGet('/v1/cae/search'));

  // IB v1 — AGI Intelligence Bus (event-driven backbone).
  router.get('/ib/health', kfGet('/v1/ib/health'));
  router.get('/ib/dashboard', kfGet('/v1/ib/dashboard'));
  router.get('/ib/events', kfGet('/v1/ib/events'));
  router.post('/ib/publish', async (req, res) => {
    try {
      const result = await engineFetch('/v1/ib/publish', { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence bus unavailable', detail: error.message });
    }
  });
  router.get('/ib/subscriptions', kfGet('/v1/ib/subscriptions'));
  router.post('/ib/subscriptions', async (req, res) => {
    try {
      const result = await engineFetch('/v1/ib/subscriptions', { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence bus unavailable', detail: error.message });
    }
  });
  router.post('/ib/replay', async (req, res) => {
    try {
      const result = await engineFetch('/v1/ib/replay', { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence bus unavailable', detail: error.message });
    }
  });
  router.get('/ib/history', kfGet('/v1/ib/history'));
  router.get('/ib/metrics', kfGet('/v1/ib/metrics'));
  router.get('/ib/traces', kfGet('/v1/ib/traces'));
  router.get('/ib/dead-letter', kfGet('/v1/ib/dead-letter'));
  router.post('/ib/dead-letter/:dlqId/resolve', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/ib/dead-letter/${encodeURIComponent(req.params.dlqId)}/resolve`,
        { method: 'POST', body: {} }
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence bus unavailable', detail: error.message });
    }
  });
  router.get('/ib/schema', kfGet('/v1/ib/schema'));
  router.post('/ib/demo-chain', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const result = await engineFetch(`/v1/ib/demo-chain${qs ? `?${qs}` : ''}`, {
        method: 'POST',
        body: {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Intelligence bus unavailable', detail: error.message });
    }
  });

  // VE v1 — Valuation Engine (intrinsic value platform).
  router.get('/ve/health', kfGet('/v1/ve/health'));
  router.get('/ve/dashboard', kfGet('/v1/ve/dashboard'));
  router.get('/ve/company/:key', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const result = await engineFetch(
        `/v1/ve/company/${encodeURIComponent(req.params.key)}${qs ? `?${qs}` : ''}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Valuation engine unavailable', detail: error.message });
    }
  });
  router.get('/ve/model', kfGet('/v1/ve/model'));
  router.get('/ve/history', kfGet('/v1/ve/history'));
  router.get('/ve/scenarios', kfGet('/v1/ve/scenarios'));
  router.get('/ve/compare', kfGet('/v1/ve/compare'));
  router.get('/ve/sensitivity', kfGet('/v1/ve/sensitivity'));
  router.get('/ve/search', kfGet('/v1/ve/search'));
  router.get('/ve/consult', kfGet('/v1/ve/consult'));
  router.post('/ve/value', async (req, res) => {
    try {
      const result = await engineFetch('/v1/ve/value', { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Valuation engine unavailable', detail: error.message });
    }
  });
  router.get('/ve/valuation/:valuationId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/ve/valuation/${encodeURIComponent(req.params.valuationId)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Valuation engine unavailable', detail: error.message });
    }
  });

  // FIML v1 — Financial Intelligence Model Library (not an engine).
  router.get('/fiml/health', kfGet('/v1/fiml/health'));
  router.get('/fiml/dashboard', kfGet('/v1/fiml/dashboard'));
  router.get('/fiml/models', kfGet('/v1/fiml/models'));
  router.get('/fiml/industries', kfGet('/v1/fiml/industries'));
  router.get('/fiml/search', kfGet('/v1/fiml/search'));
  router.get('/fiml/metrics', kfGet('/v1/fiml/metrics'));
  router.get('/fiml/graph', kfGet('/v1/fiml/graph'));
  router.post('/fiml/analyse/:domain', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/fiml/analyse/${encodeURIComponent(req.params.domain)}`, {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'FIML unavailable', detail: error.message });
    }
  });
  router.post('/fiml/score/:domain', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/fiml/score/${encodeURIComponent(req.params.domain)}`, {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'FIML unavailable', detail: error.message });
    }
  });
  router.post('/fiml/explain/:domain', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/fiml/explain/${encodeURIComponent(req.params.domain)}`, {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'FIML unavailable', detail: error.message });
    }
  });
  router.post('/fiml/compare/:domain', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/fiml/compare/${encodeURIComponent(req.params.domain)}`, {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'FIML unavailable', detail: error.message });
    }
  });
  router.post('/fiml/bundle', async (req, res) => {
    try {
      const result = await engineFetch('/v1/fiml/bundle', { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'FIML unavailable', detail: error.message });
    }
  });
  router.post('/fiml/consumer/:engine', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/fiml/consumer/${encodeURIComponent(req.params.engine)}`, {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'FIML unavailable', detail: error.message });
    }
  });

  // AGI Finance Academy v1.1 — multi-course curriculum library (not an engine).
  router.get('/academy/health', kfGet('/v1/academy/health'));
  router.get('/academy/dashboard', kfGet('/v1/academy/dashboard'));
  router.get('/academy/courses', kfGet('/v1/academy/courses'));
  router.get('/academy/course', kfGet('/v1/academy/course'));
  router.get('/academy/concepts', kfGet('/v1/academy/concepts'));
  router.get('/academy/concepts/:conceptId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/academy/concepts/${encodeURIComponent(req.params.conceptId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance Academy unavailable', detail: error.message });
    }
  });
  router.get('/academy/teach/:conceptId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/academy/teach/${encodeURIComponent(req.params.conceptId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance Academy unavailable', detail: error.message });
    }
  });
  router.get('/academy/graph', kfGet('/v1/academy/graph'));
  router.get('/academy/neighborhood/:conceptId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/academy/neighborhood/${encodeURIComponent(req.params.conceptId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance Academy unavailable', detail: error.message });
    }
  });
  router.get('/academy/causal-models', kfGet('/v1/academy/causal-models'));
  router.get('/academy/mental-models', kfGet('/v1/academy/mental-models'));
  router.get('/academy/quality', kfGet('/v1/academy/quality'));
  router.get('/academy/provenance', kfGet('/v1/academy/provenance'));
  router.get('/academy/exams', kfGet('/v1/academy/exams'));
  router.get('/academy/exams/:questionId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/academy/exams/${encodeURIComponent(req.params.questionId)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance Academy unavailable', detail: error.message });
    }
  });
  router.get('/academy/search', kfGet('/v1/academy/search'));
  router.get('/academy/red-flags', kfGet('/v1/academy/red-flags'));
  router.get('/academy/accounting', kfGet('/v1/academy/accounting'));
  router.get('/academy/corporate-finance', kfGet('/v1/academy/corporate-finance'));
  router.get('/academy/completion', kfGet('/v1/academy/completion'));
  router.get('/academy/metrics', kfGet('/v1/academy/metrics'));
  router.get('/academy/production', kfGet('/v1/academy/production'));
  router.get('/academy/production/ab', kfGet('/v1/academy/production/ab'));
  router.get('/academy/production/quality-gates', kfGet('/v1/academy/production/quality-gates'));
  router.post('/academy/production/package', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.query) qs.set('query', String(req.query.query));
      if (req.query.engine) qs.set('engine', String(req.query.engine));
      if (req.query.ticker) qs.set('ticker', String(req.query.ticker));
      if (req.body?.query) qs.set('query', String(req.body.query));
      if (req.body?.engine) qs.set('engine', String(req.body.engine));
      if (req.body?.ticker) qs.set('ticker', String(req.body.ticker));
      const result = await engineFetch(`/v1/academy/production/package?${qs.toString()}`, {
        method: 'POST',
        body: req.body || {},
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Academy production package failed' });
    }
  });
  // AGI Academy Books V1 — structured institutional learning (not searchable PDFs)
  router.get('/academy/books/health', kfGet('/v1/academy/books/health'));
  router.get('/academy/books/dashboard', kfGet('/v1/academy/books/dashboard'));
  router.get('/academy/books/quality-gates', kfGet('/v1/academy/books/quality-gates'));
  router.get('/academy/books/graph', kfGet('/v1/academy/books/graph'));
  router.post('/academy/books/ingest', async (req, res) => {
    try {
      const result = await engineFetch('/v1/academy/books/ingest', {
        method: 'POST',
        body: req.body || {},
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Academy books ingest failed' });
    }
  });
  router.post('/academy/books/package', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      const query = req.query.query || req.body?.query;
      const ticker = req.query.ticker || req.body?.ticker;
      if (query) qs.set('query', String(query));
      if (ticker) qs.set('ticker', String(ticker));
      const result = await engineFetch(`/v1/academy/books/package?${qs.toString()}`, {
        method: 'POST',
        body: {},
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Academy books package failed' });
    }
  });
  router.post('/academy/books/attach-kf', async (req, res) => {
    try {
      const result = await engineFetch('/v1/academy/books/attach-kf', { method: 'POST', body: {} });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Academy books KF attach failed' });
    }
  });
  router.get('/academy/books/library', kfGet('/v1/academy/books/library'));
  router.get('/academy/books/ingestion-report', kfGet('/v1/academy/books/ingestion-report'));
  router.post('/academy/books/ingest-library', async (req, res) => {
    try {
      const result = await engineFetch('/v1/academy/books/ingest-library', {
        method: 'POST',
        body: req.body || {},
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Academy library ingest failed' });
    }
  });
  // SIF v1.0 — Sector Intelligence Framework (additive; not an engine)
  router.get('/sif/health', kfGet('/v1/sif/health'));
  router.get('/sif/dashboard', kfGet('/v1/sif/dashboard'));
  router.get('/sif/frameworks', kfGet('/v1/sif/frameworks'));
  router.get('/sif/frameworks/:sectorId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/sif/frameworks/${encodeURIComponent(req.params.sectorId)}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'SIF framework failed' });
    }
  });
  router.get('/sif/quality-gates', kfGet('/v1/sif/quality-gates'));
  router.post('/sif/analyse', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      const query = req.query.query || req.body?.query;
      const ticker = req.query.ticker || req.body?.ticker;
      const engine = req.query.engine || req.body?.engine || 'ask_agi';
      if (query) qs.set('query', String(query));
      if (ticker) qs.set('ticker', String(ticker));
      if (engine) qs.set('engine', String(engine));
      const result = await engineFetch(`/v1/sif/analyse?${qs.toString()}`, {
        method: 'POST',
        body: req.body || {},
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'SIF analyse failed' });
    }
  });
  router.post('/academy/red-flags/score', async (req, res) => {
    try {
      const result = await engineFetch('/v1/academy/red-flags/score', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance Academy unavailable', detail: error.message });
    }
  });
  router.post('/academy/earnings-quality', async (req, res) => {
    try {
      const result = await engineFetch('/v1/academy/earnings-quality', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance Academy unavailable', detail: error.message });
    }
  });
  router.post('/academy/consumer/:engine', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/academy/consumer/${encodeURIComponent(req.params.engine)}`, {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Finance Academy unavailable', detail: error.message });
    }
  });

  // Knowledge Factory — Decision Coverage / Historical / Sector / Macro (Sprints 1–6)
  router.get('/knowledge-factory/health', kfGet('/v1/knowledge-factory/health'));
  router.get('/knowledge-factory/dashboard', kfGet('/v1/knowledge-factory/dashboard'));
  router.get('/knowledge-factory/coverage', kfGet('/v1/knowledge-factory/coverage'));
  router.get('/knowledge-factory/decision-coverage', kfGet('/v1/knowledge-factory/decision-coverage'));
  router.get('/knowledge-factory/dimensions', kfGet('/v1/knowledge-factory/dimensions'));
  router.get('/knowledge-factory/daily-health', kfGet('/v1/knowledge-factory/daily-health'));
  router.get('/knowledge-factory/institutional-depth', kfGet('/v1/knowledge-factory/institutional-depth'));
  router.get('/knowledge-factory/institutional-depth/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/knowledge-factory/institutional-depth/${encodeURIComponent(req.params.ticker)}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'institutional-depth proxy failed' });
    }
  });
  router.get('/knowledge-factory/universe-tiers', kfGet('/v1/knowledge-factory/universe-tiers'));
  // AGIB v1.2 — Institutional Universe Intelligence (soft registry)
  router.get('/universe-intelligence/health', kfGet('/v1/universe-intelligence/health'));
  router.get('/universe-intelligence/dashboard', kfGet('/v1/universe-intelligence/dashboard'));
  router.post('/universe-intelligence/run', kfPost('/v1/universe-intelligence/run'));
  router.get('/universe-intelligence/universes', kfGet('/v1/universe-intelligence/universes'));
  router.get('/universe-intelligence/tree', kfGet('/v1/universe-intelligence/tree'));
  router.get('/universe-intelligence/quality-gates', kfGet('/v1/universe-intelligence/quality-gates'));
  router.get('/universe-intelligence/membership', async (req, res) => {
    try {
      const q = new URLSearchParams({
        ticker: String(req.query.ticker || ''),
        universe_id: String(req.query.universe_id || ''),
        as_of: String(req.query.as_of || ''),
      }).toString();
      const result = await engineFetch(`/v1/universe-intelligence/membership?${q}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'universe membership proxy failed' });
    }
  });
  router.get('/universe-intelligence/memberships/:ticker', async (req, res) => {
    try {
      const q = req.query.as_of ? `?as_of=${encodeURIComponent(String(req.query.as_of))}` : '';
      const result = await engineFetch(
        `/v1/universe-intelligence/memberships/${encodeURIComponent(req.params.ticker)}${q}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'universe memberships proxy failed' });
    }
  });
  router.get('/universe-intelligence/company/:ticker', async (req, res) => {
    try {
      const q = req.query.refresh ? '?refresh=true' : '';
      const result = await engineFetch(
        `/v1/universe-intelligence/company/${encodeURIComponent(req.params.ticker)}${q}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'universe company proxy failed' });
    }
  });
  router.get('/universe-intelligence/ici/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/universe-intelligence/ici/${encodeURIComponent(req.params.ticker)}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'ICI proxy failed' });
    }
  });
  // AGIB v2.0 Sprint 1 — Institutional Company Intelligence (soft KF; read-only)
  router.get('/company-intelligence/health', kfGet('/v1/company-intelligence/health'));
  router.get('/company-intelligence/dashboard', kfGet('/v1/company-intelligence/dashboard'));
  router.post('/company-intelligence/run', kfPost('/v1/company-intelligence/run'));
  router.get('/company-intelligence/coverage', kfGet('/v1/company-intelligence/coverage'));
  router.get('/company-intelligence/quality', kfGet('/v1/company-intelligence/quality'));
  router.get('/company-intelligence/search', async (req, res) => {
    try {
      const q = new URLSearchParams({
        q: String(req.query.q || ''),
        limit: String(req.query.limit || '25'),
      }).toString();
      const result = await engineFetch(`/v1/company-intelligence/search?${q}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'company-intelligence search proxy failed' });
    }
  });
  router.get('/company-intelligence/:ticker', async (req, res) => {
    try {
      const q = req.query.refresh ? '?refresh=true' : '';
      const result = await engineFetch(
        `/v1/company-intelligence/${encodeURIComponent(req.params.ticker)}${q}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'company-intelligence proxy failed' });
    }
  });
  // AGIB v2.0 Sprint 2 — Institutional Corporate Event Intelligence (soft KF)
  router.get('/corporate-events/health', kfGet('/v1/corporate-events/health'));
  router.get('/corporate-events/dashboard', kfGet('/v1/corporate-events/dashboard'));
  router.post('/corporate-events/run', kfPost('/v1/corporate-events/run'));
  router.get('/corporate-events/search', async (req, res) => {
    try {
      const q = new URLSearchParams({
        q: String(req.query.q || ''),
        limit: String(req.query.limit || '25'),
      }).toString();
      const result = await engineFetch(`/v1/corporate-events/search?${q}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'corporate-events search proxy failed' });
    }
  });
  router.get('/corporate-events/:ticker', async (req, res) => {
    try {
      const q = req.query.refresh ? '?refresh=true' : '';
      const result = await engineFetch(
        `/v1/corporate-events/${encodeURIComponent(req.params.ticker)}${q}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'corporate-events proxy failed' });
    }
  });
  router.get('/company-timeline/:ticker', async (req, res) => {
    try {
      const params = new URLSearchParams();
      if (req.query.as_of) params.set('as_of', String(req.query.as_of));
      if (req.query.refresh) params.set('refresh', 'true');
      const q = params.toString() ? `?${params}` : '';
      const result = await engineFetch(
        `/v1/company-timeline/${encodeURIComponent(req.params.ticker)}${q}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'company-timeline proxy failed' });
    }
  });
  router.get('/events/today', kfGet('/v1/events/today'));
  router.get('/events/critical', kfGet('/v1/events/critical'));
  // AGIB v2.0 Sprint 3 — Institutional Government & Regulatory Intelligence
  router.get('/government/health', kfGet('/v1/government/health'));
  router.get('/government/dashboard', kfGet('/v1/government/dashboard'));
  router.post('/government/run', kfPost('/v1/government/run'));
  router.get('/government/policies', kfGet('/v1/government/policies'));
  router.get('/government/search', async (req, res) => {
    try {
      const q = new URLSearchParams({
        q: String(req.query.q || ''),
        limit: String(req.query.limit || '25'),
      }).toString();
      const result = await engineFetch(`/v1/government/search?${q}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'government search proxy failed' });
    }
  });
  router.get('/government/rbi', kfGet('/v1/government/rbi'));
  router.get('/government/sebi', kfGet('/v1/government/sebi'));
  router.get('/government/budget', kfGet('/v1/government/budget'));
  router.get('/government/gst', kfGet('/v1/government/gst'));
  router.get('/government/pli', kfGet('/v1/government/pli'));
  router.get('/government/trade', kfGet('/v1/government/trade'));
  router.get('/government/timeline', async (req, res) => {
    try {
      const q = req.query.as_of ? `?as_of=${encodeURIComponent(String(req.query.as_of))}` : '';
      const result = await engineFetch(`/v1/government/timeline${q}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'government timeline proxy failed' });
    }
  });
  router.get('/government/policy/:policyId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/government/policy/${encodeURIComponent(req.params.policyId)}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'government policy proxy failed' });
    }
  });
  // AGIB v2.0 Sprint 4 — Institutional Industry & Value Chain Intelligence
  router.get('/industry/health', kfGet('/v1/industry/health'));
  router.get('/industry/dashboard', kfGet('/v1/industry/dashboard'));
  router.post('/industry/run', kfPost('/v1/industry/run'));
  router.get('/industry/search', async (req, res) => {
    try {
      const q = new URLSearchParams({
        q: String(req.query.q || ''),
        limit: String(req.query.limit || '25'),
      }).toString();
      const result = await engineFetch(`/v1/industry/search?${q}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'industry search proxy failed' });
    }
  });
  for (const mod of ['playbook', 'value-chain', 'accounting', 'valuation', 'cycles', 'kpis']) {
    router.get(`/industry/${mod}`, async (req, res) => {
      try {
        const q = new URLSearchParams({ name: String(req.query.name || '') }).toString();
        const result = await engineFetch(`/v1/industry/${mod}?${q}`);
        res.json(result);
      } catch (err) {
        res.status(502).json({ error: err?.message || `industry ${mod} proxy failed` });
      }
    });
  }
  router.get('/industry/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/industry/company/${encodeURIComponent(req.params.ticker)}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'industry company proxy failed' });
    }
  });
  // AGIB v2.0 Sprint 5 — Institutional Economic Relationship Intelligence (IERI)
  router.get('/relationship/health', kfGet('/v1/relationship/health'));
  router.get('/relationship/dashboard', kfGet('/v1/relationship/dashboard'));
  router.post('/relationship/run', kfPost('/v1/relationship/run'));
  router.get('/relationship/registry', kfGet('/v1/relationship/registry'));
  router.get('/relationship/search', async (req, res) => {
    try {
      const q = new URLSearchParams({
        q: String(req.query.q || ''),
        limit: String(req.query.limit || '50'),
      });
      if (req.query.semantics) q.set('semantics', String(req.query.semantics));
      if (req.query.relationship_type) q.set('relationship_type', String(req.query.relationship_type));
      if (req.query.as_of) q.set('as_of', String(req.query.as_of));
      const result = await engineFetch(`/v1/relationship/search?${q.toString()}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'relationship search proxy failed' });
    }
  });
  router.get('/relationship/path', async (req, res) => {
    try {
      const q = new URLSearchParams({
        source: String(req.query.source || ''),
        max_depth: String(req.query.max_depth || '3'),
        limit: String(req.query.limit || '25'),
      });
      if (req.query.target) q.set('target', String(req.query.target));
      if (req.query.semantics) q.set('semantics', String(req.query.semantics));
      if (req.query.relationship_type) q.set('relationship_type', String(req.query.relationship_type));
      if (req.query.as_of) q.set('as_of', String(req.query.as_of));
      const result = await engineFetch(`/v1/relationship/path?${q.toString()}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'relationship path proxy failed' });
    }
  });
  router.get('/relationship/replay', async (req, res) => {
    try {
      const q = new URLSearchParams({ as_of: String(req.query.as_of || '') }).toString();
      const result = await engineFetch(`/v1/relationship/replay?${q}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'relationship replay proxy failed' });
    }
  });
  router.get('/relationship/shock/:entity', async (req, res) => {
    try {
      const q = new URLSearchParams();
      if (req.query.direction) q.set('direction', String(req.query.direction));
      if (req.query.max_order) q.set('max_order', String(req.query.max_order));
      if (req.query.as_of) q.set('as_of', String(req.query.as_of));
      const qs = q.toString();
      const result = await engineFetch(
        `/v1/relationship/shock/${encodeURIComponent(req.params.entity)}${qs ? `?${qs}` : ''}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'relationship shock proxy failed' });
    }
  });
  for (const kind of ['company', 'industry', 'commodity', 'policy', 'macro', 'network']) {
    router.get(`/relationship/${kind}/:id`, async (req, res) => {
      try {
        const q = new URLSearchParams();
        if (req.query.as_of) q.set('as_of', String(req.query.as_of));
        if (req.query.depth) q.set('depth', String(req.query.depth));
        const qs = q.toString();
        const result = await engineFetch(
          `/v1/relationship/${kind}/${encodeURIComponent(req.params.id)}${qs ? `?${qs}` : ''}`
        );
        res.json(result);
      } catch (err) {
        res.status(502).json({ error: err?.message || `relationship ${kind} proxy failed` });
      }
    });
  }
  router.get('/industry/:name', async (req, res) => {
    try {
      const q = req.query.refresh ? '?refresh=true' : '';
      const result = await engineFetch(
        `/v1/industry/${encodeURIComponent(req.params.name)}${q}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'industry proxy failed' });
    }
  });
  // AGIB v2.0 Sprint 6 — Institutional Alternative Data Intelligence (IADI)
  router.get('/alternative-data/health', kfGet('/v1/alternative-data/health'));
  router.get('/alternative-data/dashboard', kfGet('/v1/alternative-data/dashboard'));
  router.post('/alternative-data/run', kfPost('/v1/alternative-data/run'));
  router.get('/alternative-data/registry', kfGet('/v1/alternative-data/registry'));
  router.get('/alternative-data/search', async (req, res) => {
    try {
      const q = new URLSearchParams({
        q: String(req.query.q || ''),
        limit: String(req.query.limit || '25'),
      }).toString();
      const result = await engineFetch(`/v1/alternative-data/search?${q}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'alternative-data search proxy failed' });
    }
  });
  router.get('/alternative-data/trends', async (req, res) => {
    try {
      const q = new URLSearchParams();
      if (req.query.dataset) q.set('dataset', String(req.query.dataset));
      if (req.query.as_of) q.set('as_of', String(req.query.as_of));
      const qs = q.toString();
      const result = await engineFetch(`/v1/alternative-data/trends${qs ? `?${qs}` : ''}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'alternative-data trends proxy failed' });
    }
  });
  router.get('/alternative-data/replay', async (req, res) => {
    try {
      const q = new URLSearchParams({ as_of: String(req.query.as_of || '') });
      if (req.query.dataset) q.set('dataset', String(req.query.dataset));
      const result = await engineFetch(`/v1/alternative-data/replay?${q.toString()}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'alternative-data replay proxy failed' });
    }
  });
  router.get('/alternative-data/dataset/:name', async (req, res) => {
    try {
      const q = req.query.as_of ? `?as_of=${encodeURIComponent(String(req.query.as_of))}` : '';
      const result = await engineFetch(
        `/v1/alternative-data/dataset/${encodeURIComponent(req.params.name)}${q}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'alternative-data dataset proxy failed' });
    }
  });
  router.get('/alternative-data/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/alternative-data/company/${encodeURIComponent(req.params.ticker)}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'alternative-data company proxy failed' });
    }
  });
  router.get('/alternative-data/industry/:industry', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/alternative-data/industry/${encodeURIComponent(req.params.industry)}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'alternative-data industry proxy failed' });
    }
  });
  router.get('/alternative-data/beneficiaries/:dataset', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/alternative-data/beneficiaries/${encodeURIComponent(req.params.dataset)}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'alternative-data beneficiaries proxy failed' });
    }
  });
  // AGIB v2.0 Sprint 7 — Institutional Market Expectations Intelligence (IMEI)
  router.get('/expectations/health', kfGet('/v1/expectations/health'));
  router.get('/expectations/dashboard', kfGet('/v1/expectations/dashboard'));
  router.post('/expectations/run', kfPost('/v1/expectations/run'));
  router.get('/expectations/registry', kfGet('/v1/expectations/registry'));
  router.get('/expectations/phase2-consensus', kfGet('/v1/expectations/phase2-consensus'));
  router.get('/expectations/search', async (req, res) => {
    try {
      const q = new URLSearchParams({
        q: String(req.query.q || ''),
        limit: String(req.query.limit || '25'),
      }).toString();
      const result = await engineFetch(`/v1/expectations/search?${q}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'expectations search proxy failed' });
    }
  });
  router.get('/expectations/revisions', async (req, res) => {
    try {
      const q = new URLSearchParams();
      if (req.query.entity) q.set('entity', String(req.query.entity));
      if (req.query.as_of) q.set('as_of', String(req.query.as_of));
      const qs = q.toString();
      const result = await engineFetch(`/v1/expectations/revisions${qs ? `?${qs}` : ''}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'expectations revisions proxy failed' });
    }
  });
  router.get('/expectations/surprises', async (req, res) => {
    try {
      const q = new URLSearchParams();
      if (req.query.entity) q.set('entity', String(req.query.entity));
      if (req.query.as_of) q.set('as_of', String(req.query.as_of));
      const qs = q.toString();
      const result = await engineFetch(`/v1/expectations/surprises${qs ? `?${qs}` : ''}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'expectations surprises proxy failed' });
    }
  });
  router.get('/expectations/narratives', async (req, res) => {
    try {
      const q = new URLSearchParams();
      if (req.query.narrative_id) q.set('narrative_id', String(req.query.narrative_id));
      const qs = q.toString();
      const result = await engineFetch(`/v1/expectations/narratives${qs ? `?${qs}` : ''}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'expectations narratives proxy failed' });
    }
  });
  router.get('/expectations/replay', async (req, res) => {
    try {
      const q = new URLSearchParams({ as_of: String(req.query.as_of || '') });
      if (req.query.entity) q.set('entity', String(req.query.entity));
      const result = await engineFetch(`/v1/expectations/replay?${q.toString()}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'expectations replay proxy failed' });
    }
  });
  router.get('/expectations/company/:ticker', async (req, res) => {
    try {
      const q = req.query.as_of ? `?as_of=${encodeURIComponent(String(req.query.as_of))}` : '';
      const result = await engineFetch(
        `/v1/expectations/company/${encodeURIComponent(req.params.ticker)}${q}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'expectations company proxy failed' });
    }
  });
  router.get('/expectations/gap/:ticker', async (req, res) => {
    try {
      const q = req.query.as_of ? `?as_of=${encodeURIComponent(String(req.query.as_of))}` : '';
      const result = await engineFetch(
        `/v1/expectations/gap/${encodeURIComponent(req.params.ticker)}${q}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'expectations gap proxy failed' });
    }
  });
  // AGIB v2.0 — Unified Institutional Knowledge Stack
  router.get('/institutional-knowledge/health', kfGet('/v1/institutional-knowledge/health'));
  router.get('/institutional-knowledge/dashboard', async (req, res) => {
    try {
      const q = req.query.ensure ? '?ensure=true' : '';
      const result = await engineFetch(`/v1/institutional-knowledge/dashboard${q}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'institutional-knowledge dashboard proxy failed' });
    }
  });
  router.post('/institutional-knowledge/run', kfPost('/v1/institutional-knowledge/run'));
  router.get('/institutional-knowledge/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/institutional-knowledge/company/${encodeURIComponent(req.params.ticker)}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'institutional-knowledge company proxy failed' });
    }
  });
  router.post('/knowledge-factory/run-daily', kfPost('/v1/knowledge-factory/run-daily'));
  router.get('/knowledge-factory/historical-depth', kfGet('/v1/knowledge-factory/historical-depth'));
  router.post('/knowledge-factory/historical-depth/run', kfPost('/v1/knowledge-factory/historical-depth/run'));
  router.get('/knowledge-factory/sector-intelligence', kfGet('/v1/knowledge-factory/sector-intelligence'));
  router.post('/knowledge-factory/sector-intelligence/run', kfPost('/v1/knowledge-factory/sector-intelligence/run'));
  router.get('/knowledge-factory/macro-intelligence', kfGet('/v1/knowledge-factory/macro-intelligence'));
  router.post('/knowledge-factory/macro-intelligence/run', kfPost('/v1/knowledge-factory/macro-intelligence/run'));

  // Institutional Decision Quality (Sprint 7 — observability only)
  router.get('/decision-quality/health', kfGet('/v1/decision-quality/health'));
  router.get('/decision-quality/dashboard', kfGet('/v1/decision-quality/dashboard'));
  router.post('/decision-quality/run', kfPost('/v1/decision-quality/run'));
  router.get('/decision-quality/quality-gates', kfGet('/v1/decision-quality/quality-gates'));
  router.get('/decision-quality/scorecards/framework', kfGet('/v1/decision-quality/scorecards/framework'));
  router.get('/decision-quality/scorecards/sector', kfGet('/v1/decision-quality/scorecards/sector'));
  router.get('/decision-quality/scorecards/macro', kfGet('/v1/decision-quality/scorecards/macro'));
  router.get('/decision-quality/scorecards/portfolio', kfGet('/v1/decision-quality/scorecards/portfolio'));
  router.get('/decision-quality/calibration', kfGet('/v1/decision-quality/calibration'));
  router.get('/decision-quality/hall', kfGet('/v1/decision-quality/hall'));
  router.get('/decision-quality/replay/:decisionId', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const suffix = qs ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/decision-quality/replay/${encodeURIComponent(req.params.decisionId)}${suffix}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Decision Quality unavailable', detail: error.message });
    }
  });

  // Continuous Gather → Learn (Ask-isolated autonomous loop)
  // IKL — Institutional Knowledge Intelligence Layer (Gather → Memory → Ask)
  router.get('/ikl/health', kfGet('/v1/ikl/health'));
  router.get('/ikl/memory/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/ikl/memory/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 15_000 },
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({
        error: 'IKL memory unavailable',
        detail: error.message,
      });
    }
  });
  router.post('/ikl/learn', async (req, res) => {
    try {
      const result = await engineFetch('/v1/ikl/learn', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 30_000,
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({
        error: 'IKL learn unavailable',
        detail: error.message,
      });
    }
  });

  router.get('/continuous-gather-learn/health', kfGet('/v1/continuous-gather-learn/health'));
  router.get('/continuous-gather-learn/dashboard', kfGet('/v1/continuous-gather-learn/dashboard'));
  router.post('/continuous-gather-learn/run', async (req, res) => {
    try {
      const result = await engineFetch('/v1/continuous-gather-learn/run', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({
        error: 'Continuous Gather→Learn unavailable',
        detail: error.message,
      });
    }
  });

  // Universe learning — seed HD queue from Nifty/NSE lists and start CGL gather→learn
  router.get('/universe-learning/health', kfGet('/v1/universe-learning/health'));
  router.get('/universe-learning/status', kfGet('/v1/universe-learning/status', 60_000));
  router.post('/universe-learning/bootstrap', async (req, res) => {
    try {
      const result = await engineFetch('/v1/universe-learning/bootstrap', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 120_000,
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'universe-learning bootstrap failed' });
    }
  });

  // AGIB V1.5 — Institutional Universe Data Factory (IUDF)
  router.get('/universe-master-registry/health', kfGet('/v1/universe-master-registry/health'));
  router.get('/universe-master-registry/dashboard', kfGet('/v1/universe-master-registry/dashboard'));
  router.get('/universe-master-registry', async (req, res) => {
    try {
      const q = new URLSearchParams();
      for (const k of ['index', 'limit', 'offset', 'include_coverage']) {
        if (req.query[k] != null) q.set(k, String(req.query[k]));
      }
      const qs = q.toString();
      const result = await engineFetch(`/v1/universe-master-registry${qs ? `?${qs}` : ''}`, {
        timeoutMs: 60_000,
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'universe-master-registry list failed' });
    }
  });
  router.get('/universe-master-registry/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/universe-master-registry/company/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 20_000 }
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'universe-master-registry company failed' });
    }
  });

  router.get('/coverage-matrix/health', kfGet('/v1/coverage-matrix/health'));
  router.get('/coverage-matrix/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/coverage-matrix/company/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 30_000 }
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'coverage-matrix company failed' });
    }
  });
  router.get('/coverage-matrix/universe', async (req, res) => {
    try {
      const q = new URLSearchParams();
      if (req.query.scope) q.set('scope', String(req.query.scope));
      if (req.query.limit != null) q.set('limit', String(req.query.limit));
      const qs = q.toString();
      const result = await engineFetch(`/v1/coverage-matrix/universe${qs ? `?${qs}` : ''}`, {
        timeoutMs: 60_000,
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'coverage-matrix universe failed' });
    }
  });

  router.get('/institutional-knowledge-tables/health', kfGet('/v1/institutional-knowledge-tables/health'));
  router.get('/institutional-knowledge-tables/tables', kfGet('/v1/institutional-knowledge-tables/tables'));
  router.get('/institutional-knowledge-tables/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/institutional-knowledge-tables/company/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 20_000 }
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'ikt company failed' });
    }
  });
  router.get('/institutional-knowledge-tables/company/:ticker/:table', async (req, res) => {
    try {
      const q = new URLSearchParams();
      if (req.query.period) q.set('period', String(req.query.period));
      const qs = q.toString();
      const result = await engineFetch(
        `/v1/institutional-knowledge-tables/company/${encodeURIComponent(
          req.params.ticker
        )}/${encodeURIComponent(req.params.table)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 20_000 }
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'ikt company table failed' });
    }
  });
  router.get(
    '/institutional-knowledge-tables/company/:ticker/:table/:field/history',
    async (req, res) => {
      try {
        const result = await engineFetch(
          `/v1/institutional-knowledge-tables/company/${encodeURIComponent(
            req.params.ticker
          )}/${encodeURIComponent(req.params.table)}/${encodeURIComponent(
            req.params.field
          )}/history`,
          { timeoutMs: 20_000 }
        );
        res.json(result);
      } catch (err) {
        res.status(502).json({ error: err.message || 'ikt field history failed' });
      }
    }
  );
  router.post('/institutional-knowledge-tables/fact', async (req, res) => {
    try {
      const result = await engineFetch('/v1/institutional-knowledge-tables/fact', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 20_000,
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'ikt record fact failed' });
    }
  });
  router.post('/institutional-knowledge-tables/onboard-universe', async (req, res) => {
    try {
      const result = await engineFetch('/v1/institutional-knowledge-tables/onboard-universe', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 120_000,
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'ikt onboard universe failed' });
    }
  });
  router.post('/institutional-knowledge-tables/company/:ticker/rebuild', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/institutional-knowledge-tables/company/${encodeURIComponent(req.params.ticker)}/rebuild`,
        { method: 'POST', body: {}, timeoutMs: 30_000 }
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'ikt rebuild company failed' });
    }
  });
  router.post('/institutional-knowledge-tables/upload-sheet', async (req, res) => {
    try {
      const result = await engineFetch('/v1/institutional-knowledge-tables/upload-sheet', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 120_000,
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'ikt upload-sheet failed' });
    }
  });

  // Valuation Intelligence — Institutional Consensus Dashboard (Capital IQ)
  router.get('/valuation-consensus/health', kfGet('/v1/valuation-consensus/health'));
  router.get('/valuation-consensus/analytics', kfGet('/v1/valuation-consensus/analytics'));
  router.get('/valuation-consensus/rows', kfGet('/v1/valuation-consensus/rows'));
  router.get('/valuation-consensus/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/valuation-consensus/company/${encodeURIComponent(req.params.ticker)}`
      );
      res.status(result.status).json(result.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-consensus company failed' });
    }
  });
  router.post('/valuation-consensus/import/preview', async (req, res) => {
    try {
      const result = await engineFetch('/v1/valuation-consensus/import/preview', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 300_000,
      });
      res.status(result.status).json(result.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-consensus import preview failed' });
    }
  });
  router.post('/valuation-consensus/import/validate', async (req, res) => {
    try {
      const result = await engineFetch('/v1/valuation-consensus/import/validate', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 120_000,
      });
      res.status(result.status).json(result.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-consensus import validate failed' });
    }
  });
  router.post('/valuation-consensus/import/publish', async (req, res) => {
    try {
      const result = await engineFetch('/v1/valuation-consensus/import/publish', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 180_000,
      });
      res.status(result.status).json(result.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-consensus import publish failed' });
    }
  });
  router.post('/valuation-consensus/import/rollback', async (req, res) => {
    try {
      const result = await engineFetch('/v1/valuation-consensus/import/rollback', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 60_000,
      });
      res.status(result.status).json(result.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-consensus import rollback failed' });
    }
  });
  router.get('/valuation-consensus/imports', kfGet('/v1/valuation-consensus/imports'));
  router.get('/valuation-consensus/versions', kfGet('/v1/valuation-consensus/versions'));
  router.get('/valuation-consensus/export', async (req, res) => {
    try {
      const result = await engineFetch('/v1/valuation-consensus/export', { timeoutMs: 120_000 });
      res.status(result.status).json(result.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-consensus export failed' });
    }
  });
  router.post('/valuation-consensus/seed', async (req, res) => {
    try {
      const result = await engineFetch('/v1/valuation-consensus/seed', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 300_000,
      });
      res.status(result.status).json(result.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-consensus seed failed' });
    }
  });

  // Hedge Fund Strategy Lab — cold-start heavy; timeouts must exceed client AbortSignal.
  router.get('/hedge-fund-lab/live-strategies', kfGet('/v1/hedge-fund-lab/live-strategies'));
  router.get('/hedge-fund-lab/live-strategies/:id', (req, res, next) =>
    kfGet(`/v1/hedge-fund-lab/live-strategies/${encode(req.params.id)}`)(req, res, next));
  router.get('/hedge-fund-lab/health', async (_req, res) => {
    try {
      const r = await engineFetch('/v1/hedge-fund-lab/health', { timeoutMs: 30_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hedge-fund-lab health failed' });
    }
  });
  // Strategy library is definitional — serve Node static fallback when the
  // engine is 502 / circuit-open so HFL page chrome stays usable.
  router.get('/hedge-fund-lab/strategies', async (_req, res) => {
    try {
      if (circuitIsOpen('/v1/hedge-fund-lab/strategies')) {
        res.set('X-AGI-Hedge-Fund-Source', 'static_fallback');
        return res.status(200).json(hflStaticLibrary());
      }
      const r = await engineFetch('/v1/hedge-fund-lab/strategies', { timeoutMs: 4_000 });
      if (r.ok && r.data?.strategies) return res.status(200).json(r.data);
      res.set('X-AGI-Hedge-Fund-Source', 'static_fallback');
      return res.status(200).json(hflStaticLibrary());
    } catch {
      res.set('X-AGI-Hedge-Fund-Source', 'static_fallback');
      return res.status(200).json(hflStaticLibrary());
    }
  });
  router.get('/hedge-fund-lab/compare', async (_req, res) => {
    try {
      if (circuitIsOpen('/v1/hedge-fund-lab/compare')) {
        res.set('X-AGI-Hedge-Fund-Source', 'static_fallback');
        return res.status(200).json(hflStaticCompare());
      }
      const r = await engineFetch('/v1/hedge-fund-lab/compare', { timeoutMs: 4_000 });
      if (r.ok && Array.isArray(r.data?.rows)) return res.status(200).json(r.data);
      res.set('X-AGI-Hedge-Fund-Source', 'static_fallback');
      return res.status(200).json(hflStaticCompare());
    } catch {
      res.set('X-AGI-Hedge-Fund-Source', 'static_fallback');
      return res.status(200).json(hflStaticCompare());
    }
  });
  router.get('/hedge-fund-lab/regime', async (_req, res) => {
    try {
      const r = await engineFetch('/v1/hedge-fund-lab/regime', { timeoutMs: 25_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(504).json({ error: err.message || 'hedge-fund-lab regime failed', timeout: true });
    }
  });
  router.get('/hedge-fund-lab/daily-monitor', kfGet('/v1/hedge-fund-lab/daily-monitor'));
  router.get('/hedge-fund-lab/terminal', async (req, res) => {
    try {
      // Cap default scan size so cold/open paths stay interactive.
      const query = { ...(req.query || {}) };
      if (query.limit == null || query.limit === '') query.limit = '12';
      const forceRefresh = String(query.refresh || '') === '1';
      const limit = Math.max(1, Math.min(Number(query.limit) || 12, 50));
      const qs = new URLSearchParams(query).toString();
      const cacheKey = qs;

      if (!forceRefresh) {
        const fresh = readHflTerminalCache(cacheKey);
        if (fresh) {
          res.set('X-AGI-Hedge-Fund-Cache', 'memory-fresh');
          res.set('X-AGI-Hedge-Fund-Freshness', fresh.data?.freshness || (fresh.stale ? 'aging' : 'fresh'));
          return res.status(200).json(fresh.data);
        }
      }

      // Prefer Supabase read model. Singleflight refresh wakes Python at most once.
      const fromStore = await getHflTerminalFromReadModel({
        engineFetch,
        limit,
        forceRefresh,
        allowStale: true,
      });
      if (fromStore?.data) {
        writeHflTerminalCache(cacheKey, fromStore.data);
        res.set('X-AGI-Hedge-Fund-Cache', fromStore.source || 'supabase');
        res.set('X-AGI-Hedge-Fund-Freshness', fromStore.data.freshness || 'unknown');
        return res.status(200).json(fromStore.data);
      }

      // Legacy live engine path (pre-migration / no Supabase credentials).
      const r = await engineFetch(
        `/v1/hedge-fund-lab/terminal${qs ? `?${qs}` : ''}`,
        { timeoutMs: 8_000 },
      );
      if (r.ok) {
        writeHflTerminalCache(cacheKey, r.data);
        res.set('X-AGI-Hedge-Fund-Cache', 'engine_live');
        return res.status(r.status).json(r.data);
      }
      const stale = readHflTerminalCache(cacheKey, { allowStale: true });
      if (stale) {
        res.set('X-AGI-Hedge-Fund-Cache', 'memory-stale');
        return res.status(200).json({ ...stale.data, cache: { stale: true, age_ms: stale.age } });
      }
      return res.status(r.status).json(r.data);
    } catch (err) {
      const query = { ...(req.query || {}) };
      if (query.limit == null || query.limit === '') query.limit = '12';
      const stale = readHflTerminalCache(new URLSearchParams(query).toString(), { allowStale: true });
      if (stale) {
        res.set('X-AGI-Hedge-Fund-Cache', 'memory-stale');
        return res.status(200).json({ ...stale.data, cache: { stale: true, age_ms: stale.age } });
      }
      res.status(504).json({ error: err.message || 'hedge-fund-lab terminal failed', timeout: true });
    }
  });
  router.get('/hedge-fund-lab/opportunity/:ticker', async (req, res) => {
    try {
      const r = await engineFetch(`/v1/hedge-fund-lab/opportunity/${encodeURIComponent(req.params.ticker)}`, {
        timeoutMs: 30_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(504).json({ error: err.message || 'hedge-fund-lab opportunity failed', timeout: true });
    }
  });
  router.get('/hedge-fund-lab/scan/:strategy', async (req, res) => {
    try {
      const query = { ...(req.query || {}) };
      if (query.limit == null || query.limit === '') query.limit = '15';
      const qs = new URLSearchParams(query).toString();
      const r = await engineFetch(
        `/v1/hedge-fund-lab/scan/${encodeURIComponent(req.params.strategy)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 45_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(504).json({ error: err.message || 'hedge-fund-lab scan failed', timeout: true });
    }
  });
  router.get('/hedge-fund-lab/strategy/:id', async (req, res) => {
    const id = req.params.id;
    try {
      if (circuitIsOpen(`/v1/hedge-fund-lab/strategy/${id}`)) {
        res.set('X-AGI-Hedge-Fund-Source', 'static_fallback');
        return res.status(200).json(hflStaticStrategy(id));
      }
      const r = await engineFetch(`/v1/hedge-fund-lab/strategy/${encodeURIComponent(id)}`, {
        timeoutMs: 4_000,
      });
      if (r.ok && r.data?.ok !== false) return res.status(r.status).json(r.data);
      res.set('X-AGI-Hedge-Fund-Source', 'static_fallback');
      return res.status(200).json(hflStaticStrategy(id));
    } catch {
      res.set('X-AGI-Hedge-Fund-Source', 'static_fallback');
      return res.status(200).json(hflStaticStrategy(id));
    }
  });
  router.post('/hedge-fund-lab/calculate/:kind', async (req, res) => {
    try {
      const r = await engineFetch(`/v1/hedge-fund-lab/calculate/${encodeURIComponent(req.params.kind)}`, {
        method: 'POST', body: req.body || {}, timeoutMs: 20_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(504).json({ error: err.message || 'hedge-fund-lab calculate failed', timeout: true });
    }
  });
  router.post('/hedge-fund-lab/backtest/:strategyId', async (req, res) => {
    try {
      const r = await engineFetch(`/v1/hedge-fund-lab/backtest/${encodeURIComponent(req.params.strategyId)}`, {
        method: 'POST', body: req.body || {}, timeoutMs: 180_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hedge-fund-lab backtest failed' });
    }
  });

  // Admin Strategy Lab. Authentication is enforced server-side in addition to
  // the React admin route; these responses are never public fallbacks.
  router.get('/strategy-lab/health', requireStrategyLabAdmin, async (_req, res) => {
    try {
      const r = await engineFetch('/v1/strategy-lab/health', { timeoutMs: 30_000 });
      return res.status(r.status).json(enrichStrategyLabWithLiveMarket(r.data));
    } catch (err) {
      return res.status(503).json({ ok: false, error: err.message || 'strategy lab health unavailable' });
    }
  });
  router.get('/strategy-lab/dashboard', requireStrategyLabAdmin, async (req, res) => {
    try {
      const limit = Math.max(1, Math.min(Number(req.query.limit || 5), 20));
      const r = await engineFetch(`/v1/strategy-lab/dashboard?limit=${limit}`, { timeoutMs: 180_000 });
      return res.status(r.status).json(enrichStrategyLabWithLiveMarket(r.data));
    } catch (err) {
      return res.status(504).json({ ok: false, error: err.message || 'strategy lab dashboard unavailable' });
    }
  });
  router.get('/strategy-lab/scan/:strategyId', requireStrategyLabAdmin, async (req, res) => {
    try {
      const limit = Math.max(1, Math.min(Number(req.query.limit || 20), 100));
      const r = await engineFetch(`/v1/strategy-lab/scan/${encodeURIComponent(req.params.strategyId)}?limit=${limit}`, { timeoutMs: 180_000 });
      return res.status(r.status).json(enrichStrategyLabWithLiveMarket(r.data));
    } catch (err) {
      return res.status(504).json({ ok: false, error: err.message || 'strategy lab scan unavailable' });
    }
  });
  router.post('/strategy-lab/backtest/:strategyId', requireStrategyLabAdmin, async (req, res) => {
    try {
      const r = await engineFetch(`/v1/strategy-lab/backtest/${encodeURIComponent(req.params.strategyId)}`, { method: 'POST', body: req.body || {}, timeoutMs: 180_000 });
      return res.status(r.status).json(r.data);
    } catch (err) {
      return res.status(504).json({ ok: false, error: err.message || 'strategy lab backtest unavailable' });
    }
  });

  router.get('/research-factors/health', kfGet('/v1/research-factors/health'));
  router.get('/research-factors/audit', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/research-factors/audit${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(504).json({ error: err.message || 'research factor audit failed', timeout: true });
    }
  });
  router.get('/research-factors/company/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/research-factors/company/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(504).json({ error: err.message || 'research factor company lookup failed', timeout: true });
    }
  });

  router.get('/universal-knowledge/health', kfGet('/v1/universal-knowledge/health'));
  router.get('/universal-knowledge/registry', kfGet('/v1/universal-knowledge/registry'));
  router.post('/universal-knowledge/orchestrate', async (req, res) => {
    try {
      const r = await engineFetch('/v1/universal-knowledge/orchestrate', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 120_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'uko orchestrate failed' });
    }
  });

  // Valuation Intelligence Terminal — Warehouse → Unified Valuation Engine
  router.get('/valuation-terminal/health', kfGet('/v1/valuation-terminal/health'));
  router.get('/valuation-terminal/overview', kfGet('/v1/valuation-terminal/overview'));
  router.get('/valuation-terminal/sectors', kfGet('/v1/valuation-terminal/sectors'));
  router.get('/valuation-terminal/sector-intelligence', kfGet('/v1/valuation-terminal/sector-intelligence'));
  router.get('/valuation-terminal/statistics', kfGet('/v1/valuation-terminal/statistics'));
  router.get('/valuation-terminal/overrides/audit', kfGet('/v1/valuation-terminal/overrides/audit'));
  router.post('/valuation-terminal/overrides', async (req, res) => {
    try {
      const r = await engineFetch('/v1/valuation-terminal/overrides', {
        method: 'POST', body: req.body || {}, timeoutMs: 30_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-terminal override failed' });
    }
  });
  router.post('/valuation-terminal/overrides/clear', async (req, res) => {
    try {
      const r = await engineFetch('/v1/valuation-terminal/overrides/clear', {
        method: 'POST', body: req.body || {}, timeoutMs: 30_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-terminal override clear failed' });
    }
  });
  router.get('/valuation-terminal/insights', kfGet('/v1/valuation-terminal/insights'));
  router.get('/valuation-terminal/companies', kfGet('/v1/valuation-terminal/companies'));
  router.get('/valuation-terminal/sector/:sector', async (req, res) => {
    try {
      const r = await engineFetch(`/v1/valuation-terminal/sector/${encodeURIComponent(req.params.sector)}`);
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-terminal sector failed' });
    }
  });
  router.get('/valuation-terminal/company/:ticker', async (req, res) => {
    try {
      const window = req.query?.window || '5Y';
      const peerLimit = Number(req.query?.peer_limit) || 12;
      const forceRefresh = String(req.query?.refresh || '') === '1';
      const fromStore = await getValuationCompanyPackFromReadModel({
        engineFetch,
        symbol: req.params.ticker,
        window,
        peerLimit,
        forceRefresh,
        allowStale: true,
      });
      if (fromStore?.data) {
        res.set('X-AGI-Valuation-Pack-Cache', fromStore.source || 'supabase');
        res.set('X-AGI-Valuation-Pack-Freshness', fromStore.data.freshness || 'unknown');
        return res.status(200).json(fromStore.data);
      }
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation-terminal/company/${encodeURIComponent(req.params.ticker)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 90_000 },
      );
      res.set('X-AGI-Valuation-Pack-Cache', 'engine_live');
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-terminal company failed' });
    }
  });
  router.get('/valuation-terminal/explain/:metric', async (req, res) => {
    try {
      const r = await engineFetch(`/v1/valuation-terminal/explain/${encodeURIComponent(req.params.metric)}`);
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-terminal explain failed' });
    }
  });

  // Valuation Policy & Applicability Engine (VPAE) — Phase 8.2A
  router.get('/valuation-policy/health', kfGet('/v1/valuation-policy/health'));
  router.get('/valuation/applicability/:symbol', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/valuation/applicability/${encodeURIComponent(req.params.symbol)}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation applicability failed' });
    }
  });
  router.get('/valuation/model/:symbol', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/valuation/model/${encodeURIComponent(req.params.symbol)}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation model failed' });
    }
  });
  router.get('/valuation/explanation/:symbol', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/valuation/explanation/${encodeURIComponent(req.params.symbol)}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation explanation failed' });
    }
  });
  // Institutional Coverage Health — register BEFORE /valuation/coverage/:symbol
  router.get('/valuation/coverage-health/health', kfGet('/v1/valuation/coverage-health/health'));
  router.get('/valuation/coverage/health', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/valuation/coverage/health${qs ? `?${qs}` : ''}`, {
        timeoutMs: 180_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'coverage health failed' });
    }
  });
  router.get('/valuation/coverage/valuation', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/valuation/coverage/valuation${qs ? `?${qs}` : ''}`, {
        timeoutMs: 180_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation coverage failed' });
    }
  });
  router.get('/valuation/coverage/metrics', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/valuation/coverage/metrics${qs ? `?${qs}` : ''}`, {
        timeoutMs: 180_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'metric coverage failed' });
    }
  });
  router.get('/valuation/coverage/research', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/valuation/coverage/research${qs ? `?${qs}` : ''}`, {
        timeoutMs: 180_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'research coverage failed' });
    }
  });
  router.get('/valuation/coverage/residual', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/valuation/coverage/residual${qs ? `?${qs}` : ''}`, {
        timeoutMs: 180_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'coverage residual failed' });
    }
  });
  router.get('/valuation/coverage/:symbol', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/valuation/coverage/${encodeURIComponent(req.params.symbol)}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation coverage failed' });
    }
  });
  router.get('/valuation/status/:symbol', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/valuation/status/${encodeURIComponent(req.params.symbol)}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation status failed' });
    }
  });
  router.get('/valuation/universe', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/universe${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation universe failed' });
    }
  });

  // Institutional Valuation Research Workspace v2 — warehouse → UVE / HVIE / VPAE
  router.get('/valuation/explorer/health', kfGet('/v1/valuation/explorer/health'));
  router.get('/valuation/market', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/valuation/market${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation market failed' });
    }
  });
  router.get('/valuation/sectors', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/valuation/sectors${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation sectors failed' });
    }
  });
  router.get('/valuation/sector/:sector', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/sector/${encodeURIComponent(req.params.sector)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation sector failed' });
    }
  });
  router.get('/valuation/sector/:sector/industries', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/sector/${encodeURIComponent(req.params.sector)}/industries${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation sector industries failed' });
    }
  });
  router.get('/valuation/industry/:industry', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/industry/${encodeURIComponent(req.params.industry)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation industry failed' });
    }
  });
  router.get('/valuation/sector/:sector/summary', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/valuation/sector/${encodeURIComponent(req.params.sector)}/summary`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation sector summary failed' });
    }
  });
  router.get('/valuation/sector/:sector/companies', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/sector/${encodeURIComponent(req.params.sector)}/companies${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation sector companies failed' });
    }
  });
  router.get('/valuation/sector/:sector/leaders', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/sector/${encodeURIComponent(req.params.sector)}/leaders${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation sector leaders failed' });
    }
  });
  router.get('/valuation/sector/:sector/heatmap', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/valuation/sector/${encodeURIComponent(req.params.sector)}/heatmap`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation sector heatmap failed' });
    }
  });
  router.get('/valuation/sector/:sector/research', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/valuation/sector/${encodeURIComponent(req.params.sector)}/research`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation sector research failed' });
    }
  });
  router.get('/valuation/sector/:sector/rotation', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/sector/${encodeURIComponent(req.params.sector)}/rotation${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation sector rotation failed' });
    }
  });
  router.get('/valuation/opportunities', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/valuation/opportunities${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation opportunities failed' });
    }
  });
  router.get('/valuation/premium', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/valuation/premium${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation premium failed' });
    }
  });
  router.get('/valuation/rerating', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/valuation/rerating${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation rerating failed' });
    }
  });
  router.get('/valuation/company/:symbol', async (req, res) => {
    try {
      const window = req.query?.window || '10Y';
      const peerLimit = Number(req.query?.peer_limit) || 12;
      const forceRefresh = String(req.query?.refresh || '') === '1';
      const fromStore = await getValuationCompanyPackFromReadModel({
        engineFetch,
        symbol: req.params.symbol,
        window,
        peerLimit,
        forceRefresh,
        allowStale: true,
      });
      if (fromStore?.data) {
        res.set('X-AGI-Valuation-Pack-Cache', fromStore.source || 'supabase');
        res.set('X-AGI-Valuation-Pack-Freshness', fromStore.data.freshness || 'unknown');
        return res.status(200).json(fromStore.data);
      }
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/company/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 90_000 },
      );
      res.set('X-AGI-Valuation-Pack-Cache', 'engine_live');
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation company failed' });
    }
  });
  router.get('/valuation/company/:symbol/history', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/company/${encodeURIComponent(req.params.symbol)}/history${qs ? `?${qs}` : ''}`,
        { timeoutMs: 90_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation company history failed' });
    }
  });

  // Valuation Attribution & Research Intelligence Engine (VARIE) v1.0
  router.get('/valuation/attribution/health', kfGet('/v1/valuation/attribution/health'));
  const varieGet = (path, timeoutMs = 120_000) => async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`${path}${qs ? `?${qs}` : ''}`, { timeoutMs });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation attribution failed' });
    }
  };
  router.get('/valuation/attribution/market', varieGet('/v1/valuation/attribution/market'));
  router.get('/valuation/attribution/opportunities', varieGet('/v1/valuation/attribution/opportunities'));
  router.get('/valuation/attribution/leaders', varieGet('/v1/valuation/attribution/leaders'));
  router.get('/valuation/attribution/company/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/attribution/company/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation attribution company failed' });
    }
  });
  router.get('/valuation/attribution/sector/:sector', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/attribution/sector/${encodeURIComponent(req.params.sector)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation attribution sector failed' });
    }
  });
  router.get('/valuation/attribution/industry/:industry', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/attribution/industry/${encodeURIComponent(req.params.industry)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation attribution industry failed' });
    }
  });
  router.get('/valuation/attribution/peer/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/attribution/peer/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation attribution peer failed' });
    }
  });
  router.get('/valuation/attribution/history/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/attribution/history/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation attribution history failed' });
    }
  });
  router.get('/valuation/attribution/timeline/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation/attribution/timeline/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation attribution timeline failed' });
    }
  });

  // Historical Valuation Intelligence Engine (HVIE) — Phase 8.3
  router.get('/historical-valuation/health', kfGet('/v1/historical-valuation/health'));
  const hvieGet = (suffix, timeoutMs = 60_000) => async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/historical-valuation/${suffix}/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || `historical-valuation ${suffix} failed` });
    }
  };
  router.get('/historical-valuation/company/:symbol', hvieGet('company'));
  router.get('/historical-valuation/history/:symbol', hvieGet('history', 90_000));
  router.get('/historical-valuation/statistics/:symbol', hvieGet('statistics'));
  router.get('/historical-valuation/bands/:symbol', hvieGet('bands'));
  router.get('/historical-valuation/percentiles/:symbol', hvieGet('percentiles'));
  router.get('/historical-valuation/regimes/:symbol', hvieGet('regimes'));
  router.get('/historical-valuation/rerating/:symbol', hvieGet('rerating'));
  router.get('/historical-valuation/coverage/:symbol', hvieGet('coverage'));
  router.post('/historical-valuation/reconstruct/:symbol', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/historical-valuation/reconstruct/${encodeURIComponent(req.params.symbol)}`,
        { method: 'POST', body: req.body || {}, timeoutMs: 180_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'historical-valuation reconstruct failed' });
    }
  });
  router.get('/historical-valuation/coverage-dashboard', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/historical-valuation/coverage-dashboard${qs ? `?${qs}` : ''}`,
        { timeoutMs: 120_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'historical-valuation coverage-dashboard failed' });
    }
  });
  router.get('/historical-valuation/runtime/status', kfGet('/v1/historical-valuation/runtime/status'));
  router.post('/historical-valuation/runtime/run', async (req, res) => {
    try {
      const r = await engineFetch('/v1/historical-valuation/runtime/run', {
        method: 'POST', body: req.body || {}, timeoutMs: 180_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie runtime run failed' });
    }
  });
  router.post('/historical-valuation/runtime/start', async (req, res) => {
    try {
      const r = await engineFetch('/v1/historical-valuation/runtime/start', {
        method: 'POST', body: {}, timeoutMs: 30_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie runtime start failed' });
    }
  });
  router.post('/historical-valuation/runtime/stop', async (req, res) => {
    try {
      const r = await engineFetch('/v1/historical-valuation/runtime/stop', {
        method: 'POST', body: {}, timeoutMs: 30_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie runtime stop failed' });
    }
  });

  // Phase 8.3B — HVIE intelligence aliases (warehouse-reconstructed)
  router.get('/hvie/company/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/hvie/company/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie company failed' });
    }
  });
  router.get('/hvie/history/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/hvie/history/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 90_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie history failed' });
    }
  });
  router.get('/hvie/statistics/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/hvie/statistics/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie statistics failed' });
    }
  });
  router.get('/hvie/percentiles/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/hvie/percentiles/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie percentiles failed' });
    }
  });
  router.get('/hvie/bands/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/hvie/bands/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie bands failed' });
    }
  });
  router.get('/hvie/regimes/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/hvie/regimes/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie regimes failed' });
    }
  });
  router.get('/hvie/rerating/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/hvie/rerating/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie rerating failed' });
    }
  });
  router.get('/hvie/coverage/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/hvie/coverage/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie coverage failed' });
    }
  });

  // HVIE Universe Completion Programme (Phase 8.3A/B)
  router.get('/hvie/runtime/health', kfGet('/v1/hvie/runtime/health'));
  router.get('/hvie/runtime/status', kfGet('/v1/hvie/runtime/status'));
  router.get('/hvie/runtime/board', kfGet('/v1/hvie/runtime/board'));
  router.get('/hvie/runtime/coverage', kfGet('/v1/hvie/runtime/coverage'));
  router.get('/hvie/runtime/pipeline', kfGet('/v1/hvie/runtime/pipeline'));
  router.get('/hvie/runtime/sector', kfGet('/v1/hvie/runtime/sector'));
  router.get('/hvie/runtime/industry', kfGet('/v1/hvie/runtime/industry'));
  router.get('/hvie/runtime/market', kfGet('/v1/hvie/runtime/market'));
  router.get('/hvie/runtime/failures', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/hvie/runtime/failures${qs ? `?${qs}` : ''}`, { timeoutMs: 60_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie failures failed' });
    }
  });
  router.get('/hvie/runtime/retry', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/hvie/runtime/retry${qs ? `?${qs}` : ''}`, { timeoutMs: 60_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie retry queue failed' });
    }
  });
  router.get('/hvie/runtime/company/:symbol', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/hvie/runtime/company/${encodeURIComponent(req.params.symbol)}`,
        { timeoutMs: 30_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie company status failed' });
    }
  });
  router.post('/hvie/runtime/start', async (req, res) => {
    try {
      const r = await engineFetch('/v1/hvie/runtime/start', { method: 'POST', body: {}, timeoutMs: 30_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie universe start failed' });
    }
  });
  router.post('/hvie/runtime/stop', async (req, res) => {
    try {
      const r = await engineFetch('/v1/hvie/runtime/stop', { method: 'POST', body: {}, timeoutMs: 30_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie universe stop failed' });
    }
  });
  router.post('/hvie/runtime/resume', async (req, res) => {
    try {
      const r = await engineFetch('/v1/hvie/runtime/resume', { method: 'POST', body: {}, timeoutMs: 30_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie universe resume failed' });
    }
  });
  router.post('/hvie/runtime/run', async (req, res) => {
    try {
      const r = await engineFetch('/v1/hvie/runtime/run', {
        method: 'POST', body: req.body || {}, timeoutMs: 300_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie universe run failed' });
    }
  });
  router.post('/hvie/runtime/retry/:symbol', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/hvie/runtime/retry/${encodeURIComponent(req.params.symbol)}`,
        { method: 'POST', body: {}, timeoutMs: 180_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie retry symbol failed' });
    }
  });
  router.post('/hvie/runtime/reconstruct/:symbol', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/hvie/runtime/reconstruct/${encodeURIComponent(req.params.symbol)}`,
        { method: 'POST', body: {}, timeoutMs: 300_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie reconstruct failed' });
    }
  });
  router.post('/hvie/runtime/aggregates', async (req, res) => {
    try {
      const r = await engineFetch('/v1/hvie/runtime/aggregates', {
        method: 'POST', body: req.body || {}, timeoutMs: 180_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'hvie aggregates failed' });
    }
  });

  // Research Intelligence Engine (Phase 8.4) — dossier consumer
  router.get('/research/health', kfGet('/v1/research/health'));
  router.get('/research/dashboard', kfGet('/v1/research/dashboard'));
  router.get('/research/coverage', kfGet('/v1/research/coverage'));
  const rieGet = (suffix, timeoutMs = 90_000) => async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/research/${suffix}/${encodeURIComponent(req.params.symbol)}`,
        { timeoutMs },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || `research ${suffix} failed` });
    }
  };
  router.get('/research/company/:symbol', rieGet('company', 180_000));
  router.get('/research/business/:symbol', rieGet('business'));
  router.get('/research/financial-quality/:symbol', rieGet('financial-quality'));
  router.get('/research/growth/:symbol', rieGet('growth'));
  router.get('/research/profitability/:symbol', rieGet('profitability'));
  router.get('/research/capital-allocation/:symbol', rieGet('capital-allocation'));
  router.get('/research/valuation/:symbol', rieGet('valuation'));
  router.get('/research/ownership/:symbol', rieGet('ownership'));
  router.get('/research/risk/:symbol', rieGet('risk'));
  router.get('/research/catalysts/:symbol', rieGet('catalysts'));
  router.get('/research/monitoring/:symbol', rieGet('monitoring'));
  router.get('/research/timeline/:symbol', rieGet('timeline'));
  router.get('/research/confidence/:symbol', rieGet('confidence', 180_000));

  // Forecast Intelligence Engine (Phase 8.5) — /fie/* avoids legacy /forecast/*
  router.get('/fie/health', kfGet('/v1/fie/health'));
  router.get('/fie/dashboard', kfGet('/v1/fie/dashboard'));
  router.get('/fie/coverage', kfGet('/v1/fie/coverage'));
  router.get('/fie/runtime/status', kfGet('/v1/fie/runtime/status'));
  router.get('/fie/runtime/board', kfGet('/v1/fie/runtime/board'));
  const fieGet = (suffix, timeoutMs = 90_000) => async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/fie/${suffix}/${encodeURIComponent(req.params.symbol)}`,
        { timeoutMs },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || `fie ${suffix} failed` });
    }
  };
  router.get('/fie/company/:symbol', fieGet('company', 180_000));
  router.get('/fie/business/:symbol', fieGet('business'));
  router.get('/fie/growth/:symbol', fieGet('growth'));
  router.get('/fie/profitability/:symbol', fieGet('profitability'));
  router.get('/fie/balance-sheet/:symbol', fieGet('balance-sheet'));
  router.get('/fie/valuation/:symbol', fieGet('valuation'));
  router.get('/fie/scenarios/:symbol', fieGet('scenarios'));
  router.get('/fie/sensitivity/:symbol', fieGet('sensitivity'));
  router.get('/fie/risks/:symbol', fieGet('risks'));
  router.get('/fie/catalysts/:symbol', fieGet('catalysts'));
  router.get('/fie/confidence/:symbol', fieGet('confidence', 180_000));
  router.get('/fie/history/:symbol', fieGet('history'));
  router.get('/fie/accuracy/:symbol', fieGet('accuracy'));
  router.post('/fie/runtime/start', async (req, res) => {
    try {
      const r = await engineFetch('/v1/fie/runtime/start', { method: 'POST', body: {}, timeoutMs: 30_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'fie runtime start failed' });
    }
  });
  router.post('/fie/runtime/stop', async (req, res) => {
    try {
      const r = await engineFetch('/v1/fie/runtime/stop', { method: 'POST', body: {}, timeoutMs: 30_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'fie runtime stop failed' });
    }
  });
  router.post('/fie/runtime/resume', async (req, res) => {
    try {
      const r = await engineFetch('/v1/fie/runtime/resume', { method: 'POST', body: {}, timeoutMs: 30_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'fie runtime resume failed' });
    }
  });
  router.post('/fie/runtime/run', async (req, res) => {
    try {
      const r = await engineFetch('/v1/fie/runtime/run', {
        method: 'POST', body: req.body || {}, timeoutMs: 300_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'fie runtime run failed' });
    }
  });

  // Macro Intelligence Engine (Phase 9.0) — /mie/* avoids legacy /macro/* sprints
  router.get('/mie/health', kfGet('/v1/mie/health'));
  router.get('/mie/dashboard', async (req, res) => {
    try {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(req.query || {}).filter(([, v]) => v != null && v !== '')),
      ).toString();
      const r = await engineFetch(`/v1/mie/dashboard${qs ? `?${qs}` : ''}`, { timeoutMs: 120_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'mie dashboard failed' });
    }
  });
  router.get('/mie/pack', async (req, res) => {
    try {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(req.query || {}).filter(([, v]) => v != null && v !== '')),
      ).toString();
      const r = await engineFetch(`/v1/mie/pack${qs ? `?${qs}` : ''}`, { timeoutMs: 180_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'mie pack failed' });
    }
  });
  router.get('/mie/snapshot', async (req, res) => {
    const country = String(req.query.country || 'Global');
    try {
      const payload = await proxy.get('/v1/mie/snapshot', {
        params: { country },
        timeout: 5_000,
      });
      res.set('Cache-Control', 'public, max-age=60, stale-while-revalidate=300');
      return res.json(payload.data);
    } catch (error) {
      return res.status(503).json({
        ok: false,
        status: 'SNAPSHOT_UNAVAILABLE',
        country,
        message: 'The global markets snapshot is being prepared. Please retry shortly.',
      });
    }
  });


  router.get('/mie/runtime/status', kfGet('/v1/mie/runtime/status'));
  router.get('/mie/runtime/board', kfGet('/v1/mie/runtime/board'));
  const mieGet = (suffix, timeoutMs = 90_000) => async (req, res) => {
    try {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(req.query || {}).filter(([, v]) => v != null && v !== '')),
      ).toString();
      const r = await engineFetch(`/v1/mie/${suffix}${qs ? `?${qs}` : ''}`, { timeoutMs });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || `mie ${suffix} failed` });
    }
  };
  router.get('/mie/regime', mieGet('regime'));
  router.get('/mie/economy', mieGet('economy'));
  router.get('/mie/inflation', mieGet('inflation'));
  router.get('/mie/rates', mieGet('rates'));
  router.get('/mie/liquidity', mieGet('liquidity'));
  router.get('/mie/currency', mieGet('currency'));
  router.get('/mie/commodities', mieGet('commodities'));
  router.get('/mie/bonds', mieGet('bonds'));
  router.get('/mie/fiscal', mieGet('fiscal'));
  router.get('/mie/external', mieGet('external'));
  router.get('/mie/sector-impact', mieGet('sector-impact'));
  router.get('/mie/industry-impact', mieGet('industry-impact'));
  router.get('/mie/forecast', mieGet('forecast'));
  router.get('/mie/scenarios', mieGet('scenarios'));
  router.get('/mie/relationships', mieGet('relationships'));
  router.get('/mie/risks', mieGet('risks'));
  router.get('/mie/company-impact/:symbol', async (req, res) => {
    try {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(req.query || {}).filter(([, v]) => v != null && v !== '')),
      ).toString();
      const r = await engineFetch(
        `/v1/mie/company-impact/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 90_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'mie company-impact failed' });
    }
  });
  router.post('/mie/runtime/start', async (req, res) => {
    try {
      const r = await engineFetch('/v1/mie/runtime/start', { method: 'POST', body: {}, timeoutMs: 30_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'mie runtime start failed' });
    }
  });
  router.post('/mie/runtime/stop', async (req, res) => {
    try {
      const r = await engineFetch('/v1/mie/runtime/stop', { method: 'POST', body: {}, timeoutMs: 30_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'mie runtime stop failed' });
    }
  });
  router.post('/mie/runtime/resume', async (req, res) => {
    try {
      const r = await engineFetch('/v1/mie/runtime/resume', { method: 'POST', body: {}, timeoutMs: 30_000 });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'mie runtime resume failed' });
    }
  });
  router.post('/mie/runtime/run', async (req, res) => {
    try {
      const r = await engineFetch('/v1/mie/runtime/run', {
        method: 'POST', body: req.body || {}, timeoutMs: 300_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'mie runtime run failed' });
    }
  });

  // Phase 9.1 — Intelligence Fusion & Answer Composer (IFAC)
  router.get('/ifac/health', kfGet('/v1/ifac/health'));
  router.get('/ifac/templates', kfGet('/v1/ifac/templates'));
  router.get('/ifac/routing', kfGet('/v1/ifac/routing'));
  router.get('/ifac/confidence', kfGet('/v1/ifac/confidence'));
  router.get('/ifac/debug', kfGet('/v1/ifac/debug'));
  router.get('/ifac/provenance', kfGet('/v1/ifac/provenance'));
  router.get('/ifac/dashboard', kfGet('/v1/ifac/dashboard'));
  router.get('/aqe/health', kfGet('/v1/aqe/health'));
  router.get('/aqe/dashboard', kfGet('/v1/aqe/dashboard'));
  router.post('/aqe/inspect', async (req, res) => {
    try {
      const r = await engineFetch('/v1/aqe/inspect', {
        method: 'POST',
        body: JSON.stringify(req.body || {}),
      });
      res.json(r);
    } catch (err) {
      res.status(502).json({ error: err.message || 'aqe inspect failed' });
    }
  });
  router.post('/aqe/quality-gate', async (req, res) => {
    try {
      const r = await engineFetch('/v1/aqe/quality-gate', {
        method: 'POST',
        body: JSON.stringify(req.body || {}),
      });
      res.json(r);
    } catch (err) {
      res.status(502).json({ error: err.message || 'aqe quality-gate failed' });
    }
  });
  router.post('/ifac/compose', async (req, res) => {
    try {
      const r = await engineFetch('/v1/ifac/compose', {
        method: 'POST', body: req.body || {}, timeoutMs: 120_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'ifac compose failed' });
    }
  });

  // Unified Valuation Engine — terminal migration surface
  router.get('/valuation-engine/health', kfGet('/v1/valuation-engine/health'));
  router.get('/valuation-engine/company/:symbol', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/valuation-engine/company/${encodeURIComponent(req.params.symbol)}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-engine company failed' });
    }
  });
  router.post('/valuation-engine/explain-change', async (req, res) => {
    try {
      const r = await engineFetch('/v1/valuation-engine/explain-change', {
        method: 'POST', body: req.body || {}, timeoutMs: 30_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-engine explain-change failed' });
    }
  });
  router.get('/valuation-engine/terminal/health', kfGet('/v1/valuation-engine/terminal/health'));
  router.get('/valuation-engine/terminal/search', kfGet('/v1/valuation-engine/terminal/search'));
  router.get('/valuation-engine/terminal/company/:symbol', async (req, res) => {
    try {
      const window = req.query?.window || '5Y';
      const peerLimit = Number(req.query?.peer_limit) || 12;
      const forceRefresh = String(req.query?.refresh || '') === '1';
      const fromStore = await getValuationCompanyPackFromReadModel({
        engineFetch,
        symbol: req.params.symbol,
        window,
        peerLimit,
        forceRefresh,
        allowStale: true,
      });
      if (fromStore?.data) {
        res.set('X-AGI-Valuation-Pack-Cache', fromStore.source || 'supabase');
        res.set('X-AGI-Valuation-Pack-Freshness', fromStore.data.freshness || 'unknown');
        return res.status(200).json(fromStore.data);
      }
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation-engine/terminal/company/${encodeURIComponent(req.params.symbol)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 90_000 },
      );
      res.set('X-AGI-Valuation-Pack-Cache', 'engine_live');
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-engine terminal company failed' });
    }
  });
  router.get('/valuation-engine/terminal/series/:symbol/:metric', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/valuation-engine/terminal/series/${encodeURIComponent(req.params.symbol)}/${encodeURIComponent(req.params.metric)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 60_000 },
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-engine terminal series failed' });
    }
  });
  router.get('/valuation-engine/terminal/explain/:metric', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/valuation-engine/terminal/explain/${encodeURIComponent(req.params.metric)}`,
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-engine terminal explain failed' });
    }
  });

  // Market & Sector Intelligence Terminal v1.0
  router.get('/market-intelligence/health', kfGet('/v1/market-intelligence/health'));
  router.get('/market-intelligence/dashboard', async (req, res) => {
    const allowStale = req.query.stale === '1' || req.query.stale === 'true';
    const cached = readMiDashboardCache({ allowStale: true });
    if (cached && !allowStale && cached.age <= MI_DASHBOARD_FRESH_MS && req.query.refresh !== '1') {
      return res.status(200).json({
        ...cached.data,
        _cache: { age_ms: cached.age, stale: cached.stale },
      });
    }
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(`/v1/market-intelligence/dashboard${qs ? `?${qs}` : ''}`, { timeoutMs: 45_000 });
      if (r.ok && r.data?.ok) writeMiDashboardCache(r.data);
      return res.status(r.status).json(r.data);
    } catch (err) {
      const detail = err?.message || 'market-intelligence dashboard failed';
      if (cached) {
        return res.status(200).json({
          ...cached.data,
          ok: true,
          degraded: true,
          error: detail,
          hint: 'Serving last good dashboard while the engine recovers.',
          _cache: { age_ms: cached.age, stale: true },
        });
      }
      return res.status(200).json(buildMiDegradedDashboard(detail));
    }
  });
  router.get('/market-intelligence/sector/:sector', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const r = await engineFetch(
        `/v1/market-intelligence/sector/${encodeURIComponent(req.params.sector)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 45_000 },
      );
      return res.status(r.status).json(r.data);
    } catch (err) {
      const detail = err?.message || 'market-intelligence sector failed';
      return res.status(200).json(buildMiDegradedSector(req.params.sector, detail));
    }
  });
  router.post('/market-intelligence/flows/ingest', async (req, res) => {
    try {
      const r = await engineFetch('/v1/market-intelligence/flows/ingest', {
        method: 'POST', body: req.body || {}, timeoutMs: 60_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'market-intelligence flows ingest failed' });
    }
  });

  // Upstox valuation ratios (key-ratios) — warehouse-backed; UI never calls Upstox
  router.get('/valuation-ratios/health', kfGet('/v1/valuation-ratios/health'));
  router.get('/valuation-ratios/coverage', kfGet('/v1/valuation-ratios/coverage'));
  router.get('/valuation-ratios/company/:symbol', async (req, res) => {
    try {
      const r = await engineFetch(
        `/v1/valuation-ratios/company/${encodeURIComponent(req.params.symbol)}`
      );
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-ratios company failed' });
    }
  });
  router.post('/valuation-ratios/ingest', async (req, res) => {
    try {
      const r = await engineFetch('/v1/valuation-ratios/ingest', {
        method: 'POST', body: req.body || {}, timeoutMs: 180_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-ratios ingest failed' });
    }
  });
  router.post('/valuation-ratios/isin-backfill', async (req, res) => {
    try {
      const r = await engineFetch('/v1/valuation-ratios/isin-backfill', {
        method: 'POST', body: req.body || {}, timeoutMs: 300_000,
      });
      res.status(r.status).json(r.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'valuation-ratios isin-backfill failed' });
    }
  });

  // Company Identity Service — canonical Capital IQ classification
  router.get('/company-identity/health', kfGet('/v1/company-identity/health'));
  router.post('/company-identity/metadata', async (req, res) => {
    try {
      const result = await engineFetch('/v1/company-identity/metadata', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 20_000,
      });
      res.status(result.status).json(result.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'company-identity metadata failed' });
    }
  });
  router.get('/company-identity/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/company-identity/${encodeURIComponent(req.params.ticker)}`
      );
      res.status(result.status).json(result.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'company-identity lookup failed' });
    }
  });
  router.post('/company-identity/validate', async (req, res) => {
    try {
      const result = await engineFetch('/v1/company-identity/validate', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 30_000,
      });
      res.status(result.status).json(result.data);
    } catch (err) {
      res.status(502).json({ error: err.message || 'company-identity validate failed' });
    }
  });

  // Mission Control V1 — administrator operations centre (read-only)
  const MC_DASHBOARD_CACHE = { body: null, at: 0 };
  const MC_DASHBOARD_CACHE_MS = 5 * 60_000;

  async function fetchMissionControlDashboard({ timeoutMs = 25_000, retries = 1 } = {}) {
    let lastErr = null;
    for (let attempt = 0; attempt <= retries; attempt += 1) {
      try {
        const result = await engineFetch('/v1/mission-control/dashboard', { timeoutMs });
        if (!result.ok) {
          const err = new Error(
            result.data?.error || result.data?.detail || `engine_http_${result.status}`,
          );
          err.status = result.status;
          throw err;
        }
        if (result.data && typeof result.data === 'object') {
          MC_DASHBOARD_CACHE.body = result.data;
          MC_DASHBOARD_CACHE.at = Date.now();
        }
        return result.data;
      } catch (err) {
        lastErr = err;
        const retryable =
          err?.name === 'TimeoutError'
          || err?.name === 'AbortError'
          || /timed out|aborted|fetch failed|ECONNRESET|ENOTFOUND|EAI_AGAIN/i.test(
            String(err?.message || ''),
          );
        if (attempt < retries && retryable) {
          // eslint-disable-next-line no-await-in-loop
          await new Promise((r) => setTimeout(r, 1500));
          continue;
        }
        break;
      }
    }
    if (
      MC_DASHBOARD_CACHE.body
      && Date.now() - MC_DASHBOARD_CACHE.at < MC_DASHBOARD_CACHE_MS
    ) {
      return {
        ...MC_DASHBOARD_CACHE.body,
        stale: true,
        _stale_reason: String(lastErr?.message || 'engine_unavailable').slice(0, 200),
      };
    }
    throw lastErr || new Error('mission_control_dashboard_unavailable');
  }

  router.get('/mission-control/health', kfGet('/v1/mission-control/health'));
  router.get('/mission-control/intelligence-map', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/mission-control/intelligence-map', {
        timeoutMs: 10_000,
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({
        error: 'Intelligence Map unavailable',
        detail: error.message,
        hint: 'Snapshot reader failed — check intelligence_map.json on disk.',
      });
    }
  });
  router.get('/mission-control/institutional-intelligence', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/mission-control/institutional-intelligence', {
        timeoutMs: 10_000,
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({
        error: 'Institutional Intelligence unavailable',
        detail: error.message,
        hint: 'Snapshot reader failed — check institutional_intelligence.json on disk.',
      });
    }
  });
  router.get('/mission-control/agent-map', async (_req, res) => {
    try {
      // Snapshot path — keep timeout short; engine must not probe modules.
      const result = await engineFetch('/v1/mission-control/agent-map', { timeoutMs: 10_000 });
      if (!result.ok) {
        return res.status(result.status).json(result.data);
      }
      const map = result.data && typeof result.data === 'object' ? { ...result.data } : {};
      const warming = map.status === 'warming' || map._warming === true;
      // Enrich Node-only ops flags — never import/probe Python modules.
      const flags = {
        ...(map.production_flags || {}),
        CIO_MORNING_SCHEDULER: process.env.CIO_MORNING_SCHEDULER || null,
        CMS_INGEST_WORKER_MODE: process.env.CMS_INGEST_WORKER_MODE || null,
        NODE_ENRICHED: true,
      };
      map.production_flags = flags;
      if (warming) {
        return res.json(map);
      }
      if (Array.isArray(map.agents)) {
        map.agents = map.agents.map((a) => {
          if (!a || typeof a !== 'object') return a;
          if (a.id === 'cio_morning_scheduler') {
            const on = String(process.env.CIO_MORNING_SCHEDULER || '').toLowerCase() === 'true';
            return {
              ...a,
              status: on ? 'working' : a.status,
              working: on,
              detail: on
                ? 'Node CIO morning scheduler enabled (CIO_MORNING_SCHEDULER=true).'
                : a.detail,
              probe: { ...(a.probe || {}), CIO_MORNING_SCHEDULER: process.env.CIO_MORNING_SCHEDULER || null },
            };
          }
          if (a.id === 'cms_ingest_worker') {
            const mode = String(process.env.CMS_INGEST_WORKER_MODE || 'embedded').toLowerCase();
            const on = mode === 'embedded' || mode === 'external' || mode === 'true' || mode === '1';
            return {
              ...a,
              status: on ? 'working' : a.status,
              working: on,
              detail: on
                ? `CMS ingest worker mode=${mode} on Node API.`
                : a.detail,
              probe: { ...(a.probe || {}), CMS_INGEST_WORKER_MODE: mode },
            };
          }
          return a;
        });
        // Recompute summary counts after Node enrichment.
        const counts = { working: 0, soft: 0, off: 0, orphan: 0, degraded: 0, unknown: 0 };
        for (const a of map.agents) {
          const st = a?.status || 'unknown';
          counts[st] = (counts[st] || 0) + 1;
        }
        map.summary = {
          ...(map.summary || {}),
          total: map.agents.length,
          ...counts,
          working_or_soft: (counts.working || 0) + (counts.soft || 0),
          headline: `${counts.working || 0} working · ${counts.soft || 0} soft-wire · ${counts.off || 0} off · ${counts.orphan || 0} orphan`,
        };
        if (Array.isArray(map.groups)) {
          map.groups = map.groups.map((g) => {
            const agents = (map.agents || []).filter((a) => a.group === g.id);
            const gc = { working: 0, soft: 0, off: 0, orphan: 0, degraded: 0, unknown: 0 };
            for (const a of agents) gc[a.status] = (gc[a.status] || 0) + 1;
            return { ...g, agents, counts: gc };
          });
        }
      }
      return res.json(map);
    } catch (error) {
      return res.status(503).json({
        error: 'Agent Map unavailable',
        detail: error.message,
        hint: 'Snapshot reader failed — check intelligence engine / agent_map.json.',
      });
    }
  });
  router.get('/mission-control/ask-observability', async (req, res) => {
    try {
      const limit = req.query?.limit || '25';
      const result = await engineFetch(`/v1/mission-control/ask-observability?limit=${limit}`, {
        timeoutMs: 10_000,
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({
        ok: false,
        error: 'ask_observability_unavailable',
        detail: error.message,
        sample_size: 0,
      });
    }
  });

  router.get('/mission-control/dashboard', async (_req, res) => {
    try {
      // Snapshot reader — tolerate IE cold start with retry + short stale cache.
      let desk = await fetchMissionControlDashboard({ timeoutMs: 25_000, retries: 1 });
      desk = desk && typeof desk === 'object' ? { ...desk } : {};
      const warming = desk.status === 'warming' || desk._warming === true;
      if (warming) {
        // Do not fan out learning/API enrich while the desk is warming.
        return res.json(desk);
      }
      // Soft enrich with CMS/KC learning digest — never block cockpit if digest is slow.
      let learning = null;
      try {
        learning = await Promise.race([
          buildRecentLearningSummary({ engineFetch, days: 5 }),
          new Promise((resolve) => setTimeout(() => resolve(null), 1500)),
        ]);
      } catch {
        learning = null;
      }
      if (learning) {
        desk.learning_last_5_days = learning;
        desk.knowledge_growth = {
          ...(desk.knowledge_growth || {}),
          research_learned: learning.articles_learned,
          research_notes: learning.unique_articles,
          last_5_days_summary: learning.summary,
          last_5_days_highlights: learning.highlights,
          last_5_days: learning.by_day,
        };
        desk.executive_status = {
          ...(desk.executive_status || {}),
          last_successful_learning:
            learning.latest_learning_date || desk.executive_status?.last_successful_learning || null,
        };
        if (Array.isArray(desk.live_event_stream) && learning.summary) {
          desk.live_event_stream = [
            {
              at: new Date().toISOString(),
              type: 'learning',
              message: learning.summary,
            },
            ...desk.live_event_stream,
          ].slice(0, 40);
        }
      } else {
        desk.learning_enrichment = { deferred: true, reason: 'timeout_or_unavailable' };
      }

      // Soft Node API probe enrich — bounded; never blocks snapshot delivery.
      let apiProbe = null;
      try {
        apiProbe = await Promise.race([
          probeMissionControlApis({ engineFetch }),
          new Promise((resolve) => setTimeout(() => resolve(null), 2500)),
        ]);
      } catch {
        apiProbe = null;
      }

      if (apiProbe?.probes?.length) {
        desk.api_probe = {
          summary: apiProbe.summary,
          probed_at: apiProbe.probed_at,
          healthy: apiProbe.healthy,
          not_configured: apiProbe.not_configured,
          critical: apiProbe.critical,
          total: apiProbe.total,
        };
        desk.api_status = mergeApiStatus(desk.api_status || [], apiProbe.probes);
        desk.system_health = {
          ...(desk.system_health || {}),
          backend: 'Healthy',
          fastapi: apiProbe.probes.find((p) => p.name === 'Intelligence Engine')?.status || desk.system_health?.fastapi,
          database: apiProbe.probes.find((p) => p.name === 'Supabase')?.status || desk.system_health?.database,
          authentication: apiProbe.probes.find((p) => p.name === 'Supabase')?.status || desk.system_health?.authentication,
          email: apiProbe.probes.find((p) => p.name === 'Email')?.status || desk.system_health?.email,
          frontend: apiProbe.probes.find((p) => p.name === 'Hostinger')?.status || desk.system_health?.frontend,
          scheduler: apiProbe.probes.find((p) => p.name === 'Scheduler')?.status || desk.system_health?.scheduler,
          cache: apiProbe.probes.find((p) => p.name === 'Redis')?.status || desk.system_health?.cache,
          note: apiProbe.summary,
        };
      }
      // Soft enrich Groww + full .env API catalogue into API Status
      try {
        const { enrichMissionControlApis } = await import('../services/envApiCatalog.js');
        desk = await enrichMissionControlApis(desk);
      } catch {
        // never block Mission Control on provider catalogue
      }
      return res.json(desk);
    } catch (error) {
      return res.status(503).json({
        error: 'Mission Control dashboard unavailable',
        detail: error.message,
        hint:
          'Intelligence engine may be cold-starting or redeploying. Wait 30–60s and refresh. '
          + 'If it persists, check /api/intelligence/health and MC snapshot on disk.',
      });
    }
  });
  router.post('/mission-control/rebuild', async (req, res) => {
    try {
      const result = await engineFetch('/v1/mission-control/rebuild', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 15_000,
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(502).json({
        error: 'Mission Control rebuild queue failed',
        detail: error.message,
      });
    }
  });
  router.get('/mission-control/quality-gates', kfGet('/v1/mission-control/quality-gates'));
  router.get('/mission-control/api-status', async (_req, res) => {
    try {
      const result = await probeMissionControlApis({ engineFetch });
      return res.json(result);
    } catch (error) {
      return res.status(503).json({
        error: 'Mission Control API probes unavailable',
        detail: error.message,
      });
    }
  });
  router.get('/mission-control/report', kfGet('/v1/mission-control/report'));
  router.post('/mission-control/acknowledge', async (req, res) => {
    try {
      const result = await engineFetch('/v1/mission-control/acknowledge', {
        method: 'POST',
        body: req.body || {},
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Mission Control acknowledge failed' });
    }
  });

  // Soft reasoning / editorial health probes (Intelligence Map)
  router.get('/institutional-reasoning/health', kfGet('/v1/institutional-reasoning/health'));
  router.get('/answer-construction/health', kfGet('/v1/answer-construction/health'));
  router.get('/editorial/health', kfGet('/v1/editorial/health'));
  router.get('/contradiction-reasoning/health', kfGet('/v1/contradiction-reasoning/health'));
  router.get('/red-team/ecr/health', kfGet('/v1/red-team/ecr/health'));
  // NSE trading universe — EQUITY_L / NIFTYstocks (all cash equities)
  router.get('/trading-universe/health', kfGet('/v1/trading-universe/health'));
  router.get('/trading-universe/dashboard', kfGet('/v1/trading-universe/dashboard'));
  router.get('/trading-universe/symbols', async (req, res) => {
    try {
      const q = new URLSearchParams();
      if (req.query.limit != null) q.set('limit', String(req.query.limit));
      if (req.query.series) q.set('series', String(req.query.series));
      const qs = q.toString();
      const result = await engineFetch(`/v1/trading-universe/symbols${qs ? `?${qs}` : ''}`, {
        timeoutMs: 30_000,
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'trading-universe symbols failed' });
    }
  });
  router.get('/trading-universe/search', async (req, res) => {
    try {
      const q = new URLSearchParams();
      if (req.query.q) q.set('q', String(req.query.q));
      if (req.query.limit != null) q.set('limit', String(req.query.limit));
      const qs = q.toString();
      const result = await engineFetch(`/v1/trading-universe/search${qs ? `?${qs}` : ''}`, {
        timeoutMs: 20_000,
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'trading-universe search failed' });
    }
  });
  router.get('/trading-universe/symbol/:symbol', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/trading-universe/symbol/${encodeURIComponent(req.params.symbol)}`,
        { timeoutMs: 15_000 }
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'trading-universe symbol failed' });
    }
  });
  // Nifty / NSE index constituents (stocks per index)
  router.get('/market-indices/health', kfGet('/v1/market-indices/health'));
  router.get('/market-indices/dashboard', kfGet('/v1/market-indices/dashboard'));
  router.get('/market-indices', kfGet('/v1/market-indices'));
  router.get('/market-indices/membership/:symbol', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/market-indices/membership/${encodeURIComponent(req.params.symbol)}`,
        { timeoutMs: 20_000 }
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'market-indices membership failed' });
    }
  });
  router.get('/market-indices/:indexId', async (req, res) => {
    try {
      const q = new URLSearchParams();
      if (req.query.members != null) q.set('members', String(req.query.members));
      const qs = q.toString();
      const result = await engineFetch(
        `/v1/market-indices/${encodeURIComponent(req.params.indexId)}${qs ? `?${qs}` : ''}`,
        { timeoutMs: 30_000 }
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'market-indices get failed' });
    }
  });
  router.get('/market-indices/:indexId/symbols', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/market-indices/${encodeURIComponent(req.params.indexId)}/symbols`,
        { timeoutMs: 30_000 }
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'market-indices symbols failed' });
    }
  });
  // Investment Office V1 — executive operating cockpit
  router.get('/investment-office/health', kfGet('/v1/investment-office/health'));
  router.get('/investment-office/dashboard', kfGet('/v1/investment-office/dashboard'));
  router.get('/investment-office/quality-gates', kfGet('/v1/investment-office/quality-gates'));
  router.get('/investment-office/company/:ticker', async (req, res) => {
    try {
      const q = new URLSearchParams();
      if (req.query.question) q.set('question', String(req.query.question));
      if (req.query.package_type) q.set('package_type', String(req.query.package_type));
      const qs = q.toString();
      const result = await engineFetch(
        `/v1/investment-office/company/${encodeURIComponent(req.params.ticker)}${qs ? `?${qs}` : ''}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'investment-office company failed' });
    }
  });
  router.post('/investment-office/query', async (req, res) => {
    try {
      const result = await engineFetch('/v1/investment-office/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'investment-office query failed' });
    }
  });
  router.post('/investment-office/package', async (req, res) => {
    try {
      const result = await engineFetch('/v1/investment-office/package', {
        method: 'POST',
        body: req.body || {},
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Investment Office package failed' });
    }
  });

  // AGI V1.3 — Institutional Morning Office (admin desk; monitoring only)
  const ioMorningGet = (enginePath, timeoutMs = 180_000) => async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const suffix = qs ? `?${qs}` : '';
      const result = await engineFetch(`${enginePath}${suffix}`, { timeoutMs });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'Investment Office unavailable' });
    }
  };
  const ioMorningPost = (enginePath, timeoutMs = 180_000) => async (req, res) => {
    try {
      const result = await engineFetch(enginePath, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'Investment Office action failed' });
    }
  };
  // V1.3.1 — overview is snapshot-backed (fast). Heavy rebuilds via POST /refresh (async).
  router.get('/investment-office/overview', ioMorningGet('/v1/investment-office/overview', 30_000));
  router.get('/investment-office/morning-office', ioMorningGet('/v1/investment-office/morning-office', 30_000));
  router.get('/investment-office/daily-brief', ioMorningGet('/v1/investment-office/daily-brief', 30_000));
  router.get('/investment-office/research-queue', ioMorningGet('/v1/investment-office/research-queue', 30_000));
  router.get('/investment-office/opportunities', ioMorningGet('/v1/investment-office/opportunities', 30_000));
  router.get('/investment-office/market-summary', ioMorningGet('/v1/investment-office/market-summary', 30_000));
  router.get('/investment-office/macro', ioMorningGet('/v1/investment-office/macro', 30_000));
  router.get('/investment-office/calendar', ioMorningGet('/v1/investment-office/calendar', 30_000));
  router.get('/investment-office/portfolio-monitor', ioMorningGet('/v1/investment-office/portfolio-monitor', 30_000));
  router.get('/investment-office/sector-monitor', ioMorningGet('/v1/investment-office/sector-monitor', 30_000));
  router.get('/investment-office/metrics', ioMorningGet('/v1/investment-office/metrics', 30_000));
  router.get('/investment-office/snapshot', ioMorningGet('/v1/investment-office/snapshot', 15_000));
  router.get('/investment-office/system-health', ioMorningGet('/v1/investment-office/system-health', 15_000));
  router.post('/investment-office/refresh', ioMorningPost('/v1/investment-office/refresh', 60_000));
  router.post(
    '/investment-office/generate-morning-brief',
    ioMorningPost('/v1/investment-office/generate-morning-brief', 60_000)
  );

  // CIO-01 — Comparative Intelligence Office (cross-company orchestration)
  router.get('/comparative-intelligence/health', kfGet('/v1/comparative-intelligence/health'));
  router.get('/comparative-intelligence/dashboard', kfGet('/v1/comparative-intelligence/dashboard'));
  router.post('/comparative-intelligence/compare', async (req, res) => {
    try {
      const result = await engineFetch('/v1/comparative-intelligence/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'comparative-intelligence compare failed' });
    }
  });
  router.post('/comparative-intelligence/query', async (req, res) => {
    try {
      const result = await engineFetch('/v1/comparative-intelligence/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'comparative-intelligence query failed' });
    }
  });

  // Office SDK — shared application office contract
  router.get('/office-sdk/health', kfGet('/v1/office-sdk/health'));
  router.get('/office-sdk/dashboard', kfGet('/v1/office-sdk/dashboard'));
  router.get('/office-sdk/catalog', kfGet('/v1/office-sdk/catalog'));
  router.get('/office-sdk/domains', kfGet('/v1/office-sdk/domains'));
  router.post('/office-sdk/invoke', async (req, res) => {
    try {
      const result = await engineFetch('/v1/office-sdk/invoke', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'office-sdk invoke failed' });
    }
  });

  // PO-01 — Portfolio Office (canonical portfolio state)
  // Uses /portfolio-office/* to avoid colliding with Institutional Portfolio Office (/portfolio/*)
  router.get('/portfolio-office/health', kfGet('/v1/portfolio-office/health'));
  router.get('/portfolio-office/dashboard', kfGet('/v1/portfolio-office/dashboard'));
  router.get('/portfolio-office/:portfolioId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/portfolio-office/${encodeURIComponent(req.params.portfolioId)}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'portfolio-office get failed' });
    }
  });
  router.get('/portfolio-office/:portfolioId/holdings', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/portfolio-office/${encodeURIComponent(req.params.portfolioId)}/holdings`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'portfolio-office holdings failed' });
    }
  });
  router.get('/portfolio-office/:portfolioId/exposures', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/portfolio-office/${encodeURIComponent(req.params.portfolioId)}/exposures`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'portfolio-office exposures failed' });
    }
  });
  router.get('/portfolio-office/:portfolioId/quality', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/portfolio-office/${encodeURIComponent(req.params.portfolioId)}/quality`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'portfolio-office quality failed' });
    }
  });
  router.get('/portfolio-office/:portfolioId/concentration', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/portfolio-office/${encodeURIComponent(req.params.portfolioId)}/concentration`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'portfolio-office concentration failed' });
    }
  });
  router.post('/portfolio-office', async (req, res) => {
    try {
      const result = await engineFetch('/v1/portfolio-office', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'portfolio-office create failed' });
    }
  });
  router.post('/portfolio-office/:portfolioId/snapshot', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/portfolio-office/${encodeURIComponent(req.params.portfolioId)}/snapshot`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req.body || {}),
        }
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'portfolio-office snapshot failed' });
    }
  });

  // PEB-01 — Platform Event Bus
  router.get('/platform/events/health', kfGet('/v1/platform/events/health'));
  router.get('/platform/events', async (req, res) => {
    try {
      const q = new URLSearchParams();
      if (req.query.limit) q.set('limit', String(req.query.limit));
      const qs = q.toString();
      const result = await engineFetch(`/v1/platform/events${qs ? `?${qs}` : ''}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'platform events failed' });
    }
  });
  router.get('/platform/events/types', kfGet('/v1/platform/events/types'));
  router.get('/platform/events/statistics', kfGet('/v1/platform/events/statistics'));

  // WO-01 — Watchlist Office (research queue)
  router.get('/watchlist-office/health', kfGet('/v1/watchlist-office/health'));
  router.get('/watchlist-office/dashboard', kfGet('/v1/watchlist-office/dashboard'));
  router.get('/watchlist-office/:watchlistId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/watchlist-office/${encodeURIComponent(req.params.watchlistId)}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'watchlist-office get failed' });
    }
  });
  router.get('/watchlist-office/:watchlistId/queue', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/watchlist-office/${encodeURIComponent(req.params.watchlistId)}/queue`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'watchlist-office queue failed' });
    }
  });
  router.post('/watchlist-office', async (req, res) => {
    try {
      const result = await engineFetch('/v1/watchlist-office', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'watchlist-office create failed' });
    }
  });
  router.post('/watchlist-office/:watchlistId/companies', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/watchlist-office/${encodeURIComponent(req.params.watchlistId)}/companies`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req.body || {}),
        }
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'watchlist-office add failed' });
    }
  });
  router.delete('/watchlist-office/:watchlistId/companies/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/watchlist-office/${encodeURIComponent(req.params.watchlistId)}/companies/${encodeURIComponent(req.params.ticker)}`,
        { method: 'DELETE' }
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'watchlist-office remove failed' });
    }
  });

  // CW-01 — Company Workspace (primary company UX; presentation only)
  router.get('/company-workspace/health', kfGet('/v1/company-workspace/health'));
  router.get('/company-workspace/dashboard', kfGet('/v1/company-workspace/dashboard'));
  router.get('/company-workspace/:ticker', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.q) qs.set('q', String(req.query.q));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/company-workspace/${encodeURIComponent(req.params.ticker)}${suffix}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'company-workspace get failed' });
    }
  });
  router.get('/company-workspace/:ticker/timeline', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.event_type) qs.set('event_type', String(req.query.event_type));
      if (req.query?.source) qs.set('source', String(req.query.source));
      if (req.query?.q) qs.set('q', String(req.query.q));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/company-workspace/${encodeURIComponent(req.params.ticker)}/timeline${suffix}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'company-workspace timeline failed' });
    }
  });
  router.get('/company-workspace/:ticker/research', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/company-workspace/${encodeURIComponent(req.params.ticker)}/research`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'company-workspace research failed' });
    }
  });
  router.get('/company-workspace/:ticker/evidence', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.q) qs.set('q', String(req.query.q));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/company-workspace/${encodeURIComponent(req.params.ticker)}/evidence${suffix}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'company-workspace evidence failed' });
    }
  });
  router.get('/company-workspace/:ticker/search', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      qs.set('q', String(req.query?.q || ''));
      if (req.query?.scope) qs.set('scope', String(req.query.scope));
      const result = await engineFetch(
        `/v1/company-workspace/${encodeURIComponent(req.params.ticker)}/search?${qs}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'company-workspace search failed' });
    }
  });

  // IST-01 — Institutional Stress Tests (orchestration exams)
  router.get('/institutional-stress-tests/health', kfGet('/v1/institutional-stress-tests/health'));
  router.get('/institutional-stress-tests/dashboard', kfGet('/v1/institutional-stress-tests/dashboard'));
  router.get('/institutional-stress-tests/report', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.case_id) qs.set('case_id', String(req.query.case_id));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(`/v1/institutional-stress-tests/report${suffix}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'institutional-stress-tests report failed' });
    }
  });
  router.post('/institutional-stress-tests/run', async (req, res) => {
    try {
      const result = await engineFetch('/v1/institutional-stress-tests/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'institutional-stress-tests run failed' });
    }
  });
  router.post('/institutional-stress-tests/run-raw', async (req, res) => {
    try {
      const result = await engineFetch('/v1/institutional-stress-tests/run-raw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'institutional-stress-tests run-raw failed' });
    }
  });

  // IBS-01 — AGI Institutional Benchmark Suite
  router.get('/institutional-benchmarks/health', kfGet('/v1/institutional-benchmarks/health'));
  router.get('/institutional-benchmarks/dashboard', kfGet('/v1/institutional-benchmarks/dashboard'));
  router.get('/institutional-benchmarks', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.sector) qs.set('sector', String(req.query.sector));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(`/v1/institutional-benchmarks${suffix}`);
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'institutional-benchmarks list failed' });
    }
  });
  router.get('/institutional-benchmarks/:caseId', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.cutoff) qs.set('cutoff', String(req.query.cutoff));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/institutional-benchmarks/${encodeURIComponent(req.params.caseId)}${suffix}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'institutional-benchmarks get failed' });
    }
  });
  router.post('/institutional-benchmarks/run', async (req, res) => {
    try {
      const result = await engineFetch('/v1/institutional-benchmarks/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'institutional-benchmarks run failed' });
    }
  });
  router.post('/institutional-benchmarks/run-all', async (req, res) => {
    try {
      const result = await engineFetch('/v1/institutional-benchmarks/run-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'institutional-benchmarks run-all failed' });
    }
  });

  // E2E-01 — Institutional Product Experience Validation (not an engine)
  router.get('/product-experience/health', kfGet('/v1/product-experience/health'));
  router.get('/product-experience/dashboard', kfGet('/v1/product-experience/dashboard'));
  router.get('/product-experience/report', kfGet('/v1/product-experience/report'));
  router.post('/product-experience/run', async (req, res) => {
    try {
      const result = await engineFetch('/v1/product-experience/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err.message || 'product-experience run failed' });
    }
  });

  // RH-01 — AGI Release Health (IST + IBS + E2E release gate)
  // Always unwrap engineFetch → result.data (same contract as kfGet).
  router.get('/release-health/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/release-health/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      const msg = err?.message || 'release-health health failed';
      const timedOut = /timed out|aborted/i.test(msg);
      return res.status(timedOut ? 504 : 502).json({
        error: timedOut
          ? 'Release Health health check timed out — intelligence engine may be cold-starting. Retry shortly.'
          : msg,
      });
    }
  });
  router.get('/release-health/dashboard', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.refresh) qs.set('refresh', String(req.query.refresh));
      const suffix = qs.toString() ? `?${qs}` : '';
      // Snapshot path should be quick; fail fast so the admin UI can show a clear retry.
      const result = await engineFetch(`/v1/release-health/dashboard${suffix}`, {
        timeoutMs: 60_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      const msg = err?.message || 'release-health dashboard failed';
      const timedOut = /timed out|aborted/i.test(msg);
      return res.status(timedOut ? 504 : 502).json({
        error: timedOut
          ? 'Release Health dashboard timed out — intelligence engine may be cold-starting or the gate is still running. Retry shortly.'
          : msg,
      });
    }
  });
  router.post('/release-health/run', async (req, res) => {
    try {
      const result = await engineFetch('/v1/release-health/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 300_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      const msg = err?.message || 'release-health run failed';
      const timedOut = /timed out|aborted/i.test(msg);
      return res.status(timedOut ? 504 : 502).json({
        error: timedOut
          ? 'Release Health run timed out waiting for the intelligence engine. Retry once the engine is warm, or run CLI: python3 -m release_health --run'
          : msg,
      });
    }
  });

  // IRE-02 — Institutional Reporting Engine + Reason Composer (deterministic; no LLM)
  router.get('/report/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/report/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional report health failed' });
    }
  });
  router.post('/report/company', async (req, res) => {
    try {
      const result = await engineFetch('/v1/report/company', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 60_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional report compose failed' });
    }
  });
  router.get('/report/company/:ticker', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.include_reasons !== undefined) {
        qs.set('include_reasons', String(req.query.include_reasons));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/report/company/${encodeURIComponent(req.params.ticker)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional report get failed' });
    }
  });

  // IDS-01 — Institutional Decision System (deterministic; owns recommendation)
  router.get('/decision/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/decision/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional decision health failed' });
    }
  });
  router.post('/decision/company', async (req, res) => {
    try {
      const result = await engineFetch('/v1/decision/company', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 60_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional decision failed' });
    }
  });
  router.get('/decision/company/:ticker', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.include_history !== undefined) {
        qs.set('include_history', String(req.query.include_history));
      }
      if (req.query?.include_calibration !== undefined) {
        qs.set('include_calibration', String(req.query.include_calibration));
      }
      if (req.query?.include_drift !== undefined) {
        qs.set('include_drift', String(req.query.include_drift));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/decision/company/${encodeURIComponent(req.params.ticker)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional decision get failed' });
    }
  });

  // FG-01 — Forecast & Scenario Graph (deterministic propagation)
  router.get('/scenario/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/scenario/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional scenario health failed' });
    }
  });
  router.post('/scenario/company', async (req, res) => {
    try {
      const result = await engineFetch('/v1/scenario/company', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 90_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional scenario failed' });
    }
  });
  router.get('/scenario/company/:ticker', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.include_graph !== undefined) {
        qs.set('include_graph', String(req.query.include_graph));
      }
      if (req.query?.include_propagation !== undefined) {
        qs.set('include_propagation', String(req.query.include_propagation));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/scenario/company/${encodeURIComponent(req.params.ticker)}${suffix}`,
        { timeoutMs: 90_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional scenario get failed' });
    }
  });

  // KG-01 — Institutional Knowledge Graph (single-company)
  router.get('/graph/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/graph/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional graph health failed' });
    }
  });
  router.post('/graph/company', async (req, res) => {
    try {
      const result = await engineFetch('/v1/graph/company', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 60_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional graph failed' });
    }
  });
  router.get('/graph/company/:ticker', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.include_paths !== undefined) {
        qs.set('include_paths', String(req.query.include_paths));
      }
      if (req.query?.include_inference !== undefined) {
        qs.set('include_inference', String(req.query.include_inference));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/graph/company/${encodeURIComponent(req.params.ticker)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional graph get failed' });
    }
  });

  // IO-01 — Institutional Observation Engine (proactive monitoring)
  router.get('/observation/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/observation/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional observation health failed' });
    }
  });
  router.post('/observation/company', async (req, res) => {
    try {
      const result = await engineFetch('/v1/observation/company', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 60_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional observation failed' });
    }
  });
  router.get('/observation/company/:ticker', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.critical_only !== undefined) {
        qs.set('critical_only', String(req.query.critical_only));
      }
      if (req.query?.include_decision_changes !== undefined) {
        qs.set('include_decision_changes', String(req.query.include_decision_changes));
      }
      if (req.query?.refresh !== undefined) {
        qs.set('refresh', String(req.query.refresh));
      }
      if (req.query?.inject !== undefined) {
        qs.set('inject', String(req.query.inject));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/observation/company/${encodeURIComponent(req.params.ticker)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional observation get failed' });
    }
  });

  // PKG-01 / Phase 4.1 PO-01 — Portfolio Knowledge Graph
  router.get('/portfolio-graph/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/portfolio-graph/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'portfolio graph health failed' });
    }
  });
  router.post('/portfolio-graph', async (req, res) => {
    try {
      const result = await engineFetch('/v1/portfolio-graph', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 60_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'portfolio graph failed' });
    }
  });
  router.get('/portfolio-graph/:portfolioId', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.include_company_graphs !== undefined) {
        qs.set('include_company_graphs', String(req.query.include_company_graphs));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/portfolio-graph/${encodeURIComponent(req.params.portfolioId)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'portfolio graph get failed' });
    }
  });
  router.get('/portfolio-graph/:portfolioId/portfolio', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/portfolio-graph/${encodeURIComponent(req.params.portfolioId)}/portfolio`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional portfolio get failed' });
    }
  });

  // CIO-01 — Institutional Portfolio Decision System
  router.get('/portfolio-decision/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/portfolio-decision/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'portfolio decision health failed' });
    }
  });
  router.post('/portfolio-decision', async (req, res) => {
    try {
      const result = await engineFetch('/v1/portfolio-decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 60_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'portfolio decision failed' });
    }
  });
  router.get('/portfolio-decision/:portfolioId', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.refresh !== undefined) qs.set('refresh', String(req.query.refresh));
      if (req.query?.include_history !== undefined) {
        qs.set('include_history', String(req.query.include_history));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/portfolio-decision/${encodeURIComponent(req.params.portfolioId)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'portfolio decision get failed' });
    }
  });

  // PRE-01 — Institutional Portfolio Risk Engine
  router.get('/portfolio-risk/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/portfolio-risk/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'portfolio risk health failed' });
    }
  });
  router.post('/portfolio-risk', async (req, res) => {
    try {
      const result = await engineFetch('/v1/portfolio-risk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 60_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'portfolio risk failed' });
    }
  });
  router.get('/portfolio-risk/:portfolioId', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.refresh !== undefined) qs.set('refresh', String(req.query.refresh));
      if (req.query?.include_history !== undefined) {
        qs.set('include_history', String(req.query.include_history));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/portfolio-risk/${encodeURIComponent(req.params.portfolioId)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'portfolio risk get failed' });
    }
  });

  // PCE-01 — Institutional Policy & Constraint Engine
  router.get('/policy/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/policy/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'policy health failed' });
    }
  });
  router.post('/policy/check', async (req, res) => {
    try {
      const result = await engineFetch('/v1/policy/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 60_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'policy check failed' });
    }
  });
  router.get('/policy/:portfolioId', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.refresh !== undefined) qs.set('refresh', String(req.query.refresh));
      if (req.query?.include_history !== undefined) {
        qs.set('include_history', String(req.query.include_history));
      }
      if (req.query?.policy !== undefined) qs.set('policy', String(req.query.policy));
      if (req.query?.profile_id !== undefined) qs.set('profile_id', String(req.query.profile_id));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/policy/${encodeURIComponent(req.params.portfolioId)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'policy get failed' });
    }
  });

  // UAG-01 — Universal Ask AGI Orchestrator
  router.get('/orchestrator/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/orchestrator/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'orchestrator health failed' });
    }
  });
  router.post('/ask', async (req, res) => {
    try {
      const result = await engineFetch('/v1/ask', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 90_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'universal ask failed' });
    }
  });
  router.post('/ask/stream', async (req, res) => {
    try {
      const result = await engineFetch('/v1/ask/stream', {
        method: 'POST',
        body: req.body || {},
        timeoutMs: 90_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'universal ask stream failed' });
    }
  });
  router.get('/query/:queryId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/query/${encodeURIComponent(req.params.queryId)}`,
        { timeoutMs: 30_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'query get failed' });
    }
  });

  // RW-01 — Institutional Research Workspace
  router.get('/workspace/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/workspace/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'workspace health failed' });
    }
  });
  router.get('/workspace/company/:ticker', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.focus) qs.set('focus', String(req.query.focus));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/workspace/company/${encodeURIComponent(req.params.ticker)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'company workspace failed' });
    }
  });
  router.get('/workspace/portfolio/:id', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.focus) qs.set('focus', String(req.query.focus));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/workspace/portfolio/${encodeURIComponent(req.params.id)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'portfolio workspace failed' });
    }
  });
  router.get('/workspace/object/:id', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.object_type) qs.set('object_type', String(req.query.object_type));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/workspace/object/${encodeURIComponent(req.params.id)}${suffix}`,
        { timeoutMs: 30_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'workspace object failed' });
    }
  });
  router.get('/workspace/timeline/:id', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.context_type) qs.set('context_type', String(req.query.context_type));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/workspace/timeline/${encodeURIComponent(req.params.id)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'workspace timeline failed' });
    }
  });
  router.get('/workspace/search', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.q) qs.set('q', String(req.query.q));
      if (req.query.context_type) qs.set('context_type', String(req.query.context_type));
      if (req.query.context_id) qs.set('context_id', String(req.query.context_id));
      const result = await engineFetch(`/v1/workspace/search?${qs}`, { timeoutMs: 30_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'workspace search failed' });
    }
  });
  router.post('/workspace/notes', async (req, res) => {
    try {
      const result = await engineFetch('/v1/workspace/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 30_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'workspace notes failed' });
    }
  });

  // CCI-01 — Cross-Company Intelligence
  router.get('/relationships/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/relationships/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'relationships health failed' });
    }
  });
  router.get('/relationships/company/:ticker', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.portfolio_id) qs.set('portfolio_id', String(req.query.portfolio_id));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/relationships/company/${encodeURIComponent(req.params.ticker)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'company relationships failed' });
    }
  });
  router.get('/relationships/sector/:sector', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/relationships/sector/${encodeURIComponent(req.params.sector)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'sector relationships failed' });
    }
  });
  router.get('/relationships/macro/:driver', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/relationships/macro/${encodeURIComponent(req.params.driver)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'macro relationships failed' });
    }
  });
  router.post('/relationships/query', async (req, res) => {
    try {
      const result = await engineFetch('/v1/relationships/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 90_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'relationships query failed' });
    }
  });
  router.get('/relationships/similar/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/relationships/similar/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 30_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'similarity failed' });
    }
  });
  router.get('/relationships/clusters', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/relationships/clusters', { timeoutMs: 30_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'clusters failed' });
    }
  });

  // PUB-01 — Publishing & Distribution
  router.get('/publications/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/publications/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'publications health failed' });
    }
  });
  router.get('/publications/types', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/publications/types', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'publications types failed' });
    }
  });
  router.get('/publications', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.limit) qs.set('limit', String(req.query.limit));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(`/v1/publications${suffix}`, { timeoutMs: 30_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'publications list failed' });
    }
  });
  router.post('/publications/generate', async (req, res) => {
    try {
      const result = await engineFetch('/v1/publications/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 90_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'publications generate failed' });
    }
  });
  router.get('/publications/:id', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/publications/${encodeURIComponent(req.params.id)}`,
        { timeoutMs: 30_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'publication get failed' });
    }
  });
  router.post('/publications/export', async (req, res) => {
    try {
      const result = await engineFetch('/v1/publications/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 90_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'publications export failed' });
    }
  });

  // MPC-01 — Multi-Portfolio & Client Platform
  router.get('/platform/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/platform/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'platform health failed' });
    }
  });
  router.get('/portfolios', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/portfolios', { timeoutMs: 30_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'portfolios list failed' });
    }
  });
  router.post('/portfolios', async (req, res) => {
    try {
      const result = await engineFetch('/v1/portfolios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 30_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'portfolio create failed' });
    }
  });
  router.get('/clients', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/clients', { timeoutMs: 30_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'clients list failed' });
    }
  });
  router.post('/clients', async (req, res) => {
    try {
      const result = await engineFetch('/v1/clients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 30_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'client create failed' });
    }
  });
  router.get('/workspaces/:id', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      for (const k of ['portfolio_id', 'client_id', 'role_id', 'user_id', 'mandate_id']) {
        if (req.query[k]) qs.set(k, String(req.query[k]));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/workspaces/${encodeURIComponent(req.params.id)}${suffix}`,
        { timeoutMs: 30_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'workspace get failed' });
    }
  });
  router.post('/workspaces/resolve', async (req, res) => {
    try {
      const result = await engineFetch('/v1/workspaces/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 30_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'workspace resolve failed' });
    }
  });
  router.post('/permissions', async (req, res) => {
    try {
      const result = await engineFetch('/v1/permissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 30_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'permissions failed' });
    }
  });
  router.post('/platform/context', async (req, res) => {
    try {
      const result = await engineFetch('/v1/platform/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 30_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'platform context failed' });
    }
  });
  router.post('/platform/ask', async (req, res) => {
    try {
      const result = await engineFetch('/v1/platform/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 90_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'platform ask failed' });
    }
  });

  // PRP-01 — Performance & Scale
  router.get('/performance/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/performance/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'performance health failed' });
    }
  });
  router.get('/performance/metrics', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/performance/metrics', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'performance metrics failed' });
    }
  });
  router.get('/performance/cache', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/performance/cache', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'performance cache failed' });
    }
  });
  router.post('/performance/cache/get', async (req, res) => {
    try {
      const result = await engineFetch('/v1/performance/cache/get', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 20_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'performance cache get failed' });
    }
  });
  router.post('/performance/cache/set', async (req, res) => {
    try {
      const result = await engineFetch('/v1/performance/cache/set', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 20_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'performance cache set failed' });
    }
  });
  router.get('/performance/queue', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/performance/queue', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'performance queue failed' });
    }
  });
  router.get('/performance/jobs', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.limit) qs.set('limit', String(req.query.limit));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(`/v1/performance/jobs${suffix}`, { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'performance jobs list failed' });
    }
  });
  router.post('/performance/jobs', async (req, res) => {
    try {
      const result = await engineFetch('/v1/performance/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 30_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'performance job enqueue failed' });
    }
  });
  router.get('/performance/jobs/:jobId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/performance/jobs/${encodeURIComponent(req.params.jobId)}`,
        { timeoutMs: 20_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'performance job get failed' });
    }
  });
  router.post('/performance/graph/incremental', async (req, res) => {
    try {
      const result = await engineFetch('/v1/performance/graph/incremental', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 30_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'graph incremental failed' });
    }
  });
  router.post('/performance/parallel', async (req, res) => {
    try {
      const result = await engineFetch('/v1/performance/parallel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 30_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'performance parallel failed' });
    }
  });

  // PRP-02 — Security & Governance
  router.get('/security/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/security/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'security health failed' });
    }
  });
  router.post('/auth/login', async (req, res) => {
    try {
      const result = await engineFetch('/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 30_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'auth login failed' });
    }
  });
  router.post('/auth/logout', async (req, res) => {
    try {
      const result = await engineFetch('/v1/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 20_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'auth logout failed' });
    }
  });
  router.post('/auth/refresh', async (req, res) => {
    try {
      const result = await engineFetch('/v1/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 20_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'auth refresh failed' });
    }
  });
  router.get('/security/context', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      for (const k of ['session_id', 'user_id', 'tenant_id', 'correlation_id']) {
        if (req.query[k]) qs.set(k, String(req.query[k]));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(`/v1/security/context${suffix}`, { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'security context failed' });
    }
  });
  router.post('/security/context', async (req, res) => {
    try {
      const result = await engineFetch('/v1/security/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 20_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'security context failed' });
    }
  });
  router.get('/security/audit', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      for (const k of ['limit', 'tenant_id', 'user_id', 'action', 'correlation_id', 'session_id']) {
        if (req.query[k]) qs.set(k, String(req.query[k]));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(`/v1/security/audit${suffix}`, { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'security audit failed' });
    }
  });
  router.post('/security/audit', async (req, res) => {
    try {
      const result = await engineFetch('/v1/security/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 20_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'security audit failed' });
    }
  });
  router.post('/security/api-keys', async (req, res) => {
    try {
      const result = await engineFetch('/v1/security/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 30_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'api key create failed' });
    }
  });
  router.delete('/security/api-keys/:id', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/security/api-keys/${encodeURIComponent(req.params.id)}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 20_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'api key revoke failed' });
    }
  });
  router.get('/security/roles', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/security/roles', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'security roles failed' });
    }
  });
  router.get('/security/permissions', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/security/permissions', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'security permissions failed' });
    }
  });
  router.get('/security/tenants', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/security/tenants', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'security tenants failed' });
    }
  });

  // PRP-03 — Observability & Operations
  router.get('/ops/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/ops/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'ops health failed' });
    }
  });
  router.get('/observability/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/observability/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'observability health failed' });
    }
  });
  router.get('/ops/metrics', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/ops/metrics', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'ops metrics failed' });
    }
  });
  router.get('/ops/traces/:traceId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/ops/traces/${encodeURIComponent(req.params.traceId)}`,
        { timeoutMs: 20_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'ops trace failed' });
    }
  });
  router.get('/ops/service-map', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/ops/service-map', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'ops service-map failed' });
    }
  });
  router.get('/ops/alerts', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/ops/alerts', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'ops alerts failed' });
    }
  });
  router.get('/ops/dependencies', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/ops/dependencies', { timeoutMs: 30_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'ops dependencies failed' });
    }
  });
  router.get('/ops/logs', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      for (const k of ['limit', 'severity', 'correlation_id', 'component']) {
        if (req.query[k]) qs.set(k, String(req.query[k]));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(`/v1/ops/logs${suffix}`, { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'ops logs failed' });
    }
  });

  // RC-01 — Architecture Conformance & Release Candidate
  router.get('/architecture/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/architecture/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'architecture health failed' });
    }
  });
  router.get('/architecture/conformance', async (req, res) => {
    try {
      const qs = req.query.force ? '?force=true' : '';
      const result = await engineFetch(`/v1/architecture/conformance${qs}`, { timeoutMs: 90_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'architecture conformance failed' });
    }
  });
  router.post('/architecture/conformance', async (req, res) => {
    try {
      const result = await engineFetch('/v1/architecture/conformance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 90_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'architecture conformance failed' });
    }
  });
  router.get('/architecture/report', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/architecture/report', { timeoutMs: 90_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'architecture report failed' });
    }
  });
  router.get('/architecture/violations', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/architecture/violations', { timeoutMs: 90_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'architecture violations failed' });
    }
  });

  // L-01 — Launch Phase
  router.get('/launch/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/launch/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'launch health failed' });
    }
  });
  router.get('/launch/metrics', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/launch/metrics', { timeoutMs: 30_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'launch metrics failed' });
    }
  });
  router.get('/launch/funnel', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/launch/funnel', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'launch funnel failed' });
    }
  });
  router.post('/launch/events', async (req, res) => {
    try {
      const result = await engineFetch('/v1/launch/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 20_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'launch event failed' });
    }
  });
  router.post('/launch/journey', async (req, res) => {
    try {
      const result = await engineFetch('/v1/launch/journey', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 20_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'launch journey failed' });
    }
  });
  router.post('/launch/feedback', async (req, res) => {
    try {
      const result = await engineFetch('/v1/launch/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 20_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'launch feedback failed' });
    }
  });
  router.get('/launch/feedback', async (req, res) => {
    try {
      const qs = req.query.limit ? `?limit=${encodeURIComponent(String(req.query.limit))}` : '';
      const result = await engineFetch(`/v1/launch/feedback${qs}`, { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'launch feedback list failed' });
    }
  });
  router.get('/launch/flags', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/launch/flags', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'launch flags failed' });
    }
  });
  router.post('/launch/flags', async (req, res) => {
    try {
      const result = await engineFetch('/v1/launch/flags', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 20_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'launch flag set failed' });
    }
  });
  router.get('/launch/sla', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/launch/sla', { timeoutMs: 30_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'launch sla failed' });
    }
  });
  router.get('/launch/report', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/launch/report', { timeoutMs: 60_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'launch report failed' });
    }
  });

  // PAT-01 — Production Acceptance Test
  router.get('/acceptance/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/acceptance/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'acceptance health failed' });
    }
  });
  router.post('/acceptance/run', async (req, res) => {
    try {
      const result = await engineFetch('/v1/acceptance/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 180_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'acceptance run failed' });
    }
  });
  router.get('/acceptance/report', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/acceptance/report', { timeoutMs: 180_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'acceptance report failed' });
    }
  });
  router.get('/acceptance/cases', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.limit !== undefined) qs.set('limit', String(req.query.limit));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(`/v1/acceptance/cases${suffix}`, { timeoutMs: 180_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'acceptance cases failed' });
    }
  });
  router.get('/acceptance/phase/:phase', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/acceptance/phase/${encodeURIComponent(req.params.phase)}`,
        { timeoutMs: 90_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'acceptance phase failed' });
    }
  });
  router.post('/acceptance/phase/:phase', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/acceptance/phase/${encodeURIComponent(req.params.phase)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req.body || {}),
          timeoutMs: 90_000,
        }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'acceptance phase run failed' });
    }
  });
  router.get('/acceptance/diagnostics', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/acceptance/diagnostics', { timeoutMs: 30_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'acceptance diagnostics failed' });
    }
  });

  // IEP-01 — Institutional Evidence Platform (AGI v1.1)
  router.get('/iep/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/iep/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep health failed' });
    }
  });
  router.get('/iep/status', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/iep/status', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep status failed' });
    }
  });
  router.get('/iep/pack/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/pack/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 90_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep pack failed' });
    }
  });
  router.get('/iep/readiness/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/readiness/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep readiness failed' });
    }
  });
  router.get('/iep/validate/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/validate/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep validate failed' });
    }
  });
  router.post('/iep/orchestrate/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/orchestrate/${encodeURIComponent(req.params.ticker)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req.body || {}),
          timeoutMs: 120_000,
        }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep orchestrate failed' });
    }
  });
  router.get('/iep/registry/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/registry/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep registry failed' });
    }
  });
  router.get('/iep/canonical/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/canonical/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep canonical failed' });
    }
  });
  router.get('/iep/memory/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/memory/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep memory failed' });
    }
  });
  router.get('/iep/phase1', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/iep/phase1', { timeoutMs: 180_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep phase1 failed' });
    }
  });
  router.get('/iep/metrics', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/iep/metrics', { timeoutMs: 180_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep metrics failed' });
    }
  });
  router.get('/iep/center', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/iep/center', { timeoutMs: 180_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep center failed' });
    }
  });
  router.get('/iep/gates/writer/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/gates/writer/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep writer gate failed' });
    }
  });
  router.post('/iep/gates/decision/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/gates/decision/${encodeURIComponent(req.params.ticker)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req.body || {}),
          timeoutMs: 60_000,
        }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep decision gate failed' });
    }
  });
  router.get('/iep/gates/publish/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/gates/publish/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep publish gate failed' });
    }
  });

  // IEP v1.1.1 — Knowledge OS + institutional company APIs
  router.get('/iep/entity/:query', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/entity/${encodeURIComponent(req.params.query)}`,
        { timeoutMs: 30_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep entity failed' });
    }
  });
  router.get('/iep/timeline/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/timeline/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep timeline failed' });
    }
  });
  router.get('/iep/graph/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/graph/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep graph failed' });
    }
  });
  router.get('/iep/eligibility/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/eligibility/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep eligibility failed' });
    }
  });
  router.get('/iep/quality/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/quality/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep quality failed' });
    }
  });
  router.get('/iep/domains/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/domains/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep domains failed' });
    }
  });
  router.get('/iep/coverage/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/coverage/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 90_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep coverage failed' });
    }
  });
  router.post('/iep/learn/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/learn/${encodeURIComponent(req.params.ticker)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req.body || {}),
          timeoutMs: 120_000,
        }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep learn failed' });
    }
  });
  router.get('/iep/lifecycle/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/lifecycle/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 30_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep lifecycle failed' });
    }
  });
  router.get('/iep/observability', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/iep/observability', { timeoutMs: 180_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep observability failed' });
    }
  });
  router.get('/iep/company/:companyRef', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/company/${encodeURIComponent(req.params.companyRef)}`,
        { timeoutMs: 120_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep company failed' });
    }
  });
  router.get('/iep/company/:companyRef/:resource', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/company/${encodeURIComponent(req.params.companyRef)}/${encodeURIComponent(req.params.resource)}`,
        { timeoutMs: 120_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep company resource failed' });
    }
  });

  // KIL-01 — Knowledge Integration Layer (AGI v1.1.2)
  router.get('/iep/kil/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/iep/kil/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'kil health failed' });
    }
  });
  router.post('/iep/kil/integrate', async (req, res) => {
    try {
      const result = await engineFetch('/v1/iep/kil/integrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 180_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'kil integrate failed' });
    }
  });
  router.post('/iep/kil/integrate/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/kil/integrate/${encodeURIComponent(req.params.ticker)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req.body || {}),
          timeoutMs: 120_000,
        }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'kil integrate company failed' });
    }
  });
  router.get('/iep/knowledge-health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/iep/knowledge-health', { timeoutMs: 180_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'knowledge health failed' });
    }
  });
  router.get('/iep/knowledge-confidence/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/knowledge-confidence/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'knowledge confidence failed' });
    }
  });
  router.get('/iep/coverage-state/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/iep/coverage-state/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 90_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'coverage state failed' });
    }
  });
  router.get('/iep/snapshots', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/iep/snapshots', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'snapshots failed' });
    }
  });
  router.get('/iep/events', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/iep/events', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'kil events failed' });
    }
  });
  router.post('/iep/ask/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/iep/ask/${encodeURIComponent(req.params.ticker)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 120_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'iep ask orchestrate failed' });
    }
  });
  router.get('/iep/expansion', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/iep/expansion', { timeoutMs: 120_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'expansion status failed' });
    }
  });
  router.post('/iep/expansion/nifty500', async (req, res) => {
    try {
      const result = await engineFetch('/v1/iep/expansion/nifty500', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 120_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'expansion enqueue failed' });
    }
  });

  // ICF-01 — Institutional Coverage Factory
  router.get('/icf/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/icf/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'icf health failed' });
    }
  });
  router.get('/icf/status', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/icf/status', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'icf status failed' });
    }
  });
  router.get('/icf/dashboard', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.scope) qs.set('scope', String(req.query.scope));
      if (req.query?.sample_limit != null) qs.set('sample_limit', String(req.query.sample_limit));
      const suffix = qs.toString() ? `?${qs.toString()}` : '';
      const result = await engineFetch(`/v1/icf/dashboard${suffix}`, { timeoutMs: 180_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'icf dashboard failed' });
    }
  });
  router.get('/icf/score/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/icf/score/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 90_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'icf score failed' });
    }
  });
  router.get('/icf/icc/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/icf/icc/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 90_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'icf icc failed' });
    }
  });
  router.get('/icf/plan', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.scope) qs.set('scope', String(req.query.scope));
      if (req.query?.limit != null) qs.set('limit', String(req.query.limit));
      const suffix = qs.toString() ? `?${qs.toString()}` : '';
      const result = await engineFetch(`/v1/icf/plan${suffix}`, { timeoutMs: 180_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'icf plan failed' });
    }
  });
  router.post('/icf/plan-dispatch', async (req, res) => {
    try {
      const result = await engineFetch('/v1/icf/plan-dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 180_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'icf plan-dispatch failed' });
    }
  });
  router.post('/icf/tick', async (req, res) => {
    try {
      const result = await engineFetch('/v1/icf/tick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 180_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'icf tick failed' });
    }
  });
  router.post('/icf/dispatch/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/icf/dispatch/${encodeURIComponent(req.params.ticker)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req.body || {}),
          timeoutMs: 180_000,
        }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'icf dispatch failed' });
    }
  });
  router.get('/icf/scheduler', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/icf/scheduler', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'icf scheduler failed' });
    }
  });

  // KOC V1.2 — Institutional Knowledge Mission Control
  // When the engine is down, return a degraded shell so the admin page opens
  // instead of hanging on long proxy timeouts.
  const kocGet = (path, timeoutMs = 60_000) => async (req, res) => {
    try {
      const qs = new URLSearchParams();
      for (const [k, v] of Object.entries(req.query || {})) {
        if (v != null && v !== '') qs.set(k, String(v));
      }
      const suffix = qs.toString() ? `?${qs.toString()}` : '';
      const result = await engineFetch(`/v1${path}${suffix}`, { timeoutMs });
      return res.status(result.status).json(result.data);
    } catch (err) {
      const detail = err?.message || `koc ${path} failed`;
      if (path === '/koc/health' || path === '/koc/status') {
        return res.status(200).json(buildKocDegradedHealth(detail));
      }
      if (path === '/koc/overview' || path === '/koc/desk' || path === '/koc/coverage') {
        return res.status(200).json(
          buildKocDegradedOverview({ scope: req.query?.scope || 'TOP20', detail })
        );
      }
      if (path === '/koc/audit') {
        return res.status(200).json(buildKocDegradedAudit({ limit: req.query?.limit, detail }));
      }
      if (path === '/koc/missing-inbox' || path === '/koc/missing-knowledge') {
        const deg = buildKocDegradedOverview({ scope: req.query?.scope || 'TOP20', detail });
        return res.status(200).json({ ...deg.missing_inbox, ok: false, degraded: true, error: detail });
      }
      return res.status(502).json({ error: detail, degraded: true });
    }
  };
  const kocPost = (path, timeoutMs = 180_000) => async (req, res) => {
    try {
      const result = await engineFetch(`/v1${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || `koc ${path} failed`, degraded: true });
    }
  };
  router.get('/koc/health', kocGet('/koc/health', 8_000));
  router.get('/koc/status', kocGet('/koc/status', 8_000));
  router.get('/koc/overview', kocGet('/koc/overview', 45_000));
  router.get('/koc/desk', kocGet('/koc/desk', 45_000));
  router.get('/koc/system-health', kocGet('/koc/system-health', 20_000));
  router.get('/koc/coverage', kocGet('/koc/coverage', 45_000));
  router.get('/koc/missing-inbox', kocGet('/koc/missing-inbox', 45_000));
  router.get('/koc/missing-knowledge', kocGet('/koc/missing-knowledge', 45_000));
  router.get('/koc/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/koc/company/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'koc company failed', degraded: true });
    }
  });
  router.get('/koc/collectors', kocGet('/koc/collectors', 20_000));
  router.get('/koc/evidence', kocGet('/koc/evidence', 45_000));
  router.get('/koc/evidence/:ticker/:documentId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/koc/evidence/${encodeURIComponent(req.params.ticker)}/${encodeURIComponent(req.params.documentId)}`,
        { timeoutMs: 45_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'koc evidence detail failed', degraded: true });
    }
  });
  router.get('/koc/knowledge-versions', kocGet('/koc/knowledge-versions', 20_000));
  router.get('/koc/gap-ai', kocGet('/koc/gap-ai', 45_000));
  router.get('/koc/gap-ai/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/koc/gap-ai/${encodeURIComponent(req.params.ticker)}`,
        { timeoutMs: 45_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'koc gap-ai failed', degraded: true });
    }
  });
  router.get('/koc/search', kocGet('/koc/search', 30_000));
  router.post('/koc/upload', kocPost('/koc/upload'));
  router.get('/koc/queue', kocGet('/koc/queue', 20_000));
  router.get('/koc/audit', kocGet('/koc/audit', 12_000));
  router.post('/koc/action', kocPost('/koc/action'));
  router.post('/koc/run-cgl', kocPost('/koc/run-cgl'));
  router.post('/koc/run-kil', kocPost('/koc/run-kil'));
  router.post('/koc/run-coverage', kocPost('/koc/run-coverage'));
  router.post('/koc/repair', kocPost('/koc/repair'));

  // ICE-01 — Investment Committee Engine
  router.get('/committee-engine/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/committee-engine/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'committee engine health failed' });
    }
  });
  router.post('/committee/review', async (req, res) => {
    try {
      const result = await engineFetch('/v1/committee/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 90_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'committee review failed' });
    }
  });
  router.get('/committee/pending', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/committee/pending', { timeoutMs: 30_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'committee pending failed' });
    }
  });
  router.get('/committee/resolution/:resolutionId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/committee/resolution/${encodeURIComponent(req.params.resolutionId)}`,
        { timeoutMs: 30_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'committee resolution get failed' });
    }
  });
  router.get('/committee/portfolio/:portfolioId', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.refresh !== undefined) qs.set('refresh', String(req.query.refresh));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/committee/portfolio/${encodeURIComponent(req.params.portfolioId)}${suffix}`,
        { timeoutMs: 90_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'committee portfolio get failed' });
    }
  });

  // IDS-02 — Decision Calibration & Explainability
  router.get('/calibration/health', async (_req, res) => {
    try {
      const result = await engineFetch('/v1/calibration/health', { timeoutMs: 20_000 });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional calibration health failed' });
    }
  });
  router.post('/calibration/company', async (req, res) => {
    try {
      const result = await engineFetch('/v1/calibration/company', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
        timeoutMs: 60_000,
      });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional calibration failed' });
    }
  });
  router.get('/calibration/company/:ticker', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.include_calibration !== undefined) {
        qs.set('include_calibration', String(req.query.include_calibration));
      }
      if (req.query?.include_drift !== undefined) {
        qs.set('include_drift', String(req.query.include_drift));
      }
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(
        `/v1/calibration/company/${encodeURIComponent(req.params.ticker)}${suffix}`,
        { timeoutMs: 60_000 }
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'institutional calibration get failed' });
    }
  });

  // AGI v4.0 Investment Office OS — Thesis / Decision / Portfolio / Monitoring / Learning
  // Static paths before dynamic :id routes. Ideas ≠ positions; events recommend review only.
  const v4Get = (enginePath) => async (_req, res) => {
    try {
      const result = await engineFetch(enginePath);
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'Investment Office GET failed' });
    }
  };
  const v4Post = (enginePath) => async (req, res) => {
    try {
      const result = await engineFetch(enginePath, { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'Investment Office POST failed' });
    }
  };

  router.get('/thesis/health', v4Get('/v1/thesis/health'));
  router.get('/thesis/dashboard', v4Get('/v1/thesis/dashboard'));
  router.get('/thesis/telemetry', v4Get('/v1/thesis/telemetry'));
  router.get('/thesis/history', v4Get('/v1/thesis/history'));
  router.post('/thesis/create', v4Post('/v1/thesis/create'));
  router.post('/thesis/list', v4Post('/v1/thesis/list'));
  router.get('/thesis/:thesisId/versions', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/thesis/${encodeURIComponent(req.params.thesisId)}/versions`
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'Thesis versions failed' });
    }
  });
  router.get('/thesis/:thesisId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/thesis/${encodeURIComponent(req.params.thesisId)}`);
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'Thesis get failed' });
    }
  });

  router.get('/decision/health', v4Get('/v1/decision/health'));
  router.get('/decision/dashboard', v4Get('/v1/decision/dashboard'));
  router.get('/decision/telemetry', v4Get('/v1/decision/telemetry'));
  router.get('/decision/history', v4Get('/v1/decision/history'));
  router.post('/decision/deliberate', v4Post('/v1/decision/deliberate'));
  router.post('/decision/list', v4Post('/v1/decision/list'));
  router.get('/decision/:decisionId/versions', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/decision/${encodeURIComponent(req.params.decisionId)}/versions`
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'Decision versions failed' });
    }
  });
  router.get('/decision/:decisionId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/decision/${encodeURIComponent(req.params.decisionId)}`
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'Decision get failed' });
    }
  });

  router.get('/portfolio/health', v4Get('/v1/portfolio/health'));
  router.get('/portfolio/dashboard', v4Get('/v1/portfolio/dashboard'));
  router.get('/portfolio/telemetry', v4Get('/v1/portfolio/telemetry'));
  router.get('/portfolio/history', v4Get('/v1/portfolio/history'));
  router.post('/portfolio/create', v4Post('/v1/portfolio/create'));
  router.post('/portfolio/list', v4Post('/v1/portfolio/list'));
  router.post('/portfolio/ranking', v4Post('/v1/portfolio/ranking'));
  router.get('/portfolio/:ideaId/versions', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/portfolio/${encodeURIComponent(req.params.ideaId)}/versions`
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'Portfolio idea versions failed' });
    }
  });
  router.get('/portfolio/:ideaId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/portfolio/${encodeURIComponent(req.params.ideaId)}`);
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'Portfolio idea get failed' });
    }
  });

  router.get('/monitoring/health', v4Get('/v1/monitoring/health'));
  router.get('/monitoring/dashboard', v4Get('/v1/monitoring/dashboard'));
  router.get('/monitoring/telemetry', v4Get('/v1/monitoring/telemetry'));
  router.get('/monitoring/history', v4Get('/v1/monitoring/history'));
  router.post('/monitoring/create', v4Post('/v1/monitoring/create'));
  router.post('/monitoring/list', v4Post('/v1/monitoring/list'));
  router.post('/monitoring/review-queue', v4Post('/v1/monitoring/review-queue'));
  router.get('/monitoring/:eventId', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/monitoring/${encodeURIComponent(req.params.eventId)}`);
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'Monitoring event get failed' });
    }
  });

  router.get('/learning/health', v4Get('/v1/learning/health'));
  router.get('/learning/dashboard', v4Get('/v1/learning/dashboard'));
  router.get('/learning/telemetry', v4Get('/v1/learning/telemetry'));
  router.get('/learning/history', v4Get('/v1/learning/history'));
  router.post('/learning/create', v4Post('/v1/learning/create'));
  router.post('/learning/list', v4Post('/v1/learning/list'));
  router.get('/learning/:learningId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/learning/${encodeURIComponent(req.params.learningId)}`
      );
      return res.status(result.status).json(result.data);
    } catch (err) {
      return res.status(502).json({ error: err?.message || 'Learning get failed' });
    }
  });

  // Company Monitoring System V1 — continuous living analyst
  router.get('/company-monitor/health', kfGet('/v1/company-monitor/health'));
  router.get('/company-monitor/dashboard', kfGet('/v1/company-monitor/dashboard'));
  router.get('/company-monitor/quality-gates', kfGet('/v1/company-monitor/quality-gates'));
  router.get('/company-monitor/changes', kfGet('/v1/company-monitor/changes'));
  router.get('/company-monitor/alerts', kfGet('/v1/company-monitor/alerts'));
  router.get('/company-monitor/reviews', kfGet('/v1/company-monitor/reviews'));
  router.post('/company-monitor/run', async (req, res) => {
    try {
      const result = await engineFetch('/v1/company-monitor/run', {
        method: 'POST',
        body: req.body || {},
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Company monitor run failed' });
    }
  });
  router.post('/company-monitor/run-universe', async (req, res) => {
    try {
      const result = await engineFetch('/v1/company-monitor/run-universe', {
        method: 'POST',
        body: req.body || {},
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Company monitor universe run failed' });
    }
  });

  // Company Analysis Engine V1 — apply Academy to companies (not Context Assembly)
  router.get('/company-analysis/health', kfGet('/v1/company-analysis/health'));
  router.get('/company-analysis/dashboard', kfGet('/v1/company-analysis/dashboard'));
  router.get('/company-analysis/quality-gates', kfGet('/v1/company-analysis/quality-gates'));
  router.get('/company-analysis/reports', kfGet('/v1/company-analysis/reports'));
  router.get('/company-analysis/report/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/company-analysis/report/${encodeURIComponent(req.params.ticker)}`
      );
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Company analysis report failed' });
    }
  });
  router.post('/company-analysis/analyse', async (req, res) => {
    try {
      const result = await engineFetch('/v1/company-analysis/analyse', {
        method: 'POST',
        body: req.body || {},
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Company analysis failed' });
    }
  });

  // Institutional Analyst Framework V1 — Answer Construction orchestration (not engines)
  router.get('/institutional-analysts/health', kfGet('/v1/institutional-analysts/health'));
  router.get('/institutional-analysts/quality-gates', kfGet('/v1/institutional-analysts/quality-gates'));

  // Investment Committee Intelligence V1 — deliberation / vote / minutes
  router.get('/investment-committee/health', kfGet('/v1/investment-committee/health'));
  router.get('/investment-committee/quality-gates', kfGet('/v1/investment-committee/quality-gates'));

  // Institutional Research Writer V1 — presentation/writing layer after CIO
  router.get('/research-writer/health', kfGet('/v1/research-writer/health'));
  router.get('/research-writer/quality-gates', kfGet('/v1/research-writer/quality-gates'));
  router.get('/investment-committee/timeline/:ticker', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.limit) qs.set('limit', String(req.query.limit));
      const path = `/v1/investment-committee/timeline/${encodeURIComponent(req.params.ticker)}${qs.toString() ? `?${qs}` : ''}`;
      res.json(await engineFetch(path));
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Committee timeline failed' });
    }
  });
  router.post('/investment-committee/record-actuals', async (req, res) => {
    try {
      res.json(
        await engineFetch('/v1/investment-committee/record-actuals', {
          method: 'POST',
          body: req.body || {},
        })
      );
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Committee actuals failed' });
    }
  });

  // AGIB Intelligence Layer V2 — living institutional research (soft-wire)
  router.get('/ail/health', kfGet('/v1/ail/health'));
  router.get('/ail/dashboard', kfGet('/v1/ail/dashboard'));
  router.get('/ail/analyse', kfGet('/v1/ail/analyse'));
  router.post('/ail/monitor/run', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.watchlist) qs.set('watchlist', String(req.query.watchlist));
      const result = await engineFetch(`/v1/ail/monitor/run${qs.toString() ? `?${qs}` : ''}`, {
        method: 'POST',
        body: {},
      });
      res.json(result);
    } catch (err) {
      res.status(502).json({ error: err?.message || 'AIL monitor run failed' });
    }
  });
  router.get('/company/:ticker/dossier', async (req, res) => {
    try {
      res.json(await engineFetch(`/v1/company/${encodeURIComponent(req.params.ticker)}/dossier`));
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Company dossier failed' });
    }
  });
  router.get('/company/:ticker/timeline', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.limit) qs.set('limit', String(req.query.limit));
      res.json(
        await engineFetch(
          `/v1/company/${encodeURIComponent(req.params.ticker)}/timeline${qs.toString() ? `?${qs}` : ''}`
        )
      );
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Company timeline failed' });
    }
  });
  router.get('/company/:ticker/events', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query?.limit) qs.set('limit', String(req.query.limit));
      res.json(
        await engineFetch(
          `/v1/company/${encodeURIComponent(req.params.ticker)}/events${qs.toString() ? `?${qs}` : ''}`
        )
      );
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Company events failed' });
    }
  });
  router.get('/company/:ticker/thesis', async (req, res) => {
    try {
      res.json(await engineFetch(`/v1/company/${encodeURIComponent(req.params.ticker)}/thesis`));
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Company thesis failed' });
    }
  });
  router.get('/company/:ticker/forecast', async (req, res) => {
    try {
      res.json(await engineFetch(`/v1/company/${encodeURIComponent(req.params.ticker)}/forecast`));
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Company forecast failed' });
    }
  });
  router.get('/company/:ticker/ledger', async (req, res) => {
    try {
      res.json(await engineFetch(`/v1/company/${encodeURIComponent(req.params.ticker)}/ledger`));
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Company ledger failed' });
    }
  });
  router.get('/company/:ticker/monitor', async (req, res) => {
    try {
      res.json(await engineFetch(`/v1/company/${encodeURIComponent(req.params.ticker)}/monitor`));
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Company monitor failed' });
    }
  });
  router.get('/event/:id', async (req, res) => {
    try {
      res.json(await engineFetch(`/v1/event/${encodeURIComponent(req.params.id)}`));
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Event lookup failed' });
    }
  });
  // AGIB v3.2 IERE — Institutional Evidence Retrieval Engine
  // Static paths MUST be registered before /evidence/:id.
  router.get('/evidence/health', kfGet('/v1/evidence/health'));
  router.get('/evidence/dashboard', kfGet('/v1/evidence/dashboard'));
  router.get('/evidence/search', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/evidence/search${qs ? `?${qs}` : ''}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Evidence search unavailable', detail: error.message });
    }
  });
  router.get('/evidence/company/:ticker', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(
        `/v1/evidence/company/${encodeURIComponent(req.params.ticker)}${qs ? `?${qs}` : ''}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Company evidence unavailable', detail: error.message });
    }
  });
  router.get('/evidence/document/:docId', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/evidence/document/${encodeURIComponent(req.params.docId)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Document evidence unavailable', detail: error.message });
    }
  });
  router.get('/evidence/graph', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/evidence/graph${qs ? `?${qs}` : ''}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Evidence graph unavailable', detail: error.message });
    }
  });
  router.get('/evidence/replay', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(`/v1/evidence/replay${qs ? `?${qs}` : ''}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Evidence replay unavailable', detail: error.message });
    }
  });
  router.get('/evidence/:id', async (req, res) => {
    try {
      res.json(await engineFetch(`/v1/evidence/${encodeURIComponent(req.params.id)}`));
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Evidence lookup failed' });
    }
  });
  router.get('/prediction/:id', async (req, res) => {
    try {
      res.json(await engineFetch(`/v1/prediction/${encodeURIComponent(req.params.id)}`));
    } catch (err) {
      res.status(502).json({ error: err?.message || 'Prediction lookup failed' });
    }
  });

  // --- Institutional Intelligence Stack (FIL→FDI→MII→EIL→PIL) ---
  router.get('/institutional-stack/health', kfGet('/v1/institutional-stack/health'));
  router.get('/institutional-stack/dashboard', kfGet('/v1/institutional-stack/dashboard'));
  router.get('/institutional-stack/quality-gates', kfGet('/v1/institutional-stack/quality-gates'));
  router.get('/institutional-stack/company/:ticker', async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query).toString();
      const result = await engineFetch(
        `/v1/institutional-stack/company/${encodeURIComponent(req.params.ticker)}${qs ? `?${qs}` : ''}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Institutional stack unavailable', detail: error.message });
    }
  });
  router.post('/institutional-stack/analyse', async (req, res) => {
    try {
      const result = await engineFetch('/v1/institutional-stack/analyse', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Institutional stack analyse failed', detail: error.message });
    }
  });
  router.post('/institutional-stack/ingest', async (req, res) => {
    try {
      const result = await engineFetch('/v1/institutional-stack/ingest', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Institutional stack ingest failed', detail: error.message });
    }
  });
  router.post('/institutional-stack/bootstrap', async (req, res) => {
    try {
      const result = await engineFetch('/v1/institutional-stack/bootstrap', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Institutional stack bootstrap failed', detail: error.message });
    }
  });

  // Layer proxies (EIL / PIL / FIL / FDI / MII)
  router.get('/academy/evidence/health', kfGet('/v1/academy/evidence/health'));
  router.get('/academy/evidence/dashboard', kfGet('/v1/academy/evidence/dashboard'));
  router.get('/academy/evidence/quality-gates', kfGet('/v1/academy/evidence/quality-gates'));
  router.get('/academy/evidence/case/:id', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/academy/evidence/case/${encodeURIComponent(req.params.id)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Evidence intelligence unavailable', detail: error.message });
    }
  });

  router.get('/peer-intelligence/health', kfGet('/v1/peer-intelligence/health'));
  router.get('/peer-intelligence/dashboard', kfGet('/v1/peer-intelligence/dashboard'));
  router.get('/peer-intelligence/quality-gates', kfGet('/v1/peer-intelligence/quality-gates'));
  router.get('/peer-intelligence/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/peer-intelligence/company/${encodeURIComponent(req.params.ticker)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Peer intelligence unavailable', detail: error.message });
    }
  });
  router.post('/peer-intelligence/analyse', async (req, res) => {
    try {
      const result = await engineFetch('/v1/peer-intelligence/analyse', { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Peer intelligence analyse failed', detail: error.message });
    }
  });

  router.get('/filing-intelligence/health', kfGet('/v1/filing-intelligence/health'));
  router.get('/filing-intelligence/dashboard', kfGet('/v1/filing-intelligence/dashboard'));
  router.get('/filing-intelligence/quality-gates', kfGet('/v1/filing-intelligence/quality-gates'));
  router.get('/filing-intelligence/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/filing-intelligence/company/${encodeURIComponent(req.params.ticker)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Filing intelligence unavailable', detail: error.message });
    }
  });
  router.post('/filing-intelligence/analyse', async (req, res) => {
    try {
      const result = await engineFetch('/v1/filing-intelligence/analyse', { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Filing intelligence analyse failed', detail: error.message });
    }
  });
  router.post('/filing-intelligence/ingest', async (req, res) => {
    try {
      const result = await engineFetch('/v1/filing-intelligence/ingest', { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Filing intelligence ingest failed', detail: error.message });
    }
  });

  router.get('/filing-diff/health', kfGet('/v1/filing-diff/health'));
  router.get('/filing-diff/dashboard', kfGet('/v1/filing-diff/dashboard'));
  router.get('/filing-diff/quality-gates', kfGet('/v1/filing-diff/quality-gates'));
  router.get('/filing-diff/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/filing-diff/company/${encodeURIComponent(req.params.ticker)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Filing diff unavailable', detail: error.message });
    }
  });
  router.post('/filing-diff/analyse', async (req, res) => {
    try {
      const result = await engineFetch('/v1/filing-diff/analyse', { method: 'POST', body: req.body || {} });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Filing diff analyse failed', detail: error.message });
    }
  });

  router.get('/management-intelligence/health', kfGet('/v1/management-intelligence/health'));
  router.get('/management-intelligence/dashboard', kfGet('/v1/management-intelligence/dashboard'));
  router.get('/management-intelligence/quality-gates', kfGet('/v1/management-intelligence/quality-gates'));
  router.get('/management-intelligence/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/management-intelligence/company/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Management intelligence unavailable', detail: error.message });
    }
  });
  router.get('/management-intelligence/guidance/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/management-intelligence/guidance/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Management guidance unavailable', detail: error.message });
    }
  });
  router.post('/management-intelligence/analyse', async (req, res) => {
    try {
      const result = await engineFetch('/v1/management-intelligence/analyse', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Management intelligence analyse failed', detail: error.message });
    }
  });

  // Financial Statements Engine + FDO (soft-wire ops)
  router.get('/financial-statements/health', kfGet('/v1/financial-statements/health'));
  router.get('/financial-statements/dashboard', kfGet('/v1/financial-statements/dashboard'));
  router.get('/financial-statements/fdo/dashboard', async (req, res) => {
    try {
      const q = req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
      const result = await engineFetch(`/v1/financial-statements/fdo/dashboard${q}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'FDO dashboard unavailable', detail: error.message });
    }
  });
  router.get('/financial-statements/fdo/schedule', async (req, res) => {
    try {
      const q = req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
      const result = await engineFetch(`/v1/financial-statements/fdo/schedule${q}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'FDO schedule unavailable', detail: error.message });
    }
  });
  router.get('/financial-statements/fdo/alerts', async (req, res) => {
    try {
      const q = req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
      const result = await engineFetch(`/v1/financial-statements/fdo/alerts${q}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'FDO alerts unavailable', detail: error.message });
    }
  });
  router.get('/financial-statements/coverage', async (req, res) => {
    try {
      const q = req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
      const result = await engineFetch(`/v1/financial-statements/coverage${q}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'FSE coverage unavailable', detail: error.message });
    }
  });
  router.get('/financial-statements/coverage/:company', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/financial-statements/coverage/${encodeURIComponent(req.params.company)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'FSE company coverage unavailable', detail: error.message });
    }
  });
  router.get('/financial-statements/source-health', kfGet('/v1/financial-statements/source-health'));
  router.get(
    '/financial-statements/collection/health',
    kfGet('/v1/financial-statements/collection/health')
  );
  router.get(
    '/financial-statements/collection/dashboard',
    kfGet('/v1/financial-statements/collection/dashboard')
  );
  router.get(
    '/financial-statements/collection/source-coverage',
    kfGet('/v1/financial-statements/collection/source-coverage')
  );
  router.get(
    '/financial-statements/collection/source-registry',
    kfGet('/v1/financial-statements/collection/source-registry')
  );
  router.get(
    '/financial-statements/orchestrator/health',
    kfGet('/v1/financial-statements/orchestrator/health')
  );
  router.get(
    '/financial-statements/orchestrator/dashboard',
    kfGet('/v1/financial-statements/orchestrator/dashboard')
  );
  router.get(
    '/financial-statements/warehouse/health',
    kfGet('/v1/financial-statements/warehouse/health')
  );
  router.get(
    '/financial-statements/warehouse/dashboard',
    kfGet('/v1/financial-statements/warehouse/dashboard')
  );
  router.get(
    '/financial-statements/verification/dashboard',
    kfGet('/v1/financial-statements/verification/dashboard')
  );
  router.get(
    '/financial-statements/evidence-coverage/dashboard',
    kfGet('/v1/financial-statements/evidence-coverage/dashboard')
  );

  // FKB-01 — Institutional Financial Knowledge Base
  router.get('/knowledge/health', kfGet('/v1/knowledge/health'));
  router.get('/knowledge/dashboard', kfGet('/v1/knowledge/dashboard'));
  router.get('/knowledge/metrics', kfGet('/v1/knowledge/metrics'));
  router.get('/knowledge/ratios', kfGet('/v1/knowledge/ratios'));
  router.get('/knowledge/relationships', kfGet('/v1/knowledge/relationships'));
  router.get('/knowledge/glossary', kfGet('/v1/knowledge/glossary'));
  router.get('/knowledge/thresholds', async (req, res) => {
    try {
      const q = req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
      const result = await engineFetch(`/v1/knowledge/thresholds${q}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge thresholds unavailable', detail: error.message });
    }
  });

  // FIRE-01 — Financial Narrative & Trend Engine
  router.get('/financial-intelligence/health', kfGet('/v1/financial-intelligence/health'));
  router.get('/financial-intelligence/dashboard', kfGet('/v1/financial-intelligence/dashboard'));
  router.get('/financial-intelligence/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/financial-intelligence/company/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Financial intelligence unavailable', detail: error.message });
    }
  });
  router.get('/financial-intelligence/findings/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/financial-intelligence/findings/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Financial findings unavailable', detail: error.message });
    }
  });
  router.get('/financial-intelligence/company/:ticker/drivers', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/financial-intelligence/company/${encodeURIComponent(req.params.ticker)}/drivers`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Financial drivers unavailable', detail: error.message });
    }
  });
  router.get('/financial-intelligence/company/:ticker/relationships', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/financial-intelligence/company/${encodeURIComponent(req.params.ticker)}/relationships`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Financial relationships unavailable', detail: error.message });
    }
  });

  // FIRE-03 — Business & Management Intelligence
  router.get('/business-intelligence/health', kfGet('/v1/business-intelligence/health'));
  router.get('/business-intelligence/dashboard', kfGet('/v1/business-intelligence/dashboard'));
  router.get('/business-intelligence/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/business-intelligence/company/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Business intelligence unavailable', detail: error.message });
    }
  });
  router.get('/business-intelligence/company/:ticker/segments', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/business-intelligence/company/${encodeURIComponent(req.params.ticker)}/segments`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Business segments unavailable', detail: error.message });
    }
  });
  router.get('/business-intelligence/company/:ticker/strategy', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/business-intelligence/company/${encodeURIComponent(req.params.ticker)}/strategy`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Business strategy unavailable', detail: error.message });
    }
  });
  router.get('/business-intelligence/company/:ticker/risks', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/business-intelligence/company/${encodeURIComponent(req.params.ticker)}/risks`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Business risks unavailable', detail: error.message });
    }
  });
  router.get('/business-intelligence/company/:ticker/guidance', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/business-intelligence/company/${encodeURIComponent(req.params.ticker)}/guidance`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Business guidance unavailable', detail: error.message });
    }
  });

  // FIRE-04 — Evidence Fusion Engine
  router.get('/evidence-fusion/health', kfGet('/v1/evidence-fusion/health'));
  router.get('/evidence-fusion/dashboard', kfGet('/v1/evidence-fusion/dashboard'));
  router.get('/evidence-fusion/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/evidence-fusion/company/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Evidence fusion unavailable', detail: error.message });
    }
  });
  router.get('/evidence-fusion/company/:ticker/supported', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/evidence-fusion/company/${encodeURIComponent(req.params.ticker)}/supported`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Evidence fusion supported unavailable', detail: error.message });
    }
  });
  router.get('/evidence-fusion/company/:ticker/conflicts', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/evidence-fusion/company/${encodeURIComponent(req.params.ticker)}/conflicts`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Evidence fusion conflicts unavailable', detail: error.message });
    }
  });
  router.get('/evidence-fusion/company/:ticker/alignment', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/evidence-fusion/company/${encodeURIComponent(req.params.ticker)}/alignment`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Evidence fusion alignment unavailable', detail: error.message });
    }
  });

  // FIRE-05 — Management Execution & Temporal Evidence
  router.get('/management-execution/health', kfGet('/v1/management-execution/health'));
  router.get('/management-execution/dashboard', kfGet('/v1/management-execution/dashboard'));
  router.get('/management-execution/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/management-execution/company/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Management execution unavailable', detail: error.message });
    }
  });
  router.get('/management-execution/company/:ticker/timeline', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/management-execution/company/${encodeURIComponent(req.params.ticker)}/timeline`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Management execution timeline unavailable', detail: error.message });
    }
  });
  router.get('/management-execution/company/:ticker/score', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/management-execution/company/${encodeURIComponent(req.params.ticker)}/score`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Management execution score unavailable', detail: error.message });
    }
  });
  router.get('/management-execution/company/:ticker/objectives', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/management-execution/company/${encodeURIComponent(req.params.ticker)}/objectives`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Management execution objectives unavailable', detail: error.message });
    }
  });

  // FIRE-06 — Business Quality Engine
  router.get('/business-quality/health', kfGet('/v1/business-quality/health'));
  router.get('/business-quality/dashboard', kfGet('/v1/business-quality/dashboard'));
  router.get('/business-quality/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/business-quality/company/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Business quality unavailable', detail: error.message });
    }
  });
  router.get('/business-quality/company/:ticker/quality', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/business-quality/company/${encodeURIComponent(req.params.ticker)}/quality`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Business quality score unavailable', detail: error.message });
    }
  });
  router.get('/business-quality/company/:ticker/pillars', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/business-quality/company/${encodeURIComponent(req.params.ticker)}/pillars`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Business quality pillars unavailable', detail: error.message });
    }
  });

  // Accounting Intelligence Engine
  router.get('/accounting-intelligence/health', kfGet('/v1/accounting-intelligence/health'));
  router.get('/accounting-intelligence/dashboard', kfGet('/v1/accounting-intelligence/dashboard'));
  router.get('/accounting-intelligence/quality-gates', kfGet('/v1/accounting-intelligence/quality-gates'));
  router.get('/accounting-intelligence/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/accounting-intelligence/company/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Accounting intelligence unavailable', detail: error.message });
    }
  });
  router.get('/accounting-intelligence/history/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/accounting-intelligence/history/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Accounting history unavailable', detail: error.message });
    }
  });
  router.post('/accounting-intelligence/analyse', async (req, res) => {
    try {
      const result = await engineFetch('/v1/accounting-intelligence/analyse', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Accounting intelligence analyse failed', detail: error.message });
    }
  });

  // Portfolio Intelligence Office
  router.get('/portfolio-intelligence/health', kfGet('/v1/portfolio-intelligence/health'));
  router.get('/portfolio-intelligence/dashboard', kfGet('/v1/portfolio-intelligence/dashboard'));
  router.get('/portfolio-intelligence/quality-gates', kfGet('/v1/portfolio-intelligence/quality-gates'));
  router.get('/portfolio-intelligence/portfolio/:id', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/portfolio-intelligence/portfolio/${encodeURIComponent(req.params.id)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Portfolio intelligence unavailable', detail: error.message });
    }
  });
  router.get('/portfolio-intelligence/health/:id', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/portfolio-intelligence/health/${encodeURIComponent(req.params.id)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Portfolio health unavailable', detail: error.message });
    }
  });
  router.get('/portfolio-intelligence/scenarios/:id', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/portfolio-intelligence/scenarios/${encodeURIComponent(req.params.id)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Portfolio scenarios unavailable', detail: error.message });
    }
  });
  router.post('/portfolio-intelligence/analyse', async (req, res) => {
    try {
      const result = await engineFetch('/v1/portfolio-intelligence/analyse', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Portfolio intelligence analyse failed', detail: error.message });
    }
  });

  // Causal Intelligence Graph V1 — why did this happen?
  router.get('/causal-intelligence/health', kfGet('/v1/causal-intelligence/health'));
  router.get('/causal-intelligence/dashboard', kfGet('/v1/causal-intelligence/dashboard'));
  router.get('/causal-intelligence/quality-gates', kfGet('/v1/causal-intelligence/quality-gates'));
  router.get('/causal-intelligence/graph', kfGet('/v1/causal-intelligence/graph'));
  router.get('/causal-intelligence/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/causal-intelligence/company/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Causal company unavailable', detail: error.message });
    }
  });
  router.get('/causal-intelligence/event/:event', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/causal-intelligence/event/${encodeURIComponent(req.params.event)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Causal event unavailable', detail: error.message });
    }
  });
  router.post('/causal-intelligence/analyse', async (req, res) => {
    try {
      const result = await engineFetch('/v1/causal-intelligence/analyse', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Causal intelligence analyse failed', detail: error.message });
    }
  });

  // Forecast Intelligence Engine V1 — what future paths are plausible?
  router.get('/forecast/health', kfGet('/v1/forecast/health'));
  router.get('/forecast/dashboard', kfGet('/v1/forecast/dashboard'));
  router.get('/forecast/quality-gates', kfGet('/v1/forecast/quality-gates'));
  router.get('/forecast/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/forecast/company/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecast company unavailable', detail: error.message });
    }
  });
  router.get('/forecast/scenarios/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/forecast/scenarios/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecast scenarios unavailable', detail: error.message });
    }
  });
  router.get('/forecast/catalysts/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/forecast/catalysts/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecast catalysts unavailable', detail: error.message });
    }
  });
  router.post('/forecast/analyse', async (req, res) => {
    try {
      const result = await engineFetch('/v1/forecast/analyse', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Forecast analyse failed', detail: error.message });
    }
  });

  // Institutional Knowledge Graph V1 — what is connected?
  router.get('/knowledge-graph/health', kfGet('/v1/knowledge-graph/health'));
  router.get('/knowledge-graph/dashboard', kfGet('/v1/knowledge-graph/dashboard'));
  router.get('/knowledge-graph/quality-gates', kfGet('/v1/knowledge-graph/quality-gates'));
  router.get('/knowledge-graph/entity/:id', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/knowledge-graph/entity/${encodeURIComponent(req.params.id)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge entity unavailable', detail: error.message });
    }
  });
  router.get('/knowledge-graph/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/knowledge-graph/company/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge company unavailable', detail: error.message });
    }
  });
  router.get('/knowledge-graph/relationships/:id', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/knowledge-graph/relationships/${encodeURIComponent(req.params.id)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge relationships unavailable', detail: error.message });
    }
  });
  router.get('/knowledge-graph/path', async (req, res) => {
    try {
      const qs = new URLSearchParams({
        source: String(req.query.source || ''),
        target: String(req.query.target || ''),
      }).toString();
      const result = await engineFetch(`/v1/knowledge-graph/path?${qs}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge path unavailable', detail: error.message });
    }
  });
  router.post('/knowledge-graph/query', async (req, res) => {
    try {
      const result = await engineFetch('/v1/knowledge-graph/query', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Knowledge query failed', detail: error.message });
    }
  });

  // Institutional Learning & Memory Engine V1 — what have we learned?
  router.get('/ilm/health', kfGet('/v1/ilm/health'));
  router.get('/ilm/dashboard', kfGet('/v1/ilm/dashboard'));
  router.get('/ilm/quality-gates', kfGet('/v1/ilm/quality-gates'));
  router.get('/ilm/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/ilm/company/${encodeURIComponent(req.params.ticker)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ILM company unavailable', detail: error.message });
    }
  });
  router.get('/ilm/thesis/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/ilm/thesis/${encodeURIComponent(req.params.ticker)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ILM thesis unavailable', detail: error.message });
    }
  });
  router.get('/ilm/committee/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/ilm/committee/${encodeURIComponent(req.params.ticker)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ILM committee unavailable', detail: error.message });
    }
  });
  router.get('/ilm/forecast/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/ilm/forecast/${encodeURIComponent(req.params.ticker)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ILM forecast unavailable', detail: error.message });
    }
  });
  router.get('/ilm/portfolio/:id', async (req, res) => {
    try {
      const result = await engineFetch(`/v1/ilm/portfolio/${encodeURIComponent(req.params.id)}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ILM portfolio unavailable', detail: error.message });
    }
  });
  router.post('/ilm/learning/update', async (req, res) => {
    try {
      const result = await engineFetch('/v1/ilm/learning/update', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ILM learning update failed', detail: error.message });
    }
  });

  // Institutional Simulation & Strategy Lab V1 — what happens if we decide?
  router.get('/simulation/health', kfGet('/v1/simulation/health'));
  router.get('/simulation/dashboard', kfGet('/v1/simulation/dashboard'));
  router.get('/simulation/quality-gates', kfGet('/v1/simulation/quality-gates'));
  router.get('/simulation/scenarios', kfGet('/v1/simulation/scenarios'));
  router.get('/simulation/history', async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.limit) qs.set('limit', String(req.query.limit));
      const suffix = qs.toString() ? `?${qs}` : '';
      const result = await engineFetch(`/v1/simulation/history${suffix}`);
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'SSL history unavailable', detail: error.message });
    }
  });
  router.post('/simulation/run', async (req, res) => {
    try {
      const result = await engineFetch('/v1/simulation/run', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'SSL run failed', detail: error.message });
    }
  });
  router.post('/simulation/portfolio', async (req, res) => {
    try {
      const result = await engineFetch('/v1/simulation/portfolio', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'SSL portfolio simulation failed', detail: error.message });
    }
  });

  // Institutional Decision Engine V2 — final constitutional orchestrator
  router.get('/decision-engine-v2/health', kfGet('/v1/decision-engine-v2/health'));
  router.get('/decision-engine-v2/dashboard', kfGet('/v1/decision-engine-v2/dashboard'));
  router.get('/decision-engine-v2/quality-gates', kfGet('/v1/decision-engine-v2/quality-gates'));
  router.get('/decision-engine-v2/freeze-review', kfGet('/v1/decision-engine-v2/freeze-review'));
  router.get('/decision-engine-v2/company/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/decision-engine-v2/company/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IDE V2 company unavailable', detail: error.message });
    }
  });
  router.get('/decision-engine-v2/audit/:id', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/decision-engine-v2/audit/${encodeURIComponent(req.params.id)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IDE V2 audit unavailable', detail: error.message });
    }
  });
  router.get('/decision-engine-v2/monitoring/:ticker', async (req, res) => {
    try {
      const result = await engineFetch(
        `/v1/decision-engine-v2/monitoring/${encodeURIComponent(req.params.ticker)}`
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IDE V2 monitoring unavailable', detail: error.message });
    }
  });
  router.post('/decision-engine-v2/analyse', async (req, res) => {
    try {
      const result = await engineFetch('/v1/decision-engine-v2/analyse', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IDE V2 analyse failed', detail: error.message });
    }
  });

  // Soft-wire validation / quality surfaces for Intelligence Map (always probeable)
  router.get('/academy/certification/health', kfGet('/v1/academy/certification/health'));
  router.get('/academy/regression/health', kfGet('/v1/academy/regression/health'));
  router.get('/leo/health', kfGet('/v1/leo/health'));
  router.get('/dvc/health', kfGet('/v1/dvc/health'));
  router.get('/company-dossier', kfGet('/v1/company-dossier'));
  router.get('/company-dossier/quality-gates', kfGet('/v1/company-dossier/quality-gates'));
  router.get('/company-dossier/health', kfGet('/v1/company-dossier/health'));
  router.get('/company-dossier/:ticker', proxyGet((req) =>
    `/v1/company-dossier/${encodeURIComponent(req.params.ticker)}`));
  router.get('/company-dossier/:ticker/timeline', proxyGet((req) => {
    const limit = Math.max(1, Math.min(500, Number(req.query.limit) || 100));
    return `/v1/company-dossier/${encodeURIComponent(req.params.ticker)}/timeline?limit=${limit}`;
  }));
  router.get('/company-dossier/:ticker/coverage', proxyGet((req) =>
    `/v1/company-dossier/${encodeURIComponent(req.params.ticker)}/coverage`));
  router.get('/company-dossier/:ticker/valuation', proxyGet((req) =>
    `/v1/company-dossier/${encodeURIComponent(req.params.ticker)}/valuation`));
  router.get('/company-dossier/:ticker/risk', proxyGet((req) =>
    `/v1/company-dossier/${encodeURIComponent(req.params.ticker)}/risk`));
  router.get('/company-dossier/:ticker/forecast', proxyGet((req) =>
    `/v1/company-dossier/${encodeURIComponent(req.params.ticker)}/forecast`));
  router.get('/company-dossier/:ticker/documents', proxyGet((req) =>
    `/v1/company-dossier/${encodeURIComponent(req.params.ticker)}/documents`));
  router.post('/company-dossier/:ticker/generate', async (req, res) => {
    try {
      const refresh = String(req.query.refresh_evidence || 'true').toLowerCase() !== 'false';
      const result = await engineFetch(
        `/v1/company-dossier/${encodeURIComponent(req.params.ticker)}/generate?refresh_evidence=${refresh}`,
        { method: 'POST', body: req.body || {}, timeoutMs: 120_000 },
      );
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Company dossier generation unavailable', detail: error.message });
    }
  });
  router.get('/decision-engine/health', kfGet('/v1/decision-engine/health'));

  // RQ1 Research Ontology — Sprint 1 classify-only (not a top-level intelligence layer)
  router.get('/research-ontology/health', kfGet('/v1/research-ontology/health'));
  router.get('/research-ontology/dashboard', kfGet('/v1/research-ontology/dashboard'));
  router.get('/research-ontology/constitution', kfGet('/v1/research-ontology/constitution'));
  router.get('/research-ontology/quality-gates', kfGet('/v1/research-ontology/quality-gates'));
  router.post('/research-ontology/classify', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-ontology/classify', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'RQ1 research ontology classify failed', detail: error.message });
    }
  });

  // RQ1 Entity Resolution Engine — Sprint 2 identity soft-wire (IKG source of truth)
  router.get('/entity-resolution/health', kfGet('/v1/entity-resolution/health'));
  router.get('/entity-resolution/dashboard', kfGet('/v1/entity-resolution/dashboard'));
  router.get('/entity-resolution/constitution', kfGet('/v1/entity-resolution/constitution'));
  router.get('/entity-resolution/quality-gates', kfGet('/v1/entity-resolution/quality-gates'));
  router.post('/entity-resolution/resolve', async (req, res) => {
    try {
      const result = await engineFetch('/v1/entity-resolution/resolve', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ERE resolve failed', detail: error.message });
    }
  });
  router.post('/entity-resolution/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/entity-resolution/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ERE diagnostics failed', detail: error.message });
    }
  });

  // RQ1 Research Objective Engine — Sprint 3 objective planning soft-wire
  router.get('/research-objective/health', kfGet('/v1/research-objective/health'));
  router.get('/research-objective/dashboard', kfGet('/v1/research-objective/dashboard'));
  router.get('/research-objective/constitution', kfGet('/v1/research-objective/constitution'));
  router.get('/research-objective/quality-gates', kfGet('/v1/research-objective/quality-gates'));
  router.post('/research-objective/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-objective/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ROE plan failed', detail: error.message });
    }
  });
  router.post('/research-objective/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-objective/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ROE diagnostics failed', detail: error.message });
    }
  });

  // RQ1 Context Intelligence Engine — Sprint 4 context enrichment soft-wire
  router.get('/context-intelligence/health', kfGet('/v1/context-intelligence/health'));
  router.get('/context-intelligence/dashboard', kfGet('/v1/context-intelligence/dashboard'));
  router.get('/context-intelligence/constitution', kfGet('/v1/context-intelligence/constitution'));
  router.get('/context-intelligence/quality-gates', kfGet('/v1/context-intelligence/quality-gates'));
  router.post('/context-intelligence/enrich', async (req, res) => {
    try {
      const result = await engineFetch('/v1/context-intelligence/enrich', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'CIE enrich failed', detail: error.message });
    }
  });
  router.post('/context-intelligence/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/context-intelligence/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'CIE diagnostics failed', detail: error.message });
    }
  });

  // RQ1 Institutional Analyst Router — Sprint 5 participation soft-wire
  router.get('/analyst-router/health', kfGet('/v1/analyst-router/health'));
  router.get('/analyst-router/dashboard', kfGet('/v1/analyst-router/dashboard'));
  router.get('/analyst-router/constitution', kfGet('/v1/analyst-router/constitution'));
  router.get('/analyst-router/quality-gates', kfGet('/v1/analyst-router/quality-gates'));
  router.post('/analyst-router/route', async (req, res) => {
    try {
      const result = await engineFetch('/v1/analyst-router/route', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IAR route failed', detail: error.message });
    }
  });
  router.post('/analyst-router/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/analyst-router/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IAR diagnostics failed', detail: error.message });
    }
  });

  // RQ1 Intelligence Layer Router — Sprint 6 execution planner soft-wire
  router.get('/layer-router/health', kfGet('/v1/layer-router/health'));
  router.get('/layer-router/dashboard', kfGet('/v1/layer-router/dashboard'));
  router.get('/layer-router/constitution', kfGet('/v1/layer-router/constitution'));
  router.get('/layer-router/quality-gates', kfGet('/v1/layer-router/quality-gates'));
  router.post('/layer-router/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/layer-router/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ILR plan failed', detail: error.message });
    }
  });
  router.post('/layer-router/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/layer-router/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ILR diagnostics failed', detail: error.message });
    }
  });


  // RQ1 Institutional Acquisition & API Planning Engine — Sprint 7 soft-wire
  router.get('/acquisition-planner/health', kfGet('/v1/acquisition-planner/health'));
  router.get('/acquisition-planner/dashboard', kfGet('/v1/acquisition-planner/dashboard'));
  router.get('/acquisition-planner/constitution', kfGet('/v1/acquisition-planner/constitution'));
  router.get('/acquisition-planner/quality-gates', kfGet('/v1/acquisition-planner/quality-gates'));
  router.post('/acquisition-planner/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/acquisition-planner/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IAPE plan failed', detail: error.message });
    }
  });
  router.post('/acquisition-planner/enrich', async (req, res) => {
    try {
      const result = await engineFetch('/v1/acquisition-planner/enrich', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IAPE enrich failed', detail: error.message });
    }
  });
  router.post('/acquisition-planner/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/acquisition-planner/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IAPE diagnostics failed', detail: error.message });
    }
  });

  // RQ1 Dynamic Research Blueprint Engine — Sprint 8 soft-wire
  router.get('/research-blueprint/health', kfGet('/v1/research-blueprint/health'));
  router.get('/research-blueprint/dashboard', kfGet('/v1/research-blueprint/dashboard'));
  router.get('/research-blueprint/constitution', kfGet('/v1/research-blueprint/constitution'));
  router.get('/research-blueprint/quality-gates', kfGet('/v1/research-blueprint/quality-gates'));
  router.post('/research-blueprint/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-blueprint/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'DRBE plan failed', detail: error.message });
    }
  });
  router.post('/research-blueprint/enrich', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-blueprint/enrich', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'DRBE enrich failed', detail: error.message });
    }
  });
  router.post('/research-blueprint/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-blueprint/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'DRBE diagnostics failed', detail: error.message });
    }
  });

  // RQ1 Institutional Validation & Clarification Engine — Sprint 9 soft-wire
  router.get('/validation-engine/health', kfGet('/v1/validation-engine/health'));
  router.get('/validation-engine/dashboard', kfGet('/v1/validation-engine/dashboard'));
  router.get('/validation-engine/constitution', kfGet('/v1/validation-engine/constitution'));
  router.get('/validation-engine/quality-gates', kfGet('/v1/validation-engine/quality-gates'));
  router.post('/validation-engine/validate', async (req, res) => {
    try {
      const result = await engineFetch('/v1/validation-engine/validate', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IVCE validate failed', detail: error.message });
    }
  });
  router.post('/validation-engine/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/validation-engine/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IVCE plan failed', detail: error.message });
    }
  });
  router.post('/validation-engine/enrich', async (req, res) => {
    try {
      const result = await engineFetch('/v1/validation-engine/enrich', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IVCE enrich failed', detail: error.message });
    }
  });
  router.post('/validation-engine/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/validation-engine/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IVCE diagnostics failed', detail: error.message });
    }
  });

  // RQ1 Institutional Research Execution Package — Sprint 10 soft-wire (final RQ1)
  router.get('/research-execution/health', kfGet('/v1/research-execution/health'));
  router.get('/research-execution/dashboard', kfGet('/v1/research-execution/dashboard'));
  router.get('/research-execution/constitution', kfGet('/v1/research-execution/constitution'));
  router.get('/research-execution/quality-gates', kfGet('/v1/research-execution/quality-gates'));
  router.post('/research-execution/build', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-execution/build', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IREP build failed', detail: error.message });
    }
  });
  router.post('/research-execution/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-execution/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IREP plan failed', detail: error.message });
    }
  });
  router.post('/research-execution/enrich', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-execution/enrich', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IREP enrich failed', detail: error.message });
    }
  });
  router.post('/research-execution/export', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-execution/export', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IREP export failed', detail: error.message });
    }
  });
  router.post('/research-execution/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-execution/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IREP diagnostics failed', detail: error.message });
    }
  });

  // RQ2 Institutional Hypothesis Generation Engine — Sprint 1 (AFTER IREP; BEFORE analysts)
  router.get('/hypothesis-engine/health', kfGet('/v1/hypothesis-engine/health'));
  router.get('/hypothesis-engine/dashboard', kfGet('/v1/hypothesis-engine/dashboard'));
  router.get('/hypothesis-engine/constitution', kfGet('/v1/hypothesis-engine/constitution'));
  router.get('/hypothesis-engine/quality-gates', kfGet('/v1/hypothesis-engine/quality-gates'));
  router.post('/hypothesis-engine/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/hypothesis-engine/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IHG plan failed', detail: error.message });
    }
  });
  router.post('/hypothesis-engine/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/hypothesis-engine/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IHG diagnostics failed', detail: error.message });
    }
  });

  // RQ2 Institutional Research Question Engine — Sprint 2 (AFTER IHG; BEFORE evidence)
  router.get('/research-questions/health', kfGet('/v1/research-questions/health'));
  router.get('/research-questions/dashboard', kfGet('/v1/research-questions/dashboard'));
  router.get('/research-questions/constitution', kfGet('/v1/research-questions/constitution'));
  router.get('/research-questions/quality-gates', kfGet('/v1/research-questions/quality-gates'));
  router.post('/research-questions/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-questions/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IRQ plan failed', detail: error.message });
    }
  });
  router.post('/research-questions/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/research-questions/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IRQ diagnostics failed', detail: error.message });
    }
  });

  // RQ2 Institutional Hypothesis Testing Engine — Sprint 4 (AFTER evidence planning; BEFORE analysts)
  router.get('/hypothesis-testing/health', kfGet('/v1/hypothesis-testing/health'));
  router.get('/hypothesis-testing/dashboard', kfGet('/v1/hypothesis-testing/dashboard'));
  router.get('/hypothesis-testing/constitution', kfGet('/v1/hypothesis-testing/constitution'));
  router.get('/hypothesis-testing/quality-gates', kfGet('/v1/hypothesis-testing/quality-gates'));
  router.post('/hypothesis-testing/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/hypothesis-testing/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IHTE plan failed', detail: error.message });
    }
  });
  router.post('/hypothesis-testing/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/hypothesis-testing/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IHTE diagnostics failed', detail: error.message });
    }
  });

  // RQ2 Bayesian Belief & Confidence Engine — Sprint 6 (AFTER falsification; BEFORE opinions)
  router.get('/belief-engine/health', kfGet('/v1/belief-engine/health'));
  router.get('/belief-engine/dashboard', kfGet('/v1/belief-engine/dashboard'));
  router.get('/belief-engine/constitution', kfGet('/v1/belief-engine/constitution'));
  router.get('/belief-engine/quality-gates', kfGet('/v1/belief-engine/quality-gates'));
  router.post('/belief-engine/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/belief-engine/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'BBCE plan failed', detail: error.message });
    }
  });
  router.post('/belief-engine/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/belief-engine/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'BBCE diagnostics failed', detail: error.message });
    }
  });

  // RQ2 Institutional Thesis Construction Engine — Sprint 7 (AFTER BBCE; BEFORE Committee)
  router.get('/thesis-engine/health', kfGet('/v1/thesis-engine/health'));
  router.get('/thesis-engine/dashboard', kfGet('/v1/thesis-engine/dashboard'));
  router.get('/thesis-engine/constitution', kfGet('/v1/thesis-engine/constitution'));
  router.get('/thesis-engine/quality-gates', kfGet('/v1/thesis-engine/quality-gates'));
  router.post('/thesis-engine/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/thesis-engine/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ITCE plan failed', detail: error.message });
    }
  });
  router.post('/thesis-engine/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/thesis-engine/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'ITCE diagnostics failed', detail: error.message });
    }
  });

  // RQ2 Institutional Debate Engine — Sprint 8 (structured debate BEFORE Committee)
  router.get('/debate-engine/health', kfGet('/v1/debate-engine/health'));
  router.get('/debate-engine/dashboard', kfGet('/v1/debate-engine/dashboard'));
  router.get('/debate-engine/constitution', kfGet('/v1/debate-engine/constitution'));
  router.get('/debate-engine/quality-gates', kfGet('/v1/debate-engine/quality-gates'));
  router.post('/debate-engine/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/debate-engine/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IDEB plan failed', detail: error.message });
    }
  });
  router.post('/debate-engine/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/debate-engine/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IDEB diagnostics failed', detail: error.message });
    }
  });

  // RQ2 Institutional Decision Readiness Engine — Sprint 9 (final pre-Committee gate)
  router.get('/decision-readiness/health', kfGet('/v1/decision-readiness/health'));
  router.get('/decision-readiness/dashboard', kfGet('/v1/decision-readiness/dashboard'));
  router.get('/decision-readiness/constitution', kfGet('/v1/decision-readiness/constitution'));
  router.get('/decision-readiness/quality-gates', kfGet('/v1/decision-readiness/quality-gates'));
  router.post('/decision-readiness/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/decision-readiness/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IDRE plan failed', detail: error.message });
    }
  });
  router.post('/decision-readiness/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/decision-readiness/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IDRE diagnostics failed', detail: error.message });
    }
  });

  // RQ2 Institutional Reasoning Audit Engine — Sprint 10 (final certification)
  router.get('/reasoning-audit/health', kfGet('/v1/reasoning-audit/health'));
  router.get('/reasoning-audit/dashboard', kfGet('/v1/reasoning-audit/dashboard'));
  router.get('/reasoning-audit/constitution', kfGet('/v1/reasoning-audit/constitution'));
  router.get('/reasoning-audit/quality-gates', kfGet('/v1/reasoning-audit/quality-gates'));
  router.post('/reasoning-audit/plan', async (req, res) => {
    try {
      const result = await engineFetch('/v1/reasoning-audit/plan', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IRAE plan failed', detail: error.message });
    }
  });
  router.post('/reasoning-audit/diagnostics', async (req, res) => {
    try {
      const result = await engineFetch('/v1/reasoning-audit/diagnostics', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IRAE diagnostics failed', detail: error.message });
    }
  });

  // IIEX — Institutional Intelligence Examination (CIO assessment)
  router.get('/iiex/health', kfGet('/v1/iiex/health'));
  router.get('/iiex/dashboard', kfGet('/v1/iiex/dashboard'));
  router.get('/iiex/questions', kfGet('/v1/iiex/questions'));
  router.get('/iiex/report', kfGet('/v1/iiex/report'));
  router.get('/iiex/grades', kfGet('/v1/iiex/grades'));
  router.get('/iiex/history', kfGet('/v1/iiex/history'));
  router.get('/institutional-intelligence-examination/health', kfGet('/v1/institutional-intelligence-examination/health'));
  router.get('/institutional-intelligence-examination/dashboard', kfGet('/v1/institutional-intelligence-examination/dashboard'));
  router.post('/iiex/run', async (req, res) => {
    try {
      const result = await engineFetch('/v1/iiex/run', {
        method: 'POST',
        body: req.body || {},
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'IIEX unavailable', detail: error.message });
    }
  });

  // MKFI — Market Forecast Intelligence
  router.get('/mkfi/health', kfGet('/v1/mkfi/health'));
  router.get('/mkfi/dashboard', kfGet('/v1/mkfi/dashboard'));
  router.get('/market/forecast', kfGet('/v1/market/forecast'));
  router.get('/market/forecast/dashboard', kfGet('/v1/market/forecast/dashboard'));

  // Live status for public/admin surfaces (soft — never hard-fails the site)
  router.get('/live-status', async (_req, res) => {
    const out = {
      ok: true,
      surface: 'live-status',
      generated_at: new Date().toISOString(),
      gateway: 'agi-node',
      engine: { ok: false },
      stack: null,
      iiex: null,
      mkfi: null,
      providers_queried: [],
    };
    try {
      const health = await engineFetch('/v1/health');
      out.engine = {
        ok: health.status < 400 && Boolean(health.data?.ok || health.data?.status === 'ok'),
        status: health.status,
        service: health.data?.service,
      };
    } catch (error) {
      out.engine = { ok: false, error: String(error.message || error).slice(0, 160) };
    }
    if (out.engine.ok) {
      try {
        const stack = await engineFetch('/v1/system/intelligence-stack');
        out.stack = stack.data;
      } catch {
        out.stack = null;
      }
      try {
        const iiex = await engineFetch('/v1/iiex/health');
        out.iiex = iiex.data;
      } catch {
        out.iiex = null;
      }
      try {
        const mkfi = await engineFetch('/v1/mkfi/health');
        out.mkfi = mkfi.data;
      } catch {
        out.mkfi = null;
      }
    }
    return res.status(200).json(out);
  });

  // ---------------------------------------------------------------------
  // AGI Institutional Data Warehouse (admin workspace)
  // ---------------------------------------------------------------------

  const warehouseActor = (req) =>
    String(
      req.get?.('X-AGI-Actor') ||
        req.body?.actor ||
        req.query?.actor ||
        'admin',
    ).slice(0, 200);

  const warehouseGet = (buildPath, timeoutMs = 120_000) => async (req, res) => {
    try {
      const qs = new URLSearchParams(req.query || {}).toString();
      const target = typeof buildPath === 'function' ? buildPath(req) : buildPath;
      const result = await engineFetch(`${target}${qs ? `?${qs}` : ''}`, {
        timeoutMs,
        headers: { 'X-AGI-Actor': warehouseActor(req) },
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Data warehouse unavailable', detail: error.message });
    }
  };

  const warehousePost = (buildPath, timeoutMs = 180_000) => async (req, res) => {
    try {
      const target = typeof buildPath === 'function' ? buildPath(req) : buildPath;
      const result = await engineFetch(target, {
        method: 'POST',
        body: req.body || {},
        timeoutMs,
        headers: { 'X-AGI-Actor': warehouseActor(req) },
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({ error: 'Data warehouse unavailable', detail: error.message });
    }
  };

  const encode = (value) => encodeURIComponent(String(value || ''));

  router.get('/warehouse/health', warehouseGet('/v1/warehouse/health'));
  router.post('/warehouse/repair/upstox-quarterly', warehousePost('/v1/warehouse/repair/upstox-quarterly', 300_000));
  router.get('/warehouse/workbook', warehouseGet('/v1/warehouse/workbook'));
  router.get('/warehouse/stats', warehouseGet('/v1/warehouse/stats'));
  router.get('/warehouse/whoami', warehouseGet('/v1/warehouse/whoami'));
  router.get('/warehouse/coverage', warehouseGet('/v1/warehouse/coverage'));
  // Phase 7.4F — Financial Warehouse Completion Programme
  router.get('/fwcp/health', warehouseGet('/v1/fwcp/health'));
  router.get('/warehouse/financial-coverage', warehouseGet('/v1/warehouse/financial-coverage'));
  // Phase 7.4F Step 0 — Financial Warehouse Coverage Audit (read-only)
  router.get('/warehouse/financial-audit', warehouseGet('/v1/warehouse/financial-audit', 180_000));
  router.get('/warehouse/coverage/summary', warehouseGet('/v1/warehouse/coverage/summary', 180_000));
  router.get('/warehouse/coverage/sector', warehouseGet('/v1/warehouse/coverage/sector', 180_000));
  router.get('/warehouse/missing-financials', warehouseGet('/v1/warehouse/missing-financials', 180_000));
  router.get('/warehouse/company/:symbol/coverage', warehouseGet((req) =>
    `/v1/warehouse/company/${encode(req.params.symbol)}/coverage`));
  router.get('/warehouse/missing-statements', warehouseGet('/v1/warehouse/missing-statements'));
  router.get('/warehouse/missing-share-count', warehouseGet('/v1/warehouse/missing-share-count'));
  router.get('/warehouse/import/status', warehouseGet('/v1/warehouse/import/status'));
  router.get('/warehouse/import/board', warehouseGet('/v1/warehouse/import/board'));
  router.get('/warehouse/import/capital-iq', warehouseGet('/v1/warehouse/import/capital-iq'));
  router.get('/warehouse/import/capital-iq-workbook', warehouseGet('/v1/warehouse/import/capital-iq-workbook', 300_000));
  router.get('/warehouse/import/vendor-exports', warehouseGet('/v1/warehouse/import/vendor-exports', 180_000));
  router.post('/warehouse/import/vendor-exports', warehousePost('/v1/warehouse/import/vendor-exports', 300_000));
  router.post('/warehouse/import/start', warehousePost('/v1/warehouse/import/start'));
  router.post('/warehouse/import/stop', warehousePost('/v1/warehouse/import/stop'));
  router.post('/warehouse/import/resume', warehousePost('/v1/warehouse/import/resume'));
  router.post('/warehouse/import/retry', warehousePost('/v1/warehouse/import/retry', 300_000));
  router.post('/warehouse/import/run', warehousePost('/v1/warehouse/import/run', 300_000));
  router.post('/warehouse/import/capital-iq', warehousePost('/v1/warehouse/import/capital-iq', 300_000));
  router.post('/warehouse/import/capital-iq-workbook', warehousePost('/v1/warehouse/import/capital-iq-workbook', 600_000));
  router.post('/warehouse/share-count/:symbol/sync', warehousePost((req) =>
    `/v1/warehouse/share-count/${encode(req.params.symbol)}/sync`));
  // Phase 7.4F — Yahoo-first financial fill (fast EMPTY / thin path)
  router.get('/warehouse/yahoo-fill/status', warehouseGet('/v1/warehouse/yahoo-fill/status', 180_000));
  router.get('/warehouse/yahoo-fill/board', warehouseGet('/v1/warehouse/yahoo-fill/board', 180_000));
  router.get('/warehouse/yahoo-fill/queue', warehouseGet('/v1/warehouse/yahoo-fill/queue', 180_000));
  router.get('/warehouse/yahoo-fill/probe', warehouseGet('/v1/warehouse/yahoo-fill/probe', 120_000));
  router.get('/warehouse/upstox-fill/queue', warehouseGet('/v1/warehouse/upstox-fill/queue', 180_000));
  router.get('/warehouse/upstox-fill/board', warehouseGet('/v1/warehouse/upstox-fill/board', 180_000));
  router.post('/warehouse/yahoo-fill/start', warehousePost('/v1/warehouse/yahoo-fill/start'));
  router.post('/warehouse/yahoo-fill/stop', warehousePost('/v1/warehouse/yahoo-fill/stop'));
  router.post('/warehouse/yahoo-fill/resume', warehousePost('/v1/warehouse/yahoo-fill/resume'));
  router.post('/warehouse/yahoo-fill/run', warehousePost('/v1/warehouse/yahoo-fill/run', 600_000));
  router.post('/warehouse/yahoo-fill/:symbol', warehousePost((req) =>
    `/v1/warehouse/yahoo-fill/${encode(req.params.symbol)}`, 120_000));
  router.get('/warehouse/audit', warehouseGet('/v1/warehouse/audit'));
  router.get('/warehouse/validate', warehouseGet('/v1/warehouse/validate'));
  router.get('/warehouse/imports', warehouseGet('/v1/warehouse/imports'));
  router.get('/warehouse/refresh-runs', warehouseGet('/v1/warehouse/refresh-runs'));
  router.get('/warehouse/scheduler', warehouseGet('/v1/warehouse/scheduler'));
  router.get('/warehouse/search', warehouseGet('/v1/warehouse/search'));
  router.get('/warehouse/suggest', warehouseGet('/v1/warehouse/suggest'));
  router.get('/warehouse/company/:symbol', warehouseGet((req) =>
    `/v1/warehouse/company/${encode(req.params.symbol)}`));

  router.get('/warehouse/tab/:tabId/schema', warehouseGet((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/schema`));
  router.get('/warehouse/tab/:tabId/export', warehouseGet((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/export`));
  router.get('/warehouse/tab/:tabId/row/:rowId/history', warehouseGet((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/row/${encode(req.params.rowId)}/history`));
  router.get('/warehouse/tab/:tabId/row/:rowId/compare', warehouseGet((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/row/${encode(req.params.rowId)}/compare`));
  router.get('/warehouse/tab/:tabId/row/:rowId', warehouseGet((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/row/${encode(req.params.rowId)}`));
  router.get('/warehouse/tab/:tabId', warehouseGet((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}`));

  router.post('/warehouse/tab/:tabId/edit', warehousePost((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/edit`));
  router.post('/warehouse/tab/:tabId/row', warehousePost((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/row`));
  router.post('/warehouse/tab/:tabId/clear-override', warehousePost((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/clear-override`));
  router.post('/warehouse/tab/:tabId/delete', warehousePost((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/delete`));
  router.post('/warehouse/tab/:tabId/publish', warehousePost((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/publish`));
  router.post('/warehouse/tab/:tabId/import', warehousePost((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/import`, 300_000));
  router.post('/warehouse/tab/:tabId/map-headers', warehousePost((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/map-headers`, 30_000));
  router.post('/warehouse/tab/:tabId/row/:rowId/restore', warehousePost((req) =>
    `/v1/warehouse/tab/${encode(req.params.tabId)}/row/${encode(req.params.rowId)}/restore`));
  router.post('/warehouse/import/:importId/commit', warehousePost((req) =>
    `/v1/warehouse/import/${encode(req.params.importId)}/commit`, 300_000));
  router.post('/warehouse/refresh', warehousePost('/v1/warehouse/refresh', 900_000));
  router.post('/warehouse/recalculate', warehousePost('/v1/warehouse/recalculate', 600_000));

  // Phase 7.1a — historical backfill and time-series reads
  router.post('/warehouse/backfill', warehousePost('/v1/warehouse/backfill', 900_000));
  router.get('/warehouse/backfill/status', warehouseGet('/v1/warehouse/backfill/status'));
  router.get('/warehouse/backfill/jobs', warehouseGet('/v1/warehouse/backfill/jobs'));
  router.get('/warehouse/historical-coverage', warehouseGet('/v1/warehouse/historical-coverage'));

  // Phase 7.3 — data quality integration
  router.get('/warehouse/quality', warehouseGet('/v1/warehouse/quality'));
  router.get('/warehouse/quarantine', warehouseGet('/v1/warehouse/quarantine'));
  router.get('/warehouse/conflicts', warehouseGet('/v1/warehouse/conflicts'));
  router.get('/warehouse/conflicts/summary', warehouseGet('/v1/warehouse/conflicts/summary'));
  router.post('/warehouse/remediate-zeros', warehousePost('/v1/warehouse/remediate-zeros', 300_000));

  router.get('/history/compare', warehouseGet('/v1/history/compare'));
  router.get('/history/company/:symbol', warehouseGet((req) =>
    `/v1/history/company/${encode(req.params.symbol)}`));
  router.get('/history/series/:symbol/:metric', warehouseGet((req) =>
    `/v1/history/series/${encode(req.params.symbol)}/${encode(req.params.metric)}`));
  router.get('/history/as-at/:symbol', warehouseGet((req) =>
    `/v1/history/as-at/${encode(req.params.symbol)}`));
  router.get('/history/table/:tabId', warehouseGet((req) =>
    `/v1/history/table/${encode(req.params.tabId)}`));
  router.get('/history/coverage/:symbol', warehouseGet((req) =>
    `/v1/history/coverage/${encode(req.params.symbol)}`));

  // Phase 7.2 — Historical Intelligence Engine
  router.get('/historical-intelligence/health', warehouseGet('/v1/historical-intelligence/health'));
  router.get('/historical-intelligence/detect', warehouseGet('/v1/historical-intelligence/detect'));
  router.get('/historical-intelligence/compare', warehouseGet('/v1/historical-intelligence/compare'));
  router.post('/historical-intelligence/ask', warehousePost('/v1/historical-intelligence/ask', 180_000));
  router.get('/historical-intelligence/coverage/:symbol', warehouseGet((req) =>
    `/v1/historical-intelligence/coverage/${encode(req.params.symbol)}`));
  router.get('/historical-intelligence/company/:symbol', warehouseGet((req) =>
    `/v1/historical-intelligence/company/${encode(req.params.symbol)}`));
  router.get('/historical-intelligence/trend/:symbol/:metric', warehouseGet((req) =>
    `/v1/historical-intelligence/trend/${encode(req.params.symbol)}/${encode(req.params.metric)}`));
  router.get('/historical-intelligence/valuation/:symbol', warehouseGet((req) =>
    `/v1/historical-intelligence/valuation/${encode(req.params.symbol)}`));
  router.get('/historical-intelligence/bands/:symbol', warehouseGet((req) =>
    `/v1/historical-intelligence/bands/${encode(req.params.symbol)}`));
  router.get('/historical-intelligence/timeline/:symbol', warehouseGet((req) =>
    `/v1/historical-intelligence/timeline/${encode(req.params.symbol)}`));
  router.get('/historical-intelligence/sector/:symbol', warehouseGet((req) =>
    `/v1/historical-intelligence/sector/${encode(req.params.symbol)}`));

  return router;
}
