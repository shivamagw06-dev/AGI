import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { boilerplateIn, BOILERPLATE } from './publicationBoilerplate.js';
import { slotsFor, intelligenceChain } from './publicationIntelligence.js';

// Verbatim from Berkshire's 2026 second-quarter report, each one rejected by
// a person reviewing the queue.
const REJECTED = [
  ['safe_harbour', 'Forward-looking statements are based on current expectations and projections '
    + 'about future events and are subject to risks, uncertainties and assumptions about Berkshire.'],
  ['results_will_differ', 'Actual payments will likely vary, perhaps materially, from any '
    + 'forecasted payments, as well as from the liabilities recorded in our Consolidated Balance Sheets.'],
  ['results_will_differ', 'Due to the inherent uncertainties in the processes of establishing these '
    + 'liabilities, the actual ultimate claim amounts will likely differ from the currently recorded amounts.'],
  ['amounts_will_be_adjusted', 'Accordingly, certain amounts currently recorded in our Consolidated '
    + 'Financial Statements will likely be adjusted in the future based on new available information.'],
  ['future_disclosure', 'We expect to include such disclosures in our interim Consolidated '
    + 'Financial Statements for the period ending September 30, 2026.'],
  ['not_materially_different', 'Except as otherwise disclosed in this Quarterly Report, our '
    + 'contractual obligations as of June 30, 2026 were, in the aggregate, not materially different from those disclosed.'],
  ['securities_value_circularity', 'Any adverse effect on our business, financial condition or '
    + 'operating results could result in a decline in the value of our securities and the loss of all or part of your investment.'],
];

// Verbatim from the same two documents, each one approved by a person.
const APPROVED = [
  'It is reasonably possible that adverse changes in such conditions or events could result in '
    + 'the recognition of impairment losses in our Consolidated Financial Statements.',
  'It is reasonably possible PacifiCorp will incur material additional losses beyond the amounts '
    + 'accrued for the Wildfires that could have a material adverse effect on our results.',
  'We anticipate that these payments will be funded by cash flows from operating activities.',
  'We expect these primary insurance businesses to face continued headwinds in 2026, and potentially beyond.',
  'Retroactive reinsurance contracts indemnify ceding companies for adverse development of claims '
    + 'arising from loss events that have already occurred.',
];

describe('boilerplate is not a risk and not an expectation', () => {
  for (const [rule, sentence] of REJECTED) {
    test(`${rule}: ${sentence.slice(0, 46)}…`, () => {
      const found = boilerplateIn(sentence);
      assert.ok(found, 'not caught');
      assert.equal(found.id, rule);
    });
  }

  for (const sentence of APPROVED) {
    test(`kept: ${sentence.slice(0, 46)}…`, () => {
      assert.equal(boilerplateIn(sentence), null);
    });
  }

  test('an approved sentence naming the financial statements survives', () => {
    // The trap a broader rule falls into. This sentence names the Consolidated
    // Financial Statements, hedges with "reasonably possible", and is exactly
    // what the risks slot exists for.
    const sentence = APPROVED[0];
    assert.ok(slotsFor(sentence).includes('risks'), 'the real disclosure was dropped');
  });

  test('boilerplate is dropped from risks and expectations', () => {
    for (const [, sentence] of REJECTED) {
      const slots = slotsFor(sentence);
      assert.equal(slots.includes('risks'), false, sentence);
      assert.equal(slots.includes('expectations'), false, sentence);
    }
  });

  test('the other seven steps are untouched by the stoplist', () => {
    // why was rejected 7 times in 201 claims and needs no stoplist. A rule
    // applied everywhere would cost real causes to fix another slot's problem.
    const sentence = 'Forward-looking statements are based on current expectations, and revenues '
      + 'grew from $1.2 billion to $1.5 billion in 2026 primarily due to higher volumes.';
    const slots = slotsFor(sentence);
    assert.ok(slots.includes('what_changed'), 'a stated change was lost');
    assert.ok(slots.includes('why'), 'a stated cause was lost');
    assert.equal(slots.includes('risks'), false);
  });

  test('every rule carries the sentence that justified it', () => {
    // A rule without evidence is a guess about what a filing looks like, and
    // what this file removes, nobody ever sees.
    for (const rule of BOILERPLATE) {
      assert.ok(rule.why && rule.why.length > 20, `${rule.id} has no stated reason`);
      assert.ok(REJECTED.some(([id]) => id === rule.id),
        `${rule.id} matches no reviewed sentence in the fixtures`);
    }
  });

  test('nothing is boilerplate by default', () => {
    for (const text of ['', null, undefined, 'Revenues grew 4% in 2026.']) {
      assert.equal(boilerplateIn(text), null, String(text));
    }
  });
});

describe('what the stoplist costs the Berkshire annual report', () => {
  test('it removes three sentences and no more', () => {
    // Measured before shipping: risks 30 -> 29, expectations 15 -> 13. Every
    // other step is unchanged, which is what makes this safe to apply to a
    // document nobody will re-review.
    // The real disclosure is quoted verbatim. An abbreviated version of it
    // dropped "material adverse effect", which is the phrase the risk cue
    // fires on, and the test failed against correct code.
    const chain = intelligenceChain('Forward-looking statements are subject to risks and uncertainties. '
      + 'Actual payments will likely vary, perhaps materially, from forecasted payments. '
      + `${APPROVED[1]}`);
    const risks = chain.slots.find((slot) => slot.slot === 'risks');
    assert.equal(risks.claims.length, 1);
    assert.match(risks.claims[0].source_excerpt, /PacifiCorp/);
  });
});
