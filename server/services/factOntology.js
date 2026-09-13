/**
 * What a disclosed figure is, as distinct from what it measures.
 *
 * Reliance's annual report states capital expenditure three times: ₹1,44,271
 * crore in the management discussion, the same figure as the segment total,
 * and ₹1,22,916 crore in the cash flow statement for property, plant,
 * equipment, spectrum and intangibles. A store with one capex column picks one
 * and loses the other two, and free cash flow computed from them differs by
 * 44.6%.
 *
 * They are not a disagreement. They are three observations of one economic
 * concept under different definitions, and the schema has to hold that before
 * anything decides whether they conflict.
 *
 * So a fact is keyed by what it is - concept, definition, period, scope,
 * segment, basis - and carries provenance separately. Two disclosures using
 * different definitions are two facts, never one overwritten by the other.
 */

/** How a figure was measured, which is not the same as what it measures. */
export const MEASUREMENT = Object.freeze({
  CASH: 'cash',
  ACCRUAL: 'accrual',
  SEGMENT_REPORTING: 'segment_reporting',
  MANAGEMENT_ADJUSTED: 'management_adjusted',
  STATUTORY: 'statutory',
  // A ratio is not measured the way its inputs are. Calling Retail's 8.2%
  // EBITDA margin "accrual" would claim something about it that is not true of
  // a quotient, and would let it be compared with figures it cannot be.
  DERIVED_RATIO: 'derived_ratio',
});

/** Whose figures these are. Consolidated against standalone is not enough. */
export const ENTITY_SCOPE = Object.freeze({
  GROUP: 'group',
  COMPANY: 'company',
  SUBSIDIARY: 'subsidiary',
  SEGMENT: 'segment',
  JV: 'jv',
  ASSOCIATE: 'associate',
});

/**
 * Normalised definitions.
 *
 * Free text accumulates seventeen spellings of one definition. An id does not.
 * `label` is what this codebase calls it; the issuer's own words are kept on
 * the fact as `as_reported_label` and never discarded - "Value of Sales and
 * Services" is how Reliance says revenue, and that matters when a reader asks
 * where a number came from.
 */
export const DEFINITIONS = new Map([
  ['CAPEX.MANAGEMENT', { concept: 'capex', measurement: MEASUREMENT.ACCRUAL, label: 'Capital expenditure as management reports it' }],
  ['CAPEX.SEGMENT', { concept: 'capex', measurement: MEASUREMENT.SEGMENT_REPORTING, label: 'Capital expenditure from the segment note' }],
  ['CAPEX.CASH_PPE_INTANGIBLES', { concept: 'capex', measurement: MEASUREMENT.CASH, label: 'Cash paid for PPE, spectrum and intangibles' }],
  ['REVENUE.VALUE_OF_SALES_AND_SERVICES', { concept: 'revenue', measurement: MEASUREMENT.STATUTORY, label: 'Value of sales and services, gross' }],
  ['REVENUE.OPERATIONS_NET', { concept: 'revenue', measurement: MEASUREMENT.STATUTORY, label: 'Revenue from operations, net of indirect taxes' }],
  ['REVENUE.TOTAL_INCOME', { concept: 'revenue', measurement: MEASUREMENT.STATUTORY, label: 'Total income' }],
  ['EBITDA.REPORTED', { concept: 'ebitda', measurement: MEASUREMENT.MANAGEMENT_ADJUSTED, label: 'EBITDA as management reports it' }],
  ['EBITDA.BEFORE_EXCEPTIONAL', { concept: 'ebitda', measurement: MEASUREMENT.MANAGEMENT_ADJUSTED, label: 'EBITDA before exceptional items' }],
  ['DEBT.GROSS', { concept: 'debt', measurement: MEASUREMENT.STATUTORY, label: 'Gross debt' }],
  ['DEBT.NET', { concept: 'debt', measurement: MEASUREMENT.STATUTORY, label: 'Net debt, as the issuer defines it' }],
  ['CFO.STATEMENT', { concept: 'cfo', measurement: MEASUREMENT.CASH, label: 'Net cash flow from operating activities' }],
  ['FCF.CFO_MINUS_MANAGEMENT_CAPEX', { concept: 'fcf', measurement: MEASUREMENT.CASH, label: 'Operating cash flow less management capex' }],
  ['FCF.CFO_MINUS_CASH_CAPEX', { concept: 'fcf', measurement: MEASUREMENT.CASH, label: 'Operating cash flow less cash capex' }],
  // Ratios name their denominator, because that is the whole disagreement.
  // Reliance's Retail business states an 8.2% EBITDA margin and a footnote
  // saying it is calculated on Revenue from Operations - the same EBITDA over
  // Value of Sales and Services is a different number and an equally real one.
  ['EBITDA_MARGIN.ON_REVENUE_OPERATIONS_NET', { concept: 'ebitda_margin', measurement: MEASUREMENT.DERIVED_RATIO, label: 'EBITDA over revenue from operations, net of indirect taxes' }],
  ['EBITDA_MARGIN.ON_VALUE_OF_SALES_AND_SERVICES', { concept: 'ebitda_margin', measurement: MEASUREMENT.DERIVED_RATIO, label: 'EBITDA over value of sales and services, gross' }],
  ['LEVERAGE.NET_DEBT_TO_EBITDA', { concept: 'leverage', measurement: MEASUREMENT.DERIVED_RATIO, label: 'Net debt over EBITDA' }],
  ['LEVERAGE.GROSS_DEBT_TO_EBITDA', { concept: 'leverage', measurement: MEASUREMENT.DERIVED_RATIO, label: 'Gross debt over EBITDA' }],
  ['FCF_MARGIN.CASH_CAPEX_ON_REVENUE_OPERATIONS_NET', { concept: 'fcf_margin', measurement: MEASUREMENT.DERIVED_RATIO, label: 'Free cash flow after cash capex, over revenue from operations' }],
  ['FCF_MARGIN.MANAGEMENT_CAPEX_ON_REVENUE_OPERATIONS_NET', { concept: 'fcf_margin', measurement: MEASUREMENT.DERIVED_RATIO, label: 'Free cash flow after management capex, over revenue from operations' }],
]);

