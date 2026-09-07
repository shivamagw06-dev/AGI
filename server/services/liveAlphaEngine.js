import { spreadWithinLimit } from './marketSpread.js';
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

/**
 * Z-scores over the rows where the factor was actually measured.
 *
 * Rows failing `measured` get null, not 0. Sector strength is
 * `sectorReturn60m - benchmarkReturn60m`, and when a sector index has no
 * history the pipeline substitutes the benchmark for the sector, so the
 * subtraction is benchmark minus itself: exactly 0 by construction. On
 * 2026-08-19 that was 1,586 of 2,198 signals, 72%. Scoring that mass of
 * structural zeros against the handful of real values manufactured a spread
 * where none was measured, and every proxied name inherited a sector tilt it
 * had never been observed to have.
 */
function zScoresWhere(rows, key, measured, { winsorize = 4 } = {}) {
  const eligible = rows.filter(measured);
  if (eligible.length < 3) return rows.map(() => null);
  const values = eligible.map((row) => row[key]);
  const average = mean(values);
  const deviation = standardDeviation(values);
  return rows.map((row) => {
    if (!measured(row)) return null;
    if (deviation === 0) return 0;
    return Math.max(-winsorize, Math.min(winsorize, (row[key] - average) / deviation));
  });
}

/**
 * Weighted blend that skips unmeasured factors and renormalises.
 *
 * Treating a missing factor as a zero contribution quietly shrinks the
 * composite toward the mean, so a name with no sector reading looked calmer
 * than one measured as genuinely neutral. Redistributing the weight keeps the
 * two distinguishable.
 */
