import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  evidenceFor, figuresAsserted, unsupportedFigures, unknownCitations,
  judgementPrompt, judge, assembleEvidence, DEPENDS_ON, FROM_ALL,
} from './judgmentTier.js';
import { QUESTIONS } from './annualReportQuestions.js';

// Berkshire's real figures, as the statements store holds them.
const EVIDENCE = evidenceFor({
  claims: [
    { slot: 'why', source_excerpt: 'McLane’s revenues declined $909 million (1.8%) in 2025 compared to 2024.' },
    { slot: 'risks', source_excerpt: 'It is reasonably possible PacifiCorp will incur material additional losses.' },
  ],
  figures: [
    { label: 'free cash flow', value: 25042, formula: 'operating_cash_flow - |capex|',
      inputs: { operating_cash_flow: 45969, capex: 20927 } },
    { label: 'net debt', value: 77204, formula: 'gross_debt - cash',
      inputs: { gross_debt: 129081, cash: 51877 } },
  ],
});

const question = QUESTIONS.find((q) => q.n === 60);

describe('what counts as a figure in an answer', () => {
  test('a quantity is checked', () => {
    assert.deepEqual(figuresAsserted('free cash flow was 25042'), [25042]);
    assert.deepEqual(figuresAsserted('margins fell 1.8%'), [1.8]);
    assert.deepEqual(figuresAsserted('net debt of $77,204'), [77204]);
    assert.deepEqual(figuresAsserted('leverage of 2.1x'), [2.1]);
    assert.deepEqual(figuresAsserted('costs of 3.9 basis points'), [3.9]);
  });

  test('a count or an ordinal is not', () => {
    // Checking these would refuse honest prose: an answer may legitimately say
    // "2 of the 3 segments" without that being a claim about a quantity.
    assert.deepEqual(figuresAsserted('2 of the 3 segments grew'), []);
    assert.deepEqual(figuresAsserted('the first of 5 reasons'), []);
  });
});

describe('a number the evidence does not contain', () => {
  test('an invented figure is caught', () => {
    // The failure this tier exists to prevent. 31,000 is plausible, adjacent
    // to the real figures, and appears nowhere in the evidence.
    assert.deepEqual(unsupportedFigures('Free cash flow of 31000 suggests underinvestment.', EVIDENCE),
      [31000]);
  });

  test('a figure taken from the evidence passes', () => {
    assert.deepEqual(unsupportedFigures('Free cash flow of 25042 against net debt of 77204.', EVIDENCE), []);
  });

  test('a figure from a formula input passes', () => {
    // 45969 and 20927 are not in the evidence text; they are the inputs that
    // produced 25042, and an answer explaining the figure needs them.
    assert.deepEqual(unsupportedFigures('Operating cash flow of 45969 less capex of 20927.', EVIDENCE), []);
  });

  test('a figure quoted from a claim passes', () => {
    assert.deepEqual(unsupportedFigures('McLane’s revenues fell $909 million, or 1.8%.', EVIDENCE), []);
  });

  test('rounding is allowed, rescaling is not', () => {
    // "25,042" written as "25,040" is the same figure rounded. Written as
    // "25.0 billion" it is a different quantity, and the tier cannot tell
    // whether the model rescaled correctly or guessed.
    assert.deepEqual(unsupportedFigures('free cash flow near 25040', EVIDENCE), []);
    assert.deepEqual(unsupportedFigures('free cash flow near 25.0 billion', EVIDENCE), [25]);
  });
});

describe('judging, with the checks in place', () => {
  const answering = (answer) => async () => answer;

  test('a supported conclusion is returned for review, never approved', () => {
    return judge({
      question,
      evidence: EVIDENCE,
      complete: answering({
        conclusion: 'Free cash flow of 25042 covers net debt of 77204 in three years; no sign of underinvestment.',
        evidence_ids: ['F1', 'F2'],
        confident: true,
      }),
    }).then((result) => {
      assert.equal(result.ok, true, result.reason);
      assert.equal(result.judgement.status, 'pending');
      assert.equal(result.judgement.reviewed_by, null);
      assert.deepEqual(result.judgement.evidence_ids, ['F1', 'F2']);
    });
  });

  test('an invented figure rejects the whole judgement', () => {
    return judge({
      question,
      evidence: EVIDENCE,
      complete: answering({
        conclusion: 'Maintenance capex is roughly 14500, well below depreciation.',
        evidence_ids: ['F1'],
      }),
    }).then((result) => {
      assert.equal(result.ok, false);
      assert.equal(result.judgement, null);
      assert.match(result.reason, /14500/);
    });
  });

  test('citing evidence that was never supplied rejects it', () => {
    return judge({
      question,
      evidence: EVIDENCE,
      complete: answering({ conclusion: 'No sign of underinvestment.', evidence_ids: ['F1', 'F9'] }),
    }).then((result) => {
      assert.equal(result.ok, false);
      assert.match(result.reason, /F9/);
    });
  });

  test('a refusal from the model is not an error', () => {
    // Rule 3 of the prompt: the evidence often will not support an answer, and
    // saying so is the useful response.
    return judge({
      question,
      evidence: EVIDENCE,
      complete: answering({ conclusion: 'The evidence does not report maintenance capex separately.', evidence_ids: [] }),
    }).then((result) => {
      assert.equal(result.ok, true, result.reason);
      assert.deepEqual(result.judgement.evidence_ids, []);
      assert.equal(result.judgement.confident, false);
    });
  });

  test('no evidence means no judgement', () => {
    return judge({ question, evidence: [], complete: answering({ conclusion: 'anything' }) })
      .then((result) => {
        assert.equal(result.ok, false);
        assert.match(result.reason, /no evidence/);
      });
  });

  test('an empty answer is refused rather than stored', () => {
    return judge({ question, evidence: EVIDENCE, complete: answering({ conclusion: '   ' }) })
      .then((result) => {
        assert.equal(result.ok, false);
        assert.match(result.reason, /no conclusion/);
      });
  });
});

