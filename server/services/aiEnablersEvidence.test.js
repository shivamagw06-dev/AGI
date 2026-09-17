import test from 'node:test';
import assert from 'node:assert/strict';
import { admits, classifyEvidence, subLayersFrom } from './aiEnablersEvidence.js';

/**
 * Titles and descriptions are verbatim from Netweb Technologies' exchange
 * announcement feed and investor presentation, retrieved via Trendlyne.
 * Fixtures marked CONSTRUCTED exercise branches that feed does not contain.
 */
const ESOP = { title: 'Netweb Technologies India Ltd - 543945 - Announcement under Regulation 30 (LODR)-Allotment of ESOP / ESPS', description: 'Intimation regarding allotment of 1645 ESOPs on 03.09.2026' };
const NEWSPAPER = { title: 'Announcement under Regulation 30 (LODR)-Newspaper Publication', description: 'Intimation regarding newspaper publication of 27th AGM Notice' };
const QIP = { title: 'Netweb Technologies shares fall 4% after raising Rs 1,200 crore through QIP', description: 'the company completed its Rs 1,200 crore Qualified Institutions Placement (QIP), its first equity capital raise since listing' };
const SEGMENT = { title: 'Q1 FY27 Revenue Breakdown by offerings', description: 'AI Systems 62.29% of Revenue from Operations, growing 484.20% YoY; order book Rs 25,069.35 million; GPU based AI systems 10,000+ installed' };

test('the filings every listed company makes admit nobody', () => {
  // A company's announcement feed is mostly this. Counting filings without
  // reading them is the second cheapest way to build a fake AI index.
  for (const routine of [ESOP, NEWSPAPER]) {
    const verdict = classifyEvidence(routine);
    assert.equal(verdict.kind, 'routine');
    assert.equal(verdict.hard, false);
  }
  assert.equal(admits([ESOP, NEWSPAPER]).admitted, false);
});

test('a fundraise is not evidence of what a company builds', () => {
  // The most common false positive: exciting, price-moving, often reported
  // beside AI commentary, and silent about the business.
  const verdict = classifyEvidence(QIP);
  assert.equal(verdict.kind, 'fundraise');
  assert.equal(verdict.hard, false);
  assert.match(verdict.why, /says nothing about what is built/);
});

test('two weeks of a real feed can contain no evidence at all', () => {
  // Netweb is unambiguously an AI infrastructure company and its recent
  // filings say so nowhere. Order announcements are episodic; a screen that
  // needs one every fortnight would drop the company between them.
  const verdict = admits([ESOP, NEWSPAPER, QIP]);
  assert.equal(verdict.admitted, false);
  assert.equal(verdict.basis, 'none');
  assert.match(verdict.reason, /no AI-infrastructure evidence/);
});

test('an operating disclosure admits, and says what it disclosed', () => {
  const verdict = classifyEvidence(SEGMENT);
  assert.equal(verdict.kind, 'operating');
  assert.equal(verdict.hard, true);
  assert.equal(verdict.aiRelevant, true);
  const decision = admits([ESOP, QIP, SEGMENT]);
  assert.equal(decision.admitted, true);
  assert.equal(decision.basis, 'hard');
  assert.equal(decision.hard.length, 1);
});

test('soft evidence never admits, however much of it there is', () => {
  // CONSTRUCTED: five partnerships and a transcript full of the vocabulary.
  const soft = [
    { title: 'MoU signed for data centre collaboration', description: 'memorandum of understanding' },
    { title: 'Strategic partnership for GPU deployment', description: 'partnership' },
    { title: 'Collaboration on hyperscale capacity', description: 'collaboration' },
    { title: 'Tie-up announced for liquid cooling', description: 'tie-up' },
    { kind: 'transcript', title: 'Earnings call', description: 'we see enormous demand for AI servers, GPU clusters and data centre racks' },
  ];
  const verdict = admits(soft);
  assert.equal(verdict.admitted, false);
  assert.equal(verdict.basis, 'soft');
  assert.equal(verdict.soft.length, 5);
  assert.match(verdict.reason, /nothing signed - for review, not for the index/);
});

test('a hard order with nothing tying it to AI does not admit', () => {
  // CONSTRUCTED: a large, real, entirely irrelevant order.
  const cement = { title: 'Company secures order worth Rs 800 crore', description: 'order for supply of cement to a highway project' };
  const verdict = classifyEvidence(cement);
  assert.equal(verdict.hard, true);
  assert.equal(verdict.aiRelevant, false);
  assert.match(verdict.why, /nothing ties it to AI infrastructure/);
  assert.equal(admits([cement]).admitted, false);
});

test('"AI" on its own is not enough to make a filing relevant', () => {
  // CONSTRUCTED. Every company says it. The words that carry information
  // describe plant: racks, substations, packaging lines, megawatts.
  const talk = { title: 'Company wins order', description: 'the order will use AI to improve efficiency' };
  assert.equal(classifyEvidence(talk).aiRelevant, false);
  const plant = { title: 'Company wins order', description: 'order for transformers for a data centre substation' };
  assert.equal(classifyEvidence(plant).aiRelevant, true);
});

test('the sub-layer is read from the evidence, not the sector label', () => {
  // "Capital goods" covers a transformer maker and a rack maker equally and
  // tells a reader nothing about which one it is.
  assert.deepEqual(subLayersFrom([SEGMENT]).map((one) => `${one.layer}/${one.subLayer}`), ['data_centre/hardware']);
  const transformers = { title: 'Order for transformers and switchgear for a data centre substation' };
  const found = subLayersFrom([transformers]).map((one) => `${one.layer}/${one.subLayer}`);
  assert.ok(found.includes('power/equipment'));
  assert.ok(found.includes('power/transmission'));
});

test('a company can sit in two sub-layers on its own evidence', () => {
  // CONSTRUCTED: one maker, two genuinely different businesses.
  const both = [
    { title: 'Order for OSAT assembly and test line' },
    { title: 'Order for wafer substrate supply' },
  ];
  const found = subLayersFrom(both).map((one) => one.subLayer).sort();
  assert.deepEqual(found, ['materials', 'osat']);
});

test('empty evidence is not soft evidence', () => {
  assert.equal(classifyEvidence({}).kind, 'empty');
  assert.equal(admits([]).basis, 'none');
  assert.equal(admits([]).admitted, false);
});
