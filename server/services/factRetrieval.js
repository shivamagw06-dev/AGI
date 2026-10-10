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
import { columnPlan, mapSections } from './documentSections.js';
import { alignRow, splitRows } from './tableColumns.js';

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
  ['REVENUE.OPERATIONS_NET', { kind: 'statements', statement: /Statement of Profit and Loss/i, patterns: [/\bRevenue [Ff]rom Operations\b/] }],
  ['REVENUE.TOTAL_INCOME', { kind: 'statements', statement: /Statement of Profit and Loss/i, patterns: [/\bTotal Income\b/] }],
  ['CASH.AND_EQUIVALENTS', { kind: 'statements', statement: /Balance Sheet/i, patterns: [/\bCash and Cash Equivalents\b/] }],
  // Debt is not a line on Reliance's balance sheet - borrowings are split into
  // current and non-current. It is stated whole in the capital management
  // note, "Gross Debt 3,74,421 / Net Debt 1,24,717", in a table with its own
  // column header rather than one at the top of the page. The standalone
  // company's version of the same table sits on another page with 2,31,381.
  ['DEBT.GROSS', { kind: 'statements', patterns: [/\bGross\s+Debt\b/gi] }],
  ['DEBT.NET', { kind: 'statements', patterns: [/\bNet\s+Debt\b/gi] }],
  // EBITDA is not a statutory line at all, so no statement page carries it.
  // The group figure in a table is the ten-year highlights, whose title says
  // "(Consolidated)" - scope read from the table, because the page it sits on
  // is management discussion and declares none. The row is footnoted "before
  // exceptional items", which is the definition it is taken under.
  ['EBITDA.BEFORE_EXCEPTIONAL', {
    table: /10-Year\s+Financial\s+Highlights\s*\(\s*(Consolidated|Standalone)\s*\)/i,
    patterns: [/Earnings\s+Before\s+Depreciation,?\s+Finance\s+Costs?\s+and\s+Tax\s+Expenses\s*\(EBITDA\)/i],
  }],
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
const collapse = (text) => String(text ?? '').replace(/\s+/g, ' ');
const everywhere = (pattern) => new RegExp(pattern.source, pattern.flags.includes('g') ? pattern.flags : `${pattern.flags}g`);

/** How far back from a row its own table's column header can be. */
const LOOKBACK = 700;

/**
 * The column header of the table a row sits in, when the page has none.
 *
 * A notes page is headed with the note's title, not with years, and each table
 * on it brings its own - "( ₹ in crore) As at 31st March, 2026 As at 31st
 * March, 2025" - immediately above its rows. The nearest such header before a
 * row is that row's, provided nothing between them reads as prose: a sentence
 * ending and another beginning means the header belongs to something else.
 */
export function localPlan(page, rowAt) {
  const from = Math.max(0, rowAt - LOOKBACK);
  const window = page.slice(from, rowAt);
  const marks = [...window.matchAll(/As\s+(?:at|of)\b[^,]{0,30},?\s*\d{4}|\b\d{4}\s*-\s*\d{2}(?!\d)/gi)];
  if (!marks.length) return { years: [], notes: false, cells: 0 };
  // The header is the last run of year marks, each close to the next.
  let first = marks.length - 1;
  while (first > 0 && marks[first].index - (marks[first - 1].index + marks[first - 1][0].length) < 40) first -= 1;
  const header = window.slice(Math.max(0, marks[first].index - 40), marks[marks.length - 1].index + marks[marks.length - 1][0].length);
  const between = window.slice(marks[marks.length - 1].index + marks[marks.length - 1][0].length);
  if (/[a-z]{3,}\.\s+[A-Z][a-z]/.test(between)) return { years: [], notes: false, cells: 0 };
  return columnPlan(header, { header: Infinity });
}

