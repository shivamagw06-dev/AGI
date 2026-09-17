/**
 * Product A behind Product B.
 *
 * The AI dashboard does not parse filings. It asks the fact store, which has
 * already made every figure cite itself, and carries the citation through to
 * the page. "Kaynes capex intensity increased" has to resolve to the rows it
 * came from and the arithmetic that produced it, or it is a sentence with a
 * number in it.
 *
 * Two things this module exists to get right.
 *
 * First, identity. A universe member is an NSE symbol and an ISIN; a fact
 * belongs to a `company` key in the store. Those are different namespaces and
 * guessing between them silently attaches one company's filings to another.
 * The mapping is declared, and an undeclared member resolves to nothing
 * rather than to a plausible neighbour.
 *
 * Second, and this is the one that matters: the store's five states do not
 * include "we have never read a filing for this company". Ask
 * resolveConcept() about a company with no ingested document and it reports
 * NOT_DISCLOSED - "places in the filing were searched and none disclosed it"
 * - which is a false statement about a filing nobody opened. On a dashboard
 * that reads as "this company discloses no capex". So the ingestion check
 * comes first, and NOT_INGESTED is its own answer.
 */

import { loadFacts } from './factStore.js';
import { DEFINITIONS } from './factOntology.js';
import { calculate, lineage, isStale } from './factCalculation.js';

/**
 * What the dashboard can be told about one concept.
 *
 * NOT_INGESTED and NOT_DISCLOSED are the pair that has to stay apart: one is
 * a gap in our reading, the other is a fact about the company.
 */
export const FUNDAMENTAL_STATE = Object.freeze({
  NOT_INGESTED: 'not_ingested',
  FOUND: 'found',
  DERIVED: 'derived',
  NOT_DISCLOSED: 'not_disclosed',
});

/** The concepts the AI dashboard asks for. */
export const DASHBOARD_CONCEPTS = Object.freeze([
  'capex', 'debt', 'ebitda', 'revenue', 'cfo',
]);

/**
 * A member's key in the fact store.
 *
 * Declared on the member as `factStoreKey`. There is no fallback to the
 * symbol on purpose: NSE symbols and the store's company keys are different
 * namespaces, and a member whose mapping nobody has declared must read as
 * unmapped rather than as a company with no disclosures.
 */
export function factStoreKeyFor(member) {
  const declared = String(member?.factStoreKey || '').trim();
  return declared || null;
}

/**
 * Add a declared mapping to each member, where one is known.
 *
 * Kept as data rather than inferred. When an annual report is ingested for a
 * member, its store key goes in the universe file beside the ISIN, and this
 * is where the two namespaces are joined - once, visibly.
 */
export function withFactStoreKeys(universe, keysBySymbol = {}) {
  return {
    ...universe,
    members: (universe?.members || []).map((member) => (
      keysBySymbol[member.symbol]
        ? { ...member, factStoreKey: keysBySymbol[member.symbol] }
        : member
    )),
  };
}

/** Every definition that measures a concept. */
export function definitionsFor(concept) {
  const ids = [];
  for (const [definition_id, definition] of DEFINITIONS) {
    if (definition.concept === concept) ids.push(definition_id);
  }
  return ids;
}

const numeric = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

/**
 * One concept, for one company, at one period - with its provenance.
 *
 * `facts` is everything already loaded for the company, so a caller resolving
 * five concepts reads the store once. An empty `facts` means nothing has been
 * ingested, which is why that check is first and unconditional.
 */
