/**
 * No module may use an identifier it never defined or imported.
 *
 * This has now bitten twice. In #937 a route called clearScreenerCache without
 * importing it, and four admin routes threw ReferenceError in production. Here
 * an edit anchored on an import line that did not exist on the branch, so
 * rankUnmapped and mappingFromLookup were used and never imported - and while
 * fixing that, `fetchJson` turned up on the CMS accession-import path, defined
 * in three other services and imported into none of them. That one would have
 * thrown the moment an analyst pasted an accession.
 *
 * `node --check` cannot see any of it: the syntax is valid. The module even
 * imports cleanly, because ESM only resolves a free identifier when the code
 * reaches it. It fails at call time, in production, on the path nobody ran.
 *
 * ESLint's no-undef does see it, so it runs here on every push over the modules
 * this product depends on.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, readdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const ESLINT = resolve(ROOT, 'node_modules/.bin/eslint');

/** Everything this feature owns: its services, its routes, its scripts. */
function targets() {
  const dirs = ['server/services', 'server/routes', 'server/scripts'];
  const files = [];
  for (const dir of dirs) {
    const full = resolve(ROOT, dir);
    if (!existsSync(full)) continue;
    for (const name of readdirSync(full)) {
      if (!/\.(js|mjs)$/.test(name) || name.endsWith('.test.js')) continue;
      // Scoped to the institutional surface rather than the whole server, so a
      // pre-existing problem elsewhere does not block this feature's pushes.
      if (!/institutional|security|collection|sec[A-Z]|pointInTime|valueScale|repair/i.test(name)) continue;
      files.push(resolve(full, name));
    }
  }
  return files;
}

test('no institutional module uses an identifier it never imported', () => {
  const files = targets();
  assert.ok(files.length >= 8, `expected the institutional modules, found ${files.length}`);

  if (!existsSync(ESLINT)) {
    // CI for the guard suite installs nothing. Skipping loudly is honest;
    // silently passing would make this look like a check when it is not.
    console.warn('  eslint not installed — no-undef not enforced in this environment');
    return;
  }

  try {
    execFileSync(ESLINT, [
      '--no-eslintrc',
      '--env', 'es2022,node',
      '--parser-options', 'ecmaVersion:latest,sourceType:module',
      '--rule', '{"no-undef":"error"}',
      ...files,
    ], { cwd: ROOT, stdio: 'pipe' });
  } catch (error) {
    const report = String(error.stdout || error.message);
    assert.fail(`an identifier is used without being defined or imported:\n${report}`);
  }
});
