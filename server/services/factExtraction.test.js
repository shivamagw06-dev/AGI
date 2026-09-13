import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { CONTRACT, extractionPrompt, sentenceStates, readFacts } from './factExtraction.js';

// Verbatim from Reliance Industries' Integrated Annual Report 2025-26.
const FILING = [
  'Capex RIL’s capital expenditure for FY 2025-26 stood at H 1,44,271 crore (US$ 15.2 billion) '
    + 'as compared to H 1,31,107 crore in the previous financial year.',
  'Capital Expenditure 32,365 1,756 21,131 33,101 52,521 3,397 1,44,271 Depreciation',
  'Purchase of Property, Plant and Equipment, Spectrum and Other Intangible Assets (1,22,916) (1,39,967)',
  'Net Cash Flow from Operating Activities * 1,92,113 1,78,703',
].join('\n');

const observation = (over) => ({
  concept: 'capex', period_end: '2026-03-31', period_type: 'annual',
  accounting_scope: 'consolidated', entity_scope: 'group',
  currency: 'INR', unit: 10000000, ...over,
});

const THREE_CAPEX = [
  observation({
    definition_id: 'CAPEX.MANAGEMENT', measurement_basis: 'accrual', value: 144271,
    as_reported_label: 'Capex', source_section: 'Financial Performance and Review',
    source_sentence: 'Capex RIL’s capital expenditure for FY 2025-26 stood at H 1,44,271 crore '
      + '(US$ 15.2 billion) as compared to H 1,31,107 crore in the previous financial year.',
  }),
  observation({
    definition_id: 'CAPEX.SEGMENT', measurement_basis: 'segment_reporting', value: 144271,
    as_reported_label: 'Capital Expenditure', source_section: 'Segment note',
    source_sentence: 'Capital Expenditure 32,365 1,756 21,131 33,101 52,521 3,397 1,44,271 Depreciation',
  }),
  observation({
    definition_id: 'CAPEX.CASH_PPE_INTANGIBLES', measurement_basis: 'cash', value: 122916,
    as_reported_label: 'Purchase of Property, Plant and Equipment, Spectrum and Other Intangible Assets',
    source_section: 'Consolidated Cash Flow Statement',
    source_sentence: 'Purchase of Property, Plant and Equipment, Spectrum and Other Intangible '
      + 'Assets (1,22,916) (1,39,967)',
  }),
];

const read = (facts) => readFacts({
  payload: { facts }, document: FILING, company: 'RELIANCE', reportedInDocument: 'RIL_IAR_2026',
});

describe('what the reader is asked for', () => {
  test('it is told not to reconcile, which is the whole instruction', () => {
    assert.match(CONTRACT, /Do not reconcile/);
    assert.match(CONTRACT, /emit two observations/);
    assert.match(CONTRACT, /Do not calculate/);
  });

  test('an absent concept is an answer', () => {
    assert.match(CONTRACT, /An absent observation\s*\n?\s*is the correct answer/);
  });

  test('the prompt offers only definitions this store knows', () => {
    const { user } = extractionPrompt({ concepts: ['capex'], text: FILING });
    assert.match(user, /CAPEX\.MANAGEMENT/);
    assert.match(user, /CAPEX\.CASH_PPE_INTANGIBLES/);
    // Not every definition in the register - only the concepts asked for.
    assert.equal(/EBITDA\.REPORTED/.test(user), false);
  });
});

describe('three disclosures of capex are three facts', () => {
  test('nothing is collapsed', () => {
    const { facts, rejected } = read(THREE_CAPEX);
    assert.deepEqual(rejected, []);
    assert.equal(facts.length, 3);
    assert.deepEqual(facts.map((f) => f.value).sort((a, b) => b - a), [144271, 144271, 122916]);
  });

  test('each keeps the issuer’s own words', () => {
    const { facts } = read(THREE_CAPEX);
    const labels = facts.map((f) => f.as_reported_label);
    assert.ok(labels.includes('Capex'));
    assert.ok(labels.some((l) => l.startsWith('Purchase of Property, Plant and Equipment')));
  });
});

