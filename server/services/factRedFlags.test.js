import test from 'node:test';
import assert from 'node:assert/strict';
import { calculate } from './factCalculation.js';
import { checkRestatements } from './factVerification.js';
import {
  CONVENTIONS, RULE_ORDER, WATCHED_PAIRS, definitionSpreads, droppedDisclosures,
  fromVerification, growthGaps, rank, review, signSplits, staleDerivations,
} from './factRedFlags.js';

/**
 * Figures are from Reliance Industries' Integrated Annual Report 2025-26 and
 * its 10-Year Financial Highlights, which prints each year beside the last.
 * Fixtures marked CONSTRUCTED reach branches the filing does not exhibit: it
 * is internally consistent, states no free cash flow, and cannot restate
 * itself.
 */
const RELIANCE = 'RIL FY2025-26';
const NOW = '2026-03-31';
const BEFORE = '2025-03-31';

const fact = (over) => ({
  company: 'RELIANCE', period_type: 'annual', accounting_scope: 'consolidated',
  entity_scope: 'group', currency: 'INR', unit: 10000000,
  reported_in_document: RELIANCE, segment: null, verdict: 'stated', ...over,
});

const TEN_YEAR = '10-Year Financial Highlights (Consolidated) US$ Million FY 2025-26 FY 2024-25';
const both = (definition_id, concept, now, before, source_sentence) => [
  fact({ concept, definition_id, period_end: NOW, value: now, source_sentence }),
  fact({ concept, definition_id, period_end: BEFORE, value: before, source_sentence }),
];

const FACTS = [
  ...both('CAPEX.MANAGEMENT', 'capex', 144271, 131107,
    'RIL’s capital expenditure for FY 2025-26 stood at H 1,44,271 crore (US$ 15.2 billion) as compared to H 1,31,107 crore in the previous financial year.'),
  ...both('CAPEX.CASH_PPE_INTANGIBLES', 'capex', 122916, 139967,
    'Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets   (1,22,916)   (1,39,967)'),
  ...both('CFO.STATEMENT', 'cfo', 192113, 178703,
    'Cash   Flow   from   Operating   Activities   *   1,92,113   1,78,703'),
  ...both('EBITDA.REPORTED', 'ebitda', 207911, 183422,
    `${TEN_YEAR} Earnings Before Depreciation, Finance Cost and Tax Expenses (EBITDA) #  21,923   2,07,911   1,83,422`),
  ...both('REVENUE.VALUE_OF_SALES_AND_SERVICES', 'revenue', 1175919, 1071174,
    `${TEN_YEAR} Value of Sales and Services (Revenue)  123,996   11,75,919   10,71,174   10,00,122`),
  ...both('REVENUE.TOTAL_INCOME', 'revenue', 1104637, 998114,
    `${TEN_YEAR} Total Income   116,480   11,04,637   9,98,114   9,30,529`),
];

const SEGMENT_ROW = 'Capital Expenditure   32,365   1,756   21,131   33,101   52,521   3,397   1,44,271';
const SEGMENTS = [['O2C', 32365], ['Oil and Gas', 1756], ['Retail', 21131],
  ['Digital Services', 33101], ['Others', 52521]].map(([segment, value]) => fact({
  concept: 'capex', definition_id: 'CAPEX.SEGMENT', entity_scope: 'segment', segment,
  period_end: NOW, value, source_sentence: SEGMENT_ROW,
}));
const SEGMENT_TOTAL = fact({
  concept: 'capex', definition_id: 'CAPEX.SEGMENT', period_end: NOW, value: 144271,
  source_sentence: SEGMENT_ROW,
});

const YEAR = { from: BEFORE, to: NOW };
const only = (flags, rule) => flags.filter((row) => row.rule === rule);

test('one concept moving in two directions is the flag that needs no threshold', () => {
  const [split] = signSplits({ facts: FACTS, ...YEAR });
  assert.equal(split.rule, 'definition_sign_split');
  assert.match(split.observation, /capex rose 10\.0% on CAPEX\.MANAGEMENT and fell 12\.2% on CAPEX\.CASH_PPE_INTANGIBLES/);
  assert.equal(split.magnitude, 0.222229);
  assert.equal(split.evidence.length, 2);
});

test('revenue rising on both definitions is not a sign split', () => {
  // Both revenue definitions grew - 9.8% and 10.7%. Two definitions
  // disagreeing about size is not two definitions disagreeing about direction.
  assert.equal(signSplits({ facts: FACTS, ...YEAR }).length, 1);
});

