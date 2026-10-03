/**
 * Generate editorial summary from calculated intelligence — AI explains, never decides.
 * Template-based; swap for GPT/Perplexity when PERPLEXITY_KEY is set.
 */

export function generateAgiSummary(intelligence) {
  const {
    outlook = 'Neutral',
    momentum = 'Moderate',
    marketBreadth = 'Neutral',
    topSector = 'Capital Goods',
    weakestSector = 'FMCG',
    volatility = 'Medium',
    risk = 'Medium',
    confidence = 0,
    openingBias = 'Neutral',
  } = intelligence;

  const parts = [];

  if (outlook.includes('Bullish')) {
    parts.push(`Markets remain ${outlook.toLowerCase()} with ${momentum.toLowerCase()} momentum.`);
  } else if (outlook.includes('Bearish')) {
    parts.push(`Markets show ${outlook.toLowerCase()} conditions with ${momentum.toLowerCase()} momentum.`);
  } else {
    parts.push(`Markets are ${outlook.toLowerCase()} with ${momentum.toLowerCase()} momentum.`);
  }

  if (marketBreadth.includes('Positive')) {
    parts.push(`Market breadth is ${marketBreadth.toLowerCase()}, supporting the current trend.`);
  } else if (marketBreadth.includes('Negative')) {
    parts.push(`Market breadth is ${marketBreadth.toLowerCase()}, suggesting selective participation.`);
  }

  parts.push(
    `${topSector} leads sector performance while ${weakestSector} lags. Volatility is ${volatility.toLowerCase()} and risk is assessed as ${risk.toLowerCase()}.`
  );

  if (openingBias === 'Positive') {
    parts.push('Opening bias remains positive based on global and pre-market cues.');
  } else if (openingBias === 'Negative') {
    parts.push('Opening bias is cautious — monitor global developments.');
  }

  parts.push(`AGI confidence in this assessment: ${confidence}%.`);

  return parts.join(' ');
}
