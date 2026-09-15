/**
 * Which security a consensus row is about.
 *
 * Consensus grouped holdings by `ticker || cusip` and then published the row
 * under `cusip`. Those are not the same thing, and the gap opens whenever one
 * security reaches the aggregation with a ticker on some rows and not others -
 * which is ordinary, because tickers resolve per filing at that filing's own
 * report date, so two managers holding the same security on different dates
 * can carry different values for it.
 *
 * The security then formed two groups, both publishing the same CUSIP, and the
 * insert carried two rows with one conflict key:
 *
 *   ON CONFLICT DO UPDATE command cannot affect row a second time
 *
 * which failed the whole signal rebuild - every fund score and every consensus
 * row - on one duplicate.
 *
 * The CUSIP is what the row is published under, so the CUSIP is what it is
 * grouped by. It is also the identifier that is always present: a ticker is a
 * label that may or may not have resolved yet, and keying on something that
 * can be absent means the key changes as enrichment catches up.
 */

/** The identity a consensus row is grouped and published under. */
export function consensusKey(row) {
  const cusip = String(row?.cusip || '').trim().toUpperCase();
  return cusip || null;
}

/**
 * Signal rows with no two sharing a conflict key.
 *
 * A safety net rather than the fix. Grouping by CUSIP is what stops duplicates
 * arising; this stops one that slips through from failing the entire rebuild,
 * because the cost is wildly out of proportion - a single repeated security
 * withheld every fund's scores as well.
 */
export function dedupeSignalRows(rows) {
  const byKey = new Map();
  const dropped = [];
  for (const row of rows || []) {
    const key = [row?.scope_type, row?.scope_id, row?.as_of, row?.signal_type].join('|');
    if (byKey.has(key)) { dropped.push(key); continue; }
    byKey.set(key, row);
  }
  return { rows: [...byKey.values()], dropped };
}
