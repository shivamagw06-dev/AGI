/**
 * When a figure applies to, and what may be compared with what.
 *
 * "FY26" is not a period. Reliance's FY26 ends 31 March 2026, Berkshire's
 * ends 31 December 2025, and a retailer's ends on whichever Saturday is
 * nearest. Putting them in one column because they share a label produces a
 * comparison no one made and no one can defend, so nothing here takes a
 * fiscal-year label as input or invents one as output. Periods are dates, and
 * two periods are comparable to the extent that they cover the same calendar
 * time - reported as a proportion, not as a yes.
 *
 * Within one company the trap is different. Reliance's capital expenditure
 * rose 10.0% on management's definition and fell 12.2% on the cash flow
 * statement's, in the same year, so a growth rate means nothing without the
 * definition attached. And a prior-year figure restated in this year's report
 * is not the figure that was published last year: comparing across documents
 * can manufacture growth that no one reported. Both years are taken from one
 * document wherever a document gives both.
 *
 * The last thing here is the look-ahead guard. `asOf` keeps only facts from
 * documents known to have been published by a date, and a document whose
 * publication date is unknown is excluded rather than assumed - defaulting the
 * unknown case to "include" is exactly how look-ahead gets in.
 */
import { statedPrecision } from './factVerification.js';

const round = (value, places = 6) => Number(value.toFixed(places));
const DAY = 86400000;

/** How long each kind of period runs, in months. */
export const MONTHS_IN = Object.freeze({ annual: 12, half_year: 6, quarterly: 3, monthly: 1 });

const asDate = (text) => {
  const parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(text ?? ''));
  return parts ? Date.UTC(Number(parts[1]), Number(parts[2]) - 1, Number(parts[3])) : null;
};

const back = (stamp, months) => {
  const date = new Date(stamp);
  const target = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() - months, 1));
  // Keep the day of month where the month is long enough to hold it, which is
  // what "twelve months back from 31 March" means to everyone who says it.
  const lastDay = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate();
  return Date.UTC(target.getUTCFullYear(), target.getUTCMonth(), Math.min(date.getUTCDate(), lastDay));
};

/**
 * The span a fact covers.
 *
 * Derived from the declared period type unless the fact states its own start.
 * A 52/53-week year is not twelve months, and an issuer that reports one
 * should say so on the fact rather than have this guess.
 */
export function periodOf(fact) {
  const end = asDate(fact?.period_end);
  if (end === null) return null;
  const type = fact?.period_type || 'annual';
  const months = MONTHS_IN[type];
  const stated = asDate(fact?.period_start);
  if (stated === null && months === undefined) return null;
  const start = stated ?? back(end + DAY, months);
  return { start, end, type, days: Math.round((end + DAY - start) / DAY), stated_start: stated !== null };
}

/** How much calendar time two periods share. */
export function overlapOf(a, b) {
  const first = periodOf(a);
  const second = periodOf(b);
  if (!first || !second) return null;
  const from = Math.max(first.start, second.start);
  const to = Math.min(first.end, second.end);
  const days = to < from ? 0 : Math.round((to + DAY - from) / DAY);
  const shorter = Math.min(first.days, second.days);
  return { days, share_of_shorter: shorter === 0 ? null : round(days / shorter, 6) };
}

const monthsBetween = (a, b) => {
  const one = new Date(a);
  const two = new Date(b);
  return (two.getUTCFullYear() - one.getUTCFullYear()) * 12 + (two.getUTCMonth() - one.getUTCMonth());
};

/**
 * Whether two periods may be put side by side, and how far apart they are.
 *
 * Never a bare yes. A nine-month overlap between an Indian March year-end and
 * an American December one is usable for some questions and not for others,
 * and the number is what lets a reader decide which.
 */
export function comparable(a, b) {
  const first = periodOf(a);
  const second = periodOf(b);
  if (!first || !second) return { status: 'unknown_period', overlap: null };
  if (first.type !== second.type) {
    return { status: 'different_length', overlap: overlapOf(a, b),
      reason: `${first.type} against ${second.type}` };
  }
  const overlap = overlapOf(a, b);
  const offset = monthsBetween(first.end, second.end);
  if (overlap.share_of_shorter >= 0.95) return { status: 'aligned', overlap, offset_months: offset };
  if (overlap.share_of_shorter >= 0.5) {
    return { status: 'offset', overlap, offset_months: offset,
      reason: `year-ends are ${Math.abs(offset)} months apart` };
  }
  return { status: 'not_comparable', overlap, offset_months: offset,
    reason: `the periods share ${overlap.days} days` };
}

/**
 * What was knowable on a date.
 *
 * A document with no known publication date is excluded and named. Including
 * it would mean asserting the filing existed when the question is precisely
 * whether it did.
 */
export function asOf(facts, { on, documents = {} }) {
  const cutoff = asDate(on);
  const kept = [];
  const excluded = [];
  for (const fact of facts || []) {
    if (!fact) continue;
    const published = asDate(documents[fact.reported_in_document]);
    if (cutoff === null) { excluded.push({ fact, reason: `${on} is not a date` }); continue; }
    if (published === null) {
      excluded.push({ fact, reason: `publication date of ${fact.reported_in_document} is unknown` });
      continue;
    }
    if (published > cutoff) {
      excluded.push({ fact, reason: `${fact.reported_in_document} was published ${documents[fact.reported_in_document]}` });
      continue;
    }
    kept.push(fact);
  }
  return { facts: kept, excluded };
}

