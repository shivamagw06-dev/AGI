import test from 'node:test';
import assert from 'node:assert/strict';
import { COVERAGE_FLOOR, computeIndex, leaders, priced, weightsFor } from './aiEnablersIndex.js';

/**
 * Members are the real universe's, with their real sub-layer splits. Prices
 * are illustrative: no market feed is connected in a test, and the arithmetic
 * is what is under test, not the quotes.
 */
const UNIVERSE = {
  members: [
    { symbol: 'POWERINDIA', layer: 'power', subLayers: ['equipment', 'transmission'], freeFloatShares: 100 },
    { symbol: 'ADANIENT', layer: 'data_centre', subLayers: ['operator', 'developer'], freeFloatShares: 9000 },
    { symbol: 'CLEANMAX', layer: 'power', subLayers: ['generation'], freeFloatShares: 100 },
    { symbol: 'ANANTRAJ', layer: 'data_centre', subLayers: ['developer', 'operator'], freeFloatShares: 100 },
  ],
};
const NOW = 1_800_000_000_000;
const quote = (ltp, previousClose = 100, at = NOW) => ({ ltp, previousClose, at });
const ALL = {
  POWERINDIA: quote(103), ADANIENT: quote(99), CLEANMAX: quote(104), ANANTRAJ: quote(101),
};

test('contributions sum to the index return', () => {
  // By construction. When they do not, something changed that the weights do
  // not know about - a split, a bonus, a rights issue - and the difference is
  // the only warning there will be.
  const index = computeIndex(UNIVERSE, ALL, { now: NOW });
  const summed = index.contributions.byName.reduce((sum, row) => sum + row.contribution_pp, 0);
  assert.equal(Math.abs(index.return_pp - summed) < 0.005, true);
  assert.equal(index.residual_ok, true);
});

test('a member split across sub-layers splits its contribution too', () => {
  // Hitachi Energy is half power equipment and half transmission on its own
  // evidence. Counting its move into both in full would make the sub-layers
  // sum to more than the index.
  const index = computeIndex(UNIVERSE, ALL, { now: NOW });
  const equipment = index.contributions.bySubLayer.find((row) => row.subLayer === 'power/equipment');
  const transmission = index.contributions.bySubLayer.find((row) => row.subLayer === 'power/transmission');
  assert.equal(equipment.contribution_pp, transmission.contribution_pp);
  const name = index.contributions.byName.find((row) => row.symbol === 'POWERINDIA');
  assert.equal(equipment.contribution_pp + transmission.contribution_pp, name.contribution_pp);
  const subTotal = index.contributions.bySubLayer.reduce((sum, row) => sum + row.contribution_pp, 0);
  assert.ok(Math.abs(subTotal - index.return_pp) < 0.005);
});

test('an index of some of the members is not the index', () => {
  const index = computeIndex(UNIVERSE, { POWERINDIA: quote(103), ADANIENT: quote(99) }, { now: NOW });
  assert.equal(index.status, 'insufficient_coverage');
  assert.equal(index.level, null);
  assert.equal(index.return_pct, null);
  assert.deepEqual(index.missing.sort(), ['ANANTRAJ', 'CLEANMAX']);
  assert.match(index.reason, /2 of 4 members priced/);
});

test('a stale price is excluded and counted, not carried', () => {
  // A price that stopped updating must never be treated as a price that
  // stopped moving.
  const stale = { ...ALL, CLEANMAX: quote(104, 100, NOW - 120_000) };
  const { live, stale: held, coverage } = priced(UNIVERSE.members, stale, { now: NOW });
  assert.equal(live.length, 3);
  assert.equal(held[0].symbol, 'CLEANMAX');
  assert.equal(held[0].ageMs, 120_000);
  assert.equal(coverage, 0.75);
});

test('equal weighting is equal, whatever the sizes are', () => {
  const weights = weightsFor(priced(UNIVERSE.members, ALL, { now: NOW }).live, { construction: 'equal' });
  assert.deepEqual([...new Set(weights.values())], [0.25]);
});

test('a capped weight stays capped after the weights are normalised', () => {
  // Capping and then renormalising undoes the cap. In the first version of
  // this, a name held at 10% came out at 75%: scaling everything back up to
  // sum to one lifted it straight past the limit again.
  const twenty = Array.from({ length: 20 }, (_, at) => ({
    symbol: `S${at}`, layer: at < 10 ? 'power' : 'data_centre', subLayers: ['x'],
    freeFloatShares: at === 0 ? 100_000 : 100,
  }));
  const quotes = Object.fromEntries(twenty.map((member) => [member.symbol, quote(101)]));
  const weights = weightsFor(priced(twenty, quotes, { now: NOW }).live, { construction: 'cap', nameCap: 0.1, layerCap: 0.4 });
  for (const [symbol, weight] of weights) assert.ok(weight <= 0.1 + 1e-9, `${symbol} at ${weight}`);
  assert.ok(Math.abs([...weights.values()].reduce((a, b) => a + b, 0) - 1) < 1e-9);
});

test('a cap below 1/n is impossible, and becomes equal weighting', () => {
  // Ten per cent across four names cannot reach one. Ignoring that silently
  // is how a cap becomes decorative; the feasible floor is used instead and
  // the result is simply equal weighting, which is the honest answer.
  const weights = weightsFor(priced(UNIVERSE.members, ALL, { now: NOW }).live, { construction: 'cap', nameCap: 0.1 });
  assert.deepEqual([...new Set([...weights.values()].map((one) => Number(one.toFixed(6))))], [0.25]);
});

