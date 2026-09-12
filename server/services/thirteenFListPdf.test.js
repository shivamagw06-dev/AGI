import assert from 'node:assert/strict';
import test from 'node:test';
import { rowsFromTextItems, securitiesFromRows, columnsFromHeader } from './thirteenFListPdf.js';

// Real x coordinates and glyph runs from page 6 of the 2026 Q2 list. The
// transform array is pdf.js's shape; only entries 4 and 5 (x and y) are read.
const at = (x, y, str) => ({ str, transform: [1, 0, 0, 1, x, y] });

// Every page reprints the column header, and the parser calibrates off it.
// A page without one carries no securities, so tests supply it.
const HEADER = [
  at(73, 536, 'CUSIP NO'), at(167, 536, 'ISSUER NAME'),
  at(350, 536, 'ISSUER DESCRIPTION'), at(466, 536, 'STATUS'),
];
const withHeader = (...rows) => [...HEADER, ...rows.flat()];

const AON_COMMON = [
  at(73, 500, 'G0403H'), at(116, 500, '10'), at(135, 500, '8'),
  at(150, 500, '*'), at(167, 500, 'AON PLC'), at(350, 500, 'SHS CL A'),
];
const AON_CALL = [
  at(73, 488, 'G0403H'), at(116, 488, '90'), at(135, 488, '8'),
  at(167, 488, 'AON PLC'), at(350, 488, 'CALL'),
];
const ADDED_ROW = [
  at(73, 476, 'G0271M'), at(116, 476, '12'), at(135, 476, '2'),
  at(167, 476, 'APEIRON ACQUISITION VEH I'), at(350, 476, 'UNIT 99/99/9999'), at(466, 476, 'ADDED'),
];
const FURNITURE = [
  at(73, 560, 'Run Date:'), at(167, 548, '** List of Section 13F Securities **'),
  at(73, 536, 'CUSIP NO'), at(167, 536, 'ISSUER NAME'), at(350, 536, 'ISSUER DESCRIPTION'),
];

test('the CUSIP is reassembled from its three columns', () => {
  const [row] = securitiesFromRows(rowsFromTextItems(withHeader(AON_COMMON)));
  assert.equal(row.cusip, 'G0403H108');
  assert.equal(row.issuer_number, 'G0403H');
  assert.equal(row.issue_number, '10');
});

test('name and description split on position, not on word order', () => {
  // These are adjacent strings with no delimiter. Splitting by text order is a
  // guess; the x band makes it exact.
  const [row] = securitiesFromRows(rowsFromTextItems(withHeader(AON_COMMON)));
  assert.equal(row.issuer_name, 'AON PLC');
  assert.equal(row.description, 'SHS CL A');
});

test('the options marker is its own column, not the first word of the name', () => {
  const [withStar] = securitiesFromRows(rowsFromTextItems(withHeader(AON_COMMON)));
  const [without] = securitiesFromRows(rowsFromTextItems(withHeader(AON_CALL)));
  assert.equal(withStar.has_listed_options, true);
  assert.equal(without.has_listed_options, false);
  assert.equal(withStar.issuer_name, 'AON PLC');
});

test('status is read only from the status column', () => {
  const [row] = securitiesFromRows(rowsFromTextItems(withHeader(ADDED_ROW)));
  assert.equal(row.status, 'ADDED');
  assert.equal(row.description, 'UNIT 99/99/9999');
});

test('page furniture is discarded', () => {
  const rows = securitiesFromRows(rowsFromTextItems(withHeader(FURNITURE, AON_COMMON)));
  assert.equal(rows.length, 1);
  assert.equal(rows[0].cusip, 'G0403H108');
});

test('rows are emitted in reading order, top of page first', () => {
  // PDF user space puts the origin at the bottom, so descending y is downward.
  const rows = securitiesFromRows(rowsFromTextItems(withHeader(ADDED_ROW, AON_CALL, AON_COMMON)));
  assert.deepEqual(rows.map((r) => r.cusip), ['G0403H108', 'G0403H908', 'G0271M122']);
});

test('a multi-run name in one band is joined, not split into two rows', () => {
  // Long names arrive as several text runs at different x offsets inside the
  // name band. They belong to one field.
  const items = [
    at(73, 400, 'G0262A'), at(116, 400, '10'), at(135, 400, '3'),
    at(167, 400, 'AMBITIONS'), at(227, 400, ' ENTERPRISE MGMT CO'),
    at(350, 400, 'USD CL A ORD SHS'),
  ];
  const [row] = securitiesFromRows(rowsFromTextItems(withHeader(items)));
  assert.equal(row.issuer_name, 'AMBITIONS ENTERPRISE MGMT CO');
  assert.equal(row.description, 'USD CL A ORD SHS');
});

