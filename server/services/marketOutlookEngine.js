/**
 * AGI Market Outlook Engine
 * Proprietary scoring model — classifies market sentiment from multi-factor inputs.
 * Designed to accept data from Groww (primary) with fallback providers.
 */

const OUTLOOK_LEVELS = [
  { key: 'strong_bullish', label: 'Strong Bullish', scoreMin: 80 },
  { key: 'bullish', label: 'Bullish', scoreMin: 65 },
  { key: 'neutral', label: 'Neutral', scoreMin: 45 },
  { key: 'bearish', label: 'Bearish', scoreMin: 30 },
  { key: 'strong_bearish', label: 'Strong Bearish', scoreMin: 0 },
];

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function classifyOutlook(score) {
  for (const level of OUTLOOK_LEVELS) {
    if (score >= level.scoreMin) return level;
  }
  return OUTLOOK_LEVELS[OUTLOOK_LEVELS.length - 1];
}

function momentumLabel(score) {
  if (score >= 75) return 'Strong';
  if (score >= 55) return 'Moderate';
  if (score >= 40) return 'Weak';
  return 'Negative';
}

function riskLabel(vix, score) {
  const v = num(vix);
  if (v <= 0) return score >= 60 ? 'Low' : score >= 45 ? 'Moderate' : 'Elevated';
  if (v < 13) return 'Low';
  if (v < 18) return 'Moderate';
  if (v < 25) return 'Elevated';
  return 'High';
}

function volatilityLabel(vix) {
  const v = num(vix);
  if (v <= 0) return 'Moderate';
  if (v < 13) return 'Low';
  if (v < 18) return 'Moderate';
  if (v < 25) return 'High';
  return 'Extreme';
}

/**
 * @param {object} inputs
 * @param {object} inputs.indices — { nifty50, bankNifty, sensex, vix, giftNifty }
 * @param {object} inputs.breadth — { gainers, losers, ratio }
 * @param {object} inputs.commodities — { usdInr, gold, brent }
 * @param {object} inputs.sectors — top sector info
 */
export function computeMarketOutlook(inputs = {}) {
  const reasons = [];
  let score = 50;

  const nifty = num(inputs.indices?.nifty50?.percentChange);
  const bank = num(inputs.indices?.bankNifty?.percentChange);
  const vix = num(inputs.indices?.vix?.price ?? inputs.indices?.vix?.value);
  const vixChange = num(inputs.indices?.vix?.percentChange);

  // Nifty trend
  if (nifty > 0.5) {
    score += 12;
    reasons.push({ type: 'positive', text: 'Nifty 50 trending higher' });
  } else if (nifty > 0) {
    score += 6;
    reasons.push({ type: 'positive', text: 'Nifty 50 in positive territory' });
  } else if (nifty < -0.5) {
    score -= 12;
    reasons.push({ type: 'negative', text: 'Nifty 50 under pressure' });
  } else if (nifty < 0) {
    score -= 6;
    reasons.push({ type: 'negative', text: 'Nifty 50 slightly weak' });
  }

  // Bank Nifty — often leads sentiment
  if (bank > 0.6) {
    score += 10;
    reasons.push({ type: 'positive', text: 'Strong Bank Nifty performance' });
  } else if (bank > 0) {
    score += 4;
  } else if (bank < -0.6) {
    score -= 10;
    reasons.push({ type: 'negative', text: 'Bank Nifty dragging indices' });
  }

  // VIX — inverse sentiment
  if (vix > 0 && vix < 14) {
    score += 8;
    reasons.push({ type: 'positive', text: 'Low VIX — calm market conditions' });
  } else if (vix >= 14 && vix < 20) {
    score += 0;
  } else if (vix >= 20) {
    score -= 10;
    reasons.push({ type: 'negative', text: 'Elevated VIX signals caution' });
  }

  if (vixChange < -3) {
    score += 4;
    reasons.push({ type: 'positive', text: 'VIX declining — risk appetite improving' });
  } else if (vixChange > 5) {
    score -= 6;
    reasons.push({ type: 'negative', text: 'VIX spiking — hedging demand rising' });
  }

  // Market breadth
  const gainers = num(inputs.breadth?.gainers);
  const losers = num(inputs.breadth?.losers);
  if (gainers > 0 && losers > 0) {
    const ratio = gainers / (gainers + losers);
    if (ratio > 0.6) {
      score += 8;
      reasons.push({ type: 'positive', text: 'Positive market breadth' });
    } else if (ratio < 0.4) {
      score -= 8;
      reasons.push({ type: 'negative', text: 'Weak market breadth' });
    }
  }

  // Global / commodity cues
  const brent = num(inputs.commodities?.brent?.percentChange);
  if (brent > 1) {
    score -= 3;
    reasons.push({ type: 'negative', text: 'Crude oil rising — inflation concern' });
  } else if (brent < -1) {
    score += 2;
  }

  const usdInr = num(inputs.commodities?.usdInr?.percentChange);
  if (usdInr > 0.2) {
    score -= 2;
    reasons.push({ type: 'negative', text: 'Rupee weakening vs USD' });
  }

  score = Math.max(0, Math.min(100, Math.round(score)));
  const outlook = classifyOutlook(score);
  const confidence = Math.min(95, Math.max(55, score + (reasons.length >= 3 ? 5 : 0)));

  const topSector = inputs.sectors?.top?.name || 'Capital Goods';

  return {
    outlook: outlook.label,
    outlookKey: outlook.key,
    confidence,
    momentum: momentumLabel(score),
    risk: riskLabel(vix, score),
    volatility: volatilityLabel(vix),
    topSector,
    marketBreadth: gainers > losers ? 'Positive' : gainers < losers ? 'Negative' : 'Mixed',
    reasons: reasons.slice(0, 5),
    score,
    updatedAt: new Date().toISOString(),
  };
}

export function computeMarketPulse(outlookResult, inputs = {}) {
  const badge =
    outlookResult.outlookKey === 'strong_bullish' || outlookResult.outlookKey === 'bullish'
      ? '🟢'
      : outlookResult.outlookKey === 'strong_bearish' || outlookResult.outlookKey === 'bearish'
        ? '🔴'
        : '🟡';

  return {
    title: 'AGI Market Pulse',
    outlook: outlookResult.outlook,
    outlookBadge: badge,
    confidence: outlookResult.confidence,
    momentum: outlookResult.momentum,
    risk: outlookResult.risk,
    volatility: outlookResult.volatility,
    topSector: outlookResult.topSector,
    marketBreadth: outlookResult.marketBreadth,
    reasons: outlookResult.reasons,
    updatedAt: outlookResult.updatedAt,
    updatedLabel: new Date().toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    }),
  };
}
