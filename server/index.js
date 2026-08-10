// server/index.js
// IndianAPI proxy + research router
// - mounts ./research.js at /research
// - provides /api/* proxy endpoints to IndianAPI
// - robust headers / JSON parsing / error handling
// - small caching for /api/trending

import express from "express";
import researchRouter from "./research.js";
import createMarketRouter from "./routes/market.js";
import createNifty500ResearchRouter from "./routes/nifty500Research.js";
import createIntelligenceRouter from "./routes/intelligence.js";
import createUiRouter from "./routes/ui.js";
import createPeIntelligenceRouter from "./routes/peIntelligence.js";
import createIntelligenceCmsRouter from "./routes/intelligenceCms.js";
import createIntelligencePlatformRouter from "./routes/intelligencePlatform.js";
import createAuthRouter from "./routes/auth.js";
import createNewsletterRouter from "./routes/newsletter.js";
import createResearchSignalsRouter from "./routes/researchSignals.js";
import { getNewsHeadlines } from "./services/newsHeadlinesService.js";
import { getIpoDetail, getIpoPlatform, getIpoSummary } from "./services/ipoService.js";
import { getMarketContext } from "./services/marketContextService.js";
import { startCioMorningScheduler } from "./services/cioMorningScheduler.js";
import { startContinuousGatherLearnScheduler } from "./services/continuousGatherLearnScheduler.js";
import { startInstitutionalFlowScheduler } from "./services/institutionalFlowScheduler.js";
import { startValuationRatiosScheduler } from "./services/valuationRatiosScheduler.js";
import { startHvieRuntimeScheduler } from "./services/hvieRuntimeScheduler.js";
import { startUifiScheduler } from "./services/uifiScheduler.js";
import { startHedgeFundLiveQuoteScheduler } from "./services/hedgeFundLiveQuoteScheduler.js";
import { startHedgeFundUpstoxCandleScheduler } from "./services/hedgeFundUpstoxCandleScheduler.js";
import { startHflTerminalSnapshotScheduler } from "./services/hflTerminalSnapshotScheduler.js";
import { startValuationCompanyPackScheduler } from "./services/valuationCompanyPackScheduler.js";
import { startGrowwEquityOpportunityScheduler } from "./services/growwEquityOpportunityScheduler.js";
import { startUpstoxStatementScheduler } from "./services/upstoxStatementScheduler.js";
import { getLiveAlphaRuntimeStatus, startLiveAlphaRuntime } from "./services/liveAlphaRuntime.js";
import { getLiveAlphaWorkspace } from "./services/liveAlphaWorkspace.js";
import { buildConfluenceQueue } from "./services/researchConfluence.js";
import { getResearchEvidence } from "./services/researchEvidenceCollector.js";
import { getConfluenceLedger, getConfluenceValidationSummary } from "./services/confluenceValidationStore.js";
import { getConfluenceValidationStatus, startConfluenceValidationScheduler } from "./services/confluenceValidationScheduler.js";
import { getCompanyResearchMemory, screenResearchChanges } from "./services/researchMemoryStore.js";
import { getCompanyForecasts, getForecastValidation } from "./services/probabilisticForecastStore.js";
import { getForecastRanking, getRankIcHealth, getWalkForwardDataset } from "./services/forecastV2Store.js";
import { getResearchPipelineHealth } from "./services/researchPipelineHealth.js";
import { startTradingCalendarService, tradingCalendar } from "./services/tradingCalendarService.js";
import { llmProviderStatus } from "./services/llmClient.js";
import rateLimit from "express-rate-limit";
import cors from "cors";
import dotenv from "dotenv";
import path from "node:path";
import { fileURLToPath } from "node:url";

const serverDirectory = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(serverDirectory, ".env") });

const app = express();
app.use(express.json({
  limit: "2mb",
  verify: (req, _res, buffer) => {
    req.rawBody = Buffer.from(buffer);
  },
}));
app.set("trust proxy", 1);

const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
const BASE_URL = process.env.INDIANAPI_BASE || "https://stock.indianapi.in";

const API_KEY = (process.env.INDIANAPI_KEY || process.env.VITE_INDIANAPI_KEY || "").toString().trim();
const PERPLEXITY_KEY = (process.env.PERPLEXITY_KEY || process.env.PERPLEXITY_API_KEY || process.env.VITE_PERPLEXITY_KEY || "").toString().trim();
const PERPLEXITY_URL = process.env.PERPLEXITY_URL || "https://api.perplexity.ai/chat/completions";
const PERPLEXITY_MODEL_ENV = (process.env.PERPLEXITY_MODEL || "").trim();
const DEBUG_API = (process.env.DEBUG_API || "").toLowerCase() === "true";

if (!API_KEY) console.warn("⚠️ Missing INDIANAPI_KEY — some endpoints may return limited data.");
if (!PERPLEXITY_KEY) console.warn("⚠️ Missing PERPLEXITY_KEY — Perplexity-backed endpoints disabled.");

// CORS: prefer explicit FRONTEND_ORIGIN entries; don't use '*' when credentials true.
// Always allow both apex + www production hosts — throwing here becomes a 500 in browsers.
const DEFAULT_FRONTEND_ORIGINS = [
  "https://agarwalglobalinvestments.com",
  "https://www.agarwalglobalinvestments.com",
];
const rawAllowed = (process.env.FRONTEND_ORIGIN || "").split(",").map(s => s.trim()).filter(Boolean);
const allowedOrigins = Array.from(new Set([...DEFAULT_FRONTEND_ORIGINS, ...rawAllowed]));

app.use(cors({
  origin: (origin, cb) => {
    if (!origin) return cb(null, true); // server-to-server or curl
    if (allowedOrigins.includes(origin)) return cb(null, true);
    // Deny quietly — never cb(Error) (that surfaces as Internal Server Error).
    return cb(null, false);
  },
  methods: ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
  optionsSuccessStatus: 200,
  credentials: true,
}));

