/**
 * Answering "do we have this" without mistaking it for "does the filing have
 * this".
 *
 * The old answer to a missing input was "operating_cash_flow not reported",
 * which reads as a statement about the annual report and was a statement about
 * the store. Reliance reports 1,92,113 crore of it on page 103. So a missing
 * input starts a search of the document, and only a search that has actually
 * run and found nothing licenses saying the filing is silent.
 *
 * That distinction needs more than two words for the outcome:
 *
 *   found_in_store          already extracted
 *   recovered_from_document not in the store, found in the filing, verified
 *   derived                 not stated anywhere, computed from what is
 *   not_disclosed           searched for and not there
 *   no_way_to_look          nothing knows where this would be in a filing
 *
 * `no_way_to_look` is not a state a reader would ask for and it is the honest
 * one for most of what is currently unanswered. Collapsing it into
 * not_disclosed would claim the filing is silent about figures nobody has
 * taught the system to find, which is the same error as before wearing a
 * better word.
 *
 * The state says where a figure came from and nothing else. Whether it can be
 * used for the purpose asked is the selection's business and is reported
 * separately, because they are different questions with different answers: a
 * cash flow recovered from page 103 is found, and is still no use to a reader
 * who asked for a statutory basis. An earlier version of this collapsed the
 * two, and reported a concept with exactly one definition as needing a
 * definition - which is the mistake this file exists to stop making.
 */
import { DEFINITIONS } from './factOntology.js';
import { readFacts } from './factExtraction.js';
import { TARGETS, findCandidates } from './factRetrieval.js';
import { observationsFor, reconcileFamily } from './factReconciliation.js';

export const STATE = Object.freeze({
  FOUND_IN_STORE: 'found_in_store',
  RECOVERED_FROM_DOCUMENT: 'recovered_from_document',
  DERIVED: 'derived',
  NOT_DISCLOSED: 'not_disclosed',
  NO_WAY_TO_LOOK: 'no_way_to_look',
});

/** Every definition of a concept that something knows how to look for. */
export function searchableDefinitions(concept) {
  return [...DEFINITIONS]
    .filter(([id, definition]) => definition.concept === concept && TARGETS.has(id))
    .map(([id]) => id);
}

/**
 * One concept, resolved against the store and then against the document.
 *
 * Returns the facts it recovered separately from the answer, because writing
 * them is the caller's decision and a resolution that wrote as a side effect
 * would put figures in the store during a dry run.
 */
export function resolveConcept({
  facts = [], pages = [], concept, period_end, purpose, prefer = {},
  accounting_scope = 'consolidated', segment = null,
  company, reportedInDocument, document, currency, unit,
}) {
  const at = { concept, period_end, accounting_scope, segment };
  const held = observationsFor(facts, at);
  if (held.length) {
    // Held, whether or not it can be used: searching the document again would
    // find the same figures and the same disagreement.
    return {
      ...at, state: STATE.FOUND_IN_STORE, recovered: [], searched: [],
      selection: reconcileFamily({ facts, ...at, purpose, prefer }),
    };
  }

  const searchable = searchableDefinitions(concept);
  if (!searchable.length) {
    return {
      ...at, state: STATE.NO_WAY_TO_LOOK, selection: null, recovered: [], searched: [],
      reason: `nothing knows where ${concept} is found in a filing`,
    };
  }

  const candidates = [];
  for (const definition_id of searchable) {
    const found = findCandidates({ pages, definition_id, accounting_scope, currency, unit });
    candidates.push(...found.candidates);
  }
  // Retrieval proposes; the citation check decides, exactly as it does for a
  // reading a model produced.
  const { facts: verified } = readFacts({
    payload: { facts: candidates }, document, company, reportedInDocument,
  });
  const forPeriod = verified.filter((fact) => fact.period_end === period_end
    && (fact.segment || null) === (segment || null));

  if (!forPeriod.length) {
    return {
      ...at, state: STATE.NOT_DISCLOSED, selection: null, recovered: verified, searched: searchable,
      reason: `${searchable.length} place${searchable.length === 1 ? '' : 's'} in the filing were searched and none disclosed it`,
    };
  }

  return {
    ...at,
    state: STATE.RECOVERED_FROM_DOCUMENT,
    selection: reconcileFamily({ facts: [...facts, ...forPeriod], ...at, purpose, prefer }),
    // Every verified fact, not only the period asked for: a statement page
    // carries two years and discarding the comparative would mean searching
    // for it again.
    recovered: verified,
    searched: searchable,
  };
}

/**
 * Several concepts at once, with the facts recovered along the way.
 *
 * Recovered facts are threaded into each subsequent resolution, so a document
 * is searched once for a definition however many questions want it.
 */
export function resolveConcepts({ concepts = [], facts = [], ...rest }) {
  const known = [...facts];
  const resolutions = new Map();
  const recovered = [];
  const seen = new Set(facts.map((fact) => `${fact.definition_id}|${fact.period_end}`));
  for (const concept of concepts) {
    const result = resolveConcept({ ...rest, facts: known, concept });
    resolutions.set(concept, result);
    for (const fact of result.recovered) {
      const key = `${fact.definition_id}|${fact.period_end}`;
      if (seen.has(key)) continue;
      seen.add(key);
      known.push(fact);
      recovered.push(fact);
    }
  }
  return { resolutions, recovered, facts: known };
}

/** What a set of resolutions found, counted by state. */
export function tally(resolutions) {
  const counts = Object.fromEntries(Object.values(STATE).map((state) => [state, 0]));
  for (const result of resolutions.values()) counts[result.state] += 1;
  return counts;
}
