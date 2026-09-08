import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseFormFour, transactions, reportingOwners, TRANSACTION_CODES } from '../services/formFour.js';

const apple = readFileSync(new URL('./fixtures/formFourApple.xml', import.meta.url), 'utf8');

test('a real filing reads into its parts', () => {
  const f = parseFormFour(apple);
  assert.equal(f.document_type, '4');
  assert.equal(f.issuer_name, 'Apple Inc.');
  assert.equal(f.ticker, 'AAPL');
  assert.equal(f.period_of_report, '2026-09-01');
  assert.equal(f.owners[0].name, 'Newstead Jennifer');
  assert.deepEqual(f.owners[0].roles, ['officer']);
  assert.equal(f.owners[0].officer_title, 'SVP, GC and Government Affairs');
});

test('shares and price come through, and the value is their product', () => {
  const [t] = parseFormFour(apple).transactions;
  assert.equal(t.shares, 1439);
  assert.equal(t.price_per_share, 317.01);
  assert.equal(t.value_usd, 1439 * 317.01);
  assert.equal(t.shares_owned_after, 35790);
});

test('a Rule 10b5-1 sale is marked as planned', () => {
  // A sale under a plan adopted months earlier says nothing about what the
  // insider thinks now. Presenting it beside a discretionary sale is how an
  // insider feed becomes noise.
  assert.equal(parseFormFour(apple).planned, true);
});

test('tax withholding and option exercises are not decisions', () => {
  // Most insider "selling" is a vesting calendar, not a view. Counting F and M
  // as sales produces a stream of alarming activity that means nothing.
  assert.equal(TRANSACTION_CODES.F.discretionary, false);
  assert.equal(TRANSACTION_CODES.M.discretionary, false);
  assert.equal(TRANSACTION_CODES.A.discretionary, false);
  assert.equal(TRANSACTION_CODES.G.discretionary, false);
  assert.equal(TRANSACTION_CODES.P.discretionary, true);
  assert.equal(TRANSACTION_CODES.S.discretionary, true);
});

test('a vesting filing contributes nothing to the discretionary totals', () => {
  const vesting = `<ownershipDocument><documentType>4</documentType>
    <issuer><issuerCik>1</issuerCik><issuerName>X</issuerName><issuerTradingSymbol>X</issuerTradingSymbol></issuer>
    <nonDerivativeTable>
      <nonDerivativeTransaction><securityTitle><value>Common</value></securityTitle>
        <transactionCoding><transactionCode>A</transactionCode></transactionCoding>
        <transactionAmounts><transactionShares><value>5000</value></transactionShares>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts>
      </nonDerivativeTransaction>
      <nonDerivativeTransaction><securityTitle><value>Common</value></securityTitle>
        <transactionCoding><transactionCode>F</transactionCode></transactionCoding>
        <transactionAmounts><transactionShares><value>2100</value></transactionShares>
        <transactionPricePerShare><value>50</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode></transactionAmounts>
      </nonDerivativeTransaction>
    </nonDerivativeTable></ownershipDocument>`;
  const f = parseFormFour(vesting);
  assert.equal(f.transactions.length, 2);
  assert.equal(f.has_discretionary, false);
  assert.equal(f.discretionary_sell_value, 0, 'a tax withholding is not a sale');
  assert.equal(f.discretionary_buy_value, 0, 'a grant is not a purchase');
});

test('a grant with no price is worth null, not zero', () => {
  // Zero would read as a transaction worth nothing rather than one whose
  // value the filing does not state.
  const [grant] = transactions(`<nonDerivativeTransaction>
    <transactionCoding><transactionCode>A</transactionCode></transactionCoding>
    <transactionAmounts><transactionShares><value>1000</value></transactionShares></transactionAmounts>
  </nonDerivativeTransaction>`);
  assert.equal(grant.shares, 1000);
  assert.equal(grant.price_per_share, null);
  assert.equal(grant.value_usd, null);
});

test('derivative rows are read and marked apart from share transactions', () => {
  // An option grant and a share purchase are different events, and a reader
  // must not have to infer which from the numbers.
  const both = `<nonDerivativeTable><nonDerivativeTransaction>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts><transactionShares><value>10</value></transactionShares><transactionPricePerShare><value>5</value></transactionPricePerShare></transactionAmounts>
    </nonDerivativeTransaction></nonDerivativeTable>
    <derivativeTable><derivativeTransaction>
      <transactionCoding><transactionCode>A</transactionCode></transactionCoding>
      <transactionAmounts><transactionShares><value>20</value></transactionShares></transactionAmounts>
    </derivativeTransaction></derivativeTable>`;
  const rows = transactions(both);
  assert.equal(rows.length, 2);
  assert.equal(rows.find((r) => r.code === 'P').derivative, false);
  assert.equal(rows.find((r) => r.code === 'A').derivative, true);
});

test('several reporting owners on one filing are all read', () => {
  const two = `<reportingOwner><reportingOwnerId><rptOwnerCik>1</rptOwnerCik><rptOwnerName>A</rptOwnerName></reportingOwnerId>
      <reportingOwnerRelationship><isDirector>true</isDirector></reportingOwnerRelationship></reportingOwner>
    <reportingOwner><reportingOwnerId><rptOwnerCik>2</rptOwnerCik><rptOwnerName>B</rptOwnerName></reportingOwnerId>
      <reportingOwnerRelationship><isTenPercentOwner>1</isTenPercentOwner></reportingOwnerRelationship></reportingOwner>`;
  const owners = reportingOwners(two);
  assert.equal(owners.length, 2);
  assert.deepEqual(owners[0].roles, ['director']);
  assert.deepEqual(owners[1].roles, ['ten_percent_owner']);
});

test('a document that is not a Form 4 yields nothing rather than throwing', () => {
  assert.equal(parseFormFour('<html>not a filing</html>'), null);
  assert.equal(parseFormFour(''), null);
  assert.equal(parseFormFour(null), null);
});

test('an unrecognised code is not silently treated as a decision', () => {
  const odd = transactions(`<nonDerivativeTransaction>
    <transactionCoding><transactionCode>Z</transactionCode></transactionCoding>
    <transactionAmounts><transactionShares><value>1</value></transactionShares></transactionAmounts>
  </nonDerivativeTransaction>`)[0];
  assert.equal(odd.discretionary, false);
  assert.match(odd.code_label, /Unrecognised code Z/);
});
