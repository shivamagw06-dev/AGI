/**
 * Storing a pasted publication, for whoever is doing the pasting.
 *
 * This was the middle of a CLI script, which meant a browser upload would
 * have had to reimplement it. Two implementations of "what gets stored" is
 * how one of them silently stops matching the other, and the rules here were
 * each paid for: uniqueness that admits a sentence answering two steps, a
 * person's decision surviving re-extraction, a row's shape being uniform, and
 * stale claims being reported rather than left live.
 *
 * Nothing is printed here. The caller gets a summary and decides how to say
 * it - a terminal and a browser want different words for the same facts.
 */
import { createHash } from 'node:crypto';
import { extractDisclosedHoldings, documentDigest } from './publicationFacts.js';
import { intelligenceChain, selectClaims } from './publicationIntelligence.js';
import { factRows } from './publicationRows.js';
import { managerMentions } from './publicationSaid.js';

/**
 * What the extractor found, without writing anything.
 *
 * Separate from storing it so a caller can show a dry run, and so the browser
 * upload can report what it is about to do before it does it.
 */
export function readPublication(text) {
  const body = String(text || '');
  const digest = documentDigest(body, (value) => createHash('sha256').update(value).digest('hex'));
  const holdings = extractDisclosedHoldings(body);
  const chain = intelligenceChain(body);
  const claims = selectClaims(chain);
  const themes = new Map();
  for (const claim of claims) {
    for (const theme of claim.themes || []) themes.set(theme, (themes.get(theme) || 0) + 1);
  }
  return {
    characters: body.length,
    digest,
    holdings,
    chain,
    claims: claims.length,
    steps: chain.slots.map(({ slot, question, basis, extractable, reason, found }) =>
      ({ slot, question, basis, extractable, reason: reason || null, found: found || 0 })),
    themes: [...themes].sort((a, b) => b[1] - a[1]).map(([theme, count]) => ({ theme, count })),
  };
}

/**
 * Whether this document plausibly belongs to this manager.
 *
 * A filer names itself. Norges Bank's annual report was once stored as 177
 * things Berkshire said because nothing connected the manager named by the
 * caller to the document in front of it.
 */
export function managerCheck(text, managerName) {
  const found = managerMentions(text, managerName);
  if (!found.checked || found.mentions > 0) return { ok: true, ...found };
  return {
    ok: false,
    ...found,
    message: `This document never mentions "${found.token}". A report almost always names `
      + 'its own author, so this is most likely the wrong document or the wrong manager.',
  };
}

/**
 * Store a publication and everything extracted from it.
 *
 * `prune` deletes claims this extraction no longer produces. Off by default,
 * because a write that silently removed rows would take an approved claim
 * with it the first time a rule was tightened by mistake.
 */
export async function storePublication({
  client, paged, manager, text, title, asOfDate = null, sourceUrl = null, prune = false,
}) {
  if (!client || !paged) throw new Error('a supabase client and a pager are required');
  if (!manager?.id) throw new Error('a manager is required');
  if (!String(title || '').trim()) throw new Error('a title is required');

  const read = readPublication(text);
  if (!read.characters) throw new Error('nothing was pasted');

  const { data: publication, error: pError } = await client.from('manager_publications')
    .upsert({
      manager_id: manager.id,
      title: String(title).trim(),
      as_of_date: asOfDate || null,
      source_url: sourceUrl || null,
      digest: read.digest,
    }, { onConflict: 'digest' })
    .select()
    .single();
  if (pError) throw new Error(`recording the publication: ${pError.message}`);

  // Read before anything is written. The upsert updates every column it is
  // given, so without this a re-run rewrites status to 'pending' and discards
  // every claim someone had read - which it did once, to 142 of them.
  const reviewed = await paged(
    () => client.from('manager_publication_facts')
      .select('slot,source_excerpt,status,reviewed_by,reviewed_at')
      .eq('publication_id', publication.id).order('id'),
    { label: 'prior-review' },
  );

  const { rows, collapsed, stale } = factRows({
    publicationId: publication.id,
    managerId: manager.id,
    holdings: read.holdings,
    chain: read.chain,
    reviewed,
  });

  // Chunked. A whole report is ~650 claims and one request carrying all of
  // them is a single point of failure for the entire run.
  for (let at = 0; at < rows.length; at += 250) {
    const chunk = rows.slice(at, at + 250);
    const { error } = await client.from('manager_publication_facts')
      .upsert(chunk, { onConflict: 'publication_id,slot,source_excerpt' });
    if (error) throw new Error(`storing facts ${at + 1}-${at + chunk.length}: ${error.message}`);
  }

  let pruned = 0;
  if (prune && stale.length) {
    for (const row of stale) {
      const query = client.from('manager_publication_facts').delete()
        .eq('publication_id', publication.id).eq('source_excerpt', row.source_excerpt);
      const { error } = await (row.slot === null
        ? query.is('slot', null) : query.eq('slot', row.slot));
      if (error) throw new Error(`pruning a stale row: ${error.message}`);
      pruned += 1;
    }
  }

  return {
    publication_id: publication.id,
    digest: read.digest,
    characters: read.characters,
    holdings: read.holdings.length,
    claims: rows.length - read.holdings.length,
    steps: read.steps,
    themes: read.themes,
    collapsed,
    kept_from_prior_review: reviewed.filter((row) => row.reviewed_by === 'person').length,
    // Counted by who decided. Summing them and calling the total the rule's
    // work is the conflation reviewed_by exists to prevent.
    approved_by_rule: rows.filter((row) => row.reviewed_by === 'rule').length,
    approved_by_person: rows.filter((row) => row.reviewed_by === 'person' && row.status === 'approved').length,
    rejected_by_person: rows.filter((row) => row.reviewed_by === 'person' && row.status === 'rejected').length,
    pending: rows.filter((row) => row.status === 'pending').length,
    stale,
    pruned,
  };
}