test('the constructions are reported separately, whatever they come to', () => {
  // With four members and an infeasible cap they coincide. The label still
  // says which is which, because a reader comparing two lines has to know
  // when they are the same line.
  const equal = computeIndex(UNIVERSE, ALL, { now: NOW, construction: 'equal' });
  const cap = computeIndex(UNIVERSE, ALL, { now: NOW, construction: 'cap' });
  assert.equal(equal.construction, 'equal');
  assert.equal(cap.construction, 'cap');
  assert.equal(equal.residual_ok && cap.residual_ok, true);
});

test('a quote missing its previous close cannot produce a return', () => {
  const broken = { ...ALL, ANANTRAJ: { ltp: 101, at: NOW } };
  assert.deepEqual(priced(UNIVERSE.members, broken, { now: NOW }).missing, ['ANANTRAJ']);
});

test('the movers are named both ways', () => {
  const index = computeIndex(UNIVERSE, ALL, { now: NOW });
  const { adding, dragging } = leaders(index);
  assert.equal(adding[0].symbol, 'CLEANMAX');
  assert.equal(dragging[0].symbol, 'ADANIENT');
  assert.ok(dragging[0].contribution_pp < 0);
});

test('a candidate is not a member', () => {
  // The universe file holds both. Only admitted members are in the basket.
  const withCandidate = { members: [...UNIVERSE.members, { symbol: 'NETWEB', layer: 'data_centre', subLayers: ['hardware'], admitted: false }] };
  const index = computeIndex(withCandidate, { ...ALL, NETWEB: quote(200) }, { now: NOW });
  assert.equal(index.total, 4);
  assert.equal(index.contributions.byName.some((row) => row.symbol === 'NETWEB'), false);
});

test('the coverage floor is a stated number, not a hidden one', () => {
  assert.equal(COVERAGE_FLOOR, 0.8);
  const index = computeIndex(UNIVERSE, ALL, { now: NOW, coverageFloor: 1.01 });
  assert.equal(index.status, 'insufficient_coverage');
});

/**
 * KEC International builds the data centre and the semiconductor fab. The
 * evidence is first-party, hard and names AI infrastructure, so the screen
 * admits it - but "developer" means the owner of the campus, not the
 * contractor who pours it, and the taxonomy has no sub-layer for the builder.
 * The index must not quietly drop such a member from the breakdown.
 */
const UNPLACED = {
  members: [
    { symbol: 'AAA', layer: 'power', subLayers: ['equipment'], freeFloatShares: 100 },
    { symbol: 'BBB', layer: 'data_centre', subLayers: [], freeFloatShares: 100 },
  ],
};
const UNPLACED_QUOTES = { AAA: quote(110), BBB: quote(120) };

test('a member with no sub-layer still counts in the index and in its layer', () => {
  const index = computeIndex(UNPLACED, UNPLACED_QUOTES, { now: NOW, construction: 'equal' });
  assert.equal(index.status, 'ok');
  assert.equal(index.return_pp, 15);
  const dc = index.contributions.byLayer.find((one) => one.layer === 'data_centre');
  assert.equal(dc.contribution_pp, 10);
});

test('a member with no sub-layer is named, not left as a hole to find', () => {
  const index = computeIndex(UNPLACED, UNPLACED_QUOTES, { now: NOW, construction: 'equal' });
  assert.deepEqual(index.unclassified, ['BBB']);
});

test('the sub-layer breakdown is reconciled separately from byName', () => {
  const index = computeIndex(UNPLACED, UNPLACED_QUOTES, { now: NOW, construction: 'equal' });
  // byName reconciles perfectly - that is exactly the trap. Only the
  // sub-layer reconciliation shows that a whole member is missing from it.
  assert.equal(index.residual_ok, true);
  assert.equal(index.subLayerResidual_pp, 10);
  assert.equal(index.subLayerResidual_ok, false);
});

test('a universe where every member has a sub-layer reconciles at both levels', () => {
  const index = computeIndex(UNIVERSE, ALL, { now: NOW, construction: 'equal' });
  assert.deepEqual(index.unclassified, []);
  assert.equal(index.residual_ok, true);
  assert.equal(index.subLayerResidual_ok, true);
});

test('a fallback quote is priced, and counted as a fallback', () => {
  // The bug this pins: the quote layer serves a last-good price precisely
  // because the tick is older than the live staleness window, and priced()
  // then re-applied that same window and threw it away. The fallback looked
  // implemented and could never fire.
  const members = [{ symbol: 'AAA', layer: 'power', subLayers: ['equipment'] }];
  const quotes = { AAA: { ltp: 110, previousClose: 100, at: NOW - 200_000, source: 'last_good' } };
  const result = priced(members, quotes, { now: NOW, staleMs: 60_000 });
  assert.equal(result.coverage, 1);
  assert.equal(result.stale.length, 0);
  assert.equal(result.fallback.length, 1);
  assert.equal(result.fallback[0].symbol, 'AAA');
});

test('an equally old quote with no source is still stale', () => {
  // Only a quote that declares itself adjudicated skips the check. Anything
  // else keeps the original behaviour, so a raw feed cannot sneak past.
  const members = [{ symbol: 'AAA', layer: 'power', subLayers: ['equipment'] }];
  const quotes = { AAA: { ltp: 110, previousClose: 100, at: NOW - 200_000 } };
  const result = priced(members, quotes, { now: NOW, staleMs: 60_000 });
  assert.equal(result.coverage, 0);
  assert.equal(result.stale.length, 1);
  assert.equal(result.fallback.length, 0);
});
