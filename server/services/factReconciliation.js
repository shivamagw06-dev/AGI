/**
 * Which figure to use, and what using it gives up.
 *
 * The store refuses to pick, and it is right to: Reliance's capital
 * expenditure is ₹1,44,271 crore and ₹1,22,916 crore, and neither is the
 * mistake. But a reader has to put one number into one calculation, and
 * answering "it depends" is not a product.
 *
 * What makes the choice answerable is a purpose. "Which capex is correct" has
 * no answer. "Which capex belongs in a cash-based free cash flow" has one, and
 * the reason is not that the cash figure is truer - it is that putting an
 * accrual figure into a cash identity changes what the result means without
 * changing what it looks like. So selection here is by declared purpose, the
 * rule applied is stated in the output, and every figure not chosen is carried
 * alongside with the difference named against both sides.
 *
 * Three refusals keep this honest. A purpose that cannot separate two
 * observations - Reliance discloses revenue three ways, all statutory - is
 * reported as needing a definition rather than broken by a tiebreak. A choice
 * made by the caller is recorded as the caller's, not dressed up as a rule.
 * And a purpose applied across several concepts is checked for coherence,
 * because choosing cash capex and then pairing it with an accrual cash flow
 * is the same category error arrived at in two steps.
 */
import { DEFINITIONS, MEASUREMENT, VERDICT, isUnrecorded } from './factOntology.js';
import { isStale } from './factCalculation.js';

const round = (value, places = 6) => Number(value.toFixed(places));
const scopeOf = (fact) => fact?.accounting_scope || 'consolidated';

/**
 * What a reader is trying to do, expressed as an ordered preference over
 * measurement bases.
 *
 * Ranks after the first are substitutions, not equals. Taking them is
 * sometimes the only way to answer at all, so they are allowed - and every one
 * of them attaches a caveat saying what was swapped for what.
 */
export const PURPOSES = new Map([
  ['cash_basis', {
    label: 'a cash-based calculation',
    rule: 'a cash calculation takes cash measurements; another basis changes what the answer means',
    prefer: [[MEASUREMENT.CASH], [MEASUREMENT.ACCRUAL, MEASUREMENT.STATUTORY, MEASUREMENT.MANAGEMENT_ADJUSTED]],
  }],
  ['accrual_basis', {
    label: 'an accruals comparison',
    rule: 'an accruals comparison takes the accrual measurement, then the statutory one',
    prefer: [[MEASUREMENT.ACCRUAL], [MEASUREMENT.STATUTORY], [MEASUREMENT.MANAGEMENT_ADJUSTED]],
  }],
  ['as_management_reports', {
    label: "management's own presentation",
    rule: "management's presentation takes its adjusted figures, then its accrual ones",
    prefer: [[MEASUREMENT.MANAGEMENT_ADJUSTED], [MEASUREMENT.ACCRUAL], [MEASUREMENT.STATUTORY]],
  }],
  ['statutory_basis', {
    label: 'the statutory accounts',
    rule: 'the statutory accounts take the statutory measurement and nothing else',
    prefer: [[MEASUREMENT.STATUTORY]],
  }],
  // Reading a filing rather than building one calculation. Fifty-one questions
  // want different bases - a margin wants a statutory revenue and a free cash
  // flow wants cash capex - and forcing one basis across them blocks whichever
  // half it does not suit. This admits every basis at first preference, so a
  // single disclosed figure is taken as it is and a concept disclosed several
  // ways comes back needing a definition, which is the reader's choice to make
  // rather than a rule's.
  ['any_disclosed', {
    label: 'reading what the filing discloses',
    rule: 'any disclosed basis is taken; where a concept is disclosed several ways the definition must be named',
    prefer: [[MEASUREMENT.CASH, MEASUREMENT.ACCRUAL, MEASUREMENT.STATUTORY,
      MEASUREMENT.MANAGEMENT_ADJUSTED, MEASUREMENT.SEGMENT_REPORTING, MEASUREMENT.DERIVED_RATIO,
      MEASUREMENT.COUNT]],
  }],
  ['segment_basis', {
    label: 'segment analysis',
    rule: 'segment analysis takes the segment note, which is the only basis segments are disclosed on',
    prefer: [[MEASUREMENT.SEGMENT_REPORTING]],
  }],
]);

/** A stated fact outranks one computed from it, which outranks a judgement. */
const STANDING = [VERDICT.STATED, VERDICT.DERIVED, VERDICT.INFERRED];
const standingOf = (fact) => {
  const at = STANDING.indexOf(fact?.verdict || VERDICT.STATED);
  return at === -1 ? STANDING.length : at;
};

