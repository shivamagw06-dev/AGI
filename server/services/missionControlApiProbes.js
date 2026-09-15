/**
 * Mission Control API probes — soft live checks from the Node API.
 * Architecture v1.0.1 LOCKED — additive enrichment only.
 */

import { getCmsLearningSchedulerStatus } from './cmsArticleLearning.js';
import { getCioSchedulerStatus } from './cioMorningScheduler.js';
import { getInstitutionalFlowSchedulerStatus } from './institutionalFlowScheduler.js';
import { getValuationRatiosSchedulerStatus } from './valuationRatiosScheduler.js';
import { getUpstoxHealth } from './upstoxHealth.js';
import { getGrowwHealth } from './growwHealth.js';

function env(...keys) {
  for (const k of keys) {
    const v = (process.env[k] || '').trim();
    if (v) return v;
  }
  return '';
}

function card({
  name,
  status,
  latency_ms = null,
  configured = null,
  last_error = null,
  note = null,
  detail = null,
  colour = null,
}) {
  const st = String(status || 'Unknown');
  const autoColour =
    colour ||
    (st === 'Healthy'
      ? 'Green'
      : st === 'Warning' || st === 'Not configured' || st === 'Unknown'
        ? 'Yellow'
        : 'Red');
  return {
    name,
    status: st,
    colour: autoColour,
    latency: latency_ms,
    latency_ms,
    configured,
    last_error,
    note,
    detail,
    provider_confidence: configured === true ? 'configured' : configured === false ? 'missing_key' : 'probed',
    probed_at: new Date().toISOString(),
    source: 'node_live_probe',
  };
}

async function timedFetch(url, init = {}, timeoutMs = 8000) {
  const started = Date.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const resp = await fetch(url, { ...init, signal: controller.signal });
    const text = await resp.text().catch(() => '');
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text.slice(0, 200) };
    }
    return {
      ok: resp.ok,
      status: resp.status,
      data,
      text,
      latency_ms: Date.now() - started,
    };
  } finally {
    clearTimeout(timer);
  }
}

async function probeIndianApi() {
  const key = env('INDIANAPI_KEY', 'VITE_INDIANAPI_KEY', 'INDIAN_API_KEY');
  const base = (env('INDIANAPI_BASE') || 'https://stock.indianapi.in').replace(/\/$/, '');
  if (!key) {
    return card({
      name: 'Indian API',
      status: 'Not configured',
      configured: false,
      note: 'Set INDIANAPI_KEY on Render Node (and intelligence engine for IOC).',
    });
  }
  try {
    const result = await timedFetch(`${base}/trending`, {
      headers: { Accept: 'application/json', 'x-api-key': key },
    });
    if (result.ok && result.data) {
      return card({
        name: 'Indian API',
        status: 'Healthy',
        configured: true,
        latency_ms: result.latency_ms,
        note: 'Live trending probe ok',
      });
    }
    return card({
      name: 'Indian API',
      status: 'Critical',
      configured: true,
      latency_ms: result.latency_ms,
      last_error: `HTTP ${result.status}`,
      note: String(result.data?.error || result.text || '').slice(0, 160) || 'trending probe failed',
    });
  } catch (err) {
    return card({
      name: 'Indian API',
      status: 'Critical',
      configured: true,
      last_error: err?.message || String(err),
    });
  }
}

async function probeFinnhub() {
  const key = env('FINNHUB_API_KEY', 'VITE_FINNHUB_API_KEY');
  if (!key) {
    return card({
      name: 'Finnhub',
      status: 'Not configured',
      configured: false,
      note: 'Set FINNHUB_API_KEY on Render to enable quotes/calendar.',
    });
  }
  try {
    const result = await timedFetch(
      `https://finnhub.io/api/v1/quote?symbol=AAPL&token=${encodeURIComponent(key)}`
    );
    const hasQuote = result.ok && result.data && (result.data.c != null || result.data.pc != null);
    return card({
      name: 'Finnhub',
      status: hasQuote ? 'Healthy' : 'Warning',
      configured: true,
      latency_ms: result.latency_ms,
      last_error: hasQuote ? null : `HTTP ${result.status}`,
      note: hasQuote ? 'Quote probe ok' : 'Key present but quote empty',
    });
  } catch (err) {
    return card({
      name: 'Finnhub',
      status: 'Critical',
      configured: true,
      last_error: err?.message || String(err),
    });
  }
}

