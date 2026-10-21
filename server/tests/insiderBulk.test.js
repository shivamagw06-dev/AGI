import test from 'node:test';
import assert from 'node:assert/strict';
import { bulkDate, parseTsv, assembleFilings, groupByAccession } from '../services/insiderBulk.js';

const tsv = (rows) => rows.map((row) => row.join('\t')).join('\n');

test('the dataset date format converts, and anything else is null', () => {
  assert.equal(bulkDate('31-OCT-2025'), '2025-10-31');
  assert.equal(bulkDate('01-JAN-2016'), '2016-01-01');
  // Blank is the common case in these files, and the empty string is exactly
  // what took the nightly job down when it reached a date column.
  assert.equal(bulkDate(''), null);
  assert.equal(bulkDate('   '), null);
  assert.equal(bulkDate(null), null);
  assert.equal(bulkDate('2025-10-31'), null);
  assert.equal(bulkDate('31-XXX-2025'), null);
  assert.equal(bulkDate('45-OCT-2025'), null);
});

test('rows are split on tabs only, so free text cannot swallow a row', () => {
  // REMARKS carries company prose. A CSV-style parser honouring quotes would
  // consume every following row after an unbalanced quotation mark, and these
  // files contain plenty.
  const rows = parseTsv(tsv([
    ['ACCESSION_NUMBER', 'REMARKS'],
    ['0001-25-000001', 'See "note 3 for the officer\'s holdings'],
    ['0001-25-000002', 'plain'],
  ]));
  assert.equal(rows.length, 2);
  assert.equal(rows[1].ACCESSION_NUMBER, '0001-25-000002');
});

test('a short row leaves later columns empty rather than undefined', () => {
  const rows = parseTsv('A\tB\tC\nonly-a');
  assert.equal(rows[0].A, 'only-a');
  assert.equal(rows[0].C, '');
});

test('grouping ignores rows with no accession', () => {
  const map = groupByAccession([{ ACCESSION_NUMBER: 'x' }, { ACCESSION_NUMBER: '' }, {}]);
  assert.equal(map.size, 1);
});

const submission = (over = {}) => ({
  ACCESSION_NUMBER: '0001-25-000001', FILING_DATE: '31-OCT-2025', PERIOD_OF_REPORT: '29-OCT-2025',
  DOCUMENT_TYPE: '4', ISSUERCIK: '0000320193', ISSUERNAME: 'Apple Inc.',
  ISSUERTRADINGSYMBOL: 'AAPL', AFF10B5ONE: '0', ...over,
});
const owner = (over = {}) => ({
  ACCESSION_NUMBER: '0001-25-000001', RPTOWNERCIK: '0009', RPTOWNERNAME: 'COOK TIMOTHY',
  RPTOWNER_RELATIONSHIP: 'Officer', RPTOWNER_TITLE: 'CEO', ...over,
});
const trans = (over = {}) => ({
  ACCESSION_NUMBER: '0001-25-000001', SECURITY_TITLE: 'Common Stock', TRANS_DATE: '29-OCT-2025',
  TRANS_CODE: 'S', TRANS_SHARES: '1000', TRANS_PRICEPERSHARE: '250.5',
  TRANS_ACQUIRED_DISP_CD: 'D', SHRS_OWND_FOLWNG_TRANS: '50000', DIRECT_INDIRECT_OWNERSHIP: 'D', ...over,
});

test('a filing assembles into the shape the insider panel reads', () => {
  const { filings } = assembleFilings({
    submissions: [submission()], owners: [owner()], nonDeriv: [trans()], deriv: [],
  });
  const [filing] = filings;
  assert.equal(filing.ticker, 'AAPL');
  assert.equal(filing.filed_at, '2025-10-31');
  assert.equal(filing.report_date, '2025-10-29');
  assert.equal(filing.parsed_data.owners[0].name, 'COOK TIMOTHY');
  assert.deepEqual(filing.parsed_data.owners[0].roles, ['officer']);
  assert.equal(filing.parsed_data.transactions[0].code_label, 'Open-market sale');
  assert.equal(filing.parsed_data.transactions[0].discretionary, true);
  assert.equal(filing.parsed_data.transactions[0].value_usd, 250500);
  assert.equal(filing.parsed_data.discretionary_sell_value, 250500);
  assert.equal(filing.parsed_data.has_discretionary, true);
});

