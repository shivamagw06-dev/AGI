import assert from 'node:assert/strict';
import test from 'node:test';
import { proposeFromChains } from './chainPropagation.js';

const aptiv = {
  known: new Map([['G3265R107', 'APTV']]),
  keyByCusip: new Map([['G6095L109', 'G6095L109'], ['G3265R107', 'G6095L109']]),
  cusipsByKey: new Map([['G6095L109', ['G6095L109', 'G3265R107']]]),
  observedFrom: new Map([['G6095L109', '2019-03-31']]),
};

test('an unmapped identifier takes the ticker its sibling already carries', () => {
  // Seven years of Aptiv holdings sit under G6095L109 and the vendor has never
  // heard of it. G3265R107 resolved on the first ask. 1,872 identifiers are in
  // this position and no lookup is needed to join them.
  const { proposals } = proposeFromChains(['G6095L109'], aptiv);
  assert.equal(proposals.length, 1);
  assert.equal(proposals[0].ticker, 'APTV');
  assert.equal(proposals[0].cusip, 'G6095L109');
});

test('the proposal claims only its own observed window', () => {
  // Taking the sibling's start date would relabel filings the mapping never
  // saw - the error valid_from exists to prevent.
  const { proposals } = proposeFromChains(['G6095L109'], aptiv);
  assert.equal(proposals[0].valid_from, '2019-03-31');
});

test('a conflicting chain is reported, never resolved by picking one', () => {
  // Two tickers in one chain means the chain is built wrong. Guessing which
  // half is right puts one company's ticker on another company's holdings,
  // which is the failure this whole exercise exists to avoid.
  const { proposals, conflicts } = proposeFromChains(['C'], {
    known: new Map([['A', 'AAA'], ['B', 'BBB']]),
    keyByCusip: new Map([['A', 'K'], ['B', 'K'], ['C', 'K']]),
    cusipsByKey: new Map([['K', ['A', 'B', 'C']]]),
    observedFrom: new Map([['C', '2020-01-01']]),
  });
  assert.equal(proposals.length, 0);
  assert.equal(conflicts.length, 1);
  assert.deepEqual(conflicts[0].tickers.sort(), ['AAA', 'BBB']);
});

test('an identifier never seen in a filing claims nothing', () => {
  const { proposals } = proposeFromChains(['G6095L109'], { ...aptiv, observedFrom: new Map() });
  assert.equal(proposals.length, 0);
});

test('an identifier that already has a ticker is never rewritten from a sibling', () => {
  // The guard has to hold even when a sibling could supply the same answer.
  // Without it, a mapping the vendor confirmed - or an operator corrected by
  // hand - is overwritten by one merely inferred from a chain, quietly
  // downgrading how well the ticker is evidenced.
  const { proposals } = proposeFromChains(['A'], {
    known: new Map([['A', 'AAA'], ['B', 'AAA']]),
    keyByCusip: new Map([['A', 'K'], ['B', 'K']]),
    cusipsByKey: new Map([['K', ['A', 'B']]]),
    observedFrom: new Map([['A', '2020-01-01']]),
  });
  assert.equal(proposals.length, 0);
});

test('an identifier in no chain is left alone', () => {
  const { proposals } = proposeFromChains(['ZZZZZZZZZ'], aptiv);
  assert.equal(proposals.length, 0);
});

test('a chain where no sibling has a ticker yields nothing', () => {
  const { proposals } = proposeFromChains(['A'], {
    known: new Map(),
    keyByCusip: new Map([['A', 'K'], ['B', 'K']]),
    cusipsByKey: new Map([['K', ['A', 'B']]]),
    observedFrom: new Map([['A', '2020-01-01']]),
  });
  assert.equal(proposals.length, 0);
});

test('the proposal records the identifier it was inferred from', () => {
  const { proposals } = proposeFromChains(['G6095L109'], aptiv);
  assert.equal(proposals[0].source, 'chain:G3265R107');
  assert.equal(proposals[0].manually_verified, false);
});
