#!/usr/bin/env node
/**
 * Collect 13F filings from SEC EDGAR, outside the web process.
 *
 * This used to run inside the API server, starting fifteen seconds after every
 * deploy. That is wrong on four counts: it crawls whether or not anyone asked,
 * it competes with client requests for the same event loop, restarting the
 * service three times runs three crawls at once, and nothing bounded how long
 * it took or reported whether it worked.
 *
 * As a scheduled job it is none of those things. It runs when the schedule
 * says, once, with a wall-clock ceiling, and it exits non-zero when collection
 * fails so the failure is visible instead of being a line in a log nobody
 * reads. Every SEC request it makes goes through the shared limiter.
 *
 *   node server/scripts/collectInstitutionalFilings.mjs [--manager slug]
 *                                                       [--quarters 12]
 *                                                       [--max-minutes 20]
 *
 * Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY. It writes to the
 * database, so it fails loudly rather than proceeding when they are absent.
 */

import { refreshInstitutionalFilings } from '../services/institutionalHoldingsService.js';
import { secLimiterStats } from '../services/secRateLimiter.js';

const args = process.argv.slice(2);
const flag = (name, fallback) => {
  const index = args.indexOf(`--${name}`);
  return index >= 0 && args[index + 1] ? args[index + 1] : fallback;
};

const managerSlug = flag('manager', 'all');
const quarters = Number(flag('quarters', '12'));
const maxMinutes = Number(flag('max-minutes', '20'));

// The collector must be told where to write before it starts crawling. Failing
// here costs nothing; failing after 900 EDGAR requests wastes the rate budget
// and leaves the run looking like a data problem rather than a config one.
const missing = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
  .filter((name) => !process.env[name] && !process.env[`VITE_${name}`]);
if (missing.length) {
  console.error(`[collector] refusing to start: ${missing.join(' and ')} not set`);
  process.exit(78); // EX_CONFIG
}

// The automation flag gates the in-process crawler. This job is the deliberate
// caller, so it turns collection on for its own process only.
process.env.INSTITUTIONAL_AUTO_REFRESH = 'false';

const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

/**
 * A ceiling, not a timeout: it stops the job, it does not roll anything back.
 * Filings already written stay written, and the next run resumes from there.
 */
const ceiling = new Promise((_, reject) => {
  const timer = setTimeout(
    () => reject(new Error(`collection exceeded its ${maxMinutes}-minute ceiling`)),
    maxMinutes * 60_000,
  );
  timer.unref();
});

console.log(`[collector] manager=${managerSlug} quarters=${quarters} ceiling=${maxMinutes}m`);

try {
  const result = await Promise.race([
    refreshInstitutionalFilings({ managerSlug, quarters }),
    ceiling,
  ]);

  const rows = result?.results || [];
  const ok = rows.filter((row) => row.ok);
  const failed = rows.filter((row) => !row.ok);
  const limiter = secLimiterStats();

  console.log(`[collector] ${ok.length}/${rows.length} managers in ${elapsed()}s`);
  console.log(`[collector] identifiers mapped: ${result?.enrichment?.mapped ?? 0}`);
  console.log(`[collector] sec requests: ${limiter.requests}, throttled: ${limiter.throttled}, `
    + `circuit trips: ${limiter.circuit_trips}, paced wait: ${(limiter.total_wait_ms / 1000).toFixed(1)}s`);

  for (const row of failed.slice(0, 20)) {
    console.error(`[collector]   failed: ${row.slug || row.manager || '?'} - ${row.error || 'no reason given'}`);
  }

  // Being throttled at all means the pacing is set too high for this address.
  if (limiter.throttled > 0) {
    console.warn(`::warning::EDGAR throttled ${limiter.throttled} request(s). `
      + `Lower SEC_MAX_REQUESTS_PER_SECOND (currently ${limiter.max_requests_per_second}).`);
  }
  if (limiter.circuit_trips > 0) {
    console.error('::error::The SEC circuit breaker tripped. This run was cut short to protect the IP.');
    process.exit(1);
  }
  // A run where every manager failed is a failed run, not a quiet one.
  if (rows.length && !ok.length) {
    console.error('::error::No manager was collected successfully.');
    process.exit(1);
  }
  process.exit(0);
} catch (error) {
  console.error(`[collector] failed after ${elapsed()}s: ${error?.message || error}`);
  console.error(`[collector] sec requests attempted: ${secLimiterStats().requests}`);
  process.exit(1);
}
