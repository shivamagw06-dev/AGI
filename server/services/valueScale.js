/**
 * Whether a 13F information table reports values in whole dollars or thousands.
 *
 * SEC amended Form 13F so that the value column is stated in whole dollars on
 * filings MADE on or after 3 January 2023. Before that it was thousands. The
 * rule turns on when the filing was made, not on the quarter it covers, and
 * those differ by up to 45 days - which is exactly where this went wrong.
 *
 * Three code paths each decided this independently and two got it backwards:
 *
 *   ingestFiling        keyed on accepted_at   correct
 *   secImportRows       keyed on report_date   wrong
 *   prepareImport (CMS) keyed on report_date   wrong
 *
 * Q4-2022 is the quarter where they disagree: period ends 2022-12-31, filed
 * mid-February 2023. Verified against Berkshire's own filing, accession
 * 0000950123-23-002585, accepted 2023-02-14T21:00:08Z - its value column sums
 * to 299,007,622,119, which is $299.0B and matches the portfolio. Read as
 * thousands it would be $299 trillion. The import paths would have stored it
 * that way, a thousandfold overstatement in whatever it touched: consensus
 * weights, sector weights, reported AUM.
 *
 * The CMS path had a second problem. It stamped accepted_at as the moment of
 * upload, so an analyst pasting a genuinely old filing today would have it
 * treated as a modern one - correct for Q4-2022 by accident, wrong for every
 * quarter before it.
 */

/** Filings made on or after this date state values in whole dollars. */
export const DOLLAR_RULE_DATE = '2023-01-03';

/** 13F is due 45 days after the quarter ends. */
const FILING_DEADLINE_DAYS = 45;

const isDate = (value) => /^\d{4}-\d{2}-\d{2}/.test(String(value || ''));

/**
 * The statutory deadline for a report period, used only when the real filing
 * date is unknown.
 *
 * A proxy, and named as one. It is right for every filing made on time, and for
 * a late one it errs toward "dollars" - which is the modern rule and therefore
 * the safer direction as filings get newer. It is never used when an actual
 * acceptance timestamp is available.
 */
export function filingDeadline(reportDate) {
  if (!isDate(reportDate)) return null;
  const date = new Date(`${String(reportDate).slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return null;
  date.setUTCDate(date.getUTCDate() + FILING_DEADLINE_DAYS);
  return date.toISOString().slice(0, 10);
}

/**
 * Decide the multiplier, and say what decided it.
 *
 * `basis` is returned so the caller can record why a filing was scaled the way
 * it was. A thousandfold error that cannot be traced to a reason is one nobody
 * can argue with afterwards.
 */
export function valueScaleFor({ acceptedAt = null, filedAt = null, reportDate = null, override = null } = {}) {
  const numericOverride = Number(override);
  if (Number.isFinite(numericOverride) && numericOverride > 0) {
    return { scale: numericOverride, basis: 'manager override' };
  }

  // The real filing date, in preference order. Both are genuine statements of
  // when the filing was made; the deadline is not.
  const filingDate = [acceptedAt, filedAt].map((v) => (isDate(v) ? String(v).slice(0, 10) : null)).find(Boolean);
  if (filingDate) {
    return {
      scale: filingDate < DOLLAR_RULE_DATE ? 1000 : 1,
      basis: `filing date ${filingDate}`,
    };
  }

  const deadline = filingDeadline(reportDate);
  if (deadline) {
    return {
      scale: deadline < DOLLAR_RULE_DATE ? 1000 : 1,
      basis: `estimated from the ${FILING_DEADLINE_DAYS}-day deadline for ${String(reportDate).slice(0, 10)}`,
    };
  }

  // Nothing to go on. Thousands is the older convention and the one that
  // applies to the filings most likely to lack a date, but the caller is told
  // this was a fallback rather than a determination.
  return { scale: 1000, basis: 'no filing or report date available' };
}

/**
 * Cross-check the decision against the numbers themselves.
 *
 * A 13F value column in whole dollars divided by share count gives a per-share
 * price - normally somewhere between a dollar and a few thousand. If most rows
 * come out below one, the values are almost certainly in thousands and were
 * scaled as dollars. This does not override the decision; it reports a
 * disagreement, because a heuristic silently overruling a documented rule is
 * how the original confusion started.
 */
export function detectScaleMismatch(rows, appliedScale) {
  const ratios = (rows || [])
    .filter((row) => Number(row?.shares) > 0 && Number(row?.value_usd) > 0 && !row?.put_call)
    .map((row) => Number(row.value_usd) / Number(row.shares))
    .sort((a, b) => a - b);
  if (ratios.length < 5) return null;

  const median = ratios[Math.floor(ratios.length / 2)];
  if (appliedScale === 1 && median < 1) {
    return { suspected: 1000, applied: appliedScale, median, reason: 'implied per-share prices are below $1, so the column is probably thousands' };
  }
  if (appliedScale === 1000 && median > 100_000) {
    return { suspected: 1, applied: appliedScale, median, reason: 'implied per-share prices exceed $100,000, so the column is probably whole dollars' };
  }
  return null;
}


/**
 * The scale to actually use, when the filing's own numbers contradict the rule.
 *
 * The rule is documented and correct: values are whole dollars on filings made
 * from 3 January 2023. Filers do not all follow it. Renaissance Technologies
 * filed its Q3 2023 table on 14 November 2023 - ten months after the change -
 * reporting Apple at 719,357 against 4,201,607 shares. That is $0.17 a share.
 * Multiplied by a thousand it is $171.21, which is what Apple closed at on
 * 29 September 2023. The table is in thousands and says so nowhere.
 *
 * Applying the rule to that filing stores a $60bn book as $60m, and the error
 * is invisible downstream: every position is wrong by the same factor, so the
 * portfolio still balances and the weights are still right.
 *
 * This is deliberately not "the heuristic wins". The heuristic only wins when
 * the arithmetic leaves no room for doubt. value / shares is a share price,
 * and a share price is not four orders of magnitude below a dollar; correcting
 * it has to land somewhere a share can actually trade. Anything short of that
 * stays a warning, because a heuristic quietly overruling a documented rule is
 * how the original thousandfold confusion took hold.
 */
export function resolveScale({ scale, basis }, mismatch) {
  if (!mismatch) return { scale, basis, overridden: false };

  const corrected = mismatch.median * mismatch.suspected / mismatch.applied;
  // A plausible share price. Wide on purpose - Berkshire's A shares trade
  // above $700,000 and penny stocks trade below a cent - because this is a
  // check that the correction is sane, not a view on what a stock should cost.
  const plausible = corrected >= 0.5 && corrected <= 1_000_000;
  // The reading being replaced has to be clearly untenable, not merely worse.
  const untenable = mismatch.applied === 1
    ? mismatch.median < 0.5
    : mismatch.median > 500_000;

  if (!plausible || !untenable) return { scale, basis, overridden: false };

  return {
    scale: mismatch.suspected,
    basis: `filing's own figures (implied price $${mismatch.median.toPrecision(3)} at scale ${mismatch.applied},`
      + ` $${corrected.toPrecision(4)} at scale ${mismatch.suspected}); the ${basis} rule says ${mismatch.applied}`,
    overridden: true,
  };
}
