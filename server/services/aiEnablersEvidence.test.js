import test from 'node:test';
import assert from 'node:assert/strict';
import { admits, admitsContractor, classifyEvidence, subLayersFrom } from './aiEnablersEvidence.js';

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

/**
 * Verbatim from filings retrieved via Trendlyne while building the first
 * universe. The market-commentary rule exists because of these three.
 */
const CBRE = { title: 'As per CBRE Group India data centre report for 2026, the country data centre stock crossed approximately 1.7 GW in 2025 and total capacity is expected to rise by about 30% during 2026' };
const INDOTECH = { title: 'Capacity expansion in steel, cement, textiles, and data centres contributes to sustained industrial transformer demand' };
const KEI = { title: 'India Data Centre Capacity set to touch 14GW by 2035 with 20% CAGR, driven by AI, Cloud and 5G demand' };
const HITACHI_CALL = { title: 'The third project is a significant data center-related order for a Load Pooling Station and Main Pooling Station, comprising 56 of 400 kV Gas-Insulated Switchgear (GIS) and 12.8 km of 400 kV Gas-Insulated Busbar' };
const HITACHI_REPORT = { title: 'Data Centers: Received an order for 3X 220kV AIS Transformers extension for a leading data center in Hyderabad' };

test('a forecast about the market is not evidence about the company printing it', () => {
  // Every transformer maker's deck carries a page on India reaching 8-10 GW of
  // data centre capacity, sourced to CRISIL or CBRE. It appears in the
  // documents of companies with data centre orders and companies with none,
  // identically. Counting it admits the sector on the strength of its slides.
  for (const deck of [CBRE, INDOTECH, KEI]) {
    assert.equal(classifyEvidence(deck).hard, false, deck.title.slice(0, 40));
  }
  assert.equal(admits([CBRE, INDOTECH, KEI]).admitted, false);
});

test('the company describing its own forecast is not market commentary', () => {
  // CONSTRUCTED: first-person language over a forward-looking sentence. The
  // rule must not silence a company saying what it is building.
  const ours = { title: 'We expect to commission our new transformer facility serving data centre customers in FY28' };
  assert.equal(classifyEvidence(ours).hard, true);
});

test('an order described rather than announced is still an order', () => {
  // How a company's own earnings call talks about the orders it just won.
  // Requiring an acquisition verb missed this entirely.
  const verdict = classifyEvidence(HITACHI_CALL);
  assert.equal(verdict.kind, 'order');
  assert.equal(verdict.hard, true);
  assert.equal(verdict.aiRelevant, true);
});

test('Hitachi Energy India admits on its own filings', () => {
  const decision = admits([CBRE, KEI, HITACHI_CALL, HITACHI_REPORT]);
  assert.equal(decision.admitted, true);
  assert.equal(decision.hard.length, 2);
  // Transformers and gas-insulated switchgear are equipment; a pooling
  // station and a gas-insulated busbar are the grid they connect to. The
  // company sits in both, and each on its own line.
  const subLayers = subLayersFrom([HITACHI_CALL, HITACHI_REPORT]).map((one) => one.subLayer).sort();
  assert.deepEqual(subLayers, ['equipment', 'transmission']);
});

test('a sub-layer is claimed only where the evidence actually says so', () => {
  // The first version of the test above asserted transmission from two
  // excerpts that name only transformers and switchgear. The code was right
  // and the expectation was wrong - which is the failure mode this whole
  // screen exists to avoid, committed while writing its tests.
  assert.deepEqual(subLayersFrom([HITACHI_REPORT]).map((one) => one.subLayer), ['equipment']);
  const hvdc = { title: '1,000 MW Kudus-Aarey HVDC transmission project in Mumbai, Maharashtra' };
  assert.deepEqual(subLayersFrom([hvdc]).map((one) => one.subLayer), ['transmission']);
});

test('a bare projection table is not an operating disclosure', () => {
  // Diamond Power's deck, verbatim. No verb in it at all - it matched on the
  // word MW and came back as an operating disclosure. The P is the whole
  // signal, and the same table appears in decks across the sector.
  const table = { title: 'Data-centre capacity (MW) FY19 350 FY25 1,300 FY30P 5,000' };
  const verdict = classifyEvidence(table);
  assert.equal(verdict.kind, 'market_commentary');
  assert.equal(verdict.hard, false);
});

