import { windowOverlaps } from './issuerTickerRegistry.js';

/**
 * Recovering the US ticker from a foreign venue's quote symbol.
 *
 * OpenFIGI was asked for a ticker and, when it had no US line for a CUSIP,
 * answered with whichever venue it did have. European venues quote US shares
 * in local currency and name the line accordingly, so Honeywell arrives as
 * HONGBP, Lam Research as LRCXEUR, Carnival as CCL1EUR.
 *
 * These are not obscure securities. They are large US positions - $622bn of
 * holdings - wearing the wrong name, and the damage is not only that Yahoo
 * cannot price them. The screener and the consensus tables key on ticker, so
 * HONGBP and HON count as two different companies and Honeywell's
 * institutional ownership is split across both.
 *
 * Three notations turn up, and only one of them is about currency. A slash
 * is a share class - BRK/B is Berkshire's B stock, which Yahoo and the SEC
 * both write BRK-B, and BRK/A and BRK/B together are $725bn, the largest
 * single block of unpriceable holdings in the book. A trailing asterisk
 * marks the line rather than the security: EA* is Electronic Arts.
 *
 * The recovery is a guess, so it is made to prove itself. Rewriting a symbol
 * produces a plausible ticker almost every time; what makes it safe is
 * refusing the result unless the issuer we hold and the company the SEC
 * lists under that ticker are the same company. Without that check, a symbol
 * whose tail merely resembles a currency code hands its position to whatever
 * unrelated ticker the rewritten string happens to spell.
 */

// Deliberately narrow. Each of these appears in the observed data, and every
// entry added is another chance to trim a symbol that only looks suffixed.
const CURRENCIES = ['USD', 'EUR', 'GBP', 'GBX', 'GBp', 'CHF', 'JPY', 'CAD', 'AUD', 'SEK', 'NOK', 'DKK', 'HKD', 'SGD', 'ZAR', 'MXN', 'BRL'];

/**
 * Candidate US tickers for a venue symbol, best first.
 *
 * A trailing digit is part of the venue's line number, not the ticker:
 * Carnival is CCL1EUR on Xetra and CCL in New York.
 */
export function candidateBases(symbol) {
  const s = String(symbol || '').trim().toUpperCase();
  if (!s) return [];
  const out = [];

  // A slash is a share class, not a venue. BRK/B is Berkshire's B stock and
  // Yahoo writes it BRK-B, as does the SEC's own ticker file. This was being
  // refused for having no currency suffix, which is true and beside the
  // point: BRK/B and BRK/A together are $725bn, the largest single block of
  // unpriceable holdings in the book.
  const slash = s.match(/^([A-Z]{1,5})\/([A-Z])$/);
  if (slash) return [`${slash[1]}-${slash[2]}`];

  // A trailing asterisk marks the line, not the security. EA* is Electronic
  // Arts; the ticker underneath is EA.
  const starred = s.match(/^([A-Z]{1,5})\*$/);
  if (starred) return [starred[1]];

  for (const ccy of CURRENCIES) {
    const cc = ccy.toUpperCase();
    if (!s.endsWith(cc) || s.length <= cc.length) continue;
    const stem = s.slice(0, -cc.length);
    out.push(stem);
    // CCL1EUR -> CCL, TEL1USD -> TEL, TRI4EUR -> TRI
    if (/\d$/.test(stem) && stem.length > 1) out.push(stem.replace(/\d+$/, ''));
  }
  return [...new Set(out)].filter((base) => /^[A-Z]{1,5}(-[A-Z])?$/.test(base));
}

/**
 * Recover a ticker, or explain why not.
 *
 * `secByTicker` maps a US ticker to the company name the SEC registers for
 * it; `issuerName` is the name on the holding. Both arrive as written - the
 * comparison does its own normalising - so this stays free of network and
 * database.
 */
/**
 * A recovery target has to be shaped like a US ticker.
 *
 * The historical registry is built from what filers typed into a Form 345
 * symbol field, and some of them typed the exchange too: the entry for
 * Steelcase is "NYSE: SCS". Proposed unchecked, that string is written into
 * security_identifier_history as a ticker, where nothing will ever price it
 * and everything downstream keys on it.
 *
 * The same shape the price planner uses, so a recovery cannot propose a symbol
 * the fetcher would refuse to ask about.
 */
const US_TICKER = /^[A-Z]{1,5}(-[A-Z])?$/;
export const isUsTicker = (value) => US_TICKER.test(String(value || '').trim().toUpperCase());

