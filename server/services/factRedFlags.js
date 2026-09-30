/**
 * What in this filing a careful reader should look at.
 *
 * A flag here is a pointer, never a verdict. It says what is observably true -
 * "capital expenditure rose 10.0% on one disclosed definition and fell 12.2%
 * on another" - and stops. It does not say the accounting is aggressive, that
 * management is hiding something, or that the number is wrong, because none of
 * those follow from the filing and all of them would be this system inventing
 * the thing it exists to avoid.
 *
 * Every flag comes from an output the other modules already produced, and
 * carries the numbers that produced it. Nothing is flagged on a pattern this
 * file noticed on its own.
 *
 * The thresholds are the weak point and are treated as one. They are
 * conventions, not findings: each is a named constant, each is overridable,
 * and every flag reports its magnitude so a reader who disagrees with the
 * threshold can apply their own. Where a rule rests on an assumption about
 * what ought to move together, the assumption is written out and travels with
 * the flag.
 */
import { DEFINITIONS, measuredQuantity } from './factOntology.js';
import { verify, FREE_CASH_FLOW } from './factVerification.js';
import { isStale, RECIPES } from './factCalculation.js';
import { changeIn } from './factPeriods.js';

const round = (value, places = 6) => Number(value.toFixed(places));

/**
 * Thresholds, which are conventions rather than findings.
 *
 * Nothing becomes true at 5% that was false at 4.9%. These exist so the output
 * is a shortlist rather than everything, and every flag carries its magnitude
 * so a reader can draw the line somewhere else.
 */
export const CONVENTIONS = Object.freeze({
  definition_spread: 0.05,
  growth_gap: 0.05,
  restatement: 0.01,
});

/**
 * Pairs whose divergence is worth a look, and why.
 *
 * This is the one place a judgement is embedded, so the judgement is written
 * down and returned with the flag rather than left in the code as an
 * unexplained rule. A reader who rejects the premise can dismiss the flag.
 */
export const WATCHED_PAIRS = Object.freeze([
  { a: 'ebitda', b: 'cfo', why: 'accrual earnings against the cash they produced' },
  { a: 'revenue', b: 'cfo', why: 'sales against the cash they produced' },
]);

/** The order flags are presented in. A convention, not a score. */
export const RULE_ORDER = Object.freeze([
  'definition_sign_split', 'unexplained_stated_figure', 'definition_mismatch',
  'restatement', 'stale_derivation', 'definition_spread', 'growth_gap',
  'segment_residual', 'disclosure_dropped',
]);

const scopeOf = (fact) => fact?.accounting_scope || 'consolidated';

const flag = (rule, { observation, magnitude, evidence, basis, assumption = null }) => ({
  rule, observation, magnitude: magnitude === null ? null : round(magnitude, 6), evidence, basis, assumption,
  // Stated explicitly so nothing downstream mistakes a pointer for a
  // conclusion about the company.
  judgement: null,
});

const groupFacts = (facts, { period_end, accounting_scope = 'consolidated', segment = null }) =>
  (facts || []).filter((fact) => fact
    && fact.period_end === period_end
    && scopeOf(fact) === accounting_scope
    && (fact.segment || null) === (segment || null)
    && Number.isFinite(Number(fact.value)));

const conceptsIn = (facts) => [...new Set(facts.map((fact) => fact.concept))].sort();

/**
 * One concept moving in two directions at once.
 *
 * The strongest thing this file can say, because it needs no threshold: a
 * reader told capital expenditure grew and a reader told it shrank were both
 * reading the same filing.
 */
export function signSplits({ facts, from, to, accounting_scope = 'consolidated', segment = null }) {
  const flags = [];
  const current = groupFacts(facts, { period_end: to, accounting_scope, segment });
  for (const concept of conceptsIn(current)) {
    const definitions = [...new Set(current.filter((fact) => fact.concept === concept)
      .map((fact) => fact.definition_id))].sort();
    if (definitions.length < 2) continue;
    const moves = definitions
      .map((definition_id) => ({ definition_id, change: changeIn({ facts, definition_id, from, to, accounting_scope, segment }) }))
      .filter((row) => row.change.status === 'measured' && row.change.growth !== null);
    if (moves.length < 2) continue;
    const up = moves.filter((row) => row.change.growth > 0);
    const down = moves.filter((row) => row.change.growth < 0);
    if (!up.length || !down.length) continue;
    const high = up.reduce((best, row) => (row.change.growth > best.change.growth ? row : best));
    const low = down.reduce((best, row) => (row.change.growth < best.change.growth ? row : best));
    flags.push(flag('definition_sign_split', {
      observation: `${concept} rose ${(high.change.growth * 100).toFixed(1)}% on ${high.definition_id} and fell ${(Math.abs(low.change.growth) * 100).toFixed(1)}% on ${low.definition_id} over the same period`,
      magnitude: high.change.growth - low.change.growth,
      basis: 'periods',
      evidence: moves.map((row) => ({
        definition_id: row.definition_id, from: row.change.from_value,
        to: row.change.to_value, growth: row.change.growth, basis: row.change.basis,
      })),
    }));
  }
  return flags;
}

