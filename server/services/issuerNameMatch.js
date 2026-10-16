/**
 * Find a security's issuer by name, when nothing else can.
 *
 * The last resort, and the only tier here that could invent an answer, so it
 * is built to refuse rather than to reach. It runs only after the SEC's ticker
 * files, the historical registry and the CUSIP issuer have all failed - which
 * leaves the securities filed with a real CUSIP, no ticker, and no other issue
 * of the same issuer to borrow from: Chart Industries, Nuvalent, Catalyst
 * Pharmaceuticals, Sealed Air.
 *
 * The tokeniser is the venue-ticker recovery's, so filer abbreviations are
 * understood the same way in both places. The comparison is not: see
 * `sameCompanyStrict` below for why a rule that is right with a symbol to
 * corroborate is dangerous without one.
 *
 * Two matches are a refusal, not a coin toss. So is none.
 *
 * `sameCompany` always compares the first word of each name, so the directory
 * is bucketed by it: without that this would be eight thousand securities
 * against thirty-nine thousand entries, and every bucket miss is a comparison
 * that could never have matched.
 */
import { tokens } from './venueTicker.js';

/**
 * The same company, judged on the name alone.
 *
 * Stricter than venueTicker's `sameCompany`, deliberately. That one accepts
 * the shorter name as a prefix of the longer, because one company is often
 * described at two lengths - FERGUSON against FERGUSON ENTERPRISES - and it
 * is only ever asked about candidates a symbol has already narrowed to a
 * handful.
 *
 * Here there is no symbol. The question is asked against thirty-nine thousand
 * companies, and under the prefix rule "Apple Inc." tokenises to the single
 * word APPLE, so Apple Hospitality REIT - a different company, in a different
 * sector - matches it. Verified: sameCompany('APPLE HOSPITALITY REIT INC',
 * 'Apple Inc.') is true.
 *
 * So every word must be present on both sides. That also refuses FERGUSON
 * against FERGUSON ENTERPRISES, which is a real match lost - and the right
 * trade when the alternative is attributing a position to the wrong company
 * silently and plausibly.
 */
function sameCompanyStrict(a, b) {
  const x = tokens(a);
  const y = tokens(b);
  if (!x.length || x.length !== y.length) return false;
  return x.every((word, index) => {
    for (const form of word) if (y[index].has(form)) return true;
    return false;
  });
}

/** The forms the first significant word of a name could take. */
function firstWordForms(name) {
  const [first] = tokens(name);
  return first ? [...first] : [];
}

/**
 * Bucket directory entries by the forms of their first significant word.
 *
 * @param {Iterable<[string, {title?: string|null}]>} entries ticker to record
 */
export function nameIndex(entries) {
  const index = new Map();
  for (const [ticker, record] of entries || []) {
    // No guard on a missing title: it tokenises to nothing, so it buckets
    // under nothing and cannot be reached.
    for (const form of firstWordForms(record?.title)) {
      if (!index.has(form)) index.set(form, []);
      index.get(form).push({ ticker, ...record });
    }
  }
  return index;
}

/**
 * The single directory entry whose name is this issuer, or null.
 *
 * Null covers both "nothing matched" and "more than one did". The caller
 * cannot act on either, and collapsing them keeps the refusal from looking
 * like a near miss worth overriding.
 */
export function matchByName(issuerName, index) {
  const forms = firstWordForms(issuerName);
  const seen = new Map();
  for (const form of forms) {
    for (const candidate of index?.get(form) || []) {
      if (!sameCompanyStrict(issuerName, candidate.title)) continue;
      // Keyed on CIK: one company reached through two of its own tickers, or
      // through two spellings of one word, is one match rather than two.
      // Keyed on CIK: one company reached through two of its own tickers, or
      // through two spellings of one word, is one match rather than two.
      seen.set(candidate.cik, candidate);
    }
  }
  // One place decides, so there is no second rule to disagree with it: a
  // single company is a match and anything else - none, or several - is not.
  return seen.size === 1 ? [...seen.values()][0] : null;
}