// Rate limiting — AGI market intelligence has its own limiter (cached, low churn)
const apiLimiter = rateLimit({
  windowMs: 60_000,
  max: 120,
  standardHeaders: true,
  legacyHeaders: false,
  skip: (req) => {
    const p = (req.path || req.url || '').split('?')[0];
    return /\/market\/(intelligence|dashboard|pulse|ticker)\/?$/.test(p);
  },
});
const marketIntelLimiter = rateLimit({
  windowMs: 60_000,
  max: 300,
  standardHeaders: true,
  legacyHeaders: false,
});
const nifty500ResearchLimiter = rateLimit({
  windowMs: 60_000,
  max: 120,
  standardHeaders: true,
  legacyHeaders: false,
});
const researchLimiter = rateLimit({ windowMs: 60_000, max: 30, standardHeaders: true, legacyHeaders: false });
app.use('/api', apiLimiter);
app.use('/research', researchLimiter);

// dynamic fetch implementation
let _fetchImpl = undefined;
async function ensureFetch() {
  if (typeof _fetchImpl === 'function') return _fetchImpl;
  if (typeof globalThis.fetch === 'function') {
    _fetchImpl = globalThis.fetch.bind(globalThis);
    return _fetchImpl;
  }
  try {
    const mod = await import('node-fetch');
    _fetchImpl = mod.default;
    return _fetchImpl;
  } catch (e) {
    console.error('Failed to load node-fetch dynamically:', e?.message || e);
    throw e;
  }
}

// fetch with timeout and timeout flag
async function fetchWithTimeout(url, opts = {}, timeoutMs = 15_000) {
  const fetchFn = await ensureFetch();
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const merged = { ...opts, signal: controller.signal };
    const resp = await fetchFn(url, merged);
    clearTimeout(id);
    return resp;
  } catch (err) {
    clearTimeout(id);
    if (err && (err.name === 'AbortError' || /aborted/i.test(String(err.message || '')))) {
      const e = new Error('Upstream request timed out');
      e.isTimeout = true;
      throw e;
    }
    throw err;
  }
}

function makeHeaders() {
  const h = { Accept: 'application/json', 'Content-Type': 'application/json', 'User-Agent': 'AGIB-Proxy/1.0' };
  if (API_KEY) h['x-api-key'] = API_KEY;
  return h;
}

// In-memory cache for IndianAPI proxies. Fresh TTL is short; stale entries are
// kept longer so homepage desks can survive upstream 429 / outages.
const PROXY_CACHE_TTL_MS = 60_000;
const PROXY_CACHE_STALE_MS = 30 * 60_000;
const proxyCache = new Map();

function proxyCacheKey(url) {
  return String(url || '');
}

function readProxyCache(url, { allowStale = false } = {}) {
  const hit = proxyCache.get(proxyCacheKey(url));
  if (!hit) return null;
  const age = Date.now() - hit.at;
  if (age <= PROXY_CACHE_TTL_MS) return { ...hit, stale: false };
  if (allowStale && age <= PROXY_CACHE_STALE_MS) return { ...hit, stale: true };
  return null;
}

function writeProxyCache(url, json) {
  if (!json || typeof json !== 'object') return;
  proxyCache.set(proxyCacheKey(url), { json, at: Date.now() });
}

function sendCachedProxy(res, cached, { reason } = {}) {
  res.set('Cache-Control', 'public, max-age=30, stale-while-revalidate=300');
  if (cached.stale || reason) {
    res.set('X-AGI-Upstream-Cache', reason || 'stale');
  }
  return res.status(200).json(cached.json);
}

function isUpstreamRateLimited(status, text = '') {
  if (status === 429) return true;
  return /rate limit exceeded/i.test(String(text || ''));
}

async function proxyFetch(res, url, opts = {}) {
  const fresh = readProxyCache(url, { allowStale: false });
  if (fresh) {
    console.log(`[proxy] cache hit ${url}`);
    return sendCachedProxy(res, fresh);
  }

  try {
    console.log(`[proxy] -> ${url}`);
    const r = await fetchWithTimeout(url, { method: opts.method || 'GET', headers: opts.headers || makeHeaders(), body: opts.body }, opts.timeout || 15_000);
    const ct = (r.headers.get('content-type') || '').toLowerCase();
    const text = await r.text().catch(() => '');

    console.log(`[proxy] ${url} returned ${r.status} content-type:${ct} length:${String(text?.length || 0)}`);

    if (!text) {
      const stale = readProxyCache(url, { allowStale: true });
      if (stale) return sendCachedProxy(res, stale, { reason: 'empty-upstream' });
      return res.status(r.status).end();
    }

    if ([401, 402, 403].includes(r.status)) {
      console.error(`[proxy][upstream ${r.status}] ${text.slice(0, 200)}`);
      res.set('Content-Type', ct || 'text/plain');
      return res.status(r.status).send(text);
    }

    if (isUpstreamRateLimited(r.status, text)) {
      const stale = readProxyCache(url, { allowStale: true });
      if (stale) {
        console.warn(`[proxy] upstream 429 — serving stale cache for ${url}`);
        return sendCachedProxy(res, stale, { reason: 'rate-limited' });
      }
      // Soft-fail for market desks: empty payload beats a hard 429 that blanks the homepage.
      console.warn(`[proxy] upstream 429 — no cache for ${url}`);
      return res.status(200).json({
        error: 'upstream_rate_limited',
        upstream_status: 429,
        items: [],
        data: [],
        stale: true,
      });
    }

    if (ct.includes('application/json') || ct.includes('+json')) {
      try {
        const json = JSON.parse(text);
        if (json && (json.error || json.upstream_error)) {
          console.error('[proxy][upstream error]', json.error || json.upstream_error);
          const stale = readProxyCache(url, { allowStale: true });
          if (stale) return sendCachedProxy(res, stale, { reason: 'upstream-error' });
          return res.status(502).json({ upstream_error: json.error || json.upstream_error, upstream_body: json });
        }
        writeProxyCache(url, json);
        return res.status(r.status).json(json);
      } catch (parseErr) {
        console.error('[proxy] failed to parse JSON from upstream', parseErr?.message || parseErr);
        const stale = readProxyCache(url, { allowStale: true });
        if (stale) return sendCachedProxy(res, stale, { reason: 'parse-error' });
        res.set('Content-Type', ct || 'application/json');
        return res.status(502).send(text);
      }
    }

    // Plain-text rate-limit bodies are handled above; other non-JSON still may have stale JSON.
    if (r.status >= 500) {
      const stale = readProxyCache(url, { allowStale: true });
      if (stale) return sendCachedProxy(res, stale, { reason: `upstream-${r.status}` });
    }

    res.set('Content-Type', ct || 'text/plain');
    return res.status(r.status).send(text);
  } catch (err) {
    console.error('🔥 proxyFetch failed:', err?.message || err);
    const stale = readProxyCache(url, { allowStale: true });
    if (stale) return sendCachedProxy(res, stale, { reason: err?.isTimeout ? 'timeout' : 'fetch-failed' });
    if (err?.isTimeout) return res.status(504).json({ error: 'Upstream request timed out' });
    return res.status(500).json({ error: 'Proxy fetch failed', detail: err?.message || String(err) });
  }
}

