/**
 * Looking for a fact in the document before saying the document does not have
 * it.
 *
 * The failure this exists to fix: a question needs operating cash flow, the
 * store has none, and the answer comes back "operating_cash_flow not
 * reported". Reliance's consolidated cash flow statement reports 1,92,113
 * crore of it. The store was being read as the truth about what the filing
 * discloses when it is only a record of what has been extracted so far, and
 * the difference between those two is most of the unanswered questions.
 *
 * So a missing input is a reason to search, not a reason to stop. What makes
 * that safe rather than reckless is where it searches. Reliance states
 * operating cash flow twice under the same words - 79,059 crore on page 61 and
 * 1,92,113 on page 103 - because one is the company and the other is the
 * group. A search for the label alone finds the standalone figure first and
 * writes a number less than half the right size whose citation checks out
 * perfectly. Scope is therefore part of the search rather than a property
 * noticed afterwards, and a page's own column header supplies the year rather
 * than the convention that current comes first.
 *
 * Nothing here writes anything. It proposes candidates, which go through
 * readFacts like any other reading: the value must appear in the line cited
 * and the line must appear in the document.
 */
import { DEFINITIONS } from './factOntology.js';
import { mapSections } from './documentSections.js';
import { splitRows } from './tableColumns.js';

/**
 * Where each definition is found and what it is called.
 *
 * Patterns, not per-question rules. "Net cash flow from operating activities"
 * is how Ind AS says it and "net cash provided by operating activities" is how
 * US GAAP does; both name the same definition, and neither is specific to a
 * company. A register of labels is the same normalisation the ontology already
 * does for definitions, one layer earlier.
 */
export const TARGETS = new Map([
  ['CFO.STATEMENT', {
    kind: 'statements',
    statement: /Cash Flow/i,
    patterns: [
      /net\s+cash\s+(?:flow\s+from|generated\s+from|provided\s+by|from)\s+operating\s+activities/i,
      /cash\s+(?:flow|flows)\s+from\s+operating\s+activities/i,
    ],
  }],
  ['CAPEX.CASH_PPE_INTANGIBLES', {
    kind: 'statements',
    statement: /Cash Flow/i,
    patterns: [
      /expenditure\s+for\s+property,?\s+plant\s+and\s+equipment/i,
      /purchase\s+of\s+property,?\s+plant\s+and\s+equipment/i,
      /payments?\s+(?:to\s+acquire|for)\s+property,?\s+plant\s+and\s+equipment/i,
    ],
  }],
  // A label can name two different things in two different statements. "Trade
  // Receivables" on the balance sheet is a balance; in the cash flow statement
  // it is the change in that balance, and Reliance's are 58,491 and (28,196).
  // Naming the statement is what keeps them apart.
  ['INVENTORIES.TOTAL', { kind: 'statements', statement: /Balance Sheet/i, patterns: [/\bInventories\b/] }],
  ['RECEIVABLES.TRADE', { kind: 'statements', statement: /Balance Sheet/i, patterns: [/\bTrade Receivables\b/] }],
  ['PAYABLES.TRADE', { kind: 'statements', statement: /Balance Sheet/i, patterns: [/\bTrade Payables\b/] }],
  ['EQUITY.TOTAL', { kind: 'statements', statement: /Balance Sheet/i, patterns: [/\bTotal Equity\b/] }],
  ['DEPRECIATION.AMORTISATION_AND_DEPLETION', {
    kind: 'statements',
    statement: /Statement of Profit and Loss/i,
    patterns: [/depreciation\s*[/,]?\s*amorti[sz]ation\s+and\s+depletion\s+expense/i],
  }],
  ['INTEREST_EXPENSE.FINANCE_COST', { kind: 'statements', statement: /Statement of Profit and Loss/i, patterns: [/\bFinance Costs?\b/] }],
  ['PRE_TAX_INCOME.STATEMENT', { kind: 'statements', statement: /Statement of Profit and Loss/i, patterns: [/Profit Before Tax\b/i] }],
]);

