/**
 * The nine-step chain, read out of a document that was pasted in.
 *
 *   WHAT happened -> WHY -> HOW the business responded -> HOW MUCH it matters
 *   -> WHAT CHANGED -> WHAT MANAGEMENT EXPECTS -> RISKS -> CATALYSTS
 *   -> SO WHAT for investors
 *
 * Seven of those nine are in the document. Two are not, and the difference is
 * the whole design.
 *
 * A report states what happened, states its own explanation of why, states its
 * own figures, and states what management expects - in sentences, written by
 * the filer. Those slots are reachable by finding the sentence that carries
 * them and returning it. Nothing is composed: the claim IS the manager's
 * sentence, so a reviewer reads the same words the filer wrote.
 *
 * CATALYSTS and SO WHAT are not in any sentence. They are inference across
 * disclosures - the step that turns "cash is $369bn, buybacks were zero" into
 * "management sees nothing worth buying and is holding optionality". That step
 * is analysis and it needs a model. It is declared unreachable here rather
 * than faked with a cue phrase, because a slot filled by pattern-matching
 * would look exactly like a slot filled by understanding and would not be.
 *
 * Three rules hold everywhere in this file.
 *
 * A named metric comes from a closed list or is null. "GEICO's expense ratio
 * was 12.4%" yields the metric `expense ratio` because that phrase is in
 * METRICS. A sentence about something not on the list keeps its figures and
 * gets `metric: null`, because inferring a metric name from surrounding words
 * is how a number acquires a label nobody wrote.
 *
 * A change is arithmetic on two figures the document states, never on one.
 * "an increase of 2.7 percentage points compared to 2024" states the delta and
 * the endpoint; it does not state the starting value, and this returns what is
 * there rather than solving for the rest.
 *
 * Every claim carries its sentence. That is the only reason any of this is
 * publishable: a reviewer approves a claim against the words that produced it.
 */

/**
 * The chain, in order, with what each slot can be filled from.
 *
 * `basis` is a promise about where a claim in that slot came from:
 *   stated   - a sentence in the document says it; the sentence is returned
 *   derived  - arithmetic on two figures the document states; the work shown
 *   inferred - analysis across disclosures; no sentence says it
 */
export const CHAIN = [
  {
    slot: 'what_happened',
    question: 'What happened?',
    basis: 'stated',
    extractable: true,
  },
  {
    slot: 'why',
    question: 'Why did it happen?',
    basis: 'stated',
    extractable: true,
    note: "Management's own explanation, in its own words. Not our reading of the cause.",
  },
  {
    slot: 'how',
    question: 'How did the business respond?',
    basis: 'stated',
    extractable: true,
  },
  {
    slot: 'how_much',
    question: 'How much?',
    basis: 'stated',
    extractable: true,
  },
  {
    slot: 'what_changed',
    question: 'What changed vs last year?',
    basis: 'derived',
    extractable: true,
    note: 'Both endpoints must be stated. A stated delta with one endpoint is returned as that, not solved.',
  },
  {
    slot: 'expectations',
    question: 'What does management expect next?',
    basis: 'stated',
    extractable: true,
    note: 'Forward-looking only where management says so. Our forecast would not belong in this slot.',
  },
  {
    slot: 'risks',
    question: 'What could go wrong?',
    basis: 'stated',
    extractable: true,
  },
  {
    slot: 'catalysts',
    question: 'What could re-rate this?',
    basis: 'inferred',
    extractable: false,
    reason: 'No sentence states a catalyst. Identifying one means reading several disclosures '
      + 'against each other and against conditions outside the document. A cue phrase cannot do it.',
  },
  {
    slot: 'so_what',
    question: 'So what for investors?',
    basis: 'inferred',
    extractable: false,
    reason: 'This is the analytical conclusion and the document never writes it down. '
      + 'Berkshire states cash, purchases, sales and zero buybacks; "management sees nothing '
      + 'worth buying" is our inference from the four together, and belongs to a model with a '
      + 'reviewer, not to a regular expression.',
  },
];

export const STATED_SLOTS = CHAIN.filter((step) => step.extractable).map((step) => step.slot);
export const INFERRED_SLOTS = CHAIN.filter((step) => !step.extractable).map((step) => step.slot);

/**
 * Metric names that may be attached to a figure.
 *
 * Closed on purpose. A figure in a sentence naming one of these gets the name;
 * every other figure keeps its sentence and no name. The alternative - reading
 * the words before a number and calling them its label - produces labels like
 * "compared to" and "the increases were driven by higher".
 */