// small in-memory trending cache (fresh 60s, stale up to 30m)
let trendingCache = null;
let trendingExpiry = 0;
let trendingStaleExpiry = 0;

function reg(path, handler) {
  app.get(path, handler);
  console.log('[route registered]', path);
}

// --- Health + debug endpoints
reg('/', (req, res) => res.json({ service: 'finance-news-backend', status: 'running' }));
reg('/api/health', (req, res) => res.json({
  ok: true,
  architecture: 'v1.0.1 LOCKED',
  ui_aggregation: true,
  intelligence_gateway: true,
  llm: llmProviderStatus(),
  commit: process.env.RENDER_GIT_COMMIT || process.env.GIT_COMMIT || null,
}));
reg('/api/market/live-alpha/status', (_req, res) => res.json(getLiveAlphaRuntimeStatus()));
reg('/api/market/trading-calendar/status', (_req, res) => res.json(tradingCalendar.health()));
reg('/api/market/live-alpha/workspace', async (_req, res) => {
  try { res.json(await getLiveAlphaWorkspace()); }
  catch (error) { res.status(503).json({ error: error.message, research_only: true, execution_enabled: false }); }
});
reg('/api/market/research-confluence', async (req, res) => {
  try {
    const workspace = await getLiveAlphaWorkspace();
    const limit = Number(req.query.limit) || 25;
    const research = await getResearchEvidence({ workspace, limit });
    res.json({ ...buildConfluenceQueue({ workspace, research: research.evidence, limit }), evidence_health: research.health });
  } catch (error) {
    res.status(503).json({ error: error.message || 'Research confluence unavailable', research_only: true });
  }
});
reg('/api/market/research-confluence/validation', async (_req, res) => {
  try { res.json({ generated_at: new Date().toISOString(), classifications: await getConfluenceValidationSummary(), status: getConfluenceValidationStatus() }); }
  catch (error) { res.status(error.status === 404 ? 503 : 500).json({ error: error.message, status: getConfluenceValidationStatus() }); }
});
reg('/api/market/research-confluence/ledger', async (req, res) => {
  try { res.json({ generated_at: new Date().toISOString(), research_only: true, rows: await getConfluenceLedger({ limit: Number(req.query.limit) || 100, symbol: req.query.symbol }) }); }
  catch (error) { res.status(error.status === 404 ? 503 : 500).json({ error: error.message, research_only: true }); }
});
reg('/api/market/research-memory/changes', async (req, res) => {
  try { res.json({ generated_at: new Date().toISOString(), research_only: true, rows: await screenResearchChanges({ type: req.query.type, days: Number(req.query.days) || 30, limit: Number(req.query.limit) || 100 }) }); }
  catch (error) { res.status(error.status === 404 ? 503 : 500).json({ error: error.message, research_only: true }); }
});
reg('/api/market/research-memory/:symbol', async (req, res) => {
  try { res.json(await getCompanyResearchMemory(req.params.symbol, { limit: Number(req.query.limit) || 50 })); }
  catch (error) { res.status(error.status === 404 ? 503 : 500).json({ error: error.message, research_only: true }); }
});
reg('/api/market/forecasts/validation', async (req, res) => {
  try { res.json({ generated_at: new Date().toISOString(), research_only: true, ...(await getForecastValidation({ horizon: req.query.horizon, limit: Number(req.query.limit) || 5000 })) }); }
  catch (error) { res.status(error.status === 404 ? 503 : 500).json({ error: error.message, research_only: true }); }
});
reg('/api/market/forecasts/rankings', async (req, res) => {
  try { res.json({ generated_at: new Date().toISOString(), research_only: true, rows: await getForecastRanking({ date: req.query.date, horizon: req.query.horizon || '5d', limit: Number(req.query.limit) || 500 }) }); }
  catch (error) { res.status(error.status === 404 ? 503 : 500).json({ error: error.message, research_only: true }); }
});
reg('/api/market/forecasts/rank-ic', async (req, res) => {
  try { res.json({ generated_at: new Date().toISOString(), research_only: true, ...(await getRankIcHealth({ horizon: req.query.horizon || '5d', limit: Number(req.query.limit) || 252 })) }); }
  catch (error) { res.status(error.status === 404 ? 503 : 500).json({ error: error.message, research_only: true }); }
});
reg('/api/market/forecasts/training-dataset', async (req, res) => {
  try { res.json(await getWalkForwardDataset({ horizon: req.query.horizon || '5d', minimumTrainPeriods: Number(req.query.minimum_train_periods) || 20, limit: Number(req.query.limit) || 10000 })); }
  catch (error) { res.status(error.status === 404 ? 503 : 500).json({ error: error.message, research_only: true }); }
});
reg('/api/market/forecasts/:symbol', async (req, res) => {
  try { res.json(await getCompanyForecasts(req.params.symbol, { limit: Number(req.query.limit) || 30 })); }
  catch (error) { res.status(error.status === 404 ? 503 : 500).json({ error: error.message, research_only: true }); }
});
reg('/api/market/research-pipeline/health', async (_req, res) => {
  try { res.json(await getResearchPipelineHealth({ schedulerStatus: getConfluenceValidationStatus() })); }
  catch (error) { res.status(error.status === 404 ? 503 : 500).json({ error: error.message, status: 'DEGRADED', research_only: true }); }
});
reg('/api/news/headlines', async (_req, res) => {
  const data = await getNewsHeadlines();
  res.set('Cache-Control', 'public, max-age=1800, stale-while-revalidate=300');
  return res.json(data);
});
reg('/_debug_env', (req, res) => res.json({ API_KEY_exists: !!API_KEY, PERPLEXITY_key_present: !!PERPLEXITY_KEY, FRONTEND_ORIGIN: process.env.FRONTEND_ORIGIN || null, PORT: process.env.PORT || null }));
reg('/_debug_key', (req, res) => { if (!API_KEY) return res.json({ key_present: false }); return res.json({ key_present: true, masked: `${API_KEY.slice(0,6)}... (length ${API_KEY.length})` }); });

