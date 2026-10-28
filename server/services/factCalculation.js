/**
 * Figures the filing does not state, computed from figures it does.
 *
 * The thing that makes this hard is not arithmetic. It is that a computed
 * figure has no meaning without the inputs that produced it, and the inputs
 * change. Reliance's free cash flow is ₹69,197 crore or ₹47,842 crore
 * depending on which capital expenditure went into it; if next year's report
 * restates the operating cash flow, both become wrong while continuing to look
 * like answers. A number that has forgotten where it came from cannot be
 * withdrawn.
 *
 * So nothing here returns a bare number. A result carries the definition it
 * computed, the keys of the facts it consumed, and the expression it applied,
 * and `isStale` re-resolves those inputs against the current facts and says so
 * when they have moved. The definition is not chosen - it is determined by the
 * inputs, which is why `FCF.CFO_MINUS_CASH_CAPEX` and
 * `FCF.CFO_MINUS_MANAGEMENT_CAPEX` are separate recipes rather than one recipe
 * with a preference.
 *
 * Two refusals matter more than any of the formulas. An input that resolves to
 * more than one value is not silently picked from; and a figure the filing
 * already states is computed anyway and reported beside the stated one, never
 * in place of it.
 */
import { DEFINITIONS, VERDICT, derive, factKey } from './factOntology.js';
import { statedPrecision } from './factVerification.js';

const round = (value, places = 6) => Number(value.toFixed(places));

/** What a derived figure is made of, and what making it implies about it. */
export const RECIPES = new Map([
  ['FCF.CFO_MINUS_CASH_CAPEX', {
    inputs: { cfo: 'CFO.STATEMENT', capex: 'CAPEX.CASH_PPE_INTANGIBLES' },
    expression: 'cfo - capex', formula: ({ cfo, capex }) => cfo - capex, produces: 'money',
  }],
  ['FCF.CFO_MINUS_MANAGEMENT_CAPEX', {
    inputs: { cfo: 'CFO.STATEMENT', capex: 'CAPEX.MANAGEMENT' },
    expression: 'cfo - capex', formula: ({ cfo, capex }) => cfo - capex, produces: 'money',
  }],
  ['EBITDA_MARGIN.ON_REVENUE_OPERATIONS_NET', {
    inputs: { ebitda: 'EBITDA.REPORTED', revenue: 'REVENUE.OPERATIONS_NET' },
    expression: 'ebitda / revenue', formula: ({ ebitda, revenue }) => ebitda / revenue, produces: 'ratio',
  }],
  ['EBITDA_MARGIN.ON_VALUE_OF_SALES_AND_SERVICES', {
    inputs: { ebitda: 'EBITDA.REPORTED', revenue: 'REVENUE.VALUE_OF_SALES_AND_SERVICES' },
    expression: 'ebitda / revenue', formula: ({ ebitda, revenue }) => ebitda / revenue, produces: 'ratio',
  }],
  ['LEVERAGE.NET_DEBT_TO_EBITDA', {
    inputs: { debt: 'DEBT.NET', ebitda: 'EBITDA.REPORTED' },
    expression: 'debt / ebitda', formula: ({ debt, ebitda }) => debt / ebitda, produces: 'ratio',
  }],
  ['LEVERAGE.GROSS_DEBT_TO_EBITDA', {
    inputs: { debt: 'DEBT.GROSS', ebitda: 'EBITDA.REPORTED' },
    expression: 'debt / ebitda', formula: ({ debt, ebitda }) => debt / ebitda, produces: 'ratio',
  }],
  // Two levels deep: the numerator is itself computed, so a restated operating
  // cash flow has to invalidate this as well as the free cash flow under it.
  ['FCF_MARGIN.CASH_CAPEX_ON_REVENUE_OPERATIONS_NET', {
    inputs: { fcf: 'FCF.CFO_MINUS_CASH_CAPEX', revenue: 'REVENUE.OPERATIONS_NET' },
    expression: 'fcf / revenue', formula: ({ fcf, revenue }) => fcf / revenue, produces: 'ratio',
  }],
  ['FCF_MARGIN.MANAGEMENT_CAPEX_ON_REVENUE_OPERATIONS_NET', {
    inputs: { fcf: 'FCF.CFO_MINUS_MANAGEMENT_CAPEX', revenue: 'REVENUE.OPERATIONS_NET' },
    expression: 'fcf / revenue', formula: ({ fcf, revenue }) => fcf / revenue, produces: 'ratio',
  }],
]);

const scopeOf = (fact) => fact?.accounting_scope || 'consolidated';
const halfUlp = (fact) => 0.5 * (10 ** -statedPrecision(fact));