describe('what the model is shown', () => {
  test('it sees numbered evidence and the question, and nothing else', () => {
    const { system, user } = judgementPrompt(question, EVIDENCE);
    assert.match(user, /^Question 60: /);
    for (const entry of EVIDENCE) assert.ok(user.includes(`[${entry.id}] `), entry.id);
    // Not the document. The tier reasons over what was extracted and verified,
    // never over raw text it could quote something new from.
    assert.equal(user.includes('Annual Report'), false);
    assert.match(system, /Every number in your answer must appear in the evidence/);
  });

  test('every judgment question in the register can be asked', () => {
    for (const q of QUESTIONS.filter((entry) => entry.kind === 'judgment')) {
      const { user } = judgementPrompt(q, EVIDENCE);
      assert.ok(user.startsWith(`Question ${q.n}: `), `${q.n}`);
    }
  });
});

describe('what each judgement may reason from', () => {
  const STATED = [
    { n: 35, status: 'answered', matches: [{ text: 'Restructuring charges of $120 million were recorded.' }] },
    { n: 37, status: 'answered', matches: [{ text: 'We recorded an impairment of $5.0 billion on Kraft Heinz.' }] },
    { n: 89, status: 'answered', matches: [{ text: 'Our decentralized approach is a competitive advantage.' }] },
    { n: 96, status: 'silent', matches: [] },
  ];
  const COMPUTED = new Map([
    [42, { value: 25042, formula: 'operating_cash_flow - |capex|', inputs: { capex: 20927 }, reason: null }],
    [53, { value: 0.0563, formula: 'capex / revenue', inputs: { capex: 20927 }, reason: null }],
    [64, { value: null, formula: null, inputs: null, reason: 'ebitda not reported' }],
  ]);

  test('a judgement sees only the questions it declares', () => {
    // Question 33 asks which exceptional costs recur, and is given the
    // charges management called exceptional - not the whole document.
    const evidence = assembleEvidence(33, { stated: STATED, computed: COMPUTED });
    const texts = evidence.map((entry) => entry.text).join(' ');
    assert.match(texts, /Restructuring charges/);
    assert.match(texts, /impairment of \$5\.0 billion/);
    assert.equal(/competitive advantage/.test(texts), false, 'unrelated evidence leaked in');
  });

  test('a question that was not answered contributes nothing', () => {
    // Silence is not evidence. A refused computation is not evidence either -
    // "ebitda not reported" says nothing about the business.
    const evidence = assembleEvidence(60, { stated: STATED, computed: COMPUTED });
    assert.equal(evidence.some((entry) => /ebitda not reported/.test(entry.text)), false);
    assert.ok(evidence.some((entry) => /25042/.test(entry.text)), 'free cash flow was not supplied');
  });

  test('question 100 reasons over everything answered, and nothing else', () => {
    const evidence = assembleEvidence(100, { stated: STATED, computed: COMPUTED });
    const texts = evidence.map((entry) => entry.text).join(' ');
    assert.match(texts, /competitive advantage/);
    assert.match(texts, /Restructuring charges/);
    assert.match(texts, /25042/);
    // Still not the refusals, and still not the silences.
    assert.equal(/ebitda not reported/.test(texts), false);
  });

  test('every judgement question has a declared source', () => {
    // A judgement with no rule would silently receive no evidence and refuse
    // forever, which reads as the model being unable rather than us.
    for (const q of QUESTIONS.filter((entry) => entry.kind === 'judgment')) {
      assert.ok(DEPENDS_ON.has(q.n) || q.n === FROM_ALL, `question ${q.n} has no evidence rule`);
    }
  });

  test('a judgement never depends on itself or on another judgement', () => {
    // The tier reasons over answers this pipeline produced and verified. One
    // conclusion feeding another compounds an unreviewed inference.
    const judgments = new Set(QUESTIONS.filter((q) => q.kind === 'judgment').map((q) => q.n));
    for (const [n, sources] of DEPENDS_ON) {
      for (const source of sources) {
        assert.equal(judgments.has(source), false,
          `question ${n} depends on judgement ${source}, whose answer assembleEvidence `
          + 'cannot supply - the declaration would read as evidence that is never given');
      }
    }
  });
});