/** How far past a label a row's own figures can reasonably run. */
const ROW = 260;

/** A note reference is a small whole number, not an amount. */
const isNoteReference = (value) => Number.isInteger(value) && value > 0 && value < 200;

/**
 * The year figures in a row, or nothing if the row cannot be read as one.
 *
 * A balance sheet row may lead with a note reference - "Trade Receivables 9
 * 58,491 42,121" - and the row below it may not: "Total Equity 10,85,866
 * 10,09,626" carries none. Requiring every row on the page to have one refused
 * the totals, and then a row on another page matched the label instead and
 * wrote a figure from somewhere else entirely.
 *
 * So a row holds the figures at its end, optionally preceded by one note
 * reference, and the leading cell has to look like a reference rather than
 * like money before it is discarded as one.
 */
export function figuresOf(row, years) {
  if (!row || !years) return null;
  const { cells } = row;
  if (cells.length === years) return cells;
  if (cells.length === years + 1 && isNoteReference(cells[0])) return cells.slice(1);
  return null;
}

/**
 * Candidate facts for one definition, from the pages that can hold it.
 *
 * A page whose column count does not match its declared years is skipped
 * rather than guessed at, and every candidate says which page and which line
 * it came from so the reading can be checked by hand.
 */
export function findCandidates({
  pages, definition_id, accounting_scope = 'consolidated',
  currency, unit, period_type = 'annual', month_end = '03-31',
}) {
  const target = TARGETS.get(definition_id);
  const definition = DEFINITIONS.get(definition_id);
  if (!target || !definition) return { candidates: [], looked_at: [], reason: `no retrieval target for ${definition_id}` };

  const sections = mapSections(pages);
  const eligible = sections.filter((entry) => entry.scope === accounting_scope
    && entry.kind === target.kind && entry.years.length
    && (!target.statement || target.statement.test(String(pages[entry.page - 1] ?? '').replace(/\s+/g, ' '))));

  const candidates = [];
  const lookedAt = [];
  for (const entry of eligible) {
    const page = String(pages[entry.page - 1] ?? '').replace(/\s+/g, ' ');
    for (const pattern of target.patterns) {
      const found = page.match(pattern);
      if (!found) continue;
      lookedAt.push({ page: entry.page, matched: found[0].trim() });
      const [row] = splitRows(page.slice(found.index, found.index + ROW));
      const figures = figuresOf(row, entry.years.length);
      if (!figures) continue;
      for (const [at, year] of entry.years.entries()) {
        const value = figures[at];
        if (value === null || value === undefined) continue;
        candidates.push({
          concept: definition.concept,
          definition_id,
          measurement_basis: definition.measurement,
          // A statement writes an outflow in brackets. The store holds the
          // magnitude, as the importer does, so a capex of 1,22,916 is 1,22,916
          // whichever side of the cash flow statement it sits on.
          value: Math.abs(value),
          period_end: `${year}-${month_end}`,
          period_type,
          accounting_scope,
          entity_scope: 'group',
          currency,
          unit,
          as_reported_label: row.label,
          source_section: `${accounting_scope} ${target.kind}`,
          source_page: entry.page,
          source_sentence: row.text,
        });
      }
      break;
    }
  }
  return { candidates, looked_at: lookedAt, reason: candidates.length ? null : 'no line matched in the pages searched' };
}

/** Everything a set of definitions can be found for, in one pass. */
export function recover({ pages, definition_ids, ...rest }) {
  const found = [];
  const missed = [];
  for (const definition_id of definition_ids || []) {
    const result = findCandidates({ pages, definition_id, ...rest });
    if (result.candidates.length) found.push(...result.candidates);
    else missed.push({ definition_id, reason: result.reason, looked_at: result.looked_at.length });
  }
  return { candidates: found, missed };
}
