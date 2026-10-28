/**
 * Turning a hundred findings into the ten that matter.
 *
 * The extraction is the solved part. What reached a reader was the $279
 * billion supply commitment and "you should read this Quarterly Report
 * completely" in the same list, at the same weight, and attention spent on the
 * second is attention not spent on the first.
 *
 * Materiality here is COMPUTED, not scored by a model. A model asked to rate
 * significance out of a hundred returns a confident number nobody can check,
 * sitting beside figures that were verified against the filing and looking
 * equally solid. That is the same failure as a year read as a value: plausible,
 * unfalsifiable, and wrong in a way nobody catches.
 *
 * So the ranking is arithmetic - how large is this figure against something the
 * company reported - and the interpretation is left to a tier that must ground
 * itself in evidence and may refuse. What cannot be computed says so.
 */

const SCALE = new Map([
  ['thousand', 1e3], ['million', 1e6], ['billion', 1e9], ['trillion', 1e12],
  ['lakh', 1e5], ['crore', 1e7],
]);

/** A money figure in units, or null if the sentence states no money. */
export function largestAmount(claim) {
  let best = null;
  for (const figure of claim?.figures || []) {
    if (figure?.kind !== 'money') continue;
    const value = Number(figure.value) * (SCALE.get(figure.scale) || 1);
    if (!Number.isFinite(value)) continue;
    if (best === null || Math.abs(value) > Math.abs(best.value)) {
      best = { value, raw: figure.raw };
    }
  }
  return best;
}

/**
 * The same fact, said twice.
 *
 * NVIDIA's filing reports one buyback in three sentences - the capital-return
 * discussion, the unregistered-sales note and the step that files it as a
 * response - and a ranked list showing all three spends two of its ten places
 * repeating itself.
 *
 * Grouped by the amount and the step, because two sentences stating the same
 * figure under the same question are the same finding, while the same figure
 * under a different question is a different reading of it. The longest sentence
 * wins: it is the one that carries the most context.
 */
export function dedupe(claims) {
  const best = new Map();
  const loose = [];
  for (const claim of claims || []) {
    const amount = largestAmount(claim);
    if (!amount) { loose.push(claim); continue; }
    const key = `${claim.slot || ''}|${amount.value}`;
    const held = best.get(key);
    if (!held || String(claim.source_excerpt || '').length > String(held.source_excerpt || '').length) {
      best.set(key, claim);
    }
  }
  return [...best.values(), ...loose];
}

/**
 * How large a finding is against what the company reported.
 *
 * `against` is a map of denominators - revenue, total assets, cash - in the
 * same units. Returns the largest share the amount represents of any of them,
 * and names which, so a reader sees "38% of revenue" rather than a score.
 *
 * Without denominators the amount still orders a list, and the result says the
 * ranking is by size alone. An unnormalised ranking is honest; an invented
 * denominator is not.
 */
export function materiality(claim, { against = {} } = {}) {
  const amount = largestAmount(claim);
  if (!amount) return { amount: null, share: null, of: null, basis: 'no amount stated' };
  let share = null;
  let of = null;
  for (const [name, denominator] of Object.entries(against)) {
    const size = Number(denominator);
    if (!Number.isFinite(size) || size <= 0) continue;
    const ratio = Math.abs(amount.value) / size;
    if (share === null || ratio > share) { share = ratio; of = name; }
  }
  return {
    amount: amount.value,
    raw: amount.raw,
    share,
    of,
    basis: share === null ? 'ranked by size alone, nothing to compare against' : `${of} as reported`,
  };
}

/**
 * Findings, largest first.
 *
 * Ordered by share of a reported denominator where there is one, and by
 * absolute size where there is not - never mixing the two, because a figure
 * with a denominator and one without are not comparable and sorting them
 * together invents a precedence.
 */
export function rank(claims, { against = {}, limit = Infinity } = {}) {
  const scored = dedupe(claims)
    .map((claim) => ({ claim, ...materiality(claim, { against }) }))
    .filter((entry) => entry.amount !== null);
  const normalised = scored.filter((entry) => entry.share !== null)
    .sort((a, b) => b.share - a.share);
  const bySize = scored.filter((entry) => entry.share === null)
    .sort((a, b) => Math.abs(b.amount) - Math.abs(a.amount));
  return [...normalised, ...bySize].slice(0, limit);
}