function blendFactors(contributions) {
  const usable = contributions.filter(([weight, value]) => weight > 0 && Number.isFinite(value));
  const total = usable.reduce((sum, [weight]) => sum + weight, 0);
  if (!(total > 0)) return 0;
  return usable.reduce((sum, [weight, value]) => sum + (weight / total) * value, 0);
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
    sectorProxyUsed: row.sectorProxyUsed === true,
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
  // Only names with a real sector index contribute to the sector factor.
  const zSector = zScoresWhere(normalized, 'sectorStrength', (row) => !row.sectorProxyUsed);
  const ranked = normalized.map((row, index) => {
    const alphaZ = blendFactors([
      [factorWeights.residual15m, z15[index]],
      [factorWeights.residual60m, z60[index]],
      [factorWeights.volumeSurprise, zVolume[index]],
      [factorWeights.sectorStrength, zSector[index]],
    ]);
    const persistence = Math.sign(row.residual15m) === Math.sign(row.residual60m) ? 1 : 0.35;
    const spreadGate = spreadWithinLimit(row.spreadBps, maximumSpreadBps);
    const liquidityOk = Boolean(row.minimumLiquidity) && spreadGate.ok;
    const liquidityVerified = Boolean(row.minimumLiquidity) && spreadGate.verified;
    const dataCoverage = row.instrumentKey ? 1 : 0.9;
    return {
      symbol: row.symbol,
      sector: row.sector,
      instrument_key: row.instrumentKey,
      alpha_z: Number(alphaZ.toFixed(4)),
      residual_15m: Number(row.residual15m.toFixed(4)),
      residual_60m: Number(row.residual60m.toFixed(4)),
      volume_surprise: Number(row.volumeSurprise.toFixed(4)),
      sector_strength: row.sectorProxyUsed ? null : Number(row.sectorStrength.toFixed(4)),
      persistence: persistence === 1 ? 'high' : 'low',
      liquidity_ok: liquidityOk,
      liquidity_verified: liquidityVerified,
      liquidity_reason: spreadGate.reason,
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
        sector_strength_z: zSector[index] === null ? null : Number(zSector[index].toFixed(4)),
        sector_proxy_used: row.sectorProxyUsed,
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
    const spreadGate = spreadWithinLimit(row.spreadBps, maximumSpreadBps);
    const liquidityOk = Boolean(row.minimumLiquidity) && spreadGate.ok;
    const liquidityVerified = Boolean(row.minimumLiquidity) && spreadGate.verified;
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
      sector_strength: row.sectorProxyUsed ? null : Number(row.sectorStrength.toFixed(4)),
      liquidity_ok: liquidityOk,
      liquidity_verified: liquidityVerified,
      liquidity_reason: spreadGate.reason,
      signal_quality: preliminarySignalQuality({ alphaZ: anomalyScore, persistence: directionalConfirmation, volumeSurprise: row.volumeSurprise, liquidityOk, dataCoverage: row.instrumentKey ? 1 : 0.9 }),
      empirical_confidence: { status: 'unvalidated', score: null, comparable_observations: 0 },
      factors: {
        volume_surprise_z: Number(volumeZ[index].toFixed(4)),
        absolute_residual_15m_z: Number(Math.abs(residualZ[index]).toFixed(4)),
        spread_bps: row.spreadBps,
        directional_confirmation: directionalConfirmation,
        sector_proxy_used: row.sectorProxyUsed,
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
    const spreadGate = spreadWithinLimit(spreadBps, maximumSpreadBps);
    const liquidityOk = row.minimumLiquidity !== false && spreadGate.ok;
    const liquidityVerified = row.minimumLiquidity !== false && spreadGate.verified;
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
      factors: { opening_high: row.openingHigh, opening_low: row.openingLow, opening_range_pct: Number(row.rangePct.toFixed(4)), breakout_pct: Number(row.breakoutPct.toFixed(4)), breakout_z: Number(breakoutZ[index].toFixed(4)), volume_surprise_z: Number(volumeZ[index].toFixed(4)), spread_bps: row.spreadBps, sector_proxy_used: row.sectorProxyUsed },
    };
  }).sort((left, right) => right.alpha_z - left.alpha_z).map((row, index) => ({ ...row, rank: index + 1 }));
  return { engine: ALPHA_ENGINES.OPENING_RANGE, as_of: new Date(asOf).toISOString(), research_only: true, execution_enabled: false, universe_size: signals.length, config: { openingMinutes: 15, breakoutBufferPct, minimumVolumeRatio, minimumRangePct, maximumRangePct, maximumSpreadBps }, signals };
}

export function evaluateIntradayMeanReversion(snapshots, {
  minimumUniverse = 10,
  minimumResidualShockPct = 0.50,
  minimumShockZ = 1.25,
  maximumBenchmarkMovePct = 0.75,
  maximumVolumeRatio = 2.50,
  maximumSpreadBps = 35,
  asOf = new Date().toISOString(),
} = {}) {
  if (!Array.isArray(snapshots) || snapshots.length < minimumUniverse) {
    throw new Error(`Intraday mean reversion requires at least ${minimumUniverse} simultaneous instruments.`);
  }
  const rows = snapshots.map(normalizeSnapshot);
  if (new Set(rows.map((row) => row.symbol)).size !== rows.length) throw new Error('Snapshot symbols must be unique.');
  const residualZ = zScores(rows, 'residual15m');
  const signals = rows.map((row, index) => {
    const shockZ = residualZ[index];
    const spreadGate = spreadWithinLimit(row.spreadBps, maximumSpreadBps);
    const liquidityOk = Boolean(row.minimumLiquidity) && spreadGate.ok;
    const liquidityVerified = Boolean(row.minimumLiquidity) && spreadGate.verified;
    const regimeOk = Math.abs(row.benchmarkReturn15m) <= maximumBenchmarkMovePct;
    const volumeOk = row.volumeSurprise <= maximumVolumeRatio;
    const shockDominates = Math.abs(row.residual15m) >= Math.max(minimumResidualShockPct, Math.abs(row.residual60m) * 0.60);
    const statisticallyExtreme = Math.abs(shockZ) >= minimumShockZ;
    const candidate = liquidityOk && regimeOk && volumeOk && shockDominates && statisticallyExtreme;
    const direction = row.residual15m < 0 ? 'positive' : 'negative';
    const alphaZ = Math.abs(shockZ);
    return {
      symbol: row.symbol, sector: row.sector, instrument_key: row.instrumentKey,
      alpha_z: Number(alphaZ.toFixed(4)), residual_15m: Number(row.residual15m.toFixed(4)), residual_60m: Number(row.residual60m.toFixed(4)),
      volume_surprise: Number(row.volumeSurprise.toFixed(4)), sector_strength: Number(row.sectorStrength.toFixed(4)), liquidity_ok: liquidityOk,
      classification: !liquidityOk ? 'filtered' : !regimeOk ? 'market_stress_filtered' : !volumeOk ? 'event_volume_filtered' : !shockDominates ? 'trend_filtered' : candidate ? (direction === 'positive' ? 'negative_shock_rebound_candidate' : 'positive_shock_pullback_candidate') : 'neutral',
      signal_quality: preliminarySignalQuality({ alphaZ, persistence: shockDominates ? 1 : 0, volumeSurprise: Math.min(row.volumeSurprise, 2), liquidityOk: liquidityOk && regimeOk && volumeOk, dataCoverage: row.instrumentKey ? 1 : 0.9 }),
      empirical_confidence: { status: 'unvalidated', score: null, comparable_observations: 0 },
      factors: { residual_15m_z: Number(shockZ.toFixed(4)), shock_dominance: Number((Math.abs(row.residual15m) / Math.max(Math.abs(row.residual60m), 0.0001)).toFixed(4)), benchmark_return_15m: row.benchmarkReturn15m, volume_surprise: Number(row.volumeSurprise.toFixed(4)), spread_bps: row.spreadBps, sector_proxy_used: row.sectorProxyUsed },
    };
  }).sort((left, right) => right.alpha_z - left.alpha_z).map((row, index) => ({ ...row, rank: index + 1 }));
  return { engine: ALPHA_ENGINES.MEAN_REVERSION, as_of: new Date(asOf).toISOString(), research_only: true, execution_enabled: false, universe_size: signals.length, config: { minimumResidualShockPct, minimumShockZ, maximumBenchmarkMovePct, maximumVolumeRatio, maximumSpreadBps }, signals };
}

export function evaluateDerivativesPositioning(snapshots, {
  minimumUniverse = 10,
  minimumPriceMovePct = 0.25,
  minimumOiChangePct = 1,
  maximumSpreadBps = 50,
  asOf = new Date().toISOString(),
} = {}) {
  if (!Array.isArray(snapshots) || snapshots.length < minimumUniverse) {
    throw new Error(`Derivatives positioning requires at least ${minimumUniverse} simultaneous contracts.`);
  }
  const rows = snapshots.map((row, index) => {
    const symbol = String(row?.symbol || '').trim().toUpperCase();
    const sector = String(row?.sector || '').trim().toUpperCase();
    const priceReturn15m = finite(row.priceReturn15m ?? row.price_return_15m);
    const oiChange15m = finite(row.oiChange15m ?? row.oi_change_15m);
    const openInterest = finite(row.openInterest ?? row.open_interest);
    const spreadBps = finite(row.spreadBps ?? row.spread_bps);
    const impliedVolatility = finite(row.impliedVolatility ?? row.implied_volatility);
    if (!/^[A-Z0-9&-]+$/.test(symbol) || !sector || ![priceReturn15m, oiChange15m, openInterest].every(Number.isFinite) || openInterest <= 0) throw new Error(`Invalid derivatives snapshot at index ${index}.`);
    return { symbol, sector, instrumentKey: String(row.instrumentKey || row.instrument_key || '').trim() || null, priceReturn15m, oiChange15m, openInterest, spreadBps, impliedVolatility, minimumLiquidity: row.minimumLiquidity !== false };
  });
  if (new Set(rows.map((row) => row.symbol)).size !== rows.length) throw new Error('Snapshot symbols must be unique.');
  const priceZ = zScores(rows, 'priceReturn15m');
  const oiZ = zScores(rows, 'oiChange15m');
  const signals = rows.map((row, index) => {
    const spreadGate = spreadWithinLimit(row.spreadBps, maximumSpreadBps);
    const liquidityOk = Boolean(row.minimumLiquidity) && spreadGate.ok;
    const liquidityVerified = Boolean(row.minimumLiquidity) && spreadGate.verified;
    const material = Math.abs(row.priceReturn15m) >= minimumPriceMovePct && Math.abs(row.oiChange15m) >= minimumOiChangePct;
    const classification = !liquidityOk ? 'filtered' : !material ? 'neutral'
      : row.priceReturn15m > 0 && row.oiChange15m > 0 ? 'long_buildup_candidate'
        : row.priceReturn15m < 0 && row.oiChange15m > 0 ? 'short_buildup_candidate'
          : row.priceReturn15m > 0 ? 'short_covering_candidate' : 'long_unwinding_candidate';
    const alphaZ = (0.45 * Math.abs(priceZ[index])) + (0.55 * Math.abs(oiZ[index]));
    return {
      symbol: row.symbol, sector: row.sector, instrument_key: row.instrumentKey, alpha_z: Number(alphaZ.toFixed(4)),
      residual_15m: Number(row.priceReturn15m.toFixed(4)), residual_60m: 0, volume_surprise: 1, sector_strength: 0, liquidity_ok: liquidityOk, classification,
      signal_quality: preliminarySignalQuality({ alphaZ, persistence: material ? 1 : 0, volumeSurprise: 1, liquidityOk, dataCoverage: row.instrumentKey ? 1 : 0.9 }),
      empirical_confidence: { status: 'unvalidated', score: null, comparable_observations: 0 },
      factors: { price_return_15m: Number(row.priceReturn15m.toFixed(4)), oi_change_15m: Number(row.oiChange15m.toFixed(4)), open_interest: row.openInterest, price_return_z: Number(priceZ[index].toFixed(4)), oi_change_z: Number(oiZ[index].toFixed(4)), implied_volatility: row.impliedVolatility, spread_bps: row.spreadBps },
    };
  }).sort((left, right) => right.alpha_z - left.alpha_z).map((row, index) => ({ ...row, rank: index + 1 }));
  return { engine: ALPHA_ENGINES.DERIVATIVES, as_of: new Date(asOf).toISOString(), research_only: true, execution_enabled: false, universe_size: signals.length, config: { minimumPriceMovePct, minimumOiChangePct, maximumSpreadBps }, signals };
}

export const LIVE_ALPHA_ROADMAP = Object.freeze([
  { engine: ALPHA_ENGINES.MOMENTUM, status: 'implemented' },
  { engine: ALPHA_ENGINES.VOLUME_ANOMALY, status: 'implemented' },
  { engine: ALPHA_ENGINES.OPENING_RANGE, status: 'implemented' },
  { engine: ALPHA_ENGINES.MEAN_REVERSION, status: 'implemented' },
  { engine: ALPHA_ENGINES.DERIVATIVES, status: 'implemented_requires_derivative_universe' },
]);
