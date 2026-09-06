/**
 * The guard suite must not need node_modules.
 *
 * The safety-guard workflow installs no dependencies - that is what lets it run
 * on every push in seconds. Twice now a test has been added that imports a
 * module which imports the Supabase client, and CI failed with "Cannot find
 * package '@supabase/supabase-js'". Both times it passed locally, because a
 * developer machine has the packages installed.
 *
 * The second time it passed even with node_modules moved aside, because this
 * repository has two of them - one at the root and one under server/ - and only
 * the first had been moved. A check that can be defeated by forgetting a
 * directory is not a check.
 *
 * So this walks the import graph statically instead. Every test the workflow
 * runs, and everything those tests reach through relative imports, may import
 * only node: builtins. A bare specifier anywhere in that graph fails here,
 * naming the file and the chain that reaches it.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const WORKFLOW = resolve(ROOT, '.github/workflows/institutional-safety-guards.yml');

/** Every test file the guard workflow runs. */
function suiteFiles() {
  const yml = readFileSync(WORKFLOW, 'utf8');
  return [...yml.matchAll(/node --test (\S+\.test\.js)/g)].map((m) => resolve(ROOT, m[1]));
}

const IMPORT = /^\s*(?:import|export)[\s\S]*?from\s*['"]([^'"]+)['"]|import\s*\(\s*['"]([^'"]+)['"]\s*\)/gm;

function importsOf(file) {
  const src = readFileSync(file, 'utf8');
  const out = [];
  for (const m of src.matchAll(IMPORT)) out.push(m[1] || m[2]);
  return out.filter(Boolean);
}

test('the guard workflow lists test files that exist', () => {
  const files = suiteFiles();
  assert.ok(files.length >= 5, `expected the workflow to run several suites, found ${files.length}`);
  for (const f of files) {
    assert.doesNotThrow(() => readFileSync(f, 'utf8'),
      `${relative(ROOT, f)} is referenced by the workflow but does not exist`);
  }
});

test('nothing the guard suite imports needs a package installed', () => {
  const seen = new Set();
  const offences = [];

  const walk = (file, chain) => {
    if (seen.has(file)) return;
    seen.add(file);
    for (const spec of importsOf(file)) {
      if (spec.startsWith('node:')) continue;
      if (spec.startsWith('.')) {
        // Relative: follow it.
        let target = resolve(dirname(file), spec);
        if (!target.endsWith('.js') && !target.endsWith('.mjs')) target += '.js';
        try { readFileSync(target, 'utf8'); } catch { continue; }
        walk(target, [...chain, relative(ROOT, file)]);
        continue;
      }
      // A bare specifier resolves through node_modules, which CI does not have.
      offences.push({
        package: spec,
        file: relative(ROOT, file),
        via: chain.length ? chain.join(' -> ') : '(directly in the suite)',
      });
    }
  };

  for (const f of suiteFiles()) walk(f, []);

  assert.deepEqual(offences, [],
    'the guard workflow installs no dependencies, so these imports will fail in CI:\n'
    + offences.map((o) => `  ${o.package}  in ${o.file}\n    reached via ${o.via}`).join('\n'));
});