async function probeFmp() {
  const key = env('FMP_API_KEY', 'VITE_FMP_API_KEY');
  if (!key) {
    return card({
      name: 'FMP',
      status: 'Not configured',
      configured: false,
      note: 'Set FMP_API_KEY on Render to enable fundamentals.',
    });
  }
  try {
    const result = await timedFetch(
      `https://financialmodelingprep.com/api/v3/quote/AAPL?apikey=${encodeURIComponent(key)}`
    );
    const ok = result.ok && Array.isArray(result.data) && result.data.length > 0;
    return card({
      name: 'FMP',
      status: ok ? 'Healthy' : 'Warning',
      configured: true,
      latency_ms: result.latency_ms,
      last_error: ok ? null : `HTTP ${result.status}`,
      note: ok ? 'Quote probe ok' : 'Key present but quote empty',
    });
  } catch (err) {
    return card({
      name: 'FMP',
      status: 'Critical',
      configured: true,
      last_error: err?.message || String(err),
    });
  }
}

async function probeYahoo() {
  try {
    const result = await timedFetch(
      'https://query1.finance.yahoo.com/v7/finance/quote?symbols=RELIANCE.NS',
      { headers: { Accept: 'application/json', 'User-Agent': 'AGI-MissionControl/1.0' } }
    );
    const quote = result.data?.quoteResponse?.result?.[0];
    const ok = result.ok && quote && (quote.regularMarketPrice != null || quote.symbol);
    return card({
      name: 'Yahoo Finance',
      status: ok ? 'Healthy' : result.status === 429 ? 'Warning' : 'Critical',
      configured: true,
      latency_ms: result.latency_ms,
      last_error: ok ? null : `HTTP ${result.status}`,
      note: ok ? 'Quote probe ok' : 'Yahoo quote probe failed',
    });
  } catch (err) {
    return card({
      name: 'Yahoo Finance',
      status: 'Critical',
      configured: true,
      last_error: err?.message || String(err),
    });
  }
}

async function probeSupabase() {
  const url = env('SUPABASE_URL', 'VITE_SUPABASE_URL').replace(/\/$/, '');
  const key = env('SUPABASE_SERVICE_ROLE_KEY', 'SUPABASE_ANON_KEY', 'VITE_SUPABASE_ANON_KEY');
  if (!url || !key) {
    return card({
      name: 'Supabase',
      status: 'Not configured',
      configured: false,
      note: 'Missing SUPABASE_URL or service/anon key on Node.',
    });
  }
  try {
    const result = await timedFetch(`${url}/rest/v1/articles?select=id&limit=1`, {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        Accept: 'application/json',
      },
    });
    return card({
      name: 'Supabase',
      status: result.ok ? 'Healthy' : 'Critical',
      configured: true,
      latency_ms: result.latency_ms,
      last_error: result.ok ? null : `HTTP ${result.status}`,
      note: result.ok ? 'articles REST probe ok' : String(result.data?.message || result.text || '').slice(0, 160),
    });
  } catch (err) {
    return card({
      name: 'Supabase',
      status: 'Critical',
      configured: true,
      last_error: err?.message || String(err),
    });
  }
}

async function probeIntelligenceEngine(engineFetch) {
  if (typeof engineFetch !== 'function') {
    return card({
      name: 'Intelligence Engine',
      status: 'Unknown',
      note: 'engineFetch unavailable',
    });
  }
  const started = Date.now();
  try {
    const result = await engineFetch('/v1/health');
    return card({
      name: 'Intelligence Engine',
      status: result.ok ? 'Healthy' : 'Critical',
      configured: true,
      latency_ms: Date.now() - started,
      last_error: result.ok ? null : `HTTP ${result.status}`,
      note: result.data?.service || 'engine health',
    });
  } catch (err) {
    return card({
      name: 'Intelligence Engine',
      status: 'Critical',
      configured: true,
      last_error: err?.message || String(err),
    });
  }
}

async function probeHostinger() {
  const site = (env('PUBLIC_SITE_URL') || 'https://agarwalglobalinvestments.com').replace(/\/$/, '');
  try {
    const result = await timedFetch(site, { method: 'GET', headers: { Accept: 'text/html' } }, 10000);
    const html = result.ok && String(result.text || '').toLowerCase().includes('<!doctype html');
    return card({
      name: 'Hostinger',
      status: html ? 'Healthy' : result.ok ? 'Warning' : 'Critical',
      configured: true,
      latency_ms: result.latency_ms,
      last_error: html ? null : `HTTP ${result.status}`,
      note: html ? 'Website HTML reachable' : 'Site probe unexpected',
    });
  } catch (err) {
    return card({
      name: 'Hostinger',
      status: 'Critical',
      configured: true,
      last_error: err?.message || String(err),
    });
  }
}