test('CINS codes beginning with a letter survive the CUSIP shape test', () => {
  // 34 rows in 2026 Q2 are B-prefixed CINS - CMB.TECH, MDxHealth, Nyxoah,
  // Titan America. A shape test written as six *digits* drops all of them.
  const items = [at(73, 300, 'B38564'), at(116, 300, '10'), at(135, 300, '8'),
    at(167, 300, 'CMB.TECH NV'), at(350, 300, 'SHS')];
  const [row] = securitiesFromRows(rowsFromTextItems(withHeader(items)));
  assert.equal(row.cusip, 'B38564108');
});

test('items without a transform or without text are ignored', () => {
  const rows = rowsFromTextItems(withHeader([{ str: 'x' }, { transform: [1,0,0,1,73,10] }, null], AON_COMMON));
  assert.equal(securitiesFromRows(rows).length, 1);
});

test('glyph runs are ordered by x before joining, whatever order they arrive in', () => {
  // pdf.js emits text runs in content-stream order, which is not guaranteed to
  // be left-to-right. Joining them as they arrive reverses multi-run fields:
  // "AMBITIONS ENTERPRISE MGMT CO" becomes "ENTERPRISE MGMT CO AMBITIONS", and
  // the CUSIP reassembles backwards.
  const shuffled = [
    at(350, 400, 'USD CL A ORD SHS'),
    at(227, 400, ' ENTERPRISE MGMT CO'),
    at(135, 400, '3'),
    at(167, 400, 'AMBITIONS'),
    at(73, 400, 'G0262A'),
    at(116, 400, '10'),
  ];
  const [row] = securitiesFromRows(rowsFromTextItems(withHeader(shuffled)));
  assert.equal(row.cusip, 'G0262A103');
  assert.equal(row.issuer_name, 'AMBITIONS ENTERPRISE MGMT CO');
});

test('a page with no column header yields nothing, rather than a guess', () => {
  assert.equal(columnsFromHeader([at(73, 500, 'Run Date:')]), null);
  assert.equal(rowsFromTextItems(AON_COMMON).length, 0);
});

test('columns are read from the header, so a shifted layout still parses', () => {
  // Across 2019Q1-2026Q2 the layout drifts. In 2025Q4 every column moves two
  // to three units left, which put the options asterisk where a fixed band
  // expected the check digit: the check became "8*", the row failed its shape
  // test, and because only optioned securities carry an asterisk exactly the
  // largest names vanished. That quarter parsed 2,498 equities against about
  // 7,000 in its neighbours, silently.
  const shifted = [
    at(74, 536, 'CUSIP NO'), at(169, 536, 'ISSUER NAME'),
    at(349, 536, 'ISSUER DESCRIPTION'), at(465, 536, 'STATUS'),
    at(74, 500, 'G0403H'), at(117, 500, '10'), at(135, 500, '8'), at(147, 500, '*'),
    at(169, 500, 'AON'), at(193, 500, ' PLC'), at(349, 500, 'SHS'), at(373, 500, ' CL A'),
  ];
  const [row] = securitiesFromRows(rowsFromTextItems(shifted));
  assert.equal(row.cusip, 'G0403H108');
  assert.equal(row.has_listed_options, true);
  assert.equal(row.issuer_name, 'AON PLC');
  assert.equal(row.description, 'SHS CL A');
});

test('a CUSIP emitted as one joined run is tokenised, not dropped', () => {
  // 2025Q2 emits "G0509J 11 5" as a single text run rather than three. Splitting
  // the left column by run position drops every row in that quarter.
  const joined = withHeader([
    at(70, 500, 'G0509J 11 5'), at(167, 500, 'ARTIUS II ACQUISITION INC'),
    at(350, 500, 'SHS CL A'), at(466, 500, 'ADDED'),
  ]);
  const [row] = securitiesFromRows(rowsFromTextItems(joined));
  assert.equal(row.cusip, 'G0509J115');
  assert.equal(row.status, 'ADDED');
});

test('a CUSIP whose runs are butted together with no spacing is still split', () => {
  // The third shape the left column arrives in. Nine characters, no separator.
  const items = withHeader([
    at(73, 500, 'G0403H'), at(116, 500, '10'), at(135, 500, '8'),
    at(167, 500, 'AON PLC'), at(350, 500, 'SHS CL A'),
  ]);
  const [row] = securitiesFromRows(rowsFromTextItems(items));
  assert.equal(row.cusip, 'G0403H108');
});
