import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const universe = JSON.parse(readFileSync(new URL('./india-ai-enablers.universe.json', import.meta.url), 'utf8'));
const members = universe.members || [];
const candidates = universe.candidates || [];
const excluded = universe.excluded || [];

test('every lead list reconciles exactly: admitted + held + excluded = the list', () => {
  for (const lead of universe.externalLeads || []) {
    const symbols = new Set(lead.symbols);
    assert.equal(symbols.size, lead.symbols.length, `${lead.id} has duplicate symbols`);
    const placed = (pool) => lead.symbols.filter((s) => pool.some((one) => one.symbol === s));
    const admitted = placed(members);
    const held = placed(candidates);
    const none = placed(excluded);
    assert.equal(admitted.length + held.length + none.length, lead.symbols.length, `${lead.id}: some lead is unplaced`);
    assert.equal(new Set([...admitted, ...held, ...none]).size, lead.symbols.length, `${lead.id}: a lead is in two places`);
    assert.equal(lead.verifiedAgainstSource, false, 'the relayed list must stay marked unverified until someone reads the source');
  }
});

test('no company is in two places', () => {
  const all = [...members, ...candidates, ...excluded].map((one) => one.symbol);
  assert.equal(new Set(all).size, all.length);
});

test('every member is priceable and cites dated, sourced evidence', () => {
  for (const m of members) {
    assert.match(m.instrumentKey || '', /^NSE_EQ\|IN[A-Z0-9]{10}$/, `${m.symbol} instrument key`);
    assert.equal(m.instrumentKey, `NSE_EQ|${m.isin}`, `${m.symbol} key and ISIN disagree`);
    assert.ok((m.admittedOn || []).length > 0, `${m.symbol} has no admitting evidence`);
    for (const e of m.admittedOn) {
      assert.ok(['order', 'capex', 'operating'].includes(e.kind), `${m.symbol}: ${e.kind} cannot admit`);
      assert.match(e.date || '', /^\d{4}-\d{2}-\d{2}$/, `${m.symbol} evidence date`);
      assert.ok(e.source && e.excerpt, `${m.symbol} evidence source/excerpt`);
    }
  }
});

test('membership is dated by decision, never before the evidence it rests on', () => {
  for (const m of members) {
    assert.match(m.membershipStart || '', /^\d{4}-\d{2}-\d{2}$/, `${m.symbol} membershipStart`);
    const earliest = m.admittedOn.map((e) => e.date).sort()[0];
    assert.ok(m.membershipStart >= earliest, `${m.symbol} is a member before its evidence`);
  }
});

test('nothing excluded carries admitting evidence', () => {
  for (const x of excluded) {
    assert.ok(!(x.admittedOn || []).length, `${x.symbol} is excluded but has admitting evidence`);
  }
});

test('each member weight split sums to one and matches its sub-layers', () => {
  for (const m of members) {
    const sum = Object.values(m.weightSplit || {}).reduce((a, b) => a + b, 0);
    assert.ok(Math.abs(sum - 1) < 1e-3, `${m.symbol} weightSplit sums to ${sum}`);
    assert.deepEqual(Object.keys(m.weightSplit).sort(), m.subLayers.map((s) => `${m.layer}_${s}`).sort(), `${m.symbol} weightSplit keys`);
  }
});