test('a flag never reaches a conclusion about the company', () => {
  const flags = review({ facts: [...FACTS, ...SEGMENTS, SEGMENT_TOTAL], period_end: NOW, prior_period_end: BEFORE }).flags;
  assert.ok(flags.length >= 4);
  assert.ok(flags.every((row) => row.judgement === null), 'a flag carried a judgement');
  assert.ok(flags.every((row) => typeof row.observation === 'string' && row.evidence));
});

test('the spread between definitions is reported against the smaller figure', () => {
  const spreads = definitionSpreads({ facts: FACTS, period_end: NOW });
  const capex = spreads.find((row) => row.observation.startsWith('capex'));
  assert.equal(capex.magnitude, 0.173737);
  assert.match(capex.observation, /from 122916 to 144271/);
  const revenue = spreads.find((row) => row.observation.startsWith('revenue'));
  assert.equal(revenue.magnitude, 0.06453);
});

test('a threshold is a convention and can be moved', () => {
  assert.equal(definitionSpreads({ facts: FACTS, period_end: NOW, threshold: 0.2 }).length, 0);
  assert.equal(definitionSpreads({ facts: FACTS, period_end: NOW, threshold: 0.01 }).length, 2);
  assert.equal(CONVENTIONS.definition_spread, 0.05);
});

test('a divergence carries the assumption that made it a divergence', () => {
  const [gap] = growthGaps({ facts: FACTS, ...YEAR });
  assert.match(gap.observation, /ebitda grew 13\.4% while cfo grew 7\.5%/);
  assert.equal(gap.magnitude, 0.058471);
  // The one judgement in this file is written down and travels with the flag,
  // so a reader who rejects the premise can dismiss the flag.
  assert.equal(gap.assumption, 'accrual earnings against the cash they produced');
  assert.ok(WATCHED_PAIRS.every((pair) => pair.why));
});

test('a concept disclosed several ways is left to the sign-split rule', () => {
  // Revenue has two definitions, so "revenue against cash" has no single
  // answer and pairing one of them arbitrarily would manufacture the finding.
  assert.equal(growthGaps({ facts: FACTS, ...YEAR }).length, 1);
  assert.deepEqual(WATCHED_PAIRS.map((pair) => pair.b), ['cfo', 'cfo']);
});

test('segments that do not sum become a pointer at the missing column', () => {
  const flags = review({ facts: [...FACTS, ...SEGMENTS, SEGMENT_TOTAL], period_end: NOW, prior_period_end: BEFORE }).flags;
  const [residual] = only(flags, 'segment_residual');
  assert.match(residual.observation, /sum to 140874 against a stated total of 144271, leaving 3397/);
  assert.match(residual.observation, /no unallocable or eliminations column was extracted/);
  assert.equal(residual.magnitude, 0.023546);
});

test('segments that do sum raise nothing', () => {
  const complete = [...SEGMENTS, fact({ concept: 'capex', definition_id: 'CAPEX.SEGMENT',
    entity_scope: 'segment', segment: 'Unallocable', period_end: NOW, value: 3397, source_sentence: SEGMENT_ROW }), SEGMENT_TOTAL];
  const flags = review({ facts: complete, period_end: NOW }).flags;
  assert.equal(only(flags, 'segment_residual').length, 0);
});

test('a stated figure the arithmetic cannot reach is flagged, not corrected', () => {
  // CONSTRUCTED: an issuer stating a free cash flow that is neither
  // 1,92,113 - 1,22,916 nor 1,92,113 - 1,44,271.
  const odd = fact({ concept: 'fcf', definition_id: 'FCF.CFO_MINUS_CASH_CAPEX',
    measurement_basis: 'cash', period_end: NOW, value: 58000,
    source_sentence: 'Free cash flow for the year was 58,000 crore.' });
  const flags = review({ facts: [...FACTS, odd], period_end: NOW }).flags;
  const [unexplained] = only(flags, 'unexplained_stated_figure');
  assert.match(unexplained.observation, /does not follow from any disclosed combination/);
  assert.match(unexplained.observation, /nearest is 10158 away/);
});

test('a figure filed under a contradicted definition is flagged', () => {
  // CONSTRUCTED: cash-capex free cash flow, filed as the management-capex one.
  const mislabelled = fact({ concept: 'fcf', definition_id: 'FCF.CFO_MINUS_MANAGEMENT_CAPEX',
    measurement_basis: 'cash', period_end: NOW, value: 69197,
    source_sentence: 'Free cash flow for the year was 69,197 crore.' });
  const flags = review({ facts: [...FACTS, mislabelled], period_end: NOW }).flags;
  const [mismatch] = only(flags, 'definition_mismatch');
  assert.match(mismatch.observation, /filed as FCF\.CFO_MINUS_MANAGEMENT_CAPEX but the arithmetic matches CAPEX\.CASH_PPE_INTANGIBLES/);
});

