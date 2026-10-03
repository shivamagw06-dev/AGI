/**
 * Whether what a filing states is consistent with the rest of what it states.
 *
 * Extraction records disclosures and refuses to reconcile them. Something then
 * has to ask whether they hang together, and the useful version of that question
 * is not "which number is right". Reliance's segment capex sums to ₹1,44,271
 * crore only if the Unallocable column is counted; leave it out and ₹3,397 crore
 * goes missing. That is not an error in the filing and not an error in the
 * reader. It is a residual, and naming it is the whole job.
 *
 * So this module reports and never resolves. It does not edit a fact, drop a
 * fact, or choose between two. A check says what it compared, what it got, what
 * was left over, and how much of the gap rounding could account for. A reader
 * who wants a verdict can have one; what they cannot have is a verdict this
 * module reached by quietly discarding a disclosure.
 *
 * Two habits here are load-bearing. Arithmetic never crosses a definition or a
 * measurement basis, because ₹1,44,271 crore of accrual capex and ₹1,22,916
 * crore of cash capex are not two attempts at one number. And tolerance comes
 * from how precisely the filing wrote the figures rather than from a percentage
 * someone picked: six figures rounded to the crore can miss by three crore
 * honestly, and by nothing else.
 */
const round = (value, places = 6) => Number(value.toFixed(places));

/**
 * Columns that appear beside segments without being segments.
 *
 * A filing puts Unallocable or Eliminations in the segment table because the
 * total needs them, so a reader extracting "the segments" reasonably omits them
 * and then cannot make the total. Knowing the difference lets a residual be
 * reported as a missing reconciling column rather than as a contradiction.
 */
export const RECONCILING_SEGMENTS = new Set([
  'unallocable', 'unallocated', 'unallocable corporate', 'unallocated corporate',
  'eliminations', 'elimination', 'inter segment', 'intersegment',
  'reconciling items', 'corporate and other', 'corporate unallocated',
]);

const normalise = (text) => String(text ?? '').toLowerCase().replace(/[^a-z]+/g, ' ').trim();

export function isReconcilingSegment(segment) {
  return RECONCILING_SEGMENTS.has(normalise(segment));
}

/**
 * How precisely the filing wrote a figure.
 *
 * Read from the sentence rather than from the stored number, because ₹0.40 and
 * ₹0.4 are the same Number and different claims about precision. Digits and
 * commas only: a table row reduced to a sentence reads "32,365   1,756", and a
 * pattern that swallowed the spaces between them would read one number of
 * fourteen digits.
 */
export function statedPrecision(fact) {
  const value = Number(fact?.value);
  if (!Number.isFinite(value)) return 0;
  const wanted = Math.abs(value);
  for (const token of String(fact?.source_sentence ?? '').match(/\d[\d,]*(?:\.\d+)?/g) || []) {
    if (Number(token.replace(/,/g, '')) === wanted) return (token.split('.')[1] || '').length;
  }
  return (String(wanted).split('.')[1] || '').length;
}

/** The most a sum of rounded figures can miss by without anything being wrong. */
export function roundingSlack(facts) {
  return round((facts || []).reduce(
    (total, fact) => total + 0.5 * (10 ** -statedPrecision(fact)), 0), 6);
}

const scopeOf = (fact) => fact?.accounting_scope || 'consolidated';

/** Facts stated in different money or different multiples cannot be added. */
function sameUnits(facts) {
  const units = new Set(facts.map((fact) => `${fact.currency}|${fact.unit}`));
  return units.size <= 1 ? null : [...units].join(' and ');
}

/**
 * Whether the parts a filing discloses add up to the total it discloses.
 *
 * Compared within one definition only. Segment capital expenditure summing to
 * management's capital expenditure would be a coincidence worth noticing and
 * not a reconciliation, and this check is not the place to decide which.
 */
