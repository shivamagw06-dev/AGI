/**
 * What a manager said, read back for a page.
 *
 * Two shapes, because there are two questions. Grouped by step answers "what
 * did this manager say about its business"; grouped by holding answers "what
 * did it say about this position". Both return the filer's own sentences.
 *
 * Only approved claims are published. Pending ones are counted and named, not
 * shown: a page that hides them implies the document said nothing on that
 * step, when in fact 142 causes and 15 stated expectations are sitting in a
 * queue. The count is the honest form of "not yet".
 *
 * The holdings vocabulary comes from the manager's own 13F, so the join is
 * between two things the manager filed. Reading holdings is expensive and is
 * done only for managers that have a publication - one of fifty today.
 */
import { CHAIN } from './publicationIntelligence.js';
import { claimsByHolding, claimsByStep, heldIssuerVocabulary } from './publicationSaid.js';

const STEP_ORDER = CHAIN.map((step) => step.slot);
const QUESTION = Object.fromEntries(CHAIN.map((step) => [step.slot, step.question]));

/**
 * One manager's publications, claims and holdings, shaped for a card.
 *
 * Pure, so the grouping rules are testable without a database. `facts` is
 * every row for the manager - approved and pending - because the pending count
 * per step is part of what the page shows.
 */
export function buildSaid({ publications = [], facts = [], holdingNames = [], managerName = '' }) {
  if (!publications.length) return null;
  const claims = facts.filter((row) => row.kind === 'chain_claim');
  const approved = claims.filter((row) => row.status === 'approved');
  const vocabulary = heldIssuerVocabulary(holdingNames, { exclude: [managerName] });

  const pendingByStep = new Map();
  for (const row of claims) {
    if (row.status === 'approved') continue;
    pendingByStep.set(row.slot, (pendingByStep.get(row.slot) || 0) + 1);
  }

  return {
    publications: publications.map(({ id, title, as_of_date, source_url, pasted_at }) => ({
      id, title, as_of_date, source_url, pasted_at,
    })),
    // The disclosed-holdings rows, which are table facts rather than chain
    // steps and carry a scale nobody has checked yet.
    disclosed: facts
      .filter((row) => row.kind === 'disclosed_holding')
      .map(({ issuer, percent_owned, market_value, cost_basis, unit, status }) => ({
        issuer, percent_owned, market_value, cost_basis, unit, status,
      })),
    by_step: claimsByStep(approved, STEP_ORDER).map((group) => ({
      ...group,
      question: QUESTION[group.slot] || group.slot,
    })),
    // Positions the filer actually wrote about. Most holdings appear here not
    // at all: a fair-value equity is disclosed in a table and discussed
    // nowhere, which is an accounting boundary rather than a gap. An absent
    // position must render as absent, never as "no comment".
    by_holding: claimsByHolding(approved, vocabulary),
    // Named rather than hidden. Without this the page implies the document was
    // silent on the steps whose claims are still in the queue.
    awaiting_review: STEP_ORDER
      .filter((slot) => pendingByStep.get(slot))
      .map((slot) => ({ slot, question: QUESTION[slot] || slot, pending: pendingByStep.get(slot) })),
    approved_count: approved.length,
    // The two steps no extractor fills, carried through so a page can render
    // the gap with its reason instead of showing seven steps as the chain.
    unreachable: CHAIN.filter((step) => !step.extractable)
      .map(({ slot, question, reason }) => ({ slot, question, reason })),
  };
}

/**
 * Issuer names a manager holds, from its most recent active filing.
 *
 * `paged` is passed in rather than imported. The research layer owns it and
 * calls this, so importing it back would make the two modules a cycle; and
 * writing a second pager here is worse, because every unbounded read in this
 * codebase has silently truncated at PostgREST's thousand rows at least once.
 */
async function holdingNamesFor(client, managerId, paged) {
  const filings = await paged(
    () => client.from('institutional_filings').select('id')
      .eq('manager_id', managerId).eq('is_active', true)
      .order('report_date', { ascending: false }).limit(1),
    { label: 'said-filing' },
  );
  if (!filings.length) return [];
  const holdings = await paged(
    () => client.from('institutional_holdings').select('issuer_name').eq('filing_id', filings[0].id),
    { label: 'said-holdings' },
  );
  return [...new Set(holdings.map((row) => row.issuer_name).filter(Boolean))];
}

/**
 * What every manager with a publication said, keyed by manager id.
 *
 * Returns an empty Map when nothing has been pasted, so a caller can attach it
 * unconditionally and forty-nine managers simply get null.
 */
export async function saidByManager(client, managers = [], { paged }) {
  const publications = await paged(
    () => client.from('manager_publications').select('*').order('pasted_at', { ascending: false }),
    { label: 'publications' },
  );
  if (!publications.length) return new Map();

  const byManager = new Map();
  for (const publication of publications) {
    if (!byManager.has(publication.manager_id)) byManager.set(publication.manager_id, []);
    byManager.get(publication.manager_id).push(publication);
  }

  const facts = await paged(
    () => client.from('manager_publication_facts')
      .select('manager_id,kind,slot,basis,metric,segment,segment_source,themes,figures,change,issuer,percent_owned,cost_basis,market_value,unit,source_excerpt,status')
      .in('manager_id', [...byManager.keys()])
      .order('id'),
    { label: 'publication-facts' },
  );
  const factsOf = new Map();
  for (const row of facts) {
    if (!factsOf.has(row.manager_id)) factsOf.set(row.manager_id, []);
    factsOf.get(row.manager_id).push(row);
  }

  const said = new Map();
  for (const [managerId, rows] of byManager) {
    const manager = managers.find((entry) => entry.id === managerId) || null;
    const built = buildSaid({
      publications: rows,
      facts: factsOf.get(managerId) || [],
      holdingNames: await holdingNamesFor(client, managerId, paged),
      managerName: manager?.display_name || '',
    });
    if (built) said.set(managerId, built);
  }
  return said;
}
