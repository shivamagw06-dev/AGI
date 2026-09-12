/**
 * Which business a claim is about, and which market question it answers.
 *
 * "We expect to write less reinsurance premium" is only useful if it can be
 * found by someone asking what Berkshire expects from the insurance market.
 * That needs two things the sentence does not always carry: the segment it
 * belongs to, and the theme it speaks to.
 *
 * Both come from closed lists. A segment is a business the filer reports; a
 * theme is a market condition the filer writes about. Neither is inferred from
 * surrounding words, for the same reason a metric is not: a label nobody wrote
 * is indistinguishable from one the filer did, once it is in a column.
 *
 * The segment has a second source, and it is the one that makes this work. An
 * annual report's MD&A is organised under segment headings, and the sentences
 * beneath a heading are about that segment without repeating its name:
 *
 *   Reinsurance Group
 *   Our reinsurance operations face similar dynamics. ... In most casualty
 *   reinsurance segments, claims inflation continued to outpace pricing. As
 *   long as these phases of the cycle endure, we expect to write less
 *   reinsurance premium.
 *
 * A heading only counts when the whole line is a segment name. A line reading
 * "Total" or "Net" - and a pasted report is full of both - is a table artefact,
 * and requiring the entire line to match a known name is what keeps those out.
 * Prose mentioning GEICO is not a GEICO heading either.
 *
 * Every attribution says where it came from. `in_sentence` means the sentence
 * named the business; `from_heading` means it was inherited from the section
 * it sits under. A reviewer treats those differently, so the column tells them
 * which one they are looking at.
 */

/**
 * Segments a filer reports, with the lines that are headings for them and the
 * words that name them in prose.
 *
 * `headings` is matched against a whole line, normalised. `mentions` is matched
 * as a substring of a sentence. They differ because "reinsurance" is a fine
 * mention and a poor heading test, while "Reinsurance Group" is the reverse.
 */
export const SEGMENTS = [
  {
    segment: 'geico',
    label: 'GEICO',
    headings: ['geico', 'geico auto insurance'],
    mentions: ['geico'],
  },
  {
    segment: 'reinsurance',
    label: 'Reinsurance',
    headings: ['reinsurance group', 'reinsurance', 'retroactive reinsurance',
      'berkshire hathaway reinsurance group', 'periodic payment annuity'],
    mentions: ['reinsurance'],
  },
  {
    segment: 'primary_insurance',
    label: 'BH Primary',
    headings: ['bh primary', 'primary group', 'berkshire hathaway primary group',
      'berkshire hathaway specialty insurance'],
    mentions: ['bh primary', 'bhsi', 'berkshire hathaway specialty'],
  },
  {
    segment: 'insurance_investments',
    label: 'Insurance investments',
    headings: ['insurance-investment income', 'insurance investment income',
      'investment gains/losses'],
    mentions: ['insurance investment income', 'insurance float'],
  },
  {
    segment: 'bnsf',
    label: 'BNSF',
    headings: ['bnsf', 'railroad', 'bnsf railway'],
    mentions: ['bnsf'],
  },
  {
    segment: 'bhe',
    label: 'Berkshire Hathaway Energy',
    headings: ['bhe', 'berkshire hathaway energy', 'utilities and energy',
      'renewables', 'pacificorp', 'nv energy', 'midamerican energy'],
    mentions: ['bhe', 'berkshire hathaway energy', 'pacificorp'],
  },
  {
    segment: 'precision_castparts',
    label: 'Precision Castparts',
    headings: ['pcc', 'precision castparts', 'precision castparts corp.'],
    mentions: ['precision castparts', 'pcc'],
  },
  {
    segment: 'building_products',
    label: 'Building products',
    headings: ['building products', 'clayton homes', 'homebuilding',
      'berkshire hathaway homeservices'],
    mentions: ['clayton homes', 'building products', 'mitek', 'johns manville',
      'shaw industries', 'benjamin moore'],
  },
  {
    segment: 'manufacturing',
    label: 'Manufacturing, service and retailing',
    headings: ['manufacturing, service and retailing', 'manufacturing',
      'industrial products', 'consumer products', 'service and retailing'],
    mentions: ['marmon', 'lubrizol', 'imc', 'iscar'],
  },
  {
    segment: 'pilot',
    label: 'Pilot',
    headings: ['pilot', 'pilot travel centers'],
    mentions: ['pilot'],
  },
  {
    segment: 'mclane',
    label: 'McLane',
    headings: ['mclane', 'mclane company'],
    mentions: ['mclane'],
  },
  {
    segment: 'auto_dealerships',
    label: 'Berkshire Hathaway Automotive',
    headings: ['bha', 'berkshire hathaway automotive'],
    mentions: ['bha', 'berkshire hathaway automotive'],
  },
  {
    segment: 'equity_investments',
    label: 'Equity investments',
    headings: ['equity investments', 'investments in equity securities'],
    mentions: ['equity securities portfolio'],
  },
];

