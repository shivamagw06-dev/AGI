import { createPointInTimeFeatures } from './probabilisticForecast.js';

export const CROSS_SECTIONAL_FEATURE_VERSION = 'agi_cross_sectional_daily_v2';
const FACTORS = Object.freeze([
  'fundamental', 'valuation', 'eod', 'live', 'catalyst',
  'leadership', 'activity', 'breakout', 'dislocation', 'positioning',
  'research_priority',
]);

const finite = (value) => value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
const round = (value, digits = 6) => value == null ? null : Number(value.toFixed(digits));
const median = (values) => {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
};
const quantile = (values, probability) => {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const position = (sorted.length - 1) * probability;
  const lower = Math.floor(position), upper = Math.ceil(position);
  return lower === upper ? sorted[lower] : sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
};

export function robustScale(values, value) {
  const clean = values.map(finite).filter((item) => item != null);
  const target = finite(value);
  if (target == null || clean.length < 3) return null;
  const low = quantile(clean, 0.025), high = quantile(clean, 0.975);
  const winsorized = clean.map((item) => Math.max(low, Math.min(high, item)));
  const clipped = Math.max(low, Math.min(high, target));
  const center = median(winsorized);
  const mad = median(winsorized.map((item) => Math.abs(item - center)));
  if (mad > 1e-9) return round(Math.max(-8, Math.min(8, (clipped - center) / (1.4826 * mad))));
  const variance = winsorized.reduce((sum, item) => sum + (item - center) ** 2, 0) / winsorized.length;
  const deviation = Math.sqrt(variance);
  return deviation > 1e-9 ? round(Math.max(-8, Math.min(8, (clipped - center) / deviation))) : 0;
}

export function buildCrossSectionalFeatureSnapshots(events = []) {
  const snapshots = events.map(createPointInTimeFeatures);
  const marketValues = Object.fromEntries(FACTORS.map((factor) => [factor, snapshots.map((row) => row.features[factor])]));
  const sectors = new Map();
  for (const snapshot of snapshots) {
    const sector = String(snapshot.sector || 'UNCLASSIFIED').trim().toUpperCase();
    const rows = sectors.get(sector) || [];
    rows.push(snapshot); sectors.set(sector, rows);
  }
  return snapshots.map((snapshot) => {
    const sector = String(snapshot.sector || 'UNCLASSIFIED').trim().toUpperCase();
    const peers = sectors.get(sector) || [];
    const marketZ = {}, sectorZ = {}, missing = {};
    for (const factor of FACTORS) {
      const value = snapshot.features[factor];
      missing[factor] = finite(value) == null;
      marketZ[factor] = robustScale(marketValues[factor], value);
      sectorZ[factor] = robustScale(peers.map((row) => row.features[factor]), value);
    }
    const available = FACTORS.filter((factor) => !missing[factor]).length;
    return {
      ...snapshot,
      feature_version: CROSS_SECTIONAL_FEATURE_VERSION,
      features: {
        ...snapshot.features,
        cross_sectional: {
          market_z: marketZ,
          sector_z: sectorZ,
          missing,
          universe_size: snapshots.length,
          sector_size: peers.length,
          normalization: 'same_day_winsorized_2_5pct_median_mad',
        },
      },
      completeness: round(available / FACTORS.length, 4),
    };
  });
}

export { FACTORS as CROSS_SECTIONAL_FACTORS };
