import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import {
  CHAIN, STATED_SLOTS, INFERRED_SLOTS,
  sentences, figuresIn, metricIn, changeIn, slotsFor, intelligenceChain,
} from './publicationIntelligence.js';

/**
 * The fixture is real prose from Berkshire's 2025 annual report, pasted the
 * way it arrives out of the PDF - wrapped mid-sentence, with one word run into
 * the next where the PDF lost a space ("GEICO'sexpense ratio").
 *
 *   server/tests/fixtures/publications/berkshire-2025-prose.txt
 *
 * Written prose is here rather than clean examples because the failures worth
 * catching are the ones invented input does not have: rhetoric that reads like
 * causation, a mitigation that reads like a hazard, a metric defined in terms
 * of a second metric, and a stated delta with only one endpoint.
 */
const FIXTURE = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '..', 'tests', 'fixtures', 'publications',
    'berkshire-2025-prose.txt'),
  'utf8',
);

describe('the shape of the chain', () => {
  test('all nine steps come back in the order the chain is asked in', () => {
    assert.deepEqual(CHAIN.map((step) => step.slot), [
      'what_happened', 'why', 'how', 'how_much', 'what_changed',
      'expectations', 'risks', 'catalysts', 'so_what',
    ]);
    assert.deepEqual(intelligenceChain(FIXTURE).slots.map((s) => s.slot),
      CHAIN.map((step) => step.slot));
  });

  test('catalysts and so-what are declared unfillable, with the reason', () => {
    // The two slots that are analysis. Returning them empty with a reason is
    // the point: a caller renders the gap. Silently omitting them would let
    // seven slots pass for the whole chain, and filling them from a cue phrase
    // would look identical to filling them from understanding.
    assert.deepEqual(INFERRED_SLOTS, ['catalysts', 'so_what']);
    for (const slot of intelligenceChain(FIXTURE).slots) {
      if (!INFERRED_SLOTS.includes(slot.slot)) continue;
      assert.equal(slot.claims.length, 0);
      assert.equal(slot.basis, 'inferred');
      assert.match(slot.reason, /\S/);
    }
  });

  test('a stated slot promises a sentence and a derived slot promises arithmetic', () => {
    const basis = Object.fromEntries(CHAIN.map((step) => [step.slot, step.basis]));
    assert.equal(basis.what_changed, 'derived');
    for (const slot of STATED_SLOTS.filter((s) => s !== 'what_changed')) {
      assert.equal(basis[slot], 'stated');
    }
  });
});

describe('reading a change the document states', () => {
  test('a stated delta is not solved for its missing endpoint', () => {
    // "an increase of 2.7 percentage points compared to 2024" gives the 2025
    // value and the move. 12.4 - 2.7 = 9.7 and the document does say 9.7%
    // elsewhere - but on the 2024 comparison basis, in a different section, a
    // year earlier. Subtracting here would manufacture an endpoint that
    // happens to be right in this report and would be wrong in one that
    // restates the base.
    const change = changeIn("GEICO’sexpense ratio (underwriting expense to premiums earned) "
      + 'was 12.4% in 2025, an increase of 2.7 percentage points compared to 2024.');
    assert.equal(change.pattern, 'stated_delta');
    assert.equal(change.delta, 2.7);
    assert.equal(change.direction, 'up');
    assert.equal(change.from, null);
    assert.equal(change.delta_stated, true);
  });

  test('a decrease of n points is a negative delta', () => {
    const change = changeIn('The ratio was 8.0% in 2025, a decrease of 1.5 percentage points compared to 2024.');
    assert.equal(change.delta, -1.5);
    assert.equal(change.direction, 'down');
  });

  test('"unchanged from" is a change with a delta of zero, not a miss', () => {
    // A value that did not move is a finding. Reading this sentence as a loose
    // year comparison loses it, which is why the pattern is tried first.
    const change = changeIn('GEICO’sexpense ratio was 9.7% in 2024, unchanged from 2023.');
    assert.equal(change.pattern, 'unchanged');
    assert.equal(change.from, 9.7);
    assert.equal(change.to, 9.7);
    assert.equal(change.delta, 0);
    assert.equal(change.direction, 'unchanged');
  });

  test('two values in two years are read as a change with the newer as the endpoint', () => {
    const change = changeIn('GEICO’s loss ratio was 71.8% in 2024 and 81.0% in 2023.');
    assert.equal(change.to, 71.8);
    assert.equal(change.to_period, '2024');
    assert.equal(change.from, 81.0);
    assert.equal(change.from_period, '2023');
    assert.equal(change.direction, 'down');
  });

  test('a from/to pair across years is read with both endpoints and the delta computed', () => {
    const change = changeIn('the score rose from 27% in 2022 to 35% in 2025');
    assert.equal(change.from, 27);
    assert.equal(change.to, 35);
    assert.equal(change.from_period, '2022');
    assert.equal(change.to_period, '2025');
    assert.equal(change.delta, 8);
    assert.equal(change.kind, 'percent');
  });

  test('a bare endpoint takes the scale its partner states', () => {
    // "from $88 billion to $176 billion" writes the scale twice; plenty of
    // sentences write it once. Where neither endpoint states one the kind is
    // null, and nothing downstream may guess it.
    assert.equal(changeIn('grew from 27 to 35 percent').kind, 'percent');
    assert.equal(changeIn('rose from $88 billion to $176 billion').kind, 'money_billion');
    assert.equal(changeIn('moved from 27 to 35').kind, null);
  });

  test('a sentence with no change returns null rather than an empty change', () => {
    assert.equal(changeIn('We have always prioritized underwriting discipline over volume.'), null);
    assert.equal(changeIn(''), null);
  });
});

