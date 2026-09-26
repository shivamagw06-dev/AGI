import test from 'node:test';
import assert from 'node:assert/strict';
import { rupeesCr, summariseIntelligence, summaryText } from './indiaAiSummary.js';

const member = (symbol, layer, sub, extra = {}) => ({
  symbol, layer, subLayers: [sub], attribution: 'NOT_ATTRIBUTABLE', membershipStart: '2026-09-17',
  admittedOn: [{ kind: 'order' }], ...extra,
});
const universe = {
  members: [
    member('AAA', 'power', 'equipment', { admittedOn: [{ kind: 'order' }, { kind: 'capex' }], attribution: 'SEGMENT_REPORTED' }),
    member('BBB', 'data_centre', 'operator', { discoveredVia: 'EXTERNAL_LEAD_2026_09_18', membershipStart: '2026-09-18' }),
  ],
  candidates: [{ symbol: 'CCC', pendingVerification: true }, { symbol: 'DDD' }],
  excluded: [{ symbol: 'EEE' }],
};
const section = (sections, id) => sections.find((one) => one.id === id);
const texts = (one) => [...one.lines.map((l) => l.text), ...one.caveats].join('\n');

const live = (quality = {}) => ({
  at: '2026-09-18T06:00:00Z',
  index: {
    status: 'ok', return_pp: 1.5, priced: 2, total: 2,
    relative: { benchmark_return_pp: 0.5, excess_pp: 1 },
    breadth: { advancing: 1 },
    contributions: { byLayer: [{ layer: 'power', contribution_pp: 2 }, { layer: 'data_centre', contribution_pp: -0.5 }], byName: [] },
    priceBreak: [], fallback: [],
  },
  quality,
});

test('the basket section counts filings by kind and names what is empty and pending', () => {
  const text = texts(section(summariseIntelligence({ universe }), 'basket'));
  assert.match(text, /2 companies admitted on 3 filings of their own: 2 signed orders and 1 committed capex filing/);
  assert.match(text, /2 of 10 sub-layers are filled/);
  assert.match(text, /1 came from AGI's own screen and 1 were first read as leads/);
  assert.match(text, /2 candidates are held back \(CCC pending verification\), and 1 excluded/);
  assert.match(text, /1 reports data-centre revenue as a segment; no filing sizes it for 1/);
});

test('a missing source leaves its section pending, not guessed', () => {
  const sections = summariseIntelligence({ universe });
  for (const id of ['session', 'record', 'size', 'intensity', 'tradability']) {
    assert.ok(section(sections, id).pending, id);
    assert.deepEqual(section(sections, id).lines, []);
  }
});

test('mid-session, the move is "today" and carries no last-trade note', () => {
  const one = section(summariseIntelligence({ universe, live: live({ closed: false }) }), 'session');
  assert.equal(one.title, 'Today');
  assert.match(one.lines[0].text, /^Today so far the basket rose 1\.50% against Nifty 50's \+0\.50%, ahead by 1\.00pp; 1 of 2 members rose\./);
  assert.match(one.lines[1].text, /Power \+2\.00pp, Data Centers −0\.50pp/);
  assert.ok(!one.caveats.some((c) => /last trade/.test(c)));
});

test('after the close, the last-trade and same-day admission notes appear', () => {
  const one = section(summariseIntelligence({
    universe, live: live({ closed: true, session_last: 2, last_trade_at: '2026-09-18T10:29:59Z', from_candles: 1 }),
  }), 'session');
  assert.equal(one.title, 'Last session');
  assert.match(one.caveats[0], /latest 15:59 IST; NSE's official close may differ slightly; 1 from the session's final minute candle/);
  assert.match(one.caveats[1], /^1 of these members were admitted on 18 Sept 2026/);
});

test('an unpriced basket says so and reports no move', () => {
  const unpriced = { index: { status: 'insufficient_coverage', reason: '0 of 27 members priced' } };
  const one = section(summariseIntelligence({ live: unpriced }), 'session');
  assert.deepEqual(one.lines.map((l) => l.text), ['The basket is not priced right now: 0 of 27 members priced.']);
});

test('the record reports its sessions, or says it has none yet', () => {
  const empty = section(summariseIntelligence({ history: { base: '2026-09-17', points: [{ date: '2026-09-17', basket: 100, benchmark: 100 }] } }), 'record');
  assert.match(empty.lines[0].text, /has no completed session yet/);
  const two = section(summariseIntelligence({ history: { base: '2026-09-17', points: [
    { date: '2026-09-17', basket: 100, benchmark: 100 },
    { date: '2026-09-18', basket: 101.5, benchmark: 100.25, members: 7, missing: ['X'], excluded: [] },
  ] } }), 'record');
  assert.match(two.lines[0].text, /over 1 session: the basket \+1\.50%, Nifty 50 \+0\.25%, a gap of \+1\.25pp\. 7 members/);
  assert.deepEqual(two.caveats, ['No close for X in the last session.']);
});

test('concentration explains equal weight only when two names dominate', () => {
  const mv = (...values) => ({
    ok: true, closeDate: '2026-09-17',
    byLayer: { totalCr: values.reduce((a, b) => a + b, 0), groups: [{ key: 'power', share: 1 }], leftOut: [] },
    rows: values.map((v, i) => ({ symbol: 'ABCDEFGH'[i], marketValueCr: v })),
  });
  const heavy = texts(section(summariseIntelligence({ marketValue: mv(300_000, 200_000, 100_000) }), 'size'));
  assert.match(heavy, /₹6\.0 lakh cr/);
  assert.match(heavy, /A and B are 83% of it, which is why the basket is equal-weighted/);
  assert.match(heavy, /whole-company value/);
  const light = texts(section(summariseIntelligence({ marketValue: mv(100, 100, 100, 100, 100, 100) }), 'size'));
  assert.doesNotMatch(light, /equal-weighted/);
});

test('tradability separates shortfalls from recorded exceptions', () => {
  const exitability = {
    ok: true, policy: { targetPosition: 1e9, exitDays: 3, maxParticipation: 0.2 }, minimumAdvtForTarget: 1_666_666_667,
    sized: [
      { symbol: 'A', meetsTarget: true, maxExecutablePosition: 5e9 },
      { symbol: 'B', meetsTarget: false, maxExecutablePosition: 5e8, exception: null },
      { symbol: 'C', meetsTarget: false, maxExecutablePosition: 1e8, exception: { by: 'portfolio owner' } },
    ],
  };
  const one = section(summariseIntelligence({ exitability }), 'tradability');
  assert.match(one.lines[0].text, /^1 of 3 members can carry a ₹100 cr position, which takes ₹167 cr/);
  assert.equal(one.lines[1].text, 'Largest executable position below target: B ₹50 cr.');
  assert.deepEqual(one.caveats, ['Held below target on recorded exceptions: C (₹10 cr).']);
});

test('the plain-text copy has every section, and pending ones say what they wait for', () => {
  const text = summaryText(summariseIntelligence({ universe }));
  assert.match(text, /^THE BASKET\n- 2 companies/);
  assert.match(text, /SINCE ADMISSION\n- Waiting for the since-admission series\./);
  assert.equal(rupeesCr(35_501.9), '₹35,502 cr');
});
