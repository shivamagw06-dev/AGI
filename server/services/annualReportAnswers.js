/**
 * Finding the sentences that answer a question, as opposed to the sentences
 * that state a kind of thing.
 *
 * The chain files a sentence by what it is - a cause, a change, an amount.
 * These questions ask what a sentence is about. Two indexes over the same
 * text, and the second cannot be built on the first: related-party
 * transactions, executive pay, insider ownership and debt covenants are all
 * discussed in Berkshire's report and produce no chain claim at all, because
 * no step's cues reach them.
 *
 * Only the questions a document can state are here. A computed question has no
 * sentence to find, and a judgment question has no pattern that could find it.
 *
 * A question with no pattern is absent rather than guessed at. "What does the
 * company actually sell" is answered by a paragraph a reader recognises and no
 * regular expression does, and a rule loose enough to catch it catches most of
 * a shareholder letter.
 */
import { sentences } from './publicationIntelligence.js';

/**
 * The subject each answerable question is about.
 *
 * Every pattern was run against a real 557,000-character annual report and
 * cut down by reading what it caught, the same way the chain's cues were.
 */
export const FINDS = new Map([
  // A sentence that defines the segments, not one that mentions the word.
  // "pricing in most commercial insurance segments was firm" matched the bare
  // form and was the first thing a reader would have seen under "what are the
  // major business segments".
  [3, /\b(?:operates?|reports?|manages?|comprises?)[^.]{0,45}\bsegments?\b|\b(?:business|reportable|operating) segments?\b[^.]{0,25}(?:are|include|consist|comprise)/i],
  // Revenue concentration, not concentration of credit risk. The loose form
  // returned "accounted for approximately 80% of greenhouse gas emissions".
  [10, /\bno single (?:customer|client)\b|\b(?:revenue|sales|customer)\s+concentration\b|\bconcentration of (?:revenue|sales|customers)\b/i],
  [20, /\bseasonal/i],
  [35, /\brestructuring\b/i],
  // An impairment that happened, not an accounting policy that mentions the
  // word. The bare form answered with "Property, Plant and Equipment are
  // stated at cost ... less accumulated depreciation and impairment losses,
  // if any", which is how every filing describes the policy.
  [37, /\b(?:recognised|recognized|recorded|booked)\b[^.]{0,40}\bimpairment\b|\bimpairment (?:loss(?:es)?|charge(?:s)?)\b[^.]{0,25}\b(?:of|totall?ing)\s*[\u20b9$H]?\s?[\d,]/i],
  [54, /\bcapital expenditures?\b/i],
  // Capacity being added, never a bare mention: "combining domestic compute
  // capacity with localised, multilingual, voice-first platforms" is prose.
  [55, /\b(?:we|our|its|the Company|the Group)\b[^.]{0,70}\b(?:capacity (?:expansion|addition|augmentation)|expand(?:ed|ing)? (?:its |our )?capacity|new capacity|additional capacity|capacity (?:of|to) \d)/i],
  // This company's utilisation. A bare mention returned an industry figure:
  // "refinery capacity rationalisation of around 1.2 mb/d, majorly in Europe".
  [57, /\b(?:our|its|the (?:company|plant|refinery|group)['’]?s?)\s+[^.]{0,30}utili[sz]ation\b|\butili[sz]ation (?:rate|level|was|of \d)/i],
  // A stated rate, or a stated range of them - which is how an Indian filing
  // puts it: "Interest rates on unsecured term loans are in range of 1.02% to
  // 6.99% per annum".
  [66, /\bweighted[- ]average interest rate\b|\baverage (?:cost|rate) of (?:borrowing|debt)\b|\binterest rates?\b[^.]{0,60}\b(?:per annum|in (?:the )?range)\b/i],
  [67, /\bfloating[- ]rate\b|\bvariable[- ]rate\b/i],
  [68, /\bmaturit(?:y|ies)\b|\bmature in\b|\bdue in \d{4}\b/i],
  [70, /\bcovenants?\b/i],
  // The company's own customers, named as such. A bare "customers" is most of
  // an operating report.
  [81, /\b(?:major|principal|largest|significant) customers?\b|\bno single customer\b/i],
  [82, /\bcustomers?\b[^.]{0,90}\b\d{1,2}(?:\.\d)?% of (?:revenues|sales|total)/i],
  [83, /\b(?:five|ten|5|10) largest customers\b|\btop (?:five|ten|5|10) customers\b/i],
  [84, /\bcontracts?\b[^.]{0,60}\b(?:expire|renew|renewal|terminate)\b/i],
  // Customer retention. A bare match returned "Talent Attraction and
  // Retention" and an audit-trail retention period, so the wrong subject
  // anywhere in the sentence disqualifies it.
  [85, /^(?![^]*\b(?:talent|employee|staff|workforce|audit|data)\b)[^]*\b(?:retention|renewal rate|churn|policies-in-force)\b/i],
  // The company's own suppliers. A bare "suppliers" caught sentences about
  // customers choosing between energy suppliers, and about an aerospace
  // manufacturer's customers who also happen to be its suppliers.
  [86, /\b(?:our|its|principal|key|major|significant) suppliers?\b|\bsuppliers? (?:to|of) (?:the )?(?:company|us)\b/i],
  [87, /\b(?:single|sole)[- ]sourced?\b|\bsole supplier\b|\bone supplier\b/i],
  [88, /\bpricing power\b|\bprice increases\b|\brate increases\b/i],
  [89, /\bcompetitive (?:advantage|position|strength)\b|\bmoat\b/i],
  [91, /\bstrategic priorit|\bour strategy\b|\blong-term (?:goal|objective)/i],
  [95, /\blitigation\b|\blegal proceedings\b|\bcontingenc/i],
  [96, /\brelated part(?:y|ies)\b/i],
  // An Indian filing says remuneration where a 10-K says compensation, and
  // the word appears nine times in Reliance's report while the US form
  // appears never.
  [97, /\bexecutive compensation\b|\bcompensation committee\b|\bincentive compensation\b|\bmanagerial remuneration\b|\bremuneration (?:paid|payable|policy)\b|\bremuneration (?:to|of) (?:the )?(?:directors|managing|key managerial|whole-time)\b/i],
  [98, /\bbeneficial(?:ly)? own|\bshares owned by\b/i],
  [99, /\bcritical accounting\b|\bsignificant (?:accounting )?estimates\b|\buse of estimates\b/i],
]);

/**
 * A 10-K's cross-reference index, which names every subject and answers none.
 *
 * "Executive Compensation Item 12." and "Security Ownership of Certain
 * Beneficial Owners and Management and Related Stockholder Matters Item 13."
 * are the only sentences in Berkshire's report that mention executive pay or
 * insider ownership - because a 10-K incorporates both by reference to the
 * proxy. Returning those lines as the answer would turn "this document does
 * not say" into "here is what it says", which is the one substitution this
 * system exists to refuse.
 */
const CROSS_REFERENCE = /\bitem\s+\d+[a-z]?\.?\s*$/i;

/** Whether a sentence is capable of answering anything. */
export function answerable(text) {
  const sentence = String(text || '').trim();
  if (sentence.length < 40) return false;
  if (CROSS_REFERENCE.test(sentence)) return false;
  return true;
}

/**
 * The sentences in a document that answer each question it can answer.
 *
 * `perQuestion` bounds what is returned for reading, never what is searched.
 */
export function answersFor(text, { perQuestion = 6 } = {}) {
  const found = sentences(text).filter((entry) => answerable(entry.text));
  const answers = new Map();
  for (const [n, pattern] of FINDS) {
    const matches = [];
    for (const entry of found) {
      if (!pattern.test(entry.text)) continue;
      matches.push({ text: entry.text, paragraph: entry.paragraph, heading: entry.heading });
      if (matches.length >= perQuestion) break;
    }
    answers.set(n, matches);
  }
  return answers;
}

/**
 * Which questions this document answers, and which it is silent on.
 *
 * A question the document does not discuss is reported as silent rather than
 * dropped: "Berkshire's annual report says nothing about related-party
 * transactions" is a finding, and a blank row is not.
 */
export function coverage(text, { questions, perQuestion = 6 } = {}) {
  const answers = answersFor(text, { perQuestion });
  return (questions || []).map((question) => {
    if (question.kind !== 'stated') {
      return { ...question, status: question.kind, matches: [] };
    }
    if (!FINDS.has(question.n)) {
      return { ...question, status: 'no_rule', matches: [] };
    }
    const matches = answers.get(question.n) || [];
    return { ...question, status: matches.length ? 'answered' : 'silent', matches };
  });
}

/**
 * The hundred questions, shaped for a preview.
 *
 * One row per question carrying its status and, where the document answers it,
 * the first sentence and how many more there are. The whole set is returned
 * rather than only the answers: a reader deciding whether to store a document
 * needs to see what it does not cover, and ninety-three rows of "not from
 * this" is the honest shape of an annual report read this way.
 */
export function coverageSummary(text, { questions, perQuestion = 6 } = {}) {
  const rows = coverage(text, { questions, perQuestion });
  const counts = { answered: 0, silent: 0, no_rule: 0, computed: 0, judgment: 0 };
  const summary = rows.map((row) => {
    counts[row.status] += 1;
    const [first] = row.matches;
    return {
      n: row.n,
      ask: row.ask,
      kind: row.kind,
      status: row.status,
      // Trimmed for a preview. The claim rows keep the sentence in full.
      answer: first ? first.text.slice(0, 400) : null,
      more: Math.max(row.matches.length - 1, 0),
      // Why a question cannot be answered, where there is a reason worth
      // reading: the line items a computation needs, or the note on a
      // judgement. A blank with no reason is the thing this avoids.
      needs: row.needs || null,
      note: row.note || null,
    };
  });
  return { counts, questions: summary };
}
