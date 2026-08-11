export const FORECAST_HORIZONS = Object.freeze(['1d', '5d', '20d']);
export const FEATURE_VERSION = 'agi_point_in_time_v1';
export const MODEL_VERSION = 'agi_probabilistic_baseline_v1';
const SCALE = Object.freeze({ '1d': 0.45, '5d': 1.15, '20d': 2.25 });
const SIGMA = Object.freeze({ '1d': 1.4, '5d': 3.1, '20d': 6.2 });
const number = (value) => value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const round = (value, digits = 4) => Number(value.toFixed(digits));
const mean = (values) => { const clean = values.filter((value) => value != null); return clean.length ? clean.reduce((sum, value) => sum + value, 0) / clean.length : null; };

export function createPointInTimeFeatures(event) {
  if (!event?.id || !event?.symbol || !event?.captured_at) throw new Error('A dated confluence event is required.');
  const live = ['leadership','activity','breakout','dislocation','positioning'].map((key) => number(event[key]));
  const features = {
    fundamental: number(event.fundamental_score), valuation: number(event.valuation_score),
    eod: number(event.eod_confirmation), live: number(event.live_confirmation), catalyst: number(event.catalyst_score),
    leadership: live[0], activity: live[1], breakout: live[2], dislocation: live[3], positioning: live[4],
    research_priority: number(event.research_priority), classification: event.classification, market_regime: event.market_regime || null,
  };
  const scored = Object.values(features).filter((value) => typeof value === 'number').length;
  return { confluence_event_id: event.id, symbol: event.symbol, captured_at: event.captured_at, feature_version: FEATURE_VERSION, market_regime: event.market_regime || null, sector: event.sector || null, features, completeness: round(scored / 11), point_in_time_safe: true, research_only: true };
}

function components(features, horizon) {
  const centered = (value) => value == null ? 0 : (value - 50) / 50;
  const factor = SCALE[horizon] * (0.30*centered(features.fundamental) + 0.25*centered(features.valuation) + 0.20*centered(features.eod) + 0.15*centered(features.live) + 0.10*centered(features.catalyst));
  const regimeMultiplier = /TREND_UP|RISK_ON/i.test(features.market_regime || '') ? 1.12 : /RISK_OFF|TREND_DOWN|EVENT_STRESS/i.test(features.market_regime || '') ? 0.72 : 1;
  const regime = factor * regimeMultiplier;
  const analogue = SCALE[horizon] * centered(features.research_priority) * 0.75;
  return { unconditional: 0, factor: round(factor), regime: round(regime), analogue: round(analogue) };
}

export function generateProbabilisticForecast(snapshot, horizon) {
  if (!FORECAST_HORIZONS.includes(horizon)) throw new Error(`Unsupported forecast horizon: ${horizon}.`);
  const c = components(snapshot.features, horizon), values = Object.values(c);
  const expected = mean(values), signs = values.filter((value) => Math.abs(value) >= 0.01).map(Math.sign);
  const agreement = signs.length ? Math.max(signs.filter((x) => x > 0).length, signs.filter((x) => x < 0).length) / signs.length : 0.5;
  const dispersion = Math.sqrt(mean(values.map((value) => (value - expected) ** 2)) || 0);
  const sigma = SIGMA[horizon] * (1.15 - 0.3 * snapshot.completeness) * (1 + Math.min(0.4, dispersion));
  const probability = clamp(0.5 + expected / (2.5 * sigma), 0.05, 0.95);
  const confidence = clamp(100 * (0.45*snapshot.completeness + 0.35*agreement + 0.20*(1-Math.min(1,dispersion))), 0, 100);
  return {
    confluence_event_id: snapshot.confluence_event_id, symbol: snapshot.symbol, forecast_time: snapshot.captured_at, horizon,
    expected_alpha_pct: round(expected), probability_positive: round(probability),
    p10: round(expected - 1.282*sigma), p25: round(expected - 0.674*sigma), p50: round(expected), p75: round(expected + 0.674*sigma), p90: round(expected + 1.282*sigma),
    confidence: round(confidence, 2), model_agreement: round(agreement), model_version: MODEL_VERSION, feature_version: snapshot.feature_version || FEATURE_VERSION,
    market_regime: snapshot.market_regime, component_forecasts: c,
    explanation: { why: ['Fundamental, valuation, EOD, live, and catalyst evidence are scored separately.','Regime conditioning and historical-state baseline are independent components.'], risks: snapshot.completeness < 0.8 ? ['Feature completeness is below 80%.'] : [], calibrated: false },
    research_only: true,
  };
}

export function settleForecast(forecast, outcome) {
  const actual = number(outcome?.sector_adjusted_alpha_pct); if (actual == null) throw new Error('Completed sector-adjusted outcome is required.');
  const positive = actual > 0, probability = number(forecast.probability_positive);
  return { forecast_id: forecast.id, observed_at: outcome.observed_at, actual_alpha_pct: actual, forecast_error: round(actual - Number(forecast.expected_alpha_pct)), direction_correct: positive === (Number(forecast.expected_alpha_pct) > 0), brier_score: round((probability - (positive ? 1 : 0)) ** 2) };
}