describe('naming a metric only when the document names it', () => {
  test('the earliest name wins, not the longest', () => {
    // The defect this replaced: a longest-first read over the whole sentence
    // labelled the expense ratio "premiums earned", picking the denominator
    // out of the metric's own parenthetical definition.
    assert.equal(
      metricIn("GEICO’sexpense ratio (underwriting expense to premiums earned) was 12.4% in 2025."),
      'expense ratio',
    );
    assert.equal(
      metricIn('GEICO’s loss ratio (losses and LAE to premiums earned) was 72.3% in 2025.'),
      'loss ratio',
    );
  });

  test('a figure whose metric is not on the list keeps its figure and gets no name', () => {
    const sentence = 'The insurance businesses ultimately returned $29 billion to Berkshire in the year.';
    assert.equal(metricIn(sentence), null);
    assert.equal(figuresIn(sentence).length, 1);
    // It still reports as something that happened. An unnamed quantity is a
    // fact; an invented name for it is not.
    assert.ok(slotsFor(sentence).includes('what_happened'));
  });
});

describe('figures as written', () => {
  test('money keeps the scale the document states and nothing is multiplied', () => {
    const [figure] = figuresIn('our insurance float stood at $176 billion.');
    assert.deepEqual(figure, { raw: '$176 billion', value: 176, scale: 'billion', kind: 'money' });
  });

  test('money with no stated scale carries a null scale', () => {
    const [figure] = figuresIn('a charge of $1,250 was recorded.');
    assert.equal(figure.value, 1250);
    assert.equal(figure.scale, null);
  });

  test('percentage points are a different kind from percent', () => {
    const kinds = figuresIn('was 12.4% in 2025, an increase of 2.7 percentage points')
      .map((figure) => figure.kind);
    assert.deepEqual(kinds, ['percent', 'percentage_points']);
  });
});

describe('what a slot refuses', () => {
  test('rhetoric that reads like causation does not fill why', () => {
    // "reflected" earns its place in the causal cues on sentences like
    // "reflecting lower interest income". On a shareholder letter it also
    // lands on this, which explains nothing quantitative about the business.
    const sentence = 'I admired how they worked together to build an enterprise '
      + 'that reflected their beliefs about business and life.';
    assert.deepEqual(slotsFor(sentence), []);
  });

  test('a mitigation is not a risk', () => {
    // The first draft used a bare /wildfire/ cue and filed this - BHE acting
    // on the hazard - as the hazard itself.
    const sentence = 'On wildfire risk, BHE has taken a leadership role, working with '
      + 'regulators, public officials, and the communities it serves.';
    assert.ok(!slotsFor(sentence).includes('risks'));
  });

  test('a cause with no actor is not a response', () => {
    // Both of these filled `how` until the cue required a first-person
    // subject. Each is a why: the second even says "due to".
    assert.ok(!slotsFor('the industry enters an investment cycle, driven by rising '
      + 'electricity demand and by increasing wildfire risk').includes('how'));
    assert.ok(!slotsFor('The largest revenue declines were experienced by the Transportation '
      + 'Products group (18.2%), primarily due to reduced volume.').includes('how'));
    assert.ok(slotsFor('In 2025, we reduced estimated ultimate pre-2025 accident years’ '
      + 'claim liabilities by $1.1 billion.').includes('how'));
  });

  test('a quantitative slot needs a quantity; a forward-looking one does not', () => {
    // "we expect accountability" fires an expectation cue and forecasts
    // nothing, but requiring a figure of this slot would also discard "we
    // expect to write less reinsurance premium", which is the most useful
    // forward statement in the report.
    assert.ok(slotsFor('As long as these phases of the cycle endure, we expect to write '
      + 'less reinsurance premium.').includes('expectations'));
    assert.deepEqual(slotsFor('Every action deepens the trust placed in Berkshire, '
      + 'reflecting a deliberate effort.'), []);
  });
});