export function recoverTicker(symbol, issuerName, secByTicker, { registry = null, window = null } = {}) {
  const bases = candidateBases(symbol);
  const held = String(issuerName || '').trim();
  if (!held) return { ticker: null, reason: 'holding has no issuer name to check against' };

  // A symbol with nothing to extract is not the end of it. HO1, 8QR, 07WA and
  // 62C carry no ticker at all - they are venue line numbers - but the holding
  // still names its issuer, and the registry knows which ticker that issuer
  // filed under. Hologic is HOLX whether or not the symbol says so.
  //
  // Only when the symbol yields nothing, and only on a unique match. A name
  // that fits two issuers is refused: the point of the register is to stop
  // guessing, not to move the guess somewhere less visible.
  if (!bases.length) {
    if (!registry) return { ticker: null, reason: 'no recoverable ticker in this symbol' };
    const byName = [];
    for (const [ticker, entries] of registry) {
      for (const entry of entries) {
        if (!sameCompany(entry.issuer_name, held)) continue;
        if (window && !windowOverlaps(entry, window)) continue;
        byName.push({ ticker, entry });
        break;
      }
    }
    // Malformed registry symbols are dropped before they can be proposed or
    // counted as ambiguity - "NYSE: SCS" is not a second candidate for
    // Steelcase, it is not a candidate at all.
    const distinct = [...new Set(byName.map((row) => row.ticker))].filter(isUsTicker);
    if (distinct.length === 1) {
      // The surviving ticker's own entry, not byName[0] - a malformed symbol
      // filtered out above could have been first, and its dates would then
      // describe a different registration than the one being proposed.
      const { entry } = byName.find((row) => row.ticker === distinct[0]);
      // Weak when the whole match rests on one word and the two names are
      // different lengths. NEW GOLD INC CDA reduces to GOLD/CDA - NEW is
      // dropped as filer noise - so a registry name reducing to GOLD alone
      // matches it on that single word, while New Gold trades as NGD and GOLD
      // is Barrick.
      //
      // Not refused, because the same shape is right elsewhere: SKECHERS U S A
      // INC against Skechers USA Inc rests on SKECHERS alone and is correct.
      // One word is distinctive and the other generic, and nothing in the
      // strings knows which - so it is marked for a reader rather than decided
      // here, where the decision would be wrong half the time in silence.
      const heldWords = tokens(held).length;
      const registeredWords = tokens(entry.issuer_name).length;
      return {
        ticker: distinct[0],
        reason: null,
        via: `the issuer name in SEC filings ${entry.first_seen}..${entry.last_seen}`,
        weak: Math.min(heldWords, registeredWords) === 1 && heldWords !== registeredWords,
      };
    }
    return {
      ticker: null,
      reason: distinct.length
        ? `no ticker in this symbol, and the issuer name fits ${distinct.length} of them: ${distinct.slice(0, 4).join('/')}`
        : 'no recoverable ticker in this symbol, and no filing names this issuer',
    };
  }

  const matched = [];
  let via = 'the SEC register';
  for (const base of bases) {
    const secName = secByTicker.get(base);
    if (!secName) continue;
    // The whole safety of this rests here. A trimmed string that happens to
    // spell a real ticker is not evidence; the companies have to agree.
    if (sameCompany(secName, held)) matched.push(base);
  }

  // The live register answers for a live holding and cannot answer for a past
  // one. Activision, Pioneer, Seagen, Splunk, WestRock, Marathon Oil, Discover
  // and Electronic Arts have all left it, and $1.48tn of holdings were refused
  // for asking a question it is not shaped to answer.
  //
  // The historical registry is consulted only when the live one has nothing,
  // so a currently-registered ticker is never overruled by what it used to be.
  // The check itself is unchanged: the companies still have to agree.
  if (!matched.length && registry) {
    for (const base of bases) {
      for (const entry of registry.get(base) || []) {
        // Both must hold. A name match alone would attribute a 2019 Paramount
        // holding to Banzai International, which took the PARA ticker over in
        // 2026 - the exact reassignment this is otherwise careful about.
        if (!sameCompany(entry.issuer_name, held)) continue;
        if (window && !windowOverlaps(entry, window)) continue;
        matched.push(base);
        via = `SEC filings ${entry.first_seen}..${entry.last_seen}`;
        break;
      }
    }
  }

  if (!matched.length) {
    const known = bases.filter((b) => secByTicker.has(b));
    const seenBefore = registry ? bases.filter((b) => (registry.get(b) || []).length) : [];
    return {
      ticker: null,
      reason: known.length
        ? `resolves to ${known.join('/')} but the issuer is "${held}", not "${known.map((b) => secByTicker.get(b)).join('/')}"`
        : seenBefore.length
          ? `resolves to ${seenBefore.join('/')}, which SEC filings show as ${seenBefore.flatMap((b) => (registry.get(b) || []).map((e) => `"${e.issuer_name}"`)).slice(0, 2).join('/')}, not "${held}"`
          : `resolves to ${bases.join(', ')}, which neither the SEC register nor past filings know`,
    };
  }
  // Two bases naming the same company is not a conflict; two different
  // companies would be, and the name check has already excluded that.
  if (new Set(matched).size > 1) return { ticker: null, reason: `ambiguous: ${matched.join('/')}` };
  return { ticker: matched[0], reason: null, via };
}


