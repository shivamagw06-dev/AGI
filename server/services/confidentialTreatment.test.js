/**
 * Withheld information tables, tested against cover pages and tables captured
 * from real SEC filings.
 *
 * The fixtures decide this one. Hand-written XML would have agreed with any
 * implementation, including the one that stored a placeholder row as a
 * position; only the real documents show that Norges Bank's Q1 2026 table
 * contains a single "NA" entry while its own cover page declares 1,507, and
 * that Berkshire's Q1 2025 carries the identical confidentiality flag over a
 * table that is complete.
 *
 *   server/tests/fixtures/sec13f/norges-confidential.primary_doc.xml
 *   server/tests/fixtures/sec13f/norges-confidential.infotable.xml
 *     Norges Bank, accession 0001374170-26-000023, report 2026-03-31,
 *     filed 2026-05-11. summaryPage: 1,507 entries, $864,690,921,985,
 *     isConfidentialOmitted true. The information table is 627 bytes.
 *     https://www.sec.gov/Archives/edgar/data/1374170/000137417026000023
 *
 *   server/tests/fixtures/sec13f/berkshire-partial-confidential.primary_doc.xml
 *     Berkshire Hathaway, accession 0000950123-25-005701, report 2025-03-31,
 *     filed 2025-05-15. summaryPage: 110 entries, $258,701,144,516,
 *     isConfidentialOmitted true - and the table really does carry 110 rows.
 *     The four positions it withheld were disclosed that August as
 *     0000950123-25-008361, "Confidential Treatment Expired".
 *     https://www.sec.gov/Archives/edgar/data/1067983/000095012325005701
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { parseSummaryPage, isPlaceholderRow, assessInformationTable } from './confidentialTreatment.js';

const FIXTURES = join(dirname(fileURLToPath(import.meta.url)), '..', 'tests', 'fixtures', 'sec13f');
const fixture = (name) => readFileSync(join(FIXTURES, name), 'utf8');

const NORGES_COVER = fixture('norges-confidential.primary_doc.xml');
const BERKSHIRE_COVER = fixture('berkshire-partial-confidential.primary_doc.xml');

const holding = (over = {}) => ({
  cusip: '037833100', issuer_name: 'APPLE INC', value_usd: 1_000_000, shares: 5_000, ...over,
});
const NORGES_PLACEHOLDER = { cusip: '000000000', issuer_name: 'NA', title_of_class: 'NA', value_usd: 0, shares: 0 };

test('the cover page declares the size of a table it does not carry', () => {
  const summary = parseSummaryPage(NORGES_COVER);
  assert.equal(summary.declaredEntries, 1507);
  assert.equal(summary.declaredValueUsd, 864690921985);
  assert.equal(summary.confidentialOmitted, true);
});

test('a filing that withheld nothing reports the flag as false, not as absent', () => {
  const summary = parseSummaryPage(fixture('berkshire-new-holdings.primary_doc.xml'));
  assert.equal(summary.confidentialOmitted, false);
  assert.equal(summary.declaredEntries, 4);
});

test('a cover page that was never fetched says nothing rather than zero', () => {
  const summary = parseSummaryPage(null);
  assert.equal(summary.declaredEntries, null);
  assert.equal(summary.declaredValueUsd, null);
  // Not false. Older filings predate the field, and reading absence as "did
  // not withhold" would let a withheld table through as complete.
  assert.equal(summary.confidentialOmitted, null);
});

test('the SEC placeholder row is recognised and a real holding is not', () => {
  assert.equal(isPlaceholderRow(NORGES_PLACEHOLDER), true);
  assert.equal(isPlaceholderRow(holding()), false);
});

test('a position at zero value keeps its identity and is not a placeholder', () => {
  // A holding written down to nothing, or reported in whole dollars that
  // rounded away, is still a disclosed position. All four marks have to agree
  // before a row is discarded.
  assert.equal(isPlaceholderRow(holding({ value_usd: 0, shares: 0 })), false);
  assert.equal(isPlaceholderRow({ cusip: '000000000', issuer_name: 'NA', value_usd: 0, shares: 12_000 }), false);
});

test("Norges Bank's withheld quarter is confidential, not short and not ingestable", () => {
  const result = assessInformationTable({
    rawRows: [NORGES_PLACEHOLDER],
    summary: parseSummaryPage(NORGES_COVER),
  });
  assert.equal(result.status, 'confidential');
  assert.equal(result.realRows.length, 0);
  assert.equal(result.placeholderCount, 1);
  // The declared size survives even though the positions do not, so the
  // quarter can say what it is holding back.
  assert.equal(result.declaredEntries, 1507);
  assert.equal(result.declaredValueUsd, 864690921985);
  assert.match(result.reason, /1,507 entries/);
});

test("Berkshire's partial withholding is a complete filing", () => {
  const summary = parseSummaryPage(BERKSHIRE_COVER);
  assert.equal(summary.confidentialOmitted, true);
  const result = assessInformationTable({
    rawRows: Array.from({ length: 110 }, (_, i) => holding({ cusip: String(i).padStart(9, '0') })),
    summary,
  });
  // Same flag as Norges Bank, opposite outcome. Rejecting on the flag would
  // have deleted a real 110-position book.
  assert.equal(result.status, 'complete');
  assert.equal(result.realRows.length, 110);
  assert.equal(result.confidentialOmitted, true);
});

test('a table far below its own declared count fails loudly when nothing was withheld', () => {
  const result = assessInformationTable({
    rawRows: [holding()],
    summary: { declaredEntries: 1507, declaredValueUsd: 1, confidentialOmitted: false },
  });
  assert.equal(result.status, 'short');
  assert.match(result.reason, /does not report withholding/);
});

test('a genuinely small book is not mistaken for a broken one', () => {
  // Alphabet held two positions in 2016 and Durable Capital three in its first
  // filing. Both agree with their own cover page, which a manager-median
  // heuristic could not have distinguished from a table that went missing.
  const result = assessInformationTable({
    rawRows: [holding(), holding({ cusip: '02079K305' })],
    summary: { declaredEntries: 2, declaredValueUsd: 5_000_000, confidentialOmitted: false },
  });
  assert.equal(result.status, 'complete');
  assert.equal(result.realRows.length, 2);
});

test('the declared count is measured against raw entries, before duplicates collapse', () => {
  // A security reported under several otherManager values is several table
  // entries and one position. tableEntryTotal counts the entries, so a filing
  // that collapses 120 entries into 80 positions is complete, not short.
  const rows = Array.from({ length: 120 }, (_, i) => holding({ cusip: String(i % 80).padStart(9, '0') }));
  const result = assessInformationTable({
    rawRows: rows,
    summary: { declaredEntries: 120, declaredValueUsd: 1, confidentialOmitted: false },
  });
  assert.equal(result.status, 'complete');
  assert.equal(result.realRows.length, 120);
});

test('an empty table with no cover page to explain it is an error, not a silent zero', () => {
  const result = assessInformationTable({ rawRows: [], summary: parseSummaryPage(null) });
  assert.equal(result.status, 'short');
});

test('a pre-schema filing without a declared total still ingests on its rows', () => {
  // Filings older than the XML summary page carry no tableEntryTotal. Absence
  // must not become a shortfall against zero.
  const result = assessInformationTable({
    rawRows: [holding(), holding({ cusip: '594918104' })],
    summary: { declaredEntries: null, declaredValueUsd: null, confidentialOmitted: null },
  });
  assert.equal(result.status, 'complete');
});

/**
 * The whole path, over the document SEC actually served.
 *
 * The tests above take the placeholder row as given. This one parses it out of
 * the real 627-byte information table with the real parser, because the
 * premise worth checking is that the parser was never at fault: it read the
 * file correctly and the file has no holdings in it.
 */
test('the real parser reads the withheld table correctly and the assessment rejects it', async () => {
  const { parseInformationTable } = await import('./institutionalHoldingsService.js');
  const rows = parseInformationTable(fixture('norges-confidential.infotable.xml'), 1);

  // Exactly what production stored: one row, and not a holding.
  assert.equal(rows.length, 1);
  assert.equal(rows[0].cusip, '000000000');
  assert.equal(rows[0].issuer_name, 'NA');
  assert.equal(rows[0].value_usd, 0);
  assert.equal(rows[0].shares, 0);

  const result = assessInformationTable({ rawRows: rows, summary: parseSummaryPage(NORGES_COVER) });
  assert.equal(result.status, 'confidential');
  assert.equal(result.realRows.length, 0);
});
