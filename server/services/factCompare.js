/**
 * The same question asked of several companies at once.
 *
 * "Capital expenditure for these five, latest year" looks like a column of
 * numbers and is four questions underneath: whether each company disclosed the
 * thing, which of its definitions to take, whether the years line up, and
 * whether the figures are even in the same money. A column that answers the
 * first and assumes the rest is the most confident wrong answer this system
 * could produce, because it looks exactly like the right one.
 *
 * So a comparison here is returned with what would make it invalid attached.
 * Every row says which definition it used and why; every pair of companies
 * says how far their periods are apart; and a table whose rows are not
 * comparable says so rather than lining them up anyway.
 *
 * Currencies are never converted. Reliance reports in rupee crore and a US
 * filer in dollar millions, and turning one into the other needs a rate on a
 * date - which this system does not have and will not invent. The figures come
 * back in the money they were reported in, and the comparison is marked
 * unusable until a caller supplies what is missing.
 */
import { comparable } from './factPeriods.js';
import { reconcileFamily } from './factReconciliation.js';
import { loadFacts } from './factStore.js';

/** The latest period each company has for a concept. */
export function latestPeriods(facts, concept) {
  const latest = new Map();
  for (const fact of facts || []) {
    if (!fact || (concept && fact.concept !== concept)) continue;
    const held = latest.get(fact.company);
    if (!held || fact.period_end > held) latest.set(fact.company, fact.period_end);
  }
  return latest;
}

const moneyOf = (row) => (row?.chosen ? `${row.chosen.currency ?? ''}|${row.chosen.unit ?? ''}` : null);

/**
 * One concept across several companies, with everything that could invalidate
 * the comparison attached to it.
 */
export function compare({
  facts, concept, companies, periods = {}, purpose, prefer = {},
  accounting_scope = 'consolidated', segment = null,
}) {
  const wanted = companies?.length
    ? companies
    : [...new Set((facts || []).filter((fact) => fact?.concept === concept).map((fact) => fact.company))].sort();
  const fallback = latestPeriods(facts, concept);

  // Every row has the same keys, including the rows that answer nothing. A
  // column where some rows lack `value` and others have it reads as a gap in
  // the data rather than as a company that did not disclose the thing.
  const blank = (company, status, reason = null) => ({
    company, period_end: null, status, definition_id: null, value: null,
    currency: null, unit: null, as_reported_label: null, rule: null,
    chosen_at_rank: null, chosen: null, forgone: [], candidates: null, reason, caveats: [],
  });

  const rows = wanted.map((company) => {
    const period_end = periods[company] || fallback.get(company) || null;
    if (!period_end) return blank(company, 'not_disclosed', `${company} has no ${concept} on record`);
    const mine = (facts || []).filter((fact) => fact?.company === company);
    const picked = reconcileFamily({
      facts: mine, concept, period_end, accounting_scope, segment, purpose, prefer,
    });
    return {
      company,
      period_end,
      status: picked.status,
      definition_id: picked.chosen?.definition_id ?? null,
      value: picked.chosen ? Number(picked.chosen.value) : null,
      currency: picked.chosen?.currency ?? null,
      unit: picked.chosen?.unit ?? null,
      as_reported_label: picked.chosen?.as_reported_label ?? null,
      rule: picked.rule ?? null,
      chosen_at_rank: picked.chosen_at_rank ?? null,
      chosen: picked.chosen ?? null,
      forgone: picked.forgone || [],
      candidates: picked.candidates || null,
      reason: picked.reason || null,
      caveats: picked.caveats || [],
    };
  });

  const settled = rows.filter((row) => row.chosen);
  const comparability = [];
  for (let i = 0; i < settled.length; i += 1) {
    for (let j = i + 1; j < settled.length; j += 1) {
      const check = comparable(
        { period_end: settled[i].period_end, period_type: settled[i].chosen.period_type },
        { period_end: settled[j].period_end, period_type: settled[j].chosen.period_type },
      );
      comparability.push({ between: [settled[i].company, settled[j].company], ...check });
    }
  }

  const blockers = [];
  for (const row of rows) {
    if (!row.chosen) blockers.push({ company: row.company, why: row.reason || row.status });
  }
  for (const row of settled) {
    if (row.chosen_at_rank > 0) blockers.push({ company: row.company, why: row.caveats[0] || 'a substituted measurement basis' });
  }
  const monies = [...new Set(settled.map(moneyOf))];
  if (monies.length > 1) {
    // Converting would need a rate on a date. There isn't one here, and
    // inventing one would put a fabricated number in the middle of a
    // comparison that looks arithmetic.
    blockers.push({ company: null, why: `figures are reported in ${monies.length} different currencies or units and are not converted` });
  }
  for (const pair of comparability) {
    if (pair.status !== 'aligned') {
      blockers.push({ company: pair.between.join(' and '), why: pair.reason || pair.status });
    }
  }

  return {
    concept, purpose: purpose || null, accounting_scope, segment,
    rows, comparability, blockers,
    usable: blockers.length === 0,
  };
}

/**
 * The same comparison, ordered - but only where ordering means anything.
 *
 * A ranking over figures that are not comparable is the thing a reader is most
 * likely to act on and least likely to check, so it is withheld rather than
 * qualified.
 */
export function rankCompanies(comparison, { descending = true } = {}) {
  if (!comparison.usable) {
    return { ordered: null, withheld: true, blockers: comparison.blockers };
  }
  const ordered = comparison.rows
    .filter((row) => row.value !== null)
    .sort((a, b) => (descending ? b.value - a.value : a.value - b.value))
    .map((row, at) => ({ position: at + 1, company: row.company, value: row.value,
      definition_id: row.definition_id, period_end: row.period_end }));
  return { ordered, withheld: false, blockers: [] };
}

/** The same question, against the store. */
export async function compareAcross(client, {
  companies, concept, periods = {}, purpose, prefer = {},
  accounting_scope = 'consolidated', segment = null, limit,
}) {
  const { facts, error, complete } = await loadFacts(client, { companies, concept, accounting_scope, limit });
  if (error) return { error, comparison: null };
  const comparison = compare({ facts, concept, companies, periods, purpose, prefer, accounting_scope, segment });
  if (!complete) {
    comparison.blockers.push({ company: null, why: 'the read did not return every matching fact' });
    comparison.usable = false;
  }
  return { error: null, comparison };
}
