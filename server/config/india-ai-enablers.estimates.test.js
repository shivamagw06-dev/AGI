import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const read = async (name) => JSON.parse(await readFile(new URL(`./${name}`, import.meta.url), 'utf8'));

test('every estimate is a member, and every input says where it comes from', async () => {
  const universe = await read('india-ai-enablers.universe.json');
  const est = await read('india-ai-enablers.estimates.json');
  const members = new Set(universe.members.map((m) => m.symbol));
  const types = new Set(['growBase', 'contract', 'target', 'capacity', 'osat', 'marketShare']);
  for (const model of est.models) {
    assert.ok(members.has(model.symbol), `${model.symbol} is not a member`);
    assert.ok(types.has(model.type), `${model.symbol} type ${model.type}`);
    assert.ok(model.basis, `${model.symbol} needs a basis`);
    for (const [name, p] of Object.entries(model.params)) {
      assert.ok(p.label && p.unit, `${model.symbol}.${name} label/unit`);
      if (p.kind === 'disclosed') {
        assert.ok(Number.isFinite(p.value) && p.source, `${model.symbol}.${name}: a disclosed input needs a value and a source`);
      } else {
        assert.equal(p.kind, 'assumption', `${model.symbol}.${name} kind`);
        assert.ok(p.rationale, `${model.symbol}.${name}: an assumption needs a reason`);
        if (p.value !== null) assert.ok(p.low <= p.value && p.value <= p.high, `${model.symbol}.${name}: low <= base <= high`);
      }
    }
    assert.equal(model.params.totalEbitdaFY26Cr?.kind, 'disclosed', `${model.symbol}: materiality needs a filed figure`);
  }
});

test('no estimate uses a broker figure', async () => {
  const text = await readFile(new URL('./india-ai-enablers.estimates.json', import.meta.url), 'utf8');
  assert.doesNotMatch(text, /goldman|consensus/i);
});
