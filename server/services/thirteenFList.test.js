import assert from 'node:assert/strict';
import test from 'node:test';
import { parseThirteenFList, classifySecurity, normaliseIssuerName, chainIdentities } from './thirteenFList.js';

// A verbatim slice of the 2026 Q2 list as pypdf extracts it, including the page
// furniture the parser has to step over and the bare asterisk that marks an
// optioned issue.
const SAMPLE = [
  'Run Date:', '6/30/2026', '** List of Section 13F Securities **', 'Page 4',
  'CUSIP NO', 'ISSUER NAME', 'ISSUER DESCRIPTION', 'STATUS',
  'G0403H', '10', '8', '*', 'AON PLC', 'SHS CL A',
  'G0403H', '90', '8', 'AON PLC', 'CALL',
  'G0403H', '95', '8', 'AON PLC', 'PUT',
  'G0344N', '10', '7', 'AMPERCAP ACQUISITION CO', 'ORD SHS', 'ADDED',
  '958102', 'AT', '2', 'WESTERN DIGITAL CORP', 'NOTE  3.000%11/1',
  '097023', '20', '4', 'BOEING CO', 'DEP CONV PFD A',
].join('\n');

test('parses the CUSIP triple back into a whole identifier', () => {
  const rows = parseThirteenFList(SAMPLE);
  assert.equal(rows.length, 6);
  assert.deepEqual(rows.map((r) => r.cusip), [
    'G0403H108', 'G0403H908', 'G0403H958', 'G0344N107', '958102AT2', '097023204',
  ]);
});

test('the asterisk is consumed, not read as the issuer name', () => {
  const [aon] = parseThirteenFList(SAMPLE);
  assert.equal(aon.issuer_name, 'AON PLC');
  assert.equal(aon.description, 'SHS CL A');
  assert.equal(aon.has_listed_options, true);
});

test('issue 90 is the call and 95 the put on the same issuer', () => {
  const rows = parseThirteenFList(SAMPLE);
  const call = rows.find((r) => r.cusip === 'G0403H908');
  const put = rows.find((r) => r.cusip === 'G0403H958');
  assert.equal(call.security_class, 'option');
  assert.equal(put.security_class, 'option');
  assert.equal(call.issue_number, '90');
  assert.equal(put.issue_number, '95');
});

test('ADDED is read as status, not as the next record', () => {
  const row = parseThirteenFList(SAMPLE).find((r) => r.cusip === 'G0344N107');
  assert.equal(row.status, 'ADDED');
  assert.equal(row.description, 'ORD SHS');
});

test('page furniture between records is skipped', () => {
  const noisy = ['Run Date:', '6/30/2026', 'Page 12', 'CUSIP NO',
    '670703', '10', '7', 'NUVALENT INC', 'COM'].join('\n');
  const rows = parseThirteenFList(noisy);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].cusip, '670703107');
});

test('class comes from the description, never from the issuer name', () => {
  // Western Digital is an equity, a note and two options at once. Only the
  // description separates them, which is the whole reason a name join is unsafe.
  assert.equal(classifySecurity('NOTE  3.000%11/1'), 'debt');
  assert.equal(classifySecurity('COM'), 'equity');
  assert.equal(classifySecurity('CALL'), 'option');
  assert.equal(classifySecurity('PUT'), 'option');
  assert.equal(classifySecurity('DEP CONV PFD A'), 'preferred');
  assert.equal(classifySecurity('PERP PFD CNV A'), 'preferred');
  assert.equal(classifySecurity('SER A MAND CNV'), 'preferred');
  assert.equal(classifySecurity('SPONSORED ADR'), 'equity');
  assert.equal(classifySecurity('ORD SHS'), 'equity');
  assert.equal(classifySecurity('UNIT 05/22/2031'), 'derivative');
  assert.equal(classifySecurity('*W EXP 02/03/202'), 'derivative');
  assert.equal(classifySecurity(''), 'unknown');
});