/**
 * Two definitions of one quantity far apart in a single period.
 *
 * Of one quantity, not of one concept. Gross debt and net debt share the
 * concept "debt" and are not two readings of one number - the 200% between
 * them is the cash balance, and flagging it would fire on every filing that
 * discloses both, which is all of them. All three capital expenditure
 * definitions do compete to be capital expenditure, and the 17.4% between them
 * is about accruals and timing. The ontology says which is which.
 */
export function definitionSpreads({ facts, period_end, accounting_scope = 'consolidated', segment = null, threshold = CONVENTIONS.definition_spread }) {
  const flags = [];
  const current = groupFacts(facts, { period_end, accounting_scope, segment });
  const quantities = [...new Set(current.map((fact) => measuredQuantity(fact.definition_id))
    .filter(Boolean))].sort();
  for (const quantity of quantities) {
    const rows = current.filter((fact) => measuredQuantity(fact.definition_id) === quantity);
    const concept = rows[0].concept;
    const units = new Set(rows.map((fact) => `${fact.currency ?? ''}|${fact.unit ?? ''}`));
    if (rows.length < 2 || units.size > 1) continue;
    const values = rows.map((fact) => Number(fact.value));
    const high = Math.max(...values);
    const low = Math.min(...values);
    if (high === low) continue;
    // A proportion of zero or of a negative base says nothing true, so the
    // divergence is still reported and the magnitude is withheld rather than
    // the whole flag being dropped.
    const spread = low > 0 ? (high - low) / low : null;
    if (spread !== null && spread < threshold) continue;
    flags.push(flag('definition_spread', {
      observation: spread === null
        ? `${concept} is disclosed from ${low} to ${high}, which is not expressible as a proportion of ${low}`
        : `${concept} is disclosed from ${low} to ${high}, a spread of ${(spread * 100).toFixed(1)}% of the smaller figure`,
      magnitude: spread,
      basis: 'facts',
      evidence: rows.map((fact) => ({ definition_id: fact.definition_id, value: Number(fact.value),
        measurement: fact.measurement_basis || DEFINITIONS.get(fact.definition_id)?.measurement || null,
        as_reported_label: fact.as_reported_label ?? null })),
    }));
  }
  return flags;
}

/** Two things that usually move together, moving apart. */
export function growthGaps({ facts, from, to, accounting_scope = 'consolidated', segment = null, threshold = CONVENTIONS.growth_gap, pairs = WATCHED_PAIRS }) {
  const flags = [];
  const current = groupFacts(facts, { period_end: to, accounting_scope, segment });
  const pick = (concept) => {
    const rows = current.filter((fact) => fact.concept === concept);
    // One definition only. Where a concept is disclosed several ways, which
    // one moved is the reader's question and definition_sign_split already
    // asks it.
    return rows.length === 1 ? rows[0].definition_id : null;
  };
  for (const pair of pairs) {
    const first = pick(pair.a);
    const second = pick(pair.b);
    if (!first || !second) continue;
    const a = changeIn({ facts, definition_id: first, from, to, accounting_scope, segment });
    const b = changeIn({ facts, definition_id: second, from, to, accounting_scope, segment });
    if (a.status !== 'measured' || b.status !== 'measured') continue;
    if (a.growth === null || b.growth === null) continue;
    const gap = a.growth - b.growth;
    if (Math.abs(gap) < threshold) continue;
    flags.push(flag('growth_gap', {
      observation: `${pair.a} grew ${(a.growth * 100).toFixed(1)}% while ${pair.b} grew ${(b.growth * 100).toFixed(1)}%, a gap of ${(Math.abs(gap) * 100).toFixed(1)} percentage points`,
      magnitude: Math.abs(gap),
      basis: 'periods',
      assumption: pair.why,
      evidence: [
        { concept: pair.a, definition_id: first, growth: a.growth, from: a.from_value, to: a.to_value },
        { concept: pair.b, definition_id: second, growth: b.growth, from: b.from_value, to: b.to_value },
      ],
    }));
  }
  return flags;
}

/** Something disclosed last time and not this time. */
export function droppedDisclosures({ facts, from, to, accounting_scope = 'consolidated', segment = null }) {
  const at = (period_end) => new Set(groupFacts(facts, { period_end, accounting_scope, segment })
    .map((fact) => fact.definition_id));
  const before = at(from);
  const now = at(to);
  return [...before].filter((definition_id) => !now.has(definition_id)).sort().map((definition_id) => flag('disclosure_dropped', {
    observation: `${definition_id} was disclosed for ${from} and is not disclosed for ${to}`,
    magnitude: 1,
    basis: 'facts',
    evidence: [{ definition_id, period_end: from,
      value: Number(groupFacts(facts, { period_end: from, accounting_scope, segment })
        .find((fact) => fact.definition_id === definition_id).value) }],
  }));
}

