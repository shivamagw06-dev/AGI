/**
 * Carrying tickers across the identifiers that are the same security.
 *
 * The enrichment path expands a chain only from the mappings it resolved on
 * that run. That covers a security whose ticker is found today, and misses
 * every one whose ticker was found already: 1,872 unmapped identifiers have a
 * sibling that carries a ticker right now, and nothing goes looking for them.
 * They are not waiting on a vendor - the answer was bought long ago, under a
 * different number.
 *
 * Aptiv is the shape of it. Seven years of holdings sit under G6095L109 and the
 * vendor has never heard of it; G3265R107 resolved on the first ask. One
 * security, one ticker, two identifiers, and no lookup required to join them.
 */

/**
 * Work out which unmapped identifiers can take a ticker from a sibling.
 *
 * `known` maps an identifier to the ticker already established for it.
 * `keyByCusip` and `cusipsByKey` describe the chains. `observedFrom` is the
 * earliest date each unmapped identifier appears in our own holdings.
 *
 * A proposal is only made when the sibling's ticker is unambiguous. Where two
 * identifiers in one chain carry different tickers the chain is left alone:
 * that is a chain built wrong, and guessing which half is right would put one
 * company's ticker on another company's holdings - the failure this whole
 * exercise exists to avoid.
 */
export function proposeFromChains(unmapped, { known, keyByCusip, cusipsByKey, observedFrom }) {
  const proposals = [];
  const conflicts = [];

  for (const cusip of unmapped || []) {
    if (known?.has?.(cusip)) continue;
    const key = keyByCusip?.get?.(cusip);
    if (!key) continue;

    const tickers = new Set();
    let from = null;
    for (const sibling of cusipsByKey?.get?.(key) || []) {
      if (sibling === cusip) continue;
      const ticker = known?.get?.(sibling);
      if (ticker) {
        tickers.add(ticker);
        if (!from) from = sibling;
      }
    }
    if (!tickers.size) continue;
    if (tickers.size > 1) {
      conflicts.push({ cusip, security_key: key, tickers: [...tickers] });
      continue;
    }

    const observed = observedFrom?.get?.(cusip);
    // An identifier we have never seen in a filing has no interval a mapping
    // is entitled to claim, so there is nothing to write.
    if (!observed) continue;

    proposals.push({
      cusip,
      ticker: [...tickers][0],
      // Anchored to this identifier's own earliest observation, not to the
      // sibling's. A mapping may only claim the window its evidence covers;
      // taking the sibling's start date would relabel filings it never saw.
      valid_from: observed,
      valid_to: null,
      security_key: key,
      // Told apart from a vendor answer, and traceable to the identifier it
      // came from if the chain turns out to be wrong.
      source: `chain:${from}`,
      manually_verified: false,
    });
  }

  return { proposals, conflicts };
}
