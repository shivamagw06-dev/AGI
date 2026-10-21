/**
 * The computed questions, answered from facts rather than from a row of
 * columns.
 *
 * computedAnswers reads a period as a bag of line items - period.revenue,
 * period.ebitda - which is the shape company_financials stores and the shape
 * that cannot say which revenue it holds. The formulas are right and worth
 * keeping; what has to change is where the numbers come from and what travels
 * with them.
 *
 * So a period is assembled by resolving each line item the questions ask for:
 * looked for in the store, then in the document, and reported as unfound only
 * after a search has run. Alongside the values goes what produced them - the
 * definition chosen, the page it was read from, and any caveat the choice
 * carries. An answer of 17.7% is worth little without knowing it was taken on
 * value of sales and services rather than on revenue from operations, and the
 * old shape had no room to say.
 */
import { DEFINITIONS } from './factOntology.js';
import { QUESTIONS } from './annualReportQuestions.js';
import { computedAnswers } from './annualReportComputed.js';
import { STATE, resolveConcepts } from './factResolution.js';

/**
 * What the questions call a thing, and what the ontology calls it.
 *
 * Only the names that differ are listed; everything else is the same word in
 * both, and a need with no concept behind it is a need nothing can answer yet.
 */
export const NEED_CONCEPTS = new Map([
  ['operating_cash_flow', 'cfo'],
  ['gross_debt', 'debt'],
  ['total_equity', 'equity'],
  ['segment_revenue', 'revenue'],
  ['segment_ebit', 'ebit'],
  ['operating_profit', 'ebit'],
  ['adjusted_ebitda', 'ebitda'],
]);

/**
 * Names that mean one definition, not a concept.
 *
 * "gross_debt" is not whichever debt a filing happens to state - it is gross
 * debt. Resolved by concept alone, a filing disclosing both gross and net debt
 * came back needing a definition, and one disclosing only net debt would have
 * put net debt under the gross name. Pinned names are written from their own
 * definition, whatever the concept's selection chose.
 */
export const DEFINITION_FIELDS = new Map([
  ['DEBT.GROSS', 'gross_debt'],
  ['DEBT.NET', 'net_debt'],
]);
const FIELD_DEFINITIONS = new Map([...DEFINITION_FIELDS].map(([id, field]) => [field, id]));

/** Every line item the computed questions ask for, as concepts. */
export function neededConcepts(questions = QUESTIONS) {
  const needs = new Set();
  for (const question of questions) {
    if (question.kind !== 'computed') continue;
    for (const need of question.needs || []) needs.add(NEED_CONCEPTS.get(need) ?? need);
  }
  return [...needs].sort();
}

const NEED_FOR_CONCEPT = (() => {
  const index = new Map();
  for (const [need, concept] of NEED_CONCEPTS) {
    if (!index.has(concept)) index.set(concept, []);
    index.get(concept).push(need);
  }
  return index;
})();

/**
 * One period as the formulas expect it, with what produced each figure.
 *
 * The line item is written under every name the questions use for it, so a
 * formula asking for `operating_cash_flow` and one asking for `cfo` read the
 * same resolved figure rather than one of them finding nothing.
 */
export function periodFromResolutions(resolutions, { period_end, currency, unit, period_type = 'annual' }) {
  const period = { period_end, period_type, currency, scale: unit };
  const provenance = {};
  for (const [concept, result] of resolutions) {
    const chosen = result.selection?.chosen;
    // Every observation of this concept for this period, by definition, so a
    // pinned name can be written from its own definition and cited to its own
    // page rather than borrowing whatever the selection chose.
    const observed = {};
    const note = (definition_id, value, source_page) => {
      if (!definition_id || observed[definition_id] || value === null || value === undefined) return;
      observed[definition_id] = {
        state: result.state, definition_id, value: Number(value),
        label: DEFINITIONS.get(definition_id)?.label ?? null, source_page: source_page ?? null,
      };
    };
    for (const fact of [chosen, ...(result.recovered || [])]) {
      if (fact && fact.period_end === period_end && !fact.segment) note(fact.definition_id, fact.value, fact.source_page);
    }
    for (const one of [...(result.selection?.candidates || []), ...(result.selection?.forgone || [])]) {
      note(one.definition_id, one.value, null);
    }

    const names = [concept, ...(NEED_FOR_CONCEPT.get(concept) || [])];
    for (const name of names) period[name] = chosen ? Number(chosen.value) : null;
    // Written after the names above, so a pinned field is its own definition's
    // figure whatever the concept's selection was - or nothing, if the filing
    // did not disclose that definition.
    for (const [definition_id, field] of DEFINITION_FIELDS) {
      if (DEFINITIONS.get(definition_id)?.concept !== concept) continue;
      period[field] = observed[definition_id] ? observed[definition_id].value : null;
    }
    provenance[concept] = {
      state: result.state,
      status: result.selection?.status ?? null,
      definition_id: chosen?.definition_id ?? null,
      label: chosen ? DEFINITIONS.get(chosen.definition_id)?.label ?? null : null,
      source_page: chosen?.source_page ?? null,
      caveats: result.selection?.caveats || [],
      candidates: result.selection?.candidates?.map((one) => one.definition_id) || null,
      reason: result.reason || result.selection?.reason || null,
      observed,
    };
  }
  return { period, provenance };
}

