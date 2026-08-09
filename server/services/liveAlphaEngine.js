/**
 * AGI Live Alpha Engine — research-only factor calculations.
 *
 * Phase 1 implements cross-sectional residual momentum. It accepts normalized
 * snapshots so feed collection, replay/backtesting and live evaluation all use
 * the exact same calculation path.
 */

export const ALPHA_ENGINES = Object.freeze({
  MOMENTUM: 'cross_sectional_momentum_v1',
  VOLUME_ANOMALY: 'volume_liquidity_anomaly_v1',
  OPENING_RANGE: 'opening_range_expansion_v1',
  MEAN_REVERSION: 'intraday_mean_reversion_v1',
  DERIVATIVES: 'derivatives_positioning_v1',
});

const DEFAULT_WEIGHTS = Object.freeze({
  residual15m: 0.30,
  residual60m: 0.30,
  volumeSurprise: 0.20,
  sectorStrength: 0.20,
});

function finite(value) {
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
}

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function standardDeviation(values) {
  if (values.length < 2) return 0;
  const average = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + ((value - average) ** 2), 0) / values.length);
}

function zScores(rows, key, { winsorize = 4 } = {}) {
  const values = rows.map((row) => row[key]);
  const average = mean(values);
  const deviation = standardDeviation(values);
  return rows.map((row) => {
    if (deviation === 0) return 0;
    const value = (row[key] - average) / deviation;
    return Math.max(-winsorize, Math.min(winsorize, value));
  });
}

function preliminarySignalQuality({ alphaZ, persistence, volumeSurprise, liquidityOk, dataCoverage }) {
  const strength = Math.min(Math.abs(alphaZ) / 2.5, 1);
  const score = 100 * (
    0.45 * strength
    + 0.20 * persistence
    + 0.15 * Math.min(Math.max(volumeSurprise - 0.5, 0) / 1.5, 1)
    + 0.10 * (liquidityOk ? 1 : 0)
    + 0.10 * dataCoverage
  );
  const rounded = Math.round(Math.max(0, Math.min(100, score)));
  return {
    score: rounded,
    label: rounded >= 90 ? 'exceptional' : rounded >= 80 ? 'very_strong' : rounded >= 70 ? 'strong' : rounded >= 60 ? 'moderate' : rounded >= 50 ? 'weak' : 'ignore',
    empirical: false,
  };
}

function normalizeSnapshot(row, index) {
  const symbol = String(row?.symbol || '').trim().toUpperCase();
  const sector = String(row?.sector || '').trim().toUpperCase();
  if (!/^[A-Z0-9&-]+$/.test(symbol)) throw new Error(`Invalid symbol at snapshots[${index}].`);
  if (!sector) throw new Error(`Missing sector at snapshots[${index}].`);
  const fields = ['return15m', 'return60m', 'benchmarkReturn15m', 'benchmarkReturn60m', 'sectorReturn15m', 'sectorReturn60m', 'cumulativeVolume', 'expectedCumulativeVolume'];
  const values = Object.fromEntries(fields.map((field) => [field, finite(row[field])]));
  for (const field of fields) if (values[field] === null) throw new Error(`Invalid ${field} for ${symbol}.`);
  if (values.expectedCumulativeVolume <= 0 || values.cumulativeVolume < 0) throw new Error(`Invalid volume baseline for ${symbol}.`);
  return {
    symbol,
    sector,
    instrumentKey: String(row.instrumentKey || row.instrument_key || '').trim() || null,
    ...values,
    spreadBps: finite(row.spreadBps ?? row.spread_bps),
    minimumLiquidity: row.minimumLiquidity !== false,
    residual15m: values.return15m - values.benchmarkReturn15m - values.sectorReturn15m,
    residual60m: values.return60m - values.benchmarkReturn60m - values.sectorReturn60m,
    volumeSurprise: values.cumulativeVolume / values.expectedCumulativeVolume,
    sectorStrength: values.sectorReturn60m - values.benchmarkReturn60m,
  };
}

function assertWeights(weights) {
  const merged = { ...DEFAULT_WEIGHTS, ...(weights || {}) };
  const total = Object.values(merged).reduce((sum, value) => sum + value, 0);
  if (Object.values(merged).some((value) => !Number.isFinite(value) || value < 0) || Math.abs(total - 1) > 1e-9) {
    throw new Error('Momentum factor weights must be non-negative and sum to 1.');
  }
  return merged;
}