const matches = (fact, { definition_id, period_end, accounting_scope, segment }) => fact
  && fact.definition_id === definition_id
  && fact.period_end === period_end
  && scopeOf(fact) === accounting_scope
  && (fact.segment || null) === (segment || null);

/**
 * The stated fact an input refers to, or the reason there isn't one.
 *
 * Two facts under one definition for one period is the restatement case, and
 * the calculator is the wrong place to decide which document is current. It
 * refuses and names both, unless the caller has said which document it means.
 */
export function resolveInput(facts, where) {
  const found = (facts || []).filter((fact) => matches(fact, where)
    && (!where.reported_in_document || fact.reported_in_document === where.reported_in_document));
  if (!found.length) return { fact: null, reason: `${where.definition_id} is not disclosed` };
  const values = new Set(found.map((fact) => Number(fact.value)));
  if (values.size > 1) {
    return {
      fact: null,
      reason: `${where.definition_id} resolves to ${[...values].join(' and ')} across ${found.length} documents`,
    };
  }
  return { fact: found[0], reason: null };
}

/**
 * How far a computed figure can be from the truth because its inputs were
 * rounded.
 *
 * Absolute slack adds under subtraction and relative slack adds under
 * division, so a ratio of two crore-rounded figures is known far more
 * precisely than either of them. Treating both the same way would either
 * reject Retail's stated 8.2% margin or accept almost anything.
 */
export function propagatedSlack({ produces, value, inputs }) {
  const rows = Object.values(inputs);
  if (produces === 'money') return round(rows.reduce((sum, fact) => sum + halfUlp(fact), 0), 9);
  const relative = rows.reduce((sum, fact) => {
    const magnitude = Math.abs(Number(fact.value));
    return magnitude === 0 ? Infinity : sum + halfUlp(fact) / magnitude;
  }, 0);
  return round(Math.abs(value) * relative, 9);
}

const MAX_DEPTH = 6;

/**
 * One derived figure, or a stated reason there is none.
 *
 * Never returns a number without `input_fact_ids`. An absent input produces an
 * unsupported result rather than a partial calculation, because a free cash
 * flow missing its capital expenditure is just an operating cash flow wearing
 * the wrong label.
 */
export function calculate(facts, where, seen = new Set()) {
  const { definition_id } = where;
  const at = { ...where, accounting_scope: where.accounting_scope || 'consolidated', segment: where.segment || null };
  const base = {
    concept: DEFINITIONS.get(definition_id)?.concept || null,
    definition_id,
    period_end: at.period_end,
    accounting_scope: at.accounting_scope,
    segment: at.segment,
  };

  const recipe = RECIPES.get(definition_id);
  if (!recipe) return { ...base, value: null, verdict: VERDICT.UNSUPPORTED, reason: `no recipe for ${definition_id}` };
  if (seen.has(definition_id)) {
    return { ...base, value: null, verdict: VERDICT.UNSUPPORTED, reason: `${definition_id} depends on itself` };
  }
  if (seen.size >= MAX_DEPTH) {
    return { ...base, value: null, verdict: VERDICT.UNSUPPORTED, reason: 'derivation is too deep' };
  }
  const deeper = new Set([...seen, definition_id]);

  const inputs = {};
  for (const [name, inputDefinition] of Object.entries(recipe.inputs)) {
    const resolved = resolveInput(facts, { ...at, definition_id: inputDefinition });
    if (resolved.fact) { inputs[name] = resolved.fact; continue; }
    // A missing input may itself be derivable. A missing input that resolves
    // to two values must not be, or the ambiguity would be laundered into a
    // computed figure that looks settled.
    if (!RECIPES.has(inputDefinition) || /resolves to/.test(resolved.reason)) {
      return { ...base, value: null, verdict: VERDICT.UNSUPPORTED, reason: resolved.reason };
    }
    const nested = calculate(facts, { ...at, definition_id: inputDefinition }, deeper);
    if (nested.verdict === VERDICT.UNSUPPORTED) {
      return { ...base, value: null, verdict: VERDICT.UNSUPPORTED, reason: nested.reason };
    }
    inputs[name] = nested;
  }

  const monies = Object.values(inputs).filter((fact) => fact.currency);
  const units = new Set(monies.map((fact) => `${fact.currency}|${fact.unit}`));
  if (units.size > 1) {
    return { ...base, value: null, verdict: VERDICT.UNSUPPORTED, reason: `inputs are stated in ${[...units].join(' and ')}` };
  }
  const [currency, unit] = (monies[0] ? `${monies[0].currency}|${monies[0].unit}` : '|').split('|');

  const denominator = recipe.produces === 'ratio'
    && Object.values(inputs).find((fact) => Number(fact.value) === 0);
  if (denominator) {
    return { ...base, value: null, verdict: VERDICT.UNSUPPORTED, reason: 'the denominator is zero' };
  }

  const computed = derive({ concept: base.concept, definition_id, formula: recipe.formula, inputs });
  if (computed.verdict === VERDICT.UNSUPPORTED) return { ...base, ...computed };

  const stated = (facts || []).find((fact) => matches(fact, { ...at, definition_id })
    && fact.verdict === 'stated');
  const tolerance = propagatedSlack({ produces: recipe.produces, value: computed.value, inputs });

  return {
    ...base,
    // A derived fact is its value together with its lineage, so its identity
    // has to include the value. Without it, a figure recomputed from a
    // restated input two levels down keeps the key it had and the restatement
    // goes unnoticed exactly where it matters most.
    id: `${factKey({ ...base, concept: base.concept })}#${computed.value}`,
    value: computed.value,
    verdict: VERDICT.DERIVED,
    formula: recipe.expression,
    input_fact_ids: computed.input_fact_ids,
    currency: recipe.produces === 'ratio' ? null : currency || null,
    unit: recipe.produces === 'ratio' ? 1 : Number(unit) || null,
    measurement_basis: DEFINITIONS.get(definition_id)?.measurement || null,
    tolerance,
    // A stated counterpart is reported beside the computed figure, never
    // instead of it. Which one is right is not this module's question.
    also_stated: stated ? {
      value: Number(stated.value),
      difference: round(computed.value - Number(stated.value), 9),
      within_rounding: Math.abs(computed.value - Number(stated.value)) <= tolerance + halfUlp(stated),
    } : null,
    reason: null,
  };
}