/**
 * The words a filer and the SEC spell differently for the same company.
 *
 * A 13F cover page abbreviates: Honeywell files as HONEYWELL INTL, the SEC
 * registers it as HONEYWELL INTERNATIONAL. Requiring the strings to match
 * exactly refused $74bn of Honeywell on a spelling difference.
 */
const ABBREVIATIONS = new Map(Object.entries({
  INTL: 'INTERNATIONAL', INTERNATIONALE: 'INTERNATIONAL',
  FINL: 'FINANCIAL', FIN: 'FINANCIAL', SVCS: 'SERVICES', SVC: 'SERVICES',
  NATL: 'NATIONAL', RES: 'RESOURCES', RESOURCE: 'RESOURCES',
  TECHNOLOGIES: 'TECHNOLOGY', TECH: 'TECHNOLOGY', PHARMACEUTICALS: 'PHARMACEUTICAL',
  PHARM: 'PHARMACEUTICAL', PHARMA: 'PHARMACEUTICAL', THERAPEUTICS: 'THERAPEUTIC',
  HLDGS: 'HOLDINGS', HLDG: 'HOLDINGS', HLDNG: 'HOLDINGS', HLDNGS: 'HOLDINGS', HOLDING: 'HOLDINGS',
  GRP: 'GROUP', INDS: 'INDUSTRIES', IND: 'INDUSTRIES', INDUSTRIE: 'INDUSTRIES',
  COMMUNICATIONS: 'COMMUNICATION', SYS: 'SYSTEMS', SYSTEM: 'SYSTEMS',
  LABS: 'LABORATORIES', LAB: 'LABORATORIES', LABORATORY: 'LABORATORIES',
  MTRS: 'MOTORS', MTR: 'MOTORS', PPTYS: 'PROPERTIES', PPTY: 'PROPERTIES',
  ENTERPRISE: 'ENTERPRISES', BIOSCIENCE: 'BIOSCIENCES', ELECTRIC: 'ELECTRICAL',
  // Added from refusals that were spelling differences and nothing else:
  // Shockwave Medical filed as SHOCKWAVE MED, New York Community Bancorp as
  // NEW YORK CMNTY, Horizon Therapeutics Public as HORIZON THERAPEUTICS PUB.
  MED: 'MEDICAL', CMNTY: 'COMMUNITY', COMMUNITIES: 'COMMUNITY',
  PUB: 'PUBLIC', PUBL: 'PUBLIC', CMNCTNS: 'COMMUNICATION',
  MGMT: 'MANAGEMENT', MGT: 'MANAGEMENT', DEV: 'DEVELOPMENT',
  MFG: 'MANUFACTURING', SOLUTION: 'SOLUTIONS', PRODUCT: 'PRODUCTS',
  BANCORPORATION: 'BANCORP', BANCSHARES: 'BANCORP',
  // A second batch, taken from the refusal messages of a real run rather than
  // from imagination. Each of these was a holding and an SEC name that name the
  // same company in different words, and nothing else:
  //
  //   ALTAIR ENGR / Altair Engineering            $7.3bn
  //   UNITED STATES STL / United States Steel    $17.5bn
  //   SUMMIT MATLS / Summit Materials             $7.0bn
  //   AMERICAN EQTY INVT LIFE HLD / American Equity Investment Life Holding
  //   SITE CTRS / SITE Centers                    $4.9bn
  //   PATTERSON COS / Patterson Companies         $4.6bn
  //   RETAIL OPPORTUNITY INVTS / ... Investments  $4.0bn
  //   SPIRIT RLTY CAP / Spirit Realty Capital     $3.1bn
  //   EQUITY COMWLTH / Equity Commonwealth        $2.9bn
  //   SIX FLAGS ENTMT / Six Flags Entertainment   $2.9bn
  ENGR: 'ENGINEERING', ENG: 'ENGINEERING',
  EQTY: 'EQUITY', INVT: 'INVESTMENT', INVTS: 'INVESTMENT', INVESTMENTS: 'INVESTMENT',
  HLD: 'HOLDINGS', CTRS: 'CENTERS', CTR: 'CENTERS', CENTER: 'CENTERS',
  COS: 'COMPANIES', RLTY: 'REALTY', CAP: 'CAPITAL',
  ENTMT: 'ENTERTAINMENT', ENTERTAINMENTS: 'ENTERTAINMENT',
  STL: 'STEEL', MATLS: 'MATERIALS', MATL: 'MATERIALS', MATERIAL: 'MATERIALS',
  COMWLTH: 'COMMONWEALTH',
}));