test('a company saying what it commissioned is not a projection', () => {
  // Clean Max, verbatim. Forward-looking words appear beside first-party ones
  // constantly, and silencing the second would refuse every company that
  // describes its own pipeline.
  const cleanmax = { title: "we've commissioned about 400 megawatt in the RE power sales segment and 100 megawatt in the RE services segment" };
  assert.equal(classifyEvidence(cleanmax).hard, true);
  assert.deepEqual(subLayersFrom([cleanmax]).map((one) => one.subLayer), ['generation']);
});

test('an order signed is an order, however the filing phrases it', () => {
  // Adani, verbatim. No acquisition verb and no "order for" either - the
  // event is carried by "signed" and by the megawatts.
  const adani = { title: 'During the quarter, 400 MW order signed with hyperscale customer for Vizag; Tied up capacity 960+ MW' };
  const verdict = classifyEvidence(adani);
  assert.equal(verdict.hard, true);
  assert.equal(verdict.aiRelevant, true);
  assert.deepEqual(subLayersFrom([adani]).map((one) => one.subLayer), ['operator']);
});

test('a company forecasting its own capacity is not forecasting the market', () => {
  // CONSTRUCTED to hold both at once, which is how filings actually read:
  // forward-looking language, a projection marker, and the company's own book
  // in the same sentence. Silencing it would refuse every company that
  // describes its own pipeline, which is most of the useful evidence there is.
  const ours = { title: 'Our contracted data centre capacity is expected to reach 2,500 MW by FY28E' };
  const verdict = classifyEvidence(ours);
  assert.equal(verdict.hard, true);
  assert.notEqual(verdict.kind, 'market_commentary');
  // The same sentence about the country instead of the company is commentary.
  const market = { title: "India's data centre capacity is expected to reach 2,500 MW by FY28E" };
  assert.equal(classifyEvidence(market).kind, 'market_commentary');
});

test('an OSAT plant that has been built admits; the revenue it is meant to earn does not', () => {
  // Kaynes, verbatim from two documents. The capex is money already spent and
  // a plant already standing. The roadmap in the same annual report is a
  // target four to five years out, and the screen must separate them - a
  // company can have both, and most do.
  const capex = { description: 'Let me turn to the newer business, OSAT and PCB. The capex done in FY26 was INR473 crores for OSAT and INR324 crores for PCB.' };
  assert.equal(classifyEvidence(capex).hard, true);
  assert.equal(admits([capex]).admitted, true);
  assert.deepEqual(subLayersFrom([capex]).map((one) => one.subLayer), ['osat']);

  const roadmap = { description: 'Targeted strategic roadmap expects the OSAT vertical to drive 30% of total Kaynes Group revenues within the next 4 to 5 years. Commercial manufacturing operations are scheduled to commence in FY 2026-27.' };
  assert.equal(classifyEvidence(roadmap).hard, false);
  assert.equal(admits([roadmap]).admitted, false);
});

test('a plant that is operational is an operating fact, not a plan', () => {
  // CG Power, verbatim. "is now operational at a peak capacity of" is the
  // disclosure; the G2 line right after it is a plan, and the two sit in one
  // paragraph. The paragraph admits on the first half.
  const cg = { description: 'CG Semi reached a defining milestone in FY26 with the inauguration of India’s first end-to-end OSAT facility at Sanand, Gujarat in August 2025. The G1 facility is now operational at a peak capacity of 0.5 million units per day, with plans to further scale up to 14.5 million chips per day with the upcoming commissioning of our G2 facility.' };
  assert.equal(admits([cg]).admitted, true);
  assert.deepEqual(subLayersFrom([cg]).map((one) => one.subLayer), ['osat']);
});

test('a segment revenue line admits where a product slide does not', () => {
  // Netweb discloses what the AI segment earned. Cyient shows which markets
  // its ASICs address. Only one of these is a fact about a completed period.
  const netweb = { description: 'Our AI segment continues to be a key growth driver, contributing Rs 5,105.70 million, being 62.29% of Revenue from Operations, growing 484.20% YoY, while HPC and Private Cloud maintained robust traction at Rs 1,252.94 million and Rs 1,353.46 million respectively. Our order book stood at Rs 25,069.35 million as of 30th June 2026.' };
  assert.equal(admits([netweb]).admitted, true);
  assert.deepEqual(subLayersFrom([netweb]).map((one) => one.subLayer), ['hardware']);

  const cyient = { description: 'Application-Specific Integrated Circuits Deep Dive. Cyient Semiconductors: Data Centers, Industrial. Kinetic Technologies: Edge AI, Automotive.' };
  assert.equal(admits([cyient]).admitted, false);
});

