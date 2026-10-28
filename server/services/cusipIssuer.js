/**
 * The issuer behind a CUSIP, and the sector that follows from it.
 *
 * About eight thousand securities in the book arrive with no ticker, carrying
 * $386bn. Nothing keyed on a symbol can name them. But a CUSIP is not opaque:
 * six characters of issuer, two of issue, one check digit - so a security with
 * no ticker still says who issued it, and a sector is a property of the issuer
 * rather than of the issue.
 *
 * Most of that value turns out not to be unknown companies at all. Filers
 * synthesise identifiers for option positions by replacing the issue digits,
 * and the check digit gives them away:
 *
 *   037833100  valid    Apple common stock
 *   037833950  invalid  a filer's identifier for an option on it
 *   67066G104  valid    Nvidia
 *   67066G904  invalid  an option on Nvidia
 *
 * Both share the issuer. An option on Apple is exposure to Apple, and putting
 * it in Information Technology is the answer a sector chart should give.
 *
 * The inference refuses whenever the issuer's own securities disagree. If
 * every classified issue under a prefix reads Information Technology then the
 * unclassified one does too; if two of them disagree, nothing is written -
 * one issuer with two sectors means the assumption behind this whole idea does
 * not hold for that issuer, and guessing would be inventing.
 *
 * The CUSIP itself is never published. It is read from data already held,
 * grouped, and thrown away; what reaches the page is a sector.
 */

/** The six-character issuer, or null if there is not one to read. */
export function issuerPrefix(cusip) {
  const value = String(cusip ?? '').trim().toUpperCase();
  // Nine is the only length a CUSIP has. A shorter string is a fragment and a
  // longer one is something else, and either would collide with real issuers
  // if truncated to six.
  if (value.length !== 9) return null;
  if (!/^[0-9A-Z*@#]{9}$/.test(value)) return null;
  return value.slice(0, 6);
}

const ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ*@#';

/**
 * Whether the check digit is the one the first eight characters imply.
 *
 * Not used to decide anything - a synthesised identifier is classified the
 * same way a real one is, through its issuer. It is reported, so the size of
 * the derivative population is visible rather than inferred.
 */
export function checkDigitValid(cusip) {
  const value = String(cusip ?? '').trim().toUpperCase();
  if (value.length !== 9) return false;
  let total = 0;
  for (let index = 0; index < 8; index += 1) {
    const position = ALPHABET.indexOf(value[index]);
    if (position < 0) return false;
    const doubled = index % 2 === 1 ? position * 2 : position;
    total += Math.floor(doubled / 10) + (doubled % 10);
  }
  return String((10 - (total % 10)) % 10) === value[8];
}

/**
 * Issuer prefix to sector, for issuers whose classified securities agree.
 *
 * Unclassified rows are not evidence and are ignored; an issuer known only
 * through them stays unknown rather than becoming Unclassified by a second
 * route.
 */
export function sectorByIssuer(classifications) {
  const sectors = new Map();
  for (const row of classifications || []) {
    const prefix = issuerPrefix(row?.cusip || row?.security_key);
    if (!prefix) continue;
    const sector = String(row?.sector || '').trim();
    if (!sector || sector === 'Unclassified') continue;
    if (!sectors.has(prefix)) sectors.set(prefix, new Set());
    sectors.get(prefix).add(sector);
  }

  const resolved = new Map();
  sectors.forEach((set, prefix) => { if (set.size === 1) resolved.set(prefix, [...set][0]); });
  return resolved;
}

/** The sector implied by a CUSIP's issuer, or null where nothing is implied. */
export function sectorFromIssuer(cusip, byIssuer) {
  const prefix = issuerPrefix(cusip);
  if (!prefix) return null;
  return byIssuer?.get(prefix) || null;
}
