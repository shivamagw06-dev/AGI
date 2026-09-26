import test from 'node:test';
import assert from 'node:assert/strict';
import { NOMINATION_TERMS, nominate, readingPriority } from './aiEnablersNomination.js';

const layers = (description) => nominate({ description }).subLayers.map((one) => one.subLayer);

test('a switchgear and transformer maker is nominated to power equipment', () => {
  const result = nominate({ description: 'Manufactures power transformers, gas-insulated switchgear and HVDC systems.' });
  assert.equal(result.nominated, true);
  assert.deepEqual(layers('Manufactures power transformers, gas-insulated switchgear and HVDC systems.'),
    ['power/transmission', 'power/equipment']);
  const equipment = result.subLayers.find((one) => one.subLayer === 'power/equipment');
  assert.deepEqual(equipment.terms, ['transformers', 'switchgear']);
});

test('data centre spelling, colocation and hyperscale all nominate', () => {
  for (const text of ['operates data centers', 'builds a datacentre campus', 'offers co-location', 'serves hyperscalers']) {
    assert.ok(layers(text).includes('data_centre/developer_operator'), text);
  }
});

test('semiconductor assembly and EMS nominate to OSAT', () => {
  assert.deepEqual(layers('an OSAT facility for assembly, testing and packaging'), ['semiconductor/osat']);
  assert.deepEqual(layers('Electronics Manufacturing Services and printed circuit boards'), ['semiconductor/osat']);
});

test('words that describe a market and not a plant nominate nothing', () => {
  const result = nominate({ description: 'A digital-first AI company leveraging data and cloud to transform energy.' });
  assert.equal(result.nominated, false);
  assert.equal(result.reason, 'NO_TERM_MATCHED');
});

test('known collisions do not nominate', () => {
  assert.equal(nominate({ description: 'A cable television network and multi-system operator.' }).nominated, false);
  assert.equal(nominate({ description: 'Makes flexible packaging and food packaging films.' }).nominated, false);
  assert.equal(nominate({ description: 'Hosts web servers for small businesses.' }).nominated, false);
  assert.equal(nominate({ description: 'Rising purchasing power in rural India.' }).nominated, false);
});

test('a collision removes only itself, not a real term beside it', () => {
  assert.deepEqual(
    layers('Makes flexible packaging, and separately LT power cables.'),
    ['power/equipment'],
  );
});

test('an empty description is recorded as such, not as a failed match', () => {
  assert.deepEqual(nominate({ description: '' }), { nominated: false, reason: 'NO_DESCRIPTION', subLayers: [] });
  assert.equal(nominate({}).reason, 'NO_DESCRIPTION');
});

test('no term is a bare market word', () => {
  const sources = Object.values(NOMINATION_TERMS).flat().map((one) => one.source);
  for (const word of ['ai', 'artificial intelligence', 'digital', 'data', 'cloud', 'power', 'energy', 'packaging', 'cable']) {
    assert.ok(!sources.includes(`\\b${word}\\b`), word);
  }
});

/* ── the first full run's measured misses, kept fixed ─────────────────── */

test('the wordings the first run missed now nominate', () => {
  assert.ok(layers('engaged in the generation and sale of bulk power to state utilities').includes('power/generation'));
  assert.ok(layers('manufactures lead-acid batteries for telecom and UPS').includes('power/equipment'));
  assert.ok(layers('makes industrial batteries').includes('power/equipment'));
  assert.ok(layers('central air conditioning and commercial refrigeration').includes('data_centre/hardware'));
});

test('a hotel with air-conditioned rooms is not a cooling maker', () => {
  assert.equal(nominate({ description: 'Operates hotels with 200 air-conditioned rooms.' }).nominated, false);
});

/* ── reading priority ─────────────────────────────────────────────────── */

const nom = (...subs) => subs.map((subLayer) => ({ subLayer, terms: [] }));

test('a sector that makes the named plant reads first', () => {
  assert.deepEqual(readingPriority({ sector: 'Electric Equipment', nomination: nom('power/equipment') }),
    { tier: 1, subLayers: ['power/equipment'] });
  assert.equal(readingPriority({ sector: 'Power', nomination: nom('power/generation') }).tier, 1);
});

test('generation-equipment makers and Dixon are strong, not incidental', () => {
  assert.equal(readingPriority({ sector: 'Electric Equipment', nomination: nom('power/generation') }).tier, 1);
  assert.equal(readingPriority({ sector: 'Capital Goods - Electrical Equipment', nomination: nom('power/generation') }).tier, 1);
  assert.equal(readingPriority({ sector: 'Consumer Durables', nomination: nom('semiconductor/osat') }).tier, 1);
});

test('a data-centre term is strong in any sector', () => {
  assert.equal(readingPriority({ sector: 'Construction', nomination: nom('data_centre/developer_operator') }).tier, 1);
});

test('EPC alone reads after the strong tier, and a captive plant reads last', () => {
  assert.deepEqual(readingPriority({ sector: 'Construction', nomination: nom('infrastructure/epc') }),
    { tier: 2, subLayers: ['infrastructure/epc'] });
  assert.equal(readingPriority({ sector: 'Textile', nomination: nom('power/generation') }).tier, 3);
  assert.equal(readingPriority({ sector: 'Sugar', nomination: nom('power/generation', 'infrastructure/epc') }).tier, 3);
});

test('an unknown sector is read late, never dropped, and a non-nomination has no priority', () => {
  assert.equal(readingPriority({ sector: 'Something New', nomination: nom('power/equipment') }).tier, 3);
  assert.equal(readingPriority({ sector: null, nomination: nom('semiconductor/osat') }).tier, 3);
  assert.equal(readingPriority({ sector: 'Power', nomination: [] }), null);
});
