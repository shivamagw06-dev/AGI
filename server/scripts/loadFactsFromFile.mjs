#!/usr/bin/env node
/**
 * Facts extracted somewhere else, written here.
 *
 *   node scripts/loadFactsFromFile.mjs --file data/facts/reliance-ten-year-highlights.json
 *   node scripts/loadFactsFromFile.mjs --file ... --apply
 *
 * Extraction needs the document and the database needs credentials, and those
 * are not always in the same place. A source PDF too large to keep on the
 * server can be read where it is, and the facts it produced brought here.
 *
 * What that costs is worth stating. The citation checks - the value appears in
 * the sentence, the sentence appears in the document - ran where the document
 * was, and cannot run again here without it. This script re-checks only what
 * it can: that every fact is shaped for the table and would not be refused by
 * it. A file whose figures were edited after extraction would pass. Each fact
 * carries the sentence it was read from, so any figure can be checked against
 * the report by hand, and the dry run prints them for exactly that reason.
 */
import fs from 'fs';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { saveFacts, unwritable } from '../services/factStore.js';

const args = process.argv.slice(2);
const flag = (name, fallback = null) => {
  const at = args.indexOf(name);
  return at === -1 || at === args.length - 1 ? fallback : args[at + 1];
};
const apply = args.includes('--apply');
const file = flag('--file');
if (!file) { console.error('--file is required.'); process.exit(1); }

const read = JSON.parse(fs.readFileSync(file, 'utf8'));
const facts = Array.isArray(read) ? read : read.facts;
if (!Array.isArray(facts)) { console.error('the file holds no facts array.'); process.exit(1); }

if (read.source) {
  console.log(`from        ${read.source.pdf ?? 'unknown'}${read.source.page ? `, page ${read.source.page}` : ''}`);
  console.log(`document    ${read.source.reported_in_document ?? 'unknown'}`);
  console.log(`extracted   ${read.source.extracted_at ?? 'unknown'}`);
}

const problems = facts.map((fact, at) => ({ at, fact, problems: unwritable(fact) }))
  .filter((one) => one.problems.length);
const cited = facts.filter((fact) => fact.source_sentence).length;

console.log(`facts       ${facts.length}`);
console.log(`citing a sentence  ${cited}`);
console.log(`would be refused   ${problems.length}`);
for (const one of problems.slice(0, 20)) {
  console.log(`  ${one.fact.definition_id} ${one.fact.period_end}: ${one.problems.join(', ')}`);
}

if (!apply) {
  console.log('\nfacts to be written:');
  for (const fact of facts) {
    console.log(`  ${fact.period_end}  ${String(fact.value).padStart(10)}  ${fact.definition_id}`);
  }
  console.log('\nDry run. Nothing written. Re-run with --apply to write.');
  process.exit(0);
}

const client = createSupabaseAdmin();
if (!client) { console.error('SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.'); process.exit(1); }
const { written, refused, error } = await saveFacts(client, facts);
console.log(`\nwritten  ${written}`);
if (refused.length) for (const one of refused) console.log(`  refused ${one.fact.definition_id}: ${one.problems.join(', ')}`);
if (error) { console.error('write failed:', error.message); process.exit(1); }