const matching = (facts, { definition_id, accounting_scope = 'consolidated', segment = null, period_end }) =>
  (facts || []).filter((fact) => fact
    && fact.definition_id === definition_id
    && (fact.accounting_scope || 'consolidated') === accounting_scope
    && (fact.segment || null) === (segment || null)
    && fact.period_end === period_end
    && Number.isFinite(Number(fact.value)));

/**
 * The change in one definition between two periods.
 *
 * Both years come from one document wherever a document reports both, because
 * a comparative restated in this year's report is not the figure published
 * last year and the difference between them is not growth.
 */
export function changeIn({
  facts, definition_id, from, to,
  accounting_scope = 'consolidated', segment = null, stated = null,
}) {
  const where = { definition_id, accounting_scope, segment };
  const base = { definition_id, from, to, accounting_scope, segment };
  const earlier = matching(facts, { ...where, period_end: from });
  const later = matching(facts, { ...where, period_end: to });
  if (!earlier.length || !later.length) {
    return { ...base, status: 'insufficient_data',
      reason: `${definition_id} is not disclosed for ${!earlier.length ? from : to}` };
  }
  const types = new Set([...earlier, ...later].map((fact) => fact.period_type || 'annual'));
  if (types.size > 1) {
    return { ...base, status: 'different_length', reason: `comparing ${[...types].join(' with ')}` };
  }
  const span = overlapOf(earlier[0], later[0]);
  if (span && span.days > 0) {
    return { ...base, status: 'overlapping_periods', reason: `the periods share ${span.days} days` };
  }
  const units = new Set([...earlier, ...later].map((fact) => `${fact.currency ?? ''}|${fact.unit ?? ''}`));
  if (units.size > 1) {
    return { ...base, status: 'not_comparable', reason: `figures are stated in ${[...units].join(' and ')}` };
  }

  const caveats = [];
  let pair = null;
  let basis = null;
  const shared = [...new Set(later.map((fact) => fact.reported_in_document))]
    .filter((document) => earlier.some((fact) => fact.reported_in_document === document));
  if (shared.length) {
    const pairs = shared.map((document) => ({
      document,
      from: earlier.find((fact) => fact.reported_in_document === document),
      to: later.find((fact) => fact.reported_in_document === document),
    }));
    const distinct = new Set(pairs.map((row) => `${row.from.value}|${row.to.value}`));
    if (distinct.size > 1) {
      return { ...base, status: 'restated',
        reason: 'documents reporting both periods do not agree',
        reported_in: pairs.map((row) => ({ document: row.document, from: Number(row.from.value), to: Number(row.to.value) })) };
    }
    pair = pairs[0];
    basis = 'same_document';
  } else {
    if (earlier.length > 1 || later.length > 1) {
      return { ...base, status: 'restated',
        reason: 'more than one document reports a period and none reports both',
        reported_in: [...earlier, ...later].map((fact) => ({ document: fact.reported_in_document, period_end: fact.period_end, value: Number(fact.value) })) };
    }
    pair = { document: null, from: earlier[0], to: later[0] };
    basis = 'across_documents';
    // The prior year as this year's report restates it is a different figure
    // from the prior year as it was published, and the gap between them is not
    // growth.
    caveats.push(`the two periods come from different documents (${earlier[0].reported_in_document} and ${later[0].reported_in_document}); a restated comparative would show here as growth`);
  }

  const before = Number(pair.from.value);
  const after = Number(pair.to.value);
  const change = round(after - before, 6);
  // A percentage from a base of zero or less says nothing true. The absolute
  // change still does, so it is reported either way.
  const growth = before > 0 ? round(change / before, 6) : null;
  if (growth === null) caveats.push(`growth is not reported from a base of ${before}`);

  const result = {
    ...base, status: 'measured', basis, document: pair.document,
    from_value: before, to_value: after, change, growth, caveats,
  };
  if (!stated || growth === null) return { ...result, also_stated: null };

  const slack = 0.5 * (10 ** -statedPrecision({ value: stated.value, source_sentence: stated.source_sentence }));
  return {
    ...result,
    also_stated: {
      value: Number(stated.value),
      difference: round(growth - Number(stated.value), 9),
      within_rounding: Math.abs(growth - Number(stated.value)) <= slack,
    },
  };
}

/** One definition across every period disclosed, oldest first, with each step. */
export function seriesOf({ facts, definition_id, accounting_scope = 'consolidated', segment = null }) {
  const ends = [...new Set((facts || [])
    .filter((fact) => fact && fact.definition_id === definition_id
      && (fact.accounting_scope || 'consolidated') === accounting_scope
      && (fact.segment || null) === (segment || null))
    .map((fact) => fact.period_end))].sort();
  const steps = [];
  for (let at = 1; at < ends.length; at += 1) {
    steps.push(changeIn({ facts, definition_id, accounting_scope, segment, from: ends[at - 1], to: ends[at] }));
  }
  return { definition_id, accounting_scope, segment, period_ends: ends, steps };
}
