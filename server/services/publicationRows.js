/**
 * Database rows for one pasted publication, with a uniform shape.
 *
 * The shape is the point. PostgREST sends an array of objects as a single
 * INSERT whose column list is the union of every key in the array, and a row
 * that omits one of those keys is given NULL - not the column's DEFAULT. So a
 * batch where some rows set a column and others leave it out silently writes
 * NULL into the ones that left it out.
 *
 * That is not hypothetical. Holdings rows never set `status` and relied on the
 * default of 'pending' for as long as no other row set it either. The moment
 * chain claims began carrying `status` so that some could be auto-approved,
 * `status` joined the column list and the nine holdings rows were sent as
 * NULL:
 *
 *   null value in column "status" of relation
 *   "manager_publication_facts" violates not-null constraint
 *
 * The whole write failed, which is the good outcome - a nullable column would
 * have taken the NULL and nobody would have known. The fix is that every row
 * from here carries every column, and a test asserts it, because the next
 * column added will otherwise reintroduce exactly this.
 *
 * A person's decision survives a re-import. The upsert updates every column it
 * is given, so a second run of the same document rewrote `status` to 'pending'
 * and wiped 142 claims someone had read and approved. Re-extracting a document
 * is a routine thing to do - every tightening of the extractor calls for it -
 * and it must not discard the one part of this pipeline that cost a human
 * being their attention.
 */
import { autoApproved } from './publicationIntelligence.js';

/**
 * Every column these rows write, in one place.
 *
 * A row is built from this list rather than from whatever the caller happened
 * to know about, so adding a column to the table means adding it here once.
 */
export const FACT_COLUMNS = [
  'publication_id', 'manager_id', 'kind',
  'issuer', 'percent_owned', 'cost_basis', 'market_value', 'dividends', 'unit',
  'slot', 'basis', 'metric', 'segment', 'segment_source', 'themes',
  'figures', 'change', 'paragraph',
  'source_excerpt', 'status', 'reviewed_by', 'reviewed_at',
];

const blank = () => Object.fromEntries(FACT_COLUMNS.map((column) => [column, null]));

/**
 * A decision a person already made about this claim, or null.
 *
 * Keyed the way the database's uniqueness is keyed, so a row that survives
 * re-extraction is recognised as the same claim.
 */
const decisionFor = (decisions, slot, excerpt) =>
  decisions?.get(JSON.stringify([slot ?? null, excerpt])) || null;

/** A disclosed-holdings row. No slot: it is a table fact, not a chain step. */
function holdingRow(fact, ids, decisions) {
  return {
    ...blank(),
    publication_id: ids.publicationId,
    manager_id: ids.managerId,
    kind: fact.kind,
    issuer: fact.issuer,
    percent_owned: fact.percent_owned,
    cost_basis: fact.cost_basis,
    market_value: fact.market_value,
    dividends: fact.dividends,
    unit: fact.unit,
    basis: 'stated',
    source_excerpt: fact.source_excerpt,
    // A holdings row always waits for a person. The figures carry a scale read
    // off a header line elsewhere on the page, and a thousand-fold error has
    // shipped from this codebase once already.
    status: 'pending',
    ...(decisionFor(decisions, null, fact.source_excerpt) || {}),
  };
}

/**
 * One chain claim. Approved by rule where the claim is quotation.
 *
 * A decision a person already recorded wins over the rule, in both directions:
 * a claim they approved stays approved, and one they rejected is not quietly
 * re-approved by a rule on the next run.
 */
function claimRow(claim, ids, now, decisions) {
  const decided = decisionFor(decisions, claim.slot, claim.source_excerpt);
  const approved = autoApproved(claim);
  return {
    ...blank(),
    publication_id: ids.publicationId,
    manager_id: ids.managerId,
    kind: 'chain_claim',
    slot: claim.slot,
    basis: claim.basis,
    metric: claim.metric,
    segment: claim.segment,
    segment_source: claim.segment_source,
    themes: claim.themes && claim.themes.length ? claim.themes : null,
    figures: claim.figures && claim.figures.length ? claim.figures : null,
    change: claim.change,
    paragraph: claim.paragraph,
    source_excerpt: claim.source_excerpt,
    status: approved ? 'approved' : 'pending',
    // Null while pending, so the table's status/reviewed_by pair constraint
    // holds: a reviewed row always records who reviewed it.
    reviewed_by: approved ? 'rule' : null,
    reviewed_at: approved ? now : null,
    ...(decided || {}),
  };
}

/**
 * Rows for a publication's holdings and chain claims, deduplicated.
 *
 * One row per (slot, excerpt). A sentence answering three steps is three rows,
 * because a reviewer accepts it as an answer to one question at a time and may
 * take it as a change while rejecting it as a cause - but the same sentence
 * twice in one slot is one finding, and sending it twice makes a single INSERT
 * touch the same row twice, which Postgres refuses outright, losing the run.
 */
export function factRows({ publicationId, managerId, holdings = [], chain = null, now,
  reviewed = [] }) {
  const ids = { publicationId, managerId };
  const at = now || new Date().toISOString();
  // Only a person's decisions are carried forward. A rule's approval is
  // recomputed every run, which is what lets a tightened rule take back a
  // claim it should not have published.
  const decisions = new Map((reviewed || [])
    .filter((row) => row.reviewed_by === 'person')
    .map((row) => [JSON.stringify([row.slot ?? null, row.source_excerpt]),
      { status: row.status, reviewed_by: 'person', reviewed_at: row.reviewed_at }]));
  const rows = [
    ...holdings.map((fact) => holdingRow(fact, ids, decisions)),
    ...(chain?.slots || []).flatMap((slot) => slot.claims
      .map((claim) => claimRow(claim, ids, at, decisions))),
  ];

  const byKey = new Map();
  for (const row of rows) {
    byKey.set(JSON.stringify([row.slot, row.source_excerpt]), row);
  }
  // Claims the database holds that this extraction no longer produces. An
  // upsert only writes, so a row the extractor has stopped believing stays
  // live with whatever status it had - which is how a balance-sheet row
  // remained approved on the page after the rule that admitted it was fixed.
  // Reported, never deleted here: removing rows is the caller's decision.
  const stale = (reviewed || [])
    .filter((row) => !byKey.has(JSON.stringify([row.slot ?? null, row.source_excerpt])))
    .map(({ slot, status, reviewed_by, source_excerpt }) =>
      ({ slot, status, reviewed_by, source_excerpt }));

  return { rows: [...byKey.values()], collapsed: rows.length - byKey.size, stale };
}
