/**
 * How much of a live snapshot is still needed, and for how long.
 *
 * live_market_snapshots grows about 150 MB a day and nothing prunes it. At the
 * current fill that exhausts the disk in roughly a month, and a full disk puts
 * Postgres into read-only, which takes the whole site down. So this is not
 * housekeeping; it is the difference between the database staying writable and
 * not.
 *
 * What reads it, and how far back:
 *
 *   hflLivePriceOverlay          20 minutes   ltp
 *   loadRecentSnapshots          90 minutes   the whole row, including raw_factors
 *   loadSessionOpeningSnapshots  today's open the whole row
 *   confluenceValidationStore    20 days      ltp and observed_at only
 *
 * Two consequences. raw_factors - roughly seventy per cent of the table - is
 * untouched by anything past ninety minutes, so it can be emptied on older
 * rows without any reader noticing. And a row older than the longest
 * confluence horizon plus its settlement window is read by nothing at all.
 *
 * What is deliberately NOT touched: live_alpha_signals. Its outcomes reference
 * it with `on delete cascade`, so deleting old signals would silently destroy
 * live_alpha_signal_outcomes - the only record of whether the five strategy
 * engines actually worked. That data is small and irreplaceable.
 */

/** Rows whose raw_factors nothing will read again. */
export const RAW_FACTORS_KEEP_DAYS = 3;

/**
 * Rows nothing will read again at all.
 *
 * The longest reader is the 20-day confluence horizon, whose settlement window
 * runs eight hours past its due time. Twenty-five days clears both with days
 * to spare, so an outcome that settles late still finds its price.
 */
export const ROW_KEEP_DAYS = 25;

/** The cutoff for a step, as an ISO instant. */
export function cutoff(days, asOf = new Date()) {
  const at = new Date(asOf);
  at.setUTCDate(at.getUTCDate() - Math.max(0, Number(days) || 0));
  return at.toISOString();
}

/**
 * Day-sized windows from oldest to newest, stopping at the cutoff.
 *
 * Worked one day at a time rather than in one statement. A single update
 * across four million rows writes a WAL record for every one of them and
 * builds an enormous temp footprint - which is what exhausted the disk when a
 * scan of this table was attempted earlier. Day-sized batches keep each
 * transaction small enough to commit and be reclaimed before the next.
 */
export function dayWindows(oldest, cutoffAt) {
  const start = new Date(oldest);
  const end = new Date(cutoffAt);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || start >= end) return [];

  const windows = [];
  let from = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), start.getUTCDate()));
  while (from < end) {
    const to = new Date(from);
    to.setUTCDate(to.getUTCDate() + 1);
    windows.push({ from: from.toISOString(), to: (to < end ? to : end).toISOString() });
    from = to;
  }
  return windows;
}

/**
 * Whether a step should stop before it starts.
 *
 * A cutoff that is not in the past, or a window that covers everything, means
 * the caller has miscomputed something. Refusing is cheaper than discovering
 * it afterwards.
 */
export function refuseReason({ cutoffAt, newest, asOf = new Date() }) {
  const at = Date.parse(cutoffAt);
  if (!Number.isFinite(at)) return 'the cutoff is not a valid date';
  if (at >= Date.parse(new Date(asOf).toISOString())) return 'the cutoff is not in the past';
  const latest = Date.parse(newest || '');
  if (Number.isFinite(latest) && at >= latest) {
    return 'the cutoff is at or after the newest row, which would clear the whole table';
  }
  return null;
}

/**
 * The two steps, in the order they must run.
 *
 * Delete comes first. A row older than ROW_KEEP_DAYS is going away entirely,
 * so blanking its raw_factors first would rewrite four million tuples for
 * rows that are about to be removed - twice the write volume and twice the
 * dead-tuple footprint, on a disk that is the reason any of this is running.
 */
export function plannedSteps(asOf = new Date()) {
  return [
    {
      name: 'delete',
      rpc: 'delete_live_snapshots',
      keepDays: ROW_KEEP_DAYS,
      cutoffAt: cutoff(ROW_KEEP_DAYS, asOf),
      describes: `remove rows older than ${ROW_KEEP_DAYS} days`,
    },
    {
      name: 'blank-factors',
      rpc: 'prune_live_snapshot_factors',
      keepDays: RAW_FACTORS_KEEP_DAYS,
      cutoffAt: cutoff(RAW_FACTORS_KEEP_DAYS, asOf),
      describes: `empty raw_factors on rows older than ${RAW_FACTORS_KEEP_DAYS} days`,
    },
  ];
}
