/**
 * A process-wide pacer for SEC EDGAR requests.
 *
 * EDGAR's Fair Access policy allows ten requests a second per source, and
 * enforces it by blocking the IP - not by throttling, and not for a few
 * seconds. Losing the address costs the whole product its data source, and it
 * is not a failure any retry loop can recover from.
 *
 * The existing caller had retry with exponential backoff, which handles a 429
 * once it has already happened. It has no way to prevent one: nothing paced
 * requests, and nothing stopped two callers bursting at the same moment. This
 * module is the missing half.
 *
 * Three things it guarantees:
 *
 *   1. Requests start at most one every MIN_INTERVAL_MS, globally. Every call
 *      site queues through the same chain, so concurrency does not multiply
 *      the rate.
 *   2. A 429 or a 403 pauses every caller, not just the one that got it. The
 *      Retry-After header is honoured when present, because guessing shorter
 *      than the server asked is how a throttle becomes a block.
 *   3. Sustained rejection opens a circuit. Continuing to send after EDGAR
 *      has said no repeatedly is what turns a bad minute into a banned IP.
 *
 * The default of 5 requests a second is deliberately half the published
 * ceiling. We are one client among many behind whatever egress address the
 * host assigns, the limit is per source rather than per application, and the
 * downside of being slow is measured in minutes while the downside of being
 * blocked is measured in days.
 */

const number = (value, fallback) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

const MAX_RPS = number(process.env.SEC_MAX_REQUESTS_PER_SECOND, 5);
const MIN_INTERVAL_MS = Math.ceil(1000 / MAX_RPS);

/** Consecutive rejections before we stop sending entirely. */
const CIRCUIT_THRESHOLD = number(process.env.SEC_CIRCUIT_THRESHOLD, 8);
/** How long the circuit stays open once it trips. */
const CIRCUIT_COOLDOWN_MS = number(process.env.SEC_CIRCUIT_COOLDOWN_MS, 15 * 60_000);
/** Ceiling on a Retry-After we will honour, so a bad header cannot wedge us. */
const MAX_BACKOFF_MS = number(process.env.SEC_MAX_BACKOFF_MS, 5 * 60_000);

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const state = {
  /** Tail of the serialising promise chain. */
  chain: Promise.resolve(),
  /** Wall-clock ms after which the next request may start. */
  nextAllowedAt: 0,
  /** Consecutive throttle responses. Reset by any success. */
  consecutiveRejections: 0,
  /** Wall-clock ms until which the circuit is open. 0 when closed. */
  circuitOpenUntil: 0,
  requests: 0,
  throttled: 0,
  circuitTrips: 0,
  waitedMs: 0,
};

export class SecCircuitOpenError extends Error {
  constructor(msRemaining) {
    super(`SEC circuit is open for another ${Math.ceil(msRemaining / 1000)}s after repeated throttling`);
    this.name = 'SecCircuitOpenError';
    this.retryAfterMs = msRemaining;
  }
}

/**
 * Parse Retry-After, which is either delta-seconds or an HTTP date.
 * Returns null when absent or unusable, so the caller falls back to its own
 * backoff rather than treating a malformed header as "retry immediately".
 */
export function parseRetryAfter(header, now = Date.now()) {
  if (!header) return null;
  const raw = String(header).trim();
  if (/^\d+$/.test(raw)) return Math.min(Number(raw) * 1000, MAX_BACKOFF_MS);
  const date = Date.parse(raw);
  if (Number.isNaN(date)) return null;
  return Math.min(Math.max(date - now, 0), MAX_BACKOFF_MS);
}

/**
 * Tell the limiter EDGAR pushed back. Pauses every queued caller, because the
 * limit is per source: one caller's 429 means all of them must slow down.
 */
export function recordThrottled(retryAfterMs = null) {
  state.throttled += 1;
  state.consecutiveRejections += 1;
  const pause = retryAfterMs ?? Math.min(1000 * (2 ** Math.min(state.consecutiveRejections, 6)), MAX_BACKOFF_MS);
  state.nextAllowedAt = Math.max(state.nextAllowedAt, Date.now() + pause);
  if (state.consecutiveRejections >= CIRCUIT_THRESHOLD) {
    state.circuitOpenUntil = Date.now() + CIRCUIT_COOLDOWN_MS;
    state.circuitTrips += 1;
    state.consecutiveRejections = 0;
    console.error(`[sec-limiter] circuit open for ${Math.round(CIRCUIT_COOLDOWN_MS / 60_000)}m after ${CIRCUIT_THRESHOLD} consecutive rejections`);
  }
}

/** A request came back clean, so the run is healthy again. */
export function recordSuccess() {
  state.consecutiveRejections = 0;
}

/**
 * Run `task` under the global pace. Every EDGAR request in the process must go
 * through here; a call site that bypasses it silently doubles the real rate.
 */
export function scheduleSecRequest(task) {
  const run = state.chain.then(async () => {
    const now = Date.now();
    if (state.circuitOpenUntil > now) throw new SecCircuitOpenError(state.circuitOpenUntil - now);
    if (state.circuitOpenUntil) state.circuitOpenUntil = 0;

    const delay = state.nextAllowedAt - now;
    if (delay > 0) {
      state.waitedMs += delay;
      await wait(delay);
    }
    state.nextAllowedAt = Date.now() + MIN_INTERVAL_MS;
    state.requests += 1;
    return task();
  });
  // The chain must survive a failing task, or one rejection stops every
  // request that queues behind it for the life of the process.
  state.chain = run.then(() => undefined, () => undefined);
  return run;
}

export function secLimiterStats() {
  return {
    max_requests_per_second: MAX_RPS,
    min_interval_ms: MIN_INTERVAL_MS,
    requests: state.requests,
    throttled: state.throttled,
    circuit_trips: state.circuitTrips,
    circuit_open: state.circuitOpenUntil > Date.now(),
    total_wait_ms: state.waitedMs,
  };
}

/** Test seam. Never call this from application code. */
export function __resetSecLimiter() {
  state.chain = Promise.resolve();
  state.nextAllowedAt = 0;
  state.consecutiveRejections = 0;
  state.circuitOpenUntil = 0;
  state.requests = 0;
  state.throttled = 0;
  state.circuitTrips = 0;
  state.waitedMs = 0;
}
