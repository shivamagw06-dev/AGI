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
import { intelligenceChain, selectClaims } from '../services/publicationIntelligence.js';
import { SEGMENT_LABELS, THEME_LABELS } from '../services/publicationSegments.js';

const APPLY = process.argv.includes('--apply');
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const MANAGER = argOf('--manager');
const TITLE = argOf('--title');
const AS_OF = argOf('--as-of');
const SOURCE_URL = argOf('--source-url');
const FILE = argOf('--file');
const PER_SLOT = Number(argOf('--per-slot')) || 25;
// Tables only, for checking a holdings parse without the chain's output.
const TABLES_ONLY = process.argv.includes('--tables-only');
// Narrow the printed chain to a question: --slot expectations --segment bnsf
// --theme freight_volumes. A filter changes what is shown, never what is
// stored: the whole chain is written so a later question can be asked of it.
const ASK_SLOT = argOf('--slot');
const ASK_SEGMENT = argOf('--segment');
const ASK_THEME = argOf('--theme');
const ASKED = Boolean(ASK_SLOT || ASK_SEGMENT || ASK_THEME);

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

const pad = (value, width) => String(value ?? '-').padEnd(width);

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
    // No longer the end of the run. A letter written entirely in sentences has
    // no holdings table and still answers seven steps of the chain, so this
    // states what the table reader did not find and carries on.
    console.log('[pub] No holdings table matched. That reader takes tables of the shape');
    console.log('[pub]   <issuer> <percent>% <cost> <market value> <dividends>');
    console.log('[pub] and returns nothing for prose rather than returning something wrong.');
  }

  if (facts.length) {
    console.log(`${pad('issuer', 34)}${pad('owned', 8)}${pad('cost', 22)}${pad('market value', 22)}dividends`);
  }
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

  const chain = TABLES_ONLY ? null : intelligenceChain(text, { perSlot: PER_SLOT });
  if (chain) {
    console.log(`\n[pub] ${chain.sentences.toLocaleString()} sentences, `
      + `${chain.matched_sentences.toLocaleString()} carrying a claim`);
    console.log('[pub] (a sentence can answer more than one step; the count above is sentences,');
    console.log('[pub]  not the sum of the steps below)\n');
    for (const slot of chain.slots) {
      if (!slot.extractable) {
        // Printed, not omitted. Seven steps shown as the whole chain is the
        // thing this line exists to prevent.
        console.log(`  ${pad(slot.question, 34)}not extractable`);
        console.log(`  ${' '.repeat(34)}${slot.reason.replace(/\s+/g, ' ')}`);
        continue;
      }
      const shown = slot.truncated ? `${slot.returned} of ${slot.found}` : String(slot.found);
      console.log(`  ${pad(slot.question, 34)}${pad(shown, 12)}${slot.basis}`);
    }
    if (ASKED) {
      const hits = selectClaims(chain, {
        slot: ASK_SLOT || undefined,
        segment: ASK_SEGMENT || undefined,
        theme: ASK_THEME || undefined,
      });
      const asked = [ASK_SLOT && `slot=${ASK_SLOT}`, ASK_SEGMENT && `segment=${ASK_SEGMENT}`,
        ASK_THEME && `theme=${ASK_THEME}`].filter(Boolean).join(' ');
      console.log(`\n--- ${asked}  (${hits.length} claim(s))`);
      if (!hits.length) {
        // Worth saying out loud rather than printing nothing. The report
        // states aerospace recovery as something that happened, not as a
        // forecast, so asking for expectations about it correctly returns
        // none - the claims are there under what_happened.
        console.log('  Nothing in the document answers that. Try the same segment or theme');
        console.log('  without --slot: a report often states a trend as an outcome rather');
        console.log('  than as something management expects.');
      }
      for (const claim of hits) {
        const where = claim.segment
          ? `${SEGMENT_LABELS[claim.segment] || claim.segment}/${claim.segment_source}`
          : 'unattributed';
        console.log(`  [${claim.slot} | ${where}] ${claim.source_excerpt.slice(0, 200)}`);
      }
    } else {
      for (const slot of chain.slots) {
        if (!slot.claims.length) continue;
        console.log(`\n--- ${slot.question}  [${slot.basis}]`);
        for (const claim of slot.claims.slice(0, 5)) {
          const label = claim.metric ? `(${claim.metric}) ` : '';
          const where = claim.segment ? `[${SEGMENT_LABELS[claim.segment] || claim.segment}] ` : '';
          const move = claim.change && claim.change.delta !== null
            ? `  [${claim.change.direction} ${claim.change.delta}`
              + `${claim.change.kind === 'percentage_points' ? 'pp' : ''}]`
            : '';
          console.log(`  ${where}${label}${claim.source_excerpt.slice(0, 150)}${move}`);
        }
        if (slot.claims.length > 5) console.log(`  ... and ${slot.claims.length - 5} more`);
      }
      const themes = new Map();
      for (const claim of selectClaims(chain)) {
        for (const theme of claim.themes || []) themes.set(theme, (themes.get(theme) || 0) + 1);
      }
      if (themes.size) {
        console.log('\n[pub] market themes found (ask with --theme):');
        for (const [theme, count] of [...themes].sort((a, b) => b[1] - a[1])) {
          console.log(`  ${pad(theme, 24)}${pad(count, 6)}${THEME_LABELS[theme] || ''}`);
        }
      }
    }
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
    // No slot: a holdings-table row is a table fact, not a step in the chain.
    slot: null,
    basis: 'stated',
    source_excerpt: fact.source_excerpt,
  }));

  // A claim per slot per sentence. A sentence answering three steps is three
  // rows, because a reviewer approves it as an answer to one question at a
  // time and may accept it as a change while rejecting it as a cause.
  for (const slot of chain ? chain.slots : []) {
    for (const claim of slot.claims) {
      rows.push({
        publication_id: publication.id,
        manager_id: manager.id,
        kind: 'chain_claim',
        issuer: null,
        slot: claim.slot,
        basis: claim.basis,
        metric: claim.metric,
        segment: claim.segment,
        segment_source: claim.segment_source,
        themes: claim.themes && claim.themes.length ? claim.themes : null,
        figures: claim.figures.length ? claim.figures : null,
        change: claim.change,
        paragraph: claim.paragraph,
        source_excerpt: claim.source_excerpt,
      });
    }
  }

  const { error: fError } = await client.from('manager_publication_facts')
    .upsert(rows, { onConflict: 'publication_id,slot,source_excerpt' });
  if (fError) throw new Error(`storing facts: ${fError.message}`);

  const claims = rows.length - facts.length;
  console.log(`\n[pub] ${facts.length} holding(s) and ${claims} chain claim(s) stored as pending`);
  console.log(`[pub] against publication ${publication.id}`);
  if (chain) {
    const gaps = chain.slots.filter((slot) => !slot.extractable).map((slot) => slot.slot);
    console.log(`[pub] ${gaps.join(' and ')} are not stored: no sentence states either, and`);
    console.log('[pub] filling them needs a model reading the document, not a pattern.');
  }
  console.log('[pub] Nothing reaches the page until a person approves them.');
}

main().catch((error) => {
  console.error(`[pub] ${error.message}`);
  process.exit(1);
});
