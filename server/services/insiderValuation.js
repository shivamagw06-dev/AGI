/**
 * What an insider filing is worth, and which parts of it to believe.
 *
 * Two faults surfaced when 320,000 filings were imported at once. Both were
 * always present; the crawl's fourteen thousand rows were too few to make
 * either visible, and both produced totals that were wrong by orders of
 * magnitude rather than obviously broken.
 *
 * Derivatives were summed alongside shares. In one quarter, 295 derivative
 * purchases and sales carried $103tn between them against 27,936 share
 * transactions worth a median of $168,000. A convertible note recorded at face
 * value is a real transaction and not a comparable one, and "the CEO bought
 * $2m of stock" must mean stock.
 *
 * And filers make mistakes. Thirteen of those 27,936 rows put the total value
 * in the price-per-share field - `shares=15,000,000 price=15,000,000` is
 * $15 million a share - and thirteen rows carried almost the entire $325tn
 * total. The raw numbers are kept exactly as filed; only the aggregate refuses
 * them, and says so.
 */

/**
 * No US equity trades above this.
 *
 * Berkshire Hathaway A is the highest-priced share in the market at roughly
 * seven hundred thousand dollars, so a million is comfortably above anything
 * real and comfortably below the millions-per-share that a mis-keyed total
 * produces. A bound is unavoidable here: nothing in the filing distinguishes a
 * typo from a genuine figure except its size.
 */
export const PLAUSIBLE_PRICE_CEILING = 1_000_000;

/** EDGAR does not hold Section 16 filings older than this. */
export const EARLIEST_PLAUSIBLE_YEAR = 1993;

/**
 * Whether a transaction's value can be believed.
 *
 * A row that fails is still stored and still shown - it is what the filer
 * said. It is only kept out of sums, because one mis-keyed row moves a
 * quarterly total by a factor of a thousand and nothing downstream can tell.
 */
export function credibleValue(row) {
  if (!row || row.derivative) return false;
  const price = Number(row.price_per_share);
  const value = Number(row.value_usd);
  if (!Number.isFinite(value)) return false;
  // A missing price is normal - a grant has none - and such a row has no value
  // to contribute anyway.
  if (!Number.isFinite(price) || price <= 0) return false;
  return price <= PLAUSIBLE_PRICE_CEILING;
}

/**
 * The summary a reader wants, computed once so both collection routes agree.
 *
 * parseFormFour and the bulk importer produce the same parsed_data, and a fund
 * page must not show two different figures for one quarter depending on which
 * ran last. That only holds if the arithmetic lives in one place.
 */
export function summariseTransactions(rows) {
  const list = Array.isArray(rows) ? rows : [];
  const countable = list.filter((row) => row?.discretionary && credibleValue(row));

  return {
    discretionary_buy_value: countable
      .filter((row) => row.direction === 'acquire' || row.direction === 'buy')
      .reduce((sum, row) => sum + Number(row.value_usd || 0), 0),
    discretionary_sell_value: countable
      .filter((row) => row.direction === 'dispose' || row.direction === 'sell')
      .reduce((sum, row) => sum + Number(row.value_usd || 0), 0),
    // Based on the transactions, not on the values: an insider who bought at a
    // price we refuse to believe still made a decision, and the panel should
    // say so rather than reporting no activity.
    has_discretionary: list.some((row) => row?.discretionary && !row?.derivative),
    // Counted so a filing whose totals exclude something says as much.
    excluded_values: list.filter((row) => row?.discretionary && !row?.derivative && !credibleValue(row)
      && Number.isFinite(Number(row?.value_usd))).length,
  };
}

/**
 * An insider filing date, or null.
 *
 * Bounded at both ends. A year-0001 period reached the database from a real
 * filing and became the earliest date in the table, which is how a chart gets
 * an axis two thousand years wide. A date in the future is equally impossible
 * and equally silent.
 */
export function plausibleFilingDate(iso, { asOf = new Date() } = {}) {
  const text = String(iso ?? '').slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return null;
  const year = Number(text.slice(0, 4));
  if (year < EARLIEST_PLAUSIBLE_YEAR) return null;
  // A couple of days of slack, because filings are dated in local time zones
  // and a run near midnight UTC should not reject today.
  const ceiling = new Date(asOf.getTime() + 2 * 86_400_000).toISOString().slice(0, 10);
  if (text > ceiling) return null;
  return text;
}
