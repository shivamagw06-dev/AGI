/**
 * Reading and writing facts, against a table that punishes three habits.
 *
 * PostgREST caps an unbounded select at a thousand rows and says nothing, so
 * nothing here selects without paging; a read that stops early is worse than a
 * read that fails, because it looks like a small company. An upsert row that
 * omits a key writes NULL rather than the column default, so every row carries
 * every column whether or not the caller filled it. And the identity index is
 * the upsert conflict target, so the two are declared once, in IDENTITY, and
 * cannot drift apart without a test noticing.
 *
 * The mapping is the other half. A fact in memory says `segment: null` for a
 * figure that is not segmental; the table holds '' for it, because the index
 * has to be over plain columns to be inferable. Neither side should have to
 * know the other's convention, so this is the only place that does.
 */
import { DIMENSIONLESS, ENTITY_SCOPE, MEASUREMENT, PERIOD_TYPE } from './factOntology.js';

export const TABLE = 'company_facts';

/** PostgREST's silent ceiling. Every read pages against it deliberately. */
export const PAGE = 1000;

/**
 * The identity columns, in the order the unique index declares them.
 *
 * This is also the upsert conflict target. Declaring it once is the point: an
 * index and a conflict target that disagree produce duplicate rows rather than
 * an error.
 */
export const IDENTITY = Object.freeze([
  'company', 'period_end', 'period_type', 'accounting_scope', 'entity_scope',
  'concept', 'definition_id', 'segment', 'geography', 'dimensions', 'reported_in_document',
]);

const REST = Object.freeze([
  'measurement_basis', 'currency', 'unit', 'original_or_restated', 'supersedes_fact_id',
  'value', 'verdict', 'input_fact_ids', 'formula', 'as_reported_label',
  'source_document_id', 'source_section', 'source_page', 'source_sentence', 'confidence',
]);

export const COLUMNS = Object.freeze([...IDENTITY, ...REST]);

const NOT_SEGMENTAL = '';

/**
 * A fact as the table holds it.
 *
 * Every column appears, always. A row that leaves one out does not inherit the
 * column default on upsert - it writes NULL over whatever was there.
 */
export function toRow(fact) {
  return {
    company: fact?.company ?? null,
    period_end: fact?.period_end ?? null,
    period_type: fact?.period_type || PERIOD_TYPE.ANNUAL,
    accounting_scope: fact?.accounting_scope || 'consolidated',
    entity_scope: fact?.entity_scope || ENTITY_SCOPE.GROUP,
    concept: fact?.concept ?? null,
    definition_id: fact?.definition_id ?? null,
    segment: fact?.segment ?? NOT_SEGMENTAL,
    geography: fact?.geography ?? NOT_SEGMENTAL,
    dimensions: fact?.dimensions ?? {},
    reported_in_document: fact?.reported_in_document ?? null,
    measurement_basis: fact?.measurement_basis ?? null,
    currency: fact?.currency ?? null,
    unit: fact?.unit ?? null,
    original_or_restated: fact?.original_or_restated || 'original',
    supersedes_fact_id: fact?.supersedes_fact_id ?? null,
    value: fact?.value ?? null,
    verdict: fact?.verdict || 'stated',
    input_fact_ids: fact?.input_fact_ids ?? null,
    formula: fact?.formula ?? null,
    as_reported_label: fact?.as_reported_label ?? null,
    source_document_id: fact?.source_document_id ?? null,
    source_section: fact?.source_section ?? null,
    source_page: fact?.source_page ?? null,
    source_sentence: fact?.source_sentence ?? null,
    confidence: fact?.confidence ?? null,
  };
}

/** A row as the rest of the code expects a fact. */
export function fromRow(row) {
  return {
    ...row,
    segment: row?.segment === NOT_SEGMENTAL ? null : row?.segment ?? null,
    geography: row?.geography === NOT_SEGMENTAL ? null : row?.geography ?? null,
    value: row?.value === null || row?.value === undefined ? null : Number(row.value),
    unit: row?.unit === null || row?.unit === undefined ? null : Number(row.unit),
    dimensions: row?.dimensions ?? {},
  };
}

/**
 * What the table will refuse, refused here first.
 *
 * A check constraint rejects the whole batch and names a value, not a fact. By
 * the time that error appears the reader that produced the row is gone.
 */
