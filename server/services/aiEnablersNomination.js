/**
 * Nomination: which of the whole exchange to read.
 *
 * The screen's decisive stage is evidence - a signed order, committed capex,
 * an operating disclosure - and that has to be read, company by company. It
 * cannot be read for 2,390 companies, and until now the answer was to read
 * the ones a semantic search over filings happened to surface. That is a
 * sample chosen by a search engine, and PART 9 says so.
 *
 * This is the step in between. Every listed company has a business
 * description; this reads each one for the plant the taxonomy is about and
 * nominates the companies whose own description names it. Every company gets
 * a recorded outcome, so "not examined" and "examined and not nominated"
 * stop being the same thing.
 *
 * Nomination is not admission and must never become it. The terms here are
 * built for recall: a false nomination costs one reading, a missed one costs
 * a member. So they are broad on purpose, and narrow only where a word is
 * known to mean something else in another industry - packaging in consumer
 * goods, cable in television, power in "purchasing power".
 *
 * A description can still omit the business that matters. A real-estate
 * developer building a data centre may describe itself as a real-estate
 * developer. The pass therefore measures itself against the companies
 * already known to qualify and reports every one it fails to nominate:
 * that miss rate is the blind spot of this step, and it is printed rather
 * than assumed away.
 */

/**
 * Terms per sub-layer.
 *
 * Plant and products, not themes: "transformers", not "energy transition".
 * The words that describe a market ("AI", "digital", "data") are absent on
 * purpose - every company uses them.
 */
