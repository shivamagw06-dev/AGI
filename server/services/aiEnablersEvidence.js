/**
 * What counts as evidence that a company builds AI infrastructure.
 *
 * The cheapest way to build a fake AI index is to count the word "AI" in
 * transcripts, and the second cheapest is to count exchange filings without
 * reading them. A company's announcement feed is mostly ESOP allotments,
 * newspaper publications, postal ballots and AGM notices; a fundraise is a
 * fundraise whatever the money is for. None of that is evidence of anything
 * except that the company is listed.
 *
 * So evidence is classified before it is counted, and the classification
 * carries the distinction the screen turns on:
 *
 *   hard  - a signed order, a committed capex, or an operating disclosure.
 *           Something happened that the company had to tell the exchange.
 *   soft  - a partnership, an intention, or language in a transcript.
 *           Something was said.
 *
 * Soft evidence never admits a company. It raises a candidate for review. That
 * single rule is what separates a screen from a word count, because the words
 * arrive first and arrive for everyone.
 */

/** Filings every listed company makes, which say nothing about its business. */
const ROUTINE = [
  /allotment of (?:esop|espp|esps)/i,
  /\besop\b|\bespp\b|\besps\b/i,
  /newspaper publication/i,
  /\bbook closure\b/i,
  /annual general meeting|\bagm\b/i,
  /postal ballot|scrutinizer/i,
  /trading window/i,
  /business responsibility and sustainability/i,
  /reg\.? ?34|annual report/i,
  /investor meet|analyst ?\/ ?investor/i,
  /dispatch of (?:physical )?letter/i,
  /change (?:in|of) (?:registrar|company secretary|auditor|director)/i,
  /loss of share certificate|duplicate share/i,
  /compliance certificate|certificate under regulation/i,
];

/**
 * A capital raise is not evidence of AI exposure.
 *
 * It is the most common false positive in this screen: a fundraise is exciting,
 * it moves the price, it is often reported alongside AI commentary, and it says
 * nothing whatever about what the company builds. It is classified explicitly
 * rather than left to fall through, so the reason is visible.
 */
const FUNDRAISE = /qualified institution(?:s|al)? placement|\bqip\b|preferential (?:issue|allotment)|rights issue|fund ?rais/i;

/**
 * Market commentary, which is not evidence about the company saying it.
 *
 * Found by running the screen against real filings. Every transformer maker's
 * investor presentation contains a page on how India's data centre capacity
 * will reach 8-10 GW by 2031, sourced to CRISIL or CareEdge. That is a claim
 * about the market, and it appears in the documents of companies with data
 * centre orders and companies with none, identically. Counting it admits the
 * entire sector on the strength of its slide decks.
 *
 * A hard item has to describe something the company did.
 */
const MARKET_COMMENTARY = [
  /\b(?:is|are) (?:expected|projected|estimated|likely|forecast) to\b/i,
  /\bmarket (?:is|size|opportunity|outlook)\b/i,
  /\bindustry (?:is|demand|outlook)\b/i,
  /\bcagr\b/i,
  /source:\s*(?:crisil|careedge|mordor|wood ?mackenzie|cbre|frost)/i,
  /\bby (?:fiscal|fy)\s?20\d\d\b.*\b(?:gw|twh|billion|trillion)\b/i,
];

/**
 * A projection, however it is dressed.
 *
 * Diamond Power's deck carries "Data-centre capacity (MW) FY19 350 FY25 1,300
 * FY30P 5,000" - a bare table with no verb in it at all, which matched on the
 * word MW and was classified as an operating disclosure. The P is the whole
 * signal.
 */
const PROJECTION = [
  /\bfy ?\d{2}\s?[pe]\b/i,
  /\b20\d\d\s?[pe]\b/,
  /\bprojected\b|\bforecast\w*\b|\bestimated\b/i,
];

/** What the company itself did, said in the first person or about its own book. */
const FIRST_PARTY = [
  /\b(?:we|our|the company|the group)\b/i,
  /\breceived an order\b|\bsecured\b|\bwon\b|\bbagged\b|\bawarded\b/i,
  /\border (?:book|backlog|intake|signed)\b/i,
  /\bcommissioned\b|\bexecuted\b|\bdispatched\b|\bhanded over\b|\bcompleted\b/i,
  /\bcod\b|\boperational capacity\b|\bcontracted capacity\b|\btied up\b/i,
];

