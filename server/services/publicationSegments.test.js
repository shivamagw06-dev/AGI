import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import {
  SEGMENTS, THEMES, SEGMENT_LABELS, THEME_LABELS,
  segmentHeading, segmentIn, themesIn, attributeSegment,
} from './publicationSegments.js';
import { sentences, intelligenceChain, selectClaims, looksTabular } from './publicationIntelligence.js';

const FIXTURE = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '..', 'tests', 'fixtures', 'publications',
    'berkshire-2025-prose.txt'),
  'utf8',
);

describe('a heading is a whole line that is a segment name', () => {
  test('a segment name on its own line is a heading', () => {
    assert.equal(segmentHeading('Reinsurance Group'), 'reinsurance');
    assert.equal(segmentHeading('GEICO'), 'geico');
    assert.equal(segmentHeading('  BNSF  '), 'bnsf');
    assert.equal(segmentHeading('Renewables'), 'bhe');
  });

  test('a table artefact on its own line is not a heading', () => {
    // A pasted report is full of these: 'Total' four times, 'Net' five,
    // 'Other' five, 'December 31, 2025' seven. Requiring the whole line to be
    // a known segment name is what keeps every one of them out.
    for (const line of ['Total', 'Net', 'Other', 'December 31, 2025', 'Liabilities',
      'Value', 'Accident', 'K-116', 'Percentage change']) {
      assert.equal(segmentHeading(line), null, `"${line}" became a heading`);
    }
  });

  test('prose mentioning a segment is not a heading for it', () => {
    // Otherwise every sentence naming GEICO resets the section, and the
    // paragraph after a passing mention inherits the wrong business.
    assert.equal(segmentHeading("GEICO’s expense ratio was 12.4% in 2025."), null);
    assert.equal(segmentHeading('We expect BNSF to continue improving.'), null);
  });

  test('a line containing a segment name is not a heading unless it is the name', () => {
    // These carry no terminal punctuation, so the sentence guard does not
    // reach them - only the whole-line rule does. A substring test passes
    // every other assertion in this file and fails here, which is the point:
    // a table column header reading "GEICO expense ratio and combined ratio"
    // would otherwise reset the section to GEICO.
    assert.equal(segmentHeading('GEICO expense ratio and combined ratio detail'), null);
    assert.equal(segmentHeading('BNSF freight car and locomotive counts'), null);
    assert.equal(segmentHeading('Reinsurance Group premiums written by line'), null);
  });

  test('a long line is not a heading even if it starts with a segment name', () => {
    assert.equal(
      segmentHeading('BNSF and its subsidiaries operate one of the largest railroad systems'),
      null,
    );
  });
});

describe('attributing a claim to a business', () => {
  test('what the sentence says beats what it sits under', () => {
    // A heading is inherited by everything beneath it, including a paragraph
    // that has moved on. The sentence naming its own business is the better
    // evidence and says so.
    assert.deepEqual(
      attributeSegment('BNSF’s operating ratio improved in 2025.', 'geico'),
      { segment: 'bnsf', segment_source: 'in_sentence' },
    );
  });

  test('a sentence naming nothing inherits the section it sits under', () => {
    assert.deepEqual(
      attributeSegment('We expect to write less premium if pricing weakens.', 'reinsurance'),
      { segment: 'reinsurance', segment_source: 'from_heading' },
    );
  });

  test('no sentence and no section leaves the segment null, not guessed', () => {
    assert.deepEqual(
      attributeSegment('Regulatory changes may adversely impact our future operating results.', null),
      { segment: null, segment_source: null },
    );
  });

  test('every segment and theme has a label for a page to render', () => {
    for (const entry of SEGMENTS) assert.match(SEGMENT_LABELS[entry.segment], /\S/);
    for (const entry of THEMES) assert.match(THEME_LABELS[entry.theme], /\S/);
  });
});

describe('themes a sentence carries', () => {
  test('a sentence carrying two market conditions reports both', () => {
    // Someone asking about capacity and someone asking about pricing should
    // each find this sentence.
    const themes = themesIn('As the year progressed, additional capital entered the market, '
      + 'resulting in lower pricing or decelerating rate increases in several important lines.');
    assert.ok(themes.includes('competition'));
    assert.ok(themes.includes('pricing'));
  });

  test('AI power demand is a theme in its own right', () => {
    assert.deepEqual(
      themesIn('the industry enters a significant investment cycle, driven by rising electricity '
        + 'demand from artificial intelligence computing'),
      ['power_demand'],
    );
  });

  test('a generic risk factor is not a tariff-policy statement', () => {
    // A bare 'regulatory' phrase put "Regulatory changes may adversely impact
    // our future operating results" under renewable tax and tariff policy.
    assert.deepEqual(
      themesIn('Regulatory changes may adversely impact our future operating results.'),
      [],
    );
    assert.ok(themesIn('changes to renewable energy tax credits and tariffs')
      .includes('policy_and_tariffs'));
  });

  test('a sentence about nothing on the lists carries no theme', () => {
    assert.deepEqual(themesIn('I admired how they worked together.'), []);
    assert.deepEqual(themesIn(''), []);
  });
});

