import test from 'node:test';
import assert from 'node:assert/strict';
import { NOMINATION_TERMS, nominate } from './aiEnablersNomination.js';

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
