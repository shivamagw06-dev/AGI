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
  // A share count is not an amount of money and not a quotient. It is measured
  // by counting, and the distinction matters because a count has no currency.
  COUNT: 'count',
  // The source did not say. Used only where a figure arrived from somewhere
  // that held one column for several definitions measured differently: capital
  // expenditure, EBIT and dividends each span cash and accrual, so for those
  // the basis is genuinely unknown rather than merely unstated. No purpose
  // admits it, which is the point - such a figure stays visible and cannot be
  // selected for work that depends on knowing how it was measured.
  UNRECORDED: 'unrecorded',
});

/**
 * Bases whose figures carry no currency.
 *
 * A quotient and a count are both numbers without money attached, and storing
 * a currency against either would let it be summed or converted with figures
 * that are amounts. Everything else must say which money it is in, because
 * there a missing currency is a bug rather than a property of the figure.
 */
export const DIMENSIONLESS = Object.freeze(new Set([MEASUREMENT.DERIVED_RATIO, MEASUREMENT.COUNT]));

/**
 * How long a period runs.
 *
 * This register is the one the company_facts check constraint enforces, and
 * company_financials already holds data under 'annual' and 'quarter'. It is
 * written down here because the alternative happened: four spellings of the
 * same three periods - annual, quarter, quarterly, yearly - accumulated across
 * this codebase in a week, which is the failure the definition register exists
 * to prevent, in the field that says when.
 */