/** Every observation of one concept for one period, scope and segment. */
export function observationsFor(facts, { concept, period_end, accounting_scope = 'consolidated', segment = null }) {
  return (facts || []).filter((fact) => fact
    && fact.concept === concept
    && fact.period_end === period_end
    && scopeOf(fact) === accounting_scope
    && (fact.segment || null) === (segment || null)
    && Number.isFinite(Number(fact.value)));
}

const measurementOf = (fact) => fact.measurement_basis
  || DEFINITIONS.get(fact.definition_id)?.measurement
  || 'unknown';

function differencesFrom(chosen, others) {
  return others.map((fact) => {
    const gap = round(Number(chosen.value) - Number(fact.value), 6);
    return {
      definition_id: fact.definition_id,
      value: Number(fact.value),
      measurement: measurementOf(fact),
      difference: gap,
      // The same gap is a different proportion of each side, and a reader
      // deciding whether it matters needs the one that applies to them.
      as_share_of_chosen: Number(chosen.value) === 0 ? null : round(gap / Number(chosen.value), 6),
      as_share_of_alternative: Number(fact.value) === 0 ? null : round(gap / Number(fact.value), 6),
    };
  });
}

/**
 * One concept, one purpose, one answer - with the rule that produced it and
 * everything it displaced.
 */
export function reconcileFamily({
  facts, concept, period_end, accounting_scope = 'consolidated', segment = null,
  purpose, prefer = {},
}) {
  const at = { concept, period_end, accounting_scope, segment };
  const base = { ...at, purpose: purpose || null };
  const caveats = [];

  let observations = observationsFor(facts, at);
  // A derived figure whose inputs have moved is not an alternative. It is a
  // figure that should already have been withdrawn.
  const live = [];
  for (const fact of observations) {
    if (fact.verdict !== VERDICT.DERIVED) { live.push(fact); continue; }
    const staleness = isStale(fact, facts);
    if (!staleness.stale) { live.push(fact); continue; }
    caveats.push(`${fact.definition_id} was left out: ${staleness.reasons.join('; ')}`);
  }
  observations = live;

  if (!observations.length) return { ...base, status: 'not_disclosed', chosen: null, forgone: [], caveats };

  const units = new Set(observations.map((fact) => `${fact.currency ?? ''}|${fact.unit ?? ''}`));
  if (units.size > 1) {
    return { ...base, status: 'not_comparable', chosen: null, forgone: [], caveats,
      reason: `observations are stated in ${[...units].join(' and ')}` };
  }

  const widest = (() => {
    const values = observations.map((fact) => Number(fact.value));
    const high = Math.max(...values);
    const low = Math.min(...values);
    return high === low ? null : {
      high, low, difference: round(high - low, 6),
      as_share_of_low: low === 0 ? null : round((high - low) / low, 6),
    };
  })();

  // The caller naming a definition is the caller's decision, and is recorded
  // as one. Dressing it up as a rule would hide who made the choice.
  const named = prefer[concept];
  if (named) {
    const chosen = observations.find((fact) => fact.definition_id === named);
    if (!chosen) {
      return { ...base, status: 'no_fit', chosen: null, spread: widest, caveats,
        forgone: differencesFrom(observations[0], observations.slice(1)),
        reason: `${named} is not among the disclosed observations` };
    }
    return answered({
      ...base, status: 'selected', chosen, rule: 'named by the caller', chosen_at_rank: null,
      forgone: differencesFrom(chosen, observations.filter((fact) => fact !== chosen)),
      spread: widest, caveats,
    });
  }

  if (!purpose) {
    return { ...base, status: 'no_purpose', chosen: null, spread: widest, caveats,
      forgone: differencesFrom(observations[0], observations.slice(1)),
      reason: 'a purpose or a named definition is required to choose' };
  }
  const wanted = PURPOSES.get(purpose);
  if (!wanted) {
    return { ...base, status: 'no_fit', chosen: null, spread: widest, caveats, reason: `unknown purpose ${purpose}` };
  }

  if (observations.length === 1) {
    const only = observations[0];
    const rank = wanted.prefer.findIndex((bases) => bases.includes(measurementOf(only)));
    if (rank === -1) {
      return { ...base, status: 'no_fit', chosen: null, spread: widest, caveats,
        forgone: [], reason: `the only observation is measured ${measurementOf(only)}, which ${wanted.label} does not admit` };
    }
    if (rank > 0) caveats.push(substitution(wanted, only));
    return answered({ ...base, status: 'only_one_observation', chosen: only, rule: wanted.rule,
      chosen_at_rank: rank, forgone: [], spread: null, caveats });
  }

  for (const [rank, bases] of wanted.prefer.entries()) {
    const fits = observations.filter((fact) => bases.includes(measurementOf(fact)));
    if (!fits.length) continue;
    const best = Math.min(...fits.map(standingOf));
    const front = fits.filter((fact) => standingOf(fact) === best);
    if (front.length > 1) {
      // Reliance discloses revenue three ways and all three are statutory. No
      // rule about measurement can separate them, and inventing a tiebreak
      // would make the store's answer depend on extraction order.
      return {
        ...base, status: 'needs_a_definition', chosen: null, spread: widest, caveats,
        candidates: front.map((fact) => ({ definition_id: fact.definition_id, value: Number(fact.value),
          measurement: measurementOf(fact) })),
        forgone: differencesFrom(front[0], observations.filter((fact) => fact !== front[0])),
        reason: `${wanted.label} does not separate ${front.map((fact) => fact.definition_id).join(' and ')}`,
      };
    }
    const chosen = front[0];
    if (rank > 0) caveats.push(substitution(wanted, chosen));
    return answered({
      ...base, status: 'selected', chosen, rule: wanted.rule, chosen_at_rank: rank,
      forgone: differencesFrom(chosen, observations.filter((fact) => fact !== chosen)),
      spread: widest, caveats,
    });
  }
  return { ...base, status: 'no_fit', chosen: null, spread: widest, caveats,
    forgone: differencesFrom(observations[0], observations.slice(1)),
    reason: `nothing disclosed is measured on a basis ${wanted.label} admits` };
}

