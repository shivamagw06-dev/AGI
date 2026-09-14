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
    const names = [concept, ...(NEED_FOR_CONCEPT.get(concept) || [])];
    for (const name of names) period[name] = chosen ? Number(chosen.value) : null;
    provenance[concept] = {
      state: result.state,
      status: result.selection?.status ?? null,
      definition_id: chosen?.definition_id ?? null,
      source_page: chosen?.source_page ?? null,
      caveats: result.selection?.caveats || [],
      candidates: result.selection?.candidates?.map((one) => one.definition_id) || null,
      reason: result.reason || result.selection?.reason || null,
    };
  }
  return { period, provenance };
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
  accounting_scope = 'consolidated', currency, unit, questions = QUESTIONS,
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
    decorated.set(question.n, {
      ...(answer || { value: null, formula: null, inputs: null, reason: 'no rule computes this yet' }),
      // What each input was, where it came from, and what it cost to choose
      // it. A margin is worth little without knowing which revenue is under it.
      used: Object.fromEntries((question.needs || [])
        .map((need) => [need, now[NEED_CONCEPTS.get(need) ?? need] ?? null])),
      blocked_by: blocking.length ? blocking : null,
    });
  }
  return { answers: decorated, periods, provenance, recovered, facts: known };
}