describe('a heading expires', () => {
  test('a heading does not carry to the end of the document', () => {
    // Unbounded, the first draft gave 661 of 665 claims a segment: "Pilot"
    // collected 88 because the heading was set once and never cleared, and
    // the notes and risk factors, which have no segment headings at all,
    // inherited whatever preceded them.
    const body = Array.from({ length: 40 },
      (unused, index) => `This is sentence number ${index} of the passage body.`).join('\n');
    const found = sentences(`BNSF\n${body}`);
    assert.equal(found[0].heading, 'bnsf');
    assert.equal(found.at(-1).heading, null,
      'a heading still applied 40 sentences later');
  });

  test('the bound is counted in sentences, because a paste has no blank lines', () => {
    // The first version of this bound counted passages. The report had two
    // blank lines in 7,194, so the passage counter only advanced at the next
    // heading and the bound could never fire - it changed the segment counts
    // by nothing at all.
    const oneParagraph = Array.from({ length: 40 },
      (unused, index) => `Sentence ${index} sits in a single unbroken passage here.`).join('\n');
    const found = sentences(`GEICO\n${oneParagraph}`);
    assert.equal(new Set(found.map((item) => item.paragraph)).size, 1,
      'the whole body should be one passage');
    assert.ok(found.some((item) => item.heading === null),
      'the bound never fired inside a single passage');
  });

  test('a heading is taken out of the text rather than glued to the next sentence', () => {
    // Before headings were detected, this came out as "Reinsurance Group Our
    // reinsurance operations face similar dynamics" - a claim whose quoted
    // excerpt carried a word the sentence does not contain.
    const found = sentences(FIXTURE);
    assert.ok(!found.some((item) => /Reinsurance Group Our/.test(item.text)));
    const first = found.find((item) => /Our reinsurance operations/.test(item.text));
    assert.equal(first.text, 'Our reinsurance operations face similar dynamics.');
    assert.equal(first.heading, 'reinsurance');
  });
});

describe('a table that survived the length cap', () => {
  test('a row of cells is not prose', () => {
    // 384 characters, under the cap, no verb - and it answered a question
    // about freight because "freight cars" is in the row.
    assert.equal(looksTabular('Land, track structure and other roadway $ 76,764 $ 74,093 '
      + 'Locomotives, freight cars and other equipment 15,772 15,766 Construction in progress '
      + '2,163 1,813 94,699 91,672'), true);
  });

  test('prose carrying figures is still prose', () => {
    assert.equal(looksTabular('In 2025, Berkshire produced $46 billion of net cash flows from '
      + 'operating activities, compared to a five-year average of more than $40 billion.'), false);
    assert.equal(looksTabular("GEICO’s loss ratio was 71.8% in 2024 and 81.0% in 2023."), false);
  });

  test('a short line is left alone', () => {
    assert.equal(looksTabular('$ 76,764 $ 74,093'), false);
  });

  test('a table row never reaches a sentence', () => {
    // looksTabular can be correct and still be wired to nothing. Removing the
    // call from sentences() left every direct test of it passing, so this
    // asserts the pipeline rejects the row rather than that the predicate
    // would have.
    const row = 'Land, track structure and other roadway $ 76,764 $ 74,093 Locomotives, '
      + 'freight cars and other equipment 15,772 15,766 Construction in progress '
      + '2,163 1,813 94,699 91,672';
    assert.equal(looksTabular(row), true);
    assert.deepEqual(sentences(row), []);
    // And it does not arrive as a claim about freight either, which is how it
    // was found: "freight cars" made a spreadsheet answer a freight question.
    const chain = intelligenceChain(`BNSF\n${row}`, { perSlot: 50 });
    assert.deepEqual(selectClaims(chain, { theme: 'freight_volumes' }), []);
  });
});

describe('narrowing the chain to a question', () => {
  const chain = intelligenceChain(FIXTURE, { perSlot: 200 });

  test('a question is a slot and a set of segments', () => {
    const hits = selectClaims(chain, {
      slot: 'expectations',
      segments: ['reinsurance', 'primary_insurance', 'geico'],
    });
    const text = hits.map((claim) => claim.source_excerpt).join(' | ');
    assert.match(text, /less reinsurance premium/);
    assert.match(text, /continued headwinds in 2026/);
    for (const claim of hits) assert.equal(claim.slot, 'expectations');
  });

  test('a claim matches if it carries any of the asked-for themes', () => {
    const hits = selectClaims(chain, { themes: ['pricing', 'competition'] });
    assert.ok(hits.length > 0);
    for (const claim of hits) {
      assert.ok(claim.themes.some((theme) => ['pricing', 'competition'].includes(theme)));
    }
  });

  test('no filter returns every claim and an unmatched filter returns none', () => {
    assert.equal(selectClaims(chain).length,
      chain.slots.reduce((total, slot) => total + slot.claims.length, 0));
    assert.deepEqual(selectClaims(chain, { segment: 'mclane', slot: 'expectations' }), []);
    assert.deepEqual(selectClaims(null), []);
  });

  test('selecting narrows and never composes', () => {
    // The filter returns the filer's sentences. Joining them into an answer is
    // the so_what step, which is still declared unreachable.
    for (const claim of selectClaims(chain)) {
      assert.ok(FIXTURE.replace(/\s+/g, ' ').includes(claim.source_excerpt));
      assert.ok(['stated', 'derived'].includes(claim.basis));
    }
  });
});

describe('what the report states as observation, not forecast', () => {
  test('aerospace recovery is what happened, not what management expects', () => {
    // Asked for expectations in aerospace, the report yields none, and that is
    // the right answer rather than a reason to loosen the cue: PCC's recovery
    // is written as a result that occurred - "reflecting the aerospace sales
    // increases" - not as a forecast. The information is in the chain, under
    // the step that describes it honestly.
    const full = intelligenceChain(readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), '..', 'tests', 'fixtures', 'publications',
        'berkshire-2025-prose.txt'), 'utf8'), { perSlot: 200 });
    const forecasts = selectClaims(full, { slot: 'expectations', theme: 'aerospace_demand' });
    assert.deepEqual(forecasts, []);
  });
});