/** Everything the facts support, with a reason for everything they don't. */
export function calculateAll(facts, where) {
  const derived = [];
  const unsupported = [];
  for (const definition_id of RECIPES.keys()) {
    const result = calculate(facts, { ...where, definition_id });
    (result.verdict === VERDICT.DERIVED ? derived : unsupported).push(result);
  }
  return { derived, unsupported };
}

/**
 * Whether a computed figure still follows from the facts.
 *
 * Checked by re-resolving the recipe's inputs rather than by trusting what was
 * stored, so a restatement that produced a new fact - a new document, a new
 * key - shows up as a changed input even though the old fact is still there.
 */
export function isStale(computed, facts) {
  const recipe = RECIPES.get(computed?.definition_id);
  if (!recipe) return { stale: true, reasons: [`no recipe for ${computed?.definition_id}`] };
  const at = {
    period_end: computed.period_end,
    accounting_scope: computed.accounting_scope || 'consolidated',
    segment: computed.segment || null,
  };
  const reasons = [];
  for (const [name, definition_id] of Object.entries(recipe.inputs)) {
    const was = computed.input_fact_ids?.[name];
    const resolved = resolveInput(facts, { ...at, definition_id });
    let now = resolved.fact ? (resolved.fact.id || factKey(resolved.fact)) : null;
    if (!resolved.fact && RECIPES.has(definition_id)) {
      const nested = calculate(facts, { ...at, definition_id });
      if (nested.verdict === VERDICT.DERIVED) now = nested.id;
    }
    if (!now) { reasons.push(`${name} (${definition_id}) ${resolved.reason}`); continue; }
    if (was && was !== now) reasons.push(`${name} now resolves to a different fact`);
  }
  return { stale: reasons.length > 0, reasons };
}

/** Where a figure came from, all the way down to what the filing states. */
export function lineage(computed, facts, seen = new Set()) {
  const recipe = RECIPES.get(computed?.definition_id);
  const node = {
    definition_id: computed?.definition_id,
    value: computed?.value ?? null,
    verdict: computed?.verdict,
  };
  if (!recipe || seen.has(computed.definition_id)) return node;
  const deeper = new Set([...seen, computed.definition_id]);
  const at = {
    period_end: computed.period_end,
    accounting_scope: computed.accounting_scope || 'consolidated',
    segment: computed.segment || null,
  };
  node.formula = recipe.expression;
  node.inputs = {};
  for (const [name, definition_id] of Object.entries(recipe.inputs)) {
    const resolved = resolveInput(facts, { ...at, definition_id });
    if (resolved.fact) {
      node.inputs[name] = {
        definition_id,
        value: Number(resolved.fact.value),
        verdict: resolved.fact.verdict || VERDICT.STATED,
        as_reported_label: resolved.fact.as_reported_label ?? null,
        source_sentence: resolved.fact.source_sentence ?? null,
      };
      continue;
    }
    node.inputs[name] = RECIPES.has(definition_id)
      ? lineage(calculate(facts, { ...at, definition_id }, deeper), facts, deeper)
      : { definition_id, value: null, verdict: VERDICT.UNSUPPORTED, reason: resolved.reason };
  }
  return node;
}