/** Whatever verification already found, turned into pointers. */
export function fromVerification(checks, { threshold = CONVENTIONS.restatement } = {}) {
  const flags = [];
  for (const check of checks || []) {
    if (check.check === 'segment_sum' && check.status === 'residual') {
      flags.push(flag('segment_residual', {
        observation: `the disclosed segments of ${check.definition_id} sum to ${check.sum} against a stated total of ${check.total}, leaving ${check.residual}; ${check.note}`,
        magnitude: check.total === 0 ? 0 : Math.abs(check.residual / check.total),
        basis: 'verification',
        evidence: { total: check.total, sum: check.sum, residual: check.residual, components: check.components },
      }));
    }
    if (check.check === 'identity') {
      for (const reading of check.readings || []) {
        if (reading.status === 'unexplained') {
          const closest = reading.against.reduce((best, row) => (Math.abs(row.residual) < Math.abs(best.residual) ? row : best));
          flags.push(flag('unexplained_stated_figure', {
            observation: `the stated ${check.target_concept} of ${reading.stated} does not follow from any disclosed combination of its inputs; the nearest is ${Math.abs(closest.residual)} away`,
            magnitude: reading.stated === 0 ? 0 : Math.abs(closest.residual / reading.stated),
            basis: 'verification',
            evidence: { stated: reading.stated, definition_id: reading.definition_id, against: reading.against },
          }));
        }
        if (reading.status === 'definition_mismatch') {
          flags.push(flag('definition_mismatch', {
            observation: `the stated ${check.target_concept} of ${reading.stated} is filed as ${reading.definition_id} but the arithmetic matches ${reading.disagreement.map((row) => row.arithmetic_says).join(' and ')}`,
            magnitude: 1,
            basis: 'verification',
            evidence: { stated: reading.stated, disagreement: reading.disagreement },
          }));
        }
      }
    }
    if (check.check === 'restatement' && check.status === 'restated') {
      const share = Math.abs(check.as_share_of_original ?? 0);
      if (share < threshold) continue;
      flags.push(flag('restatement', {
        observation: `${check.definition_id} for ${check.period_end} changed by ${check.change} between documents, ${(share * 100).toFixed(1)}% of the original`,
        magnitude: share,
        basis: 'verification',
        evidence: { change: check.change, reported_in: check.reported_in },
      }));
    }
  }
  return flags;
}

/** Computed figures that no longer follow from the facts under them. */
export function staleDerivations(facts) {
  return (facts || [])
    .filter((fact) => fact && fact.verdict === 'derived' && RECIPES.has(fact.definition_id))
    .map((fact) => ({ fact, staleness: isStale(fact, facts) }))
    .filter((row) => row.staleness.stale)
    .map((row) => flag('stale_derivation', {
      observation: `${row.fact.definition_id} of ${row.fact.value} was computed from inputs that have since moved: ${row.staleness.reasons.join('; ')}`,
      magnitude: 1,
      basis: 'calculation',
      evidence: { definition_id: row.fact.definition_id, value: row.fact.value, reasons: row.staleness.reasons },
    }));
}

/** Flags in a declared order, largest first within each rule. */
export function rank(flags) {
  return [...(flags || [])].sort((a, b) => {
    const byRule = RULE_ORDER.indexOf(a.rule) - RULE_ORDER.indexOf(b.rule);
    // Magnitudes from different rules measure different things, so they are
    // never compared. Only the rule order is, and that order is a convention
    // stated in RULE_ORDER rather than a score computed from the numbers.
    if (byRule !== 0) return byRule;
    // A withheld magnitude sorts last within its rule rather than ahead of
    // every number, which is what comparing it as zero would do.
    return (b.magnitude ?? -Infinity) - (a.magnitude ?? -Infinity);
  });
}

/** Everything worth a look in one filing, from what the other modules found. */
export function review({
  facts, period_end, prior_period_end, accounting_scope = 'consolidated', segment = null,
  thresholds = {}, identities = [FREE_CASH_FLOW],
}) {
  const limits = { ...CONVENTIONS, ...thresholds };
  const checks = verify(facts, {
    identities: identities.map((identity) => ({ period_end, accounting_scope, ...identity })),
  });
  const flags = [
    ...fromVerification(checks, { threshold: limits.restatement }),
    ...staleDerivations(facts),
    ...definitionSpreads({ facts, period_end, accounting_scope, segment, threshold: limits.definition_spread }),
  ];
  if (prior_period_end) {
    flags.push(
      ...signSplits({ facts, from: prior_period_end, to: period_end, accounting_scope, segment }),
      ...growthGaps({ facts, from: prior_period_end, to: period_end, accounting_scope, segment, threshold: limits.growth_gap }),
      ...droppedDisclosures({ facts, from: prior_period_end, to: period_end, accounting_scope, segment }),
    );
  }
  return { period_end, prior_period_end, accounting_scope, segment, thresholds: limits, flags: rank(flags) };
}
