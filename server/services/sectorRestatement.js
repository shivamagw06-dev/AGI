/**
 * Re-derive stored sectors from stored SIC codes.
 *
 * When the sector map changes, every row classified by the old one is wrong
 * and nothing notices. The nightly queue measures staleness by when a row was
 * written, which is the right question for "has this company been re-checked
 * lately" and the wrong one for "was this produced by the map we now use" - so
 * the seventy rows written by the broken map were the exact rows the queue
 * protected from being redone.
 *
 * No SEC traffic is needed to fix that. sic_code is stored on every row, and
 * the sector is a pure function of it, so the whole table can be restated from
 * data already held.
 *
 * Two things are deliberately not touched. `industry` is left alone: it holds
 * EDGAR's own sicDescription where the registrant supplied one, which is more
 * specific than any label of ours and is not what was wrong. And a row whose
 * sic_code cannot be read is left exactly as it is - re-deriving it would
 * turn a classification we once had into Unclassified on the strength of a
 * missing input, which is a loss, not a correction.
 */

/**
 * The rows whose sector would change, and what it would change to.
 *
 * @param {object[]} rows stored classifications, carrying at least sic_code and sector
 * @param {(code: string|number) => {sector: string}} classify usually classifySic
 * @returns {{row: object, from: string, to: string}[]}
 */
export function restatements(rows, classify) {
  const out = [];
  for (const row of rows || []) {
    const next = classify(row?.sic_code)?.sector;
    // Unclassified is never written back, and this one check covers both ways
    // of arriving at it: a code the map cannot read, and a code it does not
    // cover. Replacing a real sector with Unclassified on the strength of a
    // missing input is a loss dressed up as a correction, and these rows are
    // the ones most likely to have been corrected by hand.
    if (!next || next === 'Unclassified') continue;

    const current = String(row?.sector || '');
    if (next === current) continue;
    out.push({ row, from: current, to: next });
  }
  return out;
}

/**
 * A restatement as a row to write back.
 *
 * The whole original row with one field replaced, so the write carries every
 * not-null column the table requires and changes exactly one thing.
 */
export function restated({ row, to }) {
  return { ...row, sector: to, updated_at: new Date().toISOString() };
}

/** How many rows move from each sector to each other, largest first. */
export function movementSummary(changes) {
  const counts = new Map();
  for (const { from, to } of changes || []) {
    const key = `${from || 'Unclassified'} -> ${to}`;
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return [...counts.entries()].map(([move, count]) => ({ move, count })).sort((a, b) => b.count - a.count);
}