test('a restatement is measured against the original', () => {
  // CONSTRUCTED: next year's report restates FY25 capital expenditure.
  const restated = { ...FACTS[1], value: 129000, reported_in_document: 'RIL FY2026-27',
    original_or_restated: 'restated' };
  const [found] = fromVerification(checkRestatements([FACTS[1], restated]));
  assert.equal(found.rule, 'restatement');
  assert.match(found.observation, /changed by -2107 between documents, 1\.6% of the original/);
  assert.equal(found.magnitude, 0.016071);
});

test('a restatement inside the convention is not raised', () => {
  // CONSTRUCTED: a change of one crore in 1,31,107.
  const trivial = { ...FACTS[1], value: 131106, reported_in_document: 'RIL FY2026-27' };
  assert.equal(fromVerification(checkRestatements([FACTS[1], trivial])).length, 0);
});

test('a computed figure whose inputs have moved is flagged', () => {
  // CONSTRUCTED.
  const derived = calculate(FACTS, { definition_id: 'FCF.CFO_MINUS_CASH_CAPEX', period_end: NOW });
  const later = FACTS.map((row) => (row === FACTS[4]
    ? { ...row, value: 190000, reported_in_document: 'RIL FY2026-27' } : row));
  const [stale] = staleDerivations([...later, derived]);
  assert.equal(stale.rule, 'stale_derivation');
  assert.match(stale.observation, /computed from inputs that have since moved/);
});

test('a live computed figure is not flagged', () => {
  const derived = calculate(FACTS, { definition_id: 'FCF.CFO_MINUS_CASH_CAPEX', period_end: NOW });
  assert.deepEqual(staleDerivations([...FACTS, derived]), []);
});

test('something disclosed last year and not this year is named', () => {
  // CONSTRUCTED: the cash capex line absent from the current year.
  const dropped = FACTS.filter((row) => !(row.definition_id === 'CAPEX.CASH_PPE_INTANGIBLES' && row.period_end === NOW));
  const [gone] = droppedDisclosures({ facts: dropped, ...YEAR });
  assert.match(gone.observation, /CAPEX\.CASH_PPE_INTANGIBLES was disclosed for 2025-03-31 and is not disclosed for 2026-03-31/);
  assert.equal(gone.evidence[0].value, 139967);
});

test('nothing dropped raises nothing', () => {
  assert.deepEqual(droppedDisclosures({ facts: FACTS, ...YEAR }), []);
});

test('flags are ordered by a stated convention, never by a score', () => {
  const flags = review({ facts: [...FACTS, ...SEGMENTS, SEGMENT_TOTAL], period_end: NOW, prior_period_end: BEFORE }).flags;
  const positions = flags.map((row) => RULE_ORDER.indexOf(row.rule));
  assert.deepEqual(positions, [...positions].sort((a, b) => a - b));
  // Magnitudes from different rules measure different things and are never
  // compared: the sign split leads on rule order, not because 0.22 beats 0.17.
  assert.equal(flags[0].rule, 'definition_sign_split');
  const spreads = only(flags, 'definition_spread');
  assert.ok(spreads[0].magnitude > spreads[1].magnitude);
});

test('without a prior period, only the single-period rules run', () => {
  const flags = review({ facts: FACTS, period_end: NOW }).flags;
  assert.equal(only(flags, 'definition_sign_split').length, 0);
  assert.equal(only(flags, 'growth_gap').length, 0);
  assert.equal(only(flags, 'definition_spread').length, 2);
});

test('a clean filing raises nothing', () => {
  const clean = both('CFO.STATEMENT', 'cfo', 192113, 178703, '1,92,113   1,78,703');
  const flags = review({ facts: clean, period_end: NOW, prior_period_end: BEFORE }).flags;
  assert.deepEqual(flags, []);
});

test('reviewing never alters the facts it was given', () => {
  const facts = [...FACTS, ...SEGMENTS, SEGMENT_TOTAL];
  const before = JSON.stringify(facts);
  review({ facts, period_end: NOW, prior_period_end: BEFORE });
  assert.equal(JSON.stringify(facts), before);
});

test('rank leaves an empty review empty', () => {
  assert.deepEqual(rank([]), []);
  assert.deepEqual(rank(undefined), []);
});

test('a gap inside the convention is not raised', () => {
  // EBITDA and cash flow are 5.8 points apart. At a threshold of 10 points
  // that is not a divergence, and the rule must actually consult the number.
  assert.equal(growthGaps({ facts: FACTS, ...YEAR, threshold: 0.1 }).length, 0);
});