describe('what the reader cannot get away with', () => {
  test('a figure not in the cited sentence', () => {
    // The failure this exists to catch: a plausible number with a real
    // sentence attached to it.
    const { facts, rejected } = read([observation({
      definition_id: 'CAPEX.MANAGEMENT', measurement_basis: 'accrual', value: 150000,
      as_reported_label: 'Capex', source_sentence: THREE_CAPEX[0].source_sentence,
    })]);
    assert.equal(facts.length, 0);
    assert.match(rejected[0].reason, /does not state 150000/);
  });

  test('a sentence not in the filing', () => {
    const { facts, rejected } = read([observation({
      definition_id: 'CAPEX.MANAGEMENT', measurement_basis: 'accrual', value: 144271,
      as_reported_label: 'Capex',
      source_sentence: 'The company spent 1,44,271 crore on capital projects during the year.',
    })]);
    assert.equal(facts.length, 0);
    assert.match(rejected[0].reason, /not in the filing/);
  });

  test('a measurement basis the definition disagrees with', () => {
    // Cash capex recorded as an accrual is a misunderstanding of one or the
    // other, and both are load-bearing.
    const { rejected } = read([observation({
      definition_id: 'CAPEX.CASH_PPE_INTANGIBLES', measurement_basis: 'accrual', value: 122916,
      as_reported_label: 'Purchase of PPE', source_sentence: THREE_CAPEX[2].source_sentence,
    })]);
    assert.match(rejected[0].reason, /measured cash, not accrual/);
  });

  test('a definition that does not exist', () => {
    const { rejected } = read([observation({
      definition_id: 'CAPEX.TOTAL', measurement_basis: 'accrual', value: 144271,
      as_reported_label: 'Capex', source_sentence: THREE_CAPEX[0].source_sentence,
    })]);
    assert.match(rejected[0].reason, /unknown definition CAPEX\.TOTAL/);
  });

  test('a definition belonging to another concept', () => {
    const { rejected } = read([observation({
      concept: 'revenue', definition_id: 'CAPEX.MANAGEMENT', measurement_basis: 'accrual',
      value: 144271, as_reported_label: 'Capex', source_sentence: THREE_CAPEX[0].source_sentence,
    })]);
    assert.match(rejected[0].reason, /is a capex, not a revenue/);
  });

  test('one definition given two different values', () => {
    // Either two disclosures were reconciled into one definition or one was
    // read twice. Picking one would be the overwrite this store exists to
    // prevent, so neither is stored.
    const { facts, rejected } = read([THREE_CAPEX[0], {
      ...THREE_CAPEX[0], value: 122916, source_sentence: THREE_CAPEX[2].source_sentence,
    }]);
    assert.equal(facts.length, 1);
    assert.match(rejected[0].reason, /already recorded as 144271/);
  });

  test('a missing field is named', () => {
    const { rejected } = read([{ concept: 'capex', value: 144271 }]);
    assert.match(rejected[0].reason, /missing definition_id/);
    assert.match(rejected[0].reason, /source_sentence/);
  });
});

describe('reading a figure as a filing writes it', () => {
  test('Indian digit grouping compares equal', () => {
    assert.equal(sentenceStates('stood at H 1,44,271 crore', 144271), true);
    assert.equal(sentenceStates('Assets (1,22,916) (1,39,967)', 122916), true);
  });

  test('a decimal cited with a trailing zero still matches', () => {
    assert.equal(sentenceStates('a $0.4 billion charge', 0.40), true);
  });

  test('a figure that is not there does not match', () => {
    assert.equal(sentenceStates('stood at H 1,44,271 crore', 144272), false);
    assert.equal(sentenceStates('', 144271), false);
    assert.equal(sentenceStates('no figures here', null), false);
  });
});

test('a figure and its prior-year comparative both survive', () => {
  // Reliance states both in one sentence. They are one definition, one scope
  // and two periods, and a key that ignored the period rejected the second as
  // a duplicate of the first - losing the comparative in most filings there
  // are.
  const sentence = 'RIL’s capital expenditure for FY 2025-26 stood at H 1,44,271 crore (US$ 15.2 billion) as compared to H 1,31,107 crore in the previous financial year.';
  const common = {
    concept: 'capex', definition_id: 'CAPEX.MANAGEMENT', measurement_basis: 'accrual',
    currency: 'INR', unit: 10000000, as_reported_label: 'capital expenditure',
    source_sentence: sentence,
  };
  const { facts, rejected } = readFacts({
    payload: { facts: [
      { ...common, value: 144271, period_end: '2026-03-31' },
      { ...common, value: 131107, period_end: '2025-03-31' },
    ] },
    document: sentence, company: 'RELIANCE', reportedInDocument: 'RIL FY2025-26',
  });
  assert.deepEqual(rejected, []);
  assert.deepEqual(facts.map((fact) => [fact.period_end, fact.value]),
    [['2026-03-31', 144271], ['2025-03-31', 131107]]);
});