function probeEmail() {
  const resend = Boolean(env('RESEND_API_KEY'));
  const sendgrid = Boolean(env('SENDGRID_API_KEY'));
  if (!resend && !sendgrid) {
    return card({
      name: 'Email',
      status: 'Not configured',
      configured: false,
      note: 'Set RESEND_API_KEY or SENDGRID_API_KEY',
    });
  }
  return card({
    name: 'Email',
    status: 'Healthy',
    configured: true,
    note: resend ? 'Resend key present' : 'SendGrid key present',
  });
}

function probeOpenAi() {
  const key = env('OPENAI_API_KEY', 'PERPLEXITY_KEY', 'PERPLEXITY_API_KEY', 'VITE_PERPLEXITY_KEY');
  if (!key) {
    return card({
      name: 'OpenAI / LLM',
      status: 'Not configured',
      configured: false,
      note: 'Optional — set OPENAI_API_KEY or PERPLEXITY_KEY',
    });
  }
  return card({
    name: 'OpenAI / LLM',
    status: 'Healthy',
    configured: true,
    note: env('OPENAI_API_KEY') ? 'OpenAI key present' : 'Perplexity key present',
  });
}

function probeSchedulers() {
  const cms = getCmsLearningSchedulerStatus();
  const cio = getCioSchedulerStatus();
  const flows = getInstitutionalFlowSchedulerStatus();
  const ratios = getValuationRatiosSchedulerStatus();
  const enabled = Boolean(cms?.enabled || cio?.enabled || flows?.enabled || ratios?.enabled);
  return card({
    name: 'Scheduler',
    status: enabled ? 'Healthy' : 'Warning',
    configured: true,
    note: `CMS=${cms?.enabled ? 'on' : 'off'}; CIO=${cio?.enabled ? 'on' : 'off'}; FII/DII=${flows?.enabled ? 'on' : 'off'}; ValRatios=${ratios?.enabled ? 'on' : 'off'}`,
    detail: { cms, cio, institutional_flow: flows, valuation_ratios: ratios },
  });
}

async function probeUpstoxFlows() {
  try {
    const health = await getUpstoxHealth({});
    const flows = getInstitutionalFlowSchedulerStatus();
    const lastOk = Boolean(flows?.lastRun?.ok);
    const configured = Boolean(health?.configured);
    let status = 'Not configured';
    if (configured && health?.ok) status = 'Healthy';
    else if (configured) status = 'Warning';
    return card({
      name: 'Upstox FII/DII',
      status,
      configured,
      note: flows?.lastSuccessDate
        ? `Last EOD success ${flows.lastSuccessDate}`
        : lastOk
          ? 'Recent ingest ok'
          : 'No warehouse flow history yet — daily 18:05 IST',
      detail: { health: { ok: health?.ok, configured }, scheduler: flows },
    });
  } catch (error) {
    return card({
      name: 'Upstox FII/DII',
      status: 'Warning',
      configured: false,
      note: error.message || 'Upstox probe failed',
    });
  }
}

async function probeGrowwProvider() {
  try {
    const health = await getGrowwHealth();
    const configured = Boolean(health?.configured);
    let status = 'Not configured';
    if (configured && health?.ok) status = 'Healthy';
    else if (configured) status = 'Warning';
    return card({
      name: 'Groww',
      status,
      configured,
      note: health?.message || (configured ? 'Groww quote provider' : 'Groww not configured'),
    });
  } catch (error) {
    return card({
      name: 'Groww',
      status: 'Warning',
      configured: false,
      note: error.message || 'Groww probe failed',
    });
  }
}

async function probeIndicesSnapshot() {
  const started = Date.now();
  try {
    const origin = `http://127.0.0.1:${process.env.PORT || 5000}`;
    const response = await fetch(`${origin}/api/indices`, {
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(8_000),
    });
    const data = await response.json().catch(() => ({}));
    const count = Array.isArray(data?.indices) ? data.indices.length : 0;
    const stale = Boolean(data?.stale || data?.live_unavailable);
    let status = 'Critical';
    if (count > 0 && !stale) status = 'Healthy';
    else if (count > 0) status = 'Warning';
    return card({
      name: 'Market Indices',
      status,
      configured: true,
      latency_ms: Date.now() - started,
      note: count
        ? stale
          ? `Serving last snapshot (${count} indices) — live unavailable`
          : `${count} indices live`
        : 'No index snapshot available yet',
    });
  } catch (error) {
    return card({
      name: 'Market Indices',
      status: 'Warning',
      configured: true,
      note: error.message || 'Indices probe failed',
      latency_ms: Date.now() - started,
    });
  }
}

function probeRedis() {
  const url = env('REDIS_URL', 'UPSTASH_REDIS_REST_URL');
  if (!url) {
    return card({
      name: 'Redis',
      status: 'Not configured',
      configured: false,
      note: 'Optional cache — not required for core AGI path',
    });
  }
  return card({
    name: 'Redis',
    status: 'Healthy',
    configured: true,
    note: 'REDIS_URL present (connectivity not deep-probed)',
  });
}

