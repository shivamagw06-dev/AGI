import test from 'node:test';
import assert from 'node:assert/strict';
import { AiEnablersLiveRuntime } from '../services/aiEnablersLiveRuntime.js';
import { ensureRuntime, resetRuntimeForTests, shutdownRuntime } from './indiaAiIntelligence.js';

const UNIVERSE = {
  benchmarkKey: 'NSE_INDEX|Nifty 50',
  members: [{ symbol: 'AAA', instrumentKey: 'NSE_EQ|INE000A01001', layer: 'power', subLayers: ['equipment'] }],
};

/**
 * Count how many feeds are started, without opening a socket.
 *
 * start() is where the WebSocket is opened, so counting calls to it counts
 * connections - which is the quantity Upstox caps at two per user.
 */
function countStarts(t) {
  let starts = 0;
  const original = AiEnablersLiveRuntime.prototype.start;
  AiEnablersLiveRuntime.prototype.start = async function counted() {
    starts += 1;
    // A slow start, so concurrent callers genuinely overlap inside it.
    await new Promise((resolve) => setTimeout(resolve, 30));
    return this.status();
  };
  t.after(() => { AiEnablersLiveRuntime.prototype.start = original; });
  return () => starts;
}

test('concurrent cold starts open exactly one feed', async (t) => {
  // The race this fixes: runtime was assigned only after a long await, so
  // requests arriving together at cold start each built their own runtime
  // and each opened a socket - two of them spend Upstox's entire allowance.
  const previous = process.env.UPSTOX_ACCESS_TOKEN;
  process.env.UPSTOX_ACCESS_TOKEN = 'test-token-long-enough-to-not-look-like-a-client-id';
  t.after(() => {
    if (previous === undefined) delete process.env.UPSTOX_ACCESS_TOKEN;
    else process.env.UPSTOX_ACCESS_TOKEN = previous;
    resetRuntimeForTests();
  });
  resetRuntimeForTests();
  const starts = countStarts(t);

  const runtimes = await Promise.all(
    Array.from({ length: 5 }, () => ensureRuntime({ universe: UNIVERSE })),
  );

  assert.equal(starts(), 1, `expected one feed; ${starts()} were started`);
  assert.ok(runtimes.every((one) => one === runtimes[0]), 'every caller must get the same runtime');
});

test('the one runtime that started is the one shutdown can reach', async (t) => {
  // With the race, an earlier runtime was overwritten and orphaned, so the
  // SIGTERM path could not close its socket. There must be nothing orphaned.
  const previous = process.env.UPSTOX_ACCESS_TOKEN;
  process.env.UPSTOX_ACCESS_TOKEN = 'test-token-long-enough-to-not-look-like-a-client-id';
  t.after(() => {
    if (previous === undefined) delete process.env.UPSTOX_ACCESS_TOKEN;
    else process.env.UPSTOX_ACCESS_TOKEN = previous;
    resetRuntimeForTests();
  });
  resetRuntimeForTests();
  countStarts(t);

  const [first] = await Promise.all([ensureRuntime({ universe: UNIVERSE }), ensureRuntime({ universe: UNIVERSE })]);
  let stopped = 0;
  first.stop = async () => { stopped += 1; };
  const result = await shutdownRuntime();
  assert.equal(result.stopped, true);
  assert.equal(stopped, 1);
});

test('a failed start does not wedge every later request', async (t) => {
  // The in-flight promise is cleared on failure, so the next request tries
  // again instead of receiving the same rejection forever.
  const previous = process.env.UPSTOX_ACCESS_TOKEN;
  delete process.env.UPSTOX_ACCESS_TOKEN;
  t.after(() => {
    if (previous !== undefined) process.env.UPSTOX_ACCESS_TOKEN = previous;
    resetRuntimeForTests();
  });
  resetRuntimeForTests();

  await assert.rejects(ensureRuntime({ universe: UNIVERSE }), /not configured/);
  process.env.UPSTOX_ACCESS_TOKEN = 'test-token-long-enough-to-not-look-like-a-client-id';
  countStarts(t);
  const recovered = await ensureRuntime({ universe: UNIVERSE });
  assert.ok(recovered, 'a later request should be able to start the runtime');
});
