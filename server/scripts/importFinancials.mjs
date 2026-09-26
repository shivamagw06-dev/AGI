#!/usr/bin/env node
/**
 * Load financial statements from a structured file.
 *
 *   node scripts/importFinancials.mjs --file statements.json
 *   node scripts/importFinancials.mjs --file statements.csv --apply
 *
 * Reads a JSON array or a CSV with a header row. Nothing is written without
 * --apply, and nothing is written at all if any row fails to read: a file
 * half-loaded is a company whose 2024 is present and whose 2025 is missing,
 * which computes growth against the wrong year rather than refusing.
 *
 * Statements are imported rather than parsed out of an annual report on
 * purpose. A reader that guesses at footnotes, restatements and currencies is
 * the highest-fabrication-risk thing this codebase could contain.
 */
import { readFileSync } from 'node:fs';
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { readFinancials } from '../services/companyFinancialsImport.js';

const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const FILE = argOf('--file');
const APPLY = process.argv.includes('--apply');

if (!FILE) {
  console.error('[fin] --file is required.');
  process.exit(64);
}
if (!getSupabaseAdminCredentials()) {
  console.error('[fin] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}

/** A CSV with a header row. Quoted fields may contain commas. */
function fromCsv(text) {
  const lines = text.split(/\r?\n/).filter((line) => line.trim());
  if (!lines.length) return [];
  const split = (line) => {
    const cells = [];
    let cell = '';
    let quoted = false;
    for (let at = 0; at < line.length; at += 1) {
      const ch = line[at];
      if (quoted && ch === '"' && line[at + 1] === '"') { cell += '"'; at += 1; continue; }
      if (ch === '"') { quoted = !quoted; continue; }
      if (ch === ',' && !quoted) { cells.push(cell); cell = ''; continue; }
      cell += ch;
    }
    cells.push(cell);
    return cells;
  };
  const header = split(lines[0]).map((name) => name.trim().toLowerCase());
  return lines.slice(1).map((line) => {
    const cells = split(line);
    return Object.fromEntries(header.map((name, at) => [name, cells[at]]));
  });
}

const text = readFileSync(FILE, 'utf8');
const raw = FILE.toLowerCase().endsWith('.csv') ? fromCsv(text) : JSON.parse(text);
const { rows, errors } = readFinancials(
  raw.map((row) => ({ source_file: FILE.split('/').pop(), ...row })),
);

console.log(`[fin] ${raw.length} row${raw.length === 1 ? '' : 's'} read, ${rows.length} valid.`);
if (errors.length) {
  console.error(`\n[fin] ${errors.length} row${errors.length === 1 ? '' : 's'} rejected:`);
  for (const why of errors) console.error(`  ${why}`);
  console.error('\n[fin] Nothing was written. A file half-loaded computes growth against');
  console.error('[fin] the wrong year instead of refusing, so every row must read first.');
  process.exit(65);
}

const byTicker = new Map();
for (const row of rows) byTicker.set(row.ticker, (byTicker.get(row.ticker) || 0) + 1);
for (const [ticker, count] of [...byTicker].sort()) {
  const periods = rows.filter((row) => row.ticker === ticker);
  const scales = [...new Set(periods.map((row) => `${row.currency} x${row.scale}`))];
  console.log(`  ${ticker.padEnd(14)} ${String(count).padStart(3)} period(s)  ${scales.join(', ')}`);
  // Named rather than merged. Two scales for one company is legitimate across
  // a currency change and is otherwise a file that will produce a
  // thousand-fold error the first time two periods are compared.
  if (scales.length > 1) console.log(`  ${' '.repeat(14)}     note: more than one currency or scale`);
}

if (!APPLY) {
  console.log('\n[fin] Dry run. Re-run with --apply to write.');
  process.exit(0);
}

const client = createSupabaseAdmin();
for (let at = 0; at < rows.length; at += 250) {
  const chunk = rows.slice(at, at + 250);
  const { error } = await client.from('company_financials')
    .upsert(chunk, { onConflict: 'ticker,period_end,period_type,basis' });
  if (error) {
    console.error(`[fin] storing rows ${at + 1}-${at + chunk.length}: ${error.message}`);
    process.exit(70);
  }
}
console.log(`\n[fin] Stored ${rows.length} period(s).`);
