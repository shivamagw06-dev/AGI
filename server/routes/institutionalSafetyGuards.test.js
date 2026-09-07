/**
 * The Institutional Holdings safety release, asserted.
 *
 * Every check here exists because the audit found the opposite state in
 * production. They are written against the source text rather than a live
 * server because the invariant is structural - a route either carries the
 * guard or it does not - and because that lets them run with no Supabase
 * credentials, in CI, on every push.
 *
 *   node --test server/routes/institutionalSafetyGuards.test.js
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const routes = readFileSync(new URL('./institutionalHoldings.js', import.meta.url), 'utf8');
const holdings = readFileSync(new URL('../services/institutionalHoldingsService.js', import.meta.url), 'utf8');
const research = readFileSync(new URL('../services/institutionalResearchLayerService.js', import.meta.url), 'utf8');
const layer = readFileSync(new URL('../services/institutionalResearchLayerService.js', import.meta.url), 'utf8');

/**
 * Routes that must never answer an unauthenticated caller.
 *
 * The first four each page the entire holdings table; measured against
 * production they exceed 120 seconds on 72,401 rows, so an open one is a
 * free denial-of-service primitive as well as a data-quality problem.
 * /backtests writes rows and publishes return figures.
 */
const ADMIN_ONLY = [
  ['get', '/combined-holdings'],
  ['get', '/screener'],
  ['get', '/heat-map'],
  ['get', '/fund-performance'],
  ['post', '/backtests'],
];

for (const [method, path] of ADMIN_ONLY) {
  test(`${method.toUpperCase()} ${path} requires admin`, () => {
    const declaration = new RegExp(
      `router\\.${method}\\('${path.replace('/', '\\/')}',\\s*([A-Za-z_$][\\w$]*)`,
    ).exec(routes);
    assert.ok(declaration, `${method.toUpperCase()} ${path} is not registered at all`);
    assert.equal(
      declaration[1], 'requireAdmin',
      `${method.toUpperCase()} ${path} is reachable without authentication`,
    );
  });
}

test('requireAdmin rejects a caller with no token before it calls out to Supabase', () => {
  const body = /async function requireAdmin[\s\S]*?\n}/.exec(routes)?.[0];
  assert.ok(body, 'requireAdmin is gone');
  const rejects = body.indexOf('!token');
  const fetches = body.indexOf('fetch(');
  assert.ok(rejects !== -1 && rejects < fetches,
    'requireAdmin must reject an empty token before making a network call');
  assert.match(body, /status\(403\)/, 'a non-admin user must get 403, not be waved through');
});

/**
 * The crawler.
 *
 * It used to default to on, so every web-process deploy began an unthrottled
 * EDGAR crawl. Both automations must now require an explicit opt-in, which
 * means the absent-variable case has to evaluate to "do not run".
 */
const AUTOMATIONS = [
  ['institutional holdings', holdings, 'INSTITUTIONAL_AUTO_REFRESH'],
  ['research layer', research, 'INSTITUTIONAL_RESEARCH_AUTOMATION_ENABLED'],
];

for (const [name, source, flag] of AUTOMATIONS) {
  test(`the ${name} crawler does not start unless ${flag} is set`, () => {
    const guard = new RegExp(`process\\.env\\.${flag}\\s*\\|\\|\\s*'([^']*)'\\)\\.toLowerCase\\(\\)\\s*(===|!==)\\s*'([^']*)'`)
      .exec(source);
    assert.ok(guard, `${flag} guard not found in the ${name} service`);
    const [, fallback, operator, compared] = guard;
    // Reproduce the guard against an unset variable. It must return early.
    const startsWhenUnset = operator === '===' ? !(fallback === compared) : !(fallback !== compared);
    assert.equal(startsWhenUnset, false,
      `with ${flag} unset the ${name} crawler still starts - the default must be off`);
  });
}

test('the backtester is not publishing returns while its entry rule is wrong', () => {
  // The audit found entry on the acceptance date itself: `row.price_date >= date`
  // takes the same session's close, which the manager could not have traded.
  // This test fails the moment someone re-enables the lab without fixing it.
  const lookAhead = /price_date\s*>=\s*date/.test(layer);
  const ui = readFileSync(
    new URL('../../src/components/Research/InstitutionalResearchLayer.jsx', import.meta.url), 'utf8');
  const labIsLive = /runInstitutionalBacktest\s*\(/.test(ui);
  assert.ok(!(lookAhead && labIsLive),
    'the Performance lab is calling the backtester while the acceptance-date entry bug is still present');
});