/**
 * A table that names its own scope in its title.
 *
 * Reliance's ten-year highlights sit on a management discussion page, which
 * declares no scope, under the title "10-Year Financial Highlights
 * (Consolidated)". The title is the only place the scope is said, so it is
 * where it is read from - and a table titled for the other scope is skipped
 * rather than taken for want of anything better.
 */
function fromTitledTable({ pages, target, definition, definition_id, accounting_scope, currency, unit, period_type, month_end }) {
  const candidates = [];
  const lookedAt = [];
  for (const [at, raw] of pages.entries()) {
    const page = collapse(raw);
    const title = page.match(target.table);
    if (!title || title[1].toLowerCase() !== accounting_scope) continue;
    const region = page.slice(title.index + title[0].length);
    const years = [...region.matchAll(/FY\s*\d{4}\s*-\s*\d{2}(?!\d)/g)];
    if (!years.length) continue;
    let last = 0;
    while (last + 1 < years.length && years[last + 1].index - (years[last].index + years[last][0].length) < 20) last += 1;
    const headerEnd = years[last].index + years[last][0].length;
    const header = region.slice(0, headerEnd);
    const row = splitRows(region.slice(headerEnd)).find((one) => target.patterns.some((pattern) => pattern.test(one.label)));
    lookedAt.push({ page: at + 1, matched: row ? row.label : null });
    if (!row) continue;
    const aligned = alignRow(header, row.text);
    if (aligned.problem) continue;
    for (const cell of aligned.cells) {
      if (cell.ends_in === null || cell.value === null) continue;
      candidates.push({
        concept: definition.concept, definition_id, measurement_basis: definition.measurement,
        value: Math.abs(cell.value), period_end: `${cell.ends_in}-${month_end}`, period_type,
        accounting_scope, entity_scope: 'group', currency, unit,
        as_reported_label: aligned.label, source_section: title[0], source_page: at + 1,
        source_sentence: row.text,
      });
    }
    break;
  }
  return { candidates, looked_at: lookedAt, reason: candidates.length ? null : 'no titled table held the line' };
}

/**
 * Candidate facts for one definition, from the pages that can hold it.
 *
 * Every occurrence of a label on a page is tried until one reads as a row,
 * not only the first: a notes page can say "gross debt" in a sentence before
 * it tabulates it, and stopping at the sentence missed the table. A row whose
 * cell count does not match its columns is skipped rather than guessed at, and
 * every candidate says which page and line it came from.
 */
export function findCandidates({
  pages, definition_id, accounting_scope = 'consolidated',
  currency, unit, period_type = 'annual', month_end = '03-31',
}) {
  const target = TARGETS.get(definition_id);
  const definition = DEFINITIONS.get(definition_id);
  if (!target || !definition) return { candidates: [], looked_at: [], reason: `no retrieval target for ${definition_id}` };
  if (target.table) {
    return fromTitledTable({ pages, target, definition, definition_id, accounting_scope, currency, unit, period_type, month_end });
  }

  const sections = mapSections(pages);
  const eligible = sections.filter((entry) => entry.scope === accounting_scope
    && entry.kind === target.kind
    && (!target.statement || target.statement.test(collapse(pages[entry.page - 1]))));

  const candidates = [];
  const lookedAt = [];
  for (const entry of eligible) {
    const page = collapse(pages[entry.page - 1]);
    let taken = false;
    for (const pattern of target.patterns) {
      for (const found of page.matchAll(everywhere(pattern))) {
        // The page's own column header if it has one; otherwise the header of
        // the table this row sits in.
        const plan = entry.years.length ? entry : localPlan(page, found.index);
        lookedAt.push({ page: entry.page, matched: found[0].trim() });
        if (!plan.years.length) continue;
        const [row] = splitRows(page.slice(found.index, found.index + ROW));
        const figures = figuresOf(row, plan.years.length);
        if (!figures) continue;
        for (const [at, year] of plan.years.entries()) {
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
        taken = true;
        break;
      }
      if (taken) break;
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
