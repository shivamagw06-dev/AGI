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
export function recoverTicker(symbol, issuerName, secByTicker) {
  const bases = candidateBases(symbol);
  if (!bases.length) return { ticker: null, reason: 'no recoverable ticker in this symbol' };

  const held = String(issuerName || '').trim();
  if (!held) return { ticker: null, reason: 'holding has no issuer name to check against' };

  const matched = [];
  for (const base of bases) {
    const secName = secByTicker.get(base);
    if (!secName) continue;
    // The whole safety of this rests here. A trimmed string that happens to
    // spell a real ticker is not evidence; the companies have to agree.
    if (sameCompany(secName, held)) matched.push(base);
  }

  if (!matched.length) {
    const known = bases.filter((b) => secByTicker.has(b));
    return {
      ticker: null,
      reason: known.length
        ? `resolves to ${known.join('/')} but the issuer is "${held}", not "${known.map((b) => secByTicker.get(b)).join('/')}"`
        : `resolves to ${bases.join(', ')}, none of which the SEC lists`,
    };
  }
  // Two bases naming the same company is not a conflict; two different
  // companies would be, and the name check has already excluded that.
  if (new Set(matched).size > 1) return { ticker: null, reason: `ambiguous: ${matched.join('/')}` };
  return { ticker: matched[0], reason: null };
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
  NATL: 'NATIONAL', NAT: 'NATIONAL', RES: 'RESOURCES', RESOURCE: 'RESOURCES',
  TECHNOLOGIES: 'TECHNOLOGY', TECH: 'TECHNOLOGY', PHARMACEUTICALS: 'PHARMACEUTICAL',
  PHARM: 'PHARMACEUTICAL', PHARMA: 'PHARMACEUTICAL', THERAPEUTICS: 'THERAPEUTIC',
  HLDGS: 'HOLDINGS', HLDG: 'HOLDINGS', HOLDING: 'HOLDINGS',
  GRP: 'GROUP', INDS: 'INDUSTRIES', IND: 'INDUSTRIES', INDUSTRIE: 'INDUSTRIES',
  COMMUNICATIONS: 'COMMUNICATION', SYS: 'SYSTEMS', SYSTEM: 'SYSTEMS',
  LABS: 'LABORATORIES', LAB: 'LABORATORIES', LABORATORY: 'LABORATORIES',
  MTRS: 'MOTORS', MTR: 'MOTORS', PPTYS: 'PROPERTIES', PPTY: 'PROPERTIES',
  ENTERPRISE: 'ENTERPRISES', BIOSCIENCE: 'BIOSCIENCES', ELECTRIC: 'ELECTRICAL',
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
]);

function tokens(name) {
  return String(name || '')
    .toUpperCase()
    .replace(/[^A-Z0-9 ]+/g, ' ')
    .split(/\s+/)
    .map((w) => ABBREVIATIONS.get(w) || w)
    .filter((w) => w && !NOISE.has(w));
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
  return short.every((word, i) => word === long[i]);
}