// mount research router
app.use('/research', researchRouter);

const marketRouter = createMarketRouter({
  indianApiKey: API_KEY,
  indianApiBase: BASE_URL,
});
app.use('/api/market', marketIntelLimiter, marketRouter);
// Phase 7.4E — plan paths are /api/upstox/* (alias onto market UIFI routes)
app.use('/api/upstox', marketIntelLimiter, (req, res, next) => {
  req.url = `/upstox${req.url === '/' ? '' : req.url}`;
  return marketRouter.handle(req, res, next);
});
const nifty500ResearchRouter = createNifty500ResearchRouter();
app.use('/api/research/nifty500', nifty500ResearchLimiter, nifty500ResearchRouter);
// Alias — some clients/probes hit /nifty50 without the trailing 0.
app.use('/api/research/nifty50', nifty500ResearchLimiter, nifty500ResearchRouter);
app.use('/api/research-signals', createResearchSignalsRouter());
app.use('/api/intelligence', createIntelligenceRouter());
app.use('/api/ui', createUiRouter());
app.use('/api/pe', createPeIntelligenceRouter());
app.use('/api/intelligence/cms', createIntelligenceCmsRouter());
app.use('/api/intelligence/platform', createIntelligencePlatformRouter());
app.use('/api/auth', createAuthRouter());
const newsletterRouter = createNewsletterRouter();
app.use('/api/newsletter', newsletterRouter);
// Legacy alias used by older CMS publish helpers
app.post('/api/notify-subscribers', (req, res, next) => {
  req.url = '/notify-subscribers';
  return newsletterRouter.handle(req, res, next);
});
startTradingCalendarService();
startCioMorningScheduler();
startContinuousGatherLearnScheduler();
startInstitutionalFlowScheduler();
startValuationRatiosScheduler();
startHvieRuntimeScheduler();
startUifiScheduler();
startHflTerminalSnapshotScheduler();
startValuationCompanyPackScheduler();
startGrowwEquityOpportunityScheduler();
startHedgeFundLiveQuoteScheduler();
startHedgeFundUpstoxCandleScheduler();
startUpstoxStatementScheduler();
startLiveAlphaRuntime().catch((error) => console.error('[live-alpha] startup failed:', error?.message || error));
startConfluenceValidationScheduler();