export function checkSegmentSum({ facts, definition_id, period_end, accounting_scope = 'consolidated' }) {
  const result = { check: 'segment_sum', definition_id, period_end, accounting_scope };
  const matching = (facts || []).filter((fact) => fact
    && fact.definition_id === definition_id
    && fact.period_end === period_end
    && scopeOf(fact) === accounting_scope);

  const total = matching.find((fact) => !fact.segment);
  const components = matching.filter((fact) => fact.segment);
  if (!total) return { ...result, status: 'insufficient_data', reason: 'no total disclosed' };
  if (components.length < 2) {
    return { ...result, status: 'insufficient_data', reason: 'fewer than two components disclosed' };
  }
  const mixed = sameUnits([total, ...components]);
  if (mixed) return { ...result, status: 'not_comparable', reason: `figures are stated in ${mixed}` };

  const reconciling = components.filter((fact) => isReconcilingSegment(fact.segment));
  const operating = components.filter((fact) => !isReconcilingSegment(fact.segment));
  const add = (rows) => round(rows.reduce((sum, fact) => sum + Number(fact.value), 0), 6);

  const sum = add(components);
  const residual = round(Number(total.value) - sum, 6);
  const tolerance = roundingSlack([total, ...components]);

  const detail = {
    ...result,
    total: Number(total.value),
    components: components.map((fact) => ({ segment: fact.segment, value: Number(fact.value) })),
    sum,
    operating_sum: add(operating),
    reconciling_sum: reconciling.length ? add(reconciling) : null,
    residual,
    tolerance,
  };

  if (residual === 0) return { ...detail, status: 'agrees' };
  if (Math.abs(residual) <= tolerance) return { ...detail, status: 'within_rounding' };
  // A filing that discloses segments almost always discloses somewhere for the
  // rest to go. A residual with no such column extracted is more likely to be a
  // column the reader missed than a filing that does not add up, and saying so
  // is more useful than either calling it correct or calling it a conflict.
  return {
    ...detail,
    status: 'residual',
    note: reconciling.length
      ? 'the disclosed reconciling columns do not close the gap'
      : 'no unallocable or eliminations column was extracted; the residual may be one',
  };
}

function combinations(lists) {
  return lists.reduce((rows, list) => rows.flatMap((row) => list.map((item) => [...row, item])), [[]]);
}

const MAX_COMBINATIONS = 24;

/**
 * Whether a stated figure equals what the filing's other figures make it.
 *
 * The point is not to confirm arithmetic. It is that most identities have more
 * than one right answer: free cash flow from Reliance's operating cash flow is
 * ₹47,842 crore against management capex and ₹69,197 crore against cash capex,
 * 44.6% apart, and both are defensible. If the issuer states a free cash flow,
 * which candidate it matches tells you which capex the issuer meant - a fact
 * about the definition, recovered from arithmetic. If the issuer states none,
 * the honest output is that there is nothing to verify and the candidates are
 * this far apart.
 */
export function checkIdentity({ facts, name, target_concept, terms, expects = {}, period_end, accounting_scope = 'consolidated' }) {
  const result = { check: 'identity', name, target_concept, period_end, accounting_scope };
  const pool = (facts || []).filter((fact) => fact
    && !fact.segment
    && fact.period_end === period_end
    && scopeOf(fact) === accounting_scope);

  const lists = [];
  for (const term of terms || []) {
    const options = pool.filter((fact) => fact.concept === term.concept);
    if (!options.length) {
      return { ...result, status: 'insufficient_data', reason: `no ${term.concept} disclosed` };
    }
    lists.push(options.map((fact) => ({ fact, sign: term.sign })));
  }
  const count = lists.reduce((product, list) => product * list.length, 1);
  if (count > MAX_COMBINATIONS) {
    return { ...result, status: 'too_many_definitions', reason: `${count} combinations of definitions` };
  }

  const candidates = [];
  for (const row of combinations(lists)) {
    const chosen = row.map((entry) => entry.fact);
    const mixed = sameUnits(chosen);
    if (mixed) continue;
    candidates.push({
      value: round(row.reduce((sum, entry) => sum + entry.sign * Number(entry.fact.value), 0), 6),
      using: Object.fromEntries(chosen.map((fact) => [fact.concept, fact.definition_id])),
      tolerance: roundingSlack(chosen),
    });
  }
  if (!candidates.length) {
    return { ...result, status: 'not_comparable', reason: 'the inputs are stated in different units' };
  }
  candidates.sort((a, b) => b.value - a.value);
  const high = candidates[0];
  const low = candidates[candidates.length - 1];
  const spread = candidates.length < 2 ? null : {
    high: high.value,
    low: low.value,
    difference: round(high.value - low.value, 6),
    // Named against the smaller side, because that is the claim being made:
    // choosing the other definition raises the answer by this much.
    as_share_of_low: low.value === 0 ? null : round((high.value - low.value) / low.value, 6),
  };

  const stated = pool.filter((fact) => fact.concept === target_concept);
  if (!stated.length) {
    return { ...result, status: 'no_stated_figure', candidates, spread,
      note: 'the filing does not state this figure, so there is nothing to verify' };
  }

  const readings = stated.map((fact) => {
    const against = candidates.map((candidate) => ({
      using: candidate.using,
      residual: round(Number(fact.value) - candidate.value, 6),
      tolerance: round(candidate.tolerance + roundingSlack([fact]), 6),
    }));
    const matches = against.filter((entry) => Math.abs(entry.residual) <= entry.tolerance);
    let status;
    let disagreement = null;
    if (!matches.length) status = 'unexplained';
    else if (matches.length > 1) status = 'indistinguishable';
    else {
      // The arithmetic says which inputs the issuer used. If the fact was
      // filed under a definition built on different inputs, one of the two is
      // wrong, and the arithmetic is the one that can be checked.
      const wanted = expects[fact.definition_id] || null;
      const used = matches[0].using;
      const wrong = Object.entries(wanted || {})
        .filter(([concept, definition_id]) => used[concept] !== definition_id)
        .map(([concept, definition_id]) => ({ concept, filed_as: definition_id, arithmetic_says: used[concept] }));
      status = wrong.length ? 'definition_mismatch' : 'identifies_definition';
      if (wrong.length) disagreement = wrong;
    }
    return { stated: Number(fact.value), definition_id: fact.definition_id, against, matches, status, disagreement };
  });

  const worst = ['unexplained', 'definition_mismatch', 'indistinguishable', 'identifies_definition']
    .find((status) => readings.some((reading) => reading.status === status));
  return { ...result, status: worst, candidates, spread, readings };
}

