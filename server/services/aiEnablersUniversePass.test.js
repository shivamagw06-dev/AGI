import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PacedLimiter, parseEquityList, publicRow, renominate, runUniversePass, summariseUniversePass,
} from './aiEnablersUniversePass.js';

const CSV = [
  'SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE',
  'POWERINDIA,Hitachi Energy India Limited,EQ,19-MAR-2020,2,1,INE07Y701011,2',
  '"ACME","Acme, Holdings Limited",BE,01-JAN-2020,10,1,INE000Z01011,10',
  'NOISIN,No Isin Limited,EQ,01-JAN-2020,10,1,,10',
  'POWERINDIA,Duplicate row,EQ,19-MAR-2020,2,1,INE07Y701011,2',
].join('\n');

test('the equity list is read with trimmed headers, quoted commas and no duplicates', () => {
  const companies = parseEquityList(CSV);
  assert.deepEqual(companies.map((one) => one.symbol), ['POWERINDIA', 'ACME', 'NOISIN']);
  assert.equal(companies[1].name, 'Acme, Holdings Limited');
  assert.equal(companies[1].series, 'BE');
  assert.equal(companies[0].isin, 'INE07Y701011');
  assert.equal(companies[2].isin, null);
  assert.throws(() => parseEquityList('A,B\n1,2'), /header not recognised/);
  const quoted = parseEquityList(`${CSV.split('\n')[0]}\nQQ,"The ""Q"" Company, Ltd",EQ,x,1,1,INE000Q01011,1`);
  assert.equal(quoted[0].name, 'The "Q" Company, Ltd');
});

/* ── the limiter, on a fake clock ─────────────────────────────────────── */

const fakeClock = () => {
  let t = 0;
  return { now: () => t, sleep: async (ms) => { t += ms; }, advance: (ms) => { t += ms; } };
};

test('the limiter holds calls to the per-minute limit', async () => {
  const clock = fakeClock();
  const limiter = new PacedLimiter({ perMinute: 3, perWindow: 100, now: clock.now, sleep: clock.sleep });
  const times = [];
  for (let i = 0; i < 7; i += 1) { await limiter.take(); times.push(clock.now()); }
  assert.deepEqual(times, [0, 0, 0, 60_000, 60_000, 60_000, 120_000]);
});

test('the limiter holds calls to the long-window limit too', async () => {
  const clock = fakeClock();
  const limiter = new PacedLimiter({ perMinute: 100, perWindow: 4, windowMs: 600_000, now: clock.now, sleep: clock.sleep });
  for (let i = 0; i < 4; i += 1) await limiter.take();
  await limiter.take();
  assert.equal(clock.now(), 600_000);
});

/* ── the run ──────────────────────────────────────────────────────────── */

const COMPANIES = [
  { symbol: 'GRID', name: 'Grid Co', series: 'EQ', isin: 'INE000A01001' },
  { symbol: 'SOAP', name: 'Soap Co', series: 'EQ', isin: 'INE000A01002' },
  { symbol: 'BLANK', name: 'Blank Co', series: 'EQ', isin: 'INE000A01003' },
  { symbol: 'GONE', name: 'Gone Co', series: 'EQ', isin: 'INE000A01004' },
  { symbol: 'NOID', name: 'No Id Co', series: 'BE', isin: null },
];
const PROFILES = {
  INE000A01001: { data: { sector: 'Capital Goods', company_profile: 'Makes switchgear and power transformers.' } },
  INE000A01002: { data: { sector: 'FMCG', company_profile: 'Makes soap and detergents.' } },
  INE000A01003: { data: { sector: 'Textiles', company_profile: '' } },
};
const noWait = { take: async () => {} };

const run = async (overrides = {}) => {
  const saved = [];
  const result = await runUniversePass({
    companies: COMPANIES,
    runId: 'r1',
    limiter: noWait,
    sleep: async () => {},
    now: () => Date.parse('2026-09-18T06:00:00Z'),
    fetchProfile: async (isin) => {
      if (isin === 'INE000A01004') { const e = new Error('Not Found'); e.status = 404; throw e; }
      return PROFILES[isin];
    },
    save: async (rows) => { saved.push(...rows); },
    batchSize: 2,
    ...overrides,
  });
  return { saved, result };
};

test('every company gets exactly one recorded outcome', async () => {
  const { saved } = await run();
  assert.deepEqual(
    Object.fromEntries(saved.map((one) => [one.symbol, one.disposition])),
    { GRID: 'NOMINATED', SOAP: 'NOT_NOMINATED', BLANK: 'NO_PROFILE', GONE: 'NO_PROFILE', NOID: 'NO_ISIN' },
  );
  const grid = saved.find((one) => one.symbol === 'GRID');
  assert.deepEqual(grid.nomination.map((one) => one.subLayer), ['power/equipment']);
  // Every row carries every key, so an upsert never nulls a column by omission.
  const keys = JSON.stringify(Object.keys(saved[0]).sort());
  assert.ok(saved.every((one) => JSON.stringify(Object.keys(one).sort()) === keys));
});

test('an interrupted run resumes without refetching what it stored', async () => {
  const fetched = [];
  const { saved } = await run({
    done: new Set(['GRID', 'SOAP']),
    fetchProfile: async (isin) => { fetched.push(isin); return PROFILES[isin] || { data: null }; },
  });
  assert.deepEqual(saved.map((one) => one.symbol), ['BLANK', 'GONE', 'NOID']);
  assert.ok(!fetched.includes('INE000A01001'));
});

