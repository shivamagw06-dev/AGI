/**
 * UI Aggregation proxy — frontend talks to /api/ui/*, never to engines directly.
 * Backs onto intelligence-engine /v1/ui/*.
 * Homepage market snapshot is enriched server-side (not via browser market APIs).
 */

import { Router } from 'express';
import {
  cachedMarketSnapshot,
  enrichHomePayload,
} from '../services/homeOfficeEnrichment.js';
import { getTickerData } from '../services/marketDataService.js';
import { getAgiIntelligence } from '../services/intelligenceService.js';
import { fetchNseIndices } from '../providers/fallback.js';
import { fetchYahooIndices } from '../providers/yahooIndices.js';
import {
  marketCycleCacheMaxAgeSeconds,
  oncePerMarketCycle,
} from '../config/marketRefresh.js';
import {
  findPublishedResearch,
  mergePublishedResearch,
  publishedResearchPack,
} from '../services/askDeskFallback.js';

function engineConfig() {
  let baseUrl = (process.env.INTELLIGENCE_ENGINE_URL || 'http://127.0.0.1:8100').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) {
    baseUrl = `https://${baseUrl}`;
  }
  const token = (process.env.INTELLIGENCE_ENGINE_TOKEN || 'dev-intelligence-token').trim();
  return { baseUrl, token };
}