/* ---------- /api/perplexity/deals ----------
   Ask Perplexity for a strict JSON array of deals with these fields:
   - acquirer, target, value (string), value_number (number, optional), sector, type, date (ISO), source (URL), image (URL), summary (string)
   The endpoint WILL try multiple models (env override -> defaults) and parse choices[0].message.content robustly.
*/
reg('/api/perplexity/deals', async (req, res) => {
  try {
    const region = req.query.region || 'global';
    const limit = Math.min(50, Number(req.query.limit || 8));

    if (!PERPLEXITY_KEY) {
      console.warn('[perplexity] PERPLEXITY_KEY missing — returning empty array');
      return res.json([]);
    }

    // Strong prompt to force structured JSON output
    const structuredPrompt = `
Return a JSON array (max ${limit}) of recent M&A / PE deals for region: ${region}.
Each array item MUST be an object with the following keys:
- acquirer (string)
- target (string)
- value (string|null) e.g. "1.5 billion USD" or null
- value_number (number|null) USD amount if determinable (e.g. 1500000000)
- sector (string|null)
- type (string) one of "M&A", "PE", "Debt", "JV", etc.
- date (string|null) ISO 8601 date if available
- source (string|null) direct URL to the news/article
- image (string|null) an image URL or og:image if available
- summary (string|null) 1-2 sentence investor-facing summary

Return ONLY valid JSON (a single top-level JSON array). Do not include any explanation text or markdown.
`.trim();

    // models to try (env override first)
    const candidateModels = PERPLEXITY_MODEL_ENV ? [PERPLEXITY_MODEL_ENV, 'sonar', 'sonar-pro'] : ['sonar', 'sonar-pro'];

    let pRes = null, pText = "", usedModel = null;

    for (const mdl of candidateModels) {
      const body = {
        model: mdl,
        messages: [
          { role: 'system', content: 'You are a factual research assistant. Respond only with JSON when asked.' },
          { role: 'user', content: structuredPrompt },
        ],
        temperature: 0.1,
        max_tokens: 1200,
      };

      try {
        console.log(`[perplexity] trying model=${mdl}`);
        pRes = await fetchWithTimeout(PERPLEXITY_URL, {
          method: 'POST',
          headers: { Authorization: `Bearer ${PERPLEXITY_KEY}`, 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }, 30_000);

        pText = await pRes.text().catch(() => "");

        if (pRes.ok) { usedModel = mdl; break; }

        // if model invalid, try next
        if (pRes.status === 400 && /invalid_model/i.test(pText)) {
          console.warn(`[perplexity] model "${mdl}" invalid — trying next candidate`);
          pRes = null; pText = "";
          continue;
        }

        // other error: break and fallback
        console.error(`[perplexity] model ${mdl} returned ${pRes.status}:`, String(pText).slice(0,300));
        break;
      } catch (err) {
        console.error(`[perplexity] request failed for model=${mdl}:`, err?.message || err);
        pRes = null; pText = "";
        continue;
      }
    }

    if (!pRes || !pRes.ok) {
      console.error('[perplexity] no successful model response; returning empty array');
      return res.json([]);
    }

    const rawText = pText;
    if (DEBUG_API) console.warn(`[perplexity] RAW RESPONSE (model=${usedModel}) (truncated):`, String(rawText).slice(0, 2000));

    // parsing: prefer choices[0].message.content, then fallbacks
    let parsed = null;
    try {
      const respObj = JSON.parse(rawText);
      const reply = respObj?.choices?.[0]?.message?.content ?? respObj?.choices?.[0]?.text ?? null;

      if (typeof reply === 'string' && reply.trim()) {
        try {
          parsed = JSON.parse(reply);
        } catch (innerErr) {
          // try to extract array substring inside reply
          const arrMatch = String(reply).match(/\[\s*(?:\{[\s\S]*?\}\s*,?\s*)+\s*\]/m);
          if (arrMatch) {
            try { parsed = JSON.parse(arrMatch[0]); } catch (ee) { parsed = null; }
          }
        }
      }

      // final fallback: try array substring from the full rawText
      if (!Array.isArray(parsed)) {
        const anyArr = String(rawText).match(/\[\s*(?:\{[\s\S]*?\}\s*,?\s*)+\s*\]/m);
        if (anyArr) {
          try { parsed = JSON.parse(anyArr[0]); } catch (ee) { parsed = null; }
        }
      }
    } catch (e) {
      const fallback = String(rawText).match(/\[\s*(?:\{[\s\S]*?\}\s*,?\s*)+\s*\]/m);
      if (fallback) {
        try { parsed = JSON.parse(fallback[0]); } catch (ee) { parsed = null; }
      } else parsed = null;
    }

    if (!Array.isArray(parsed)) {
      if (DEBUG_API) console.warn('[perplexity] unexpected shape from API, returning empty array; raw (truncated):', String(rawText).slice(0,2000));
      return res.json([]);
    }

    // Normalize items: keep required fields consistent
    const normalized = parsed.slice(0, limit).map(it => ({
      acquirer: it?.acquirer ?? it?.buyer ?? null,
      target: it?.target ?? it?.company ?? null,
      value: it?.value ?? null,
      value_number: typeof it?.value_number === 'number' ? it.value_number : (it?.value_number ? Number(it.value_number) : null),
      sector: it?.sector ?? null,
      region: it?.region ?? region,
      date: it?.date ?? null,
      source: it?.source ?? null,
      image: it?.image ?? null,
      summary: it?.summary ?? null,
      type: it?.type ?? 'M&A'
    }));

    return res.json(normalized);
  } catch (err) {
    console.error('Perplexity proxy failed:', err);
    if (err?.isTimeout) return res.status(504).json({ error: 'Perplexity request timed out' });
    return res.json([]);
  }
});

/* --- /api/quote (tries multiple upstream endpoints) --- */
reg('/api/quote', async (req, res) => {
  try {
    const symbol = req.query.symbol || req.query.name;
    if (!symbol) return res.status(400).json({ error: 'Missing ?symbol or ?name' });

    const candidates = [
      `${BASE_URL}/stock?name=${encodeURIComponent(symbol)}`,
      `${BASE_URL}/stock?symbol=${encodeURIComponent(symbol)}`,
      `${BASE_URL}/quote?symbol=${encodeURIComponent(symbol)}`
    ];

    let lastErr = null;
    for (const url of candidates) {
      try {
        const r = await fetchWithTimeout(url, { method: 'GET', headers: makeHeaders() }, 15_000);
        const ct = (r.headers.get('content-type') || '').toLowerCase();
        const text = await r.text().catch(() => '');
        if (!text) { lastErr = new Error(`empty upstream response ${r.status} from ${url}`); continue; }
        if (!r.ok) { lastErr = new Error(`${r.status} : ${text}`); if (r.status >= 500) { res.set('Content-Type', ct || 'text/plain'); return res.status(r.status).send(text); } continue; }
        if (ct.includes('json') || ct.includes('+json')) {
          try {
            const json = JSON.parse(text);
            const cp = json.currentPrice ?? json.current_price ?? json.price ?? json.last_price ?? json.lastTradedPrice ?? null;
            const percent = json.percentChange ?? json.changePercent ?? json.percent_change ?? json.percent ?? json.change ?? null;
            const volume = json.volume ?? json.totalVolume ?? json.v ?? null;
            const prevClose = json.prevClose ?? json.previous_close ?? json.prev_close ?? null;
            const openPrice = json.openPrice ?? json.open ?? null;
            const dayRange = json.dayRange ?? (json.low && json.high ? { low: json.low, high: json.high } : null);
            return res.json({ currentPrice: cp, percentChange: percent, volume, prevClose, openPrice, dayRange, raw: json });
          } catch (e) {
            res.set('Content-Type', ct || 'text/plain');
            return res.status(200).send(text);
          }
        }
        res.set('Content-Type', ct || 'text/plain');
        return res.status(200).send(text);
      } catch (err) { lastErr = err; continue; }
    }
    return res.status(502).json({ error: 'Upstream quote fetch failed', detail: String(lastErr?.message || lastErr) });
  } catch (err) {
    console.error('/api/quote failed:', err);
    return res.status(500).json({ error: 'Internal server error', detail: String(err?.message || err) });
  }
});

// --- many proxy endpoints (unchanged) ---
reg('/api/stock', (req, res) => { const q = req.query.name || req.query.symbol; if (!q) return res.status(400).json({ error: 'Missing ?name or ?symbol' }); return proxyFetch(res, `${BASE_URL}/stock?name=${encodeURIComponent(q)}`); });
reg('/api/industry_search', (req, res) => { const q = req.query.query; if (!q) return res.status(400).json({ error: 'Missing ?query' }); return proxyFetch(res, `${BASE_URL}/industry_search?query=${encodeURIComponent(q)}`); });
reg('/api/mutual_fund_search', (req, res) => { const q = req.query.query; if (!q) return res.status(400).json({ error: 'Missing ?query' }); return proxyFetch(res, `${BASE_URL}/mutual_fund_search?query=${encodeURIComponent(q)}`); });

reg('/api/trending', async (req, res) => {
  const now = Date.now();
  if (trendingCache && now < trendingExpiry) {
    console.log('[trending] returning cache');
    return res.json(trendingCache);
  }
  try {
    const r = await fetchWithTimeout(`${BASE_URL}/trending`, { headers: makeHeaders(), method: 'GET' }, 15_000);
    const ct = (r.headers.get('content-type') || '').toLowerCase();
    const text = await r.text().catch(() => '');
    if (!text) {
      if (trendingCache && now < trendingStaleExpiry) {
        res.set('X-AGI-Upstream-Cache', 'empty-upstream');
        return res.json(trendingCache);
      }
      return res.status(r.status).end();
    }
    if (isUpstreamRateLimited(r.status, text)) {
      if (trendingCache && now < trendingStaleExpiry) {
        console.warn('[trending] upstream 429 — serving stale cache');
        res.set('X-AGI-Upstream-Cache', 'rate-limited');
        return res.json(trendingCache);
      }
      // Soft fallback via Groww/NSE dashboard so homepage desks stay populated.
      try {
        const { getDashboardData } = await import('./services/marketDataService.js');
        const dash = await getDashboardData({
          indianApiKey: API_KEY,
          indianApiBase: BASE_URL,
        });
        const soft = {
          trending_stocks: {
            top_gainers: dash?.gainers || [],
            top_losers: dash?.losers || [],
          },
          source: 'agi-market-fallback',
          stale: true,
          upstream_status: 429,
        };
        if ((soft.trending_stocks.top_gainers.length + soft.trending_stocks.top_losers.length) > 0) {
          trendingCache = soft;
          trendingExpiry = Date.now() + Math.min(PROXY_CACHE_TTL_MS, 60_000);
          trendingStaleExpiry = Date.now() + PROXY_CACHE_STALE_MS;
          res.set('X-AGI-Upstream-Cache', 'dashboard-fallback');
          return res.status(200).json(soft);
        }
      } catch (fallbackErr) {
        console.warn('[trending] dashboard fallback failed:', fallbackErr?.message || fallbackErr);
      }
      return res.status(200).json({
        error: 'upstream_rate_limited',
        trending_stocks: { top_gainers: [], top_losers: [] },
        stale: true,
      });
    }
    if (ct.includes('application/json') || ct.includes('+json')) {
      try {
        const json = JSON.parse(text);
        trendingCache = json;
        trendingExpiry = Date.now() + PROXY_CACHE_TTL_MS;
        trendingStaleExpiry = Date.now() + PROXY_CACHE_STALE_MS;
        return res.status(r.status).json(json);
      } catch (parseErr) {
        console.error('[trending] parse error:', parseErr?.message || parseErr);
        if (trendingCache && now < trendingStaleExpiry) {
          res.set('X-AGI-Upstream-Cache', 'parse-error');
          return res.json(trendingCache);
        }
        return res.status(502).json({ error: 'Invalid trending JSON' });
      }
    } else {
      if (trendingCache && now < trendingStaleExpiry) {
        res.set('X-AGI-Upstream-Cache', 'non-json-upstream');
        return res.json(trendingCache);
      }
      return res.status(r.status).send(text);
    }
  } catch (err) {
    console.error('trending fetch failed:', err?.message || err);
    if (trendingCache && Date.now() < trendingStaleExpiry) {
      res.set('X-AGI-Upstream-Cache', err?.isTimeout ? 'timeout' : 'fetch-failed');
      return res.json(trendingCache);
    }
    return res.status(502).json({ error: 'Upstream trending error', detail: err?.message || String(err) });
  }
});

reg('/api/fetch_52_week_high_low_data', (req, res) => proxyFetch(res, `${BASE_URL}/fetch_52_week_high_low_data`));
reg('/api/NSE_most_active', (req, res) => proxyFetch(res, `${BASE_URL}/NSE_most_active`));
reg('/api/BSE_most_active', (req, res) => proxyFetch(res, `${BASE_URL}/BSE_most_active`));
reg('/api/mutual_funds', (req, res) => proxyFetch(res, `${BASE_URL}/mutual_funds`));
reg('/api/price_shockers', (req, res) => proxyFetch(res, `${BASE_URL}/price_shockers`));
reg('/api/commodities', async (req, res) => {
  try {
    const { fetchYahooIndices } = await import('./providers/yahooIndices.js');
    const rows = await fetchYahooIndices(['Gold', 'Silver', 'Brent', 'Bitcoin', 'USDINR']);
    if (rows.length) {
      return res.status(200).json({
        commodities: rows.map((r) => ({
          name: r.name,
          price: r.price,
          percentChange: r.percentChange,
          change: r.percentChange,
          source: r.source || 'yahoo',
        })),
        source: 'yahoo',
        updatedAt: new Date().toISOString(),
        stale: false,
      });
    }
  } catch (err) {
    console.warn('[commodities] yahoo fallback failed:', err?.message || err);
  }
  return proxyFetch(res, `${BASE_URL}/commodities`);
});
reg('/api/market-context', async (_req, res) => {
  const data = await getMarketContext();
  res.set('Cache-Control', 'public, max-age=900, stale-while-revalidate=300');
  return res.json(data);
});

// NSE index snapshot for homepage Market Snapshot (IndianAPI has no /indices endpoint).
const INDEX_NAMES = ['NIFTY 50', 'NIFTY BANK', 'BANK NIFTY'];
const INDICES_FRESH_MS = 60_000;
const INDICES_STALE_MS = 30 * 60_000;
let indicesCache = null; // { body, at }

function sendIndices(res, cacheHit, { reason } = {}) {
  const body = {
    ...cacheHit.body,
    stale: Boolean(cacheHit.stale || reason),
    live_unavailable: Boolean(reason),
    updated_at: cacheHit.body?.updated_at || new Date(cacheHit.at).toISOString(),
  };
  res.set('Cache-Control', 'public, max-age=30, stale-while-revalidate=300');
  if (reason) res.set('X-AGI-Upstream-Cache', reason);
  return res.status(200).json(body);
}

reg('/api/indices', async (req, res) => {
  const now = Date.now();
  if (indicesCache && now - indicesCache.at < INDICES_FRESH_MS) {
    return sendIndices(res, { ...indicesCache, stale: false });
  }

  try {
    const r = await fetchWithTimeout('https://www.nseindia.com/api/allIndices', {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; AGIB-Proxy/1.0)',
        Referer: 'https://www.nseindia.com/',
      },
    }, 15_000);

    const text = await r.text().catch(() => '');
    if (!r.ok || !text) {
      if (indicesCache && now - indicesCache.at < INDICES_STALE_MS) {
        return sendIndices(res, { ...indicesCache, stale: true }, { reason: `upstream-${r.status || 'empty'}` });
      }
      return res.status(200).json({
        error: 'Failed to fetch NSE indices',
        indices: [],
        stale: true,
        live_unavailable: true,
      });
    }

    const payload = JSON.parse(text);
    const rows = Array.isArray(payload?.data) ? payload.data : [];
    const wanted = new Set(INDEX_NAMES.map((n) => n.toUpperCase()));
    const indices = [];

    for (const row of rows) {
      const name = String(row.index || row.indexSymbol || '').trim();
      if (!name || !wanted.has(name.toUpperCase())) continue;

      indices.push({
        name,
        price: row.last ?? row.previousClose ?? null,
        percentChange: row.percentChange ?? row.variation ?? null,
        date: row.timeStamp ? String(row.timeStamp).split(' ')[0] : null,
        time: row.timeStamp ? String(row.timeStamp).split(' ').slice(1).join(' ') : null,
      });
    }

    // Hero also looks for "BANK NIFTY" — alias NIFTY BANK if needed.
    const bank = indices.find((i) => i.name.toUpperCase() === 'NIFTY BANK');
    if (bank && !indices.some((i) => i.name.toUpperCase() === 'BANK NIFTY')) {
      indices.push({ ...bank, name: 'BANK NIFTY' });
    }

    if (!indices.length) {
      if (indicesCache && now - indicesCache.at < INDICES_STALE_MS) {
        return sendIndices(res, { ...indicesCache, stale: true }, { reason: 'empty-payload' });
      }
      return res.status(200).json({ indices: [], stale: true, live_unavailable: true });
    }

    const body = { indices, updated_at: new Date().toISOString(), stale: false, live_unavailable: false };
    indicesCache = { body, at: Date.now() };
    return sendIndices(res, { ...indicesCache, stale: false });
  } catch (err) {
    console.error('[indices] fetch failed:', err?.message || err);
    if (indicesCache && Date.now() - indicesCache.at < INDICES_STALE_MS) {
      return sendIndices(res, { ...indicesCache, stale: true }, {
        reason: err?.isTimeout ? 'timeout' : 'fetch-failed',
      });
    }
    return res.status(200).json({
      error: 'Indices fetch failed',
      indices: [],
      stale: true,
      live_unavailable: true,
      detail: String(err?.message || err),
    });
  }
});