test('"AI segment" says a company has an AI business, not which one', () => {
  // The distinction the sub-layer patterns have to hold. An AI segment could
  // be a software house; Netweb is hardware because it says AI Systems, HPC
  // and high-end computing. So the phrase admits and places nowhere, and the
  // member is only classified from evidence that names the product.
  const vague = { description: 'Our AI segment contributed Rs 5,105.70 million of Revenue from Operations.' };
  assert.equal(classifyEvidence(vague).aiRelevant, true);
  assert.equal(admits([vague]).admitted, true);
  assert.deepEqual(subLayersFrom([vague]), []);
});

test('plurals do not hide a sub-layer, in AI systems as in transformers', () => {
  // "AI Systems" is how Netweb's own presentation writes it. /\bai system\b/
  // missed it, the same way /\btransformer\b/ once missed "Transformers".
  const plural = { description: 'Revenue from AI Systems grew 484.20% YoY; order book of Rs 25,069.35 million.' };
  assert.deepEqual(subLayersFrom([plural]).map((one) => one.subLayer), ['hardware']);
});

test('a molecule under development is not a molecule being sold', () => {
  // Aether. The AI vocabulary is all there - AI hardware, high-speed boards,
  // semiconductors - and there is real capex in the same call. But the capex
  // is for the oil-and-gas site, and the electronic materials are in R&D.
  // This is the case the screen exists to refuse.
  const aether = { description: 'Few of them are the specialty monomers that Aether is actively developing. These molecules that Aether will be manufacturing in its brand new site, Magnum, are an upstream input to the board inside 5G and AI hardware.' };
  const verdict = classifyEvidence(aether);
  assert.equal(verdict.aiRelevant, true);
  assert.equal(verdict.hard, false);
  assert.equal(admits([aether]).admitted, false);
  assert.equal(admits([aether]).basis, 'soft');
});

test('the contractor who builds the campus now has a sub-layer of its own', () => {
  // KEC International builds the data centre and the Sanand fab. Calling that
  // "developer" would say it owns a campus it does not own; leaving it out
  // would drop a company with signed, dated, named project evidence. It is
  // the builder, and the taxonomy now says so.
  const kec = { description: 'DATA CENTRE PROJECT, KOLKATA: construction of a mission critical facility. Project physically completed in Q1 FY27. SEMICONDUCTOR MANUFACTURING PLANT, SANAND, GUJARAT: construction of a semiconductor manufacturing facility including specialised cleanroom construction. Main plant commissioned in Q4 FY26.' };
  assert.equal(admits([kec]).admitted, true);
  assert.deepEqual(subLayersFrom([kec]).map((one) => `${one.layer}/${one.subLayer}`), ['infrastructure/epc']);
});

test('a contractor needs the project, the role and the exposure together', () => {
  // Its exposure is to projects rather than to a product line, so the
  // ordinary test would admit any builder whose brochure mentions data
  // centres. All three, or nothing.
  // The full excerpt from KEC's annual report, as the universe holds it. The
  // Kolkata line alone is not enough - "physically completed" is not one of
  // the hard-evidence patterns, and that refusal is correct rather than a
  // gap: it is the Sanand commissioning that carries this.
  const kec = { description: 'DATA CENTRE PROJECT, KOLKATA: construction of a mission critical facility. Project physically completed in Q1 FY27. SEMICONDUCTOR MANUFACTURING PLANT, SANAND, GUJARAT: construction of a semiconductor manufacturing facility including specialised cleanroom construction. Main plant commissioned in Q4 FY26.' };
  const verdict = admitsContractor([kec]);
  assert.equal(verdict.admitted, true);
  assert.equal(verdict.basis, 'hard_contractor');
});

test('a brochure mentioning data centres admits no contractor', () => {
  const marketing = { description: 'We serve data centres, semiconductor plants and other mission critical infrastructure across India, and are a trusted partner to leading developers.' };
  const verdict = admitsContractor([marketing]);
  assert.equal(verdict.admitted, false);
  assert.match(verdict.reason, /contracted delivery role|project, the role and the exposure/);
});

test('a named project with a role but no size does not admit a contractor', () => {
  // Without a figure there is nothing to attribute, and a contractor with
  // unquantified exposure is a company that mentioned a sector.
  const vague = { description: 'We were awarded construction of a data centre for a leading operator.' };
  assert.equal(admitsContractor([vague]).admitted, false);
});

test('a member the taxonomy still cannot place is reported, not forced', () => {
  // The EPC sub-layer closes the case that prompted it, and the index guard
  // for an unplaceable member stays, because the next one will not be a
  // builder.
  const unplaceable = { description: 'We commissioned a new logistics corridor serving several industrial customers during the year.' };
  assert.deepEqual(subLayersFrom([unplaceable]), []);
});