async function engineFetch(
  path,
  { method = 'GET', body = null, timeoutMs = 360_000, headers: extraHeaders = null } = {},
) {
  const { baseUrl, token } = engineConfig();
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      'X-AGI-Intelligence-Token': token,
      ...(extraHeaders && typeof extraHeaders === 'object' ? extraHeaders : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  return { ok: response.ok, status: response.status, data };
}

function sparkFromChange(change) {
  const n = Number(change);
  const base = 50;
  if (!Number.isFinite(n)) return [48, 50, 49, 51, 50, 52, 51];
  const dir = n >= 0 ? 1 : -1;
  return [0, 1, 2, 3, 4, 5, 6].map((i) => base + dir * Math.abs(n) * (i / 2));
}

const SNAPSHOT_NAME_ALIASES = {
  'NIFTY 50': 'NIFTY',
  NIFTY: 'NIFTY',
  'NIFTY BANK': 'BANK NIFTY',
  'BANK NIFTY': 'BANK NIFTY',
  BANKNIFTY: 'BANK NIFTY',
  SENSEX: 'SENSEX',
  'BSE SENSEX': 'SENSEX',
  'S&P BSE SENSEX': 'SENSEX',
  'INDIA VIX': 'VIX',
  VIX: 'VIX',
  'NIFTY MIDCAP 100': 'MIDCAP',
  'NIFTY MIDCAP 50': 'MIDCAP',
  // Next 50 is a weaker stand-in — only used if Midcap 100/50 are missing.
  'NIFTY NEXT 50': 'MIDCAP',
  MIDCAP: 'MIDCAP',
  'NIFTY SMALLCAP 100': 'SMALLCAP',
  'NIFTY SMALLCAP 50': 'SMALLCAP',
  'NIFTY SMLCAP 100': 'SMALLCAP',
  SMALLCAP: 'SMALLCAP',
};

/** Higher wins when multiple raw indices map to the same snapshot label. */
const SNAPSHOT_SOURCE_PRIORITY = {
  'NIFTY 50': 100,
  NIFTY: 100,
  'NIFTY BANK': 100,
  'BANK NIFTY': 100,
  BANKNIFTY: 100,
  SENSEX: 100,
  'BSE SENSEX': 90,
  'S&P BSE SENSEX': 90,
  'INDIA VIX': 100,
  VIX: 100,
  'NIFTY MIDCAP 100': 100,
  MIDCAP: 95,
  'NIFTY MIDCAP 50': 80,
  'NIFTY NEXT 50': 40,
  'NIFTY SMALLCAP 100': 100,
  'NIFTY SMLCAP 100': 95,
  SMALLCAP: 90,
  'NIFTY SMALLCAP 50': 70,
};

const CORE_INDIAN = ['NIFTY', 'BANK NIFTY', 'SENSEX', 'MIDCAP', 'SMALLCAP', 'VIX'];
const CORE_GLOBAL = ['NASDAQ', 'S&P', 'Dow', 'Gold', 'Silver', 'Brent', 'Bitcoin', 'USDINR'];

/** ETF proxy prices must never be shown as cash index levels. */
function looksLikeEtfProxy(name, price) {
  const n = Number(price);
  if (!Number.isFinite(n) || n <= 0) return false;
  if (name === 'S&P' && n < 2000) return true; // SPY ~700s vs S&P cash ~thousands
  if (name === 'NASDAQ' && n < 5000) return true; // QQQ vs NASDAQ Composite
  if (name === 'Dow' && n < 10000) return true; // DIA vs Dow cash
  if (name === 'Gold' && n < 1000) return true; // GLD ETF vs gold futures/oz
  return false;
}

function normalizeSnapshotName(raw) {
  const key = String(raw || '').trim().toUpperCase();
  return SNAPSHOT_NAME_ALIASES[key] || null;
}

function snapshotPriority(raw) {
  const key = String(raw || '').trim().toUpperCase();
  return SNAPSHOT_SOURCE_PRIORITY[key] || 50;
}

function hasLivePrice(card) {
  const n = Number(card?.price);
  // Groww sometimes returns 0 for unresolved symbols — treat as missing.
  return Number.isFinite(n) && n > 0;
}

function isValidPrice(price) {
  const n = Number(price);
  return Number.isFinite(n) && n > 0;
}

async function buildMarketSnapshot() {
  return oncePerMarketCycle('home-market-snapshot', () => buildMarketSnapshotFresh());
}

async function buildMarketSnapshotFresh() {
  const cycleUpdatedAt = new Date().toISOString();
  const cards = [];
  const push = (name, price, percentChange, extra = {}, priority = 50) => {
    if (!name) return;
    const existing = cards.find((c) => c.name === name);
    const livePrice = isValidPrice(price) ? Number(price) : null;
    if (existing) {
      const existingPriority = Number(existing._priority || 0);
      const betterPriority = priority > existingPriority;
      if (hasLivePrice(existing) && !betterPriority) return;
      if (livePrice != null && (betterPriority || !hasLivePrice(existing))) {
        existing.price = livePrice;
        existing.percentChange = percentChange ?? existing.percentChange ?? null;
        existing.sparkline = sparkFromChange(existing.percentChange);
        existing._priority = priority;
        Object.assign(existing, extra);
      }
      return;
    }
    if (livePrice == null) return;
    cards.push({
      name,
      price: livePrice,
      percentChange: percentChange ?? null,
      sparkline: sparkFromChange(percentChange),
      _priority: priority,
      ...extra,
    });
  };

  // 1) Groww primary (+ NSE inside marketDataService when Groww is thin)
  try {
    const ticker = await getTickerData({
      indianApiKey: process.env.INDIANAPI_KEY || process.env.VITE_INDIANAPI_KEY || '',
      indianApiBase: process.env.INDIANAPI_BASE || 'https://stock.indianapi.in',
    });
    for (const row of ticker?.items || []) {
      const raw = row.name || row.label;
      const name = normalizeSnapshotName(raw);
      if (!name || !isValidPrice(row.price)) continue;
      push(
        name,
        row.price,
        row.percentChange ?? row.change ?? null,
        {
          session: row.source === 'groww' ? 'Groww' : row.source === 'nse' ? 'NSE' : 'Live',
          updatedAt: cycleUpdatedAt,
        },
        snapshotPriority(raw) + (row.source === 'groww' ? 5 : 0)
      );
    }
  } catch {
    /* soft */
  }

  // 2) Direct NSE allIndices (covers MIDCAP / SMALLCAP beyond Groww ticker set)
  try {
    const nseRows = await fetchNseIndices();
    for (const row of nseRows) {
      const name = normalizeSnapshotName(row.name);
      if (!name || !isValidPrice(row.price)) continue;
      push(
        name,
        row.price,
        row.percentChange ?? null,
        {
          session: 'NSE',
          updatedAt: cycleUpdatedAt,
        },
        snapshotPriority(row.name)
      );
    }
  } catch {
    /* soft */
  }

  // 3) Yahoo cash indices / commodities — preferred for global cards.
  // Pre-market context historically used ETF proxies (SPY/QQQ/DIA/GLD); those must not win.
  const missingYahoo = [...CORE_INDIAN, ...CORE_GLOBAL].filter((name) => {
    const card = cards.find((c) => c.name === name);
    return !hasLivePrice(card) || looksLikeEtfProxy(name, card.price);
  });
  if (missingYahoo.length) {
    try {
      const yahooRows = await fetchYahooIndices(missingYahoo);
      for (const row of yahooRows) {
        if (!isValidPrice(row.price) || looksLikeEtfProxy(row.name, row.price)) continue;
        push(
          row.name,
          row.price,
          row.percentChange ?? null,
          {
            session: 'Yahoo',
            updatedAt: cycleUpdatedAt,
          },
          120
        );
      }
    } catch {
      /* soft */
    }
  }

  // Global / commodity tone feed — only fill names still missing after Yahoo cash quotes.
  try {
    const { getPreMarketContext } = await import('../services/preMarketContextService.js');
    const ctx = await getPreMarketContext({ force: false });
    for (const m of ctx.globalMarkets || []) {
      const label = String(m.label || m.id || '').trim();
      if (!label) continue;
      let name = label;
      if (/nasdaq/i.test(label)) name = 'NASDAQ';
      else if (/s&p|spx/i.test(label)) name = 'S&P';
      else if (/dow/i.test(label)) name = 'Dow';
      else if (/gold/i.test(label)) name = 'Gold';
      else if (/silver/i.test(label)) name = 'Silver';
      else if (/brent|crude|wti|usoil/i.test(label)) name = 'Brent';
      else if (/bitcoin|btc/i.test(label)) name = 'Bitcoin';
      else if (/vix/i.test(label)) name = 'VIX';
      else continue;
      const price = m.level ?? m.price ?? null;
      if (looksLikeEtfProxy(name, price)) continue;
      if (hasLivePrice(cards.find((c) => c.name === name))) continue;
      push(name, price, m.changePct ?? m.percentChange ?? null, {
        session: m.source || 'Global',
        updatedAt: cycleUpdatedAt,
      }, 40);
    }
    for (const c of ctx.commodities || []) {
      const label = String(c.label || c.name || '');
      let name = null;
      if (/gold/i.test(label)) name = 'Gold';
      if (/silver/i.test(label)) name = 'Silver';
      if (/brent|crude/i.test(label)) name = 'Brent';
      if (!name) continue;
      const price = c.level ?? c.price ?? null;
      if (looksLikeEtfProxy(name, price)) continue;
      if (hasLivePrice(cards.find((x) => x.name === name))) continue;
      push(name, price, c.changePct ?? c.percentChange ?? null, {
        session: c.source || 'Global',
        updatedAt: cycleUpdatedAt,
      }, 40);
    }
  } catch {
    /* soft */
  }

  // USDINR via Frankfurter soft (Yahoo INR=X preferred above when available)
  try {
    if (!hasLivePrice(cards.find((c) => c.name === 'USDINR'))) {
      const fx = await fetch('https://api.frankfurter.app/latest?from=USD&to=INR', {
        signal: AbortSignal.timeout(8_000),
      });
      if (fx.ok) {
        const body = await fx.json();
        const rate = body?.rates?.INR;
        if (Number.isFinite(rate)) {
          push('USDINR', rate, null, { session: 'Frankfurter', updatedAt: cycleUpdatedAt }, 30);
        }
      }
    }
  } catch {
    /* soft */
  }

  // Soft desk close levels — last successful snapshot. Never blank the strip.
  if (!cards.length) {
    const cached = cachedMarketSnapshot();
    if (cached.rows?.length) {
      return cached.rows.map((row) => ({
        ...row,
        liveUnavailable: true,
        stale: true,
        session: row.session || 'Last snapshot',
        updatedAt: row.updatedAt || new Date(cached.at || Date.now()).toISOString(),
      }));
    }
  }

  const order = [
    'NIFTY',
    'BANK NIFTY',
    'SENSEX',
    'MIDCAP',
    'SMALLCAP',
    'NASDAQ',
    'S&P',
    'Dow',
    'Gold',
    'Silver',
    'USDINR',
    'Brent',
    'Bitcoin',
    'VIX',
  ];
  cards.sort((a, b) => {
    const ai = order.indexOf(a.name);
    const bi = order.indexOf(b.name);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });
  return cards.map(({ _priority, ...rest }) => ({
    ...rest,
    updatedAt: cycleUpdatedAt,
    stale: false,
    liveUnavailable: false,
  }));
}

function marketSessionNow() {
  const now = new Date();
  // Approximate IST session 09:15–15:30
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const mins = ist.getHours() * 60 + ist.getMinutes();
  const open = 9 * 60 + 15;
  const close = 15 * 60 + 30;
  const weekday = ist.getDay();
  if (weekday === 0 || weekday === 6 || mins < open || mins > close) {
    const nextOpen = open;
    let remaining = nextOpen - mins;
    if (mins > close) remaining = 24 * 60 - mins + open;
    if (weekday === 6) remaining += 24 * 60;
    if (weekday === 0) remaining += 0;
    return {
      status: 'closed',
      label: 'Market Closed',
      time_remaining: `${Math.max(0, Math.floor(remaining / 60))}h ${Math.abs(remaining % 60)}m to open`,
    };
  }
  const remaining = close - mins;
  return {
    status: 'open',
    label: 'Market Open',
    time_remaining: `${Math.floor(remaining / 60)}h ${remaining % 60}m remaining`,
  };
}

export default function createUiRouter() {
  const router = Router();

  router.get('/health', async (_req, res) => {
    // BFF homepage enrichment can serve /api/ui/home without the Python engine.
    // Report operational+degraded instead of hard-unavailable when only the engine is down.
    let engine = null;
    try {
      const result = await engineFetch('/v1/ui/health', { timeoutMs: 5_000 });
      engine = {
        ok: Boolean(result.ok),
        status: result.status,
        data: result.data,
      };
    } catch (error) {
      engine = { ok: false, status: 503, error: error.message };
    }

    const payload = {
      status: engine.ok ? 'ok' : 'degraded',
      layer: 'UI Aggregation',
      architecture_status: 'v1.0.1 LOCKED',
      bff: {
        home: true,
        enrichment: true,
        note: 'Express /api/ui/home serves AGI intelligence + institutional desk defaults even when the engine is offline.',
      },
      engine: engine.ok
        ? { status: 'ok', detail: engine.data }
        : {
            status: 'unavailable',
            error: engine.error || engine.data?.error || 'fetch failed',
            hint: 'Set INTELLIGENCE_ENGINE_URL to a live agib-intelligence-engine service and redeploy.',
          },
    };
    return res.status(200).json(payload);
  });

  // Homepage — always 200 with populated institutional desks (engine optional)
  router.get('/home', async (_req, res) => {
    const session = marketSessionNow();
    // Warm AGI intelligence in the same 30-min cycle as the Groww/Yahoo snapshot
    // so Market Outlook strip and homepage prices refresh together.
    void getAgiIntelligence({
      indianApiKey: process.env.INDIANAPI_KEY || process.env.VITE_INDIANAPI_KEY || '',
      indianApiBase: process.env.INDIANAPI_BASE || 'https://stock.indianapi.in',
    }).catch(() => null);

    let snapshot = [];
    try {
      snapshot = await buildMarketSnapshot();
    } catch {
      snapshot = cachedMarketSnapshot().rows || [];
    }

    let engineData = null;
    try {
      const result = await engineFetch('/v1/ui/home', { timeoutMs: 8_000 });
      if (result.ok) engineData = result.data || null;
    } catch {
      engineData = null;
    }

    try {
      const payload = await enrichHomePayload(engineData, { snapshot, session });
      const maxAge = marketCycleCacheMaxAgeSeconds();
      res.set(
        'Cache-Control',
        `public, max-age=${Math.min(maxAge, 120)}, stale-while-revalidate=${Math.max(60, maxAge)}`
      );
      return res.status(200).json(payload);
    } catch (error) {
      // Last-resort populated shell — never blank homepage
      try {
        const payload = await enrichHomePayload(null, { snapshot, session });
        payload.meta = { ...(payload.meta || {}), degraded: true, detail: error.message };
        return res.status(200).json(payload);
      } catch (err2) {
        return res.status(503).json({ error: 'UI aggregation unavailable', detail: err2.message });
      }
    }
  });

  const getPaths = [
    '/dashboard',
    '/macro',
    '/portfolio',
    '/workflow',
    '/company/:ticker',
    '/research/:researchId',
    '/article/:articleId',
    '/timeline/:entity',
    '/theme/:themeId',
    '/sector/:sectorId',
    '/predictions',
    '/calendar',
    '/copilot',
    '/autocomplete',
  ];

  for (const p of getPaths) {
    router.get(p, async (req, res) => {
      try {
        const path = `/v1/ui${req.path}`;
        const qs = new URLSearchParams(req.query).toString();
        // Public pages (Market Intelligence) must not hang for minutes when the
        // engine is cold. Dashboard is enrichment, not a hard dependency.
        const timeoutMs = p === '/dashboard' ? 12_000 : 45_000;
        const result = await engineFetch(`${path}${qs ? `?${qs}` : ''}`, { timeoutMs });
        return res.status(result.status).json(result.data);
      } catch (error) {
        return res.status(503).json({ error: 'UI aggregation unavailable', detail: error.message });
      }
    });
  }

  /** Phase-1 request id: ask_YYYYMMDD_<hex>. Accepts legacy ASK-* / ask_*. */
  const newAskRequestId = () => {
    const day = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const hex = Math.random().toString(16).slice(2, 10);
    return `ask_${day}_${hex}`;
  };

  const normalizeAskRequestId = (raw) => {
    const s = String(raw || '').trim();
    if (!s) return newAskRequestId();
    if (/^ask_/i.test(s)) return s.startsWith('ask_') ? s : s.toLowerCase();
    // Legacy ASK-YYYYMMDD-HEX → ask_YYYYMMDD_hex
    if (/^ASK-/i.test(s) && !s.includes('_')) {
      const parts = s.split('-');
      if (parts.length >= 3) {
        const day = parts[1];
        const hexpart = parts.slice(2).join('').toLowerCase();
        if (/^\d+$/.test(day) && hexpart) return `ask_${day}_${hexpart}`;
      }
    }
    return s;
  };

  const logAskPipeline = (stage, requestId, extra = {}) => {
    const payload = {
      stage,
      timestamp: new Date().toISOString(),
      request_id: requestId,
      duration_ms: extra.duration_ms ?? null,
      status: extra.status || 'ok',
      ...extra,
    };
    // eslint-disable-next-line no-console
    console.log(
      `ask_pipeline request_id=${requestId} stage=${stage} status=${payload.status} duration_ms=${payload.duration_ms ?? 0}`,
      JSON.stringify(payload),
    );
  };

  const classifyFallbackReason = (detail, meta = {}) => {
    if (meta.timeout) return 'timeout';
    if (meta.circuitBreaker) return 'circuit_breaker';
    if (meta.engineStatus === 0) return 'engine_unavailable';
    if (meta.html502 || meta.engineStatus === 502 || meta.engineStatus === 503) {
      return 'engine_unavailable';
    }
    if (meta.engineStatus >= 500) return 'dependency_failure';
    const d = String(detail || '').toLowerCase();
    if (d.includes('timeout')) return 'timeout';
    if (d.includes('intent')) return 'intent_failure';
    if (d.includes('retriev')) return 'retrieval_failure';
    if (d.includes('llm')) return 'llm_timeout';
    if (d.includes('circuit')) return 'circuit_breaker';
    if (d.includes('unavailable') || d.includes('502') || d.includes('503')) {
      return 'engine_unavailable';
    }
    return 'dependency_failure';
  };

  router.get('/debug/request/:requestId', async (req, res) => {
    const requestId = String(req.params.requestId || '').trim();
    if (!requestId) {
      return res.status(400).json({ error: 'request_id required' });
    }
    try {
      const result = await engineFetch(`/v1/debug/request/${encodeURIComponent(requestId)}`, {
        timeoutMs: 5_000,
      });
      return res.status(result.status).json(result.data);
    } catch (error) {
      return res.status(503).json({
        error: 'debug_request_unavailable',
        detail: error.message,
        request_id: requestId,
      });
    }
  });

  router.post('/search', async (req, res) => {
    const question = req.body?.question || req.query.question;
    const ticker = req.body?.ticker || req.query.ticker;
    const conversationId = req.body?.conversation_id || req.body?.conversationId;
    const resetConversation = Boolean(req.body?.reset_conversation || req.body?.resetConversation);
    if (!question) {
      return res.status(400).json({ error: 'question is required' });
    }

    const askTimeoutMs = Math.max(
      15_000,
      Number.parseInt(process.env.ASK_ENGINE_TIMEOUT_MS || '55000', 10) || 55_000,
    );
    const httpStarted = Date.now();
    const gatewayTraceId = normalizeAskRequestId(
      req.body?.request_id ||
        req.body?.ask_trace_id ||
        req.headers['x-request-id'] ||
        req.headers['x-ask-trace-id'],
    );
    logAskPipeline('REQUEST_RECEIVED', gatewayTraceId, {
      status: 'ok',
      duration_ms: 0,
      question_excerpt: String(question).slice(0, 160),
    });
    // Published AGI research is an immediate source of truth. Fetch it in
    // parallel with the deeper engine so newly published articles are usable
    // before asynchronous chunking/embedding has completed.
    const publishedResearchPromise = findPublishedResearch(String(question)).catch(() => null);

    const buildTimeoutOrch = (detail, meta = {}) => {
      const elapsed = Date.now() - httpStarted;
      const timedOut = Boolean(meta.timeout);
      const fallbackReason = classifyFallbackReason(detail, meta);
      const partial = meta.partialTrace && typeof meta.partialTrace === 'object' ? meta.partialTrace : {};
      const partialLat = partial.latency && typeof partial.latency === 'object' ? partial.latency : {};
      const lastStage =
        partial.last_completed_stage ||
        partialLat.last_completed_stage ||
        'http_ingress';
      const funnel = {
        retrieved: Number(partial.evidence?.retrieved || partial.funnel?.retrieved || 0),
        ranked: Number(partial.evidence?.ranked || partial.funnel?.ranked || 0),
        passed: Number(partial.evidence?.passed || partial.funnel?.passed || 0),
        referenced: Number(partial.evidence?.referenced || partial.funnel?.referenced || 0),
      };
      const entityFromPartial = partial.entity && typeof partial.entity === 'object' ? partial.entity : {};
      const entityName =
        entityFromPartial.name ||
        entityFromPartial.detected ||
        (ticker ? String(ticker).toUpperCase() : null);
      const orch = {
        version: 'ask-orchestration-trace-2',
        ask_trace_id: gatewayTraceId,
        request_id: gatewayTraceId,
        engine_reached: Boolean(partial.engine_reached) || lastStage !== 'http_ingress',
        fallback: true,
        fallback_used: true,
        fallback_reason: fallbackReason,
        reason: detail,
        completed: false,
        timeout: timedOut,
        partial: true,
        last_completed_stage: lastStage,
        elapsed_ms: elapsed,
        timeout_ms: askTimeoutMs,
        engine_status: meta.engineStatus ?? null,
        html_502: Boolean(meta.html502),
        entity: {
          name: entityName,
          detected: entityName,
          confidence: Number(entityFromPartial.confidence || (ticker ? 0.95 : 0)),
          question_excerpt: String(question || '').slice(0, 160),
          ...(entityFromPartial.source ? { source: entityFromPartial.source } : {}),
        },
        funnel,
        evidence: funnel,
        ikl: partial.ikl || {},
        latency: {
          http_ms: elapsed,
          total_ms: elapsed,
          node_ms: elapsed,
          http_ingress_ms: Number(partialLat.http_ingress_ms || 0),
          entity_ms: Number(partialLat.entity_ms || partialLat.stages?.entity_resolution || 0),
          ikl_ms: Number(partialLat.ikl_ms || partialLat.stages?.ikl || 0),
          retrieval_ms: Number(partialLat.retrieval_ms || partialLat.stages?.retrieval || 0),
          ranking_ms: Number(partialLat.ranking_ms || partialLat.stages?.ranking || 0),
          reasoning_ms: Number(partialLat.reasoning_ms || partialLat.stages?.reasoning || 0),
          assembly_ms: Number(partialLat.assembly_ms || partialLat.stages?.response_assembly || 0),
          serialization_ms: Number(partialLat.serialization_ms || 0),
          last_completed_stage: lastStage,
          stages: { http_ingress: 0, ...(partialLat.stages || {}), http: elapsed },
          warnings: [
            ...((Array.isArray(partial.stage_warnings) && partial.stage_warnings) ||
              (Array.isArray(partialLat.warnings) && partialLat.warnings) ||
              []),
            ...(timedOut
              ? [
                  {
                    kind: 'gateway_engine_timeout',
                    elapsed_ms: elapsed,
                    threshold_ms: askTimeoutMs,
                    ask_trace_id: gatewayTraceId,
                    request_id: gatewayTraceId,
                    last_completed_stage: lastStage,
                  },
                ]
              : []),
          ],
        },
        diagnostics_visibility: 'internal',
        execution_trace: [
          `Request ID: ${gatewayTraceId}`,
          `Ask Trace ID: ${gatewayTraceId}`,
          `Entity: ${entityName || '—'} (${entityFromPartial.confidence != null ? entityFromPartial.confidence : ticker ? '0.95' : '—'})`,
          `IKL: ${Number(partialLat.ikl_ms || 0)}ms`,
          `Retrieved: ${funnel.retrieved}`,
          `Ranked: ${funnel.ranked}`,
          `Passed: ${funnel.passed}`,
          `Referenced: ${funnel.referenced}`,
          `Reasoning: ${(Number(partialLat.reasoning_ms || 0) / 1000).toFixed(1)}s`,
          `Assembly: ${Number(partialLat.assembly_ms || 0)}ms`,
          'Completed: false',
          `Last completed stage: ${lastStage}`,
          `Elapsed: ${(elapsed / 1000).toFixed(1)}s`,
          `Fallback reason: ${fallbackReason}`,
          timedOut ? 'Timeout: true' : 'Fallback: true',
        ].join('\n'),
        trace_summary: `Request: ${gatewayTraceId} | Timeout: ${timedOut ? 'Yes' : 'No'} | Fallback: Yes (${fallbackReason}) | Last stage: ${lastStage} | Total: ${(elapsed / 1000).toFixed(1)}s`,
      };
      return orch;
    };

    const fetchPartialTrace = async () => {
      try {
        const result = await engineFetch(`/v1/ui/ask-trace/${encodeURIComponent(gatewayTraceId)}`, {
          timeoutMs: 2_500,
        });
        if (result.status === 200 && result.data?.trace && typeof result.data.trace === 'object') {
          return result.data.trace;
        }
      } catch {
        /* best-effort only */
      }
      return null;
    };

    const serveFallback = async (detail, meta = {}) => {
      const fallbackReason = classifyFallbackReason(detail, meta);
      const forwardMs = Date.now() - httpStarted;
      logAskPipeline('FALLBACK_USED', gatewayTraceId, {
        status: 'fallback',
        duration_ms: forwardMs,
        reason: fallbackReason,
        detail: String(detail || '').slice(0, 240),
        timeout: Boolean(meta.timeout),
        engine_status: meta.engineStatus ?? null,
      });
      try {
        const partialTrace = meta.partialTrace || (await fetchPartialTrace());
        const { buildAskDeskFallback } = await import('../services/askDeskFallback.js');
        const pack = await buildAskDeskFallback(question);
        pack.detail = detail;
        pack.ask_orchestration = {
          ...(pack.ask_orchestration || {}),
          ...buildTimeoutOrch(detail, { ...meta, partialTrace }),
        };
        res.setHeader('X-Ask-Trace-Id', gatewayTraceId);
        res.setHeader('X-Request-Id', gatewayTraceId);
        logAskPipeline('RESPONSE_SENT', gatewayTraceId, {
          status: 'fallback',
          duration_ms: Date.now() - httpStarted,
          fallback_reason: fallbackReason,
        });
        // Best-effort wake for the next client retry.
        engineFetch('/v1/health', { timeoutMs: 8_000 }).catch(() => {});
        return res.status(200).json(pack);
      } catch (fallbackError) {
        logAskPipeline('ERROR', gatewayTraceId, {
          status: 'error',
          duration_ms: Date.now() - httpStarted,
          reason: 'fallback_builder_failed',
          detail: String(fallbackError?.message || fallbackError).slice(0, 240),
        });
        return res.status(503).json({
          error: 'research_desk_unavailable',
          retryable: true,
          detail: detail || fallbackError.message,
          request_id: gatewayTraceId,
          ask_orchestration: buildTimeoutOrch(detail || fallbackError.message, meta),
        });
      }
    };

    // Do not make a visitor wait for the full institutional pipeline when AGI
    // has already published a directly matching report. The deeper engine is
    // reserved for follow-up synthesis; the house article itself is the
    // authoritative answer for this request.
    const directPublishedResearch = await Promise.race([
      publishedResearchPromise,
      new Promise((resolve) => {
        const timer = setTimeout(() => resolve(null), 2_500);
        timer.unref?.();
      }),
    ]);
    if (directPublishedResearch) {
      const pack = publishedResearchPack(String(question), directPublishedResearch);
      pack.ask_orchestration = {
        ...(pack.ask_orchestration || {}),
        ask_trace_id: gatewayTraceId,
        request_id: gatewayTraceId,
        engine_reached: false,
        fallback: false,
        fallback_used: false,
        completed: true,
        timeout: false,
        last_completed_stage: 'published_research_retrieval',
        elapsed_ms: Date.now() - httpStarted,
        published_research: {
          matched: true,
          article_id: directPublishedResearch.id,
          title: directPublishedResearch.title,
          role: 'primary_evidence',
        },
      };
      res.setHeader('X-Ask-Trace-Id', gatewayTraceId);
      res.setHeader('X-Request-Id', gatewayTraceId);
      logAskPipeline('RESPONSE_SENT', gatewayTraceId, {
        status: 'published_research_fast_path',
        duration_ms: Date.now() - httpStarted,
        article_id: directPublishedResearch.id,
      });
      return res.status(200).json(pack);
    }

    try {
      const qs = new URLSearchParams({ question: String(question) });
      if (ticker) qs.set('ticker', String(ticker));
      const path = `/v1/ui/search?${qs.toString()}`;
      const forwardAt = Date.now();
      logAskPipeline('REQUEST_FORWARDED', gatewayTraceId, {
        status: 'ok',
        duration_ms: forwardAt - httpStarted,
        path,
      });
      // Keep the public desk responsive. Long-running analysis should return an honest degraded response rather than hold the browser on a skeleton for two minutes. Deployments can still override this setting explicitly.
      const result = await engineFetch(path, {
        method: 'POST',
        body: {
          question: String(question),
          request_id: gatewayTraceId,
          ask_trace_id: gatewayTraceId,
          ...(ticker ? { ticker: String(ticker) } : {}),
          ...(conversationId ? { conversation_id: String(conversationId) } : {}),
          ...(resetConversation ? { reset_conversation: true } : {}),
        },
        timeoutMs: askTimeoutMs,
        headers: {
          'X-Ask-Trace-Id': gatewayTraceId,
          'X-Request-Id': gatewayTraceId,
        },
      });
      const html502 =
        typeof result.data?.raw === 'string' && result.data.raw.trim().startsWith('<');
      if (html502 || result.status === 502 || result.status === 503 || result.status >= 500) {
        return serveFallback(
          `Intelligence engine unavailable (HTTP ${result.status}${html502 ? ', HTML body' : ''}) — Node desk fallback.`,
          { engineStatus: result.status, html502, timeout: false },
        );
      }
      if (result.data && typeof result.data === 'object') {
        const publishedResearch = await publishedResearchPromise;
        if (publishedResearch) {
          result.data = mergePublishedResearch(result.data, String(question), publishedResearch);
        }
        const orch =
          result.data.ask_orchestration || result.data.degradation?.ask_orchestration || {};
        const httpMs = Date.now() - httpStarted;
        const engineFallback = Boolean(orch.fallback || orch.fallback_used);
        result.data.ask_orchestration = {
          ...orch,
          ask_trace_id: orch.ask_trace_id || gatewayTraceId,
          request_id: orch.request_id || orch.ask_trace_id || gatewayTraceId,
          engine_reached: true,
          fallback: engineFallback,
          fallback_used: engineFallback,
          fallback_reason: orch.fallback_reason || (engineFallback ? 'engine_reported_fallback' : null),
          completed: orch.completed !== false && !engineFallback,
          timeout: Boolean(orch.timeout),
          last_completed_stage:
            orch.last_completed_stage || orch.latency?.last_completed_stage || 'serialization',
          elapsed_ms: orch.elapsed_ms || orch.latency?.total_ms || httpMs,
          timeout_ms: askTimeoutMs,
          engine_status: result.status,
          latency: {
            ...(orch.latency || {}),
            http_ms: httpMs,
            node_ms: httpMs,
          },
          diagnostics_visibility: 'internal',
        };
        const rid = result.data.ask_orchestration.request_id;
        res.setHeader('X-Ask-Trace-Id', rid);
        res.setHeader('X-Request-Id', rid);
        logAskPipeline('RESPONSE_SENT', rid, {
          status: engineFallback ? 'fallback' : 'success',
          duration_ms: httpMs,
          fallback_used: engineFallback,
        });
      }
      return res.status(result.status).json(result.data);
    } catch (error) {
      const timedOut =
        error?.name === 'TimeoutError' || /aborted|timeout/i.test(String(error?.message || ''));
      const msg = timedOut
        ? `Intelligence engine exceeded ASK timeout (${askTimeoutMs}ms) — Node desk fallback.`
        : error.message;
      return serveFallback(msg, { engineStatus: 0, timeout: timedOut });
    }
  });

  return router;
}