reg('/api/stock_target_price', (req, res) => { const id = req.query.stock_id; if (!id) return res.status(400).json({ error: 'Missing ?stock_id' }); return proxyFetch(res, `${BASE_URL}/stock_target_price?stock_id=${encodeURIComponent(id)}`); });
reg('/api/stock_forecasts', (req, res) => { const params = new URLSearchParams(req.query); if (!params.has('stock_id')) return res.status(400).json({ error: 'Missing required ?stock_id' }); return proxyFetch(res, `${BASE_URL}/stock_forecasts?${params.toString()}`); });

reg('/api/historical_data', async (req, res) => {
  try {
    const symbol = req.query.symbol || req.query.stock_id || req.query.name;
    if (!symbol) return res.status(400).json({ error: 'Missing required ?symbol or ?stock_id or ?name' });
    const qs = new URLSearchParams(req.query).toString();
    const upstream = `${BASE_URL}/historical_data?${qs}`;
    const r = await fetchWithTimeout(upstream, { method: 'GET', headers: makeHeaders() }, 20_000);
    const ct = (r.headers.get('content-type') || '').toLowerCase();
    const text = await r.text().catch(() => '');
    if (!r.ok) { res.set('Content-Type', ct || 'text/plain'); return res.status(r.status).send(text); }
    if (ct.includes('application/json') || ct.includes('+json')) { try { const json = JSON.parse(text); return res.status(200).json(json); } catch (e) { res.set('Content-Type', ct || 'text/plain'); return res.status(200).send(text); } }
    res.set('Content-Type', ct || 'text/plain'); return res.status(200).send(text);
  } catch (err) { console.error('/api/historical_data failed:', err); return res.status(500).json({ error: 'Internal server error', detail: String(err?.message || err) }); }
});

