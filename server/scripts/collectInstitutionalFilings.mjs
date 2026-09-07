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

import { hostname } from 'node:os';
import { refreshInstitutionalFilings } from '../services/institutionalHoldingsService.js';
import { secLimiterStats } from '../services/secRateLimiter.js';
import {
  startRun, finishRun, progressRun, deriveStatus, summariseRefresh, nextScheduledAt,
} from '../services/institutionalCollectionRuns.js';

const args = process.argv.slice(2);
const flag = (name, fallback) => {
  const index = args.indexOf(`--${name}`);
  return index >= 0 && args[index + 1] ? args[index + 1] : fallback;
};

const managerSlug = flag('manager', 'all');
const quarters = Number(flag('quarters', '12'));
const maxMinutes = Number(flag('max-minutes', '50'));
const trigger = flag('trigger', 'schedule');
// Passed in rather than hardcoded, so the record reflects the schedule that
// actually invoked this run instead of one this file believes in.
const schedule = flag('schedule', process.env.COLLECTION_SCHEDULE || null);

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

console.log(`[collector] manager=${managerSlug} quarters=${quarters} ceiling=${maxMinutes}m trigger=${trigger}`);

// Opened before any EDGAR request. A run that dies mid-crawl then leaves a row
// stuck in 'running', which an operator can see; a record written only at the
// end would leave nothing, and silence looks exactly like success.
const runId = await startRun({
  trigger,
  host: process.env.RENDER_SERVICE_NAME || hostname(),
  managerSlug,
  quarters,
  scheduleExpression: schedule,
});
if (runId) console.log(`[collector] run ${runId}`);

let aborted = false;
let failureMessage = null;
let refresh = null;

// Progress is accumulated as each manager finishes, not read from the final
// result. Hitting the ceiling abandons that result, and the previous run
// reported "managers: 0/0, filings: 0, holdings rows: 0" for work that was
// already committed - a record that says nothing happened is worse than no
// record, because someone will believe it.
const completed = [];
let roster = 0;

// Written as each manager finishes, not only at the end.
//
// A hard stop - the platform's runtime limit, an out-of-memory kill, a deploy
// replacing the container - never reaches the code below, so the row stayed as
// startRun created it: running, zero managers, no finish time. That zero is
// the column default rather than a measurement, and it reads as a collector
// that crawled nothing. Both of the runs that were investigated looked like
// that, and neither could be told apart from one that never started.
let lastProgressAt = 0;
async function reportProgress(force = false) {
  if (!runId) return;
  const now = Date.now();
  if (!force && now - lastProgressAt < 15_000) return;
  lastProgressAt = now;
  const done = summariseRefresh({ results: completed }, roster);
  await progressRun(runId, {
    // What has actually reported back, not the roster. A row claiming 51
    // attempted while three have finished is the same lie in the other
    // direction.
    managersAttempted: done.managersAttempted,
    managersSucceeded: done.managersSucceeded,
    filingsIngested: done.filingsIngested,
    holdingsRows: done.holdingsRows,
  });
}

// Render sends SIGTERM before it kills a job, so there is a moment to record
// where the crawl actually got to. Filings already written stay written; this
// only stops the record from claiming nothing happened.
let terminating = false;
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.on(signal, async () => {
    if (terminating) return;
    terminating = true;
    console.error(`[collector] ${signal} after ${elapsed()}s with ${completed.length}/${roster} manager(s) done`);
    const done = summariseRefresh({ results: completed }, roster);
    const stats = secLimiterStats();
    await finishRun(runId, {
      ...done,
      status: 'aborted',
      error: `terminated by ${signal} after ${elapsed()}s`,
      // Named as finishRun expects. The limiter reports requests/throttled;
      // spreading it raw would silently record zeros for all of them.
      secRequests: stats.requests,
      secThrottled: stats.throttled,
      secThrottlePauseMs: stats.throttle_pause_ms,
      secPacedWaitMs: stats.total_wait_ms,
      secCircuitTrips: stats.circuit_trips,
    });
    process.exit(1);
  });
}

try {
  refresh = await Promise.race([
    refreshInstitutionalFilings({
      managerSlug,
      quarters,
      onManagerDone: (result) => { completed.push(result); void reportProgress(); },
      onRoster: (count) => { roster = count; void reportProgress(true); },
    }),
    ceiling,
  ]);
} catch (error) {
  failureMessage = String(error?.message || error);
  aborted = /ceiling/.test(failureMessage);
  console.error(`[collector] failed after ${elapsed()}s: ${failureMessage}`);
}

// Prefer the complete result; fall back to what was observed finishing.
const work = summariseRefresh(refresh || { results: completed }, roster);
if (!refresh && completed.length) {
  console.log(`[collector] cut short, but ${completed.length} manager(s) completed and were written`);
}
const limiter = secLimiterStats();
const status = deriveStatus({
  attempted: work.managersAttempted,
  succeeded: work.managersSucceeded,
  error: failureMessage,
  aborted,
  roster: work.managersInRoster,
});

// The circuit tripping means the run was cut short to protect the address, so
// it is not a success however many managers happened to complete first.
const circuitTripped = limiter.circuit_trips > 0;
const finalStatus = circuitTripped && status === 'success' ? 'partial' : status;

await finishRun(runId, {
  status: finalStatus,
  secRequests: limiter.requests,
  secThrottled: limiter.throttled,
  secThrottlePauseMs: limiter.throttle_pause_ms,
  secPacedWaitMs: limiter.total_wait_ms,
  secCircuitTrips: limiter.circuit_trips,
  ...work,
  retryState: circuitTripped || (work.postProcessingErrors || []).length
    ? {
      ...(circuitTripped ? { circuit_tripped: true, note: 'run cut short to protect the source address' } : {}),
      ...((work.postProcessingErrors || []).length
        ? { post_processing_errors: work.postProcessingErrors }
        : {}),
    }
    : null,
  error: failureMessage,
});

console.log(`[collector] status=${finalStatus} in ${elapsed()}s`);
console.log(`[collector] managers: ${work.managersSucceeded}/${work.managersInRoster || work.managersAttempted}`
  + `${work.managersInRoster && work.managersSucceeded < work.managersInRoster ? ` (${work.managersInRoster - work.managersSucceeded} not reached)` : ''}, `
  + `filings: ${work.filingsIngested}, holdings rows: ${work.holdingsRows}, `
  + `amendments: ${work.amendmentsDetected}`);
console.log(`[collector] sec requests: ${limiter.requests}, throttled: ${limiter.throttled}, `
  + `throttle pause: ${(limiter.throttle_pause_ms / 1000).toFixed(1)}s, `
  + `paced wait: ${(limiter.total_wait_ms / 1000).toFixed(1)}s, `
  + `circuit trips: ${limiter.circuit_trips}`);
if (schedule) console.log(`[collector] next scheduled run: ${nextScheduledAt(schedule) || 'unknown'}`);

for (const problem of work.postProcessingErrors || []) {
  console.warn(`[collector] post-processing: ${problem}`);
}

for (const failure of work.failures.slice(0, 20)) {
  console.error(`[collector]   failed: ${failure.manager} - ${failure.error}`);
}

if (limiter.throttled > 0) {
  console.warn(`[collector] WARNING: EDGAR throttled ${limiter.throttled} request(s). `
    + `Lower SEC_MAX_REQUESTS_PER_SECOND (currently ${limiter.max_requests_per_second}).`);
}
if (circuitTripped) {
  console.error('[collector] ERROR: the SEC circuit breaker tripped; this run was cut short to protect the IP.');
}

process.exit(['success', 'partial'].includes(finalStatus) ? 0 : 1);