test('an ambiguous concept stays unpaired even where a pairing would fire', () => {
  // At two points, revenue against cash flow would clear the threshold on
  // either revenue definition - 2.3 points on one, 3.2 on the other. Picking
  // whichever came first would manufacture the finding, so neither is used.
  const gaps = growthGaps({ facts: FACTS, ...YEAR, threshold: 0.02 });
  assert.deepEqual(gaps.map((row) => row.evidence[0].concept), ['ebitda']);
});

test('a flag with no assumption says so rather than implying one', () => {
  const [split] = signSplits({ facts: FACTS, ...YEAR });
  assert.equal(split.assumption, null);
});

test('rule order beats magnitude when the two disagree', () => {
  // CONSTRUCTED: total income absent this year. That flag carries a magnitude
  // of 1 and sits last in RULE_ORDER, while the sign split is 0.22 and sits
  // first. Sorting by magnitude would invert them.
  const dropped = FACTS.filter((row) => !(row.definition_id === 'REVENUE.TOTAL_INCOME' && row.period_end === NOW));
  const flags = review({ facts: dropped, period_end: NOW, prior_period_end: BEFORE }).flags;
  assert.equal(flags[0].rule, 'definition_sign_split');
  assert.equal(flags[flags.length - 1].rule, 'disclosure_dropped');
  assert.equal(flags[0].magnitude < flags[flags.length - 1].magnitude, true);
});

test('a divergence from a base of zero is reported without a proportion', () => {
  // CONSTRUCTED: a concept disclosed as nil on one definition and not on
  // another. Dividing by zero would drop the flag; the divergence is real.
  const nil = [
    fact({ concept: 'ebitda', definition_id: 'EBITDA.REPORTED', period_end: NOW, value: 0,
      source_sentence: 'EBITDA of 0 crore.' }),
    fact({ concept: 'ebitda', definition_id: 'EBITDA.BEFORE_EXCEPTIONAL', period_end: NOW, value: 5000,
      source_sentence: 'EBITDA before exceptional items of 5,000 crore.' }),
  ];
  const [found] = definitionSpreads({ facts: nil, period_end: NOW });
  assert.match(found.observation, /from 0 to 5000, which is not expressible as a proportion of 0/);
  assert.equal(found.magnitude, null);
});

test('a withheld magnitude sorts last within its rule, not first', () => {
  const nil = [
    fact({ concept: 'ebitda', definition_id: 'EBITDA.REPORTED', period_end: NOW, value: 0, source_sentence: '0' }),
    fact({ concept: 'ebitda', definition_id: 'EBITDA.BEFORE_EXCEPTIONAL', period_end: NOW, value: 5000, source_sentence: '5,000' }),
  ];
  const ordered = rank([...definitionSpreads({ facts: [...FACTS, ...nil], period_end: NOW })]);
  assert.equal(ordered[ordered.length - 1].magnitude, null);
  assert.equal(ordered[0].magnitude, 0.173737);
});

test('a stated figure does not go stale; it gets restated', () => {
  // CONSTRUCTED: a stated free cash flow, with the cash flow beneath it moved.
  // Only a computed figure can stop following from its inputs - a stated one
  // never followed from them in the first place.
  const stated = fact({ concept: 'fcf', definition_id: 'FCF.CFO_MINUS_CASH_CAPEX',
    measurement_basis: 'cash', period_end: NOW, value: 69197,
    source_sentence: 'Free cash flow for the year was 69,197 crore.' });
  const moved = FACTS.map((row) => (row === FACTS[4]
    ? { ...row, value: 190000, reported_in_document: 'RIL FY2026-27' } : row));
  assert.deepEqual(staleDerivations([...moved, stated]), []);
});

test('a stated figure with no inputs in the filing is not called a stale derivation', () => {
  // CONSTRUCTED: an issuer states a free cash flow and discloses neither the
  // operating cash flow nor the capital expenditure under it. A computed
  // figure in that position has lost its inputs. A stated one never had them,
  // and reporting it as "computed from inputs that have since moved" would
  // describe the filing as something it is not.
  const stated = fact({ concept: 'fcf', definition_id: 'FCF.CFO_MINUS_CASH_CAPEX',
    measurement_basis: 'cash', period_end: NOW, value: 69197,
    source_sentence: 'Free cash flow for the year was 69,197 crore.' });
  assert.deepEqual(staleDerivations([stated]), []);
});

test('rank puts a withheld magnitude behind a measured zero', () => {
  // Ordering is tested directly: a withheld magnitude means "no proportion is
  // defined", which is not the same claim as "the proportion is nothing", and
  // treating the two as equal would interleave them arbitrarily.
  const of = (magnitude) => ({ rule: 'definition_spread', magnitude, observation: '', evidence: [], basis: 'facts', judgement: null });
  assert.deepEqual(rank([of(null), of(0), of(0.5)]).map((row) => row.magnitude), [0.5, 0, null]);
});
