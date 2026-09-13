import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { answersFor, coverage, answerable, coverageSummary, FINDS } from './annualReportAnswers.js';
import { QUESTIONS } from './annualReportQuestions.js';

// Verbatim from Berkshire's 2025 annual report.
const REPORT = [
  'McLane’s major customers during 2025 included Walmart (approximately 17.2% of revenues); '
    + '7-Eleven (approximately 13.3% of revenues); and Yum! Brands.',
  'Seasonal variations in GEICO’s insurance business are not significant.',
  'Our decentralized approach is a competitive advantage, attracting managers who thrive on '
    + 'autonomy and deliver on accountability.',
  'GEICO’s broad rate increases in recent years have restored margins but come at the cost of lower retention.',
  // The only two sentences in the report that mention either subject: a 10-K
  // incorporates both by reference to the proxy statement.
  'Executive Compensation Item 12.',
  'Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters Item 13.',
].join('\n\n');

describe('finding the sentence that answers a question', () => {
  test('a named customer and its share of revenue is found', () => {
    const answers = answersFor(REPORT);
    for (const n of [81, 82]) {
      const [first] = answers.get(n);
      assert.ok(first, `question ${n} found nothing`);
      assert.match(first.text, /Walmart \(approximately 17\.2% of revenues\)/);
    }
  });

  test('a subject the document settles in one sentence is found', () => {
    assert.match(answersFor(REPORT).get(20)[0].text, /Seasonal variations in GEICO/);
    assert.match(answersFor(REPORT).get(89)[0].text, /decentralized approach is a competitive advantage/);
    assert.match(answersFor(REPORT).get(85)[0].text, /lower retention/);
  });

  test('a cross-reference index is not an answer', () => {
    // "Executive Compensation Item 12." is the only sentence in the whole
    // report that mentions executive pay, because a 10-K incorporates it by
    // reference. Returning it would turn "this document does not say" into
    // "here is what it says", which is the substitution this system exists to
    // refuse.
    assert.equal(answerable('Executive Compensation Item 12.'), false);
    assert.equal(answerable('Security Ownership of Certain Beneficial Owners and Management '
      + 'and Related Stockholder Matters Item 13.'), false);
    const answers = answersFor(REPORT);
    assert.deepEqual(answers.get(97), []);
    assert.deepEqual(answers.get(98), []);
  });

  test('a fragment too short to state anything is not an answer', () => {
    assert.equal(answerable('Impairment.'), false);
    assert.equal(answerable(''), false);
    assert.equal(answerable(null), false);
  });
});

describe('what a document answers and what it is silent on', () => {
  const rows = () => coverage(REPORT, { questions: QUESTIONS });

  test('silence is reported, not dropped', () => {
    // "Berkshire's annual report says nothing about related-party
    // transactions" is a finding. A blank row is not.
    const related = rows().find((row) => row.n === 96);
    assert.equal(related.status, 'silent');
    assert.deepEqual(related.matches, []);
  });

  test('a question with no retrieval rule says so, rather than saying silent', () => {
    // The two are different: one means the document does not discuss it, the
    // other means we have not written a way to look. Reporting the second as
    // the first is a claim about the document that nobody checked.
    const noRule = rows().find((row) => row.n === 1);
    assert.equal(noRule.status, 'no_rule');
    assert.equal(FINDS.has(1), false);
  });

  test('a computed or judgment question is never answered from prose', () => {
    for (const row of rows()) {
      if (row.kind === 'computed') assert.equal(row.status, 'computed', `${row.n}`);
      if (row.kind === 'judgment') assert.equal(row.status, 'judgment', `${row.n}`);
      if (row.kind !== 'stated') assert.deepEqual(row.matches, [], `${row.n}`);
    }
  });

  test('every question is accounted for exactly once', () => {
    const all = rows();
    assert.equal(all.length, 100);
    assert.deepEqual(all.map((row) => row.n), QUESTIONS.map((q) => q.n));
    for (const row of all) {
      assert.ok(['answered', 'silent', 'no_rule', 'computed', 'judgment'].includes(row.status));
    }
  });

  test('every retrieval rule belongs to a question that is stated', () => {
    // A rule on a computed question would never run, and a rule on a number
    // that is not a question at all is a typo nobody would see.
    const stated = new Set(QUESTIONS.filter((q) => q.kind === 'stated').map((q) => q.n));
    for (const n of FINDS.keys()) assert.ok(stated.has(n), `question ${n} is not stated`);
  });

  test('perQuestion bounds what is returned, not what is searched', () => {
    const many = [...Array(12)].map((_, at) =>
      `The group recorded an impairment of $${at + 1} million during the year under review.`).join('\n\n');
    assert.equal(answersFor(many, { perQuestion: 3 }).get(37).length, 3);
    assert.equal(answersFor(many, { perQuestion: 20 }).get(37).length, 12);
  });
});

