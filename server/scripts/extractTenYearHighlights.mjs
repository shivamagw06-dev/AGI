#!/usr/bin/env node
/**
 * A ten-year highlights table, as facts that cite the row they came from.
 *
 *   node scripts/extractTenYearHighlights.mjs --pdf "RIL_IAR 2026.pdf" --company RELIANCE
 *   node scripts/extractTenYearHighlights.mjs --pdf "..." --company RELIANCE --apply
 *
 * Dry run is the default. It writes nothing and prints every fact it would
 * write with the row it reads it from, because thirty-five figures entering a
 * store deserve to be read first.
 *
 * The point of doing it this way rather than transcribing the numbers: a
 * ten-year row flattens to one line, so a citation proves only that a figure
 * is somewhere in it. 7,88,743 is in Reliance's revenue row whichever year it
 * is claimed for. The column alignment in tableColumns is what makes the year
 * a reading. A row whose cell count does not match the header is refused
 * rather than aligned approximately, because an off-by-one puts every figure
 * under the wrong year and the result looks entirely reasonable.
 *
 * Every fact then goes through readFacts, which requires the value to appear
 * in the cited row and the row to appear in the document. Nothing is written
 * that has not survived both.
 */
import fs from 'fs';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { readFacts } from '../services/factExtraction.js';
import { saveFacts } from '../services/factStore.js';
import { alignRow, cellEndingIn, splitRows } from '../services/tableColumns.js';

const args = process.argv.slice(2);
const flag = (name, fallback = null) => {
  const at = args.indexOf(name);
  return at === -1 || at === args.length - 1 ? fallback : args[at + 1];
};
const apply = args.includes('--apply');
const pdfPath = flag('--pdf');
const company = flag('--company');
const years = (flag('--years', '2022,2023,2024,2025,2026')).split(',').map(Number);

if (!pdfPath || !company) {
  console.error('--pdf and --company are required.');
  process.exit(1);
}

/**
 * Reliance's labels for the rows this understands.
 *
 * The footnotes are the reason two of these are not the obvious definition.
 * The EBITDA row is marked "# Before exceptional items", and Reliance reports
 * a 2,836 crore exceptional gain in FY 2021-22, so that row is not EBITDA as
 * reported for every year in it. The dividend row is marked "on actual payment
 * basis", which is cash paid and not the amount declared.
 */
const ROWS = [
  { label: 'Value of Sales and Services (Revenue)', definition_id: 'REVENUE.VALUE_OF_SALES_AND_SERVICES', measurement_basis: 'statutory' },
  { label: 'Total Income', definition_id: 'REVENUE.TOTAL_INCOME', measurement_basis: 'statutory' },
  { label: 'Earnings Before Depreciation, Finance Cost and Tax Expenses (EBITDA)', definition_id: 'EBITDA.BEFORE_EXCEPTIONAL', measurement_basis: 'management_adjusted' },
  { label: 'Depreciation and Amortisation', definition_id: 'DEPRECIATION.AMORTISATION_AND_DEPLETION', measurement_basis: 'accrual' },
  { label: 'Profit for the Year', definition_id: 'NET_INCOME.BEFORE_NCI', measurement_basis: 'statutory' },
  { label: 'Dividend Payout', definition_id: 'DIVIDENDS.PAID_CASH', measurement_basis: 'cash' },
  { label: 'Net Worth', definition_id: 'EQUITY.TOTAL', measurement_basis: 'statutory' },
];
const CONCEPTS = {
  'REVENUE.VALUE_OF_SALES_AND_SERVICES': 'revenue', 'REVENUE.TOTAL_INCOME': 'revenue',
  'EBITDA.BEFORE_EXCEPTIONAL': 'ebitda', 'DEPRECIATION.AMORTISATION_AND_DEPLETION': 'depreciation',
  'NET_INCOME.BEFORE_NCI': 'net_income', 'DIVIDENDS.PAID_CASH': 'dividends', 'EQUITY.TOTAL': 'equity',
};