/**
 * Market conditions a filer writes about.
 *
 * These are the questions the chain gets asked - what does it expect from
 * insurance pricing, what does it see in power demand, what does the railroad
 * say about freight. A theme is only attached when the sentence itself carries
 * one of these phrases; unlike a segment it is never inherited from a heading,
 * because a section about BHE covers both power demand and tax policy and
 * inheriting one of them would mislabel the other.
 */
export const THEMES = [
  {
    theme: 'pricing',
    label: 'Pricing and rate',
    phrases: ['pricing', 'price declines', 'rate increases', 'rate decreases',
      'premium rates', 'less attractive', 'adequate or improving', 'rate adequacy'],
  },
  {
    theme: 'competition',
    label: 'Competition and capacity',
    phrases: ['additional capital entered', 'available capital', 'competitors',
      'competition', 'competitive', 'market capacity', 'alternative markets'],
  },
  {
    theme: 'claims_cost',
    label: 'Claims cost and severity',
    phrases: ['claims severit', 'claims frequenc', 'claims inflation',
      'social inflation', 'loss cost', 'adverse development', 'severity'],
  },
  {
    theme: 'retention',
    label: 'Policy retention and growth',
    phrases: ['policies-in-force', 'policies in force', 'retention',
      'policy acquisition', 'advertising'],
  },
  {
    theme: 'power_demand',
    label: 'Electricity demand and AI',
    phrases: ['electricity demand', 'electric demand', 'data center',
      'artificial intelligence', 'load growth', 'generation capacity',
      'transmission'],
  },
  {
    theme: 'aerospace_demand',
    label: 'Aerospace demand',
    phrases: ['aerospace', 'aircraft', 'aviation', 'airframe', 'jet engine'],
  },
  {
    theme: 'housing_demand',
    label: 'Housing and construction demand',
    phrases: ['housing', 'home construction', 'residential construction',
      'commercial construction', 'mortgage rates', 'new home'],
  },
  {
    theme: 'freight_volumes',
    label: 'Freight and trade volumes',
    phrases: ['freight', 'carloads', 'intermodal', 'imports', 'export',
      'grain', 'coal', 'petroleum', 'consumer products volumes'],
  },
  {
    theme: 'policy_and_tariffs',
    label: 'Tax, trade and tariff policy',
    // No bare 'regulatory'. It appears in every generic risk factor a filer
    // writes - "Regulatory changes may adversely impact our future operating
    // results" - and pulled those in as answers about renewable-project tax
    // and tariff policy, which is a different question.
    // 'income tax rate' is gone too: an effective-rate movement is an outcome,
    // not a policy change, and it dominated this theme.
    //
    // 'tariff' stays and carries a homonym that cannot be resolved by pattern.
    // In a UK utility's results "lower tariffs from inflation adjustments"
    // means the regulated price schedule, not trade policy, and Northern
    // Powergrid's revenue line lands here as a result. A reviewer catches it;
    // dropping the word would lose every real trade-tariff statement.
    phrases: ['tax credit', 'tariff', 'trade polic',
      'inflation reduction act', 'renewable energy credit'],
  },
  {
    theme: 'interest_rates',
    label: 'Interest rates and short-term yields',
    phrases: ['interest rates', 'interest income', 'short-term investments',
      'treasury bill', 'yield'],
  },
  {
    theme: 'capital_deployment',
    label: 'Capital deployment',
    phrases: ['acquisition', 'repurchase', 'buyback', 'capital expenditure',
      'deploy', 'opportunit'],
  },
  {
    theme: 'catastrophe',
    label: 'Catastrophe and wildfire exposure',
    phrases: ['wildfire', 'hurricane', 'catastrophe', 'convective storm',
      'earthquake'],
  },
];

