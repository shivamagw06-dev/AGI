/**
 * Which numbering scheme an identifier belongs to, and whether it is one at all.
 *
 * The enrichment asked OpenFIGI `idType: 'ID_CUSIP'` for every identifier it
 * had. That is correct for a US security and wrong for everything else, and the
 * cost of being wrong was not a warning - it was "No identifier found", which
 * is indistinguishable from a security the vendor has never heard of.
 *
 * So 147 of the largest unmapped securities looked like private placements and
 * were reported as such. They were Chubb, Linde, Accenture, Spotify, ASML,
 * Medtronic, UBS, Eaton, NXP, Aon, CRH, Ferrari and Royal Caribbean - around
 * three trillion dollars of cumulative disclosed value, sitting behind a
 * message that said they probably had no listing. Verified against the vendor:
 *
 *   ID_CUSIP  G54950103 -> No identifier found.
 *   ID_CINS   G54950103 -> LIN  (US, Common Stock)
 *   ID_CUSIP  L8681T102 -> No identifier found.
 *   ID_CINS   L8681T102 -> SPOT (US, Common Stock)
 *
 * Two schemes share the nine-character shape and one leading character tells
 * them apart. A CINS - CUSIP International Numbering System - begins with a
 * letter standing for the issuer's country or region; a domestic CUSIP begins
 * with a digit. That is the whole rule, and it is worth stating in one place
 * because getting it wrong is silent.
 *
 * The check digit is validated here too, for a different reason. Some lines in
 * these filings carry identifiers whose ninth character does not compute - the
 * 90-series and 95-series issue numbers that appear on option lines, such as
 * 037833900 against Apple's 037833100. The vendor rejects those as "Invalid
 * idValue format", and asking it again next week will not change that. Knowing
 * an identifier is malformed before spending a request on it is the difference
 * between a permanent answer and a permanent retry.
 */

/** Character values for the CUSIP check digit: 0-9, then A=10 through Z=35. */
function charValue(ch) {
  if (ch >= '0' && ch <= '9') return ch.charCodeAt(0) - 48;
  if (ch >= 'A' && ch <= 'Z') return ch.charCodeAt(0) - 55;
  if (ch === '*') return 36;
  if (ch === '@') return 37;
  if (ch === '#') return 38;
  return null;
}

/**
 * The check digit an identifier's first eight characters imply.
 *
 * Modulus 10 double-add-double, which is the same computation for a CUSIP and
 * a CINS - the leading letter is just another character with a value.
 * Returns null when the body contains something that is not a legal character,
 * because then there is no digit to compare against.
 */
export function checkDigit(body) {
  const chars = String(body || '').toUpperCase().slice(0, 8);
  if (chars.length !== 8) return null;
  let sum = 0;
  for (let i = 0; i < 8; i += 1) {
    let value = charValue(chars[i]);
    if (value === null) return null;
    // Every second character counts double, starting from the second.
    if (i % 2 === 1) value *= 2;
    sum += Math.floor(value / 10) + (value % 10);
  }
  return (10 - (sum % 10)) % 10;
}

/**
 * Classify an identifier.
 *
 * Returns the OpenFIGI idType to ask with, or null when there is no point
 * asking. `valid` is separate from `idType` so a caller can tell "I know what
 * this is and it is malformed" from "I do not recognise this shape at all".
 */
export function classifyIdentifier(value) {
  const id = String(value || '').trim().toUpperCase();
  if (!/^[0-9A-Z*@#]{9}$/.test(id)) {
    return { identifier: id, scheme: 'unknown', idType: null, valid: false, reason: 'not a nine-character identifier' };
  }
  // A leading letter means CINS: the character encodes the issuer's country
  // or region. A leading digit means a domestic CUSIP.
  const scheme = /^[A-Z]/.test(id) ? 'cins' : 'cusip';
  const expected = checkDigit(id.slice(0, 8));
  const actual = charValue(id[8]);
  if (expected === null || actual === null || expected !== actual) {
    return {
      identifier: id,
      scheme,
      idType: null,
      valid: false,
      // Named for what it is rather than for what it usually means. These are
      // overwhelmingly option lines, but the check digit proves malformation,
      // not purpose, and the report should not claim more than it knows.
      reason: `check digit ${id[8]} does not match computed ${expected === null ? '?' : expected}`,
    };
  }
  return {
    identifier: id,
    scheme,
    idType: scheme === 'cins' ? 'ID_CINS' : 'ID_CUSIP',
    valid: true,
    reason: null,
  };
}

/**
 * Group identifiers by the idType they should be asked with.
 *
 * OpenFIGI accepts a mixed batch - each job carries its own idType - but
 * grouping keeps the caller from having to thread the classification through
 * the request builder, and makes the malformed ones a set the caller must
 * decide about rather than a silent omission.
 */
export function groupByIdType(identifiers) {
  const jobs = [];
  const invalid = [];
  for (const value of identifiers || []) {
    const classified = classifyIdentifier(value);
    if (classified.valid) jobs.push({ idType: classified.idType, idValue: classified.identifier });
    else invalid.push(classified);
  }
  return { jobs, invalid };
}