const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
const doc = await pdfjs.getDocument({ data: new Uint8Array(fs.readFileSync(pdfPath)), useSystemFonts: true }).promise;
const pages = [];
for (let page = 1; page <= doc.numPages; page += 1) {
  const content = await (await doc.getPage(page)).getTextContent();
  pages.push(content.items.map((item) => item.str).join(' '));
}
const document = pages.join('\n');

const at = pages.findIndex((page) => page.includes('10-Year Financial Highlights'));
if (at === -1) { console.error('no 10-Year Financial Highlights table in this document'); process.exit(1); }
const page = pages[at].replace(/\s+/g, ' ');
const sourcePage = at + 1;

const headerStart = page.indexOf('US$ Million');
const header = page.slice(headerStart, page.indexOf('FY 2016-17', headerStart) + 'FY 2016-17'.length);

// The table is split into every row it contains, not just the ones wanted.
// Slicing from one wanted label to the next skips the rows in between and
// takes their figures: a slice from "Depreciation and Amortisation" to "Profit
// for the Year" contains the exceptional items row, and eleven of its cells
// align against eleven columns without complaint.
const region = page.slice(page.indexOf('FY 2016-17', headerStart) + 'FY 2016-17'.length,
  page.indexOf('Key Indicators') >= 0 ? page.indexOf('Key Indicators') : undefined);
const found = splitRows(region);

const candidates = [];
const refusedRows = [];
const missing = [];
for (const row of ROWS) {
  const match = found.find((one) => one.label.startsWith(row.label));
  if (!match) { missing.push(row); continue; }
  const aligned = alignRow(header, match.text);
  if (aligned.problem) { refusedRows.push({ label: row.label, problem: aligned.problem }); continue; }
  for (const year of years) {
    const cell = cellEndingIn(aligned, year);
    if (!cell || cell.value === null) continue;
    candidates.push({
      concept: CONCEPTS[row.definition_id],
      definition_id: row.definition_id,
      measurement_basis: row.measurement_basis,
      value: cell.value,
      period_end: `${year}-03-31`,
      period_type: 'annual',
      accounting_scope: 'consolidated',
      entity_scope: 'group',
      currency: 'INR',
      unit: 10000000,
      as_reported_label: aligned.label,
      source_section: '10-Year Financial Highlights (Consolidated)',
      source_page: sourcePage,
      source_sentence: match.text,
    });
  }
}

const { facts, rejected } = readFacts({
  payload: { facts: candidates }, document, company,
  reportedInDocument: flag('--document', 'RIL FY2025-26'),
});
for (const fact of facts) fact.source_page = sourcePage;

console.log(`page                  ${sourcePage}`);
console.log(`rows understood       ${ROWS.length - missing.length - refusedRows.length} of ${ROWS.length}`);
if (missing.length) for (const row of missing) console.log(`  not in this table   ${row.label}`);
if (refusedRows.length) for (const row of refusedRows) console.log(`  REFUSED             ${row.label}: ${row.problem}`);
console.log(`facts proposed        ${candidates.length}`);
console.log(`survived citation     ${facts.length}`);
if (rejected.length) {
  console.log(`rejected              ${rejected.length}`);
  for (const one of rejected.slice(0, 10)) console.log(`  ${one.reason}`);
}
console.log();
for (const year of years) {
  const mine = facts.filter((fact) => fact.period_end.startsWith(String(year)));
  console.log(`${year}-03-31  ${mine.length} facts`);
  for (const fact of mine) console.log(`   ${String(fact.value).padStart(10)}  ${fact.definition_id}`);
}

if (!apply) { console.log('\nDry run. Nothing written. Re-run with --apply to write.'); process.exit(0); }

const client = createSupabaseAdmin();
if (!client) { console.error('SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.'); process.exit(1); }
const { written, refused, error } = await saveFacts(client, facts);
console.log(`\nwritten  ${written}`);
if (refused.length) for (const one of refused) console.log(`  refused ${one.fact.definition_id}: ${one.problems.join(', ')}`);
if (error) { console.error('write failed:', error.message); process.exit(1); }
