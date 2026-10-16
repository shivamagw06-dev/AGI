/**
 * Deciding what to ask the vendor about, and what needs no asking at all.
 *
 * Enrichment offered every unmapped identifier to OpenFIGI and took silence as
 * evidence of nothing. Silence turned out to mean three different things, and
 * the SEC's own list of 13(f) securities tells them apart.
 *
 * Measured against the loaded list, the identifiers with no ticker were:
 *
 *   8,735  equity          140,072 rows, $610bn - real, and worth asking about
 *   3,394  other            41,474 rows, $101bn - mostly funds; also worth asking
 *     563  debt              6,530 rows, $114bn - convertible notes
 *   1,015  derivative        4,965 rows          - warrants, rights, SPAC units
 *      52  preferred           900 rows, $10.9bn
 *       1  not on the list      16 rows
 *
 * The middle three are 1,630 securities that consumed a vendor call on every
 * run and could never produce a ticker, because a convertible note does not
 * have one. They are now not asked about.
 *
 * That one identifier absent from the list is worth noting for what it says
 * about coverage: of the 13,760 distinct identifiers our holdings carry without
 * a ticker, the SEC's list knows all but one.
 */

/**
 * Classes that cannot resolve to a common-equity ticker, ever.
 *
 * "other" is deliberately absent. For funds the SEC's description field carries
 * the fund's name rather than a class code - "CORE S&P500 ETF", "RUSSELL 2000
 * ETF" - so a fifth of the list lands there, including securities that trade
 * under a ticker like any share. Treating unclassified as excluded would drop
 * 3,394 securities and $101bn of holdings on the strength of a truncated
 * string.
 */
export const UNRESOLVABLE_CLASSES = new Set(['debt', 'preferred', 'option', 'derivative']);

/**
 * Split candidates into those worth a vendor call and those that are not.
 *
 * An identifier the list does not classify is kept. Absence of evidence about
 * what something is has already been mistaken for evidence that it is nothing
 * once in this codebase, and the cost was 147 blue chips reported as private
 * placements.
 */
export function partitionByClass(candidates, classByCusip) {
  const askable = [];
  const excluded = [];
  for (const candidate of candidates || []) {
    const klass = classByCusip?.get?.(candidate?.cusip);
    if (klass && UNRESOLVABLE_CLASSES.has(klass)) excluded.push({ ...candidate, security_class: klass });
    else askable.push(candidate);
  }
  return { askable, excluded };
}

/**
 * Carry a resolved ticker across the identifiers that are the same security.
 *
 * This is what the chains are for. Aptiv's holdings sit under G6095L109 for
 * seven years and under G3265R107 since; the vendor knows only the second. A
 * ticker found on either belongs to both, and 1,872 unmapped identifiers have a
 * sibling that already carries one - resolvable with no vendor call at all.
 *
 * `validFrom` comes from the sibling's own earliest observation rather than
 * from the resolved identifier's, because a mapping may only claim the window
 * its evidence covers. Applying G3265R107's 2024 start date to seven years of
 * G6095L109 holdings would relabel filings the mapping says nothing about,
 * which is the error the valid_from work exists to prevent.
 */
export function expandThroughChains(mappings, { keyByCusip, cusipsByKey, observedFrom }) {
  const already = new Set((mappings || []).map((m) => m.cusip));
  const extra = [];
  for (const mapping of mappings || []) {
    const key = keyByCusip?.get?.(mapping.cusip);
    if (!key) continue;
    for (const sibling of cusipsByKey?.get?.(key) || []) {
      if (sibling === mapping.cusip || already.has(sibling)) continue;
      const from = observedFrom?.get?.(sibling);
      // No observation means no interval the mapping is entitled to claim.
      if (!from) continue;
      already.add(sibling);
      extra.push({
        ...mapping,
        cusip: sibling,
        valid_from: from,
        // Recorded so a ticket that arrived this way can be told from one the
        // vendor answered directly, and traced back to the identifier it came
        // from if it turns out to be wrong.
        source: `chain:${mapping.cusip}`,
      });
    }
  }
  return extra;
}

/**
 * Read the class of each identifier from the loaded list.
 *
 * Chunked because the identifier list is passed as a filter and a URL has a
 * length limit; a single `in` of several thousand identifiers fails as a
 * malformed request rather than as a query that returns nothing, which is at
 * least loud, but it fails.
 */
export async function readClasses(client, cusips, chunk = 200) {
  const out = new Map();
  const list = [...new Set(cusips || [])].filter(Boolean);
  for (let i = 0; i < list.length; i += chunk) {
    const { data, error } = await client
      .from('sec_13f_securities')
      .select('cusip,security_class')
      .in('cusip', list.slice(i, i + chunk));
    if (error) throw new Error(`sec_13f_securities: ${error.message}`);
    for (const row of data || []) out.set(row.cusip, row.security_class);
  }
  return out;
}

/** Read the identity chains covering these identifiers, and their siblings. */
export async function readChains(client, cusips, chunk = 200) {
  const keyByCusip = new Map();
  const list = [...new Set(cusips || [])].filter(Boolean);
  for (let i = 0; i < list.length; i += chunk) {
    const { data, error } = await client
      .from('sec_13f_identity_chain')
      .select('cusip,security_key')
      .in('cusip', list.slice(i, i + chunk));
    if (error) throw new Error(`sec_13f_identity_chain: ${error.message}`);
    for (const row of data || []) keyByCusip.set(row.cusip, row.security_key);
  }

  // Then every identifier sharing those keys, which is where the siblings are.
  const cusipsByKey = new Map();
  const keys = [...new Set(keyByCusip.values())];
  for (let i = 0; i < keys.length; i += chunk) {
    const { data, error } = await client
      .from('sec_13f_identity_chain')
      .select('cusip,security_key')
      .in('security_key', keys.slice(i, i + chunk));
    if (error) throw new Error(`sec_13f_identity_chain siblings: ${error.message}`);
    for (const row of data || []) {
      if (!cusipsByKey.has(row.security_key)) cusipsByKey.set(row.security_key, []);
      cusipsByKey.get(row.security_key).push(row.cusip);
      keyByCusip.set(row.cusip, row.security_key);
    }
  }
  return { keyByCusip, cusipsByKey };
}
