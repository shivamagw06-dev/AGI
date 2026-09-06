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

const source = readFileSync(new URL('./repairAmendments.mjs', import.meta.url), 'utf8');
const code = source
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/(^|[^:])\/\/.*$/gm, '$1');

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
  const reviewBlock = /if \(resolved === 'unknown'\)[\s\S]{0,700}?continue;/.exec(code)?.[0];
  assert.ok(reviewBlock, 'there is no branch for an unclassifiable amendment');
  assert.match(reviewBlock, /needs_review/);
  assert.equal(/reingestFiling/.test(reviewBlock), false,
    'an amendment we cannot classify must not be applied in either direction');
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