describe('the shape a preview reads', () => {
  const REPORT_TEXT = 'Lubrizol operates two business segments: Lubrizol Additives, which '
    + 'produces engine lubricant additives, and Lubrizol Advanced Materials.\n\n'
    + 'Seasonal variations in GEICO’s insurance business are not significant.\n\n'
    + 'Executive Compensation Item 12.';
  const summary = () => coverageSummary(REPORT_TEXT, { questions: QUESTIONS });

  test('all hundred are returned, answered or not', () => {
    // A reader deciding whether to store a document needs to see what it does
    // not cover. Returning only the answers would show a short, flattering
    // list and hide the shape of the thing.
    const { questions } = summary();
    assert.equal(questions.length, 100);
    assert.deepEqual(questions.map((q) => q.n), QUESTIONS.map((q) => q.n));
  });

  test('the counts add up to a hundred', () => {
    const { counts } = summary();
    assert.equal(Object.values(counts).reduce((a, b) => a + b, 0), 100);
  });

  test('a computed question carries the line items it needs, not a blank', () => {
    // The list is the specification for loading them.
    const leverage = summary().questions.find((q) => q.n === 64);
    assert.equal(leverage.status, 'computed');
    assert.equal(leverage.answer, null);
    assert.deepEqual(leverage.needs, ['gross_debt', 'cash', 'ebitda']);
  });

  test('a judgment question carries its reason', () => {
    const worth = summary().questions.find((q) => q.n === 100);
    assert.equal(worth.status, 'judgment');
    assert.match(worth.note, /ninety-nine/);
  });

  test('a defining sentence is the answer, not a passing mention', () => {
    // "pricing in most commercial insurance segments was firm" matched the
    // bare form and was the first thing a reader saw under this question.
    const segments = summary().questions.find((q) => q.n === 3);
    assert.equal(segments.status, 'answered');
    assert.match(segments.answer, /Lubrizol operates two business segments/);
  });

  test('an answer is trimmed for a preview but not truncated mid-count', () => {
    for (const question of summary().questions) {
      if (question.answer) assert.ok(question.answer.length <= 400, `${question.n}`);
      assert.ok(Number.isInteger(question.more) && question.more >= 0, `${question.n}`);
    }
  });
});