describe('sentences out of a pasted PDF', () => {
  test('a sentence wrapped over several lines is put back together', () => {
    const found = sentences(FIXTURE).map((s) => s.text);
    assert.ok(found.some((text) => text
      === 'As long as these phases of the cycle endure, we expect to write less reinsurance premium.'));
  });

  test('a paragraph break is not a sentence break', () => {
    const found = sentences('One heading here\n\nThe sentence under it runs on to a full stop.');
    assert.equal(found.length, 1);
    assert.equal(found[0].text, 'The sentence under it runs on to a full stop.');
    assert.equal(found[0].paragraph, 1);
  });

  test('a table that lost its line breaks is not returned as a sentence', () => {
    const long = `Apple Inc. 1.6% 6,255 61,962 280 ${'American Express Company 22.1% 1,287 56,088 479 '.repeat(9)}`;
    assert.deepEqual(sentences(long), []);
  });
});

describe('the chain over a real report', () => {
  const chain = intelligenceChain(FIXTURE, { perSlot: 50 });
  const bySlot = Object.fromEntries(chain.slots.map((slot) => [slot.slot, slot]));

  test('every claim carries a sentence that is in the document', () => {
    const flat = FIXTURE.replace(/\s+/g, ' ');
    let checked = 0;
    for (const slot of chain.slots) {
      for (const claim of slot.claims) {
        assert.ok(flat.includes(claim.source_excerpt),
          `claim not found in the document: ${claim.source_excerpt}`);
        assert.equal(typeof claim.paragraph, 'number');
        checked += 1;
      }
    }
    // Not an empty pass. If the extractor returns nothing this test must fail
    // rather than report that all zero claims were traceable.
    assert.ok(checked > 10, `only ${checked} claims to check`);
  });

  test('the count of what was found is distinct sentences, not slot fills', () => {
    const fills = chain.slots.reduce((total, slot) => total + slot.found, 0);
    // One sentence can be a change, a why and an amount at once. Adding the
    // buckets up would report it three times.
    assert.ok(chain.matched_sentences < fills);
    assert.ok(chain.matched_sentences <= chain.sentences);
  });

  test('the per-slot bound is reported rather than applied silently', () => {
    const tight = intelligenceChain(FIXTURE, { perSlot: 1 });
    const changed = tight.slots.find((slot) => slot.slot === 'what_changed');
    assert.equal(changed.claims.length, 1);
    assert.equal(changed.truncated, true);
    assert.ok(changed.found > 1);
    assert.equal(bySlot.what_changed.truncated, false);
  });

  test('the report yields the changes, amounts and forward statements it states', () => {
    const excerpts = (slot) => bySlot[slot].claims.map((claim) => claim.source_excerpt).join(' | ');
    assert.match(excerpts('what_changed'), /expense ratio .{0,80}12\.4% in 2025/);
    assert.match(excerpts('how_much'), /float .{0,120}\$176 billion/);
    assert.match(excerpts('expectations'), /less reinsurance premium/);
    assert.match(excerpts('why'), /driven by higher interest income/);
    assert.match(excerpts('risks'), /material adverse effect/);
    assert.match(excerpts('how'), /always prioritized underwriting discipline/);
  });

  test('a change claim carries the arithmetic and a stated claim does not', () => {
    for (const claim of bySlot.what_changed.claims) {
      assert.equal(claim.basis, 'derived');
      assert.ok(claim.change, 'a change claim without a change');
    }
    for (const claim of bySlot.how_much.claims) {
      assert.equal(claim.basis, 'stated');
      assert.equal(claim.change, null);
    }
  });

  test('an empty paste yields the chain with nothing in it, not an error', () => {
    const empty = intelligenceChain('');
    assert.equal(empty.sentences, 0);
    assert.equal(empty.matched_sentences, 0);
    assert.equal(empty.slots.length, 9);
    assert.equal(empty.slots.every((slot) => slot.claims.length === 0), true);
  });
});
