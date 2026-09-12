import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./intelligence.js', import.meta.url), 'utf8');

test('company dossier gateway exposes read and OpenAI generation routes', () => {
  assert.match(source, /router\.get\('\/company-dossier'/);
  assert.match(source, /router\.get\('\/company-dossier\/:ticker'/);
  assert.match(source, /router\.post\('\/company-dossier\/:ticker\/generate'/);
  assert.match(source, /timeoutMs: 120_000/);
});
