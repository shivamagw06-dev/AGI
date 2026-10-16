import test from 'node:test';
import assert from 'node:assert/strict';
import { filesAsFund, FUND_FORM_PREFIXES } from '../services/fundEvidence.js';

const filer = (...forms) => ({ filings: { recent: { form: forms } } });

test('the registrants this exists for', () => {
  // Real form mixes, read from EDGAR. SPY and QQQ report an empty SIC, so
  // nothing else distinguishes them from a company with a missing code.
  assert.equal(filesAsFund(filer('497', 'N-30D', '24F-2NT', 'NPORT-P', '485BPOS')), true, 'SPY');
  assert.equal(filesAsFund(filer('DEFA14A', '497', '485BPOS', 'NPORT-P', '24F-2NT')), true, 'QQQ');
  assert.equal(filesAsFund(filer('4', '8-K', '424B2', '144', '10-Q')), false, 'AAPL');
  assert.equal(filesAsFund(filer('4', 'DEFA14A', '8-K', 'DFAN14A', 'PX14A6G')), false, 'XOM');
});

test('N-PX is not evidence of a fund', () => {
  // Every 13F filer files N-PX for its say-on-pay votes. Counting it would
  // reclassify Berkshire and the managers themselves as funds.
  assert.equal(filesAsFund(filer('N-PX', '13F-HR', '4')), false);
  assert.equal(filesAsFund(filer('N-PX')), false);
});

test('a Schedule 13G is not evidence either', () => {
  // Funds and operating companies both file them, so they separate nothing.
  assert.equal(filesAsFund(filer('SC 13G', 'SC 13G/A')), false);
});

test('one Investment Company Act form is enough', () => {
  // An operating company never files any of them, so a single occurrence is
  // decisive rather than suggestive.
  assert.equal(filesAsFund(filer('8-K', '10-K', '485BPOS')), true);
});

test('prefixes cover the variants', () => {
  for (const form of ['485BPOS', '485APOS', '485BXT', '497K', '497J', 'N-CSRS', 'NPORT-P', 'N-30B-2', 'N-CEN']) {
    assert.equal(filesAsFund(filer(form)), true, form);
  }
});

test('form matching ignores case and padding', () => {
  assert.equal(filesAsFund(filer('  nport-p  ')), true);
});

test('a payload with no filings is not a fund', () => {
  // Absence of evidence. The caller leaves such a security unclassified
  // rather than assigning it a sector on nothing.
  assert.equal(filesAsFund(undefined), false);
  assert.equal(filesAsFund({}), false);
  assert.equal(filesAsFund({ filings: {} }), false);
  assert.equal(filesAsFund({ filings: { recent: {} } }), false);
  assert.equal(filesAsFund({ filings: { recent: { form: 'not an array' } } }), false);
  assert.equal(filesAsFund(filer()), false);
  assert.equal(filesAsFund(filer('', null, undefined)), false);
});

test('the prefix list holds no form an operating company files', () => {
  // The guard on the whole idea: one wrong entry here moves a sector.
  const operating = ['10-K', '10-Q', '8-K', '4', '3', '5', 'DEF 14A', 'DEFA14A', 'S-1', 'S-3', 'S-4', '424B2', '144', '13F-HR', 'N-PX', 'SC 13D', 'SC 13G', '20-F', '6-K', '11-K', 'PX14A6G', 'DFAN14A'];
  for (const form of operating) {
    assert.equal(filesAsFund(filer(form)), false, `${form} must not read as a fund`);
  }
  assert.ok(FUND_FORM_PREFIXES.length > 10);
});