describe('a filing that is not a 10-K', () => {
  // Verbatim from Reliance Industries' Integrated Annual Report 2025-26. The
  // patterns were cut against Berkshire, and an Indian filing uses different
  // words for the same disclosures - and the same words for different ones.
  const RIL = {
    remuneration: 'Board Compensation The Company’s Remuneration Policy for Directors, Key Managerial '
      + 'Personnel and other employees is available on the website.',
    rates: 'Interest rates on unsecured term loans are in range of 1.02% to 6.99% per annum.',
    talent: 'Talent Attraction and Retention Reliance’s talent strategy continues to evolve in line '
      + 'with its expanding portfolio of businesses.',
    creditRisk: 'Credit risk is actively managed through Letters of Credit, Bank Guarantees, Parent '
      + 'Company Guarantees, advance payments and factoring without recourse to the company to avoid '
      + 'concentration of risk.',
    industry: 'FY 2025-26 also saw refinery capacity rationalisation of around 1.2 mb/d, majorly in '
      + 'Europe and North America, as older and less competitive sites closed.',
    compute: 'By combining domestic compute capacity with localised, multilingual, voice-first '
      + 'platforms, Reliance will empower millions of users across India.',
  };
  const answers = (text) => answersFor(text);

  test('remuneration is what a filing outside the US calls executive pay', () => {
    // "Remuneration Committee" appears nine times in that report and
    // "compensation committee" never.
    assert.match(answers(RIL.remuneration).get(97)[0].text, /Remuneration Policy for Directors/);
  });

  test('a stated range of interest rates answers the rate question', () => {
    assert.match(answers(RIL.rates).get(66)[0].text, /1\.02% to 6\.99% per annum/);
  });

  test('talent retention is not customer retention', () => {
    assert.deepEqual(answers(RIL.talent).get(85), []);
  });

  test('concentration of credit risk is not revenue concentration', () => {
    // Answered "how concentrated is the revenue base?" with a sentence about
    // letters of credit, because the word appears in both.
    assert.deepEqual(answers(RIL.creditRisk).get(10), []);
  });

  test('an industry’s capacity is not this company’s utilisation', () => {
    assert.deepEqual(answers(RIL.industry).get(57), []);
  });

  test('a bare mention of capacity is not capacity being added', () => {
    assert.deepEqual(answers(RIL.compute).get(55), []);
  });

  test('the Berkshire answers these rules were cut from still hold', () => {
    // The rules were tightened against a second filing, and the first must not
    // regress: 22 answered before and after.
    const brk = 'Some of Lubrizol’s largest customers also may be suppliers, although no single '
      + 'customer represented more than 10% of Lubrizol’s consolidated revenues.\n\n'
      + 'GEICO’s broad rate increases in recent years have restored margins but come at the cost '
      + 'of lower retention.\n\n'
      + 'In 2025, BNSF issued $1.85 billion of debentures due in 2056 with a weighted average '
      + 'interest rate of 5.6%.';
    const found = answers(brk);
    assert.match(found.get(10)[0].text, /no single customer represented more than 10%/);
    assert.match(found.get(85)[0].text, /cost of lower retention/);
    assert.match(found.get(66)[0].text, /weighted average interest rate/);
  });
});

describe('an abbreviation is not the end of a sentence', () => {
  test('the segments named after "viz." survive', () => {
    // Reliance's report answers question 3 in full and the splitter threw the
    // answer away: "four principal operating and reporting segments; viz." was
    // all that reached the page.
    const text = 'Segment Information The Group has four principal operating and reporting '
      + 'segments; viz. Oil To Chemicals (O2C), Oil and Gas, Retail and Digital Services. '
      + 'The accounting policies adopted for segment reporting are in line with the policy of the Company.';
    assert.match(answersFor(text).get(3)[0].text, /Oil To Chemicals \(O2C\), Oil and Gas, Retail and Digital Services/);
  });

  test('a company suffix still ends one', () => {
    // The list is short on purpose. Refusing to split after "Inc." welds two
    // sentences together, which is the same defect facing the other way.
    const text = 'We acquired Pilot Travel Centers LLC and Alleghany Inc. The transaction '
      + 'closed in January and added materially to the insurance segment.';
    const claims = answersFor(text);
    assert.equal([...claims.values()].flat().some((m) => /Inc\. The transaction/.test(m.text)), false);
  });
});

describe('a policy that mentions a thing is not the thing', () => {
  test('an accounting policy is not an impairment', () => {
    // Every filing describes this policy, so the bare word answered question
    // 37 for every company that has ever published a balance sheet.
    const policy = 'Property, Plant and Equipment are stated at cost, net of recoverable taxes, '
      + 'trade discount and rebates less accumulated depreciation and impairment losses, if any.';
    assert.deepEqual(answersFor(policy).get(37), []);
  });

  test('an impairment that was recorded is', () => {
    const real = 'We recorded other-than-temporary impairment losses in 2025 on our investments '
      + 'in The Kraft Heinz Company.';
    assert.match(answersFor(real).get(37)[0].text, /recorded other-than-temporary impairment/);
  });

  test('another company’s capacity is not this company’s', () => {
    const china = 'PTA-PX delta decreased by 9.8% due to significant capacity expansion of PTA in China.';
    assert.deepEqual(answersFor(china).get(55), []);
  });
});
