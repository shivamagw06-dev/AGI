export const CONVICTION_FILTERS = Object.freeze([
  ['shortlist', 'Shortlist'],
  ['watch', 'Watch'],
  ['incomplete', 'Needs evidence'],
  ['all', 'All ranked'],
]);

export function filterConvictionRows(rows = [], filter = 'shortlist') {
  if (filter === 'shortlist') return rows.filter((row) => row.eligible_for_research_shortlist);
  if (filter === 'watch') return rows.filter((row) => row.conviction_label === 'WATCH');
  if (filter === 'incomplete') return rows.filter((row) => row.conviction_label === 'INCOMPLETE');
  return rows;
}

export function convictionTone(label = '') {
  if (label === 'HIGH_CONVICTION' || label === 'CONFIRMED') return 'positive';
  if (label === 'CONTRADICTED') return 'negative';
  if (label === 'TACTICAL_ONLY') return 'tactical';
  return 'neutral';
}

export function readableConvictionLabel(label = '') {
  return String(label || 'unclassified').replaceAll('_', ' ').toLowerCase();
}
