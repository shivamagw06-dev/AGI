import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const read = async (name) => JSON.parse(await readFile(new URL(`./${name}`, import.meta.url), 'utf8'));

test('scoring rows are members, with sane magnitudes', async () => {
  const universe = await read('india-ai-enablers.universe.json');
  const s = await read('india-ai-enablers.scoring.json');
  const members = new Set(universe.members.map((m) => m.symbol));
  const seen = new Set();
  for (const r of s.rows) {
    assert.ok(members.has(r.symbol), `${r.symbol} is not a member`);
    assert.ok(!seen.has(r.symbol), `${r.symbol} twice`); seen.add(r.symbol);
    for (const k of ['revenueFY26', 'revenueQ1FY27', 'revenueQ1FY26', 'capexFY26']) {
      assert.ok(r[k] === null || r[k] === undefined || (Number.isFinite(r[k]) && r[k] >= 0), `${r.symbol}.${k}`);
    }
    if (r.statedRoceFY26 != null) assert.ok(r.statedRoceFY26 > -1 && r.statedRoceFY26 < 1, `${r.symbol} ROCE as a fraction`);
    if (r.revenueQ1FY27 && r.revenueFY26) assert.ok(r.revenueQ1FY27 < r.revenueFY26, `${r.symbol}: a quarter is less than a year`);
  }
});