const METRICS = [
  'combined ratio', 'expense ratio', 'loss ratio', 'operating ratio',
  'premiums written', 'premiums earned', 'underwriting expenses',
  'policies-in-force', 'claims frequenc', 'claims severit',
  'float', 'book value', 'capital expenditures', 'capex',
  'net cash flow', 'operating earnings', 'net earnings', 'revenues',
  'cash and cash equivalents', 'treasury bills', 'cost of borrowing',
  'dividend', 'share repurchase', 'buyback', 'impairment',
];

/**
 * Sentences that fire a slot because of how they are phrased.
 *
 * Every cue here was cut down after being run against a real 557,000-character
 * report and reading what it caught. The first draft fired `why` on "reflected
 * their beliefs about business and life" and `risks` on "BHE has taken a
 * leadership role" on wildfires - a mitigation read as a hazard because the
 * topic word alone was a cue. A cue that matches rhetoric matches most of a
 * shareholder letter.
 */
const CUES = {
  why: [
    /\bbecause\b/i, /\bdue to\b/i, /\battributable to\b/i, /\bdriven by\b/i,
    /\bas a result of\b/i, /\bresult(?:ed|ing) from\b/i, /\bowing to\b/i,
    /\breflecting\b/i, /\breflected the\b/i,
    /\bthe (?:increase|decrease|decline|improvement)s? (?:was|were|reflect)/i,
  ],
  how: [
    // Something the business did, in the past tense or as a stated policy.
    // "We will remain relentless in this effort" was the whole of the first
    // draft's output for this slot: a promise, not a response.
    // First person only. An agentless "by increasing" or "reduced volume"
    // catches the cause rather than the response: "driven by rising
    // electricity demand and by increasing wildfire risk" is a why, and
    // "declines ... due to reduced volume" is a why, and both landed here
    // until the cue required a subject. This slot is small and correct rather
    // than larger and half misfiled, because the cost of a wrong claim is a
    // reviewer's attention.
    /\bwe (?:have )?(?:reduced|increased|expanded|invested|acquired|sold|prioriti[sz]ed|shifted|cut|repurchased|deployed|non-?renewed)\b/i,
    /\bwe (?:have )?always (?:prioriti[sz]ed|preferred)\b/i,
    /\bwe (?:reduced|increased|lowered|raised) (?:volume|exposure|limits|capacity|premium)/i,
  ],
  expectations: [
    /\bwe expect\b/i, /\bwe anticipate\b/i, /\bwe intend to\b/i, /\bwe plan to\b/i,
    /\bwill likely\b/i, /\bis expected to\b/i, /\bare expected to\b/i,
    /\bwe (?:do not|don't) expect\b/i,
  ],
  risks: [
    /\bcould (?:adversely|materially|be material|result in|have a)\b/i,
    /\bmay adversely\b/i, /\bno assurance\b/i, /\bsubject to (?:significant )?risk/i,
    /\bexposed to\b/i, /\bexposure to\b/i,
    /\bcannot be (?:reliably )?(?:estimated|predicted|determined)\b/i,
    /\bmaterially (?:different|adverse)\b/i, /\badverse development\b/i,
    /\bif .{0,60}were to\b/i,
  ],
};

/**
 * Slots that require the sentence to carry a number or a period.
 *
 * These four answer quantitative questions, and a sentence answering one of
 * them without a quantity is a topic sentence. "In return, we expect
 * accountability and integrity in performance" fires an expectation cue and is
 * not a forecast about the business; the same sentence in `why` would be
 * prose. `expectations`, `how` and `risks` are deliberately not in this set -
 * "we expect to write less reinsurance premium" carries no figure and is one
 * of the most useful statements in the document.
 */
const NEEDS_QUANTITY = new Set(['what_happened', 'why', 'how_much', 'what_changed']);

/**
 * Changes the document states, as patterns.
 *
 * Order matters: `unchanged from` is tried before the general year-comparison
 * patterns, because "9.7% in 2024, unchanged from 2023" also matches a looser
 * comparison read and would lose the fact that the value did not move.
 */
const CHANGES = [
  {
    id: 'unchanged',
    re: /([\d,]+(?:\.\d+)?)\s*(%|percent)\s+in\s+(\d{4}),?\s+unchanged from\s+(\d{4})/i,
    read: (m) => ({
      to: num(m[1]), from: num(m[1]), to_period: m[3], from_period: m[4],
      kind: 'percent', direction: 'unchanged',
    }),
  },
  {
    id: 'from_to',
    re: /\bfrom\s+\$?\s?([\d,]+(?:\.\d+)?)\s*(%|percent|billion|million|thousand)?\s*(?:in\s+(\d{4})\s*)?\s*to\s+\$?\s?([\d,]+(?:\.\d+)?)\s*(%|percent|billion|million|thousand)?\s*(?:in\s+(\d{4}))?/i,
    read: (m) => ({
      from: num(m[1]), to: num(m[4]),
      from_period: m[3] || null, to_period: m[6] || null,
      // A bare endpoint takes the scale its partner states: "from 27% to 35%"
      // writes the unit once. Where neither states one, the kind is unknown
      // and no delta is computed from it.
      kind: kindOf(m[2] || m[5]),
    }),
  },
  {
    id: 'value_vs_year',
    re: /([\d,]+(?:\.\d+)?)\s*(%|percent)\s+in\s+(\d{4})\s+and\s+([\d,]+(?:\.\d+)?)\s*(?:%|percent)\s+in\s+(\d{4})/i,
    read: (m) => ({
      to: num(m[1]), to_period: m[3], from: num(m[4]), from_period: m[5], kind: 'percent',
    }),
  },
  {
    id: 'stated_delta',
    // States the move and one endpoint. The other endpoint is not in the
    // sentence and is left null rather than subtracted into existence, because
    // the starting value may be restated elsewhere on a different basis.
    re: /an?\s+(increase|decrease)\s+of\s+([\d,]+(?:\.\d+)?)\s*(percentage points?|%)\s*compared to\s+(\d{4})/i,
    read: (m) => ({
      delta: num(m[2]) * (m[1].toLowerCase() === 'decrease' ? -1 : 1),
      from: null, to: null, from_period: m[4], to_period: null,
      kind: 'percentage_points', direction: m[1].toLowerCase() === 'increase' ? 'up' : 'down',
      delta_stated: true,
    }),
  },
];

const num = (value) => {
  const parsed = Number(String(value ?? '').replace(/,/g, ''));
  return Number.isFinite(parsed) ? parsed : null;
};

const kindOf = (token) => {
  const word = String(token || '').toLowerCase();
  if (word === '%' || word === 'percent') return 'percent';
  if (word === 'billion' || word === 'million' || word === 'thousand') return `money_${word}`;
  return null;
};

/**
 * A pasted document as sentences.
 *
 * Text out of a PDF wraps mid-sentence, so single newlines inside a paragraph
 * are joined before splitting. Blank lines stay as paragraph boundaries, which
 * keeps a heading from being glued onto the sentence under it.
 *
 * Each sentence carries the paragraph it came from so a reviewer can find it,
 * and nothing carries a byte offset into the original: the paste is not stored,
 * so an offset into it would point at nothing.
 */
export function sentences(text) {
  const out = [];
  const paragraphs = String(text || '').split(/\n\s*\n/);
  paragraphs.forEach((paragraph, index) => {
    const joined = paragraph.replace(/\s*\n\s*/g, ' ').replace(/\s+/g, ' ').trim();
    if (!joined) return;
    for (const raw of joined.split(/(?<=[.!?])\s+(?=[A-Z$“"(])/)) {
      const sentence = raw.trim();
      if (sentence.length < 20) continue;
      // A very long "sentence" is a table that lost its line breaks, not
      // prose. It is also more of the document than a citation should carry.
      if (sentence.length > 400) continue;
      out.push({ text: sentence, paragraph: index });
    }
  });
  return out;
}

/** Every money and percentage figure in a sentence, as written. */
export function figuresIn(sentence) {
  const text = String(sentence || '');
  const found = [];
  const money = /\$\s?([\d,]+(?:\.\d+)?)\s*(trillion|billion|million|thousand)?/gi;
  for (const match of text.matchAll(money)) {
    found.push({
      raw: match[0].trim(),
      value: num(match[1]),
      scale: match[2] ? match[2].toLowerCase() : null,
      kind: 'money',
    });
  }
  const percent = /([\d,]+(?:\.\d+)?)\s*(?:%|percentage points?|percent\b)/gi;
  for (const match of text.matchAll(percent)) {
    found.push({
      raw: match[0].trim(),
      value: num(match[1]),
      scale: null,
      kind: /percentage points?/i.test(match[0]) ? 'percentage_points' : 'percent',
    });
  }
  return found;
}

/**
 * The metric a sentence names, from the closed list, or null.
 *
 * Earliest mention wins, and the longest name at that position breaks a tie.
 * A longest-first read across the whole sentence gets this wrong: "GEICO's
 * expense ratio (underwriting expense to premiums earned) was 12.4%" is about
 * the expense ratio, and picking the longer `premiums earned` from inside the
 * parenthetical labels the figure with the denominator of its own definition.
 */
export function metricIn(sentence) {
  const text = String(sentence || '').toLowerCase();
  let best = null;
  for (const name of METRICS) {
    const at = text.indexOf(name);
    if (at < 0) continue;
    if (!best || at < best.at || (at === best.at && name.length > best.name.length)) {
      best = { at, name };
    }
  }
  return best ? best.name : null;
}

/** The change a sentence states, or null. */
export function changeIn(sentence) {
  const text = String(sentence || '');
  for (const pattern of CHANGES) {
    const match = pattern.re.exec(text);
    if (!match) continue;
    const read = pattern.read(match);
    const change = { pattern: pattern.id, delta: null, direction: null, ...read };
    if (change.delta === null && change.from !== null && change.to !== null) {
      change.delta = Number((change.to - change.from).toFixed(6));
      change.direction = change.delta === 0 ? 'unchanged' : change.delta > 0 ? 'up' : 'down';
    }
    return change;
  }
  return null;
}

const fires = (sentence, slot) => (CUES[slot] || []).some((cue) => cue.test(sentence));

/**
 * Which slots a sentence can fill.
 *
 * A sentence can fill several and that is not a defect: "Underwriting expenses
 * increased 34.2% in 2025 compared to 2024" is both a figure and a change, and
 * the sentence after it is both a why and a how. What matters is that a
 * sentence counted twice is not reported as two findings.
 */
export function slotsFor(sentence) {
  const text = String(sentence || '');
  const figures = figuresIn(text);
  const change = changeIn(text);
  // A year counts as a quantity. "We expect these businesses to face continued
  // headwinds in 2026" is anchored in time even though it states no figure.
  const quantified = figures.length > 0 || /\b(?:19|20)\d{2}\b/.test(text);
  const slots = [];
  if (change) slots.push('what_changed');
  for (const slot of ['why', 'how', 'expectations', 'risks']) {
    if (fires(text, slot)) slots.push(slot);
  }
  // A figure with a named metric is an amount; a figure without one still
  // reports an event.
  if (figures.length) {
    slots.push(metricIn(text) ? 'how_much' : 'what_happened');
  }
  return slots.filter((slot) => !NEEDS_QUANTITY.has(slot) || quantified);
}

/**
 * The chain, filled from a document.
 *
 * Returns every slot in order - including the two that cannot be filled, each
 * carrying the reason. A caller rendering this shows the gap instead of
 * presenting seven slots as if they were the whole chain.
 *
 * `perSlot` bounds what comes back. A 555,000-character report has thousands
 * of qualifying sentences and a reviewer cannot approve thousands; the count
 * of what was found is reported alongside what is returned, so the bound is
 * visible rather than silent.
 */
export function intelligenceChain(text, options = {}) {
  const perSlot = Number.isFinite(options.perSlot) ? options.perSlot : 25;
  const all = sentences(text);
  const buckets = new Map(STATED_SLOTS.map((slot) => [slot, []]));
  let matched = 0;

  for (const sentence of all) {
    const slots = slotsFor(sentence.text);
    if (!slots.length) continue;
    matched += 1;
    for (const slot of slots) {
      const bucket = buckets.get(slot);
      if (!bucket) continue;
      bucket.push({
        slot,
        basis: slot === 'what_changed' ? 'derived' : 'stated',
        metric: metricIn(sentence.text),
        figures: figuresIn(sentence.text),
        change: slot === 'what_changed' ? changeIn(sentence.text) : null,
        paragraph: sentence.paragraph,
        // The claim is the filer's sentence. Not a summary of it.
        source_excerpt: sentence.text,
      });
    }
  }

  const slots = CHAIN.map((step) => {
    if (!step.extractable) {
      return { ...step, claims: [], found: 0, returned: 0 };
    }
    const found = buckets.get(step.slot) || [];
    return {
      ...step,
      found: found.length,
      returned: Math.min(found.length, perSlot),
      truncated: found.length > perSlot,
      claims: found.slice(0, perSlot),
    };
  });

  return {
    sentences: all.length,
    // Distinct sentences, not the sum of the slots: one sentence filling three
    // slots is one thing found, and adding the buckets up would treble it.
    matched_sentences: matched,
    slots,
  };
}