/**
 * A selection, with a caveat if the figure's definition was never recorded.
 *
 * Applied at every point a figure is chosen rather than at one of them,
 * because the quiet case is the dangerous one: a company with a single
 * unrecorded revenue would otherwise come back as a clean answer with nothing
 * saying the definition is unknown.
 */
function answered(result) {
  if (!result.chosen || !isUnrecorded(result.chosen.definition_id)) return result;
  return {
    ...result,
    unrecorded: true,
    caveats: [...(result.caveats || []),
      `${result.chosen.definition_id}: the source recorded a figure but not which definition it is`],
  };
}

function substitution(wanted, fact) {
  return `no ${wanted.prefer[0].join(' or ')} observation was disclosed; `
    + `${fact.definition_id} is measured ${measurementOf(fact)}, which is not the same thing`;
}

/**
 * Whether a set of choices can be used together.
 *
 * Choosing cash capital expenditure and then pairing it with an accrual cash
 * flow is the same category error the purpose exists to prevent, arrived at
 * one concept at a time. Anything taken below first preference is named.
 */
export function coherenceOf(selections, purpose) {
  const wanted = PURPOSES.get(purpose);
  if (!wanted) return { coherent: false, reason: `unknown purpose ${purpose}`, substituted: [], unresolved: [] };
  const made = selections.filter((row) => row.chosen);
  const substituted = made.filter((row) => row.chosen_at_rank > 0)
    .map((row) => ({ concept: row.concept, definition_id: row.chosen.definition_id,
      measurement: measurementOf(row.chosen) }));
  const unresolved = selections.filter((row) => !row.chosen)
    .map((row) => ({ concept: row.concept, status: row.status, reason: row.reason || null }));
  // A figure whose definition nobody wrote down is not a basis for work that
  // depends on the definition, so a set containing one is not coherent however
  // cleanly the rest of it resolved.
  const unrecorded = made.filter((row) => row.unrecorded)
    .map((row) => ({ concept: row.concept, definition_id: row.chosen.definition_id }));
  return {
    coherent: substituted.length === 0 && unresolved.length === 0 && unrecorded.length === 0,
    bases: [...new Set(made.map((row) => measurementOf(row.chosen)))].sort(),
    substituted,
    unrecorded,
    unresolved,
  };
}

/** Every concept the facts cover, reconciled for one purpose, plus coherence. */
export function reconcileFor({ facts, purpose, period_end, accounting_scope = 'consolidated', segment = null, prefer = {} }) {
  const concepts = [...new Set((facts || [])
    .filter((fact) => fact && fact.period_end === period_end
      && scopeOf(fact) === accounting_scope
      && (fact.segment || null) === (segment || null))
    .map((fact) => fact.concept))].sort();
  const selections = concepts.map((concept) => reconcileFamily({
    facts, concept, period_end, accounting_scope, segment, purpose, prefer,
  }));
  return { purpose, period_end, accounting_scope, segment, selections, coherence: coherenceOf(selections, purpose) };
}
