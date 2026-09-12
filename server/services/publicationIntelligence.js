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

import { attributeSegment, segmentHeading, themesIn } from './publicationSegments.js';

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
    note: 'Both endpoints must be stated, or the filer states the move itself - in which '
      + 'case the claim is stated, not derived, and each claim carries its own basis.',
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
    // First person only. Passive "is expected to" and "are expected to" read
    // as forecasts and in an insurer's report are mostly definitions of how a
    // contract works - "expected ultimate losses payable under these policies
    // are expected to exceed premiums" - plus organisational boilerplate:
    // "its CEO, who is expected to pursue operational excellence". Management
    // saying what it expects is the thing this slot is for.
    /\bwe expect\b/i, /\bwe anticipate\b/i, /\bwe intend to\b/i, /\bwe plan to\b/i,
    /\bwe (?:do not|don't) expect\b/i, /\bwe (?:believe|foresee) .{0,40}will\b/i,
    /\bwill likely\b/i,
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
 * A run of table cells that got joined into something sentence-shaped.
 *
 * The length cap alone let this through and it reached a claim:
 *
 *   Land, track structure and other roadway $ 76,764 $ 74,093 Locomotives,
 *   freight cars and other equipment 15,772 15,766 Construction in progress
 *
 * 384 characters, no verb, and it answered a question about freight because
 * "freight cars" is in the row. A sentence quotes a filer; this quotes a
 * spreadsheet, and a reviewer shown it as evidence learns nothing.
 *
 * Two tests, because one was not enough.
 *
 * The share of tokens that are bare numbers. Prose carries figures and stays
 * mostly words; a table row is mostly numbers however it is wrapped. A
 * four-digit year is not counted: years are prose, and "GEICO's loss ratio was
 * 71.8% in 2024 and 81.0% in 2023" was rejected as a table until they stopped
 * counting.
 *
 * Trailing punctuation is stripped before either test, which the first version
 * did not do. "2026," is not "2026", so a year inside a list kept its comma
 * and counted as a column: "Estimated future payments were $10 billion in
 * 2026, $6 billion in 2027, $4 billion in 2028, $3 billion in 2029" scored
 * 0.400 and was thrown away as a table. It is a commitments schedule written
 * as a sentence, and the years are the reason it is worth having.
 *
 * And adjacent bare numbers, which is the sharper signal. A balance-sheet row
 * with long labels between its columns dilutes the ratio below any threshold
 * that leaves dense prose alone - this one reached 0.229 against a 0.25 bar,
 * was filed as an amount with the metric "treasury bills", and was published
 * by the auto-approval rule:
 *
 *   Treasury Bills 112,811 89,705 Investments in and advances to consolidated
 *   subsidiaries 604,100 568,987 Investment in Kraft Heinz and other assets
 *   8,871 13,417 $ 740,409 $ 678,446 Liabilities and Shareholders' equity:
 *
 * Two numbers side by side is what a column pair looks like and what a
 * sentence almost never contains. Prose separates its figures with words:
 * "$46 billion of net cash flows, compared to a five-year average of more than
 * $40 billion" has none. Two such pairs is a table.
 */
export function looksTabular(sentence) {
  const tokens = String(sentence || '').trim().split(/\s+/).filter(Boolean);
  if (tokens.length < 6) return false;
  const bare = tokens.map((token) => token.replace(/[.,;:]+$/, ''));
  const numeric = bare.filter((token) => /^[$(]?[\d,]+(?:\.\d+)?\)?%?$/.test(token)
    && !/^(?:19|20)\d{2}$/.test(token)).length;
  if (numeric / bare.length >= 0.25) return true;
  const pairs = String(sentence).match(/(?<![\d,.])[\d,]+(?:\.\d+)?\s+[\d,]+(?:\.\d+)?(?![\d,.])/g);
  return (pairs || []).length >= 2;
}

/**
 * Lines that repeat across a document because they are page furniture.
 *
 * A pasted report carries its running headers inline: this one had "Notes to
 * Consolidated Financial Statements" 45 times, "Management's Discussion and
 * Analysis" 29, "2025 versus 2024" 12, and bare page markers like "K-116".
 * They reached claims - one answer about Pilot began "K-79 Notes to
 * Consolidated Financial Statements (2)Significant business acquisitions On
 * January 31, 2023, we acquired..." - which quotes the page template rather
 * than the filer.
 *
 * Found by repetition rather than from a list of Berkshire's headers, so it
 * works on any filer's document. A line qualifies by repeating at least four
 * times, being short, and carrying no terminal punctuation - text that
 * repetitive is a template, not a sentence.
 *
 * A real section heading also repeats ("Manufacturing, Service and Retailing"
 * appears eight times), so segment headings are matched BEFORE this set is
 * consulted. Getting that order wrong discards the attribution.
 */
/**
 * A standalone page marker, by shape rather than by repetition.
 *
 * Repetition misses these: "K-116" appears eleven times but "K-38", "K-79"
 * and "K-25" appear once or twice each, and all three reached a claim as a
 * prefix - "K-79 (2)Significant business acquisitions On January 31, 2023, we
 * acquired..." The shape is what gives them away: a few optional letters, an
 * optional dash, and digits, alone on a line. No sentence looks like that, and
 * a bare number on its own line is a table cell either way.
 */
export function isPageMarker(line) {
  return /^[A-Za-z]{0,3}[-\u2013\u2014]?\d{1,4}$/.test(String(line || '').trim());
}

export function runningHeaders(text) {
  const counts = new Map();
  for (const raw of String(text || '').split('\n')) {
    const line = raw.trim();
    if (!line || line.length > 80) continue;
    if (/[.!?]$/.test(line)) continue;
    counts.set(line, (counts.get(line) || 0) + 1);
  }
  return new Set([...counts].filter(([, count]) => count >= 4).map(([line]) => line));
}

/**
 * How many sentences a section heading carries for.
 *
 * Counted in sentences, not passages, because a pasted report has almost no
 * blank lines - this one had two in 7,194 - so a passage counter advances only
 * at the next heading and a bound written against it can never fire. The first
 * version of this bound was exactly that: inert, and it changed the segment
 * counts by nothing.
 *
 * Twenty-five covers an MD&A segment discussion. Past that the sentence is
 * usually in the notes or the risk factors, which carry no segment headings at
 * all, and the nearest heading above is not evidence about them.
 */
const HEADING_SPAN = 25;

/**
 * A pasted document as sentences, under the section each one sits in.
 *
 * Text out of a PDF wraps mid-sentence, so lines inside a passage are joined
 * before splitting on terminal punctuation.
 *
 * A section heading is a line of its own and has to be taken out before that
 * join, not after. An annual report's MD&A puts "Reinsurance Group" on its own
 * line with no blank line around it, and joining first produced the sentence
 * "Reinsurance Group Our reinsurance operations face similar dynamics" - a
 * claim whose excerpt carried a word the sentence does not contain. Pulling
 * the heading out fixes that and yields the thing that makes a claim findable:
 * the business the passage beneath it is about.
 *
 * A heading expires. It applies to the passages beneath it until the next
 * heading OR until HEADING_SPAN passages have gone by, whichever comes first.
 * Without the bound, the first draft attributed 661 of 665 claims to a segment
 * across a 557,000-character report - "Pilot" collected 88 claims because the
 * heading was set once in the letter and never cleared, and the notes to the
 * financial statements and the risk factors, which carry no segment headings
 * at all, inherited whatever section happened to precede them. A heading 200
 * passages above a sentence is not evidence about that sentence.
 *
 * Each sentence carries its section and the passage it came from. Nothing
 * carries a byte offset into the original, because the paste is not stored and
 * an offset into it would point at nothing.
 */
export function sentences(text) {
  const out = [];
  const furniture = runningHeaders(text);
  let heading = null;
  let sinceHeading = 0;
  let paragraph = 0;
  let buffer = [];

  const flush = () => {
    const joined = buffer.join(' ').replace(/\s+/g, ' ').trim();
    buffer = [];
    if (!joined) return;
    for (const raw of joined.split(/(?<=[.!?])\s+(?=[A-Z$“"(])/)) {
      const sentence = raw.trim();
      if (sentence.length < 20) continue;
      // A very long "sentence" is a table that lost its line breaks, not
      // prose. It is also more of the document than a citation should carry.
      if (sentence.length > 400) continue;
      if (looksTabular(sentence)) continue;
      sinceHeading += 1;
      const live = heading !== null && sinceHeading <= HEADING_SPAN;
      out.push({ text: sentence, paragraph, heading: live ? heading : null });
    }
  };

  for (const line of String(text || '').split('\n')) {
    if (!line.trim()) {
      flush();
      paragraph += 1;
      continue;
    }
    const section = segmentHeading(line);
    // A repeated line is dropped without flushing the buffer. A sentence can
    // wrap across a page break, and flushing at the page header would cut it
    // in half; dropping the header lets the halves join.
    if (!section && (furniture.has(line.trim()) || isPageMarker(line))) continue;
    if (section) {
      // A heading closes the passage above it and names the one below.
      flush();
      paragraph += 1;
      heading = section;
      sinceHeading = 0;
      continue;
    }
    buffer.push(line.trim());
  }
  flush();
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
  // A cause about an identified market condition counts even with no figure
  // in it. "the industry enters a significant investment cycle, driven by
  // rising electricity demand from artificial intelligence computing" states
  // no number and is the answer to what Berkshire sees in AI power demand;
  // the quantity rule alone discarded it. Rhetoric still fails both tests:
  // "reflected their beliefs about business and life" names no market.
  const themed = themesIn(text).length > 0;
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
  return slots.filter((slot) => {
    if (!NEEDS_QUANTITY.has(slot)) return true;
    if (quantified) return true;
    return slot === 'why' && themed;
  });
}

/**
 * The chain, filled from a document.
 *
 * Returns every slot in order - including the two that cannot be filled, each
 * carrying the reason. A caller rendering this shows the gap instead of
 * presenting seven slots as if they were the whole chain.
 *
 * Everything found comes back. `perSlot` exists for a caller that wants to
 * print a sample and is not a storage bound - it was one, and that was a
 * defect: the default of 25 silently discarded 509 of the 654 claims in a
 * 557,000-character report, keeping whichever 25 appeared first in document
 * order. Asking that store for BNSF's freight causes then searched 25 of 142,
 * which defeats the point of storing claims at all. Review load is a
 * different problem from ingest and is solved by prioritising the queue, not
 * by throwing data away without saying so.
 */
export function intelligenceChain(text, options = {}) {
  const perSlot = Number.isFinite(options.perSlot) ? options.perSlot : Infinity;
  const all = sentences(text);
  const buckets = new Map(STATED_SLOTS.map((slot) => [slot, []]));
  // One sentence, one claim per slot. A document repeats sentences - the yen
  // borrowing terms appear in both the MD&A and the parent-company note - and
  // the same words twice are not two findings. Left in, they consumed the
  // per-slot bound and made one INSERT touch the same row twice, which
  // Postgres refuses outright: "ON CONFLICT DO UPDATE command cannot affect
  // row a second time".
  const seen = new Map(STATED_SLOTS.map((slot) => [slot, new Set()]));
  let matched = 0;

  for (const sentence of all) {
    const slots = slotsFor(sentence.text);
    if (!slots.length) continue;
    matched += 1;
    for (const slot of slots) {
      const bucket = buckets.get(slot);
      if (!bucket) continue;
      const already = seen.get(slot);
      if (already.has(sentence.text)) continue;
      already.add(sentence.text);
      const change = slot === 'what_changed' ? changeIn(sentence.text) : null;
      bucket.push({
        slot,
        // Per claim, not per slot. "an increase of 2.7 percentage points
        // compared to 2024" is the filer's own arithmetic and this codebase
        // did none: labelling it `derived` claimed credit for a subtraction
        // nobody performed, and understated how well supported the row is.
        // Only a delta this code computed from two stated endpoints is derived.
        basis: change && change.delta_stated ? 'stated'
          : slot === 'what_changed' ? 'derived' : 'stated',
        metric: metricIn(sentence.text),
        figures: figuresIn(sentence.text),
        change,
        // Which business, and whether the sentence said so or the section did.
        ...attributeSegment(sentence.text, sentence.heading),
        // Which market questions it speaks to. Several is normal.
        themes: themesIn(sentence.text),
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

/**
 * Whether a claim can be published without a person reading it.
 *
 * Two cases, and both are narrow on purpose.
 *
 * A change whose move the document supports. Either it states both endpoints,
 * and the delta is a subtraction anyone can check against the sentence, or it
 * states the move itself - "an increase of 2.7 percentage points compared to
 * 2024" - in which case there is no arithmetic to check at all and the row is
 * pure quotation. The first draft of this rule held the second case back on
 * the grounds that its starting value is missing, which confused a value the
 * row does not claim with a value the row gets wrong: `from` is null and the
 * row says so.
 *
 * An amount whose metric is on the closed list. The sentence names the metric
 * and carries the figure, so the row is quotation with a label the filer
 * wrote.
 *
 * Everything cue-matched stays pending: `why`, `risks`, `how` and
 * `expectations` are a regular expression's guess at what a sentence is doing,
 * and the expectations slot runs at roughly half precision - "we expect the
 * resolution periods will be very long" is contract mechanics sitting beside
 * "we expect to write less reinsurance premium".
 *
 * What this certifies is that the row quotes the document accurately. It does
 * not certify that the fact is worth reading: "our insurance businesses'
 * ability to declare ordinary dividends ... permitting up to $31 billion" is
 * an accurate amount with a named metric and is also dull. Accuracy is a
 * property of the extraction and can be decided by rule; interest is
 * editorial and cannot.
 */
export function autoApproved(claim) {
  if (!claim) return false;
  if (claim.slot === 'what_changed') {
    const change = claim.change;
    if (!change || change.delta === null || change.delta === undefined) return false;
    if (change.delta_stated) return true;
    return change.from !== null && change.from !== undefined
      && change.to !== null && change.to !== undefined;
  }
  if (claim.slot === 'how_much') {
    return Boolean(claim.metric && claim.figures && claim.figures.length);
  }
  return false;
}

/**
 * Claims from a chain, narrowed to a question.
 *
 * "What does Berkshire expect from the insurance market?" is a slot and a set
 * of segments. "What demand trends does it see in AI power?" is a theme. This
 * is a filter and is named like one: it selects claims the filer wrote, and
 * does not compose an answer out of them. Composing the answer is the
 * so_what step, which is still declared unreachable.
 */
export function selectClaims(chain, filter = {}) {
  const wanted = (value) => (value === undefined || value === null
    ? null
    : new Set(Array.isArray(value) ? value : [value]));
  const slots = wanted(filter.slots ?? filter.slot);
  const segments = wanted(filter.segments ?? filter.segment);
  const themes = wanted(filter.themes ?? filter.theme);

  const out = [];
  for (const slot of chain?.slots || []) {
    if (slots && !slots.has(slot.slot)) continue;
    for (const claim of slot.claims) {
      if (segments && !segments.has(claim.segment)) continue;
      // A claim carries several themes; matching any of the asked-for ones is
      // a match, because a sentence about capital entering the market and
      // pricing falling answers a question about either.
      if (themes && !(claim.themes || []).some((theme) => themes.has(theme))) continue;
      out.push(claim);
    }
  }
  return out;
}
