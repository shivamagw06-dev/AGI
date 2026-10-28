import test from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';

/**
 * A function's output columns are part of its return type.
 *
 * `create or replace function` cannot change a return type. Adding one column
 * to a `returns table (...)` is a type change, and Postgres refuses the whole
 * migration with "cannot change return type of existing function". The
 * argument list does not have to change for this to happen, which is what
 * makes it easy to miss: the drop was remembered when the arguments last
 * changed and forgotten when only the columns did.
 *
 * Nothing catches it before the migration is pasted into a live database and
 * errors there - the file is valid SQL and the test suite never executes it.
 * This does: if a migration redefines a function that an earlier migration
 * already defined, and the column list differs, that migration has to drop it
 * first.
 */

const MIGRATIONS = new URL('../../supabase/migrations/', import.meta.url).pathname;

/** Every `returns table` definition in one file, in order. */
function definitions(sql) {
  const found = [];
  const pattern = /create\s+(?:or\s+replace\s+)?function\s+([a-z0-9_.]+)\s*\(([\s\S]*?)\)\s*returns\s+table\s*\(([\s\S]*?)\)\s*language/gi;
  for (const match of sql.matchAll(pattern)) {
    const columns = match[3]
      .split(',')
      .map((line) => line.replace(/--[^\n]*/g, '').trim().split(/\s+/)[0])
      .filter(Boolean);
    found.push({ name: match[1].replace(/^public\./, ''), columns });
  }
  return found;
}

test('a migration that changes a function\'s output columns drops it first', () => {
  const files = readdirSync(MIGRATIONS).filter((name) => name.endsWith('.sql')).sort();
  const previous = new Map();
  const problems = [];

  for (const file of files) {
    const sql = readFileSync(path.join(MIGRATIONS, file), 'utf8');
    for (const { name, columns } of definitions(sql)) {
      const before = previous.get(name);
      previous.set(name, columns);
      // First definition of this function: nothing to drop.
      if (!before) continue;
      if (before.join('|') === columns.join('|')) continue;
      // The bare name is enough - a drop naming any signature of it means the
      // author was thinking about the replacement.
      const dropped = new RegExp(`drop\\s+function[^;]*${name.replace('.', '\\.')}`, 'i').test(sql);
      if (!dropped) {
        problems.push(
          `${file}: ${name} changes its output columns from [${before.join(', ')}] `
          + `to [${columns.join(', ')}] without dropping the old definition first. `
          + 'Postgres will refuse this with "cannot change return type of existing function".',
        );
      }
    }
  }

  assert.deepEqual(problems, [], `\n${problems.join('\n')}`);
});

test('the guard can see the definitions it is meant to check', () => {
  // A parser that silently matches nothing would make the test above pass for
  // the wrong reason - the failure mode this whole file exists to prevent.
  const files = readdirSync(MIGRATIONS).filter((name) => name.endsWith('.sql'));
  const all = files.flatMap((file) => definitions(readFileSync(path.join(MIGRATIONS, file), 'utf8')));
  assert.ok(all.length > 0, 'no returns-table function found in any migration');
  const metrics = all.filter((row) => row.name === 'institutional_strategy_metrics');
  assert.ok(metrics.length >= 2, 'expected the strategy metrics function to be defined more than once');
  assert.ok(metrics.at(-1).columns.includes('prior_report_date'));
});
