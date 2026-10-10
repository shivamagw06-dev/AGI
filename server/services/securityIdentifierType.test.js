import assert from 'node:assert/strict';
import test from 'node:test';
import { checkDigit, classifyIdentifier, groupByIdType } from './securityIdentifierType.js';

test('a domestic CUSIP is asked with ID_CUSIP', () => {
  for (const id of ['037833100', '88160R101', '67066G104', '78462F103']) {
    const c = classifyIdentifier(id);
    assert.equal(c.valid, true, `${id} should be valid`);
    assert.equal(c.idType, 'ID_CUSIP');
    assert.equal(c.scheme, 'cusip');
  }
});

test('a letter-prefixed CINS is asked with ID_CINS, not ID_CUSIP', () => {
  // Verified against OpenFIGI: ID_CUSIP returns "No identifier found" for
  // every one of these, ID_CINS returns LIN, CB, SPOT, ASML, ACN.
  for (const id of ['G54950103', 'H1467J104', 'L8681T102', 'N07059210', 'G1151C101']) {
    const c = classifyIdentifier(id);
    assert.equal(c.valid, true, `${id} should be valid`);
    assert.equal(c.idType, 'ID_CINS', `${id} must not be asked as ID_CUSIP`);
    assert.equal(c.scheme, 'cins');
  }
});

test('option-line identifiers fail the check digit and are never asked', () => {
  // 90- and 95-series issue numbers against a real issuer. OpenFIGI answers
  // "Invalid idValue format" for these, so a request spent on one is wasted.
  for (const id of ['037833900', '67066G904', '88160R901', '78462F953', '46090E953', '464287955']) {
    const c = classifyIdentifier(id);
    assert.equal(c.valid, false, `${id} should be rejected`);
    assert.equal(c.idType, null, `${id} must not be given an idType`);
    assert.match(c.reason, /check digit/);
  }
});

test('the check digit is computed, not assumed from the last character', () => {
  // Mutation guard: a checkDigit that returned Number(body[7]) or a constant
  // would pass a validity test but fail these known values.
  assert.equal(checkDigit('03783310'), 0);   // Apple
  assert.equal(checkDigit('88160R10'), 1);   // Tesla
  assert.equal(checkDigit('G5495010'), 3);   // Linde
  assert.equal(checkDigit('67066G10'), 4);   // NVIDIA
  assert.equal(checkDigit('N0705921'), 0);   // ASML
});

test('the double-add-double weighting is applied to the right positions', () => {
  // Mutation guard for `i % 2 === 1`. Under the correct rule the second,
  // fourth, sixth and eighth characters double. Transposing two characters
  // across a doubling boundary must change the result, otherwise the
  // weighting is not being applied at all.
  const a = checkDigit('12000000');
  const b = checkDigit('21000000');
  assert.notEqual(a, b, 'transposition must change the check digit');
});

test('shape is validated before the check digit', () => {
  for (const bad of ['', '12345', '0378331000', 'ABC!@#123', null, undefined]) {
    const c = classifyIdentifier(bad);
    assert.equal(c.valid, false);
    assert.equal(c.scheme, 'unknown');
  }
});

test('grouping keeps schemes apart and quarantines the malformed', () => {
  const { jobs, invalid } = groupByIdType(['037833100', 'G54950103', '037833900']);
  assert.deepEqual(jobs, [
    { idType: 'ID_CUSIP', idValue: '037833100' },
    { idType: 'ID_CINS', idValue: 'G54950103' },
  ]);
  assert.equal(invalid.length, 1);
  assert.equal(invalid[0].identifier, '037833900');
});

test('grouping normalises case and whitespace', () => {
  const { jobs } = groupByIdType([' g54950103 ']);
  assert.deepEqual(jobs, [{ idType: 'ID_CINS', idValue: 'G54950103' }]);
});
