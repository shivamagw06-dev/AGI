/**
 * Matching securities to tickers by name, safely.
 *
 * This is the join I refused to make earlier, and the reason it is safe now is
 * worth stating, because the reason it was unsafe has not gone away.
 *
 * Given a 2019 company list, matching our holdings on issuer name produced
 * WESTERN DIGITAL CORP -> WDC, BOEING CO -> BA and WELLS FARGO & CO -> WFC.
 * All three were wrong: those identifiers are a convertible note, a depositary
 * convertible preferred and a perpetual convertible preferred. An issuer's name
 * is identical across its common stock, its preferred, its notes and its
 * options, so a name alone cannot tell them apart, and labelling a bond with
 * the equity's ticker puts debt into equity consensus and sector weights.
 *
 * What changed is that the class is now known from the SEC's own list. Matching
 * only identifiers it calls equity removes the failure entirely - not by being
 * more careful about names, but by never asking the question about a bond.
 *
 * Three further rules keep the rest honest:
 *
 *   a name that maps to more than one ticker is skipped, not guessed at
 *   a ticker already held by a different security is skipped
 *   matching is exact after normalisation, never by edit distance
 *
 * The last one costs coverage. The 13F list truncates issuer names at 28
 * characters and carries typos - "TWO HARBORS INVENTMENT CORPO" is verbatim -
 * so some securities will not match and stay unmapped. A near-miss resolved by
 * similarity is a guess, and the failure mode of a wrong guess is one company's
 * holdings carrying another company's ticker.
 */

/**
 * Index the SEC's ticker file by normalised company name.
 *
 * Names that resolve to more than one ticker are recorded as ambiguous rather
 * than letting the last one win: 1,032 names in the file do this, mostly share
 * classes of one issuer, and silently taking whichever came last would assign a
 * class A ticker to class B holdings.
 */
export function indexTickerFile(entries, normalise) {
  const byName = new Map();
  const ambiguous = new Set();
  for (const entry of Object.values(entries || {})) {
    const ticker = String(entry?.ticker || '').trim().toUpperCase();
    const name = normalise(entry?.title || '');
    if (!ticker || !name) continue;
    if (byName.has(name) && byName.get(name) !== ticker) ambiguous.add(name);
    byName.set(name, ticker);
  }
  for (const name of ambiguous) byName.delete(name);
  return { byName, ambiguous };
}

/**
 * Propose a ticker for each unmapped identifier the SEC list calls equity.
 *
 * `securities` carries the SEC's own issuer name and class per identifier.
 * `takenTickers` maps a ticker to the identifier already using it, so one
 * ticker cannot come to describe two different securities.
 */
export function proposeFromTickerFile(unmapped, {
  securities, byName, ambiguousNames, observedFrom, takenTickers, normalise,
}) {
  const proposals = [];
  const skipped = { notEquity: 0, noName: 0, ambiguousName: 0, tickerTaken: 0, noMatch: 0, noObservation: 0 };

  for (const cusip of unmapped || []) {
    const security = securities?.get?.(cusip);
    // Only equities. This single condition is what makes a name join safe:
    // the bond, the preferred and the option all share the issuer's name and
    // none of them is asked about.
    if (!security || security.security_class !== 'equity') { skipped.notEquity += 1; continue; }

    const name = normalise(security.issuer_name || '');
    if (!name) { skipped.noName += 1; continue; }
    if (ambiguousNames?.has?.(name)) { skipped.ambiguousName += 1; continue; }

    const ticker = byName?.get?.(name);
    if (!ticker) { skipped.noMatch += 1; continue; }

    // One ticker describes one security. If another identifier already carries
    // it, either they are the same security - in which case the chain pass is
    // the right tool and this one should not guess - or they are not, and
    // assigning it twice merges two companies' holdings.
    const holder = takenTickers?.get?.(ticker);
    if (holder && holder !== cusip) { skipped.tickerTaken += 1; continue; }

    const from = observedFrom?.get?.(cusip);
    if (!from) { skipped.noObservation += 1; continue; }

    proposals.push({
      cusip,
      ticker,
      // Only the window this identifier's own filings cover.
      valid_from: from,
      valid_to: null,
      security_key: cusip,
      issuer_name: security.issuer_name || null,
      // Distinguishable from a vendor answer and from a chain inference, so a
      // wrong one can be found and removed by where it came from.
      source: 'sec_ticker_file',
      manually_verified: false,
    });
  }

  return { proposals, skipped };
}
