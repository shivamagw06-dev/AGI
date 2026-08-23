import {
  LIVE_ALPHA_STRATEGIES,
  signedSignalScore,
} from './liveAlphaSignalModel.js';

export const ENGINE_PLAIN = Object.freeze({
  cross_sectional_momentum_v1: {
    label: 'Leadership',
    plain: 'Stocks moving more strongly than similar companies.',
    technical: 'Cross-sectional residual momentum versus sector over 15m/60m windows.',
  },
  volume_liquidity_anomaly_v1: {
    label: 'Activity',
    plain: 'Trading activity is unusually high or low.',
    technical: 'Volume and liquidity versus expected cumulative-volume baselines.',
  },
  opening_range_expansion_v1: {
    label: 'Breakout',
    plain: 'Price has moved beyond its normal early-session range.',
    technical: 'Opening-range expansion with participation and liquidity filters.',
  },
  intraday_mean_reversion_v1: {
    label: 'Dislocation',
    plain: 'A stock has made an unusual short-term move that may be separating from its recent behaviour.',
    technical: 'Intraday mean-reversion / shock residual after trend and event-volume filters.',
  },
  derivatives_positioning_v1: {
    label: 'Positioning',
    plain: 'Futures and open-interest behaviour is changing relative to the cash market.',
    technical: 'Derivatives positioning versus cash with coverage requirements.',
  },
});

function intensityFromActiveShare(active, evaluated) {
  if (!evaluated) return { key: 'none', label: 'Unavailable', bars: 0 };
  const share = active / Math.max(1, evaluated);
  if (share >= 0.08) return { key: 'strong', label: 'Strong', bars: 5 };
  if (share >= 0.05) return { key: 'elevated', label: 'Elevated', bars: 4 };
  if (share >= 0.03) return { key: 'moderate', label: 'Moderate', bars: 3 };
  if (share > 0) return { key: 'low', label: 'Low', bars: 2 };
  return { key: 'quiet', label: 'Quiet', bars: 1 };
}

export function buildMarketBehaviorRows(allRows, strategyHealth = {}, isFresh = false) {
  return LIVE_ALPHA_STRATEGIES.map(([engine]) => {
    const meta = ENGINE_PLAIN[engine];
    const active = allRows.filter((row) => row.strategies[engine]?.direction).length;
    const evaluated = Number(strategyHealth[engine]?.stored_signals) || 0;
    const health = strategyHealth[engine]?.status || 'never_run';
    const intensity = !isFresh && evaluated
      ? { key: 'stale', label: 'Stale', bars: Math.min(5, Math.max(1, Math.round((active / Math.max(1, evaluated)) * 20))) }
      : intensityFromActiveShare(active, evaluated || active);
    return {
      engine,
      label: meta.label,
      plain: meta.plain,
      technical: meta.technical,
      active: isFresh ? active : 0,
      evaluated,
      health,
      intensity,
    };
  });
}

function cellMark(activeCount, totalDirectional) {
  if (!totalDirectional) return { mark: '·', tone: 'empty', label: 'No evidence' };
  const share = activeCount / totalDirectional;
  if (share >= 0.12) return { mark: '+++', tone: 'strong', label: 'Strong' };
  if (share >= 0.07) return { mark: '++', tone: 'above', label: 'Above normal' };
  if (share >= 0.03) return { mark: '+', tone: 'normal', label: 'Supportive' };
  if (share > 0) return { mark: '−', tone: 'below', label: 'Below normal' };
  return { mark: '−−', tone: 'weak', label: 'Weak' };
}

/**
 * Sector × behaviour matrix from current canonical rows.
 * Returns unavailable when fewer than 3 distinct sectors have directional evidence.
 */
export function buildMarketMap(allRows, { isFresh = false } = {}) {
  if (!isFresh) {
    return { available: false, reason: 'Sector aggregation awaits fresh Live Alpha evidence.', sectors: [], engines: LIVE_ALPHA_STRATEGIES.map(([engine]) => engine) };
  }
  const engines = LIVE_ALPHA_STRATEGIES.map(([engine]) => engine);
  const bySector = new Map();
  for (const row of allRows) {
    if (!row.active?.length) continue;
    const sector = String(row.sector || '').trim();
    if (!sector || sector === '—') continue;
    const bucket = bySector.get(sector) || Object.fromEntries(engines.map((engine) => [engine, 0]));
    for (const engine of engines) {
      if (row.strategies[engine]?.direction) bucket[engine] += 1;
    }
    bySector.set(sector, bucket);
  }
  if (bySector.size < 3) {
    return { available: false, reason: 'Sector aggregation unavailable — not enough sector-tagged directional evidence.', sectors: [], engines };
  }
  const sectors = [...bySector.entries()]
    .map(([sector, counts]) => {
      const total = engines.reduce((sum, engine) => sum + counts[engine], 0);
      return {
        sector,
        total,
        cells: Object.fromEntries(engines.map((engine) => [engine, cellMark(counts[engine], Math.max(1, total))])),
      };
    })
    .sort((a, b) => b.total - a.total)
    .slice(0, 8);
  return { available: true, reason: null, sectors, engines };
}

