/**
 * company_financials, as facts.
 *
 * The old store held one column per line item, which is why it has to be
 * migrated rather than read: a column called `capex` cannot hold Reliance's
 * 1,44,271 and 1,22,916 at once, and whichever was entered, nothing recorded
 * which one it was. Twelve of its twenty-six columns name exactly one
 * definition in the register. Ten name two or three, and for those the answer
 * to "which" is not in the row, not in the importer, and not in any column -
 * the import validated scale and currency and period type strictly, and said
 * nothing about definitions.
 *
 * Dropping those ten would lose the figures the questions want most: 38 of the
 * 51 computed questions need at least one of them, and revenue, EBITDA, capex
 * and EBIT are the four most asked for. Importing them as though the
 * definition were known would be worse, because then the uncertainty is
 * invisible and reconciliation would rank an unknown figure against a known
 * one as if they were comparable.
 *
 * So they come in under the unrecorded markers, which are visible, queryable,
 * and refused by any purpose that depends on knowing the basis.
 */
import { DEFINITIONS, ENTITY_SCOPE, MEASUREMENT, PERIOD_TYPE } from './factOntology.js';

/**
 * Which definition each column becomes.
 *
 * A column mapped to an `.UNRECORDED` marker is one the old schema could not
 * distinguish. The comment on each says what was lost.
 */
export const COLUMN_DEFINITIONS = new Map([
  // Unambiguous: one column, one definition.
  ['cost_of_sales', 'COST_OF_SALES.STATEMENT'],
  ['gross_profit', 'GROSS_PROFIT.STATEMENT'],
  ['operating_expense', 'OPERATING_EXPENSE.STATEMENT'],
  ['depreciation', 'DEPRECIATION.AMORTISATION_AND_DEPLETION'],
  ['interest_expense', 'INTEREST_EXPENSE.FINANCE_COST'],
  ['pre_tax_income', 'PRE_TAX_INCOME.STATEMENT'],
  ['share_based_comp', 'SHARE_BASED_COMP.EXPENSE'],
  ['receivables', 'RECEIVABLES.TRADE'],
  ['inventories', 'INVENTORIES.TOTAL'],
  ['payables', 'PAYABLES.TRADE'],
  ['total_equity', 'EQUITY.TOTAL'],
  ['operating_cash_flow', 'CFO.STATEMENT'],
  ['acquisitions', 'ACQUISITIONS.CASH_PAID'],
  ['buybacks', 'BUYBACKS.CASH_PAID'],
  ['shares_issued', 'SHARES_ISSUED.DURING_PERIOD'],

  // Ambiguous: the register has more than one, and the row does not say which.
  ['revenue', 'REVENUE.UNRECORDED'],            // gross of tax, net of tax, or including other income
  ['ebitda', 'EBITDA.UNRECORDED'],              // reported or before exceptional items
  ['ebit', 'EBIT.UNRECORDED'],                  // segment result, management's, or statutory operating profit
  ['tax_expense', 'TAX_EXPENSE.UNRECORDED'],    // total, current or deferred
  ['net_income', 'NET_INCOME.UNRECORDED'],      // before or after non-controlling interests
  ['cash', 'CASH.UNRECORDED'],                  // equivalents only, or including current investments
  ['gross_debt', 'DEBT.UNRECORDED'],            // the column is named gross, the data may not be
  ['invested_capital', 'INVESTED_CAPITAL.UNRECORDED'], // a computed figure with no formula recorded
  ['capex', 'CAPEX.UNRECORDED'],                // management's, the segment note's, or the cash flow statement's
  ['dividends', 'DIVIDENDS.UNRECORDED'],        // declared for the year, or paid in it
  ['share_count', 'SHARE_COUNT.UNRECORDED'],    // outstanding, weighted basic, or weighted diluted
]);

/** Where a migrated figure came from, which is a spreadsheet and not a filing. */
export const SOURCE = 'company_financials import';
export const SOURCE_RESTATED = 'company_financials import (restated)';

const PERIODS = new Map([
  ['annual', PERIOD_TYPE.ANNUAL],
  ['quarter', PERIOD_TYPE.QUARTER],
]);

/**
 * One row of the old store as the facts it contains.
 *
 * A blank column is not a zero and produces no fact. The document a fact is
 * reported in distinguishes restated rows from original ones, so a period that
 * exists both ways survives as two facts rather than one overwriting the other.
 */
export function factsFromRow(row, { company } = {}) {
  const problems = [];
  const period_type = PERIODS.get(String(row?.period_type || '').trim());
  if (!period_type) problems.push(`period_type ${row?.period_type}`);
  const accounting_scope = String(row?.basis || 'consolidated').trim();
  if (!['consolidated', 'standalone'].includes(accounting_scope)) problems.push(`basis ${row?.basis}`);
  const unit = Number(row?.scale);
  if (!(unit > 0)) problems.push(`scale ${row?.scale}`);
  const named = company || row?.ticker;
  if (!named) problems.push('no ticker');
  if (!row?.period_end) problems.push('no period_end');
  if (!row?.currency) problems.push('no currency');
  if (problems.length) return { facts: [], problems };

  const facts = [];
  for (const [column, definition_id] of COLUMN_DEFINITIONS) {
    const value = row[column];
    // Blank means the period did not report it, which is not zero.
    if (value === null || value === undefined || value === '') continue;
    if (!Number.isFinite(Number(value))) { problems.push(`${column} is not a number`); continue; }
    const definition = DEFINITIONS.get(definition_id);
    const dimensionless = definition.measurement === MEASUREMENT.COUNT;
    facts.push({
      company: named,
      period_end: row.period_end,
      period_type,
      accounting_scope,
      entity_scope: ENTITY_SCOPE.GROUP,
      concept: definition.concept,
      definition_id,
      measurement_basis: definition.measurement,
      segment: null,
      geography: null,
      dimensions: {},
      // A count carries no currency, whatever the row said the money was.
      currency: dimensionless ? null : row.currency,
      unit,
      reported_in_document: row.restated ? SOURCE_RESTATED : SOURCE,
      original_or_restated: row.restated ? 'restated' : 'original',
      value: Number(value),
      verdict: 'stated',
      // The issuer's own words are not available; the column name is the most
      // honest label there is for a figure that arrived in a spreadsheet.
      as_reported_label: column,
      source_document_id: row.id ?? null,
      source_section: null,
      source_page: null,
      source_sentence: null,
      confidence: null,
    });
  }
  return { facts, problems };
}

/** What a migration of these rows would produce, without writing anything. */
export function summarise(rows, { company } = {}) {
  let facts = 0;
  let unrecorded = 0;
  const problems = [];
  const byDefinition = new Map();
  for (const [at, row] of (rows || []).entries()) {
    const read = factsFromRow(row, { company });
    for (const problem of read.problems) problems.push(`row ${at + 1}: ${problem}`);
    for (const fact of read.facts) {
      facts += 1;
      if (DEFINITIONS.get(fact.definition_id)?.unrecorded) unrecorded += 1;
      byDefinition.set(fact.definition_id, (byDefinition.get(fact.definition_id) || 0) + 1);
    }
  }
  return {
    rows: (rows || []).length,
    facts,
    unrecorded,
    // The proportion that arrives without a definition is the number worth
    // reading before any of this is written.
    unrecorded_share: facts === 0 ? null : Number((unrecorded / facts).toFixed(4)),
    by_definition: [...byDefinition].sort((a, b) => b[1] - a[1]),
    problems,
  };
}
