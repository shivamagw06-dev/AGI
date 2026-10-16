import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const read = async (name) => JSON.parse(await readFile(new URL(`./${name}`, import.meta.url), 'utf8'));

test('every member has a materiality entry, and nothing else does', async () => {
  const universe = await read('india-ai-enablers.universe.json');
  const mat = await read('india-ai-enablers.materiality.json');
  const members = universe.members.map((m) => m.symbol).sort();
  assert.deepEqual(Object.keys(mat.members).sort(), members);
  for (const s of Object.keys(mat.vehicles || {})) assert.ok(members.includes(s), `vehicle for non-member ${s}`);
  for (const e of mat.exceptions || []) assert.ok(members.includes(e.symbol) && e.reason && e.decided, 'an exception needs a member, a reason and a date');
});

test('every qualifying figure names its basis and source, and arithmetic shows its steps', async () => {
  const mat = await read('india-ai-enablers.materiality.json');
  for (const [symbol, entry] of Object.entries(mat.members)) {
    if (!(entry.facts || []).length) assert.ok(entry.note, `${symbol} has no figures and no note saying why`);
    for (const f of entry.facts || []) {
      assert.ok(['amount', 'share', 'contracted'].includes(f.test), `${symbol} test ${f.test}`);
      assert.ok(['D', 'I'].includes(f.basis), `${symbol}: a qualifying figure is disclosed or arithmetic, never an estimate`);
      assert.ok(f.label && (f.source || f.steps), `${symbol} ${f.label}: no source`);
      if (f.basis === 'I') assert.ok(f.steps, `${symbol} ${f.label}: arithmetic without steps`);
      if (f.test === 'amount') assert.ok(Number.isFinite(f.valueCr) && f.valueCr > 0, `${symbol} amount`);
      if (f.test === 'share') assert.ok(f.share > 0 && f.share <= 1, `${symbol} share`);
      if (f.test === 'contracted') {
        assert.ok(Number.isFinite(f.mw) && typeof f.customerNamed === 'boolean', `${symbol} contracted`);
        assert.equal(typeof f.representative, 'boolean', `${symbol}: say whether capacity is a representative denominator for this company`);
      }
    }
    if (entry.path) assert.ok(['revenue', 'stated', 'judged'].includes(entry.path.kind) && entry.path.note, `${symbol} path`);
  }
});

test('the rules are the ones decided, and no broker figure appears', async () => {
  const raw = await readFile(new URL('./india-ai-enablers.materiality.json', import.meta.url), 'utf8');
  const mat = JSON.parse(raw);
  assert.equal(mat.rules.amountCr, 100);
  assert.equal(mat.rules.revenueShare, 0.05);
  assert.equal(mat.rules.fy29EbitdaShare, 0.05);
  assert.deepEqual(mat.rules.evidenceBands, ['medium', 'high']);
  assert.doesNotMatch(raw, /goldman|consensus estimate/i);
});
