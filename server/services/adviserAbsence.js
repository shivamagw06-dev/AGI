/**
 * Why a tracked manager has no Form ADV.
 *
 * Seventeen of fifty-one managers matched no adviser registration, and the
 * page said the same thing about all of them: "No SEC investment-adviser
 * registration on record." For Baker Bros that is a fact about our matching.
 * For Berkshire Hathaway it is a fact about Berkshire - an operating company
 * that files 13F on its own balance sheet has no Form ADV to find, and never
 * will. Rendering both as the same blank makes the first look fine and the
 * second look broken.
 *
 * What is actually measured here is narrow and worth stating plainly: the
 * SEC's adviser search returned no exact legal-name match. Every entry below
 * pairs that with the reason there is nothing to match, and the reasons are
 * ours - a reading of what kind of entity this is, not something the SEC
 * publishes as a field.
 *
 * The keys are slugs, read from institutional_managers on 2026-09-11 rather
 * than derived from display names - the two do not track each other, and
 * "NVIDIA Corp" is `nvidia` while "Appaloosa" is `appaloosa-management`. A key
 * that matches no manager explains nothing and says nothing about it, so
 * `unmatchedAbsenceSlugs` reports the drift rather than leaving it silent.
 *
 * So the entries are kept honest in two ways. The `basis` records what the
 * search returned, because "zero results" and "twenty-one near misses" are
 * different situations and only the first supports "there is nothing to
 * find". And a manager not listed here gets no explanation rather than a
 * guessed one - the generic line is the right answer when we do not know.
 */

/** Categories, with the sentence each puts on the card. */
export const ABSENCE_KINDS = {
  operating_company:
    'An operating company. It files 13F on its own corporate holdings rather than '
    + 'managing money for clients, so there is no Form ADV to file.',
  family_office:
    'A private investment office. Family offices have been exempt from adviser '
    + 'registration since the exemption took effect in 2011.',
  sovereign_fund:
    'A sovereign or national fund. It is not a US-registered investment adviser, '
    + 'so it files 13F without filing Form ADV.',
  charitable_trust:
    'A charitable trust holding its own endowment rather than managing client '
    + 'money, so no adviser registration applies.',
};

/**
 * Keyed on slug, with the search result that supports it.
 *
 * `basis: 'no_results'` means the SEC adviser search returned nothing at all
 * for this name - the strongest evidence available that there is no
 * registration. `basis: 'near_misses'` means it returned firms that were not
 * this one, which supports the category but not as firmly.
 */
export const ADVISER_ABSENCE = {
  // Files a 10-K. The 13F covers the insurance float's equity book.
  'berkshire-hathaway': { kind: 'operating_company', basis: 'no_results' },
  nvidia: { kind: 'operating_company', basis: 'no_results' },
  // One unrelated firm matched the name "Alphabet"; none was this one.
  alphabet: { kind: 'operating_company', basis: 'near_misses' },

  // Druckenmiller returned outside capital and converted in 2010.
  'duquesne-family-office': { kind: 'family_office', basis: 'no_results' },
  // Soros returned outside capital and deregistered in 2011.
  'soros-fund-management': { kind: 'family_office', basis: 'no_results' },
  'thiel-macro': { kind: 'family_office', basis: 'no_results' },

  // Norway's central bank, through Norges Bank Investment Management.
  'norges-bank': { kind: 'sovereign_fund', basis: 'no_results' },
  // South Korea's national pension scheme.
  'national-pension-service': { kind: 'sovereign_fund', basis: 'no_results' },

  'gates-foundation-trust': { kind: 'charitable_trust', basis: 'no_results' },
};

/**
 * The explanation for one manager, or null when there is none to give.
 *
 * Null is the common and correct answer. Baker Bros, Himalaya, Jane Street,
 * Baillie Gifford and Dalal Street all register somewhere - under a name our
 * matcher does not reach - and inventing a category for them would state the
 * opposite of the truth.
 */
export function adviserAbsence(slug) {
  const entry = ADVISER_ABSENCE[String(slug || '').trim()];
  if (!entry) return null;
  const explanation = ABSENCE_KINDS[entry.kind];
  if (!explanation) return null;
  return {
    kind: entry.kind,
    explanation,
    // Said on the card, because the difference matters to anyone checking.
    basis: entry.basis === 'no_results'
      ? 'The SEC adviser registry returns no firm under this name.'
      : 'The SEC adviser registry returns other firms under this name, none of them this one.',
  };
}

/**
 * Keys here that match no tracked manager.
 *
 * A slug that drifts - a manager renamed, or a key mistyped - removes the
 * explanation from the card and reports nothing, which is the one failure this
 * file cannot detect from the inside. The caller has the manager list, so it
 * can.
 */
export function unmatchedAbsenceSlugs(managers = []) {
  const known = new Set((managers || []).map((row) => String(row?.slug || '').trim()));
  return Object.keys(ADVISER_ABSENCE).filter((slug) => !known.has(slug));
}
