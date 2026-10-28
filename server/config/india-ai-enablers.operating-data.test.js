import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const read = async (name) => JSON.parse(await readFile(new URL(`./${name}`, import.meta.url), 'utf8'));

test('every order book and capacity row is a member, dated and quoted', async () => {
  const universe = await read('india-ai-enablers.universe.json');
  const data = await read('india-ai-enablers.operating-data.json');
  const members = new Set(universe.members.map((m) => m.symbol));
  for (const row of [...data.orderBooks, ...data.dataCentreCapacity]) {
    assert.ok(members.has(row.symbol), `${row.symbol} is not a member`);
    assert.match(row.asOf, /^\d{4}-\d{2}-\d{2}$/, `${row.symbol} asOf`);
    assert.ok(row.document && row.quote, `${row.symbol} needs a document and a quote`);
  }
  for (const row of data.orderBooks) {
    for (const key of ['backlogCr', 'intakeCr']) {
      assert.ok(row[key] === null || (Number.isFinite(row[key]) && row[key] > 0), `${row.symbol} ${key}`);
    }
    assert.ok(row.backlogCr !== null || row.basisNote, `${row.symbol}: no backlog needs a basis note`);
  }
  for (const row of data.dataCentreCapacity) {
    for (const key of ['operationalMW', 'underConstructionMW', 'tiedUpMW']) {
      assert.ok(row[key] === null || (Number.isFinite(row[key]) && row[key] >= 0), `${row.symbol} ${key}`);
    }
  }
});

test('evidence found after admission is dated, sourced and quoted', async () => {
  const universe = await read('india-ai-enablers.universe.json');
  for (const m of universe.members) {
    for (const e of m.supportingEvidence || []) {
      assert.ok(['order', 'capex', 'operating'].includes(e.kind), `${m.symbol}: ${e.kind}`);
      assert.match(e.date || '', /^\d{4}-\d{2}-\d{2}$/, `${m.symbol} supporting evidence date`);
      assert.ok(e.document && e.source && e.excerpt, `${m.symbol} supporting evidence fields`);
    }
  }
});