function primaryReasonLabel(row) {
  const driver = row.interpretation?.primary_driver;
  if (driver?.engine && ENGINE_PLAIN[driver.engine]) return ENGINE_PLAIN[driver.engine].label;
  if (row.signal_structure === 'CONFLICTING') return 'Conflicting evidence';
  if (!row.active?.length) return 'No active signal';
  return 'Mixed evidence';
}

export function plainSignalDirection(row) {
  if (row.signal_structure === 'CONFLICTING') return { key: 'conflicting', label: 'Conflicting' };
  if (row.composite > 0) return { key: 'positive', label: 'Positive' };
  if (row.composite < 0) return { key: 'negative', label: 'Negative' };
  return { key: 'neutral', label: 'Neutral' };
}

export function evidenceStrengthLabel(confidence) {
  if (confidence === 'SAMPLE-RICH' || confidence === 'HIGH') return 'HIGH';
  if (confidence === 'MEDIUM') return 'MEDIUM';
  if (confidence === 'LOW') return 'LOW';
  return 'UNAVAILABLE';
}

/**
 * Deterministic AGI Live Brief from canonical rows — no LLM, no invented causes.
 */
export function buildLiveBrief(allRows, { isFresh = false, now = new Date() } = {}) {
  const directional = allRows.filter((row) => row.active?.length);
  const clean = directional.filter((row) => row.signal_structure !== 'CONFLICTING');
  const conflicts = directional.filter((row) => row.signal_structure === 'CONFLICTING');
  const positive = clean.filter((row) => row.composite > 0).sort((a, b) => b.composite - a.composite);
  const negative = clean.filter((row) => row.composite < 0).sort((a, b) => a.composite - b.composite);
  const multi = directional.filter((row) => row.active.length >= 2);

  const behaviourCounts = Object.fromEntries(
    LIVE_ALPHA_STRATEGIES.map(([engine]) => [engine, directional.filter((row) => row.strategies[engine]?.direction).length]),
  );
  const dominantBehaviours = LIVE_ALPHA_STRATEGIES
    .map(([engine]) => ({ engine, label: ENGINE_PLAIN[engine].label, count: behaviourCounts[engine] }))
    .filter((row) => row.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 3);

  const sectorScores = new Map();
  for (const row of clean) {
    const sector = String(row.sector || '').trim();
    if (!sector || sector === '—') continue;
    const current = sectorScores.get(sector) || { sector, score: 0, n: 0 };
    current.score += row.composite;
    current.n += 1;
    sectorScores.set(sector, current);
  }
  const rankedSectors = [...sectorScores.values()]
    .map((row) => ({ ...row, avg: row.score / row.n }))
    .sort((a, b) => b.avg - a.avg);
  const strongestSectors = rankedSectors.filter((row) => row.avg > 0).slice(0, 2);
  const weakestSectors = rankedSectors.filter((row) => row.avg < 0).sort((a, b) => a.avg - b.avg).slice(0, 2);

  const highEvidence = directional.filter((row) => row.confidence === 'HIGH' || row.confidence === 'SAMPLE-RICH').length;
  const evidenceStrength = !isFresh
    ? 'STALE'
    : highEvidence >= 8 || multi.length >= 5
      ? 'HIGH'
      : highEvidence >= 3 || multi.length >= 2
        ? 'MEDIUM'
        : directional.length
          ? 'LOW'
          : 'UNAVAILABLE';

  const notable = [
    ...positive.slice(0, 2).map((row) => ({
      symbol: row.symbol,
      direction: 'up',
      line: `${ENGINE_PLAIN[row.interpretation.primary_driver?.engine]?.label || 'Signal'} · ${row.active.length} engine${row.active.length === 1 ? '' : 's'}`,
    })),
    ...negative.slice(0, 1).map((row) => ({
      symbol: row.symbol,
      direction: 'down',
      line: `${ENGINE_PLAIN[row.interpretation.primary_driver?.engine]?.label || 'Signal'} · weaker vs peers`,
    })),
  ];

  let headline;
  if (!isFresh) headline = 'Displayed Live Alpha evidence is historical. Fresh evaluation resumes in the next live session.';
  else if (!directional.length) headline = 'No qualifying Live Alpha behaviours are active yet.';
  else if (positive.length > negative.length * 1.5) headline = 'Market activity leans positive across Live Alpha behaviours.';
  else if (negative.length > positive.length * 1.5) headline = 'Market activity leans negative across Live Alpha behaviours.';
  else if (conflicts.length >= 3) headline = 'Live Alpha evidence is mixed, with several conflicting multi-engine readings.';
  else headline = 'Market activity is mixed across Live Alpha behaviours.';

  const sectorLine = (() => {
    if (!strongestSectors.length && !weakestSectors.length) return null;
    const strong = strongestSectors.map((row) => row.sector).join(' and ');
    const weak = weakestSectors.map((row) => row.sector).join(' and ');
    if (strong && weak) return `${strong} show the strongest positive behaviour. ${weak} ${weakestSectors.length === 1 ? 'is' : 'are'} weaker than the broader set.`;
    if (strong) return `${strong} show the strongest positive behaviour in the current evidence set.`;
    return `${weak} ${weakestSectors.length === 1 ? 'is' : 'are'} weaker than the broader set.`;
  })();

  const timeLabel = now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' });

  return {
    generated_at: now.toISOString(),
    time_label: `${timeLabel} IST`,
    headline,
    sector_line: sectorLine,
    dominant_behaviours: dominantBehaviours,
    strongest_sectors: strongestSectors.map((row) => row.sector),
    weakest_sectors: weakestSectors.map((row) => row.sector),
    top_positive: positive.slice(0, 5).map((row) => ({ symbol: row.symbol, sector: row.sector, strength: Math.abs(row.composite), reason: primaryReasonLabel(row) })),
    top_negative: negative.slice(0, 5).map((row) => ({ symbol: row.symbol, sector: row.sector, strength: Math.abs(row.composite), reason: primaryReasonLabel(row) })),
    conflicts: conflicts.slice(0, 5).map((row) => ({ symbol: row.symbol, sector: row.sector, strength: Math.abs(row.composite) })),
    notable,
    breadth: {
      active: isFresh ? directional.length : 0,
      positive: isFresh ? positive.length : 0,
      negative: isFresh ? negative.length : 0,
      multi: isFresh ? multi.length : 0,
      conflicts: isFresh ? conflicts.length : 0,
      high_evidence: isFresh ? highEvidence : 0,
    },
    evidence_strength: evidenceStrength,
    is_fresh: isFresh,
  };
}