export function resolveFromStore({ facts, concept, period_end, accounting_scope = 'consolidated', segment = null }) {
  if (!facts.length) {
    return {
      concept, period_end, state: FUNDAMENTAL_STATE.NOT_INGESTED, value: null,
      reason: 'no filing has been ingested for this company, so nothing is known either way',
      definition_id: null, lineage: null, citations: [],
    };
  }

  const at = (fact) => fact.period_end === period_end
    && (fact.accounting_scope || 'consolidated') === accounting_scope
    && (fact.segment || null) === (segment || null);

  const stated = facts.filter((fact) => at(fact)
    && DEFINITIONS.get(fact.definition_id)?.concept === concept
    && numeric(fact.value) !== null);

  if (stated.length) {
    // Several disclosed definitions of one concept is the normal case, not an
    // error - management capex and cash capex are both real. All of them are
    // returned with their labels so the page shows which is which rather
    // than picking one and calling it "capex".
    return {
      concept, period_end, state: FUNDAMENTAL_STATE.FOUND,
      value: numeric(stated[0].value),
      definition_id: stated[0].definition_id,
      definitions: stated.map((fact) => ({
        definition_id: fact.definition_id,
        label: DEFINITIONS.get(fact.definition_id)?.label || fact.definition_id,
        measurement: DEFINITIONS.get(fact.definition_id)?.measurement || null,
        value: numeric(fact.value),
        verdict: fact.verdict || null,
      })),
      lineage: null,
      citations: stated.map((fact) => ({
        definition_id: fact.definition_id,
        as_reported_label: fact.as_reported_label ?? null,
        source_document_id: fact.source_document_id ?? null,
        source_section: fact.source_section ?? null,
        source_page: fact.source_page ?? null,
        source_sentence: fact.source_sentence ?? null,
        reported_in_document: fact.reported_in_document ?? null,
      })),
      reason: null,
    };
  }

  // Nothing stated. Try the recipes, which is where lineage comes from.
  for (const definition_id of definitionsFor(concept)) {
    const computed = calculate(facts, { definition_id, period_end, accounting_scope, segment });
    if (computed && numeric(computed.value) !== null) {
      return {
        concept, period_end, state: FUNDAMENTAL_STATE.DERIVED,
        value: numeric(computed.value),
        definition_id,
        definitions: null,
        lineage: lineage(computed, facts),
        stale: isStale(computed, facts),
        citations: [],
        reason: null,
      };
    }
  }

  return {
    concept, period_end, state: FUNDAMENTAL_STATE.NOT_DISCLOSED, value: null,
    definition_id: null, lineage: null, citations: [],
    reason: `${facts.length} fact${facts.length === 1 ? '' : 's'} are held for this company and none of them measure ${concept} at ${period_end}`,
  };
}

/**
 * Every dashboard concept for one member, at one period.
 *
 * Reads the store once. A member with no declared mapping does not read the
 * store at all, and says so.
 */
export async function fundamentalsFor(client, member, {
  period_end, concepts = DASHBOARD_CONCEPTS, accounting_scope = 'consolidated',
} = {}) {
  const company = factStoreKeyFor(member);
  if (!company) {
    return {
      symbol: member.symbol, company: null, unmapped: true, complete: false,
      concepts: Object.fromEntries(concepts.map((concept) => [concept, {
        concept, period_end, state: FUNDAMENTAL_STATE.NOT_INGESTED, value: null,
        reason: 'this member has no declared fact-store key, so no filing can be looked up for it',
        definition_id: null, lineage: null, citations: [],
      }])),
    };
  }

  const { facts, error, complete } = await loadFacts(client, { company });
  if (error) return { symbol: member.symbol, company, error: String(error?.message || error), complete: false, concepts: {} };

  return {
    symbol: member.symbol,
    company,
    unmapped: false,
    // A truncated read is not a company with fewer disclosures. The flag
    // travels so nothing downstream reports on a partial reading as though
    // it were the whole one.
    complete,
    factCount: facts.length,
    periods: [...new Set(facts.map((fact) => fact.period_end))].sort().reverse(),
    concepts: Object.fromEntries(concepts.map((concept) => [
      concept,
      resolveFromStore({ facts, concept, period_end, accounting_scope }),
    ])),
  };
}

/** The whole universe, one member at a time. */
export async function fundamentalsForUniverse(client, universe, options = {}) {
  const members = (universe?.members || []).filter((one) => one.admitted !== false);
  const bySymbol = {};
  for (const member of members) {
    bySymbol[member.symbol] = await fundamentalsFor(client, member, options);
  }
  const ingested = Object.values(bySymbol).filter(
    (one) => one.factCount > 0).map((one) => one.symbol);
  return {
    bySymbol,
    ingested,
    notIngested: members.map((one) => one.symbol).filter((symbol) => !ingested.includes(symbol)),
    unmapped: Object.values(bySymbol).filter((one) => one.unmapped).map((one) => one.symbol),
  };
}

