#!/usr/bin/env node
/**
 * company_financials into company_facts, without pretending to know more than
 * the old table recorded.
 *
 *   node server/scripts/migrateCompanyFinancials.mjs                  # dry run
 *   node server/scripts/migrateCompanyFinancials.mjs --apply
 *   node server/scripts/migrateCompanyFinancials.mjs --apply --limit 500
 *
 * Dry run is the default and writes nothing. It prints how many facts the rows
 * would become and what share of them arrive with no recorded definition,
 * which is the number to read before deciding to write any of it.
 *
 * Ten of the old table's twenty-six columns name more than one definition in
 * the register, and nothing in the row says which. Those are migrated under
 * the unrecorded markers rather than dropped or guessed: visible, queryable,
 * and refused by any purpose that depends on knowing the basis.
 *
 * The ticker becomes the company. If facts already exist under another name
 * for the same issuer, pass --company to override for a single ticker rather
 * than letting two names for one company accumulate.
 */
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { saveFacts } from '../services/factStore.js';
import { factsFromRow, summarise } from '../services/companyFinancialsMigration.js';

const args = process.argv.slice(2);
const has = (name) => args.includes(name);
const flag = (name, fallback = null) => {
  const at = args.indexOf(name);
  return at === -1 || at === args.length - 1 ? fallback : args[at + 1];
};

const apply = has('--apply');
const limit = Number(flag('--limit', '0')) || null;
const ticker = flag('--ticker');
const company = flag('--company');

const client = createSupabaseAdmin();
if (!client) {
  console.error('SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(1);
}

// Paged deliberately: an unbounded select returns a thousand rows and says
// nothing about the rest, which would read as a small table.
const PAGE = 1000;
const rows = [];
for (let page = 0; ; page += 1) {
  let query = client.from('company_financials').select('*')
    .order('ticker', { ascending: true })
    .order('period_end', { ascending: true })
    .range(page * PAGE, page * PAGE + PAGE - 1);
  if (ticker) query = query.eq('ticker', ticker);
  const { data, error } = await query;
  if (error) { console.error('read failed:', error.message); process.exit(1); }
  rows.push(...(data || []));
  if (!data || data.length < PAGE) break;
  if (limit && rows.length >= limit) break;
}
const selected = limit ? rows.slice(0, limit) : rows;

const plan = summarise(selected, { company });
console.log(`rows read                 ${plan.rows}`);
console.log(`facts they become         ${plan.facts}`);
console.log(`without a definition      ${plan.unrecorded}  (${plan.unrecorded_share === null ? 'n/a' : (plan.unrecorded_share * 100).toFixed(1) + '%'})`);
if (plan.problems.length) {
  console.log(`\nrows that produce nothing (${plan.problems.length}):`);
  for (const problem of plan.problems.slice(0, 20)) console.log('  ' + problem);
  if (plan.problems.length > 20) console.log(`  ... and ${plan.problems.length - 20} more`);
}
console.log('\nby definition:');
for (const [definition_id, count] of plan.by_definition) {
  console.log('  ' + String(count).padStart(6) + '  ' + definition_id);
}

if (!apply) {
  console.log('\nDry run. Nothing written. Re-run with --apply to write.');
  process.exit(0);
}

const facts = selected.flatMap((row) => factsFromRow(row, { company }).facts);
const { written, refused, error } = await saveFacts(client, facts);
console.log(`\nwritten  ${written}`);
if (refused.length) {
  console.log(`refused  ${refused.length}`);
  for (const one of refused.slice(0, 20)) {
    console.log(`  ${one.fact.company} ${one.fact.period_end} ${one.fact.definition_id}: ${one.problems.join(', ')}`);
  }
}
if (error) { console.error('write failed:', error.message); process.exit(1); }