export function marketStateFromBrief(brief) {
  if (!brief?.is_fresh) return { label: 'Historical', tone: 'stale', detail: 'Awaiting fresh evaluation' };
  const { positive = 0, negative = 0, active = 0 } = brief.breadth || {};
  if (!active) return { label: 'Quiet', tone: 'neutral', detail: 'No active signals' };
  if (positive > negative * 1.5) return { label: 'Positive', tone: 'positive', detail: 'Broad supportive tilt' };
  if (negative > positive * 1.5) return { label: 'Negative', tone: 'negative', detail: 'Broad weakening tilt' };
  return { label: 'Mixed', tone: 'warning', detail: 'Balanced / conflicting tilt' };
}

export function filterRadarRows(rows, filter, { search = '', sector = '' } = {}) {
  const query = search.trim().toUpperCase();
  const sectorQuery = sector.trim().toUpperCase();
  return rows.filter((row) => {
    if (query && !String(row.symbol || '').toUpperCase().includes(query)) return false;
    if (sectorQuery && !String(row.sector || '').toUpperCase().includes(sectorQuery)) return false;
    if (filter === 'all') return true;
    if (filter === 'positive') return row.composite > 0 && row.signal_structure !== 'CONFLICTING';
    if (filter === 'negative') return row.composite < 0 && row.signal_structure !== 'CONFLICTING';
    if (filter === 'high') return row.confidence === 'HIGH' || row.confidence === 'SAMPLE-RICH';
    if (filter === 'multi') return row.active?.length >= 2 && row.signal_structure !== 'CONFLICTING';
    if (filter === 'conflicting') return row.signal_structure === 'CONFLICTING';
    if (LIVE_ALPHA_STRATEGIES.some(([engine]) => engine === filter)) return Boolean(row.strategies[filter]?.direction);
    return true;
  });
}

export function sortRadarRows(rows, sort) {
  const copy = [...rows];
  if (sort === 'newest') return copy.sort((a, b) => Date.parse(b.newest) - Date.parse(a.newest));
  if (sort === 'confirmed') return copy.sort((a, b) => b.active.length - a.active.length || Math.abs(b.composite) - Math.abs(a.composite));
  if (sort === 'change') return copy.sort((a, b) => Math.abs(b.composite) - Math.abs(a.composite));
  return copy.sort((a, b) => Math.abs(b.composite) - Math.abs(a.composite));
}

export function radarReason(row) {
  return primaryReasonLabel(row);
}

export { primaryReasonLabel };
