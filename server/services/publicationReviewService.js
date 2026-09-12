/**
 * The queue a person works to decide what a document said.
 *
 * 520 claims sat invisible across two documents because the only way to
 * approve one was a SQL statement. That worked for one person who knew the
 * schema and was the reason the layer was correct and unusable at the same
 * time.
 *
 * Three rules shape this, and each is a consequence of something that went
 * wrong while the extractor was being built.
 *
 * A decision names a person. `reviewed_by` is always 'person' here, never
 * 'rule', because a page that presents a rule's approval as a human's is the
 * conflation the column exists to prevent - and the import script printed
 * exactly that conflation for a day.
 *
 * Claims are decided by id, never by filter. "Approve everything matching
 * slot = why" is one keystroke away from publishing 142 sentences nobody
 * read, which is what happened when the only tool was an UPDATE with a WHERE
 * clause. The caller sends the ids it was shown.
 *
 * Rejecting is as available as approving. A queue whose only button is
 * "approve" is a queue that launders the extractor's mistakes, and the
 * extractor has published a balance-sheet row, five date ranges and a
 * mitigation-as-hazard in the course of one day.
 */

/** Decisions a person may record. A rule's approval is not one of them. */
export const REVIEW_STATUSES = ['approved', 'rejected'];

/** How many claims one request may decide. */
export const REVIEW_BATCH_LIMIT = 100;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * The decision to write, or an error explaining why there is none.
 *
 * Validated here rather than at the route, so the rules are testable without
 * a request. Returns `{ error }` instead of throwing because every failure
 * here is a caller mistake worth reporting verbatim, not an exception.
 */
export function reviewPatch({ ids, status, at } = {}) {
  if (!REVIEW_STATUSES.includes(status)) {
    return { error: `status must be one of ${REVIEW_STATUSES.join(', ')}` };
  }
  const list = Array.isArray(ids) ? ids : [];
  if (!list.length) return { error: 'no claims were selected' };
  // Deduplicated before the cap is applied, so sending the same id twice is
  // not counted against the batch.
  const unique = [...new Set(list.map((id) => String(id)))];
  const bad = unique.filter((id) => !UUID.test(id));
  if (bad.length) return { error: `not a claim id: ${bad.slice(0, 3).join(', ')}` };
  if (unique.length > REVIEW_BATCH_LIMIT) {
    return { error: `at most ${REVIEW_BATCH_LIMIT} claims at a time, got ${unique.length}` };
  }
  return {
    ids: unique,
    patch: {
      status,
      // Always a person. The rule's own approvals are recomputed on every
      // import and are not recorded through this path.
      reviewed_by: 'person',
      reviewed_at: at || new Date().toISOString(),
    },
  };
}

/**
 * What a reviewer needs to see to judge one claim.
 *
 * The sentence first, because everything else is a label on it. `basis` says
 * whether the claim is the filer's words or our subtraction; `segment_source`
 * says whether the business was named in the sentence or inherited from a
 * heading twenty-five sentences up, which is the difference between evidence
 * and a guess.
 */
export function reviewRow(row) {
  return {
    id: row.id,
    manager: row.institutional_managers?.display_name || null,
    manager_slug: row.institutional_managers?.slug || null,
    publication: row.manager_publications?.title || null,
    as_of_date: row.manager_publications?.as_of_date || null,
    kind: row.kind,
    slot: row.slot,
    basis: row.basis,
    metric: row.metric,
    segment: row.segment,
    segment_source: row.segment_source,
    themes: row.themes || [],
    change: row.change,
    figures: row.figures,
    issuer: row.issuer,
    unit: row.unit,
    status: row.status,
    reviewed_by: row.reviewed_by,
    source_excerpt: row.source_excerpt,
  };
}

const SELECT = 'id,kind,slot,basis,metric,segment,segment_source,themes,change,figures,'
  + 'issuer,unit,source_excerpt,status,reviewed_by,created_at,'
  + 'institutional_managers(display_name,slug),manager_publications(title,as_of_date)';

/**
 * A page of the review queue.
 *
 * Bounded and honest about it. An unbounded read here silently stops at
 * PostgREST's thousandth row, which this codebase has been bitten by more
 * than once, so the limit is explicit and `more` says whether the filter
 * matched beyond it.
 */
export async function publicationQueue(client, {
  status = 'pending', slot = null, managerSlug = null, limit = 50, offset = 0,
} = {}) {
  const size = Math.min(Math.max(Number(limit) || 50, 1), 200);
  const from = Math.max(Number(offset) || 0, 0);
  let query = client.from('manager_publication_facts').select(SELECT, { count: 'exact' });
  if (status !== 'all') query = query.eq('status', status);
  if (slot === 'holding') query = query.is('slot', null);
  else if (slot) query = query.eq('slot', slot);
  if (managerSlug) query = query.eq('institutional_managers.slug', managerSlug);
  const { data, error, count } = await query
    // Oldest first: the queue is worked front to back, and a stable order
    // means the same claim is not shown twice across two pages.
    .order('created_at', { ascending: true }).order('id', { ascending: true })
    .range(from, from + size - 1);
  if (error) throw new Error(`reading the review queue: ${error.message}`);
  const rows = (data || []).map(reviewRow);
  return { rows, total: count ?? null, offset: from, limit: size, more: (count ?? 0) > from + rows.length };
}

/** Counts per step for the queue, so a reviewer can see what is left. */
export async function publicationQueueCounts(client) {
  const { data, error } = await client.from('manager_publication_facts')
    .select('slot,status,reviewed_by');
  if (error) throw new Error(`counting the review queue: ${error.message}`);
  const counts = new Map();
  for (const row of data || []) {
    const key = row.slot || 'holding';
    const entry = counts.get(key) || { slot: key, pending: 0, approved: 0, rejected: 0, by_rule: 0 };
    if (row.status === 'pending') entry.pending += 1;
    if (row.status === 'approved') entry.approved += 1;
    if (row.status === 'rejected') entry.rejected += 1;
    if (row.reviewed_by === 'rule') entry.by_rule += 1;
    counts.set(key, entry);
  }
  return [...counts.values()].sort((a, b) => b.pending - a.pending || a.slot.localeCompare(b.slot));
}

/** Record a person's decision on the claims they were shown. */
export async function reviewPublicationClaims(client, { ids, status } = {}) {
  const decision = reviewPatch({ ids, status });
  if (decision.error) throw new Error(decision.error);
  const { data, error } = await client.from('manager_publication_facts')
    .update(decision.patch).in('id', decision.ids).select('id,status,reviewed_by');
  if (error) throw new Error(`recording the review: ${error.message}`);
  const decided = data || [];
  return {
    decided: decided.length,
    // Reported rather than silently ignored: an id that matched nothing means
    // the queue the reviewer was looking at is stale.
    missing: decision.ids.filter((id) => !decided.some((row) => row.id === id)),
    status: decision.patch.status,
  };
}
