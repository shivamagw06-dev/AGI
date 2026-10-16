/**
 * The nine questions no sentence states and no formula yields.
 *
 * Everything else in this pipeline either finds a sentence or refuses. This is
 * the one layer that concludes, and it is built so that concluding cannot
 * become inventing:
 *
 *   - The model sees only evidence this codebase assembled: approved claims,
 *     each carrying the sentence it came from, and figures computed from
 *     imported statements, each carrying its formula and inputs. It is never
 *     shown the document and never asked to recall anything.
 *   - Every figure in its answer is checked against that evidence. A number
 *     that appears in the conclusion and nowhere in the evidence rejects the
 *     whole judgement. This is the difference between trusting a model and
 *     checking one, and it is machine-checkable rather than a hope.
 *   - Every judgement cites the evidence it used, by id, and an id that was
 *     not supplied rejects it too.
 *   - Nothing is auto-approved. A judgement reaches a reviewer with its
 *     evidence beside it, which is the only form in which a conclusion about
 *     a company is publishable.
 *
 * Question 100 depends on the other ninety-nine and is therefore answered
 * last, from their answers, rather than from the document.
 */

/** One piece of evidence, numbered so a judgement can cite it. */
function item(id, kind, text, source) {
  return { id, kind, text, source: source || null };
}

/**
 * The evidence a question is allowed to reason from.
 *
 * Assembled here rather than by the model, because what counts as relevant is
 * a decision this codebase should own and be able to show a reviewer.
 */
export function evidenceFor({ claims = [], figures = [] } = {}) {
  const evidence = [];
  claims.forEach((claim, at) => {
    if (!claim?.source_excerpt) return;
    evidence.push(item(`C${at + 1}`, 'claim', claim.source_excerpt,
      { slot: claim.slot || null, metric: claim.metric || null }));
  });
  figures.forEach((figure, at) => {
    if (!figure || figure.value === null || figure.value === undefined) return;
    evidence.push(item(`F${at + 1}`, 'figure',
      `${figure.label}: ${figure.value}`,
      { formula: figure.formula || null, inputs: figure.inputs || null }));
  });
  return evidence;
}

const NUMBER = /-?\d[\d,]*(?:\.\d+)?/g;
const UNIT_AFTER = /^\s*(?:%|percent|percentage points?|basis points?|bps|x\b|times\b|trillion|billion|million|thousand|crore|lakh)/i;

/**
 * The figures a piece of text asserts.
 *
 * A bare small integer is a count or an ordinal - "two of the three segments",
 * "1 of 5" - and checking those against the evidence would refuse honest
 * prose. A number carrying a unit, a decimal, a thousands separator, or a
 * magnitude of a hundred or more is being asserted as a quantity, and that is
 * what has to be supported.
 */
export function figuresAsserted(text) {
  const body = String(text || '');
  const found = [];
  for (const match of body.matchAll(NUMBER)) {
    const raw = match[0];
    const after = body.slice(match.index + raw.length);
    const before = body.slice(Math.max(0, match.index - 1), match.index);
    const value = Number(raw.replace(/,/g, ''));
    if (!Number.isFinite(value)) continue;
    const quantified = UNIT_AFTER.test(after) || /[$₹€£]/.test(before)
      || raw.includes('.') || raw.includes(',') || Math.abs(value) >= 100;
    if (quantified) found.push(value);
  }
  return found;
}

/** Whether a value appears in the evidence, allowing for rounding in prose. */
function supported(value, evidenceNumbers) {
  return evidenceNumbers.some((known) => {
    if (known === value) return true;
    // "0.6843" reported as "0.68", "77204" as "77.2 billion" is not allowed -
    // only a rounding of the same magnitude is.
    const scale = Math.max(Math.abs(known), Math.abs(value));
    return scale > 0 && Math.abs(known - value) <= scale * 0.005;
  });
}

/**
 * Figures the answer asserts that the evidence does not contain.
 *
 * The whole point of the tier. A conclusion drawn from evidence is a
 * judgement; a conclusion carrying a number nobody supplied is a fabrication,
 * and the two are indistinguishable to a reader.
 */
export function unsupportedFigures(answer, evidence) {
  const known = [];
  for (const entry of evidence || []) {
    known.push(...figuresAsserted(entry.text));
    for (const value of Object.values(entry.source?.inputs || {})) {
      const asNumber = Number(value);
      if (Number.isFinite(asNumber)) known.push(asNumber);
    }
  }
  return figuresAsserted(answer).filter((value) => !supported(value, known));
}

/** Evidence ids a judgement cites that were never supplied. */
export function unknownCitations(cited, evidence) {
  const ids = new Set((evidence || []).map((entry) => entry.id));
  return [...new Set(cited || [])].filter((id) => !ids.has(id));
}