/** Lower-case, punctuation-light form used for matching a whole line. */
const normalise = (value) => String(value || '')
  .toLowerCase()
  .replace(/[‘’“”]/g, "'")
  .replace(/[^a-z0-9,.&' -]/g, ' ')
  .replace(/\s+/g, ' ')
  .trim()
  .replace(/[.,]+$/, '');

/**
 * The segment a whole line is a heading for, or null.
 *
 * The entire line must be the name. This is the guard that keeps "Total",
 * "Net", "Other" and "December 31, 2025" - all of which appear as standalone
 * lines dozens of times in a pasted report - from becoming section headings,
 * and keeps a prose sentence that happens to mention GEICO from resetting the
 * section every time it appears.
 */
export function segmentHeading(line) {
  const text = normalise(line);
  if (!text || text.length > 60) return null;
  // A heading is not a sentence. Anything with terminal punctuation or a verb
  // phrase long enough to need one is prose.
  if (/[.!?]$/.test(String(line || '').trim())) return null;
  for (const entry of SEGMENTS) {
    if (entry.headings.some((heading) => heading === text)) return entry.segment;
  }
  return null;
}

/** The segment a sentence names, or null. Earliest mention wins. */
export function segmentIn(sentence) {
  const text = normalise(sentence);
  let best = null;
  for (const entry of SEGMENTS) {
    for (const mention of entry.mentions) {
      const at = text.indexOf(mention);
      if (at < 0) continue;
      if (!best || at < best.at || (at === best.at && mention.length > best.length)) {
        best = { at, length: mention.length, segment: entry.segment };
      }
    }
  }
  return best ? best.segment : null;
}

/**
 * Themes a sentence carries, in the order the lists declare them.
 *
 * A sentence may carry several and usually should: "additional capital entered
 * the market, resulting in lower pricing" is competition and pricing at once,
 * and a reader asking about either should find it.
 */
export function themesIn(sentence) {
  const text = normalise(sentence);
  return THEMES
    .filter((entry) => entry.phrases.some((phrase) => text.includes(phrase)))
    .map((entry) => entry.theme);
}

/**
 * Segment for a claim, preferring what the sentence says over what it sits
 * under.
 *
 * A sentence naming its own business is better evidence than the heading above
 * it, because a section about GEICO discusses the auto market generally and a
 * heading is inherited by everything beneath it until the next one - including
 * a paragraph that has moved on.
 */
export function attributeSegment(sentence, heading) {
  const named = segmentIn(sentence);
  if (named) return { segment: named, segment_source: 'in_sentence' };
  if (heading) return { segment: heading, segment_source: 'from_heading' };
  return { segment: null, segment_source: null };
}

export const SEGMENT_LABELS = Object.fromEntries(
  SEGMENTS.map((entry) => [entry.segment, entry.label]),
);
export const THEME_LABELS = Object.fromEntries(
  THEMES.map((entry) => [entry.theme, entry.label]),
);