export const NOMINATION_TERMS = Object.freeze({
  'power/generation': [
    /\bpower generation\b/,
    /\bgenerat(?:es|ing|ion of) (?:electricity|power)\b/,
    /\bindependent power producers?\b/,
    /\brenewable (?:energy|power)\b/,
    /\bsolar (?:power|energy|parks?|projects?|plants?|modules?|cells?)\b/,
    /\bwind (?:power|energy|farms?|turbines?)\b/,
    /\bhydro ?(?:electric|power)\b/,
    /\bthermal power\b/,
    /\bcaptive power\b/,
    // NTPC: "generation and sale of bulk power". Missed by the first run.
    /\bgeneration (?:and|&) (?:sale|supply|distribution) of (?:bulk )?(?:power|electricity)\b/,
    /\bpower (?:plants?|stations?|producers?)\b/,
  ],
  'power/transmission': [
    /\bpower transmission\b/,
    /\btransmission (?:lines?|towers?|projects?|infrastructure|and distribution)\b/,
    /\bsub-?stations?\b/,
    /\bhvdc\b/,
    /\bgrid (?:infrastructure|automation|connectivity)\b/,
  ],
  'power/equipment': [
    /\btransformers?\b/,
    /\bswitchgears?\b/,
    /\bswitch ?boards?\b/,
    /\bcircuit breakers?\b/,
    /\b(?:power|electrical|electric|lt|ht|high voltage|low voltage|medium voltage) cables?\b/,
    /\bwires? and cables?\b/,
    /\bcables? and wires?\b/,
    /\bgensets?\b/,
    /\bdiesel generat(?:ors?|ing sets?)\b/,
    /\bbus ?(?:bars?|ducts?)\b/,
    /\b(?:power|electrical) equipment\b/,
    /\buninterruptible power\b/,
    /\bups systems?\b/,
    /\bbattery energy storage\b/,
    /\blithium[- ]ion batter(?:y|ies)\b/,
    /\bsmart meter(?:s|ing)?\b/,
    // Amara Raja, HBL: data centre UPS runs on these. Missed by the first run.
    /\blead[- ]acid batter(?:y|ies)\b/,
    /\b(?:industrial|storage|stationary) batter(?:y|ies)\b/,
  ],
  'data_centre/developer_operator': [
    /\bdata ?cent(?:er|re)s?\b/,
    /\bco-?location\b/,
    /\bhyperscale(?:rs?)?\b/,
  ],
  'data_centre/hardware': [
    /\bservers?\b/,
    /\bstorage systems?\b/,
    /\bhigh[- ]performance computing\b/,
    /\bsupercomput(?:er|ers|ing)\b/,
    /\bnetworking (?:equipment|products|solutions|hardware)\b/,
    /\boptical fib(?:re|er)s?\b/,
    /\bfib(?:re|er)[- ]optic(?:s|al)?\b/,
    /\bprecision (?:air[- ]conditioning|cooling)\b/,
    /\bliquid cooling\b/,
    /\bchillers?\b/,
    /\bhvac\b/,
    // Blue Star says "air conditioning", not HVAC. Missed by the first run.
    // "air-conditioned" (a hotel room) does not match; "air conditioning" does.
    /\bair[- ]conditioning\b/,
    /\bcooling (?:solutions|systems|equipment)\b/,
    /\btelecom(?:munications?)? equipment\b/,
  ],
  'semiconductor/osat': [
    /\bsemiconductors?\b/,
    /\bosat\b/,
    /\bassembly,? test(?:ing)?,? (?:and|&) packaging\b/,
    /\b(?:chip|ic|semiconductor) packaging\b/,
    /\bintegrated circuits?\b/,
    /\belectronics? manufacturing services\b/,
    /\bems\b/,
    /\bprinted circuit boards?\b/,
    /\bpcbs?\b/,
  ],
  'semiconductor/materials': [
    /\bspecialty gases\b/,
    /\bindustrial gases\b/,
    /\belectronic[- ]grade (?:chemicals|gases|materials)\b/,
    /\bhigh[- ]purity (?:chemicals|gases|materials)\b/,
    /\bphotoresists?\b/,
    /\bpolysilicon\b/,
    /\b(?:silicon )?wafers?\b/,
    /\bsputtering targets?\b/,
    /\bultra[- ]?pure\b/,
  ],
  'semiconductor/hardware': [
    /\bsemiconductor (?:capital )?equipment\b/,
    /\bfab(?:rication)? equipment\b/,
    /\btest (?:and|&) measurement\b/,
    /\bclean ?rooms?\b/,
    /\bvacuum (?:pumps?|systems?)\b/,
  ],
  'infrastructure/epc': [
    /\bepc\b/,
    /\bengineering,? procurement,? (?:and|&) construction\b/,
    /\bturnkey (?:projects?|solutions?)\b/,
  ],
});

/**
 * Phrases that contain a term but mean something else.
 *
 * Removed from the text before matching, so they cannot nominate. Each is a
 * known collision, not a guess: "cable television" is a broadcaster, "web
 * servers" in a description is an IT services firm's hosting line, not a
 * server maker.
 */
const FALSE_FRIENDS = Object.freeze([
  /\bcable (?:tv|television|network|operators?|broadband)\b/g,
  /\bmulti[- ]system operators?\b/g,
  /\b(?:food|flexible|consumer|rigid|paper|plastic|pet) packaging\b/g,
  /\bweb servers?\b/g,
  /\bgame servers?\b/g,
  /\bfood servers?\b/g,
]);

const normalise = (text) => {
  let out = String(text || '').toLowerCase().replace(/\s+/g, ' ');
  for (const phrase of FALSE_FRIENDS) out = out.replace(phrase, ' ');
  return out;
};

/**
 * Which sub-layers a company's own description names, and by which words.
 *
 * `terms` records the text that matched, so a reviewer can see at a glance
 * whether "servers" meant rack servers or something else.
 */
export function nominate({ description = '' } = {}) {
  const text = normalise(description);
  if (!text.trim()) return { nominated: false, reason: 'NO_DESCRIPTION', subLayers: [] };
  const subLayers = [];
  for (const [subLayer, patterns] of Object.entries(NOMINATION_TERMS)) {
    const terms = new Set();
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) terms.add(match[0]);
    }
    if (terms.size) subLayers.push({ subLayer, terms: [...terms] });
  }
  return subLayers.length
    ? { nominated: true, reason: null, subLayers }
    : { nominated: false, reason: 'NO_TERM_MATCHED', subLayers: [] };
}