export const SYSTEM = [
  'You are helping an investment analyst answer one question about one company.',
  '',
  'You are given numbered evidence: sentences the company published, and figures',
  'computed from its filed financial statements. That evidence is all you know.',
  '',
  'Rules, which are checked automatically after you answer:',
  '1. Every number in your answer must appear in the evidence. Do not calculate',
  '   new figures, do not recall figures from memory, and do not estimate.',
  '2. Cite the evidence ids you used.',
  '3. If the evidence does not support an answer, say so in `conclusion` and',
  '   return an empty `evidence_ids`. A refusal is a useful answer here.',
  '4. Write for a reader who will check you against the evidence.',
  '',
  'Reply as JSON: {"conclusion": string, "evidence_ids": string[], "confident": boolean}',
].join('\n');

export function judgementPrompt(question, evidence) {
  const lines = (evidence || []).map((entry) => `[${entry.id}] ${entry.text}`);
  return {
    system: SYSTEM,
    user: [`Question ${question.n}: ${question.ask}`, '', 'Evidence:', ...lines].join('\n'),
  };
}

/**
 * One judgement, verified.
 *
 * `complete` is injected so the checking can be tested without a provider, and
 * so a caller decides which model answers.
 */
export async function judge({ question, evidence, complete }) {
  if (!question || !complete) throw new Error('a question and a completion function are required');
  if (!evidence?.length) {
    return { ok: false, reason: 'no evidence was assembled for this question', judgement: null };
  }
  const answer = await complete(judgementPrompt(question, evidence));
  const conclusion = String(answer?.conclusion || '').trim();
  if (!conclusion) return { ok: false, reason: 'the model returned no conclusion', judgement: null };

  const invented = unsupportedFigures(conclusion, evidence);
  if (invented.length) {
    return {
      ok: false,
      reason: `the answer asserts ${invented.join(', ')}, which the evidence does not contain`,
      judgement: null,
    };
  }
  const unknown = unknownCitations(answer?.evidence_ids, evidence);
  if (unknown.length) {
    return { ok: false, reason: `cites evidence that was not supplied: ${unknown.join(', ')}`, judgement: null };
  }

  return {
    ok: true,
    reason: null,
    judgement: {
      question: question.n,
      ask: question.ask,
      conclusion,
      evidence_ids: [...new Set(answer.evidence_ids || [])],
      confident: answer?.confident === true,
      // Never approved by a rule. A conclusion about a company is publishable
      // only in the form a person has read.
      status: 'pending',
      reviewed_by: null,
    },
  };
}

/**
 * What each judgement is allowed to reason from, by question number.
 *
 * Declared rather than inferred, because "what counts as relevant" is the
 * decision that decides whether a conclusion is grounded, and it should be
 * readable and arguable rather than buried in a prompt.
 *
 * Each entry lists the questions whose answers become the evidence. A
 * judgement therefore reasons over answers this pipeline produced and
 * verified - sentences with their source, figures with their formula - and
 * never over the document.
 *
 * Question 100 depends on every question that was answered. That is the whole
 * ordering: it is a function of the other ninety-nine, so it is asked last and
 * from their answers. Asking it first is guessing in a confident voice.
 */
export const DEPENDS_ON = new Map([
  // Normalising earnings needs the charges management called exceptional.
  // Question 33 asks which of them recur and is the same reasoning, so 32
  // reads the same charges rather than 33's answer: a judgement built on a
  // judgement compounds an inference nobody has reviewed yet.
  [32, [31, 35, 36, 37, 38, 39]],
  [33, [35, 36, 37, 38]],
  // Whether adjusted figures flatter: the gap, and what was excluded.
  [40, [31, 34, 39]],
  // Underinvestment: what is spent, against what wears out, against the cash
  // it appears to release.
  [60, [42, 51, 52, 53, 54, 59, 72]],
  // What acquisitions cost, and what the segments did afterwards.
  [78, [13, 36, 73]],
  // A claimed advantage weighed against the numbers elsewhere.
  [90, [85, 88, 89, 23, 24, 25]],
  // Both need last year's document, and say so when it is absent.
  [92, [91]],
  [93, [91, 11, 23, 42]],
]);

/** The question whose evidence is everything else that was answered. */
export const FROM_ALL = 100;

/**
 * The evidence for one judgement, drawn from answers already produced.
 *
 * `stated` are coverage rows carrying their matched sentences; `computed` is a
 * Map of question number to a figure with its formula. Neither is the
 * document.
 */
export function assembleEvidence(n, { stated = [], computed = new Map() } = {}) {
  const wanted = n === FROM_ALL
    ? [...new Set([...stated.map((row) => row.n), ...computed.keys()])]
    : (DEPENDS_ON.get(n) || []);
  const from = new Set(wanted);
  const claims = [];
  const figures = [];
  for (const row of stated) {
    if (!from.has(row.n) || row.status !== 'answered') continue;
    for (const match of row.matches || []) {
      claims.push({ slot: `Q${row.n}`, source_excerpt: match.text });
    }
  }
  for (const [question, result] of computed) {
    if (!from.has(question) || !result || result.reason !== null) continue;
    figures.push({
      label: `Q${question} ${result.formula}`,
      value: result.value,
      formula: result.formula,
      inputs: result.inputs,
    });
  }
  return evidenceFor({ claims, figures });
}