reg('/api/historical_stats', (req, res) => proxyFetch(res, `${BASE_URL}/historical_stats?${new URLSearchParams(req.query).toString()}`));
reg('/api/news', async (req, res) => {
  // Prefer public headlines service when IndianAPI is rate-limited / empty.
  try {
    const headlines = await getNewsHeadlines();
    if (Array.isArray(headlines?.items) && headlines.items.length) {
      res.set('Cache-Control', 'public, max-age=1800, stale-while-revalidate=300');
      return res.status(200).json({
        news: headlines.items,
        items: headlines.items,
        source: headlines.source || 'newsapi',
        updatedAt: headlines.updatedAt,
        stale: Boolean(headlines.stale),
      });
    }
  } catch (err) {
    console.warn('[news] headlines fallback failed:', err?.message || err);
  }
  return proxyFetch(res, `${BASE_URL}/news?${new URLSearchParams(req.query).toString()}`);
});
reg('/api/ipo/summary', async (_req, res) => {
  const data = await getIpoSummary();
  res.set('Cache-Control', 'public, max-age=3600, stale-while-revalidate=300');
  return res.json(data);
});
reg('/api/ipo/platform', async (_req, res) => {
  const data = await getIpoPlatform();
  res.set('Cache-Control', 'public, max-age=3600, stale-while-revalidate=300');
  return res.json(data);
});
reg('/api/ipo/:symbol', async (req, res) => {
  const data = await getIpoDetail(req.params.symbol);
  if (!data.ipo) return res.status(404).json({ error: 'IPO record not found.' });
  res.set('Cache-Control', 'public, max-age=3600, stale-while-revalidate=300');
  return res.json(data);
});
reg('/api/ipo', (req, res) => proxyFetch(res, `${BASE_URL}/ipo`));
reg('/api/recent_announcements', (req, res) => proxyFetch(res, `${BASE_URL}/recent_announcements?${new URLSearchParams(req.query).toString()}`));
reg('/api/corporate_actions', (req, res) => proxyFetch(res, `${BASE_URL}/corporate_actions?${new URLSearchParams(req.query).toString()}`));
reg('/api/statement', (req, res) => proxyFetch(res, `${BASE_URL}/statement?${new URLSearchParams(req.query).toString()}`));