/** What produced a named input: its pinned definition if it has one, else its concept. */
function provenanceOf(name, provenance) {
  const pinned = FIELD_DEFINITIONS.get(name);
  const concept = pinned ? DEFINITIONS.get(pinned).concept : (NEED_CONCEPTS.get(name) ?? name);
  const entry = provenance[concept];
  if (!entry) return null;
  return pinned ? entry.observed?.[pinned] ?? null : entry;
}

/**
 * Why a question could not be answered, in the words of the thing that stopped
 * it.
 *
 * "not reported" said about a filing that reports it was the whole complaint.
 * A question blocked by an input says which input and what happened when it
 * was looked for.
 */
export function blockedBy(question, provenance) {
  const blocking = [];
  for (const need of question.needs || []) {
    const concept = NEED_CONCEPTS.get(need) ?? need;
    const found = provenance[concept];
    if (!found) { blocking.push({ need, concept, state: 'not_asked_for' }); continue; }
    const pinned = FIELD_DEFINITIONS.get(need);
    if (pinned) {
      // A pinned name is satisfied by its own definition, not by the concept's
      // selection - which, with gross and net debt both disclosed, is a choice
      // nobody asking for gross debt needs to make.
      if (found.observed?.[pinned]) continue;
      if (found.state === STATE.FOUND_IN_STORE || found.state === STATE.RECOVERED_FROM_DOCUMENT) {
        blocking.push({ need, concept: need, state: STATE.NOT_DISCLOSED, reason: `${pinned} was not found, though ${concept} was` });
      } else {
        blocking.push({ need, concept, state: found.state, reason: found.reason });
      }
      continue;
    }
    if (found.state === STATE.FOUND_IN_STORE || found.state === STATE.RECOVERED_FROM_DOCUMENT) {
      if (found.status === 'needs_a_definition' || found.status === 'no_fit') {
        blocking.push({ need, concept, state: found.state, status: found.status,
          candidates: found.candidates, reason: found.reason });
      }
      continue;
    }
    blocking.push({ need, concept, state: found.state, reason: found.reason });
  }
  return blocking;
}

/**
 * Which periods to resolve, given what is already stored and what was asked
 * for.
 *
 * Newest first and bounded. A filing carries ten years in its highlights table
 * and resolving all of them costs a search of the document per year for
 * nothing a reader asked about, so the list is capped - and the cap takes the
 * newest, because a question about growth wants this year and last, not the
 * two furthest back.
 */
export function periodEndsFor({ held = [], requested = [], limit = 6 } = {}) {
  const ends = new Set();
  for (const fact of held) if (fact?.period_end) ends.add(fact.period_end);
  for (const end of requested) {
    const trimmed = String(end ?? '').trim();
    if (trimmed) ends.add(trimmed);
  }
  return [...ends].sort((a, b) => String(b).localeCompare(String(a))).slice(0, limit);
}

/**
 * Every computed question, answered from the store and the document together.
 *
 * `periods` are resolved newest first, because the formulas compare the first
 * against the second and a series assembled the other way round reports every
 * change with its sign reversed.
 */
export function answersFromFacts({
  periodEnds = [], facts = [], pages = [], document,
  company, reportedInDocument, purpose = 'as_management_reports', prefer = {},
  accounting_scope = 'consolidated', currency, unit, month_end, questions = QUESTIONS,
}) {
  const concepts = neededConcepts(questions);
  const ordered = [...periodEnds].sort((a, b) => String(b).localeCompare(String(a)));
  const known = [...facts];
  const recovered = [];
  const periods = [];
  const provenance = new Map();

  for (const period_end of ordered) {
    const result = resolveConcepts({
      concepts, facts: known, pages, document, company, reportedInDocument,
      period_end, purpose, prefer, accounting_scope, currency, unit,
      month_end: month_end || String(period_end).slice(5),
    });
    for (const fact of result.recovered) { known.push(fact); recovered.push(fact); }
    const built = periodFromResolutions(result.resolutions, { period_end, currency, unit });
    periods.push(built.period);
    provenance.set(period_end, built.provenance);
  }

  const answers = computedAnswers(periods);
  const now = provenance.get(ordered[0]) || {};
  const decorated = new Map();
  for (const question of questions) {
    if (question.kind !== 'computed') continue;
    const answer = answers.get(question.n) || null;
    const blocking = blockedBy(question, now);
    // What each input was, where it came from, and what it cost to choose it.
    // A margin is worth little without knowing which revenue is under it.
    let used = Object.fromEntries((question.needs || []).map((need) => [need, provenanceOf(need, now)]));
    // An answer that read a stated figure in place of computing it cites what
    // it read. Net debt taken as stated is not built from cash, and citing the
    // cash line would send a reader to a figure the answer never used.
    if (answer?.stated?.length) {
      const inputs = new Set(Object.keys(answer.inputs || {}));
      used = Object.fromEntries(Object.entries(used).filter(([name]) => inputs.has(name)));
      for (const field of answer.stated) used[field] = provenanceOf(field, now);
    }
    const hasValue = answer && answer.value !== null && answer.value !== undefined;
    decorated.set(question.n, {
      // A missing formula is flagged rather than left to be read out of the
      // reason's wording, because a question with every input resolved and no
      // formula is a different gap from one whose inputs were never found.
      ...(answer || { value: null, formula: null, inputs: null, reason: 'no rule computes this yet', no_rule: true }),
      used,
      // An answered question has nothing blocking it, whatever an unused need
      // would have reported.
      blocked_by: !hasValue && blocking.length ? blocking : null,
    });
  }
  return { answers: decorated, periods, provenance, recovered, facts: known };
}
