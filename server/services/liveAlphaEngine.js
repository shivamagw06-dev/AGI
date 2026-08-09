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
    // Sector index return already contains the broad-market move. Stock minus
    // sector is therefore the clean residual; subtracting Nifty again would
    // double-count the market component.
    residual15m: values.return15m - values.sectorReturn15m,
    residual60m: values.return60m - values.sectorReturn60m,
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

/**
 * Detect abnormal participation confirmed by price direction. This is a
 * research ranking only: it deliberately emits no order side, size or target.
 */
export function evaluateVolumeLiquidityAnomaly(snapshots, {
  minimumUniverse = 10,
  tailFraction = 0.15,
  minimumVolumeRatio = 1.25,
  maximumSpreadBps = 35,
  asOf = new Date().toISOString(),
} = {}) {
  if (!Array.isArray(snapshots) || snapshots.length < minimumUniverse) {
    throw new Error(`Volume anomaly requires at least ${minimumUniverse} simultaneous instruments.`);
  }
  if (!(tailFraction > 0 && tailFraction <= 0.25)) throw new Error('tailFraction must be above 0 and at most 0.25.');
  const normalized = snapshots.map(normalizeSnapshot);
  if (new Set(normalized.map((row) => row.symbol)).size !== normalized.length) throw new Error('Snapshot symbols must be unique.');
  const volumeZ = zScores(normalized, 'volumeSurprise');
  const residualZ = zScores(normalized, 'residual15m');
  const ranked = normalized.map((row, index) => {
    const liquidityOk = row.minimumLiquidity && (row.spreadBps === null || row.spreadBps <= maximumSpreadBps);
    const directionalConfirmation = Math.sign(row.residual15m) === Math.sign(row.residual60m) ? 1 : 0.5;
    const anomalyScore = (0.70 * volumeZ[index]) + (0.30 * Math.abs(residualZ[index]) * directionalConfirmation);
    return {
      symbol: row.symbol,
      sector: row.sector,
      instrument_key: row.instrumentKey,
      alpha_z: Number(anomalyScore.toFixed(4)),
      residual_15m: Number(row.residual15m.toFixed(4)),
      residual_60m: Number(row.residual60m.toFixed(4)),
      volume_surprise: Number(row.volumeSurprise.toFixed(4)),
      sector_strength: Number(row.sectorStrength.toFixed(4)),
      liquidity_ok: liquidityOk,
      signal_quality: preliminarySignalQuality({ alphaZ: anomalyScore, persistence: directionalConfirmation, volumeSurprise: row.volumeSurprise, liquidityOk, dataCoverage: row.instrumentKey ? 1 : 0.9 }),
      empirical_confidence: { status: 'unvalidated', score: null, comparable_observations: 0 },
      factors: {
        volume_surprise_z: Number(volumeZ[index].toFixed(4)),
        absolute_residual_15m_z: Number(Math.abs(residualZ[index]).toFixed(4)),
        spread_bps: row.spreadBps,
        directional_confirmation: directionalConfirmation,
      },
    };
  }).sort((left, right) => right.alpha_z - left.alpha_z);
  const eligible = ranked.filter((row) => row.liquidity_ok && row.volume_surprise >= minimumVolumeRatio && row.alpha_z > 0);
  const candidateCount = Math.min(eligible.length, Math.max(1, Math.ceil(ranked.length * tailFraction)));
  const candidateSymbols = new Set(eligible.slice(0, candidateCount).map((row) => row.symbol));
  const signals = ranked.map((row, index) => ({
    ...row,
    rank: index + 1,
    classification: !row.liquidity_ok ? 'filtered' : candidateSymbols.has(row.symbol)
      ? (row.residual_15m >= 0 ? 'abnormal_accumulation_candidate' : 'abnormal_distribution_candidate')
      : 'neutral',
  }));
  return {
    engine: ALPHA_ENGINES.VOLUME_ANOMALY,
    as_of: new Date(asOf).toISOString(),
    research_only: true,
    execution_enabled: false,
    universe_size: signals.length,
    tail_size: candidateCount,
    config: { tailFraction, minimumVolumeRatio, maximumSpreadBps },
    signals,
  };
}

