import assert from 'node:assert/strict';
import test from 'node:test';
import { aggregateByCusip } from './thirteenFAggregate.js';

const row = (cusip, quarter, over = {}) => ({
  cusip, quarter, issuer_name: 'AON PLC', description: 'SHS CL A',
  security_class: 'equity', has_listed_options: false, ...over,
});

test('the quarter window keeps both ends', () => {
  // The last quarter is how a superseded identifier is told apart from one
  // that was never listed at all. Keeping only the first loses that.
  const [agg] = aggregateByCusip([
    row('G0403H108', '2024q2'), row('G0403H108', '2019q1'), row('G0403H108', '2026q2'),
  ]);
  assert.equal(agg.first_quarter, '2019q1');
  assert.equal(agg.last_quarter, '2026q2');
  assert.equal(agg.observed_quarters, 3);
});

test('class and name come from the latest quarter, not the first', () => {
  // The SEC restates descriptions. The current one is what it stands behind.
  const [agg] = aggregateByCusip([
    row('X', '2019q1', { description: 'ORD', issuer_name: 'OLD NAME', security_class: 'equity' }),
    row('X', '2026q2', { description: 'NOTE 3.000%11/1', issuer_name: 'NEW NAME', security_class: 'debt' }),
  ]);
  assert.equal(agg.description, 'NOTE 3.000%11/1');
  assert.equal(agg.issuer_name, 'NEW NAME');
  assert.equal(agg.security_class, 'debt');
});

test('rows arriving out of order still produce the right window', () => {
  const [agg] = aggregateByCusip([row('X', '2026q2'), row('X', '2019q1')]);
  assert.equal(agg.first_quarter, '2019q1');
  assert.equal(agg.last_quarter, '2026q2');
});

test('options are ever-listed, not currently-listed', () => {
  // An issue that carried options in any quarter is one whose 90 and 95 lines
  // exist somewhere in our holdings, whether or not it carries them today.
  const [agg] = aggregateByCusip([
    row('X', '2019q1', { has_listed_options: true }),
    row('X', '2026q2', { has_listed_options: false }),
  ]);
  assert.equal(agg.has_listed_options, true);
});

test('rows without a CUSIP are dropped rather than keyed on empty', () => {
  assert.equal(aggregateByCusip([{ quarter: '2019q1' }, row('X', '2019q1')]).length, 1);
});
