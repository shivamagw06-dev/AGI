/**
 * The data-integrity gate.
 *
 * Repairing amendments quarter by quarter leaves a window in which some history
 * is corrected and some is not, and a consensus figure computed across both is
 * not a figure of anything. These tests pin the two properties that make the
 * gate worth having: it fails closed, and the surfaces that aggregate actually
 * consult it.
 *
 *   node --test server/services/repairGate.test.js
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { stripCommentLines } from '../tests/stripComments.js';

const strip = stripCommentLines;

const holdings = strip(readFileSync(new URL('./institutionalHoldingsService.js', import.meta.url), 'utf8'));
const research = strip(readFileSync(new URL('./institutionalResearchLayerService.js', import.meta.url), 'utf8'));
const repair = strip(readFileSync(new URL('../scripts/repairAmendments.mjs', import.meta.url), 'utf8'));

test('the gate fails closed on every unresolved state', () => {
  const gate = /export async function getRepairStatus[\s\S]*?\n}/.exec(holdings)?.[0];
  assert.ok(gate, 'the gate is gone');

  // Each of these must produce clean:false. A gate that reads clear while
  // filings sit unreviewed is a gate that does nothing.
  for (const state of ['not_started', 'in_progress', 'unknown']) {
    const branch = new RegExp(`status: '${state}',\\s*\\n\\s*clean: false`).test(gate);
    assert.ok(branch, `status '${state}' does not set clean:false`);
  }
  assert.match(gate, /status: 'complete',\s*\n\s*clean: true/,
    'no state can ever report clean, so the banner would never clear');
});

test('a dry run never clears the gate', () => {
  const gate = /export async function getRepairStatus[\s\S]*?\n}/.exec(holdings)?.[0];
  assert.match(gate, /repairApplied/,
    'a dry run repairs nothing; it must not be able to report the history as clean');
});

test('a missing repair table reads as unknown, not clean', () => {
  const gate = /export async function getRepairStatus[\s\S]*?\n}/.exec(holdings)?.[0];
  const rescue = /catch \(error\)[\s\S]*?\}/.exec(gate)?.[0];
  assert.ok(rescue, 'there is no fallback for a missing repair table');
  assert.match(rescue, /clean: false/,
    'before the migration is applied the gate must not report a clean bill of health');
});

test('the aggregate surfaces consult the gate', () => {
  // Consensus and sector rotation both aggregate across managers and quarters,
  // which is exactly what a half-repaired history invalidates.
  assert.match(holdings, /data_integrity: dataIntegrity/,
    'the overview payload does not carry the gate, so consensus cannot be labelled');
  assert.match(research, /data_integrity: dataIntegrity/,
    'sector rotation does not carry the gate');
});

test('both client surfaces render the warning', () => {
  const page = readFileSync(new URL('../../src/pages/InstitutionalHoldingsPage.jsx', import.meta.url), 'utf8');
  const layer = readFileSync(new URL('../../src/components/Research/InstitutionalResearchLayer.jsx', import.meta.url), 'utf8');
  for (const [name, source] of [['holdings browser', page], ['research layer', layer]]) {
    assert.match(source, /data_integrity/, `${name} never reads the gate`);
    assert.match(source, /Historical repair in progress/, `${name} never shows the warning`);
    assert.match(source, /clean === false/,
      `${name} must key off clean, so an unknown or unstarted repair also warns`);
  }
});

test('an unclassifiable amendment is excluded from derived signals, not just flagged', () => {
  const quarantine = /export async function quarantineAmendment[\s\S]*?\n}/.exec(holdings)?.[0];
  assert.ok(quarantine, 'nothing excludes an unclassifiable amendment');
  // The amendment's OWN update must clear is_active. Matching `is_active: false`
  // anywhere in the function is not enough - the successor block sets it too,
  // so a version that only flags the filing still passed.
  assert.match(quarantine, /update\(\{\s*is_active: false,\s*needs_review: true/,
    'the amendment is flagged for review but left active, so it keeps feeding consensus and sector weights');
  assert.equal(/\.delete\(\)/.test(quarantine), false,
    'the raw filing is the audit record and must be preserved');
});

test('quarantining leaves exactly one active filing for the quarter', () => {
  const quarantine = /export async function quarantineAmendment[\s\S]*?\n}/.exec(holdings)?.[0];
  assert.match(quarantine, /successor/,
    'deactivating the amendment without reactivating what it superseded leaves the quarter with no report at all');
  assert.match(quarantine, /orphaned_quarter/,
    'the caller must be told when a quarter has been left with no active filing');
});

test('the repair job excludes on apply and says so on a dry run', () => {
  assert.match(repair, /quarantineAmendment\(/, 'the repair job never excludes anything');
  assert.match(repair, /would be excluded from derived signals/,
    'a dry run must state that it would exclude, so the report matches what --apply does');
});

test('the repair job ends by reporting the gate', () => {
  assert.match(repair, /getRepairStatus\(\)/,
    'the run must end by saying whether the numbers can be published, not only what it touched');
});

test('the integrity gate is never served from the overview cache', () => {
  // The overview payload is cached for five minutes with a stale-while-
  // revalidate fallback. That is fine for consensus, which measures filings
  // that changed hours ago. It is not fine for the gate: it states whether the
  // numbers beside it can be trusted right now.
  //
  // Observed after the repair completed - the script reported the gate as
  // complete while /overview kept serving "historical repair in progress" from
  // cache. The same staleness in the other direction would show a clean bill of
  // health after a repair had failed, which is the version that matters.
  const routes = strip(readFileSync(
    new URL('../routes/institutionalHoldings.js', import.meta.url), 'utf8'));

  const handler = /router\.get\('\/overview'[\s\S]*?\n {2}\}\);/.exec(routes)?.[0];
  assert.ok(handler, 'the overview handler is gone');
  assert.match(handler, /await getRepairStatus\(\)/,
    'the overview handler must read the gate live rather than returning the cached copy');
  assert.match(handler, /data_integrity: dataIntegrity/,
    'the live gate must replace whatever the cached payload carried');

  // And the fallback must keep the cached value rather than dropping the gate,
  // since an absent gate reads as no warning at all.
  assert.match(handler, /data\?\.data_integrity \?\? null/,
    'if the live read fails the cached gate must stand; an absent gate shows no warning');
});