export const PERIOD_TYPE = Object.freeze({
  ANNUAL: 'annual',
  HALF: 'half',
  QUARTER: 'quarter',
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
/**
 * What a definition is a definition *of*.
 *
 * Two definitions under one concept are not always two attempts at one number.
 * All three capital expenditure definitions compete to be "capital
 * expenditure", and their disagreement says something about accruals and
 * timing. Gross debt and net debt do not compete: the issuer names them as two
 * quantities and the 200% between them is the cash balance, which is arithmetic
 * rather than a finding.
 *
 * `measures` is the test - do these compete to be the same named quantity, or
 * does the issuer present them as different ones. Anything comparing figures
 * for disagreement has to compare within it, or it reports every filing that
 * discloses both gross and net anything.
 */
export const DEFINITIONS = new Map([
  ['CAPEX.MANAGEMENT', { concept: 'capex', measurement: MEASUREMENT.ACCRUAL, measures: 'capital_expenditure', label: 'Capital expenditure as management reports it' }],
  ['CAPEX.SEGMENT', { concept: 'capex', measurement: MEASUREMENT.SEGMENT_REPORTING, measures: 'capital_expenditure', label: 'Capital expenditure from the segment note' }],
  ['CAPEX.CASH_PPE_INTANGIBLES', { concept: 'capex', measurement: MEASUREMENT.CASH, measures: 'capital_expenditure', label: 'Cash paid for PPE, spectrum and intangibles' }],
  ['REVENUE.VALUE_OF_SALES_AND_SERVICES', { concept: 'revenue', measurement: MEASUREMENT.STATUTORY, measures: 'gross_sales', label: 'Value of sales and services, gross' }],
  ['REVENUE.OPERATIONS_NET', { concept: 'revenue', measurement: MEASUREMENT.STATUTORY, measures: 'net_sales', label: 'Revenue from operations, net of indirect taxes' }],
  ['REVENUE.TOTAL_INCOME', { concept: 'revenue', measurement: MEASUREMENT.STATUTORY, measures: 'total_income', label: 'Total income' }],
  ['EBITDA.REPORTED', { concept: 'ebitda', measurement: MEASUREMENT.MANAGEMENT_ADJUSTED, measures: 'ebitda', label: 'EBITDA as management reports it' }],
  ['EBITDA.BEFORE_EXCEPTIONAL', { concept: 'ebitda', measurement: MEASUREMENT.MANAGEMENT_ADJUSTED, measures: 'ebitda_before_exceptional', label: 'EBITDA before exceptional items' }],
  ['DEBT.GROSS', { concept: 'debt', measurement: MEASUREMENT.STATUTORY, measures: 'gross_debt', label: 'Gross debt' }],
  ['DEBT.NET', { concept: 'debt', measurement: MEASUREMENT.STATUTORY, measures: 'net_debt', label: 'Net debt, as the issuer defines it' }],
  ['CFO.STATEMENT', { concept: 'cfo', measurement: MEASUREMENT.CASH, measures: 'operating_cash_flow', label: 'Net cash flow from operating activities' }],
  ['FCF.CFO_MINUS_MANAGEMENT_CAPEX', { concept: 'fcf', measurement: MEASUREMENT.CASH, measures: 'free_cash_flow', label: 'Operating cash flow less management capex' }],
  ['FCF.CFO_MINUS_CASH_CAPEX', { concept: 'fcf', measurement: MEASUREMENT.CASH, measures: 'free_cash_flow', label: 'Operating cash flow less cash capex' }],

  // ── the income statement ──────────────────────────────────────────
  // Q39 asks whether adjusted EBITDA is materially higher than statutory
  // operating profit, so those are two quantities and not two names.
  ['EBIT.SEGMENT_RESULT', { concept: 'ebit', measurement: MEASUREMENT.SEGMENT_REPORTING, measures: 'ebit', label: 'Segment result before interest and taxes' }],
  ['EBIT.REPORTED', { concept: 'ebit', measurement: MEASUREMENT.MANAGEMENT_ADJUSTED, measures: 'ebit', label: 'EBIT as management reports it' }],
  ['EBIT.STATUTORY_OPERATING_PROFIT', { concept: 'ebit', measurement: MEASUREMENT.STATUTORY, measures: 'statutory_operating_profit', label: 'Operating profit as the statutory accounts present it' }],
  ['COST_OF_SALES.STATEMENT', { concept: 'cost_of_sales', measurement: MEASUREMENT.STATUTORY, measures: 'cost_of_sales', label: 'Cost of materials and goods sold' }],
  ['DEPRECIATION.AMORTISATION_AND_DEPLETION', { concept: 'depreciation', measurement: MEASUREMENT.ACCRUAL, measures: 'depreciation_and_amortisation', label: 'Depreciation, amortisation and depletion expense' }],
  ['INTEREST_EXPENSE.FINANCE_COST', { concept: 'interest_expense', measurement: MEASUREMENT.ACCRUAL, measures: 'finance_cost', label: 'Finance cost' }],
  ['SHARE_BASED_COMP.EXPENSE', { concept: 'share_based_comp', measurement: MEASUREMENT.ACCRUAL, measures: 'share_based_compensation', label: 'Share-based compensation expense' }],
  ['PRE_TAX_INCOME.STATEMENT', { concept: 'pre_tax_income', measurement: MEASUREMENT.STATUTORY, measures: 'profit_before_tax', label: 'Profit before tax' }],
  // Current and deferred are components, not competing readings of the total.
  ['TAX_EXPENSE.TOTAL', { concept: 'tax_expense', measurement: MEASUREMENT.ACCRUAL, measures: 'tax_expense', label: 'Total tax expense' }],
  ['TAX_EXPENSE.CURRENT', { concept: 'tax_expense', measurement: MEASUREMENT.ACCRUAL, measures: 'current_tax', label: 'Current tax' }],
  ['TAX_EXPENSE.DEFERRED', { concept: 'tax_expense', measurement: MEASUREMENT.ACCRUAL, measures: 'deferred_tax', label: 'Deferred tax' }],
  // Before and after non-controlling interests are different quantities, and
  // Reliance discloses both: 95,610 before, 80,775 after.
  ['NET_INCOME.BEFORE_NCI', { concept: 'net_income', measurement: MEASUREMENT.STATUTORY, measures: 'net_income_before_nci', label: 'Profit after tax, before adjustment for non-controlling interests' }],
  ['NET_INCOME.ATTRIBUTABLE_TO_OWNERS', { concept: 'net_income', measurement: MEASUREMENT.STATUTORY, measures: 'net_income_attributable', label: 'Profit after tax attributable to owners of the company' }],

  // ── the balance sheet ─────────────────────────────────────────────
  ['GROSS_PROFIT.STATEMENT', { concept: 'gross_profit', measurement: MEASUREMENT.STATUTORY, measures: 'gross_profit', label: 'Gross profit' }],
  ['OPERATING_EXPENSE.STATEMENT', { concept: 'operating_expense', measurement: MEASUREMENT.STATUTORY, measures: 'operating_expense', label: 'Operating expenses' }],
  ['ACQUISITIONS.CASH_PAID', { concept: 'acquisitions', measurement: MEASUREMENT.CASH, measures: 'acquisitions', label: 'Cash paid to acquire businesses' }],
  ['RECEIVABLES.TRADE', { concept: 'receivables', measurement: MEASUREMENT.STATUTORY, measures: 'trade_receivables', label: 'Trade receivables' }],
  ['INVENTORIES.TOTAL', { concept: 'inventories', measurement: MEASUREMENT.STATUTORY, measures: 'inventories', label: 'Inventories' }],
  ['PAYABLES.TRADE', { concept: 'payables', measurement: MEASUREMENT.STATUTORY, measures: 'trade_payables', label: 'Trade payables' }],
  // Which cash an issuer nets against debt is the whole of the disagreement
  // about net debt, so the two are never one definition.
  ['CASH.AND_EQUIVALENTS', { concept: 'cash', measurement: MEASUREMENT.STATUTORY, measures: 'cash_and_equivalents', label: 'Cash and cash equivalents' }],
  ['CASH.AND_INVESTMENTS', { concept: 'cash', measurement: MEASUREMENT.STATUTORY, measures: 'cash_and_investments', label: 'Cash, equivalents and current investments' }],
  ['EQUITY.TOTAL', { concept: 'equity', measurement: MEASUREMENT.STATUTORY, measures: 'total_equity', label: 'Total equity' }],

  // ── what went back to shareholders ────────────────────────────────
  // Declared for the year and paid in the year are different quantities; the
  // gap is timing, and a question about capital returned means the cash.
  ['DIVIDENDS.DECLARED', { concept: 'dividends', measurement: MEASUREMENT.ACCRUAL, measures: 'dividends_declared', label: 'Dividends declared for the year' }],
  ['DIVIDENDS.PAID_CASH', { concept: 'dividends', measurement: MEASUREMENT.CASH, measures: 'dividends_paid', label: 'Dividends paid, per the cash flow statement' }],
  ['BUYBACKS.CASH_PAID', { concept: 'buybacks', measurement: MEASUREMENT.CASH, measures: 'buybacks', label: 'Cash paid to repurchase shares' }],

  // ── counts, which carry no currency ───────────────────────────────
  ['SHARE_COUNT.OUTSTANDING', { concept: 'share_count', measurement: MEASUREMENT.COUNT, measures: 'shares_outstanding', label: 'Shares outstanding at the period end' }],
  ['SHARE_COUNT.WEIGHTED_AVERAGE_BASIC', { concept: 'share_count', measurement: MEASUREMENT.COUNT, measures: 'weighted_average_basic_shares', label: 'Weighted average shares, basic' }],
  ['SHARE_COUNT.WEIGHTED_AVERAGE_DILUTED', { concept: 'share_count', measurement: MEASUREMENT.COUNT, measures: 'weighted_average_diluted_shares', label: 'Weighted average shares, diluted' }],
  ['SHARES_ISSUED.DURING_PERIOD', { concept: 'shares_issued', measurement: MEASUREMENT.COUNT, measures: 'shares_issued', label: 'Shares issued during the period' }],
  // Ratios name their denominator, because that is the whole disagreement.
  // Reliance's Retail business states an 8.2% EBITDA margin and a footnote
  // saying it is calculated on Revenue from Operations - the same EBITDA over
  // Value of Sales and Services is a different number and an equally real one.
  ['EBITDA_MARGIN.ON_REVENUE_OPERATIONS_NET', { concept: 'ebitda_margin', measurement: MEASUREMENT.DERIVED_RATIO, measures: 'ebitda_margin', label: 'EBITDA over revenue from operations, net of indirect taxes' }],
  ['EBITDA_MARGIN.ON_VALUE_OF_SALES_AND_SERVICES', { concept: 'ebitda_margin', measurement: MEASUREMENT.DERIVED_RATIO, measures: 'ebitda_margin', label: 'EBITDA over value of sales and services, gross' }],
  ['LEVERAGE.NET_DEBT_TO_EBITDA', { concept: 'leverage', measurement: MEASUREMENT.DERIVED_RATIO, measures: 'net_debt_to_ebitda', label: 'Net debt over EBITDA' }],
  ['LEVERAGE.GROSS_DEBT_TO_EBITDA', { concept: 'leverage', measurement: MEASUREMENT.DERIVED_RATIO, measures: 'gross_debt_to_ebitda', label: 'Gross debt over EBITDA' }],
  ['FCF_MARGIN.CASH_CAPEX_ON_REVENUE_OPERATIONS_NET', { concept: 'fcf_margin', measurement: MEASUREMENT.DERIVED_RATIO, measures: 'free_cash_flow_margin', label: 'Free cash flow after cash capex, over revenue from operations' }],
  ['FCF_MARGIN.MANAGEMENT_CAPEX_ON_REVENUE_OPERATIONS_NET', { concept: 'fcf_margin', measurement: MEASUREMENT.DERIVED_RATIO, measures: 'free_cash_flow_margin', label: 'Free cash flow after management capex, over revenue from operations' }],
  // ── figures whose definition the source never recorded ────────────
  //
  // company_financials held one column per line item, so a capex of 1,44,271
  // could be management's, the segment note's or the cash flow statement's,
  // and nothing recorded which. Dropping those rows loses real data; importing
  // them as though the definition were known is worse, because then the
  // uncertainty is invisible. They come in under these instead.
  //
  // Where every definition of a concept shares a basis, the basis is kept: an
  // unrecorded revenue is still a statutory figure, and only which statutory
  // figure is missing. Where the definitions are measured differently, the
  // basis is unrecorded too.
  //
  // Each has its own `measures`, so an unrecorded figure never produces a
  // spread against a known one. Two numbers cannot be said to disagree when
  // one of them might be the other under a different label.
  ['CAPEX.UNRECORDED', { concept: 'capex', measurement: MEASUREMENT.UNRECORDED, measures: 'capital_expenditure_unrecorded', unrecorded: true, label: 'Capital expenditure, definition not recorded' }],
  ['EBIT.UNRECORDED', { concept: 'ebit', measurement: MEASUREMENT.UNRECORDED, measures: 'ebit_unrecorded', unrecorded: true, label: 'EBIT, definition not recorded' }],
  ['DIVIDENDS.UNRECORDED', { concept: 'dividends', measurement: MEASUREMENT.UNRECORDED, measures: 'dividends_unrecorded', unrecorded: true, label: 'Dividends, declared or paid not recorded' }],
  ['REVENUE.UNRECORDED', { concept: 'revenue', measurement: MEASUREMENT.STATUTORY, measures: 'revenue_unrecorded', unrecorded: true, label: 'Revenue, definition not recorded' }],
  ['EBITDA.UNRECORDED', { concept: 'ebitda', measurement: MEASUREMENT.MANAGEMENT_ADJUSTED, measures: 'ebitda_unrecorded', unrecorded: true, label: 'EBITDA, definition not recorded' }],
  ['DEBT.UNRECORDED', { concept: 'debt', measurement: MEASUREMENT.STATUTORY, measures: 'debt_unrecorded', unrecorded: true, label: 'Debt, gross or net not recorded' }],
  ['CASH.UNRECORDED', { concept: 'cash', measurement: MEASUREMENT.STATUTORY, measures: 'cash_unrecorded', unrecorded: true, label: 'Cash, definition not recorded' }],
  ['NET_INCOME.UNRECORDED', { concept: 'net_income', measurement: MEASUREMENT.STATUTORY, measures: 'net_income_unrecorded', unrecorded: true, label: 'Profit after tax, before or after non-controlling interests not recorded' }],
  ['TAX_EXPENSE.UNRECORDED', { concept: 'tax_expense', measurement: MEASUREMENT.ACCRUAL, measures: 'tax_expense_unrecorded', unrecorded: true, label: 'Tax expense, definition not recorded' }],
  // Invested capital is computed, never disclosed, and company_financials
  // recorded the answer without the formula. There is no non-unrecorded
  // version of it to hold until something computes it with its inputs.
  ['INVESTED_CAPITAL.UNRECORDED', { concept: 'invested_capital', measurement: MEASUREMENT.UNRECORDED, measures: 'invested_capital_unrecorded', unrecorded: true, label: 'Invested capital, formula not recorded' }],
  ['SHARE_COUNT.UNRECORDED', { concept: 'share_count', measurement: MEASUREMENT.COUNT, measures: 'share_count_unrecorded', unrecorded: true, label: 'Share count, definition not recorded' }],
]);

/**
 * Whether the source that supplied a figure recorded which definition it is.
 *
 * Asked wherever a figure is about to be presented as an answer, because a
 * number whose definition nobody wrote down looks exactly like one whose
 * definition is known.
 */
export function isUnrecorded(definition_id) {
  return DEFINITIONS.get(definition_id)?.unrecorded === true;
}

/** What a definition claims to measure, or null if the definition is unknown. */
export function measuredQuantity(definition_id) {
  return DEFINITIONS.get(definition_id)?.measures ?? null;
}

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
