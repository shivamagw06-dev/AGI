/**
 * What each row of the hundred questions says, and why.
 *
 * The page used to have one word for every computed question it could not
 * answer: "needs statements". It covered four different situations - a figure
 * disclosed two ways and waiting for someone to choose, a figure nobody has
 * taught the reader to look for, a figure searched for and not in the filing,
 * and a figure the pasted text never had a chance to contain - and a reader
 * told "needs statements" about operating cash flow, which Reliance reports on
 * page 103, could not tell which.
 *
 * So a row carries the reason from the thing that stopped it, in the order a
 * reader can act on it: a choice they can make now comes first, a search that
 * found nothing comes last, because that one is the only claim about the
 * filing itself.
 */

export const LABEL = {
  answered: 'from the report',
  computed: 'computed',
  choose: 'choose a definition',
  not_looked_for: 'not looked for yet',
  not_resolved: 'not resolved',
  cannot_compute: 'cannot be computed',
  not_disclosed: 'searched, not disclosed',
  silent: 'the report is silent',
  no_rule: 'no rule written yet',
  judgment: 'needs a reviewer',
  needs_data: 'needs statements',
};

export const ORDER = ['answered', 'computed', 'choose', 'not_looked_for', 'not_resolved',
  'cannot_compute', 'not_disclosed', 'needs_data', 'silent', 'no_rule', 'judgment'];

/**
 * Which blocker a row reports when several stopped it.
 *
 * A choice the reader can make outranks everything, because making it answers
 * the question. A search that found nothing ranks last, because it is the one
 * statement about what the filing contains and should not be made while
 * something else could still be the cause.
 */
const PRECEDENCE = [
  (one) => one.status === 'needs_a_definition' && 'choose',
  (one) => one.status === 'no_fit' && 'choose',
  (one) => one.state === 'no_way_to_look' && 'not_looked_for',
  // An input that was never resolved says nothing about whether anything knows
  // where to find it. Reporting it as "nothing looks for cfo" was false on the
  // first live upload: the search for cfo works, and no period had been
  // resolved to run it against.
  (one) => one.state === 'not_asked_for' && 'not_resolved',
  (one) => one.state === 'not_disclosed' && 'not_disclosed',
];

export function statusOfBlocked(blockedBy) {
  for (const rule of PRECEDENCE) {
    const hit = (blockedBy || []).find((one) => rule(one));
    if (hit) return { status: rule(hit), blocker: hit };
  }
  return { status: 'needs_data', blocker: null };
}

/** A sentence for a blocker, naming the input and what happened to it. */
export function explain(blocker) {
  if (!blocker) return null;
  const name = blocker.concept || blocker.need;
  if (blocker.status === 'needs_a_definition') {
    const choices = (blocker.candidates || []).map((id) => id.split('.').slice(1).join('.')).join(' or ');
    return `${name} is disclosed more than one way${choices ? ` (${choices})` : ''} - choose which`;
  }
  if (blocker.status === 'no_fit') return `${name} was found, but not on a basis this question can use`;
  if (blocker.state === 'no_way_to_look') return `nothing looks for ${name} in a filing yet`;
  if (blocker.state === 'not_asked_for') return `${name} was not resolved for this period`;
  if (blocker.state === 'not_disclosed') return `searched for ${name}; the report does not disclose it`;
  return blocker.reason || null;
}

/**
 * The definitions an answer's inputs were taken under, in words.
 *
 * Q31 asks for reported EBITDA and is answered from a table footnoted "before
 * exceptional items". The figure is the same this year and would not be in a
 * year with an exceptional charge, so the answer says which it is rather than
 * leaving the question's wording to imply the other.
 */
export function usedDefinitions(used) {
  const labels = Object.values(used || {}).map((input) => input?.label).filter(Boolean);
  return [...new Set(labels)];
}

/** The pages an answer's inputs were read from, in order, without repeats. */
export function citedPages(used) {
  const pages = Object.values(used || {})
    .map((input) => input?.source_page)
    .filter((page) => Number.isInteger(page));
  return [...new Set(pages)].sort((a, b) => a - b);
}

/**
 * Every row, for either kind of reading.
 *
 * A pasted report comes back with the old shape - an answer per question and
 * a reason where there was none - and a PDF comes back with provenance and a
 * list of what blocked each question. Both render; only one can say which page
 * a figure is on.
 */
export function rowsFor(result, judgements = null) {
  // A reason that stopped the whole reading - no period could be resolved -
  // is what every computed row reports. Deriving a separate cause per row
  // from an empty resolution invents fifty-one explanations for one fact.
  const wholesale = result?.computed?.reason || null;
  return (result?.questions || []).map((question) => {
    const computed = result?.computed?.answers?.[question.n] || null;
    const judged = (judgements?.judgements || []).find((entry) => entry.n === question.n) || null;
    if (question.kind === 'judgment') return { ...question, computed: null, judged };
    if (question.kind !== 'computed') return { ...question, computed: null, judged: null };
    if (wholesale) {
      return { ...question, status: 'not_resolved', computed, judged: null, explanation: wholesale };
    }
    if (computed && computed.reason === null && computed.value !== null && computed.value !== undefined) {
      return {
        ...question, status: 'computed', computed, judged: null,
        pages: citedPages(computed.used), definitions: usedDefinitions(computed.used),
      };
    }
    if (computed?.blocked_by?.length) {
      const { status, blocker } = statusOfBlocked(computed.blocked_by);
      return { ...question, status, computed, judged: null, explanation: explain(blocker) };
    }
    // A reading from a document always says what blocked it, even when the
    // answer is nothing. With every input resolved, what is left is the
    // arithmetic: a formula nobody has written, or one that needs more years
    // than the filing reports. Neither is a missing statement.
    if (computed && 'blocked_by' in computed) {
      return {
        ...question, status: computed.no_rule ? 'no_rule' : 'cannot_compute',
        computed, judged: null, explanation: computed.reason || null,
      };
    }
    // Pasted text, which carries no provenance: the old reason, unchanged.
    return { ...question, status: 'needs_data', computed, judged: null, explanation: computed?.reason || null };
  });
}

export function countRows(rows) {
  return rows.reduce((tally, row) => ({ ...tally, [row.status]: (tally[row.status] || 0) + 1 }), {});
}

/**
 * How the periods read, for either response shape.
 *
 * The paste endpoint describes periods as a range with units; the document
 * endpoint lists the period ends it resolved.
 */
export function periodsLine(computed) {
  if (!computed?.periods) return null;
  const who = computed.company || computed.ticker || '';
  if (Array.isArray(computed.periods)) {
    if (!computed.periods.length) return null;
    const recovered = computed.recovered
      ? `, ${computed.recovered} figure${computed.recovered === 1 ? '' : 's'} read from the document` : '';
    return `${who}: ${computed.periods.join(', ')}${recovered}`;
  }
  const { periods, from, to, units = [] } = computed.periods;
  return `${who}: ${periods} annual periods, ${from} to ${to}, ${units.join(', ')}`;
}
