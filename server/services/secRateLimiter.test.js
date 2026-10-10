/**
 * The limiter is the only thing standing between this product and an EDGAR IP
 * block, so these are behavioural tests, not shape tests: they measure elapsed
 * time and assert the pacing actually happened.
 *
 *   node --test server/services/secRateLimiter.test.js
 */

import test from 'node:test';
import assert from 'node:assert/strict';

// Read by the module at import time. 20/s keeps the suite fast while leaving
// the interval (50ms) far enough above timer jitter to measure honestly.
process.env.SEC_MAX_REQUESTS_PER_SECOND = '20';
process.env.SEC_CIRCUIT_THRESHOLD = '3';
process.env.SEC_CIRCUIT_COOLDOWN_MS = '400';

const {
  scheduleSecRequest, recordThrottled, recordSuccess, parseRetryAfter,
  secLimiterStats, SecCircuitOpenError, __resetSecLimiter,
} = await import('./secRateLimiter.js');

const INTERVAL = 50;

test.beforeEach(() => __resetSecLimiter());

test('concurrent callers do not multiply the request rate', async () => {
  const started = Date.now();
  // Fired all at once, the way two collectors racing after a deploy would.
  await Promise.all(Array.from({ length: 5 }, () => scheduleSecRequest(async () => 'ok')));
  const elapsed = Date.now() - started;
  // Five requests at one per INTERVAL: four gaps between them.
  assert.ok(elapsed >= INTERVAL * 4 * 0.9,
    `five concurrent requests finished in ${elapsed}ms, faster than the ${INTERVAL * 4}ms floor - they were not paced`);
});

test('a single request is not delayed by the limiter', async () => {
  const started = Date.now();
  await scheduleSecRequest(async () => 'ok');
  assert.ok(Date.now() - started < INTERVAL, 'the first request should not wait');
});

test('a throttle pauses every caller, not just the one that saw it', async () => {
  recordThrottled(200);
  const started = Date.now();
  await scheduleSecRequest(async () => 'ok');
  const waited = Date.now() - started;
  assert.ok(waited >= 180, `a queued caller waited only ${waited}ms after a 200ms pushback`);
});

test('sustained rejection opens the circuit and stops sending', async () => {
  for (let i = 0; i < 3; i += 1) recordThrottled(1);
  assert.equal(secLimiterStats().circuit_open, true, 'three rejections should have tripped the circuit');
  await assert.rejects(
    () => scheduleSecRequest(async () => 'should never run'),
    SecCircuitOpenError,
    'requests must be refused while the circuit is open',
  );
});

test('the circuit closes again after its cooldown', async () => {
  for (let i = 0; i < 3; i += 1) recordThrottled(1);
  await new Promise((resolve) => setTimeout(resolve, 450));
  assert.equal(await scheduleSecRequest(async () => 'ok'), 'ok');
});

test('a success resets the run toward healthy', async () => {
  recordThrottled(1);
  recordThrottled(1);
  recordSuccess();
  recordThrottled(1); // Would be the third in a row without the reset.
  assert.equal(secLimiterStats().circuit_open, false,
    'a success between rejections must stop them counting as consecutive');
});

test('one failing request does not wedge the queue behind it', async () => {
  // The chain is shared. If a rejection propagates into it, every later
  // request inherits the failure and collection stops for the process.
  await assert.rejects(() => scheduleSecRequest(async () => { throw new Error('boom'); }));
  assert.equal(await scheduleSecRequest(async () => 'still working'), 'still working');
});

test('Retry-After is honoured in both of its formats', () => {
  const now = Date.parse('2026-01-01T00:00:00Z');
  assert.equal(parseRetryAfter('30', now), 30_000, 'delta-seconds');
  assert.equal(parseRetryAfter('Thu, 01 Jan 2026 00:00:10 GMT', now), 10_000, 'HTTP date');
  assert.equal(parseRetryAfter(null), null, 'absent header falls back to our own backoff');
  assert.equal(parseRetryAfter('not-a-date'), null, 'a malformed header must not read as retry-now');
  assert.ok(parseRetryAfter('999999', now) <= 5 * 60_000, 'an absurd value is capped so it cannot wedge us');
});

test('a past HTTP date does not produce a negative pause', () => {
  const now = Date.parse('2026-01-01T00:00:00Z');
  assert.equal(parseRetryAfter('Thu, 01 Jan 2026 00:00:00 GMT', now + 5000), 0);
});

test('the default rate is at or under half of what EDGAR permits', async () => {
  delete process.env.SEC_MAX_REQUESTS_PER_SECOND;
  // A fresh module instance, so the env default is what is under test.
  const fresh = await import(`./secRateLimiter.js?default-check`);
  assert.ok(fresh.secLimiterStats().max_requests_per_second <= 5,
    'the default must stay well below the published ten per second');
});
