import test from 'node:test';
import assert from 'node:assert/strict';
import { issuerDirectory, FUND_SECTOR, FUND_INDUSTRY } from '../services/issuerDirectory.js';

const companies = { 0: { ticker: 'XOM', cik_str: 34088, title: 'EXXON MOBIL CORP' } };
const exchange = { fields: ['cik', 'name', 'ticker', 'exchange'], data: [[884394, 'SPDR S&P 500 ETF TRUST', 'SPY', 'NYSE']] };
const funds = { fields: ['cik', 'seriesId', 'classId', 'symbol'], data: [[36405, 'S000002839', 'C000092055', 'VOO']] };

test('the securities that were silently skipped are now found', () => {
  // 8.6% of the book by value, almost all of it funds: an index ETF is not an
  // operating company and has no entry in company_tickers.json.
  const directory = issuerDirectory({ companies, exchange, funds });
  assert.equal(directory.get('VOO').kind, 'fund');
  assert.equal(directory.get('SPY').kind, 'company'); // present at all, which it was not before
  assert.equal(directory.get('XOM').kind, 'company');
});

test('SPY comes from the exchange file, because it is in neither of the others', () => {
  // The SPDR trust is a unit investment trust: not an operating company and
  // not a registered fund, so it appears only in company_tickers_exchange.
  assert.equal(issuerDirectory({ companies, funds }).has('SPY'), false);
  assert.equal(issuerDirectory({ companies, exchange, funds }).get('SPY').cik, '0000884394');
});

test('an operating company outranks a fund of the same ticker', () => {
  // A SIC code from a real registrant says more than "this is a fund".
  const clash = { fields: ['cik', 'seriesId', 'classId', 'symbol'], data: [[999, 'S1', 'C1', 'XOM']] };
  assert.equal(issuerDirectory({ companies, funds: clash }).get('XOM').kind, 'company');
  assert.equal(issuerDirectory({ companies, funds: clash }).get('XOM').cik, '0000034088');
});

test('a fund that also lists on an exchange stays a fund', () => {
  // The exchange file mixes both and does not distinguish them; the fund list
  // does, and being listed is not evidence of being an operating company.
  const both = { fields: ['cik', 'name', 'ticker', 'exchange'], data: [[36405, 'VANGUARD S&P 500 ETF', 'VOO', 'NYSEARCA']] };
  assert.equal(issuerDirectory({ exchange: both, funds }).get('VOO').kind, 'fund');
});

test('CIKs are zero-padded to ten digits however they arrive', () => {
  // EDGAR paths need the padded form, and these files give bare integers.
  const directory = issuerDirectory({ companies, exchange, funds });
  assert.equal(directory.get('XOM').cik, '0000034088');
  assert.equal(directory.get('VOO').cik, '0000036405');
  assert.equal(issuerDirectory({ companies: { 0: { ticker: 'A', cik_str: '  CIK0000320193 ', title: 'X' } } }).get('A').cik, '0000320193');
});

test('tickers are matched upper-case and trimmed', () => {
  const directory = issuerDirectory({ companies: { 0: { ticker: ' xom ', cik_str: 34088, title: 'X' } } });
  assert.equal(directory.has('XOM'), true);
});

test('a Map of already-parsed companies is accepted', () => {
  // tickerMap() in the service returns exactly this shape, and building the
  // directory must not require re-fetching a file it already holds.
  const directory = issuerDirectory({ companies: new Map([['XOM', { cik: '0000034088', title: 'EXXON MOBIL CORP' }]]) });
  assert.equal(directory.get('XOM').cik, '0000034088');
  assert.equal(directory.get('XOM').title, 'EXXON MOBIL CORP');
});

test('a malformed or missing payload contributes nothing rather than throwing', () => {
  // These are fetched over the network and the shapes are not guaranteed.
  assert.equal(issuerDirectory().size, 0);
  assert.equal(issuerDirectory({}).size, 0);
  assert.equal(issuerDirectory({ funds: { fields: null, data: null } }).size, 0);
  assert.equal(issuerDirectory({ exchange: { data: [[1, 'x', 'Y', 'Z']] } }).size, 0);
  assert.equal(issuerDirectory({ companies, funds: 'nonsense' }).size, 1);
});

test('a row with no symbol is not stored under a blank key', () => {
  // A blank entry would match every security whose ticker is missing.
  const blanks = { fields: ['cik', 'seriesId', 'classId', 'symbol'], data: [[1, 'S', 'C', ''], [2, 'S', 'C', null]] };
  assert.equal(issuerDirectory({ funds: blanks }).size, 0);
});

test('the fund labels are stable', () => {
  // They are written into the classifications table and read by the rotation
  // chart; changing them silently would split the sector in two.
  assert.equal(FUND_SECTOR, 'Funds & ETFs');
  assert.equal(FUND_INDUSTRY, 'Fund or ETF');
});

test('a foreign private issuer is in the directory, because registration is not Section 16', () => {
  // The gap this matters for. sec_issuer_tickers is built from Form 3/4/5
  // submissions, and Section 16 does not apply to a foreign private issuer -
  // CyberArk files 20-F and no Form 4 exists for it, so the insider registry
  // cannot hold CYBR at all. Being absent from it is what marks a shape-valid
  // symbol as a venue code, and being marked is what makes the price backfill
  // skip it, so nothing prices it and the absence never resolves. $26.7bn of
  // CyberArk sat in that loop.
  //
  // The SEC's own register does list it, because listing is not Section 16.
  const fpi = {
    fields: ['cik', 'name', 'ticker', 'exchange'],
    data: [[1598110, 'CyberArk Software Ltd.', 'CYBR', 'Nasdaq']],
  };
  const directory = issuerDirectory({ companies, exchange: fpi });
  assert.equal(directory.get('CYBR').cik, '0001598110');
  assert.equal(directory.get('CYBR').title, 'CyberArk Software Ltd.');
  // A company, not a fund: the exchange file mixes both and only the fund file
  // settles it.
  assert.equal(directory.get('CYBR').kind, 'company');
});