test('the 10b5-1 flag survives the import', () => {
  // A sale under a plan adopted months earlier says nothing about what the
  // insider thinks now. Losing this field is how an insider feed becomes
  // noise, and it is the one column that cannot be reconstructed later.
  const planned = assembleFilings({ submissions: [submission({ AFF10B5ONE: '1' })], owners: [], nonDeriv: [], deriv: [] });
  assert.equal(planned.filings[0].parsed_data.planned, true);
  const unplanned = assembleFilings({ submissions: [submission({ AFF10B5ONE: '0' })], owners: [], nonDeriv: [], deriv: [] });
  assert.equal(unplanned.filings[0].parsed_data.planned, false);
  const blank = assembleFilings({ submissions: [submission({ AFF10B5ONE: '' })], owners: [], nonDeriv: [], deriv: [] });
  assert.equal(blank.filings[0].parsed_data.planned, false);
});

test('vesting is not counted as a decision', () => {
  // F is shares withheld for tax and A is a grant. Both move shares and
  // neither is a view on the stock. Counting them would make every quarter
  // look like heavy insider activity.
  const { filings } = assembleFilings({
    submissions: [submission()], owners: [],
    nonDeriv: [trans({ TRANS_CODE: 'F' }), trans({ TRANS_CODE: 'A', TRANS_ACQUIRED_DISP_CD: 'A' })],
    deriv: [],
  });
  assert.equal(filings[0].parsed_data.has_discretionary, false);
  assert.equal(filings[0].parsed_data.discretionary_sell_value, 0);
  assert.equal(filings[0].parsed_data.discretionary_buy_value, 0);
});

test('a grant with no price is valued null, not zero', () => {
  const { filings } = assembleFilings({
    submissions: [submission()], owners: [],
    nonDeriv: [trans({ TRANS_CODE: 'A', TRANS_PRICEPERSHARE: '', TRANS_ACQUIRED_DISP_CD: 'A' })],
    deriv: [],
  });
  assert.equal(filings[0].parsed_data.transactions[0].value_usd, null);
});

test('derivative rows are marked so an option grant is not read as a share purchase', () => {
  const { filings } = assembleFilings({
    submissions: [submission()], owners: [], nonDeriv: [trans()], deriv: [trans({ TRANS_CODE: 'M' })],
  });
  const marks = filings[0].parsed_data.transactions.map((t) => t.derivative);
  assert.deepEqual(marks, [false, true]);
});

test('only Form 4 and its amendments are kept', () => {
  // Form 3 is an initial statement of ownership and Form 5 an annual
  // catch-up. Neither is a transaction, and both would land in a transaction
  // feed as filings with nothing in them.
  const { filings, skippedForm } = assembleFilings({
    submissions: [submission(), submission({ ACCESSION_NUMBER: 'a', DOCUMENT_TYPE: '3' }),
      submission({ ACCESSION_NUMBER: 'b', DOCUMENT_TYPE: '5' }),
      submission({ ACCESSION_NUMBER: 'c', DOCUMENT_TYPE: '4/A' })],
    owners: [], nonDeriv: [], deriv: [],
  });
  assert.deepEqual(filings.map((f) => f.form_type), ['4', '4/A']);
  assert.equal(skippedForm, 2);
});

test('the held-ticker filter is applied case-insensitively and counted', () => {
  const { filings, skippedTicker } = assembleFilings({
    submissions: [submission(), submission({ ACCESSION_NUMBER: 'z', ISSUERTRADINGSYMBOL: 'ZZZZ' })],
    owners: [], nonDeriv: [], deriv: [], tickers: ['aapl'],
  });
  assert.deepEqual(filings.map((f) => f.ticker), ['AAPL']);
  assert.equal(skippedTicker, 1);
});

test('no ticker filter keeps everything', () => {
  const { filings } = assembleFilings({
    submissions: [submission(), submission({ ACCESSION_NUMBER: 'z', ISSUERTRADINGSYMBOL: 'ZZZZ' })],
    owners: [], nonDeriv: [], deriv: [], tickers: null,
  });
  assert.equal(filings.length, 2);
});

test('an unrecognised transaction code is labelled, not dropped', () => {
  // Dropping it would understate a filing's activity; treating it as
  // discretionary would invent a decision nobody made.
  const { filings } = assembleFilings({
    submissions: [submission()], owners: [], nonDeriv: [trans({ TRANS_CODE: 'Z' })], deriv: [],
  });
  const [tx] = filings[0].parsed_data.transactions;
  assert.match(tx.code_label, /Unrecognised code Z/);
  assert.equal(tx.discretionary, false);
});
