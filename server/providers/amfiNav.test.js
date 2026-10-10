import test from 'node:test';
import assert from 'node:assert/strict';
import { parseAmfiNav, createAmfiNavProvider } from './amfiNav.js';
const legacy = 'Open Ended Schemes(Equity Scheme)\nExample Mutual Fund\n100001;INF000000001;-;Example Direct Growth;25.45;24-Sep-2026';
test('parses old and new AMFI schemas, distinguishes plans, rejects missing prices and impossible dates', () => {
  const rows = parseAmfiNav(`${legacy}\n100002;INF000000002;-;Example Fund;Direct Plan;Growth Option;31.5;24-Sep-2026\n100003;-;-;Bad;N.A.;24-Sep-2026\n100004;-;-;Bad date;20;31-Feb-2026\n100005;-;-;Infinity;Infinity;24-Sep-2026`);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].price, 25.45);
  assert.equal(rows[1].price, 31.5);
  assert.equal(rows[1].name, 'Example Fund · Direct Plan · Growth Option');
  assert.equal(rows[0].asOf, '2026-09-24');
  assert.equal(rows[0].fundHouse, 'Example Mutual Fund');
});
test('deduplicates in-flight requests and retains dated stale observations after failure', async () => {
  let calls = 0, clock = 0, fail = false;
  const provider = createAmfiNavProvider({ now: () => clock, fetchImpl: async () => {
    calls++; if (fail) throw new Error('offline'); return { ok: true, text: async () => legacy };
  } });
  const [a, b] = await Promise.all([provider(), provider()]);
  assert.equal(calls, 1); assert.deepEqual(a, b);
  fail = true; clock = 4000000;
  const stale = await provider();
  assert.equal(stale.status, 'stale'); assert.equal(stale.rows[0].price, 25.45);
  assert.equal(stale.fetchedAt, a.fetchedAt);
  await provider(); assert.equal(calls, 2);
});
test('empty or malformed upstream returns unavailable, never invented NAVs', async () => {
  const provider = createAmfiNavProvider({ fetchImpl: async () => ({ ok: true, text: async () => '<html>Unavailable</html>' }) });
  const result = await provider();
  assert.equal(result.status, 'unavailable'); assert.deepEqual(result.rows, []);
});