/** How strongly a figure is supported. */
export const VERDICT = Object.freeze({
  // The document states it.
  STATED: 'stated',
  // Arithmetic over stated inputs, and the inputs are named.
  DERIVED: 'derived',
  // Supported by facts but not entailed by them. "No material refinancing
  // risk" reads liquidity, maturities and a rating together and is a judgement.
  INFERRED: 'inferred',
  // Nothing supports it.
  UNSUPPORTED: 'unsupported',
});

/**
 * What makes two observations the same fact.
 *
 * Dimensions are part of the key rather than columns, so a maturity bucket or
 * a subscriber type does not require a migration. The document a figure was
 * reported in is part of it too: FY25 as first reported and FY25 restated in
 * the FY26 report are two facts, and letting one overwrite the other loses the
 * restatement.
 */
export function factKey(fact) {
  const dimensions = Object.entries(fact?.dimensions || {})
    .filter(([, value]) => value !== null && value !== undefined)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, value]) => `${name}=${value}`)
    .join(',');
  return [
    // `period_end` is what a stored fact carries; `period` is what the first
    // callers here used. Reading only one of them silently collapsed FY26 and
    // FY25 into one key, and a filing that states a figure beside its
    // prior-year comparative - which is most of them - lost the comparative.
    fact?.company, fact?.period_end ?? fact?.period, fact?.period_type || 'annual',
    fact?.accounting_scope || 'consolidated', fact?.entity_scope || ENTITY_SCOPE.GROUP,
    fact?.concept, fact?.definition_id, fact?.segment || '', fact?.geography || '',
    dimensions, fact?.reported_in_document || '',
  ].join('|');
}

/** Every observation of one concept, for one period and scope. */
export function familyOf(facts, { concept, period, period_end, accounting_scope = 'consolidated' } = {}) {
  const wanted = period_end ?? period;
  return (facts || []).filter((fact) => fact
    && fact.concept === concept
    && (fact.period_end ?? fact.period) === wanted
    && (fact.accounting_scope || 'consolidated') === accounting_scope
    && !fact.segment);
}

const round = (value, places = 4) => Number(value.toFixed(places));

/**
 * What a family of observations says, and whether they agree.
 *
 * Reports a difference against each observation it is a difference from,
 * because one absolute gap is a different proportion of each. Reliance's two
 * capex figures differ by ₹21,355 crore - 14.8% of the management figure and
 * 17.4% of the cash figure - and the free cash flows computed from them differ
 * by 44.6%, which is a statement about free cash flow and not about capex.
 */
export function reconcile(family) {
  const observations = [...(family || [])]
    .filter((fact) => Number.isFinite(Number(fact?.value)))
    .sort((a, b) => Number(b.value) - Number(a.value));
  if (observations.length < 2) {
    return { observations, status: observations.length ? 'single_observation' : 'none', differences: [] };
  }
  const differences = [];
  for (let i = 0; i < observations.length; i += 1) {
    for (let j = i + 1; j < observations.length; j += 1) {
      const a = observations[i];
      const b = observations[j];
      const gap = Number(a.value) - Number(b.value);
      differences.push({
        between: [a.definition_id, b.definition_id],
        difference: round(gap, 6),
        // Named against each side, because "17.4%" and "14.8%" are both true
        // of the same gap and mean different things.
        // Six places: a ratio rounded to four loses precision that a reader
        // comparing two of them would notice.
        as_share_of: {
          [a.definition_id]: Number(a.value) === 0 ? null : round(gap / Number(a.value), 6),
          [b.definition_id]: Number(b.value) === 0 ? null : round(gap / Number(b.value), 6),
        },
      });
    }
  }
  const agree = differences.every((entry) => entry.difference === 0);
  const sameMeasurement = new Set(observations
    .map((fact) => DEFINITIONS.get(fact.definition_id)?.measurement || 'unknown')).size === 1;
  return {
    observations,
    differences,
    // Different definitions disagreeing is not a contradiction until something
    // establishes they should have matched. Unresolved is the honest status.
    status: agree ? 'agree' : sameMeasurement ? 'conflict_same_basis' : 'different_definitions',
    reconciliation: agree ? 'identical' : 'unresolved',
  };
}

/**
 * A figure computed from other facts, carrying what produced it.
 *
 * The inputs are fact ids rather than numbers, so a restated input can
 * invalidate everything downstream of it instead of leaving a stale figure
 * that still looks computed.
 */
export function derive({ concept, definition_id, formula, inputs }) {
  const missing = Object.entries(inputs || {})
    .filter(([, fact]) => !fact || !Number.isFinite(Number(fact.value)))
    .map(([name]) => name);
  if (missing.length) {
    return { concept, definition_id, value: null, verdict: VERDICT.UNSUPPORTED,
      reason: `${missing.join(' and ')} not available`, input_fact_ids: null };
  }
  const value = formula(Object.fromEntries(
    Object.entries(inputs).map(([name, fact]) => [name, Number(fact.value)])));
  return {
    concept,
    definition_id,
    value: round(value, 6),
    verdict: VERDICT.DERIVED,
    reason: null,
    input_fact_ids: Object.fromEntries(
      Object.entries(inputs).map(([name, fact]) => [name, fact.id || factKey(fact)])),
  };
}
