#!/usr/bin/env node
/**
 * What each tracked manager actually files with the SEC.
 *
 *   node server/scripts/managerDocumentTypes.mjs
 *   node server/scripts/managerDocumentTypes.mjs --manager berkshire-hathaway
 *
 * Read-only, and it writes nothing. The intelligence layer reads publications,
 * and the first question is which of the fifty publish anything to read. A
 * 13F-HR is a table of positions with no prose in it; an ARS is the annual
 * report where Berkshire's letter lives. Both come from the same filer.
 *
 * EDGAR answers this exactly. Every CIK has a submissions file listing the
 * form type of every filing, so this is a count of what is there rather than
 * an assumption about what a hedge fund probably publishes.
 *
 * What it cannot answer: quarterly investor letters, decks and newsletters
 * that never reach EDGAR. Third Point and Greenlight write to their limited
 * partners, not to the Commission, and no index covers that. Those have to be
 * checked one firm at a time, and the report says so rather than implying the
 * SEC list is the whole picture.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { scheduleSecRequest } from '../services/secRateLimiter.js';
import { paged } from '../services/institutionalResearchLayerService.js';
import { summariseForms } from '../services/narrativeForms.js';

const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const ONLY = argOf('--manager');
const UA = process.env.SEC_USER_AGENT || 'AGI Institutional Research research@agarwalglobalinvestments.com';

if (!getSupabaseAdminCredentials()) {
  console.error('[forms] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();

async function submissions(cik) {
  const padded = String(cik).replace(/\D/g, '').padStart(10, '0');
  const response = await scheduleSecRequest(() => fetch(
    `https://data.sec.gov/submissions/CIK${padded}.json`,
    { headers: { Accept: 'application/json', 'User-Agent': UA }, signal: AbortSignal.timeout(30_000) },
  ));
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function main() {
  const managers = await paged(
    () => client.from('institutional_managers').select('slug, display_name, cik')
      .eq('active', true).order('display_name'),
    { label: 'managers' },
  );
  const wanted = ONLY ? managers.filter((row) => row.slug === ONLY) : managers;
  console.log(`[forms] reading EDGAR submissions for ${wanted.length} manager(s)\n`);

  const results = [];
  for (const manager of wanted) {
    try {
      const payload = await submissions(manager.cik);
      // The recent block holds roughly the last thousand filings, which is
      // more than enough to answer "what kinds of thing does this filer
      // publish". Older archives would change the counts, not the kinds.
      const forms = payload?.filings?.recent?.form || [];
      results.push({
        manager,
        entityName: payload?.name || null,
        // EDGAR's own classification of the registrant. An operating company
        // reads "operating"; an adviser that files only 13F often reads
        // "other", which is a fact worth showing beside the forms.
        entityType: payload?.entityType || null,
        summary: summariseForms(forms),
      });
      process.stdout.write('.');
    } catch (error) {
      results.push({ manager, error: error.message });
      process.stdout.write('x');
    }
  }
  process.stdout.write('\n\n');

  const label = (row) => row.manager.display_name.slice(0, 30).padEnd(32);
  const list = (rows) => (rows.length ? rows.map((r) => `${r.form}(${r.count})`).join(' ') : '-');

  console.log('=== Forms that carry the manager\'s own words ===\n');
  const publishers = results.filter((r) => r.summary?.narrative.length);
  for (const row of publishers.sort((a, b) => b.summary.narrative.length - a.summary.narrative.length)) {
    console.log(`${label(row)}${list(row.summary.narrative)}`);
  }
  if (!publishers.length) console.log('  none');

  console.log('\n=== Stated intent: Schedule 13D and 13G ===\n');
  for (const row of results.filter((r) => r.summary?.intent.length)) {
    console.log(`${label(row)}${list(row.summary.intent)}`);
  }

  console.log('\n=== Positions only, nothing to read ===\n');
  const silent = results.filter((r) => r.summary && !r.summary.narrative.length && !r.summary.intent.length);
  for (const row of silent) {
    console.log(`${label(row)}${list(row.summary.positions)}   [${row.entityType || 'unknown type'}]`);
  }

  const unclassified = new Map();
  for (const row of results) {
    for (const entry of row.summary?.unclassified || []) {
      unclassified.set(entry.form, (unclassified.get(entry.form) || 0) + entry.count);
    }
  }
  if (unclassified.size) {
    console.log('\n=== Form types this does not classify yet ===\n');
    console.log(`  ${[...unclassified.entries()].sort((a, b) => b[1] - a[1]).map(([f, c]) => `${f}(${c})`).join(' ')}`);
  }

  const failed = results.filter((r) => r.error);
  if (failed.length) {
    console.log('\n=== Could not be read ===\n');
    for (const row of failed) console.log(`${label(row)}${row.error}`);
  }

  console.log(`\n[forms] ${publishers.length} of ${results.length} manager(s) file something with prose in it.`);
  console.log('[forms] This is the SEC only. Quarterly investor letters and decks never reach EDGAR');
  console.log('[forms] and are not counted here - they have to be checked one firm at a time.');
}

main().catch((error) => {
  console.error(`[forms] ${error.message}`);
  process.exit(1);
});
