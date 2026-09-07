/**
 * Safety properties of the amendment repair job.
 *
 * This script overwrites holdings for every quarter that carries an amendment,
 * so the properties worth pinning are not what it computes - that is
 * secAmendment.js, tested separately against real filings - but what it refuses
 * to do: write without being asked, overwrite without archiving first, and
 * report only the filings it happened to change.
 *
 *   node --test server/scripts/repairAmendments.test.js
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { stripCommentLines } from '../tests/stripComments.js';

const source = readFileSync(new URL('./repairAmendments.mjs', import.meta.url), 'utf8');
const code = stripCommentLines(source);

test('the job is a dry run unless --apply is passed', () => {
  assert.match(code, /const APPLY = args\.includes\('--apply'\)/,
    'writing must be opt-in; a repair that runs by default is one nobody chose');
  // Every write path has to be behind it.
  for (const guard of [/if \(!APPLY\)/, /if \(APPLY/]) {
    assert.match(code, guard, 'APPLY is parsed but never gates anything');
  }
});

test('it refuses to start without database credentials', () => {
  const check = code.indexOf('SUPABASE_SERVICE_ROLE_KEY');
  // The call site, not the import at the top of the file.
  const firstWrite = code.indexOf('await previewFilingRepair(');
  assert.ok(check !== -1 && check < firstWrite,
    'credentials must be checked before any EDGAR fetch, or a config error costs the rate budget');
});

test('holdings are archived before anything overwrites them', () => {
  // Ordering is the property. Re-ingesting first and archiving after preserves
  // the repaired state, which is not an audit record of anything.
  const archiveCall = code.indexOf('await archive(');
  const reingestCall = code.indexOf('await reingestFiling(');
  assert.ok(archiveCall !== -1, 'nothing is archived at all');
  assert.ok(reingestCall !== -1, 'nothing is re-ingested at all');
  assert.ok(archiveCall < reingestCall,
    'the re-ingest runs before the archive, so the pre-repair rows are lost');
});

test('the archive stores the whole row, not a projection of it', () => {
  assert.match(code, /holding,/,
    'the archive must keep the row as it stood; a normalised copy stops being an audit record after the next schema change');
});

test('a quarter is replayed in acceptance order, not amendment-only', () => {
  // Re-ingesting only the amendment leaves the merged rows from the original
  // in place, so the phantom positions survive the repair.
  assert.match(code, /filingsForQuarter\(/,
    'the repair must replay the whole quarter, not just the amendment');
  assert.match(code, /for \(const filing of chain\) await reingestFiling\(filing\.id\)/,
    'the chain must be replayed in order');
});

test('every filing examined is recorded, not only the ones that changed', () => {
  // "We looked at 47 amendments, 12 were wrong" is verifiable.
  // "12 amendments were wrong" is not.
  for (const outcome of ['unchanged', 'needs_review', 'failed', 'repaired', 'would_repair']) {
    assert.ok(code.includes(`'${outcome}'`), `outcome ${outcome} is never recorded`);
  }
});

test('an unclassifiable amendment is reported for review, never repaired', () => {
  // Sized to the block itself rather than a fixed window: the branch grew when
  // quarantine was added, and a window that silently overruns into the next
  // branch stops testing this one.
  const opened = code.indexOf("if (resolved === 'unknown')");
  assert.ok(opened !== -1, 'there is no branch for an unclassifiable amendment');
  const reviewBlock = code.slice(opened, code.indexOf('continue;', opened));

  assert.match(reviewBlock, /needs_review/);
  assert.equal(/reingestFiling/.test(reviewBlock), false,
    'an amendment we cannot classify must not be applied in either direction');
  assert.match(reviewBlock, /quarantineAmendment/,
    'recording that it needs review does not stop it counting - it must also be excluded from derived signals');
});

test('signals are rebuilt after holdings change, and only when they changed', () => {
  const rebuild = /if \(APPLY && totals\.repaired\)[\s\S]{0,400}?rebuildInstitutionalSignals\(\)/.exec(code);
  assert.ok(rebuild, 'signals are materialised from holdings and go stale the moment holdings are repaired');
});

test('a failed filing does not abort the run', () => {
  // One unfetchable filing must not strand every later quarter unrepaired.
  assert.match(code, /catch \(error\) \{[\s\S]{0,600}?totals\.failed \+= 1/);
  assert.match(code, /process\.exit\(totals\.failed \? 1 : 0\)/,
    'failures must still surface in the exit code');
});

test('the prior version is found regardless of which filing is active', () => {
  // Ingesting an amendment makes it the active filing and deactivates the
  // report it supersedes, so a lookup filtered on is_active excludes the very
  // filing it is looking for. That returned null for every amendment in the
  // database: removals reported zero while row counts dropped by hundreds, and
  // strategy fell through to replace regardless of the cover page - which would
  // erase valid positions on an additive amendment.
  // Raw source: the block extracted below contains no comments, and this
  // branch does not carry the shared comment stripper.
  const service = readFileSync(
    new URL('../services/institutionalHoldingsService.js', import.meta.url), 'utf8');
  const preview = /export async function previewFilingRepair[\s\S]*?\n}/.exec(service)?.[0];
  assert.ok(preview, 'previewFilingRepair is gone');

  const lookup = /const \{ data: previousVersion \}[\s\S]*?maybeSingle\(\);/.exec(preview)?.[0];
  assert.ok(lookup, 'the prior-version lookup is gone');
  assert.equal(/is_active/.test(lookup), false,
    'the prior-version lookup filters on is_active, so it can never find the filing the amendment superseded');
});

test('removals are measured against the rows stored today', () => {
  // Raw source: the block extracted below contains no comments, and this
  // branch does not carry the shared comment stripper.
  const service = readFileSync(
    new URL('../services/institutionalHoldingsService.js', import.meta.url), 'utf8');
  const preview = /export async function previewFilingRepair[\s\S]*?\n}/.exec(service)?.[0];
  assert.match(preview, /currentRows/,
    'removals must be computed against what is stored now - that is what a client sees and what would disappear');
  assert.match(preview, /const goingAway = currentRows\.filter/,
    'what disappears must be derived from the rows stored now, not from the prior version');
});

test('the report refuses to print counts that do not reconcile', () => {
  assert.match(code, /do not reconcile/,
    'a report that prints "0 removed" beside a 257-row drop invites someone to trust the smaller number');
});

test('a restated row is not reported as a divestment', () => {
  // filingKey is cusip|class|shareType|putCall and carries no value, so a
  // restatement that re-reports the same security with corrected figures drops
  // the old row and adds a new one. At row level that looks exactly like a sale.
  //
  // H&H International's Q4-2024 restatement is the case: the report named
  // APPLE, BERKSHIRE, ALPHABET, PDD and OCCIDENTAL as removed when all five are
  // in the amendment SEC filed. A reviewer reading that would refuse to approve
  // the repair, and would be right to.
  const service = readFileSync(
    new URL('../services/institutionalHoldingsService.js', import.meta.url), 'utf8');
  const preview = /export async function previewFilingRepair[\s\S]*?\n}/.exec(service)?.[0];
  assert.ok(preview, 'previewFilingRepair is gone');

  assert.match(preview, /survivingSecurities/,
    'removals must be judged on whether the SECURITY survives, not whether the row key does');
  assert.match(preview, /const superseded = goingAway\.filter/,
    'rows replaced by a restated version of the same security must be reported separately');

  // The two sets must be disjoint and cover everything that goes away.
  assert.match(preview, /const removed = goingAway\.filter\(\s*\n?\s*\(row\) => !survivingSecurities/,
    'removed must be the complement of superseded over the same set');
});

test('the report names divestments and only counts restatements', () => {
  assert.match(code, /divested:/, 'genuine divestments must be named');
  assert.match(code, /restated in place/,
    'restated rows must be summarised, not listed as if the position were sold');
  assert.match(code, /positions divested:/, 'the totals must distinguish the two');
  assert.match(code, /rows restated:/);
});
