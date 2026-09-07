#!/usr/bin/env node
/**
 * Hit every registered Institutional Holdings endpoint and reject anything that
 * is not a real answer.
 *
 * The point is the rejection, not the request. A missing route on this app used
 * to return HTTP 200 carrying {"error":"upstream_rate_limited"} - the wildcard
 * IndianAPI forwarder answering a question about AGI with a third party's
 * throttle - so four endpoints that did not exist looked identical to a working
 * service under load. Checking the status code alone would have passed.
 *
 * So a pass here requires three things: a 2xx, a JSON body that is not the
 * rate-limit shell, and at least one field the endpoint is supposed to return.
 *
 *   node server/scripts/smokeInstitutionalRoutes.mjs [--base URL] [--json]
 *
 * Exit code 0 when every route passes, 1 otherwise, so it can gate a deploy.
 */

const args = process.argv.slice(2);
const baseArg = args.indexOf('--base');
const BASE = (baseArg >= 0 ? args[baseArg + 1] : process.env.SMOKE_BASE_URL
  || 'https://finance-news-backend-19i5.onrender.com').replace(/\/$/, '');
const asJson = args.includes('--json');
const TIMEOUT_MS = 120_000;

/**
 * Every registered Institutional Holdings route, and what a caller with no
 * credentials must get back.
 *
 * The four admin-only entries are the point of this list. Each pages the whole
 * holdings table - over 120 seconds against production's 72,401 rows - and each
 * reports on data whose price coverage is still 0%, so an anonymous 200 from any
 * of them is a defect, not a success. `expect` names a field that proves the
 * route answered with its own payload; it only applies to a public route.
 */
const ROUTES = [
  { path: '/api/institutional-holdings/overview', status: 200, expect: null },
  { path: '/api/institutional-holdings/decision-intelligence', status: 200, expect: null },
  { path: '/api/institutional-holdings/research-layer', status: 200, expect: 'readiness' },
  { path: '/api/institutional-holdings/combined-holdings?limit=5', status: 401 },
  { path: '/api/institutional-holdings/screener?limit=5', status: 401 },
  { path: '/api/institutional-holdings/heat-map?limit=5', status: 401 },
  { path: '/api/institutional-holdings/fund-performance', status: 401 },
  { path: '/api/institutional-holdings/backtests', method: 'POST', status: 401 },
];

/**
 * A path that must NOT exist. It proves the wildcard forwarder is no longer
 * disguising a 404, which is the failure this whole script exists to catch.
 */
const MUST_404 = '/api/institutional-holdings/__smoke_missing_route__';

function isRateLimitShell(body) {
  return Boolean(body)
    && typeof body === 'object'
    && (body.error === 'upstream_rate_limited' || body.upstream_status === 429);
}

async function hit(path, method = 'GET') {
  const started = Date.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(`${BASE}${path}`, {
      method,
      headers: { Accept: 'application/json', ...(method === 'POST' ? { 'Content-Type': 'application/json' } : {}) },
      body: method === 'POST' ? '{}' : undefined,
      signal: controller.signal,
    });
    const text = await response.text();
    let body = null;
    try { body = text ? JSON.parse(text) : null; } catch { body = null; }
    return {
      status: response.status,
      ms: Date.now() - started,
      bytes: text.length,
      body,
      parseable: body !== null,
    };
  } catch (error) {
    return {
      status: 0,
      ms: Date.now() - started,
      bytes: 0,
      body: null,
      parseable: false,
      networkError: error?.name === 'AbortError' ? 'timeout' : String(error?.message || error),
    };
  } finally {
    clearTimeout(timer);
  }
}

function judge(route, result) {
  if (result.status === 0) return `no response (${result.networkError})`;
  // An admin-only route answering an anonymous caller is the failure, whatever
  // it says. 403 is equally acceptable: both mean the guard held.
  if (route.status === 401) {
    return [401, 403].includes(result.status)
      ? null
      : `expected the admin guard to reject this, got HTTP ${result.status}`;
  }
  if (result.status < 200 || result.status >= 300) return `HTTP ${result.status}`;
  if (!result.parseable) return 'response was not JSON';
  // The whole reason this script exists.
  if (isRateLimitShell(result.body)) {
    return 'returned the upstream_rate_limited shell - this route is almost certainly not registered';
  }
  if (result.body?.ok === false) return `body reported ok:false (${result.body.error || 'no reason'})`;
  if (route.expect && !(route.expect in result.body)) {
    return `body is missing "${route.expect}", so the route answered but not with its own payload`;
  }
  return null;
}

const results = [];
for (const route of ROUTES) {
  const result = await hit(route.path, route.method);
  const failure = judge(route, result);
  results.push({ path: route.path, status: result.status, ms: result.ms, bytes: result.bytes, failure });
}

// The negative case: a route that does not exist must say so.
const missing = await hit(MUST_404);
const missingFailure = missing.status === 404
  ? null
  : `expected 404, got HTTP ${missing.status}${isRateLimitShell(missing.body) ? ' with the rate-limit shell' : ''}`;
results.push({ path: `${MUST_404} (must 404)`, status: missing.status, ms: missing.ms, bytes: missing.bytes, failure: missingFailure });

const failed = results.filter((r) => r.failure);

if (asJson) {
  console.log(JSON.stringify({ base: BASE, passed: results.length - failed.length, failed: failed.length, results }, null, 2));
} else {
  console.log(`\n  Institutional Holdings route smoke — ${BASE}\n`);
  for (const r of results) {
    const mark = r.failure ? 'FAIL' : 'pass';
    console.log(`  ${mark}  ${String(r.status).padEnd(3)} ${String(r.ms + 'ms').padStart(7)} ${String(r.bytes + 'B').padStart(9)}  ${r.path}`);
    if (r.failure) console.log(`        ${r.failure}`);
  }
  console.log(`\n  ${results.length - failed.length}/${results.length} passed\n`);
}

process.exit(failed.length ? 1 : 0);
