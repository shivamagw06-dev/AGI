#!/usr/bin/env node
/**
 * Paste a manager's publication and pull the facts out of it.
 *
 *   node server/scripts/importPublication.mjs --manager berkshire-hathaway \
 *     --title "2025 Annual Report" --as-of 2025-12-31
 *   ... paste the document, then press Ctrl-D
 *
 *   node server/scripts/importPublication.mjs --manager berkshire-hathaway \
 *     --title "2025 Annual Report" --as-of 2025-12-31 --file report.txt --apply
 *
 * Reads from a file or from standard input, so pasting into the terminal works
 * without a page to paste into.
 *
 * The manager and the title are given rather than detected. A quarterly letter
 * carries no CIK, no fiscal-year header and no title in any fixed place -
 * Berkshire's annual report happens to carry all three and is the exception,
 * not the pattern. Guessing which manager wrote a document would be inventing
 * the one fact everything else hangs off.
 *
 * The document is not stored. It is the manager's own writing and its own
 * copyright; what is kept is each extracted fact and the line it came from.
 *
 * Facts are stored pending. A table is more reliable than prose and neither is
 * good enough to publish unreviewed.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { paged } from '../services/institutionalResearchLayerService.js';
import { extractDisclosedHoldings, documentDigest } from '../services/publicationFacts.js';

const APPLY = process.argv.includes('--apply');
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const MANAGER = argOf('--manager');
const TITLE = argOf('--title');
const AS_OF = argOf('--as-of');
const SOURCE_URL = argOf('--source-url');
const FILE = argOf('--file');

if (!getSupabaseAdminCredentials()) {
  console.error('[pub] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
if (!MANAGER || !TITLE) {
  console.error('[pub] --manager <slug> and --title "..." are required.');
  console.error('[pub] The manager is not detected from the document; a letter does not name itself.');
  process.exit(64);
}
const client = createSupabaseAdmin();

async function readInput() {
  if (FILE) return readFileSync(FILE, 'utf8');
  if (process.stdin.isTTY) {
    console.log('[pub] paste the document, then press Ctrl-D:\n');
  }
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString('utf8');
}

const money = (value, unit) => {
  if (value === null || value === undefined) return '-';
  const suffix = unit ? ` ${unit}` : ' (unit not stated)';
  return `${Number(value).toLocaleString('en-US')}${suffix}`;
};

async function main() {
  const [manager] = await paged(
    () => client.from('institutional_managers').select('id, slug, display_name')
      .eq('slug', MANAGER),
    { label: 'manager' },
  );
  if (!manager) {
    console.error(`[pub] no active manager with slug "${MANAGER}".`);
    process.exit(65);
  }

  const text = await readInput();
  if (!text.trim()) {
    console.error('[pub] nothing was pasted.');
    process.exit(65);
  }
  const digest = documentDigest(text, (value) => createHash('sha256').update(value).digest('hex'));
  const facts = extractDisclosedHoldings(text);

  console.log(`\n[pub] ${manager.display_name} - ${TITLE}`);
  console.log(`[pub] ${text.length.toLocaleString()} characters, digest ${digest.slice(0, 12)}`);
  console.log(`[pub] ${facts.length} disclosed holding(s) found\n`);

  if (!facts.length) {
    // The honest limit, stated rather than left as an empty result to puzzle
    // over. This reads tables; a letter written in sentences yields nothing.
    console.log('[pub] No holdings table matched. This extractor reads tables of the shape');
    console.log('[pub]   <issuer> <percent>% <cost> <market value> <dividends>');
    console.log('[pub] and returns nothing for prose, rather than returning something wrong.');
    return;
  }

  const pad = (value, width) => String(value ?? '-').padEnd(width);
  console.log(`${pad('issuer', 34)}${pad('owned', 8)}${pad('cost', 22)}${pad('market value', 22)}dividends`);
  for (const fact of facts) {
    console.log(pad(fact.issuer.slice(0, 32), 34)
      + pad(`${fact.percent_owned}%`, 8)
      + pad(money(fact.cost_basis, fact.unit), 22)
      + pad(money(fact.market_value, fact.unit), 22)
      + money(fact.dividends, fact.unit));
  }

  const unstated = facts.filter((fact) => !fact.unit);
  if (unstated.length) {
    console.log(`\n[pub] ${unstated.length} row(s) have no declared unit. The figures are stored as`);
    console.log('[pub] written and nothing downstream will scale them. Check the document for a');
    console.log('[pub] "(Dollars in millions)" line above the table before approving those.');
  }

  if (!APPLY) {
    console.log('\n[pub] dry run only. Re-run with --apply to store these as pending facts.');
    return;
  }

  const { data: publication, error: pError } = await client.from('manager_publications')
    .upsert({
      manager_id: manager.id,
      title: TITLE,
      as_of_date: AS_OF || null,
      source_url: SOURCE_URL || null,
      digest,
    }, { onConflict: 'digest' })
    .select()
    .single();
  if (pError) throw new Error(`recording the publication: ${pError.message}`);

  const rows = facts.map((fact) => ({
    publication_id: publication.id,
    manager_id: manager.id,
    kind: fact.kind,
    issuer: fact.issuer,
    percent_owned: fact.percent_owned,
    cost_basis: fact.cost_basis,
    market_value: fact.market_value,
    dividends: fact.dividends,
    unit: fact.unit,
    source_excerpt: fact.source_excerpt,
  }));
  const { error: fError } = await client.from('manager_publication_facts')
    .upsert(rows, { onConflict: 'publication_id,source_excerpt' });
  if (fError) throw new Error(`storing facts: ${fError.message}`);

  console.log(`\n[pub] ${rows.length} fact(s) stored as pending against publication ${publication.id}`);
  console.log('[pub] Nothing reaches the page until a person approves them.');
}

main().catch((error) => {
  console.error(`[pub] ${error.message}`);
  process.exit(1);
});