export function evaluateOpeningRangeExpansion(snapshots, {
  minimumUniverse = 10,
  breakoutBufferPct = 0.10,
  minimumVolumeRatio = 1.10,
  minimumRangePct = 0.15,
  maximumRangePct = 3,
  maximumSpreadBps = 35,
  asOf = new Date().toISOString(),
} = {}) {
  if (!Array.isArray(snapshots) || snapshots.length < minimumUniverse) {
    throw new Error(`Opening-range expansion requires at least ${minimumUniverse} simultaneous instruments.`);
  }
  const rows = snapshots.map((row, index) => {
    const symbol = String(row?.symbol || '').trim().toUpperCase();
    const sector = String(row?.sector || '').trim().toUpperCase();
    const currentPrice = finite(row.currentPrice ?? row.current_price);
    const openingHigh = finite(row.openingHigh ?? row.opening_high);
    const openingLow = finite(row.openingLow ?? row.opening_low);
    const volumeSurprise = finite(row.cumulativeVolume) / finite(row.expectedCumulativeVolume);
    const spreadBps = finite(row.spreadBps ?? row.spread_bps);
    if (!/^[A-Z0-9&-]+$/.test(symbol) || !sector || ![currentPrice, openingHigh, openingLow, volumeSurprise].every(Number.isFinite)) throw new Error(`Invalid opening-range snapshot at index ${index}.`);
    if (!(openingLow > 0 && openingHigh >= openingLow && currentPrice > 0 && volumeSurprise >= 0)) throw new Error(`Invalid opening range for ${symbol}.`);
    const midpoint = (openingHigh + openingLow) / 2;
    const rangePct = ((openingHigh - openingLow) / midpoint) * 100;
    const upsideBreakoutPct = ((currentPrice / openingHigh) - 1) * 100;
    const downsideBreakoutPct = ((openingLow / currentPrice) - 1) * 100;
    const direction = upsideBreakoutPct >= breakoutBufferPct ? 'positive' : downsideBreakoutPct >= breakoutBufferPct ? 'negative' : null;
    const breakoutPct = Math.max(upsideBreakoutPct, downsideBreakoutPct, 0);
    const rangeOk = rangePct >= minimumRangePct && rangePct <= maximumRangePct;
    const liquidityOk = row.minimumLiquidity !== false && (spreadBps === null || spreadBps <= maximumSpreadBps);
    return { symbol, sector, instrumentKey: String(row.instrumentKey || row.instrument_key || '').trim() || null, currentPrice, openingHigh, openingLow, rangePct, breakoutPct, direction, volumeSurprise, spreadBps, rangeOk, liquidityOk };
  });
  if (new Set(rows.map((row) => row.symbol)).size !== rows.length) throw new Error('Snapshot symbols must be unique.');
  const breakoutZ = zScores(rows, 'breakoutPct');
  const volumeZ = zScores(rows, 'volumeSurprise');
  const signals = rows.map((row, index) => {
    const alphaZ = (0.65 * breakoutZ[index]) + (0.35 * volumeZ[index]);
    const candidate = row.direction && row.rangeOk && row.liquidityOk && row.volumeSurprise >= minimumVolumeRatio;
    return {
      symbol: row.symbol, sector: row.sector, instrument_key: row.instrumentKey,
      alpha_z: Number(alphaZ.toFixed(4)), residual_15m: 0, residual_60m: 0,
      volume_surprise: Number(row.volumeSurprise.toFixed(4)), sector_strength: 0,
      liquidity_ok: row.liquidityOk,
      classification: !row.liquidityOk ? 'filtered' : !row.rangeOk ? 'invalid_opening_range' : candidate ? (row.direction === 'positive' ? 'upside_opening_breakout_candidate' : 'downside_opening_breakout_candidate') : 'neutral',
      signal_quality: preliminarySignalQuality({ alphaZ, persistence: candidate ? 1 : 0, volumeSurprise: row.volumeSurprise, liquidityOk: row.liquidityOk && row.rangeOk, dataCoverage: row.instrumentKey ? 1 : 0.9 }),
      empirical_confidence: { status: 'unvalidated', score: null, comparable_observations: 0 },
      factors: { opening_high: row.openingHigh, opening_low: row.openingLow, opening_range_pct: Number(row.rangePct.toFixed(4)), breakout_pct: Number(row.breakoutPct.toFixed(4)), breakout_z: Number(breakoutZ[index].toFixed(4)), volume_surprise_z: Number(volumeZ[index].toFixed(4)), spread_bps: row.spreadBps },
    };
  }).sort((left, right) => right.alpha_z - left.alpha_z).map((row, index) => ({ ...row, rank: index + 1 }));
  return { engine: ALPHA_ENGINES.OPENING_RANGE, as_of: new Date(asOf).toISOString(), research_only: true, execution_enabled: false, universe_size: signals.length, config: { openingMinutes: 15, breakoutBufferPct, minimumVolumeRatio, minimumRangePct, maximumRangePct, maximumSpreadBps }, signals };
}

export const LIVE_ALPHA_ROADMAP = Object.freeze([
  { engine: ALPHA_ENGINES.MOMENTUM, status: 'implemented' },
  { engine: ALPHA_ENGINES.VOLUME_ANOMALY, status: 'implemented' },
  { engine: ALPHA_ENGINES.OPENING_RANGE, status: 'implemented' },
  { engine: ALPHA_ENGINES.MEAN_REVERSION, status: 'planned' },
  { engine: ALPHA_ENGINES.DERIVATIVES, status: 'planned' },
]);