const HARD_KINDS = [
  {
    kind: 'order',
    // Both halves matter. A filing may say "received an order" or it may
    // describe one: "a significant data center-related order for a Load
    // Pooling Station". Requiring the verb missed the second, which is how a
    // company's own earnings call describes the orders it just won.
    test: /\b(?:receiv|secur|bagg?|win|won|award|letter of (?:intent|award)|\bloa\b|work order|purchase order|contract)\w*\b|\border (?:for|from|worth|valued)\b/i,
  },
  {
    kind: 'capex',
    test: /\b(?:capital expenditure|capex|new (?:plant|facility|fab|unit|line)|expansion of|commission\w*|greenfield|brownfield|ground ?break)\b/i,
  },
  {
    kind: 'operating',
    test: /\b(?:segment (?:revenue|results?)|revenue from operations|order book|capacity (?:added|commissioned|energi[sz]ed)|units? shipped|mw\b|megawatt)\b/i,
  },
];

const SOFT_KINDS = [
  { kind: 'partnership', test: /\b(?:memorandum of understanding|\bmou\b|partnership|collaborat\w+|tie-?up|joint venture|\bjv\b|strategic (?:alliance|agreement))\b/i },
];

/**
 * The vocabulary that makes a filing AI-infrastructure relevant.
 *
 * Deliberately physical. "AI" alone is not on this list as a sufficient term
 * for a hard item, because every company says it; the words that carry
 * information are the ones describing plant: racks, substations, packaging
 * lines, megawatts.
 */
export const INFRASTRUCTURE_TERMS = Object.freeze([
  /\bdata ?cent(?:er|re)\b/i, /\bhyperscal\w+/i, /\bcolocation\b|\bco-?lo\b/i,
  /\bgpu\b/i, /\baccelerator\b/i, /\bhpc\b|high[- ]end computing/i,
  // "AI" as a qualifier of a business noun. A bare /\bai\b/ would match every
  // deck in the market; this matches a company talking about an AI line of
  // business. Netweb discloses "AI Systems 62.29% of revenue" - the plainest
  // evidence there is - and without this it was only caught because the word
  // HPC happened to appear later in the same paragraph.
  /\bai (?:segment\w*|revenue\w*|server\w*|system\w*|infrastructure|hardware|compute|cluster\w*|workload\w*|accelerator\w*|factor(?:y|ies)|data ?cent(?:er|re)\w*)/i,
  /\bliquid cooling\b|\bchiller\b/i, /\brack\b/i,
  /\bsubstation\b/i, /\btransformer\b/i, /\bswitchgear\b/i, /\bhvdc\b/i, /\btransmission line\b/i,
  /\bpower purchase agreement\b|\bppa\b/i, /\bcaptive power\b/i, /\bmegawatt\b|\bmw\b/i,
  /\bosat\b/i, /\bsemiconductor\b/i, /\bfab\b/i, /advanced packaging/i, /\bwafer\b/i, /\bassembly and test\b/i,
  /\bfib(?:er|re)\b/i, /\bdark fibre\b/i, /\bnvidia\b/i,
]);

const matches = (text, patterns) => patterns.some((pattern) => pattern.test(text));

/**
 * One announcement or document, classified.
 *
 * `aiRelevant` and `hard` are independent, and both are required to admit.
 * A large order for a cement plant is hard and irrelevant; a press note about
 * an AI partnership is relevant and soft. Neither admits anyone.
 */
export function classifyEvidence({ title = '', description = '', source = '', kind: declared = null } = {}) {
  const text = `${title} ${description}`.trim();
  if (!text) return { kind: 'empty', hard: false, aiRelevant: false, why: 'no text' };

  if (matches(text, ROUTINE)) {
    return { kind: 'routine', hard: false, aiRelevant: false, why: 'a filing every listed company makes' };
  }
  if (FUNDRAISE.test(text)) {
    return { kind: 'fundraise', hard: false, aiRelevant: false, why: 'a capital raise says nothing about what is built' };
  }

  const aiRelevant = matches(text, INFRASTRUCTURE_TERMS);
  const hard = HARD_KINDS.find((one) => one.test.test(text));
  if (hard) {
    // A forecast about the sector, in a deck, is not something the company
    // did - and it appears in the decks of companies with orders and
    // companies with none, identically.
    // Forward-looking language, a projection marker, or a research house in
    // the source line - any of them, with nothing the company itself did.
    const commentary = (matches(text, MARKET_COMMENTARY) || matches(text, PROJECTION))
      && !matches(text, FIRST_PARTY);
    if (commentary) {
      return { kind: 'market_commentary', hard: false, aiRelevant, source,
        why: 'a claim about the market, not about this company' };
    }
    return {
      kind: hard.kind, hard: true, aiRelevant, source,
      why: aiRelevant ? `${hard.kind} naming AI infrastructure` : `${hard.kind}, but nothing ties it to AI infrastructure`,
    };
  }
  const soft = SOFT_KINDS.find((one) => one.test.test(text));
  if (soft) {
    return { kind: soft.kind, hard: false, aiRelevant, source, why: 'an intention, not a commitment' };
  }
  // Language in a transcript or a news story with no event behind it.
  return {
    kind: declared === 'transcript' ? 'language' : 'news', hard: false, aiRelevant, source,
    why: aiRelevant ? 'the vocabulary is there, the event is not' : 'neither an event nor the vocabulary',
  };
}