// Free NSE/BSE stock API proxy (http://65.0.104.9 — avoids browser mixed-content/CORS)
const FREE_STOCK_API = (process.env.FREE_STOCK_API || 'http://65.0.104.9').replace(/\/+$/, '');

reg('/api/market/search', (req, res) => {
  const q = req.query.q;
  if (!q) return res.status(400).json({ status: 'error', message: 'Missing ?q' });
  return proxyFetch(res, `${FREE_STOCK_API}/search?q=${encodeURIComponent(q)}`);
});

reg('/api/market/stock/list', (req, res) => {
  const symbols = req.query.symbols;
  if (!symbols) return res.status(400).json({ status: 'error', message: 'Missing ?symbols' });
  const qs = new URLSearchParams(req.query).toString();
  return proxyFetch(res, `${FREE_STOCK_API}/stock/list?${qs}`);
});

reg('/api/market/stock', (req, res) => {
  const symbol = req.query.symbol;
  if (!symbol) return res.status(400).json({ status: 'error', message: 'Missing ?symbol' });
  const qs = new URLSearchParams(req.query).toString();
  return proxyFetch(res, `${FREE_STOCK_API}/stock?${qs}`);
});

reg('/api/market/symbols', (req, res) => proxyFetch(res, `${FREE_STOCK_API}/symbols`));

// Do not proxy AGI paths to IndianAPI — that produced confusing "Endpoint not allowed"
// 404s when a mount lagged or a request fell through the wildcard.
const AGI_MARKET_INTEL = new Set([
  'briefing',
  'macro-briefing',
  'pre-market-briefing',
  'intelligence',
  'dashboard',
  'ticker',
  'pulse',
  'overview',
  'global-snapshot',
  'groww-health',
  'groww-status',
]);

// Mounted AGI routers (must never be forwarded to IndianAPI).
const AGI_API_PREFIXES = new Set(['ui', 'intelligence', 'research']);

// wildcard fallback (IndianAPI proxy only)
reg('/api/:path(*)', (req, res) => {
  const path = req.params.path || '';
  const [head, ...rest] = path.split('/').filter(Boolean);
  if (AGI_API_PREFIXES.has(head)) {
    return res.status(503).json({
      error: 'AGI API route unavailable on this server build',
      path: `/api/${path}`,
      hint: 'Redeploy finance-news-backend from main so /api/ui, /api/intelligence, and /api/research/nifty500 are mounted.',
      architecture: 'v1.0.1 LOCKED',
    });
  }
  if (head === 'market' && AGI_MARKET_INTEL.has(rest[0])) {
    return res.status(503).json({
      error: 'AGI market intelligence route unavailable on this server build',
      path: `/api/${path}`,
      hint: 'Redeploy finance-news-backend with the latest market router (briefing / macro-briefing / pre-market-briefing).',
    });
  }
  const qs = new URLSearchParams(req.query).toString();
  const upstream = `${BASE_URL}/${path}${qs ? `?${qs}` : ''}`;
  console.log(`[wildcard proxy] /api/${path} -> ${upstream}`);
  return proxyFetch(res, upstream);
});

reg('/__routes', (req, res) => {
  const routes = [];
  (app._router.stack || []).forEach(layer => { if (layer.route && layer.route.path) routes.push({ path: layer.route.path, methods: Object.keys(layer.route.methods).join(',') }); });
  res.json(routes);
});

app.use((req, res) => res.status(404).json({ error: 'Not found', path: req.path }));

// start server
const server = app.listen(PORT, () => {
  console.log(`🚀 IndianAPI Proxy running on port ${PORT} — Base: ${BASE_URL}`);
});

process.on('SIGTERM', () => {
  console.info('SIGTERM received — closing HTTP server');
  server.close(() => {
    console.info('HTTP server closed');
    process.exit(0);
  });
});

export default app;

// Live intelligence harden — force API redeploy (Ask AGI timeout + Playwright default)

// CIE V1 proxy mounted

// ILR V1 proxy mounted

// IREP V1 proxy mounted — force API redeploy (RQ1 complete)
