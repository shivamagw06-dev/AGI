/**
 * Deciding what interval a looked-up identifier is entitled to claim.
 *
 * OpenFIGI answers one question: what does this CUSIP map to *now*. The
 * existing enrichment stored that answer as `valid_from: '1900-01-01'` - as
 * though today's ticker had applied for the whole of history. Under the old
 * newest-mapping-wins resolution that was invisible, because the interval was
 * never consulted. Under point-in-time resolution it actively asserts
 * something false about every filing it touches.
 *
 * What is actually known is narrower and worth stating exactly:
 *
 *   the CUSIP appears in filings between two dates, which is evidence it
 *   existed then; and a vendor says it currently maps to a ticker.
 *
 * So a looked-up mapping claims from the earliest date the CUSIP was observed,
 * not from 1900. That is still an assumption - the CUSIP could have meant
 * something else before we saw it, or been reassigned during the window - but
 * it is bounded by evidence, and it is recorded as unverified so a later
 * discovery can split the interval rather than having to argue with a claim
 * that reaches back to the nineteenth century.
 */

/** The earliest report date a CUSIP was observed in, as an ISO date. */
export function earliestObservation(rows) {
  const dates = (rows || [])
    .map((row) => String(row?.report_date || '').slice(0, 10))
    .filter((d) => /^\d{4}-\d{2}-\d{2}$/.test(d))
    .sort();
  return dates[0] || null;
}

/**
 * Build the mapping row for a vendor answer.
 *
 * Returns null when there is nothing to claim - no ticker, or no observation to
 * anchor the interval to. Writing a mapping with no evidence behind it is how
 * the 1900 claim got there in the first place.
 */
export function mappingFromLookup({ cusip, ticker, issuerName, observedFrom, source = 'openfigi' }) {
  const key = String(cusip || '').trim().toUpperCase();
  const symbol = String(ticker || '').trim().toUpperCase();
  if (!key || !symbol) return null;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(observedFrom || ''))) return null;

  return {
    cusip: key,
    ticker: symbol,
    issuer_name: issuerName || null,
    // Bounded by what was observed, not by 1900.
    valid_from: observedFrom,
    valid_to: null,
    // A security is its own key until something merges it.
    security_key: key,
    source,
    manually_verified: false,
    updated_at: new Date().toISOString(),
  };
}

/**
 * Rank unmapped securities by how much they matter.
 *
 * Roughly ninety per cent of holdings rows have no ticker, and they cannot all
 * be resolved at once against a rate-limited vendor. Ordering by disclosed
 * value means each run closes the gap where it changes the most numbers -
 * consensus, sector weights, and eventually prices - rather than working
 * alphabetically through the tail.
 */
export function rankUnmapped(rows, limit = 500) {
  const byCusip = new Map();
  for (const row of rows || []) {
    const cusip = String(row?.cusip || '').trim().toUpperCase();
    if (!cusip) continue;
    let entry = byCusip.get(cusip);
    if (!entry) {
      entry = {
        cusip,
        issuer_name: row.issuer_name || null,
        // Summed across every manager-quarter row, which is a ranking
        // heuristic and not a holding. Reported under a name that says so:
        // presented as "disclosed value" it read as though fifty-two managers
        // held $850bn of QQQ, which is more than the fund has.
        cumulative_value: 0,
        // The latest quarter's value, which is what a position is actually
        // worth now, and the figure worth eyeballing before writing a mapping.
        latest_value: 0,
        latest_date: null,
        observations: 0,
        managers: new Set(),
        dates: [],
      };
      byCusip.set(cusip, entry);
    }
    const value = Number(row.value_usd) || 0;
    const date = row.report_date ? String(row.report_date).slice(0, 10) : null;
    entry.cumulative_value += value;
    entry.observations += 1;
    // Distinct managers. The count printed before was the row count, so a
    // holding reported by five managers over eleven quarters read as fifty-five.
    if (row.manager_id) entry.managers.add(row.manager_id);
    if (date) {
      entry.dates.push(date);
      if (!entry.latest_date || date > entry.latest_date) {
        entry.latest_date = date;
        entry.latest_value = value;
      } else if (date === entry.latest_date) {
        entry.latest_value += value;
      }
    }
    if (!entry.issuer_name && row.issuer_name) entry.issuer_name = row.issuer_name;
  }

  return [...byCusip.values()]
    .map((entry) => ({
      cusip: entry.cusip,
      issuer_name: entry.issuer_name,
      cumulative_value: entry.cumulative_value,
      latest_value: entry.latest_value,
      latest_date: entry.latest_date,
      observations: entry.observations,
      managers: entry.managers.size,
      observed_from: earliestObservation(entry.dates.map((d) => ({ report_date: d }))),
    }))
    // Cumulative value first, because a position held large across many
    // quarters matters more than one that appeared once; then distinct managers.
    .sort((a, b) => b.cumulative_value - a.cumulative_value || b.managers - a.managers)
    .slice(0, limit);
}

/**
 * Coverage, as a figure that can be quoted.
 *
 * Reported before and after a run so the effect is visible, and so a claim
 * about coverage on the page can be traced to a measurement rather than an
 * impression.
 */
export function coverage({ total, mapped }) {
  const t = Number(total) || 0;
  const m = Number(mapped) || 0;
  return {
    total_rows: t,
    mapped_rows: m,
    unmapped_rows: Math.max(0, t - m),
    mapped_pct: t ? Number(((m / t) * 100).toFixed(2)) : 0,
  };
}
