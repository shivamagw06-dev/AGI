/**
 * Amendment handling, tested against cover pages captured from real SEC
 * filings rather than hand-written XML.
 *
 * The fixtures are the point. The previous implementation looked correct in
 * review - it had an is-restatement check, an amendment_type column and a
 * merge branch - and was inert against every filing SEC has ever published,
 * because the tag it searched for does not exist and the document carrying the
 * real tag was never downloaded. Only real filings show that.
 *
 *   server/tests/fixtures/sec13f/elliott-restatement.primary_doc.xml
 *     Elliott Investment Management, accession 0000902664-25-003078,
 *     report 2025-03-31, accepted 2025-07-21. SEC amendmentType: RESTATEMENT.
 *     https://www.sec.gov/Archives/edgar/data/1603466/000090266425003078
 *
 *   server/tests/fixtures/sec13f/berkshire-new-holdings.primary_doc.xml
 *     Berkshire Hathaway, accession 0000950123-25-008361,
 *     report 2025-03-31, accepted 2025-08-14. SEC amendmentType: NEW HOLDINGS,
 *     reason "Confidential Treatment Expired" - so the amendment carries only
 *     the positions previously withheld.
 *     https://www.sec.gov/Archives/edgar/data/1067983/000095012325008361
 *
 *   node --test server/services/secAmendment.test.js
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  parseAmendmentCoverPage, classifyFiling, applyAmendment, droppedPositions,
} from './secAmendment.js';

const fixture = (name) =>
  readFileSync(new URL(`../tests/fixtures/sec13f/${name}`, import.meta.url), 'utf8');

const RESTATEMENT = fixture('elliott-restatement.primary_doc.xml');
const NEW_HOLDINGS = fixture('berkshire-new-holdings.primary_doc.xml');

// ---------------------------------------------------------------------------
// The tag the old code looked for
// ---------------------------------------------------------------------------

test('no real SEC cover page contains the tag the old parser searched for', () => {
  // If this ever fails, SEC changed its schema and the rest of this file needs
  // rereading. Until then it documents why amendment detection was dead.
  for (const [name, xml] of [['restatement', RESTATEMENT], ['new holdings', NEW_HOLDINGS]]) {
    assert.equal(/isRestatement/i.test(xml), false,
      `the ${name} fixture contains "isRestatement", which SEC does not emit`);
    assert.equal(/<amendmentType>/i.test(xml), true,
      `the ${name} fixture should carry the real amendmentType tag`);
  }
});

// ---------------------------------------------------------------------------
// Classification against real filings
// ---------------------------------------------------------------------------

test('a real RESTATEMENT is classified as a restatement', () => {
  const cover = parseAmendmentCoverPage(RESTATEMENT);
  assert.equal(cover.isAmendment, true);
  assert.equal(cover.amendmentType, 'RESTATEMENT');

  const result = classifyFiling('13F-HR/A', RESTATEMENT);
  assert.equal(result.amendmentType, 'restatement');
  assert.equal(result.strategy, 'replace');
  assert.equal(result.confident, true);
});

test('a real NEW HOLDINGS amendment is classified as additional holdings', () => {
  const cover = parseAmendmentCoverPage(NEW_HOLDINGS);
  assert.equal(cover.isAmendment, true);
  assert.equal(cover.amendmentType, 'NEW HOLDINGS');
  assert.match(cover.reason || '', /Confidential Treatment Expired/i);

  const result = classifyFiling('13F-HR/A', NEW_HOLDINGS);
  assert.equal(result.amendmentType, 'additional_holdings');
  assert.equal(result.strategy, 'merge');
  assert.equal(result.confident, true);
});

test('an original filing is not an amendment', () => {
  const result = classifyFiling('13F-HR', null);
  assert.equal(result.amendmentType, 'original');
  assert.equal(result.strategy, 'replace');
});

test('an amendment with no readable cover page is escalated, never guessed', () => {
  // The old code silently treated this as additional_holdings. Both possible
  // guesses are severely wrong in opposite directions, so neither is taken.
  for (const cover of [null, '', '<xml><unrelated>true</unrelated></xml>']) {
    const result = classifyFiling('13F-HR/A', cover);
    assert.equal(result.amendmentType, 'unknown');
    assert.equal(result.strategy, 'review');
    assert.equal(result.confident, false);
    assert.match(result.reviewReason, /cover page/i);
  }
});

test('an unrecognised amendmentType is escalated and quoted back', () => {
  const result = classifyFiling('13F-HR/A',
    '<isAmendment>true</isAmendment><amendmentInfo><amendmentType>PARTIAL REVISION</amendmentType></amendmentInfo>');
  assert.equal(result.amendmentType, 'unknown');
  assert.equal(result.strategy, 'review');
  assert.match(result.reviewReason, /PARTIAL REVISION/);
});

// ---------------------------------------------------------------------------
// What the classification does to holdings
// ---------------------------------------------------------------------------

const PRIOR = [
  { cusip: '037833100', issuer_name: 'APPLE INC', shares: 1000 },
  { cusip: '594918104', issuer_name: 'MICROSOFT CORP', shares: 500 },
  { cusip: '02079K305', issuer_name: 'ALPHABET INC', shares: 250 },
];

test('a restatement removes a position the manager dropped', () => {
  // The amendment omits Microsoft. After a restatement it must be gone.
  const amendment = [
    { cusip: '037833100', issuer_name: 'APPLE INC', shares: 1200 },
    { cusip: '02079K305', issuer_name: 'ALPHABET INC', shares: 250 },
  ];
  const { strategy } = classifyFiling('13F-HR/A', RESTATEMENT);
  const { rows, applied } = applyAmendment({ strategy, priorRows: PRIOR, amendmentRows: amendment });

  assert.equal(applied, true);
  assert.equal(rows.length, 2);
  assert.equal(rows.some((r) => r.cusip === '594918104'), false,
    'MICROSOFT survived a restatement that dropped it - this is the phantom holding');
  assert.equal(rows.find((r) => r.cusip === '037833100').shares, 1200,
    'the restated share count must win');

  const dropped = droppedPositions({ priorRows: PRIOR, amendmentRows: amendment });
  assert.deepEqual(dropped.map((r) => r.cusip), ['594918104'],
    'the removal should be reported so it is auditable');
});

test('the old merge behaviour is exactly what produces a phantom holding', () => {
  // Demonstrates the defect directly: run a restatement through the merge path
  // the old code always took, and the dropped position is still there.
  const amendment = [{ cusip: '037833100', issuer_name: 'APPLE INC', shares: 1200 }];
  const { rows } = applyAmendment({ strategy: 'merge', priorRows: PRIOR, amendmentRows: amendment });
  assert.equal(rows.some((r) => r.cusip === '594918104'), true);
  assert.equal(rows.length, 3,
    'merging a restatement keeps every dropped position - the bug, stated as a test');
});

test('a NEW HOLDINGS amendment does not erase the original positions', () => {
  // Berkshire's case: confidential treatment expired, so the amendment carries
  // only the withheld names. Replacing on it would delete the whole portfolio.
  const amendment = [{ cusip: '92826C839', issuer_name: 'VISA INC', shares: 900 }];
  const { strategy } = classifyFiling('13F-HR/A', NEW_HOLDINGS);
  const { rows, applied } = applyAmendment({ strategy, priorRows: PRIOR, amendmentRows: amendment });

  assert.equal(applied, true);
  assert.equal(rows.length, 4, 'three original positions plus the newly disclosed one');
  for (const cusip of PRIOR.map((r) => r.cusip)) {
    assert.equal(rows.some((r) => r.cusip === cusip), true, `${cusip} was erased by an additive amendment`);
  }
  assert.equal(rows.some((r) => r.cusip === '92826C839'), true, 'the newly disclosed position is missing');
});

test('an amendment that cannot be classified changes nothing', () => {
  const amendment = [{ cusip: '037833100', issuer_name: 'APPLE INC', shares: 5 }];
  const { strategy } = classifyFiling('13F-HR/A', null);
  const { rows, applied } = applyAmendment({ strategy, priorRows: PRIOR, amendmentRows: amendment });

  assert.equal(applied, false);
  assert.deepEqual(rows, PRIOR, 'the prior report must be left exactly as it was');
});

test('an amendment restating to an empty portfolio empties it', () => {
  // A manager can restate to nothing. Merge would leave the entire portfolio
  // standing, which is the phantom failure in its most extreme form.
  const { rows } = applyAmendment({ strategy: 'replace', priorRows: PRIOR, amendmentRows: [] });
  assert.deepEqual(rows, []);
});

test('an unknown strategy is refused rather than defaulting to one', () => {
  assert.throws(() => applyAmendment({ strategy: 'sensible-guess', priorRows: PRIOR, amendmentRows: [] }),
    /Unknown amendment strategy/);
});

// ---------------------------------------------------------------------------
// Superseding has to reach every surface, not just the ingest path
// ---------------------------------------------------------------------------

/**
 * Correct classification is not enough on its own.
 *
 * A superseded filing keeps its row - when an amendment restates a quarter the
 * earlier version is marked inactive rather than deleted, so what was
 * originally disclosed stays on record. Any surface that loads filings without
 * filtering on is_active therefore reads both versions of that quarter and
 * counts the withdrawn positions alongside the restated ones.
 *
 * The research layer did exactly that: it selected every filing, ordered by
 * report_date, with no is_active predicate, so sector rotation and the backtest
 * read superseded holdings even after classification was fixed. Only
 * same-quarter versions are ever deactivated, so this filter costs no history.
 */
test('every surface that reads filings filters out superseded versions', () => {
  const surfaces = [
    ['research layer (sector rotation, backtest input)', '../services/institutionalResearchLayerService.js'],
    ['screener (combined holdings, heat map, fund performance)', '../services/institutionalScreenerService.js'],
  ];

  for (const [name, path] of surfaces) {
    const source = readFileSync(new URL(path, import.meta.url), 'utf8');
    const selects = [...source.matchAll(/from\('institutional_filings'\)([\s\S]{0,400}?);/g)];
    assert.ok(selects.length, `${name} reads no filings at all - has it moved?`);
    for (const [statement] of selects) {
      assert.match(
        statement,
        /is_active/,
        `${name} loads filings without filtering on is_active, so a restated quarter is counted twice`,
      );
    }
  }
});