function probeRenderSelf() {
  return card({
    name: 'Render',
    status: 'Healthy',
    configured: true,
    note: 'Node API process responding',
    latency_ms: 0,
  });
}

function probeGithub() {
  // Presence-only — do not call GitHub API without token scope assumptions
  const token = env('GITHUB_TOKEN', 'GH_TOKEN');
  return card({
    name: 'GitHub',
    status: token ? 'Healthy' : 'Not configured',
    configured: Boolean(token),
    note: token ? 'Deploy/token present' : 'Optional for local ops',
  });
}

function normalizeName(name = '') {
  const raw = String(name || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
  if (!raw) return '';
  if (raw.includes('indian')) return 'indianapi';
  if (raw.includes('yahoo')) return 'yahoo';
  if (raw.includes('finnhub')) return 'finnhub';
  if (raw === 'fmp' || raw.includes('financialmodeling')) return 'fmp';
  if (raw.includes('supabase')) return 'supabase';
  if (raw.includes('hostinger') || raw.includes('website')) return 'hostinger';
  if (raw.includes('render')) return 'render';
  if (raw === 'smtp' || raw.includes('email') || raw.includes('resend') || raw.includes('sendgrid')) {
    return 'email';
  }
  if (raw.includes('openai') || raw.includes('perplexity') || raw === 'llm') return 'openai';
  if (raw.includes('scheduler')) return 'scheduler';
  if (raw.includes('github')) return 'github';
  if (raw.includes('redis')) return 'redis';
  if (raw.includes('intelligence') || raw === 'engine') return 'intelligenceengine';
  return raw;
}

/**
 * Merge live Node probes over engine/soft api_status rows.
 */
export function mergeApiStatus(existing = [], probes = []) {
  const byKey = new Map();
  for (const row of existing || []) {
    byKey.set(normalizeName(row.name), { ...row, name: row.name });
  }
  for (const probe of probes || []) {
    const key = normalizeName(probe.name);
    const prev = byKey.get(key) || {};
    byKey.set(key, {
      ...prev,
      ...probe,
      name: probe.name || prev.name,
      // Prefer live probe status over soft Offline/Unknown placeholders
      status: probe.status,
      colour: probe.colour,
      note: probe.note || prev.note || null,
      last_error: probe.last_error ?? prev.last_error ?? null,
      latency: probe.latency_ms ?? probe.latency ?? prev.latency ?? null,
    });
  }
  // Stable founder-facing order
  const order = [
    'Intelligence Engine',
    'Indian API',
    'Yahoo Finance',
    'Groww',
    'Upstox FII/DII',
    'Market Indices',
    'Finnhub',
    'FMP',
    'Supabase',
    'Render',
    'Hostinger',
    'Email',
    'OpenAI / LLM',
    'Scheduler',
    'GitHub',
    'Redis',
  ];
  const ordered = [];
  const used = new Set();
  for (const name of order) {
    const key = normalizeName(name);
    if (byKey.has(key)) {
      ordered.push(byKey.get(key));
      used.add(key);
    }
  }
  for (const [key, row] of byKey.entries()) {
    if (!used.has(key)) ordered.push(row);
  }
  return ordered;
}

export async function probeMissionControlApis({ engineFetch } = {}) {
  const started = Date.now();
  const probes = await Promise.all([
    probeIntelligenceEngine(engineFetch),
    probeIndianApi(),
    probeYahoo(),
    probeGrowwProvider(),
    probeUpstoxFlows(),
    probeIndicesSnapshot(),
    probeFinnhub(),
    probeFmp(),
    probeSupabase(),
    Promise.resolve(probeRenderSelf()),
    probeHostinger(),
    Promise.resolve(probeEmail()),
    Promise.resolve(probeOpenAi()),
    Promise.resolve(probeSchedulers()),
    Promise.resolve(probeGithub()),
    Promise.resolve(probeRedis()),
  ]);

  const healthy = probes.filter((p) => p.status === 'Healthy').length;
  const notConfigured = probes.filter((p) => p.status === 'Not configured').length;
  const critical = probes.filter((p) => p.status === 'Critical' || p.status === 'Offline').length;

  return {
    ok: critical === 0,
    probed_at: new Date().toISOString(),
    latency_ms: Date.now() - started,
    healthy,
    not_configured: notConfigured,
    critical,
    total: probes.length,
    probes,
    summary: `${healthy}/${probes.length} healthy · ${notConfigured} not configured · ${critical} critical`,
    architecture_status: 'v1.0.1 LOCKED',
  };
}