test('a rate limit is waited out, not recorded against the company', async () => {
  let calls = 0;
  const waits = [];
  const { saved } = await run({
    companies: [COMPANIES[0]],
    sleep: async (ms) => { waits.push(ms); },
    backoffMs: 1_000,
    fetchProfile: async (isin) => {
      calls += 1;
      if (calls <= 2) { const e = new Error('Too Many Requests'); e.status = 429; throw e; }
      return PROFILES[isin];
    },
  });
  assert.equal(saved[0].disposition, 'NOMINATED');
  assert.deepEqual(waits, [1_000, 2_000]);
});

test('a rate limit that never clears is a recorded failure, not a non-nomination', async () => {
  const { saved } = await run({
    companies: [COMPANIES[0]],
    maxRetries: 2,
    fetchProfile: async () => { const e = new Error('Too Many Requests'); e.status = 429; throw e; },
  });
  assert.equal(saved[0].disposition, 'PROFILE_ERROR');
  assert.equal(saved[0].error, 'RATE_LIMITED_AFTER_RETRIES');
});

test('one broken company does not stop the run', async () => {
  const { saved } = await run({
    fetchProfile: async (isin) => {
      if (isin === 'INE000A01001') throw new Error('socket hang up');
      return PROFILES[isin] || { data: null };
    },
  });
  assert.equal(saved.find((one) => one.symbol === 'GRID').disposition, 'PROFILE_ERROR');
  assert.equal(saved.find((one) => one.symbol === 'SOAP').disposition, 'NOT_NOMINATED');
  assert.equal(saved.length, 5);
});

test('an authorisation failure stops the run and keeps what was already fetched', async () => {
  const saved = [];
  let calls = 0;
  await assert.rejects(runUniversePass({
    companies: COMPANIES,
    runId: 'r1',
    limiter: noWait,
    batchSize: 50,
    fetchProfile: async (isin) => {
      calls += 1;
      if (calls === 2) { const e = new Error('Unauthorized'); e.status = 401; throw e; }
      return PROFILES[isin];
    },
    save: async (rows) => { saved.push(...rows); },
  }), (error) => error.code === 'UPSTOX_AUTH');
  assert.equal(calls, 2);
  assert.deepEqual(saved.map((one) => one.symbol), ['GRID']);
});

/* ── the summary ──────────────────────────────────────────────────────── */

test('coverage excludes companies without an ISIN, and a thin run is DEGRADED', async () => {
  const { saved } = await run();
  const summary = summariseUniversePass(saved, { listed: 5 });
  assert.equal(summary.addressable, 4);
  assert.equal(summary.examined, 2);
  assert.equal(summary.coverage, 0.5);
  assert.equal(summary.status, 'DEGRADED');
  assert.equal(summary.complete, true);
  assert.deepEqual(summary.bySubLayer, { 'power/equipment': 1 });
});

test('a known qualifier the pass did not nominate is reported as a miss', async () => {
  const { saved } = await run();
  const summary = summariseUniversePass(saved, {
    reference: [
      { symbol: 'GRID', kind: 'member' },
      { symbol: 'SOAP', kind: 'member' },
      { symbol: 'ELSEWHERE', kind: 'candidate' },
    ],
  });
  assert.equal(summary.recall.nominated, 1);
  assert.deepEqual(summary.recall.missed.map((one) => [one.symbol, one.disposition]), [
    ['SOAP', 'NOT_NOMINATED'],
    ['ELSEWHERE', 'NOT_IN_LIST'],
  ]);
});

/* ── the SME board, stored descriptions, re-scoring ───────────────────── */

test('the SME list is read with underscore headers and tagged by board', () => {
  const sme = parseEquityList([
    'SYMBOL,NAME_OF_COMPANY,SERIES,DATE_OF_LISTING,PAID_UP_VALUE,MARKET_LOT,ISIN_NUMBER,FACE_VALUE',
    'ESDS,ESDS Software Solution Limited,SM,01-JAN-2024,10,1000,INE08YJ01011,10',
  ].join('\n'), { board: 'sme' });
  assert.deepEqual(sme, [{ symbol: 'ESDS', name: 'ESDS Software Solution Limited', series: 'SM', isin: 'INE08YJ01011', board: 'sme' }]);
  assert.equal(parseEquityList(CSV)[0].board, 'main');
});

test('the description is stored with the row but never served', async () => {
  const { saved } = await run();
  const grid = saved.find((one) => one.symbol === 'GRID');
  assert.equal(grid.description, 'Makes switchgear and power transformers.');
  assert.equal(grid.description_chars, grid.description.length);
  const served = publicRow(grid);
  assert.ok(!('description' in served));
  assert.deepEqual(served.priority, { tier: 1, subLayers: ['power/equipment'] });
  assert.equal(publicRow(saved.find((one) => one.symbol === 'SOAP')).priority, null);
});

test('re-scoring changes only examined rows whose outcome moved', async () => {
  const { saved } = await run();
  const stale = saved.map((one) => (one.symbol === 'GRID' ? { ...one, disposition: 'NOT_NOMINATED', nomination: null } : one));
  const changed = renominate(stale);
  assert.deepEqual(changed.map((one) => [one.symbol, one.disposition]), [['GRID', 'NOMINATED']]);
  // Unexamined rows are never touched, even with a description present.
  assert.deepEqual(renominate([{ ...saved[0], disposition: 'PROFILE_ERROR' }]), []);
});

test('the summary counts reading tiers and boards', async () => {
  const { saved } = await run();
  const rows = saved.map((one) => (one.symbol === 'GRID' ? { ...one, sector: 'Electric Equipment' } : one));
  const summary = summariseUniversePass([...rows, { ...rows[1], symbol: 'SMEX', board: 'sme' }]);
  assert.deepEqual(summary.byTier, { 1: 1, 2: 0, 3: 0 });
  assert.deepEqual(summary.byBoard, { main: { listed: 5, nominated: 1 }, sme: { listed: 1, nominated: 0 } });
});