/**
 * Rank one simultaneous universe snapshot. Returns research candidates only;
 * no execution instruction, quantity, target or order side is produced.
 */
export function evaluateCrossSectionalMomentum(snapshots, {
  weights,
  tailFraction = 0.10,
  minimumUniverse = 10,
  maximumSpreadBps = 35,
  asOf = new Date().toISOString(),
} = {}) {
  if (!Array.isArray(snapshots) || snapshots.length < minimumUniverse) {
    throw new Error(`Cross-sectional momentum requires at least ${minimumUniverse} simultaneous instruments.`);
  }
  if (!(tailFraction > 0 && tailFraction <= 0.25)) throw new Error('tailFraction must be above 0 and at most 0.25.');
  const factorWeights = assertWeights(weights);
  const normalized = snapshots.map(normalizeSnapshot);
  if (new Set(normalized.map((row) => row.symbol)).size !== normalized.length) throw new Error('Snapshot symbols must be unique.');

  const z15 = zScores(normalized, 'residual15m');
  const z60 = zScores(normalized, 'residual60m');
  const zVolume = zScores(normalized, 'volumeSurprise');
  const zSector = zScores(normalized, 'sectorStrength');
  const ranked = normalized.map((row, index) => {
    const alphaZ = factorWeights.residual15m * z15[index]
      + factorWeights.residual60m * z60[index]
      + factorWeights.volumeSurprise * zVolume[index]
      + factorWeights.sectorStrength * zSector[index];
    const persistence = Math.sign(row.residual15m) === Math.sign(row.residual60m) ? 1 : 0.35;
    const liquidityOk = row.minimumLiquidity && (row.spreadBps === null || row.spreadBps <= maximumSpreadBps);
    const dataCoverage = row.instrumentKey ? 1 : 0.9;
    return {
      symbol: row.symbol,
      sector: row.sector,
      instrument_key: row.instrumentKey,
      alpha_z: Number(alphaZ.toFixed(4)),
      residual_15m: Number(row.residual15m.toFixed(4)),
      residual_60m: Number(row.residual60m.toFixed(4)),
      volume_surprise: Number(row.volumeSurprise.toFixed(4)),
      sector_strength: Number(row.sectorStrength.toFixed(4)),
      persistence: persistence === 1 ? 'high' : 'low',
      liquidity_ok: liquidityOk,
      signal_quality: preliminarySignalQuality({ alphaZ, persistence, volumeSurprise: row.volumeSurprise, liquidityOk, dataCoverage }),
      empirical_confidence: {
        status: 'unvalidated',
        score: null,
        comparable_observations: 0,
      },
      factors: {
        residual_15m_z: Number(z15[index].toFixed(4)),
        residual_60m_z: Number(z60[index].toFixed(4)),
        volume_surprise_z: Number(zVolume[index].toFixed(4)),
        sector_strength_z: Number(zSector[index].toFixed(4)),
      },
    };
  }).sort((left, right) => right.alpha_z - left.alpha_z);

  const tailSize = Math.max(1, Math.ceil(ranked.length * tailFraction));
  const enriched = ranked.map((row, index) => ({
    ...row,
    rank: index + 1,
    classification: !row.liquidity_ok
      ? 'filtered'
      : index < tailSize
        ? 'positive_research_candidate'
        : index >= ranked.length - tailSize
          ? 'negative_research_candidate'
          : 'neutral',
  }));
  return {
    engine: ALPHA_ENGINES.MOMENTUM,
    as_of: new Date(asOf).toISOString(),
    research_only: true,
    execution_enabled: false,
    universe_size: enriched.length,
    tail_size: tailSize,
    weights: factorWeights,
    signals: enriched,
  };
}

export const LIVE_ALPHA_ROADMAP = Object.freeze([
  { engine: ALPHA_ENGINES.MOMENTUM, status: 'implemented' },
  { engine: ALPHA_ENGINES.VOLUME_ANOMALY, status: 'planned' },
  { engine: ALPHA_ENGINES.OPENING_RANGE, status: 'planned' },
  { engine: ALPHA_ENGINES.MEAN_REVERSION, status: 'planned' },
  { engine: ALPHA_ENGINES.DERIVATIVES, status: 'planned' },
]);
