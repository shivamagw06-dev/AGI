import test from 'node:test';
import assert from 'node:assert/strict';
import {
  issuerTickerPairs, mergePairs, namesByTicker, windowOverlaps,
} from '../services/issuerTickerRegistry.js';
import { bulkDate } from '../services/insiderBulk.js';

const sub = (over = {}) => ({
  ISSUERTRADINGSYMBOL: 'PARA', ISSUERCIK: '0000813828',
  ISSUERNAME: 'Paramount Global', FILING_DATE: '15-MAR-2024', ...over,
});

test('pairs carry the window they were observed over', () => {
  const [pair] = issuerTickerPairs([
    sub({ FILING_DATE: '15-MAR-2024' }),
    sub({ FILING_DATE: '02-NOV-2024' }),
    sub({ FILING_DATE: '08-JAN-2024' }),
  ], { bulkDate });
  assert.equal(pair.ticker, 'PARA');
  assert.equal(pair.first_seen, '2024-01-08');
  assert.equal(pair.last_seen, '2024-11-02');
  assert.equal(pair.filings, 3);
});

test('a ticker that changes hands is two rows, not one', () => {
  // The case that makes this whole table necessary. PARA was Paramount Global
  // and is now Banzai International; collapsing on ticker alone would leave
  // one of them, and a 2019 holding would resolve to whichever survived.
  const pairs = issuerTickerPairs([
    sub({ FILING_DATE: '15-MAR-2024' }),
    sub({ ISSUERCIK: '0001826011', ISSUERNAME: 'Banzai International, Inc.', FILING_DATE: '10-JUN-2026' }),
  ], { bulkDate });
  assert.equal(pairs.length, 2);
  assert.deepEqual(pairs.map((p) => p.issuer_name).sort(), ['Banzai International, Inc.', 'Paramount Global']);
});

test('a company that changes ticker is also two rows', () => {
  // The same fact from the other direction. Only the pair is stable.
  const pairs = issuerTickerPairs([
    sub({ ISSUERTRADINGSYMBOL: 'FB', ISSUERNAME: 'Meta Platforms, Inc.', ISSUERCIK: '0001326801' }),
    sub({ ISSUERTRADINGSYMBOL: 'META', ISSUERNAME: 'Meta Platforms, Inc.', ISSUERCIK: '0001326801' }),
  ], { bulkDate });
  assert.equal(pairs.length, 2);
});

test('a row missing any of the three is not a mapping', () => {
  // A blank ticker stored as a mapping would match every symbol that fails to
  // resolve, which is the opposite of what the table is for.
  const pairs = issuerTickerPairs([
    sub({ ISSUERTRADINGSYMBOL: '' }),
    sub({ ISSUERCIK: '' }),
    sub({ ISSUERNAME: '' }),
    sub({ FILING_DATE: '' }),
  ], { bulkDate });
  assert.deepEqual(pairs, []);
});

test('merging widens a window rather than replacing it', () => {
  // A later import must not narrow the record to whatever it happened to load.
  const merged = mergePairs(
    [{ ticker: 'PARA', cik: '1', issuer_name: 'Paramount Global', first_seen: '2024-01-08', last_seen: '2024-11-02', filings: 3 }],
    [{ ticker: 'PARA', cik: '1', issuer_name: 'Paramount Global', first_seen: '2023-02-01', last_seen: '2024-06-01', filings: 2 }],
  );
  assert.equal(merged.length, 1);
  assert.equal(merged[0].first_seen, '2023-02-01');
  assert.equal(merged[0].last_seen, '2024-11-02');
  assert.equal(merged[0].filings, 5);
});

test('names are indexed by ticker, newest window first', () => {
  const index = namesByTicker([
    { ticker: 'PARA', cik: '1', issuer_name: 'Paramount Global', first_seen: '2024-01-08', last_seen: '2024-11-02' },
    { ticker: 'PARA', cik: '2', issuer_name: 'Banzai International, Inc.', first_seen: '2026-01-05', last_seen: '2026-08-01' },
  ]);
  assert.deepEqual(index.get('PARA').map((r) => r.issuer_name), ['Banzai International, Inc.', 'Paramount Global']);
});

test('a holding matches the registry window that overlaps it', () => {
  const paramount = { first_seen: '2020-02-01', last_seen: '2024-06-01' };
  const banzai = { first_seen: '2026-01-05', last_seen: '2026-08-01' };
  const held2021 = { earliest: '2021-03-31', latest: '2021-12-31' };

  assert.equal(windowOverlaps(paramount, held2021), true);
  // The one that matters: a 2021 holding must not match the company that took
  // the ticker over in 2026, or Paramount's position is attributed to Banzai.
  assert.equal(windowOverlaps(banzai, held2021), false);
});

test('the margin is generous, because the two windows measure different things', () => {
  // A holding runs from a quarter-end; the registry runs from filing dates,
  // and only for quarters in which an insider actually filed. Requiring
  // containment would refuse nearly every true pair.
  const entry = { first_seen: '2024-05-01', last_seen: '2024-05-02' };
  assert.equal(windowOverlaps(entry, { earliest: '2023-09-30', latest: '2023-12-31' }), true);
  assert.equal(windowOverlaps(entry, { earliest: '2016-09-30', latest: '2016-12-31' }), false);
});

test('a missing window never overlaps', () => {
  assert.equal(windowOverlaps({}, { earliest: '2021-01-01', latest: '2021-12-31' }), false);
  assert.equal(windowOverlaps({ first_seen: '2021-01-01', last_seen: '2021-06-01' }, {}), false);
});

test('nothing in yields nothing out, without throwing', () => {
  assert.deepEqual(issuerTickerPairs(), []);
  assert.deepEqual(mergePairs(), []);
  assert.equal(namesByTicker().size, 0);
});
