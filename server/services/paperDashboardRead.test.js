import test from 'node:test';
import assert from 'node:assert/strict';
import { createPaperDashboardReader } from './paperDashboardRead.js';
const result = { ok: true, status: 200, data: { ok: true, live: { agents: {} } } };

test('concurrent reads share one bounded request; completed results are not cached', async () => {
  let resolve, calls = 0;
  const reader = createPaperDashboardReader((path, options) => {
    calls++;
    assert.equal(path, '/v1/options-lab/paper-agents');
    assert.equal(options.timeoutMs, 15000);
    assert.equal(options.circuit.failures, 0);
    return new Promise(r => { resolve = r; });
  });
  const a = reader(), b = reader();
  assert.equal(a, b);
  await Promise.resolve();
  assert.equal(calls, 1);
  resolve(result);
  assert.equal(await a, result);
  const c = reader();
  await Promise.resolve();
  assert.equal(calls, 2);
  resolve(result); await c;
});

test('failure releases request and retains a circuit isolated from other readers', async () => {
  let calls = 0, firstCircuit;
  const reader = createPaperDashboardReader(async (_, {circuit}) => {
    if (++calls === 1) { firstCircuit = circuit; circuit.failures = 1; throw new Error('timeout'); }
    assert.equal(circuit, firstCircuit);
    assert.equal(circuit.failures, 1);
    return result;
  });
  await assert.rejects(reader(), /timeout/);
  assert.equal(await reader(), result);
  await createPaperDashboardReader(async (_, {circuit}) => {
    assert.notEqual(circuit, firstCircuit);
    assert.equal(circuit.failures, 0);
    return result;
  })();
});

test('rejects malformed success and passes through upstream auth/service errors', async () => {
  await assert.rejects(createPaperDashboardReader(async () => ({ok:true,data:null}))(), /Invalid/);
  for (const status of [401,403,503]) {
    const error = {ok:false,status,data:{error:'unavailable'}};
    assert.equal(await createPaperDashboardReader(async () => error)(), error);
  }
});
