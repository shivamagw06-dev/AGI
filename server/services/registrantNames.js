/**
 * Match an issuer name against every registrant the SEC has ever assigned a
 * CIK, for securities nothing else can identify.
 *
 * What is left after the ticker files, the historical registry and the CUSIP
 * issuer is mostly not operating companies. It is fund trusts - TIDAL TRUST II,
 * DIREXION SHARES ETF TRUST, FIRST TR EXCHNG TRADED FD VI - which have no
 * ticker because the trust issues dozens of ETFs and the trust is the issuer.
 * Then SPACs, then closed-end funds. Measured on a sample of the real tail,
 * this resolves 34 of 43.
 *
 * It deliberately does not reuse venueTicker's tokeniser. That one drops TRUST,
 * FUND and REIT as filler, which is right for an operating company and exactly
 * wrong here: for TIDAL TRUST II every one of those words is the identity.
 * Measured, dropping them collapsed forty distinct registrants into one
 * ambiguous match. Roman numerals are kept for the same reason - Trust II and
 * Trust III are different registrants.
 *
 * The rule is equality on the normalised words, so the normalised form is a
 * key rather than a comparison. That is what makes it cheap: the SEC's file is
 * a million lines and forty megabytes, and it can be streamed against the few
 * thousand names actually being asked about instead of held in memory.
 *
 * Prefix matching was tried and rejected on evidence. Allowing a holding's name
 * to be a truncation of a registrant's resolved four more names and made eleven
 * ambiguous that had been exact - a net loss - because a 13F name truncated to
 * twenty-eight characters is a prefix of many registrants at once.
 */

/** Words that name a company's form rather than the company. */
const SUFFIX = new Set([
  'INC', 'CORP', 'CORPORATION', 'CO', 'COMPANY', 'LTD', 'LIMITED', 'PLC', 'LLC',
  'LP', 'LLP', 'THE', 'NEW', 'SA', 'NV', 'AG', 'CL', 'CLASS', 'COM', 'ORD', 'SHS', 'ADR', 'ADS',
]);

/**
 * Filer abbreviations, expanded to the SEC's spelling.
 *
 * Every entry here came from a name in the real unresolved tail, not from
 * imagination: the SEC writes TRUST and the filer writes TR, and neither is
 * predictable from the other.
 */
const ABBREVIATIONS = new Map(Object.entries({
  TR: 'TRUST', TRUSTS: 'TRUST', FD: 'FUND', FDS: 'FUND', FUNDS: 'FUND',
  SER: 'SERIES', EXCHNG: 'EXCHANGE', EXCH: 'EXCHANGE', ETFS: 'ETF',
  CAP: 'CAPITAL', INVT: 'INVESTMENT', INVTS: 'INVESTMENT', INVESTMENTS: 'INVESTMENT',
  MGMT: 'MANAGEMENT', INDL: 'INDUSTRIAL', INDS: 'INDUSTRIES', IND: 'INDUSTRIES',
  GBL: 'GLOBAL', INTL: 'INTERNATIONAL', MUN: 'MUNICIPAL', MUNI: 'MUNICIPAL',
  INCM: 'INCOME', PFD: 'PREFERRED', SECS: 'SECURITIES', HLDGS: 'HOLDINGS', HLDG: 'HOLDINGS',
  FINL: 'FINANCIAL', SVCS: 'SERVICES', SVC: 'SERVICES', TECHNOLOGIES: 'TECHNOLOGY',
  GRP: 'GROUP', PHARMACEUTICALS: 'PHARMACEUTICAL', MED: 'MEDICAL', NATL: 'NATIONAL',
  LTS: 'LIGHTS', PPTYS: 'PROPERTIES', PPTY: 'PROPERTIES', RLTY: 'REALTY',
  BANCORPORATION: 'BANCORP', THERAPEUTICS: 'THERAPEUTIC', LABS: 'LABORATORIES',
}));

/**
 * A name reduced to the words that identify the registrant, joined.
 *
 * Empty where nothing survives - a name that is only a corporate suffix
 * identifies nobody, and a blank key would match every other blank.
 */
export function canonicalName(name) {
  return String(name ?? '')
    .toUpperCase()
    // Periods go before anything else, so a dotted abbreviation stays one
    // word. Turning punctuation into spaces first makes "L.L.C." into L, L, C
    // - three tokens, none of them recognised as a corporate form - and
    // COATUE MANAGEMENT, L.L.C. then fails to match COATUE MANAGEMENT. The
    // same for L.P., which is how most funds are constituted, so the names
    // this is least able to match were the ones it most needed to.
    .replace(/\./g, '')
    .replace(/[^A-Z0-9 ]+/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => ABBREVIATIONS.get(word) || word)
    .filter((word) => !SUFFIX.has(word))
    .join(' ');
}

/**
 * Parse one line of the SEC's cik-lookup-data.txt.
 *
 * The format is NAME:CIK: and a name may itself contain colons, so the CIK is
 * taken from the end rather than by splitting.
 */
export function parseRegistrant(line) {
  const trimmed = String(line ?? '').trim();
  const last = trimmed.lastIndexOf(':', trimmed.length - 2);
  if (last <= 0) return null;
  const name = trimmed.slice(0, last);
  const cik = trimmed.slice(last + 1).replace(/:/g, '');
  if (!name || !/^\d{10}$/.test(cik)) return null;
  return { name, cik };
}

/**
 * Resolve wanted names against a stream of registrant lines.
 *
 * @param {Iterable<string>} names the issuer names being asked about
 * @param {Iterable<string>} lines cik-lookup-data.txt, line by line
 * @returns {Map<string, {name: string, cik: string}>} keyed by the original
 *   name; a name matching more than one registrant is absent, because two
 *   matches is a refusal rather than a choice.
 */
export function resolveRegistrants(names, lines) {
  const wanted = new Map();
  for (const name of names || []) {
    const key = canonicalName(name);
    if (!key) continue;
    if (!wanted.has(key)) wanted.set(key, []);
    wanted.get(key).push(name);
  }
  if (!wanted.size) return new Map();

  const found = new Map();
  for (const line of lines || []) {
    const row = parseRegistrant(line);
    if (!row) continue;
    const key = canonicalName(row.name);
    // No separate blank check: a wanted key is never blank - the loop above
    // refuses those - so a registrant that normalises to nothing cannot be
    // wanted, and a guard no test can distinguish is one nobody can trust.
    if (!wanted.has(key)) continue;
    const current = found.get(key);
    // Keyed on CIK: the same registrant listed twice under spellings that
    // normalise alike is one match, not two.
    if (!current) { found.set(key, new Map([[row.cik, row]])); continue; }
    current.set(row.cik, row);
  }

  const out = new Map();
  found.forEach((byCik, key) => {
    if (byCik.size !== 1) return;
    const [match] = [...byCik.values()];
    for (const name of wanted.get(key)) out.set(name, match);
  });
  return out;
}