/**
 * Whether a body of evidence admits a company to the universe.
 *
 * One hard, AI-relevant item admits. Everything else - however much of it there
 * is - raises a candidate for a named reviewer, and the count of soft items is
 * reported so a reviewer can see how loud the talk is relative to the silence.
 */
export function admits(evidence = []) {
  const classified = evidence.map((one) => ({ ...one, verdict: classifyEvidence(one) }));
  const hard = classified.filter((one) => one.verdict.hard && one.verdict.aiRelevant);
  const soft = classified.filter((one) => !one.verdict.hard && one.verdict.aiRelevant);
  if (hard.length) {
    return {
      admitted: true, basis: 'hard', hard, soft,
      reason: `${hard.length} hard item${hard.length === 1 ? '' : 's'} naming AI infrastructure`,
    };
  }
  if (soft.length) {
    return {
      admitted: false, basis: 'soft', hard: [], soft,
      reason: `${soft.length} soft item${soft.length === 1 ? '' : 's'} and nothing signed - for review, not for the index`,
    };
  }
  return { admitted: false, basis: 'none', hard: [], soft: [], reason: 'no AI-infrastructure evidence found' };
}

/**
 * Which sub-layer the evidence puts a company in.
 *
 * Read from what the evidence describes rather than from the company's sector
 * label, because a capital goods classification covers a transformer maker and
 * a rack maker equally and tells a reader nothing about which one it is.
 * Returns every sub-layer the evidence supports - a company that makes both
 * transformers and switchgear for data centres genuinely sits in two.
 */
// Every noun here ends in \w* rather than \b. A filing writes "3X 220kV AIS
// Transformers", and \btransformer\b does not match "Transformers" - which
// silently gave that order no sub-layer at all. Only the start of these terms
// can be bounded safely.
const SUB_LAYERS = [
  ['power', 'generation', /\b(?:power purchase agreement\w*|ppa\b|captive power|solar\w*|wind farm\w*|renewable (?:energy|capacity)|re power|power sales|generation capacity|independent power producer)/i],
  ['power', 'transmission', /\b(?:transmission line\w*|substation\w*|pooling station\w*|hvdc|gas-?insulated busbar\w*|grid connect\w*|evacuation)/i],
  ['power', 'equipment', /\b(?:transformer\w*|switchgear\w*|circuit breaker\w*|cable\w*|genset\w*|rectifier\w*|gas-?insulated switchgear\w*)/i],
  ['data_centre', 'developer', /\b(?:data ?cent(?:er|re)s? (?:park|campus|shell|epc)\w*|build\w* a data ?cent(?:er|re))/i],
  ['data_centre', 'operator', /\b(?:colocation|co-?lo\b|data ?cent(?:er|re)s? (?:capacity|operations)|hyperscal\w+ (?:customer|tenant)\w*)/i],
  ['data_centre', 'hardware', /\b(?:ai server\w*|ai system\w*|gpu\w*|rack\w*|liquid cooling|chiller\w*|accelerator\w*|hpc\b|high[- ]end computing)/i],
  ['semiconductor', 'osat', /\b(?:osat\w*|assembly and test\w*|advanced packaging|outsourced semiconductor)/i],
  ['semiconductor', 'materials', /\b(?:wafer\w*|substrate\w*|specialty gas\w*|photoresist\w*|electronic chemical\w*)/i],
  ['semiconductor', 'hardware', /\b(?:fab equipment|test equipment|lithograph\w+|deposition|etch(?:ing)? (?:tool|system)\w*)/i],
];

export function subLayersFrom(evidence = []) {
  const found = new Map();
  for (const item of evidence) {
    const text = `${item.title || ''} ${item.description || ''}`;
    for (const [layer, subLayer, pattern] of SUB_LAYERS) {
      if (!pattern.test(text)) continue;
      const key = `${layer}/${subLayer}`;
      if (!found.has(key)) found.set(key, { layer, subLayer, evidence: [] });
      found.get(key).evidence.push(item.title || item.description || '');
    }
  }
  return [...found.values()];
}