/**
 * The same figure reported twice by two documents.
 *
 * FY25 as first published and FY25 as restated in the FY26 report are two
 * facts by design, so they meet here rather than overwriting each other. A
 * restatement is news; the same number confirmed twice is corroboration.
 */
export function checkRestatements(facts) {
  const groups = new Map();
  for (const fact of facts || []) {
    if (!fact) continue;
    const key = [fact.company, fact.period_end, fact.period_type || 'annual',
      scopeOf(fact), fact.entity_scope || 'group', fact.concept,
      fact.definition_id, fact.segment || ''].join('|');
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(fact);
  }
  const findings = [];
  for (const rows of groups.values()) {
    const documents = new Set(rows.map((fact) => fact.reported_in_document));
    if (documents.size < 2) continue;
    const values = [...new Set(rows.map((fact) => Number(fact.value)))];
    const shared = {
      check: 'restatement',
      concept: rows[0].concept,
      definition_id: rows[0].definition_id,
      period_end: rows[0].period_end,
      reported_in: rows.map((fact) => ({ document: fact.reported_in_document, value: Number(fact.value) })),
    };
    if (values.length === 1) { findings.push({ ...shared, status: 'confirmed' }); continue; }
    const earliest = rows[0];
    const latest = rows[rows.length - 1];
    const change = round(Number(latest.value) - Number(earliest.value), 6);
    findings.push({
      ...shared,
      status: 'restated',
      change,
      as_share_of_original: Number(earliest.value) === 0 ? null
        : round(change / Number(earliest.value), 6),
    });
  }
  return findings;
}

/** Every check the facts admit, without being told which to run. */
export function verify(facts, { identities = [] } = {}) {
  const rows = (facts || []).filter(Boolean);
  const checks = [];

  const segmented = new Set(rows.filter((fact) => fact.segment)
    .map((fact) => `${fact.definition_id}|${fact.period_end}|${scopeOf(fact)}`));
  for (const key of [...segmented].sort()) {
    const [definition_id, period_end, accounting_scope] = key.split('|');
    checks.push(checkSegmentSum({ facts: rows, definition_id, period_end, accounting_scope }));
  }
  for (const identity of identities) checks.push(checkIdentity({ facts: rows, ...identity }));
  checks.push(...checkRestatements(rows));
  return checks;
}

/** Free cash flow, which is the identity most worth asking this of. */
export const FREE_CASH_FLOW = Object.freeze({
  name: 'free cash flow',
  target_concept: 'fcf',
  terms: [{ concept: 'cfo', sign: 1 }, { concept: 'capex', sign: -1 }],
  // Which capex each free cash flow definition is built on. A stated figure
  // that matches the other one is filed under the wrong definition.
  expects: {
    'FCF.CFO_MINUS_MANAGEMENT_CAPEX': { capex: 'CAPEX.MANAGEMENT' },
    'FCF.CFO_MINUS_CASH_CAPEX': { capex: 'CAPEX.CASH_PPE_INTANGIBLES' },
  },
});
