/**
 * What a fund says about a position it holds.
 *
 * The 13F says what a manager owns. Its own report says what it thinks. This
 * joins the two: a claim is linked to a holding when the filer's sentence
 * names that holding, so "what is Berkshire saying about Kraft Heinz" is a
 * lookup rather than a reading exercise.
 *
 * The vocabulary is the manager's own holdings, not a list written here. That
 * matters for the same reason the metric list is closed: a name nobody filed
 * is indistinguishable from one they did, once it is a column.
 *
 * Measured against Berkshire's 2025 report before it was built, because the
 * result decides whether the feature is worth having:
 *
 *   Kraft Heinz     22 sentences   "Our investment in Kraft Heinz has been
 *                                   disappointing."
 *   Occidental      27 sentences
 *   Apple            2 sentences   both enumerations
 *   Coca-Cola        2 sentences   both enumerations
 *   Moody's          1 sentence    an enumeration
 *   ITOCHU           0 sentences
 *
 * That split is an accounting boundary, not a gap in the extractor. An equity
 * method investee or a consolidated business gets discussed in prose because
 * the notes require it; a fair-value equity holding appears in a table and
 * nowhere else. So this layer is rich for a handful of positions and empty for
 * most, and the empty ones must render as absent rather than as "no comment" -
 * Berkshire did not decline to discuss Apple, it disclosed Apple in a table.
 *
 * The hardest case found while measuring, and the reason nothing here is
 * auto-approved:
 *
 *   "Other manufacturing companies such as Kyocera, Mitsubishi, Sumitomo,
 *    Ceratizit, OSG, Guhring, Mapal and YG-1 also play a significant role in
 *    the cutting tools market"
 *
 * Mitsubishi Corporation and Sumitomo Corporation are both holdings. This
 * sentence is about IMC's competitors in cutting tools and has nothing to do
 * with either trading house. Only world knowledge separates them, so a
 * single-word match is reported as the weaker kind and a person decides.
 */

/** Words that carry no identity, so they cannot distinguish one filer from another. */
const SUFFIX = new Set([
  'inc', 'inc.', 'corp', 'corp.', 'corporation', 'company', 'co', 'co.', 'cos',
  'ltd', 'ltd.', 'limited', 'plc', 'lp', 'llc', 'llp', 'nv', 'sa', 'ag', 'kk',
  'holdings', 'holding', 'group', 'groups', 'the', 'and', 'of', 'class',
  'common', 'stock', 'shares', 'ordinary', 'new', 'del', 'cl',
]);

/**
 * Words that never identify a company on their own.
 *
 * Only consulted when a single word is all there is to match on. "Bank of
 * America" is matched in full wherever the filer writes it in full; what this
 * prevents is every sentence containing the word "bank" being filed against
 * that holding.
 */
const GENERIC = new Set([
  'bank', 'banks', 'america', 'american', 'general', 'national', 'first',
  'united', 'states', 'southern', 'northern', 'western', 'eastern', 'central',
  'capital', 'financial', 'finance', 'energy', 'technologies', 'technology',
  'systems', 'international', 'industries', 'industrial', 'resources',
  'communications', 'properties', 'partners', 'global', 'pacific', 'atlantic',
  'standard', 'premier', 'service', 'services', 'products', 'brands', 'motors',
  'stores', 'foods', 'health', 'healthcare', 'pharmaceuticals', 'materials',
  'mining', 'petroleum', 'chemical', 'chemicals', 'airlines', 'express',
  'electric', 'power', 'water', 'media', 'digital', 'data', 'trust', 'fund',
]);

