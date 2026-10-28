import test from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';

/**
 * PostgREST caps a response at a thousand rows, and it does so silently: a
 * query that would return five thousand returns one thousand and reports
 * success. That applies to `rpc()` exactly as it applies to `select()`, which
 * is the part that keeps being forgotten - the twelfth occurrence in this
 * codebase was a coverage lookup that returned the alphabetically first
 * thousand tickers and reported them as the whole table. Nothing failed. The
 * run simply repaired the wrong symbols.
 *
 * A comment does not prevent the thirteenth. This does: every set-returning
 * rpc() call must either page or say why it cannot return many rows.
 */

// ../.. from server/tests, so ROOT is the repo and ROOT/server is the tree.
const ROOT = new URL('../../', import.meta.url).pathname;

function sourceFiles(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry.startsWith('.')) continue;
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) { sourceFiles(full, out); continue; }
    if (/\.(js|mjs)$/.test(entry) && !/\.test\.(js|mjs)$/.test(entry)) out.push(full);
  }
  return out;
}

/**
 * Ways a call is legitimately bounded.
 *
 * `.range(` and a paging helper cover the many-row case. `.single()`,
 * `.maybeSingle()` and a head count return one row by construction, and an
 * rpc that takes arguments to act rather than to read - a repair step, an
 * import - returns a status rather than a table.
 */
const BOUNDED = [
  /\.range\(/, /\bpaged\(/, /\ball\(/, /\.single\(\)/, /\.maybeSingle\(\)/,
  /count:\s*'exact'/, /head:\s*true/, /\.limit\(/,
];

test('every set-returning rpc() is paged or bounded', () => {
  const unbounded = [];
  for (const file of sourceFiles(path.join(ROOT, 'server'))) {
    const source = readFileSync(file, 'utf8');
    const lines = source.split('\n');
    lines.forEach((line, index) => {
      if (!/\.rpc\(/.test(line)) return;
      if (line.trim().startsWith('*') || line.trim().startsWith('//')) return;
      // The call can span lines: a builder chain often puts .range() or
      // .order() underneath. Read a small window rather than one line.
      const window = lines.slice(Math.max(0, index - 2), index + 6).join('\n');
      if (BOUNDED.some((pattern) => pattern.test(window))) return;
      // An rpc given arguments is acting, not reading a table.
      if (/\.rpc\([^)]*,\s*\{/.test(window)) return;
      unbounded.push(`${path.relative(ROOT, file)}:${index + 1}  ${line.trim()}`);
    });
  }

  assert.deepEqual(unbounded, [],
    'these rpc() calls can be silently truncated at PostgREST\'s thousand-row cap:\n  '
    + unbounded.join('\n  '));
});

test('the guard would catch the call that prompted it', () => {
  // The exact shape of the bug: an rpc read straight into a destructure, no
  // range, no helper, no limit.
  const offending = "const { data } = await client.rpc('institutional_price_coverage');";
  assert.equal(BOUNDED.some((pattern) => pattern.test(offending)), false);

  // And the shape that replaced it.
  const fixed = "const rows = await all(() => client.rpc('institutional_price_coverage').select('ticker,first_date').order('ticker'));";
  assert.equal(BOUNDED.some((pattern) => pattern.test(fixed)), true);
});
