import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { queryOf, candidatesFor, evidenceSentencesFor, SUBJECT_TERMS } from './questionRetrieval.js';
import { QUESTIONS } from './annualReportQuestions.js';
import { FINDS } from './annualReportAnswers.js';

const ask = (n) => QUESTIONS.find((q) => q.n === n);

describe('a question cannot retrieve with its own words', () => {
  test('the query drops words every sentence contains', () => {
    // "What is the company's EBITDA margin" must not rank on "is" and "the".
    const query = queryOf({ ask: 'What is the company’s EBITDA margin?' });
    assert.equal(query.includes('the'), false);
    assert.equal(query.includes('company'), false);
    assert.ok(query.includes('ebitda'), query.join(','));
  });

  test('an analyst’s words do not appear in a filing', () => {
    // This is why SUBJECT_TERMS exists. "What does the company actually sell?"
    // shares no content word with the sentence that answers it.
    const answer = [{ text: 'The Company is engaged in activities spanning across hydrocarbon '
      + 'exploration and production, Oil to Chemicals, Retail and Digital Services.' }];
    assert.deepEqual(candidatesFor(ask(1), answer), []);
  });
});

describe('subject terms are the filing’s words', () => {
  const doc = [
    { text: 'The Company is engaged in activities spanning across hydrocarbon exploration and '
      + 'production, Oil to Chemicals, Retail and Digital Services.' },
    { text: 'PVC demand declined by 6.4% mainly in pipe sector on account of extended monsoon season.' },
    { text: 'Capex was principally directed towards growth projects in the O2C and New Energy business.' },
    { text: 'The Board met four times during the year under review.' },
  ];

  test('a question with no pattern still finds its sentence', () => {
    assert.match(evidenceSentencesFor(ask(1), doc, { finds: FINDS })[0].text, /engaged in activities spanning/);
    assert.match(evidenceSentencesFor(ask(52), doc, { finds: FINDS })[0].text, /growth projects/);
  });

  test('a question with a pattern uses the pattern first', () => {
    // The rules were cut against real documents and are stricter, so they win
    // where they match.
    const found = evidenceSentencesFor(ask(96), [{ text: 'There were no materially significant '
      + 'related party transactions during the year.' }], { finds: FINDS });
    assert.match(found[0].text, /related party transactions/);
  });

  test('the terms get a turn when the pattern finds nothing', () => {
    // Question 20 looks for "seasonal". Reliance writes "monsoon season", and
    // a pattern tuned on one filing should not stop a looser query on another
    // when the tier can refuse what it retrieves.
    assert.match(evidenceSentencesFor(ask(20), doc, { finds: FINDS })[0].text, /monsoon season/);
  });

  test('a question with neither gets nothing, rather than whatever is nearby', () => {
    // Reasoning from unrelated sentences is how a confident wrong answer is
    // produced. Nothing is the honest input.
    const orphan = { n: 999, ask: 'Some question nobody wrote anything for' };
    assert.deepEqual(evidenceSentencesFor(orphan, doc, { finds: FINDS }), []);
  });

  test('every subject term belongs to a real question', () => {
    const numbers = new Set(QUESTIONS.map((q) => q.n));
    for (const n of SUBJECT_TERMS.keys()) assert.ok(numbers.has(n), `question ${n} does not exist`);
  });

  test('a sentence matching more of the subject ranks first', () => {
    const mixed = [
      { text: 'Growth was strong across the portfolio of businesses during the year under review.' },
      { text: 'The Company is engaged in activities spanning refining, retailing and digital services.' },
    ];
    assert.match(evidenceSentencesFor(ask(1), mixed, { finds: FINDS })[0].text, /engaged in activities/);
  });
});
