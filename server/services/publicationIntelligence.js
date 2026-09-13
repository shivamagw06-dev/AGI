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

import { boilerplateIn, BOILERPLATE_SLOTS } from './publicationBoilerplate.js';
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
export const METRICS = [
  'combined ratio', 'expense ratio', 'loss ratio', 'operating ratio',
  'premiums written', 'premiums earned', 'underwriting expense*',
  'policies-in-force', 'claims frequenc*', 'claims severit*',
  'float', 'book value', 'capital expenditures', 'capex',
  'net cash flow', 'operating earnings', 'net earnings', 'revenue*',
  'cash and cash equivalents', 'treasury bills', 'cost of borrowing',
  'dividend*', 'share repurchase*', 'buyback*', 'impairment*',
  // An operating company's margin, which the ratio above does not cover: an
  // operating ratio falls when a railroad improves and a margin rises, and
  // "BNSF's operating margin improved to 34.5% from 32.0%" was filed as an
  // unnamed event for want of this one name.
  'operating margin*', 'operating income', 'net interest income',
  // A fund reports on itself in a vocabulary none of the above contains.
  // Norges Bank's annual report produced 177 claims and zero amounts, because
  // every figure in it is a return, a flow or a fee.
  //
  // Every name here is a phrase or a long word, never an abbreviation. The
  // match is a substring on the lowercased sentence, so "nav" is inside
  // "naval", "aum" inside "trauma" and "eps" inside "steps" - and a named
  // metric with figures beside it is published without a reviewer, so a name
  // that matches an ordinary word publishes ordinary prose as an amount.
  'assets under management', 'net asset value', 'fund value',
  'total return', 'excess return', 'relative return', 'annualised return',
  'annualized return', 'return on equity', 'return on investment',
  'return on capital', 'benchmark return', 'benchmark index',
  'tracking error', 'information ratio', 'sharpe ratio', 'standard deviation',
  'management fee*', 'performance fee*', 'effective fee rate', 'fee rate',
  'net inflows', 'net outflows', 'net flows', 'gross flows',
  'net subscriptions', 'net redemptions',
  'earnings per share', 'operating expense*', 'assets under advisement',
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
/**
 * "Attributable to" that allocates rather than explains.
 *
 * NVIDIA's filing says "Depreciation and amortization expense attributable to
 * our Compute & Networking segment was $642 million" and Berkshire's says
 * "revenues attributable to the United States were 87%". Both were filed as
 * causes. Neither explains anything: they say which part of the business or
 * which country a figure belongs to.
 *
 * A change word before the segment or the place is what separates them, and
 * the distinction is narrow on purpose. "attributable to lower organic sales
 * across all major regions" mentions regions and is a cause, and dropping it
 * for the word "regions" was the first version of this rule.
 */
const ALLOCATION_NOT_CAUSE = /\battributable to\s+(?:our|the|its)?\s*(?![^.]{0,45}\b(?:higher|lower|increas|decreas|declin|growth|impact|chang|favorable|unfavorable|strong|weak|rise|fall)\w*\b)[^.]{0,45}?\b(?:segments?|United States|Europe|Asia|region|geograph)/i;

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
 * How a filer names the period it is comparing against.
 *
 * An annual report says "compared to 2024". A quarterly release says "from
 * the second quarter of 2025", and every one of BlackRock's nine stated
 * changes was missed because the pattern only knew the annual form:
 *
 *   "Performance fees increased $211 million from the second quarter of 2025"
 *   "General and administration expense increased $107 million from the
 *    second quarter of 2025"
 *
 * Those landed in what_happened instead - the information was kept, filed
 * under the wrong question.
 *
 * A bare "from <year>" is accepted, but only where the number is not preceded
 * by a currency sign, so "increased $510 million from $420 million" is left
 * to the pattern that reads two endpoints rather than being mistaken for a
 * period.
 */
const AGAINST_PERIOD = '(?:compared to|versus|vs\\.?|from)\\s+'
  + '(?:the\\s+(?:first|second|third|fourth)\\s+quarter\\s+of\\s+)?(?<!\\$)(\\d{4})';

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
    re: /\bfrom\s+\$?\s?([\d,]+(?:\.\d+)?)\s*(%|percent|trillion|billion|million|thousand)?\s*(?:in\s+(\d{4})\s*)?\s*to\s+\$?\s?([\d,]+(?:\.\d+)?)\s*(%|percent|trillion|billion|million|thousand)?\s*(?:in\s+(\d{4}))?/i,
    read: (m) => {
      // A range is not a change. Checked before the endpoints are read at
      // all, because both readings produce two perfectly plausible figures.
      if (isRange(m)) return null;
      const from = num(m[1]);
      const to = num(m[4]);
      // A bare endpoint takes the scale its partner states: "from 27% to 35%"
      // writes the unit once.
      const kind = kindOf(m[2] || m[5]);
      // Two year-like numbers with no unit is a span, not a move. Nothing
      // distinguishes "from 1998 to 2025" from "from 27 to 35" by shape, so
      // the years settle it.
      //
      // This also refused two claims in Berkshire's report that had been
      // published all along - "maturity dates ranging from 2035 to 2056",
      // read as a rise of 21 - so the rule removes four known-bad claims
      // across two documents and no good ones.
      //
      // The cost, stated because it is real: a genuine change measured in a
      // unit `kindOf` does not know is refused too. "capacity grew from 2,013
      // to 2,025 megawatts" is a change and this treats it as a date range,
      // because megawatts is not one of percent, thousand, million or
      // billion. Adding a unit to `kindOf` is what fixes that case, not
      // loosening this.
      if (kind === null && isYear(from) && isYear(to)) return null;
      // One year-like endpoint with no unit of its own is a date this pattern
      // has mistaken for a figure - worse than a span, because it produces a
      // delta against a real number.
      if (yearNotValue(from, m[2]) || yearNotValue(to, m[5])) return null;
      return { from, to, from_period: m[3] || null, to_period: m[6] || null, kind };
    },
  },
  {
    id: 'to_from',
    // The endpoints in the order a filer often writes them, which the
    // from/to pattern cannot read because it expects "from" first:
    //
    //   "BNSF's operating margin improved to 34.5% from 32.0% in 2024"
    //
    // That sentence sat in what_happened for the whole of its life here, and
    // it is one of the headline figures in the report. Reading actual
    // endpoints also handles the verbs stated_move refuses - "improved" says
    // nothing about which way the number went, but 34.5 and 32.0 do.
    re: /\bto\s+\$?\s?([\d,]+(?:\.\d+)?)\s*(%|percent|trillion|billion|million|thousand)?\s*(?:in\s+(\d{4}))?\s+from\s+\$?\s?([\d,]+(?:\.\d+)?)\s*(%|percent|trillion|billion|million|thousand)?\s*(?:in\s+(\d{4}))?/i,
    read: (m) => {
      const to = num(m[1]);
      const from = num(m[4]);
      const kind = kindOf(m[2] || m[5]);
      // Same refusal as the from/to pattern: two year-like numbers with no
      // unit is a span, not a move.
      if (kind === null && isYear(from) && isYear(to)) return null;
      // Same per-endpoint check, endpoints the other way round. This is the
      // order that produced both live fabrications.
      if (yearNotValue(to, m[2]) || yearNotValue(from, m[5])) return null;
      return { from, to, from_period: m[6] || null, to_period: m[3] || null, kind };
    },
  },
  {
    id: 'value_vs_year',
    re: /([\d,]+(?:\.\d+)?)\s*(%|percent)\s+in\s+(\d{4})\s+and\s+([\d,]+(?:\.\d+)?)\s*(?:%|percent)\s+in\s+(\d{4})/i,
    read: (m) => ({
      to: num(m[1]), to_period: m[3], from: num(m[4]), from_period: m[5], kind: 'percent',
    }),
  },
  {
    id: 'stated_move',
    // The way a filer usually states a change, and the way this missed for a
    // long time: 74 sentences in one report are shaped like this and none of
    // them were read as changes, which is why what_changed came back at 22
    // out of 641.
    //
    //   "Underwriting expenses increased 34.2% in 2025 compared to 2024"
    //   "Insurance investment income increased $4.1 billion in 2024 compared
    //    to 2023"
    //   "The expense ratio increased 1.1 percentage points in 2025 compared
    //    to 2024"
    //
    // The magnitude and both periods are stated; the endpoints are not, and
    // are left null rather than solved, the same as a stated delta.
    //
    // "compared to" must be followed by a year. "compared to a five-year
    // average of more than $40 billion" is a level against an average, not a
    // move between two periods, and reading it as a change would invent a
    // year-on-year comparison the filer did not make.
    //
    // The verbs are only the ones whose direction is unambiguous about the
    // NUMBER. "improved" and "deteriorated" describe the metric's fortunes -
    // an operating ratio improves by falling - so a direction taken from them
    // would be wrong half the time.
    // The gap classes are [^\n] rather than [^.], which is what they were
    // first written as. A decimal point is a period, so [^.] could not reach
    // past "1.2" - and in "declined $147 million (1.2%) in 2025 compared to
    // 2024" it skipped the $147 million and took the parenthetical 1.2%
    // instead. Not a choice, an accident of the character class. Crossing a
    // sentence is not a risk here because changeIn is handed one sentence at
    // a time, already split.
    //
    // The first stated magnitude wins, which is the absolute move where a
    // filer gives both. That is the figure the sentence leads with; the
    // percentage in brackets is its restatement.
    re: new RegExp('\\b(increased|rose|grew|decreased|declined|fell)\\b[^\\n]{0,50}?'
      + '\\$?\\s?([\\d,]+(?:\\.\\d+)?)\\s*(%|percentage points?|trillion|billion|million|thousand)?'
      + '[^\\n]{0,40}?(?:in\\s+(\\d{4})\\s*)?' + AGAINST_PERIOD, 'i'),
    read: (m) => {
      const magnitude = num(m[2]);
      if (magnitude === null) return null;
      const word = String(m[3] || '').toLowerCase();
      const kind = /percentage points?/.test(word) ? 'percentage_points' : kindOf(word);
      // A bare number with no unit at all could be anything. The filer always
      // gives a unit for a move worth stating.
      if (!kind) return null;
      const down = /^(decreased|declined|fell)$/i.test(m[1]);
      return {
        delta: down ? -magnitude : magnitude,
        direction: down ? 'down' : 'up',
        from: null, to: null,
        from_period: m[5] || null, to_period: m[4] || null,
        kind,
        delta_stated: true,
      };
    },
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

/**
 * A number that can only be a calendar year.
 *
 * Used to refuse a date range that is shaped exactly like a change. Norges
 * Bank's report is full of them - "Measured over the entire period from 1998
 * to 2025, the realised tracking error has been 0.62 percentage point" - and
 * the from/to pattern read that as a rise of 27, with no unit, and the
 * auto-approval rule published it. Three of the four changes found in that
 * document were date ranges.
 */
const isYear = (value) => Number.isInteger(value) && value >= 1800 && value <= 2200;

/**
 * An endpoint that is a year wearing a value's clothes.
 *
 * Found by sorting the published changes by the size of their delta, which
 * put the fabrications at the top of the list:
 *
 *   "Operating revenues from industrial products declined 1.2% in 2024 to
 *    $5.1 billion from 2023"     -> to 5.1, from 2023, delta -2017.9
 *   "...the ratio of railroad operating expenses to railroad operating
 *    revenues was 65.5%..."      -> to 65.5, from 2024, delta -1958.5
 *
 * Both were auto-approved and live on the page. The two-years refusal missed
 * them because only one endpoint was a year - the other was a real figure, so
 * the pair looked like a move from 2023 to 5.1 rather than a span.
 *
 * A real figure that happens to fall in the year range states its own unit:
 * "$2,023 million", "2,025 megawatts". A bare four-digit number in that range
 * with no unit of its own is a date.
 */
const yearNotValue = (value, unit) => isYear(value) && !unit;

/**
 * Whether the "from X to Y" a pattern just matched is a range rather than a
 * move.
 *
 * "borrowings have interest rates ranging from 1.35% to 3.12%" is a spread
 * across different borrowings and "expect to pay interest on our debt ranging
 * from $4.9 billion in 2026 to $4.3 billion in 2030" is a payment schedule.
 * In both, nothing changed, and subtracting the endpoints invents a movement
 * the filer never claimed - the first was published as a 1.77 point rise in
 * Berkshire's interest rates, which the document does not say anywhere.
 *
 * Decided by the words immediately before the "from", because the endpoints
 * are the same shape in both readings and nothing about 1.35 and 3.12 says
 * which one it is. "rose from 27% in 2022 to 35% in 2025" and "increased our
 * economic interest from 25% to 75%" are moves and keep their delta.
 */
const RANGE_LEAD = /\b(?:rang(?:e|es|ed|ing)|spread|spreads|vary|varying|varies|varied|anywhere)\s*$/i;
const isRange = (match) => RANGE_LEAD.test(String(match.input).slice(0, match.index));


const kindOf = (token) => {
  const word = String(token || '').toLowerCase();
  if (word === '%' || word === 'percent') return 'percent';
  // Trillion was missing from here and from every change pattern's unit list,
  // while figuresIn already had it. "AUM rose to $15.3 trillion from $12.5
  // trillion" read as no change at all - a scale this codebase only met when
  // a document measured in trillions arrived.
  if (['trillion', 'billion', 'million', 'thousand'].includes(word)) return `money_${word}`;
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
 * A line that is nothing but a stray glyph or two.
 *
 * A PDF paste carries loose characters where the converter lost a bullet, a
 * rule or a logo: this report has bare "g" lines between several sections.
 * They are not furniture by repetition or by page-marker shape, and left in
 * they weld two sentences together, because a full stop followed by a
 * lowercase word is not a sentence boundary:
 *
 *   "BNSF can be exposed to significant litigation costs ... and from
 *    ongoing business operations. q g BNSF derives significant revenues from
 *    the transportation of energy-related commodities, including coal."
 *
 * That is two disclosures presented as one claim, and the second one's
 * subject reads as a continuation of the first.
 */
export function isStrayGlyph(line) {
  const text = String(line || '').trim();
  return text.length > 0 && text.length <= 2 && !/[A-Za-z0-9]{2}/.test(text);
}

/**
 * Debris between two sentences, removed so the split can happen.
 *
 * Only after terminal punctuation and only before a capital, which is the one
 * position where a run of one- and two-letter lowercase tokens cannot be
 * prose. Nothing legitimate reads ". q g BNSF"; plenty reads "... of a
 * Berkshire subsidiary", which this leaves alone because there is no full
 * stop in front of it.
 */
/**
 * A filing's cover page, and its cross-reference index.
 *
 * NVIDIA's 10-Q opens with checkbox ballots - "Yes [ ] No [X]" - and the first
 * real fact on the page was welded to one: "Yes (box) No (box) The number of
 * shares of common stock, $0.001 par value, outstanding as of August 21, 2026,
 * was 24.1 billion."
 *
 * And a sentence ending in "Item 2." is a cross-reference, which in that
 * document arrived with a whole lease table flattened in front of it.
 */
const COVER_BALLOT = /^(?:yes|no)\s*[\u2610\u2611\u2612\u2713\u2714]\s*(?:(?:yes|no)\s*[\u2610\u2611\u2612\u2713\u2714]\s*)?/i;
const ITEM_CROSS_REFERENCE = /\bitem\s+\d+[a-z]?\.?\s*$/i;

/** Whether a sentence is a filing's furniture rather than its content. */
export function isFilingFurniture(text) {
  return ITEM_CROSS_REFERENCE.test(String(text || '').trim());
}

export function stripSentenceDebris(text) {
  return String(text || '')
    // A cover page's checkbox ballot, before anything else: the first real
    // fact in NVIDIA's 10-Q arrived welded to one.
    .replace(COVER_BALLOT, '')
    // A table's footnote marker, which belongs to the table: "(2) Included
    // $13.0 billion and $7.5 billion related to customer advances". Only a
    // marker followed by a space and a capital - "(2)Significant business
    // acquisitions" is a note heading welded on, which is a different problem
    // and not one a prefix strip can fix.
    .replace(/^\(\d{1,2}\)\s+(?=[A-Z])/, '')
    // The lookahead is the same set of sentence openers the splitter below
    // recognises, and deliberately so: this function exists to let that split
    // happen, so a start it cannot see is debris it cannot remove. They were
    // out of sync, and "$95 million to the pension plans in 2026. j g (24)
    // Pension plans Fair value measurements..." is what that cost - the stray
    // "j g" stopped the split, welding a pension contribution to the caption
    // of a different disclosure's table, and it reached the live page.
    .replace(/([.!?])\s+(?:[a-z]{1,2}\s+){1,4}(?=[A-Z$“"(])/g, '$1 ');
}

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
/**
 * Where one sentence ends and the next begins.
 *
 * A full stop after certain abbreviations is not a sentence ending, and
 * splitting there throws away the half that answers the question. Reliance's
 * report says "The Group has four principal operating and reporting segments;
 * viz. Oil To Chemicals (O2C), Oil and Gas, Retail and Digital Services" - and
 * the segments, which are the answer, were being discarded.
 *
 * The list is deliberately short. `Inc.`, `Ltd.` and `etc.` genuinely do end
 * sentences, and refusing to split after them welds two sentences together,
 * which is the same defect in the other direction and harder to notice. Only
 * abbreviations that are almost never sentence-final are here.
 */
const NEVER_ENDS_A_SENTENCE = 'viz|e\\.g|i\\.e|vs|approx|cf|Mr|Mrs|Ms|Dr|Prof|St|No|Nos|Fig|Vol|Ch';
const SENTENCE_BREAK = new RegExp(
  `(?<!\\b(?:${NEVER_ENDS_A_SENTENCE})\\.)(?<=[.!?])\\s+(?=[A-Z$“"(])`,
);

export function sentences(text) {
  const out = [];
  const furniture = runningHeaders(text);
  let heading = null;
  let sinceHeading = 0;
  let paragraph = 0;
  let buffer = [];

  const flush = () => {
    // Debris is removed from the joined passage rather than line by line,
    // because a stray glyph that shared a line with real text survives the
    // line-level check and only shows up once the lines are together.
    const joined = stripSentenceDebris(buffer.join(' ').replace(/\s+/g, ' ').trim());
    buffer = [];
    if (!joined) return;
    for (const raw of joined.split(SENTENCE_BREAK)) {
      const sentence = raw.trim();
      if (sentence.length < 20) continue;
      // A cross-reference names a section and reports nothing. NVIDIA's
      // arrived with a lease table flattened in front of it.
      if (isFilingFurniture(sentence)) continue;
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
    if (!section && (furniture.has(line.trim()) || isPageMarker(line)
      || isStrayGlyph(line))) continue;
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
  const money = /\$\s?([\d,]+(?:\.\d+)?)\s*(trillion|trillion|billion|million|thousand)?/gi;
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
  // A fund quotes a fee in basis points and nothing else does. Without this,
  // "the management fee was 4.2 basis points of assets" states no figure, so a
  // named metric has nothing to report and the sentence is filed as an event.
  const basisPoints = /([\d,]+(?:\.\d+)?)\s*basis points?\b/gi;
  for (const match of text.matchAll(basisPoints)) {
    found.push({
      raw: match[0].trim(), value: num(match[1]), scale: null, kind: 'basis_points',
    });
  }
  return found;
}

/**
 * A sentence measuring something that is not money.
 *
 * Norges Bank's report published three of these as amounts, each with a metric
 * name taken from elsewhere in the sentence:
 *
 *   "financed emissions ... were 51 million tonnes of CO2 equivalent ... which
 *    is 4% lower than the corresponding figure for the benchmark index"
 *        -> labelled `benchmark index`
 *   "the equity portfolio's carbon intensity, which was 7% lower than that of
 *    the benchmark index"        -> labelled `benchmark index`
 *   "the portfolio's emissions intensity was 92 tonnes of CO2 equivalent per
 *    million USD in revenue"     -> labelled `revenue`
 *
 * In each, the figure measures emissions and the metric is a comparator or a
 * denominator. They were auto-approved, because a named metric beside figures
 * needs no reviewer.
 *
 * Proximity was tried first and measured: the distance from metric to figure
 * ran 11 to 45 characters for these three and 4 to 109 for the sixteen correct
 * labels in the same document. The ranges overlap completely - the closest
 * pairing of all is a correct one - so distance cannot separate them and the
 * subject has to.
 *
 * The sentence is still kept, as a what_happened claim awaiting a reader. What
 * changes is that it is no longer published as an amount under a metric it
 * does not measure.
 */
const NOT_MONEY = /\b(?:emissions?|carbon|CO2|greenhouse|tonnes?|megawatts?|gigawatts?|kilowatts?)\b/i;

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
  for (const entry of METRICS) {
    // A trailing * is a stem: `dividend*` is meant to reach "dividends" and
    // `claims frequenc*` to reach "frequency" and "frequencies". Everything
    // else is a whole word, because `float` was reaching "floating rate" -
    // and a metric named wrongly beside a figure is published with no
    // reviewer, under a label the sentence never used.
    const stem = entry.endsWith('*');
    const name = stem ? entry.slice(0, -1) : entry;
    let at = -1;
    for (let from = 0; from <= text.length;) {
      const found = text.indexOf(name, from);
      if (found < 0) break;
      // Only the end is checked. The hazard is a name reaching further than it
      // should - `float` into "floating", `nav` into "naval", `eps` into
      // "steps" - and a trailing letter refuses all of them. A leading letter
      // does not: this document says "GEICO'sexpense ratio", welded by
      // whatever produced the text, and a start boundary loses the metric in
      // the sentence that taught us earliest-mention-wins.
      const after = text[found + name.length] || '';
      if (stem || !LETTER.test(after)) { at = found; break; }
      from = found + 1;
    }
    if (at < 0) continue;
    if (!best || at < best.at || (at === best.at && name.length > best.name.length)) {
      best = { at, name };
    }
  }
  return best ? best.name : null;
}

const LETTER = /[a-z]/;

/** The change a sentence states, or null. */
export function changeIn(sentence) {
  const text = String(sentence || '');
  for (const pattern of CHANGES) {
    const match = pattern.re.exec(text);
    if (!match) continue;
    const read = pattern.read(match);
    // A pattern may match the shape and then refuse the reading. The next
    // pattern still gets its turn: a sentence carrying a date range may also
    // carry a real change.
    if (!read) continue;
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
  // A filing states its risks in the same grammar it states its disclaimers,
  // so the cues that find a real disclosure also find the safe-harbour
  // paragraph beside it. Reviewing Berkshire's two documents rejected 28 of
  // the 56 claims in these two slots, every one of them boilerplate.
  const boilerplate = boilerplateIn(text);
  const slots = [];
  if (change) slots.push('what_changed');
  const allocates = ALLOCATION_NOT_CAUSE.test(text);
  for (const slot of ['why', 'how', 'expectations', 'risks']) {
    if (!fires(text, slot)) continue;
    if (boilerplate && BOILERPLATE_SLOTS.has(slot)) continue;
    // Saying which segment or country a figure belongs to is not saying why.
    if (slot === 'why' && allocates) continue;
    slots.push(slot);
  }
  // A figure with a named metric is an amount; a figure without one still
  // reports an event. A figure measuring something that is not money is
  // neither, however familiar the words around it: the metric is claimed by a
  // name appearing elsewhere in the sentence, and an amount is published with
  // no reviewer.
  if (figures.length) {
    slots.push(metricIn(text) && !NOT_MONEY.test(text) ? 'how_much' : 'what_happened');
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