export function unwritable(fact) {
  const row = toRow(fact);
  const problems = [];
  for (const column of ['company', 'period_end', 'concept', 'definition_id',
    'reported_in_document', 'measurement_basis', 'unit']) {
    if (row[column] === null || row[column] === '') problems.push(`${column} is missing`);
  }
  // A quotient and a count have no currency, and requiring one would refuse
  // every ratio the calculator produces and every share count there is. For
  // anything that is an amount of money the requirement stands, because a
  // missing currency there is a bug and not a property of the figure.
  const dimensionless = DIMENSIONLESS.has(row.measurement_basis);
  if (!dimensionless && !row.currency) problems.push('currency is missing');
  if (dimensionless && row.currency) {
    problems.push(`currency ${row.currency} on a ${row.measurement_basis} figure`);
  }
  if (!Object.values(PERIOD_TYPE).includes(row.period_type)) problems.push(`period_type ${row.period_type}`);
  if (!Object.values(ENTITY_SCOPE).includes(row.entity_scope)) problems.push(`entity_scope ${row.entity_scope}`);
  if (row.measurement_basis !== null && !Object.values(MEASUREMENT).includes(row.measurement_basis)) {
    problems.push(`measurement_basis ${row.measurement_basis}`);
  }
  if (!['consolidated', 'standalone'].includes(row.accounting_scope)) problems.push(`accounting_scope ${row.accounting_scope}`);
  if (!['stated', 'derived', 'inferred', 'unsupported'].includes(row.verdict)) problems.push(`verdict ${row.verdict}`);
  if (row.unit !== null && !(Number(row.unit) > 0)) problems.push(`unit ${row.unit}`);
  return problems;
}

const chunked = (rows, size) => {
  const out = [];
  for (let at = 0; at < rows.length; at += size) out.push(rows.slice(at, at + size));
  return out;
};

/**
 * Write facts, refusing the ones the table would reject.
 *
 * Refused facts are returned rather than thrown, because one bad row in a
 * hundred should not cost the other ninety-nine, and a caller that never hears
 * which row was dropped cannot fix the reader that produced it.
 */
export async function saveFacts(client, facts, { chunk = 500 } = {}) {
  const writable = [];
  const refused = [];
  for (const [at, fact] of (facts || []).entries()) {
    const problems = unwritable(fact);
    if (problems.length) { refused.push({ at, fact, problems }); continue; }
    writable.push(toRow(fact));
  }
  let written = 0;
  for (const batch of chunked(writable, chunk)) {
    const { error } = await client.from(TABLE)
      .upsert(batch, { onConflict: IDENTITY.join(','), ignoreDuplicates: false });
    if (error) return { written, refused, error };
    written += batch.length;
  }
  return { written, refused, error: null };
}

const applyFilter = (query, filter) => {
  const only = (column, one, many) => {
    if (many?.length) return query.in(column, many);
    if (one !== undefined && one !== null) return query.eq(column, one);
    return query;
  };
  query = only('company', filter.company, filter.companies);
  query = only('concept', filter.concept, filter.concepts);
  query = only('definition_id', filter.definition_id, filter.definition_ids);
  query = only('period_end', filter.period_end, filter.period_ends);
  query = only('reported_in_document', filter.reported_in_document, filter.reported_in_documents);
  if (filter.accounting_scope) query = query.eq('accounting_scope', filter.accounting_scope);
  if (filter.segment !== undefined) query = query.eq('segment', filter.segment ?? NOT_SEGMENTAL);
  if (filter.verdict) query = query.eq('verdict', filter.verdict);
  return query;
};

/**
 * Read facts, all of them.
 *
 * Paged explicitly because an unbounded select returns a thousand rows and no
 * indication that there were more. A page that comes back full is followed by
 * another; a short page ends it.
 */
export async function loadFacts(client, filter = {}) {
  const facts = [];
  for (let page = 0; ; page += 1) {
    const from = page * PAGE;
    const query = applyFilter(client.from(TABLE).select('*'), filter)
      .order('period_end', { ascending: false })
      .order('definition_id', { ascending: true })
      .range(from, from + PAGE - 1);
    const { data, error } = await query;
    if (error) return { facts, error, complete: false };
    facts.push(...(data || []).map(fromRow));
    // The limit is checked before the short page, or a result smaller than one
    // page would return more rows than the caller asked for. A limited read is
    // never complete, whatever else is true of it: complete means every
    // matching fact, and a caller that cannot tell the difference will treat a
    // truncated read as a company with fewer disclosures.
    if (filter.limit && facts.length >= filter.limit) {
      return { facts: facts.slice(0, filter.limit), error: null, complete: false };
    }
    if (!data || data.length < PAGE) return { facts, error: null, complete: true };
  }
}

/** Which documents a company has facts from, newest period first. */
export async function documentsFor(client, company) {
  const { facts, error } = await loadFacts(client, { company });
  if (error) return { documents: [], error };
  const seen = new Map();
  for (const fact of facts) {
    const held = seen.get(fact.reported_in_document) || { document: fact.reported_in_document, facts: 0, latest_period: null };
    held.facts += 1;
    if (!held.latest_period || fact.period_end > held.latest_period) held.latest_period = fact.period_end;
    seen.set(fact.reported_in_document, held);
  }
  return { documents: [...seen.values()].sort((a, b) => (b.latest_period || '').localeCompare(a.latest_period || '')), error: null };
}