test('preferred is tested before equity, because ADRs of preferred match both', () => {
  // Five descriptions in the 2026 Q2 list match the equity pattern and the
  // preferred pattern at once - they are depositary receipts *of preferred
  // stock*. With equity tested first the ADR wins and a preferred is published
  // as common. These are verbatim rows, not constructed ones.
  for (const d of ['SP ADR PFD A', 'SPON ADS PFD B1', 'SPON ADR REP PFD', 'SP ADR N-V PFD', 'SP ADR PFD NEW']) {
    assert.equal(classifySecurity(d), 'preferred', `${d} must not classify as equity`);
  }
});

test('issuer names normalise across the two sources spelling', () => {
  assert.equal(normaliseIssuerName('COOPER COS INC'), normaliseIssuerName('COOPER COMPANIES, INC.'));
  assert.equal(normaliseIssuerName('APTIV PLC'), 'APTIV');
  assert.equal(normaliseIssuerName('JANUS HENDERSON GROUP PLC'), 'JANUS HENDERSON');
});

test('a CUSIP change is chained into one security key', () => {
  const rows = [
    { cusip: 'G6095L109', issuer_name: 'APTIV PLC', security_class: 'equity', quarter: '2024q1' },
    { cusip: 'G3265R107', issuer_name: 'APTIV PLC', security_class: 'equity', quarter: '2026q2' },
  ];
  const [chain] = chainIdentities(rows);
  assert.equal(chain.changed_identifier, true);
  assert.equal(chain.cusips.length, 2);
  // Earliest observation is the key, so history filed under the old identifier
  // is not orphaned by the change.
  assert.equal(chain.security_key, 'G6095L109');
});

test('debt is never chained, because two bonds share a name and a class', () => {
  const rows = [
    { cusip: '958102AT2', issuer_name: 'WESTERN DIGITAL CORP', security_class: 'debt', quarter: '2024q1' },
    { cusip: '958102AB9', issuer_name: 'WESTERN DIGITAL CORP', security_class: 'debt', quarter: '2024q1' },
  ];
  assert.equal(chainIdentities(rows).length, 0);
});

test('normalisation is exact, and a near-miss does not match', () => {
  // The list truncates at 28 characters and contains typos - "TWO HARBORS
  // INVENTMENT CORPO" is verbatim from 2026 Q2. It must NOT normalise onto the
  // ticker file's "Two Harbors Investment Corp": resolving that by edit
  // distance is a guess, and the failure mode of a wrong guess is one issuer's
  // holdings carrying another issuer's ticker.
  assert.notEqual(
    normaliseIssuerName('TWO HARBORS INVENTMENT CORPO'),
    normaliseIssuerName('Two Harbors Investment Corp'),
  );
});

test('a trust unit is a share; a dated unit is a SPAC', () => {
  // SPY's description is "TR UNIT" and QQQ's is "UNIT SER 1". A rule matching
  // \bUNIT\b without requiring a date classifies both as derivatives and drops
  // the two most widely held securities in 13F filings out of resolution
  // entirely. A real SPAC unit carries an expiry: "UNIT 05/22/2031".
  assert.equal(classifySecurity('TR UNIT'), 'equity');
  assert.equal(classifySecurity('UNIT SER 1'), 'equity');
  assert.equal(classifySecurity('UNIT 05/22/2031'), 'derivative');
  assert.equal(classifySecurity('UNIT 99/99/9999'), 'derivative');
  assert.equal(classifySecurity('RIGHT 05/22/2031'), 'derivative');
  assert.equal(classifySecurity('*W EXP 02/03/202'), 'derivative');
});

test('fund descriptions carrying a name are equity, not excluded', () => {
  // For funds the 28-character description field holds the fund's name rather
  // than a class code. These are tradeable shares with tickers.
  assert.equal(classifySecurity('S&P 500 ETF SHS'), 'equity');
  assert.equal(classifySecurity('CORE S&P500 ETF'), 'equity');
  assert.equal(classifySecurity('RUSSELL 2000 ETF'), 'equity');
});
