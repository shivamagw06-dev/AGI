/**
 * Choosing which OpenFIGI line describes a 13F holding.
 *
 * OpenFIGI answers an identifier with every line it knows - one per venue -
 * and this picked the best-scoring of them, with a US listing merely
 * preferred:
 *
 *   (row.exchCode === 'US' ? 20 : 0) + ...
 *
 * When there was no US line, the score simply fell through to a foreign one
 * and its symbol was stored as the security's ticker. That is where HONGBP,
 * LRCXEUR and 8QR came from: 193 tickers over $622bn of holdings, none of
 * which name a US listing, because European venues label their lines by
 * currency and Frankfurt uses short codes of its own.
 *
 * A security reportable on Form 13F trades on a US exchange - that is what
 * makes it a section 13(f) security. So a foreign venue's symbol is never the
 * right answer here, and a wrong ticker is worse than none: the screener and
 * consensus tables key on ticker, so Honeywell's ownership was split between
 * HON and HONGBP, and a short foreign code can collide with a real US symbol
 * and put another company's prices on the position.
 *
 * No US line means we do not know the ticker. Saying so leaves the identifier
 * for the SEC ticker file and the identity chain to resolve, which is what
 * those exist for.
 */

/** Lines that could describe a US-listed equity. */
function eligible(rows) {
  return (rows || []).filter((row) => row?.ticker
    && row?.marketSector === 'Equity'
    // The one hard requirement. Everything below only ranks what is left.
    && row?.exchCode === 'US');
}

/**
 * The best US line for this identifier, or null if there is no US line.
 *
 * Ranking among US lines is unchanged: an ordinary share or depositary
 * receipt beats an unusual instrument, and a composite FIGI beats a
 * venue-specific one because it names the security rather than one listing
 * of it.
 */
export function preferredFigiCandidate(result) {
  const candidates = eligible(result?.data);
  if (!candidates.length) return null;
  const score = (row) => (/Common Stock|Depositary Receipt|REIT|ETP/i.test(row.securityType2 || '') ? 10 : 0)
    + (row.compositeFIGI ? 2 : 0);
  return [...candidates].sort((a, b) => score(b) - score(a))[0];
}

/**
 * Why an identifier produced no ticker, for the operator reading a run.
 *
 * "OpenFIGI knows this security but lists it nowhere in the US" is a
 * different fact from "OpenFIGI has never heard of it", and they need
 * different work: the first wants the SEC ticker file, the second wants a
 * look at whether the identifier is right.
 */
export function noCandidateReason(result) {
  const rows = result?.data || [];
  if (!rows.length) return 'no OpenFIGI listing';
  if (!rows.some((row) => row?.marketSector === 'Equity')) return 'listed, but not as equity';
  return `listed only outside the US (${[...new Set(rows.map((r) => r?.exchCode).filter(Boolean))].slice(0, 4).join(', ')})`;
}
