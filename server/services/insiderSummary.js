/**
 * Summarising insider activity for one security.
 *
 * A Form 4 feed is easy to make and easy to make misleading. Most filings
 * record a vesting calendar rather than a decision - shares withheld for tax,
 * options exercised on a schedule set years earlier, grants nobody chose to
 * buy - and a panel that totals them produces alarming "insider selling" from
 * a payroll event.
 *
 * So the summary leads with what somebody decided, counts the rest apart, and
 * marks trades made under a Rule 10b5-1 plan. A sale scheduled months in
 * advance is not a view on the price today, and putting it beside a
 * discretionary sale is what makes these feeds noise.
 *
 * Where the filings say nothing, the answer is that they say nothing. A
 * quarter with no insider activity and a quarter we failed to parse are
 * different facts and are reported as different facts.
 */

const n = (value) => (Number.isFinite(Number(value)) ? Number(value) : 0);

/** The transactions inside a stored filing row, or none if it was never read. */
export function transactionsOf(row) {
  const parsed = row?.parsed_data;
  if (!parsed || !Array.isArray(parsed.transactions)) return null;
  return parsed.transactions;
}

/**
 * Roll up insider filings for a security.
 *
 * `unread` counts filings whose document was never parsed. They are not zero
 * activity - they are unknown activity, and a summary that folds them into the
 * totals reports an absence it did not observe.
 */
export function summariseInsiderFilings(filings, { sinceDays = 180, asOf = null } = {}) {
  const cutoff = asOf ? Date.parse(asOf) - sinceDays * 86_400_000 : null;
  const rows = (filings || []).filter((row) => {
    if (!cutoff) return true;
    const filed = Date.parse(row?.filed_at || row?.report_date || '');
    return !Number.isFinite(filed) || filed >= cutoff;
  });

  const events = [];
  let unread = 0;
  for (const row of rows) {
    const transactions = transactionsOf(row);
    if (transactions === null) { unread += 1; continue; }
    const parsed = row.parsed_data;
    for (const t of transactions) {
      events.push({
        filed_at: row.filed_at,
        accession_number: row.accession_number,
        source_url: row.source_url,
        insider: parsed.owners?.[0]?.name || null,
        insider_title: parsed.owners?.[0]?.officer_title || null,
        roles: parsed.owners?.[0]?.roles || [],
        planned: Boolean(parsed.planned),
        ...t,
      });
    }
  }

  const discretionary = events.filter((e) => e.discretionary);
  const buys = discretionary.filter((e) => e.direction === 'acquire');
  const sells = discretionary.filter((e) => e.direction === 'dispose');

  return {
    window_days: sinceDays,
    filings: rows.length,
    unread,
    events: events.sort((a, b) => String(b.transaction_date || '').localeCompare(String(a.transaction_date || ''))),
    // What somebody decided to do.
    buy_count: buys.length,
    sell_count: sells.length,
    buy_value: buys.reduce((s, e) => s + n(e.value_usd), 0),
    sell_value: sells.reduce((s, e) => s + n(e.value_usd), 0),
    // Trades that were scheduled rather than decided on the day. Counted
    // inside the discretionary figures because they are real transactions,
    // but flagged so a reader can discount them.
    planned_count: discretionary.filter((e) => e.planned).length,
    // The vesting calendar, kept apart from the decisions.
    routine_count: events.length - discretionary.length,
    distinct_insiders: new Set(events.map((e) => e.insider).filter(Boolean)).size,
  };
}

/** One line a reader can act on, or an honest statement that there is none. */
export function insiderHeadline(summary) {
  if (!summary || (!summary.filings && !summary.unread)) return 'No insider filings in this window.';
  if (!summary.events.length) {
    return summary.unread
      ? `${summary.unread} insider filing(s) in this window could not be read.`
      : 'No insider filings in this window.';
  }
  if (!summary.buy_count && !summary.sell_count) {
    return `${summary.routine_count} insider transaction(s), all grants, option exercises or tax withholding — no discretionary trades.`;
  }
  const parts = [];
  if (summary.buy_count) parts.push(`${summary.buy_count} discretionary purchase${summary.buy_count === 1 ? '' : 's'}`);
  if (summary.sell_count) parts.push(`${summary.sell_count} discretionary sale${summary.sell_count === 1 ? '' : 's'}`);
  const planned = summary.planned_count ? `, ${summary.planned_count} under a pre-arranged plan` : '';
  return `${parts.join(' and ')}${planned}.`;
}
