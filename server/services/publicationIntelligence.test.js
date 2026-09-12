import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import {
  CHAIN, STATED_SLOTS, INFERRED_SLOTS,
  sentences, figuresIn, metricIn, changeIn, slotsFor, intelligenceChain,
  runningHeaders, isPageMarker, autoApproved,
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

  test('a span of years is not a change', () => {
    // Norges Bank's annual report is full of these, and three of the four
    // changes found in it were date ranges - each given a delta, each with no
    // unit, each published by the auto-approval rule:
    //
    //   "Measured over the entire period from 1998 to 2025, the realised
    //    tracking error has been 0.62 percentage point"   -> up 27
    //
    // Berkshire's report had two of its own that had been live all along:
    // "maturity dates ranging from 2035 to 2056" -> up 21.
    for (const span of [
      'Measured over the entire period from 1998 to 2025, the tracking error has been 0.62 points.',
      'In the period from 2013 to 2025, annual management costs have been 0.05 percent.',
      'In 2025, BHE subsidiaries issued $4.3 billion of term debt with maturity dates ranging '
        + 'from 2035 to 2056.',
    ]) {
      const change = changeIn(span);
      assert.ok(!change || change.delta === null, `read a span as a change: ${span}`);
    }
  });

  test('a stated unit makes two year-like numbers a change again', () => {
    // The years are only decisive when nothing says what is being measured.
    const change = changeIn('the ratio moved from 2,013% to 2,025%');
    assert.equal(change.delta, 12);
  });

  test('a refused reading does not stop another pattern matching', () => {
    // A sentence can carry both a date range and a real change, and the date
    // range must not consume it.
    const change = changeIn('Over the period from 2013 to 2025 the loss ratio was 71.8% in 2024 '
      + 'and 81.0% in 2023.');
    assert.equal(change.from, 81.0);
    assert.equal(change.to, 71.8);
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

  test('a change claim says whose arithmetic it is', () => {
    // This test previously asserted every change claim was `derived`, which
    // was wrong and understated the rows. "an increase of 2.7 percentage
    // points compared to 2024" is the filer's own subtraction; calling it
    // derived claimed credit for arithmetic this code never performed.
    for (const claim of bySlot.what_changed.claims) {
      assert.ok(claim.change, 'a change claim without a change');
      assert.equal(claim.basis, claim.change.delta_stated ? 'stated' : 'derived');
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

describe('page furniture in a pasted report', () => {
  test('a line repeated across the document is a running header', () => {
    const text = `${'Notes to Consolidated Financial Statements\nSome body text here for the page.\n'.repeat(5)}`;
    assert.ok(runningHeaders(text).has('Notes to Consolidated Financial Statements'));
  });

  test('three repeats is not enough, and a sentence is never furniture', () => {
    const thrice = 'A heading repeated thrice\nbody\n'.repeat(3);
    assert.ok(!runningHeaders(thrice).has('A heading repeated thrice'));
    // Terminal punctuation disqualifies it however often it repeats: a
    // genuinely repeated sentence is a claim to collapse, not furniture.
    const sentence = 'We remain disciplined about price.\nbody\n'.repeat(9);
    assert.ok(!runningHeaders(sentence).has('We remain disciplined about price.'));
  });

  test('a running header does not become the prefix of the next sentence', () => {
    // "K-79 Notes to Consolidated Financial Statements (2)Significant business
    // acquisitions On January 31, 2023, we acquired..." was a real claim. It
    // quoted the page template instead of the filer.
    const page = 'Notes to Consolidated Financial Statements\n'
      + 'In January 2024, we acquired the remaining interests for $2.6 billion.\n';
    const found = sentences(page.repeat(4));
    assert.ok(found.length > 0);
    for (const item of found) {
      assert.ok(!/Notes to Consolidated/.test(item.text), item.text);
    }
  });

  test('a page marker is dropped by its shape, not by repetition', () => {
    // Each page number is nearly unique - "K-116" repeated eleven times but
    // "K-38", "K-79" and "K-25" appeared once or twice and all three reached
    // a claim.
    for (const marker of ['K-38', 'K-116', 'A-1', '2025', '101', 'F-4']) {
      assert.equal(isPageMarker(marker), true, marker);
    }
    for (const notMarker of ['GEICO', 'BNSF', 'Total 2025', 'We expect less.']) {
      assert.equal(isPageMarker(notMarker), false, notMarker);
    }
    const found = sentences('K-38\nPremiums written increased $694 million in 2024 compared to 2023.');
    assert.equal(found.length, 1);
    assert.equal(found[0].text,
      'Premiums written increased $694 million in 2024 compared to 2023.');
  });

  test('a repeated segment heading is a heading, not furniture', () => {
    // The ordering inside sentences() is load-bearing and was asserted only in
    // a comment: "Manufacturing, Service and Retailing" appears eight times in
    // the report, so consulting the furniture set before segmentHeading drops
    // it and every sentence under it loses its attribution. Checking furniture
    // first passes every other test in this file.
    const text = 'Manufacturing, Service and Retailing\nRevenues rose in 2025 across the group.\n'
      .repeat(5);
    assert.ok(runningHeaders(text).has('Manufacturing, Service and Retailing'),
      'the heading does repeat often enough to look like furniture');
    const found = sentences(text);
    assert.ok(found.length > 0);
    assert.equal(found[0].heading, 'manufacturing',
      'a repeated segment heading was discarded as page furniture');
  });

  test('dropping furniture joins a sentence that wrapped across the page break', () => {
    // Flushing the buffer at a page header would cut the sentence in half.
    // Dropping the header and carrying on lets the halves meet.
    const across = 'The volumes increase was primarily due to higher intermodal\n'
      + 'K-42\n'
      + 'shipments resulting from higher West Coast imports in 2025.\n';
    const found = sentences(across);
    assert.equal(found.length, 1);
    assert.match(found[0].text, /higher intermodal shipments resulting from/);
  });
});

describe('the same sentence twice is one finding', () => {
  test('a sentence repeated in the document yields one claim per slot', () => {
    // The yen borrowing terms appear in both the MD&A and the parent-company
    // note. Two rows of identical words help no reviewer, they consumed the
    // per-slot bound, and they made one INSERT touch the same row twice -
    // which Postgres rejects outright, losing every fact in the run.
    const line = 'The borrowings have interest rates ranging from 1.35% to 3.12% '
      + 'and maturity dates ranging from 2028 to 2055.';
    const chain = intelligenceChain(`${line}\n\nUnrelated filler text sits here.\n\n${line}`,
      { perSlot: 50 });
    const changed = chain.slots.find((slot) => slot.slot === 'what_changed');
    assert.equal(changed.claims.length, 1);
    assert.equal(changed.found, 1);
  });

  test('no two claims in one slot share an excerpt', () => {
    // The uniqueness the database enforces, asserted where it is produced.
    for (const slot of intelligenceChain(FIXTURE, { perSlot: 500 }).slots) {
      const excerpts = slot.claims.map((claim) => claim.source_excerpt);
      assert.equal(new Set(excerpts).size, excerpts.length, `${slot.slot} repeats an excerpt`);
    }
  });

  test('the same sentence may still answer two different steps', () => {
    // Deduplication is per slot, not across the chain. "GEICO's expense ratio
    // was 9.7% in 2024, unchanged from 2023" is an amount and a change, and
    // collapsing it to one would drop half of what it says.
    const line = "GEICO’s expense ratio was 9.7% in 2024, unchanged from 2023.";
    const filled = intelligenceChain(line).slots
      .filter((slot) => slot.claims.length)
      .map((slot) => slot.slot);
    assert.deepEqual(filled.sort(), ['how_much', 'what_changed']);
  });
});

describe('nothing is dropped at ingest', () => {
  test('every claim found comes back by default', () => {
    // The bound used to default to 25 and was applied where claims are made,
    // so storage inherited it: 509 of the 654 claims in a 557,000-character
    // report were discarded, keeping whichever 25 appeared first in document
    // order. Asking that store about BNSF's freight then searched 25 of 142.
    //
    // The input has to exceed the old default or the test proves nothing. Run
    // against the fixture alone this passed with the cap restored, because no
    // slot in it holds 25 claims - the same inert-guard mistake as the
    // heading bound that counted paragraphs in a document with no blank
    // lines.
    const many = Array.from({ length: 40 },
      (unused, index) => `Our insurance float stood at $${120 + index} billion in ${1980 + index}.`)
      .join('\n\n');
    const chain = intelligenceChain(many);
    const amounts = chain.slots.find((slot) => slot.slot === 'how_much');
    assert.equal(amounts.found, 40, 'the input should yield 40 distinct amounts');
    assert.equal(amounts.claims.length, 40, 'claims were dropped at ingest');
    assert.equal(amounts.truncated, false);

    for (const slot of intelligenceChain(FIXTURE).slots) {
      assert.equal(slot.claims.length, slot.found, `${slot.slot} came back short`);
    }
  });

  test('a caller that wants a sample asks for one, and is told it got one', () => {
    const sample = intelligenceChain(FIXTURE, { perSlot: 1 });
    const changed = sample.slots.find((slot) => slot.slot === 'what_changed');
    assert.equal(changed.claims.length, 1);
    assert.equal(changed.truncated, true);
    assert.ok(changed.found > 1);
  });
});

describe('what may be published without a person reading it', () => {
  const claims = (text) => intelligenceChain(text).slots.flatMap((slot) => slot.claims);

  test('a change stating both endpoints needs no reviewer', () => {
    // The delta is a subtraction anyone can check against the sentence.
    const [claim] = claims("GEICO’s loss ratio was 71.8% in 2024 and 81.0% in 2023.")
      .filter((item) => item.slot === 'what_changed');
    assert.equal(claim.basis, 'derived');
    assert.equal(autoApproved(claim), true);
  });

  test('a change the filer computed itself needs no reviewer either', () => {
    // No arithmetic to check: the move is in the sentence. `from` is null and
    // the row says so, which is different from the row being wrong.
    const [claim] = claims("GEICO’sexpense ratio was 12.4% in 2025, an increase of "
      + '2.7 percentage points compared to 2024.')
      .filter((item) => item.slot === 'what_changed');
    assert.equal(claim.change.delta_stated, true);
    assert.equal(claim.change.from, null);
    assert.equal(claim.basis, 'stated');
    assert.equal(autoApproved(claim), true);
  });

  test('a change with no usable move is held back', () => {
    // Constructed, because no pattern currently produces one. The rule must
    // refuse it anyway: a change row whose delta is unknown is the one case
    // where a reader would supply the missing number themselves.
    assert.equal(autoApproved({ slot: 'what_changed', change: { delta: null } }), false);
    assert.equal(autoApproved({ slot: 'what_changed', change: null }), false);
    assert.equal(autoApproved(null), false);
  });

  test('an amount naming a metric the filer used needs no reviewer', () => {
    const [claim] = claims('our insurance float stood at $176 billion at year-end.')
      .filter((item) => item.slot === 'how_much');
    assert.equal(claim.metric, 'float');
    assert.equal(autoApproved(claim), true);
  });

  test('a figure with no named metric is not an amount and is not approved', () => {
    const [claim] = claims('The insurance businesses returned $29 billion to Berkshire.')
      .filter((item) => item.slot === 'what_happened');
    assert.equal(claim.metric, null);
    assert.equal(autoApproved(claim), false);
  });

  test('every cue-matched slot waits for a person, without exception', () => {
    // `why`, `risks`, `how` and `expectations` are a regular expression's
    // guess at what a sentence is doing. The expectations slot runs at about
    // half precision - "we expect the resolution periods will be very long"
    // is contract mechanics sitting beside "we expect to write less
    // reinsurance premium" - and no rule separates them.
    const cueMatched = ['why', 'risks', 'how', 'expectations'];
    const chain = intelligenceChain(FIXTURE);
    let checked = 0;
    for (const slot of chain.slots) {
      if (!cueMatched.includes(slot.slot)) continue;
      for (const claim of slot.claims) {
        assert.equal(autoApproved(claim), false, `${slot.slot}: ${claim.source_excerpt}`);
        checked += 1;
      }
    }
    assert.ok(checked > 5, `only ${checked} cue-matched claims to check`);
  });

  test('an approved claim still carries the sentence it came from', () => {
    // Auto-approval is what makes provenance load-bearing rather than
    // decorative: these rows reach a page with nobody having read them.
    const flat = FIXTURE.replace(/\s+/g, ' ');
    let checked = 0;
    for (const claim of claims(FIXTURE).filter(autoApproved)) {
      assert.ok(flat.includes(claim.source_excerpt), claim.source_excerpt);
      checked += 1;
    }
    assert.ok(checked > 3, `only ${checked} approved claims to check`);
  });
});