/**
 * Stage 3's inputs, from the fact store.
 *
 * This is the join the architecture was for: the screen's investment-intensity
 * stage stops being a set of numbers somebody typed and becomes a derivation
 * over cited filing rows. Every ratio returned carries the periods and the
 * definitions it was built from, so "capex intensity increased" can be opened.
 *
 * A ratio whose inputs are not all present is null with a reason. It is never
 * a zero, and never a figure built from one disclosed year standing in for
 * three.
 */
export function intensityFrom(facts, { periods, accounting_scope = 'consolidated' } = {}) {
  const ordered = [...new Set(periods || facts.map((fact) => fact.period_end))].sort().reverse();
  const valueAt = (concept, period_end) => {
    const resolved = resolveFromStore({ facts, concept, period_end, accounting_scope });
    return resolved.value === null ? null : { ...resolved };
  };

  const latest = ordered[0] ?? null;
  const prior = ordered[1] ?? null;
  const threeBack = ordered[3] ?? null;     // FY-3, for a three-year CAGR

  const provenance = [];
  const record = (label, resolved) => {
    if (resolved) provenance.push({ input: label, ...resolved });
    return resolved;
  };

  const capexNow = latest ? record('capex@latest', valueAt('capex', latest)) : null;
  const capexPrior = prior ? record('capex@prior', valueAt('capex', prior)) : null;
  const revenueNow = latest ? record('revenue@latest', valueAt('revenue', latest)) : null;
  const revenueThreeBack = threeBack ? record('revenue@fy-3', valueAt('revenue', threeBack)) : null;

  const ratio = (numerator, denominator) =>
    (numerator?.value != null && denominator?.value != null && denominator.value !== 0
      ? numerator.value / denominator.value
      : null);

  const capexToSales = ratio(capexNow, revenueNow);
  const capexGrowth = capexNow?.value != null && capexPrior?.value != null && capexPrior.value !== 0
    ? capexNow.value / capexPrior.value - 1
    : null;
  const revenueCagr3y = revenueNow?.value != null && revenueThreeBack?.value != null && revenueThreeBack.value > 0
    ? (revenueNow.value / revenueThreeBack.value) ** (1 / 3) - 1
    : null;

  return {
    periods: { latest, prior, threeBack },
    capexToSales,
    capexGrowth,
    revenueCagr3y,
    // R&D is not in the dashboard concept set yet, so it is absent rather
    // than inferred from anything that happens to be nearby.
    rndToSales: null,
    unavailable: [
      ...(capexToSales === null ? ['capexToSales'] : []),
      ...(capexGrowth === null ? ['capexGrowth'] : []),
      ...(revenueCagr3y === null ? ['revenueCagr3y'] : []),
      'rndToSales',
    ],
    provenance,
  };
}

/**
 * Stage 3 inputs for the universe, in the shape `stageThree` reads.
 *
 * Members with nothing ingested come back with null ratios, which stageThree
 * correctly reports as unscreened rather than as failing.
 */
export async function intensityForUniverse(client, universe, { accounting_scope = 'consolidated' } = {}) {
  const members = (universe?.members || []).filter((one) => one.admitted !== false);
  const rows = [];
  const detail = {};
  for (const member of members) {
    const company = factStoreKeyFor(member);
    if (!company) {
      rows.push({ symbol: member.symbol });
      detail[member.symbol] = { unmapped: true, provenance: [] };
      continue;
    }
    const { facts, error, complete } = await loadFacts(client, { company });
    if (error) {
      rows.push({ symbol: member.symbol });
      detail[member.symbol] = { error: String(error?.message || error), provenance: [] };
      continue;
    }
    const intensity = intensityFrom(facts, { accounting_scope });
    rows.push({
      symbol: member.symbol,
      capexToSales: intensity.capexToSales,
      capexGrowth: intensity.capexGrowth,
      revenueCagr3y: intensity.revenueCagr3y,
      rndToSales: intensity.rndToSales,
    });
    detail[member.symbol] = { ...intensity, complete, factCount: facts.length };
  }
  return { rows, detail };
}