/**
 * Abbreviations that stand for more than one word.
 *
 * A filer writing NAT could mean NATIONAL or NATURAL, and forcing one reading
 * is worse than admitting both: PIONEER NAT RES became Pioneer *National*
 * Resources and failed against PIONEER NATURAL RESOURCES, refusing $49bn on a
 * choice the abbreviation never made.
 *
 * A word with alternatives matches if any of them agrees, which is looser than
 * a single expansion and still far stricter than ignoring the word - the
 * position in the name must still line up, and every other word must still
 * match exactly.
 */
const AMBIGUOUS = new Map(Object.entries({
  NAT: ['NATIONAL', 'NATURAL'],
  AMER: ['AMERICA', 'AMERICAN'],
  CORPORATE: ['CORPORATE', 'CORPORATION'],
  GEN: ['GENERAL', 'GENERAL'],
  INTL: ['INTERNATIONAL'],
}));

/** Words that identify a filing, not a company. */
const NOISE = new Set([
  'INC', 'CORP', 'CORPORATION', 'CO', 'COMPANY', 'LTD', 'LIMITED', 'PLC', 'LLC', 'LP',
  'SA', 'NV', 'AG', 'THE', 'NEW', 'DEL', 'DE', 'CL', 'CLASS', 'COM', 'ORD', 'SHS',
  'CAN', 'USA', 'US', 'AMERICA', 'AMERICAN', 'TRUST', 'REIT', 'ADR', 'ADS', 'SPON', 'SPONSORED',
  // Share class, which the ticker suffix already carries. A holding reading
  // "Petrobras Pref ADR" is the same company as "PETROBRAS - PETROLEO
  // BRASILEIRO SA"; the word that differs describes the line, not the issuer,
  // and PBR/A resolves to PBR-A, whose class is in the ticker itself.
  'PREF', 'PREFERRED', 'PFD',
  // OLD is deliberately absent, though EDGAR marks a renamed registrant's old
  // record with it. Six Flags Entertainment Corp/OLD already matches SIX FLAGS
  // ENTMT CORP NEW without it, because a shorter name is allowed to say less
  // than a longer one - so dropping OLD changes nothing there and only loosens
  // the case where the holding is the longer name. A word that earns nothing
  // and costs precision is not worth carrying.
  //
  // A truncated CORP. 13F issuer names are cut to a fixed width, and a name
  // ending "INVTS COR" is one character short of a word already ignored.
  'COR',
]);

/**
 * A name as a list of words, each with the forms it could stand for.
 *
 * A set per word rather than a single string, because an abbreviation can be
 * honest about being ambiguous. Two words agree when their sets intersect.
 */
export function tokens(name) {
  return String(name || '')
    .toUpperCase()
    .replace(/[^A-Z0-9 ]+/g, ' ')
    .split(/\s+/)
    .filter((w) => w && !NOISE.has(w) && !NOISE.has(ABBREVIATIONS.get(w) || w))
    .map((w) => new Set(AMBIGUOUS.get(w) || [ABBREVIATIONS.get(w) || w]));
}

function agrees(a, b) {
  for (const form of a) if (b.has(form)) return true;
  return false;
}

/**
 * Are these two names the same company?
 *
 * Loose enough for a filer's abbreviations, strict enough to keep a ticker
 * that changed hands. Words are compared in order from the first, so RNA -
 * AVIDITY BIOSCIENCES on the holding, ATRIUM THERAPEUTICS at the SEC - fails
 * on the opening word, which is the tell for a real reassignment. What the
 * order allows is one name simply saying less than the other: FERGUSON
 * against FERGUSON ENTERPRISES is one company described at two lengths.
 */
export function sameCompany(a, b) {
  const x = tokens(a);
  const y = tokens(b);
  if (!x.length || !y.length) return false;
  const short = x.length <= y.length ? x : y;
  const long = short === x ? y : x;
  return short.every((word, i) => long[i] && agrees(word, long[i]));
}