const normalise = (value) => String(value || '')
  .toLowerCase()
  .replace(/[‘’]/g, "'")
  .replace(/[^a-z0-9'&. -]/g, ' ')
  .replace(/\s+/g, ' ')
  .trim();

/**
 * The words in a name that identify the company.
 *
 * A token under four characters is dropped: "BP" and "3M" would need their own
 * handling and matching them loosely puts every sentence containing "bp" on
 * the holding.
 */
export function identityTokens(name) {
  return normalise(name)
    .split(' ')
    .map((word) => word.replace(/[.,]+$/, ''))
    .filter((word) => word.length >= 4 && !SUFFIX.has(word) && !/^\d+$/.test(word));
}

/**
 * Matchable entries for the issuers a manager holds.
 *
 * The manager's own name is excluded, or every sentence in the document would
 * be filed against a holding in the manager itself.
 */
export function heldIssuerVocabulary(names, { exclude = [] } = {}) {
  const excluded = new Set(exclude.flatMap((name) => identityTokens(name)));
  const entries = new Map();
  for (const name of names || []) {
    const tokens = identityTokens(name).filter((token) => !excluded.has(token));
    if (!tokens.length) continue;
    const key = tokens.join(' ');
    // The same company filed under two spellings is one entry. Keeping the
    // shortest name means the label reads as a company rather than as a
    // registrar's string.
    const existing = entries.get(key);
    if (!existing || String(name).length < String(existing.issuer).length) {
      entries.set(key, { issuer: name, tokens });
    }
  }
  return [...entries.values()];
}

const says = (text, token) => new RegExp(`\\b${token.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')}\\b`, 'i').test(text);

/**
 * Every held issuer a sentence names.
 *
 * All of them, not the best one. "The five largest holdings at each date were
 * American Express Company, Apple Inc., Bank of America Corporation and The
 * Coca-Cola Company" names four holdings, and someone asking what the fund
 * said about Apple should find it. Returning a single best match filed that
 * sentence under whichever name happened to score highest and hid it from the
 * other three.
 *
 * Each issuer appears once, at its strongest match.
 */
export function heldIssuersIn(sentence, vocabulary) {
  const text = normalise(sentence);
  if (!text) return [];
  const found = new Map();
  for (const entry of vocabulary || []) {
    const [lead] = entry.tokens;
    // The identifying word has to be there at all. Nothing else is considered
    // without it, so a sentence about Heinz ketchup is not evidence about a
    // holding called Kraft Heinz.
    if (!says(text, lead)) continue;
    const whole = entry.tokens.every((token) => says(text, token));
    // Graded, not binary. Requiring every word lost Occidental entirely: the
    // registrant name is "OCCIDENTAL PETROLEUM CORP" and the filer writes
    // "our investment in Occidental", which is 27 sentences of real
    // commentary. A lead word alone is weaker evidence and says so.
    const strength = whole && entry.tokens.length > 1 ? 'name'
      : lead.length >= 5 && !GENERIC.has(lead) ? 'word'
        : null;
    if (!strength) continue;
    const existing = found.get(entry.issuer);
    if (!existing || (existing.match === 'word' && strength === 'name')) {
      found.set(entry.issuer, { issuer: entry.issuer, match: strength });
    }
  }
  return [...found.values()];
}

/** The strongest held issuer a sentence names, or null. */
export function heldIssuerIn(sentence, vocabulary) {
  const found = heldIssuersIn(sentence, vocabulary);
  if (!found.length) return null;
  return found.find((entry) => entry.match === 'name') || found[0];
}

/** Sentences that list companies rather than say anything about them. */
const ENUMERATION = /\b(?:such as|including|as well as|and other|among them)\b/i;

/**
 * Claims about the positions a manager holds, by position.
 *
 * An enumeration is kept but flagged. "A large portion of our portfolio is
 * concentrated in a small number of American companies such as Apple,
 * American Express, Coca-Cola, and Moody's" is a real statement about
 * concentration and a poor statement about Apple, and a reviewer shown the
 * sentence can see which.
 */
export function claimsByHolding(claims, vocabulary) {
  const byIssuer = new Map();
  for (const claim of claims || []) {
    for (const found of heldIssuersIn(claim.source_excerpt, vocabulary)) {
      if (!byIssuer.has(found.issuer)) byIssuer.set(found.issuer, { issuer: found.issuer, claims: [] });
      byIssuer.get(found.issuer).claims.push({
        ...claim,
        issuer: found.issuer,
        issuer_match: found.match,
        // A list of names is not commentary on each name in it.
        enumeration: ENUMERATION.test(claim.source_excerpt),
      });
    }
  }
  return [...byIssuer.values()]
    .map((entry) => ({
      ...entry,
      // Most-discussed first: the number of things a filer says about a
      // position is itself the signal about which positions it is thinking
      // about.
      commentary: entry.claims.filter((claim) => !claim.enumeration).length,
    }))
    .sort((a, b) => b.commentary - a.commentary || b.claims.length - a.claims.length);
}

/** Claims grouped by the step of the chain they answer, in chain order. */
export function claimsByStep(claims, order) {
  const position = new Map((order || []).map((slot, index) => [slot, index]));
  const bySlot = new Map();
  for (const claim of claims || []) {
    if (!bySlot.has(claim.slot)) bySlot.set(claim.slot, []);
    bySlot.get(claim.slot).push(claim);
  }
  return [...bySlot.entries()]
    .map(([slot, rows]) => ({ slot, claims: rows }))
    .sort((a, b) => (position.get(a.slot) ?? 99) - (position.get(b.slot) ?? 99));
}

/**
 * Whether a pasted document ever names the manager it is being filed under.
 *
 * The manager is given on the command line and the document is pasted, and
 * nothing connected the two. Norges Bank's annual report was pasted into a
 * command that said `--manager berkshire-hathaway`, and 177 of Norges Bank's
 * sentences were stored as things Berkshire said - under a new publication,
 * because the digest differed, so the mistake was additive and silent rather
 * than destructive.
 *
 * A filer names itself. Berkshire's report says "Berkshire" on almost every
 * page; Norges Bank's says it never. That is a weak signal by design: it
 * cannot tell a Berkshire annual report from a Berkshire quarterly, and it is
 * not trying to. It catches the whole document being the wrong document.
 *
 * Returns the count rather than a verdict, so a caller decides what to do
 * with zero. A letter that genuinely never names its author exists, which is
 * why this refuses rather than being impossible to override.
 */
export function managerMentions(text, managerName) {
  const tokens = identityTokens(managerName);
  if (!tokens.length) return { checked: false, mentions: 0, token: null };
  // The most distinctive word, which for "Berkshire Hathaway Inc" is
  // "berkshire" and for "Norges Bank Investment Management" is "norges" -
  // "bank", "investment" and "management" being words any fund's report uses.
  const token = tokens.find((word) => !GENERIC.has(word)) || tokens[0];
  const matches = normalise(text).match(new RegExp(`\\b${token}\\b`, 'g'));
  return { checked: true, mentions: matches ? matches.length : 0, token };
}