/**
 * The order to read nominations in. Not a score, and never a filter.
 *
 * 495 companies were nominated by the first full run, and they are read one
 * at a time. This decides which come first:
 *
 *   1 - strong: the company's own sector makes the plant it names its
 *       business. An electrical-equipment maker naming transformers; a
 *       power utility naming generation. Data-centre terms are specific
 *       enough to be strong in any sector.
 *   2 - contractor: nominated only as EPC, and in a construction sector.
 *       The contractor rule is stricter (a named project, a contracted role,
 *       identifiable exposure), so these read after the strong tier.
 *   3 - incidental: the term is real but probably not the business - a
 *       textile mill's captive windmill, a sugar mill's co-generation plant.
 *       Still read, last.
 *
 * Sector names are Upstox's. A sector missing from a set sends a company to
 * tier 3, never out of the list, so the cost of an incomplete set is a late
 * reading, not a lost member.
 */
const ELECTRICAL = ['Electric Equipment', 'Capital Goods - Electrical Equipment', 'Capital Goods', 'Engineering'];
const POWER = ['Power', 'Power Generation & Distribution', 'Power Infrastructure'];
const CONSTRUCTION = ['Engineering', 'Construction', 'Infrastructure Developers & Operators', 'Power Infrastructure', 'Transmission Towers'];

export const SECTOR_AFFINITY = Object.freeze({
  // Generation equipment makers (turbines, modules) sit in electrical
  // sectors, not in Power. The first run ranked Suzlon, Inox Wind and Waaree
  // incidental because this set held only utilities.
  'power/generation': new Set([...POWER, ...ELECTRICAL]),
  'power/transmission': new Set([...ELECTRICAL, ...POWER, 'Transmission Towers', 'Cable', 'Cables', 'Infrastructure Developers & Operators']),
  'power/equipment': new Set([...ELECTRICAL, 'Cable', 'Cables', 'Diesel Engines', 'Batteries', 'Electronics', 'Compressors', 'Power Infrastructure']),
  'data_centre/developer_operator': null,
  'data_centre/hardware': new Set([
    'IT - Hardware', 'IT - Networking', 'Electronics', 'Cable', 'Cables', 'Telecom Equipment & Infra Services',
    'Telecommunication', 'Air Conditioners', 'Consumer Durables', 'Compressors', ...ELECTRICAL,
  ]),
  // Dixon is filed under Consumer Durables. Missed by the first run.
  'semiconductor/osat': new Set([
    'Electronics', 'IT - Hardware', 'IT - Networking', 'Aerospace & Defence', 'Defence', 'Consumer Durables', ...ELECTRICAL,
  ]),
  'semiconductor/materials': new Set(['Chemicals', 'Gases & Fuels', 'Petrochemicals', 'Non Ferrous Metals', 'Metals', 'Minerals', 'Dyes & Pigments']),
  'semiconductor/hardware': new Set(['Capital Goods-Non Electrical Equipment', 'Electronics', 'Compressors', ...ELECTRICAL]),
});

export function readingPriority({ sector = null, nomination = [] } = {}) {
  const subLayers = (nomination || []).map((one) => one.subLayer);
  if (!subLayers.length) return null;
  const strong = subLayers.filter((sub) => sub !== 'infrastructure/epc'
    && (SECTOR_AFFINITY[sub] === null || SECTOR_AFFINITY[sub]?.has(sector)));
  if (strong.length) return { tier: 1, subLayers: strong };
  if (subLayers.includes('infrastructure/epc') && CONSTRUCTION.includes(sector)) {
    return { tier: 2, subLayers: ['infrastructure/epc'] };
  }
  return { tier: 3, subLayers };
}
