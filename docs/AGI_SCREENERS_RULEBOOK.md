# AGI NSE screener rulebook

These are proposed AGI rules, not copies of any other provider's proprietary screens. A screen is a **shortlist for review**, never a trade signal. Results must carry the latest input date and coverage count. A stock with a missing or stale required input does not qualify.

| Family | Example shortlist rule | Required input | Refresh |
| --- | --- | --- | --- |
| Market activity | Daily gain >= 2% and liquid traded value; show volume and previous close | Current-session quote and volume; use actual traded value when available rather than share count alone | During session and after close |
| Fundamental quality | Positive sales and operating-cash-flow growth, ROE >= 15%, manageable debt, no deteriorating margins | Filed financial statements with fiscal-period and consolidation basis | After a new filing |
| Shareholding | Promoter pledge = 0 and material promoter or institutional ownership increase versus prior quarter | Two dated shareholding disclosures; resolve changes in total shares/corporate actions | After a new filing |
| Technical momentum | RSI(14) between 50 and 70 and rising, MACD line crosses above signal, current volume >= 1.5x its 20-session average | Adjusted daily OHLCV, at least 35 sessions | After each complete session |
| Candlestick confirmation | Bullish engulfing or hammer after a decline, followed by confirmation above the pattern high with above-average volume | Adjusted daily OHLCV, at least 25 sessions | After each complete session |
| Moving-average trend | Close above SMA(50) and SMA(200), SMA(50) > SMA(200); identify a *new* golden cross separately from an existing one | Adjusted closes, at least 200 complete sessions | After each complete session |
| Composite / expert-style | Fundamental quality + trend + adequate liquidity; rank by transparent sub-scores, with no look-ahead data | Complete validated inputs from the relevant families | After the slowest required input is updated |

Shortlist flow: (1) select current NSE common equities; (2) reject missing or stale inputs; (3) apply the selected rule; (4) sort survivors by a stated metric; (5) show the rule values, source dates, and exclusions; (6) inspect news, liquidity, valuation, and risks manually. A screen cannot promise that its survivors will rise.

Current AGI implementation has market activity and published research filters. The remaining families above are specifications, **not implemented screens**. In particular, a daily quote snapshot is not sufficient to compute 200-day averages, candlestick patterns, historical volume ratios, financial growth, or shareholding changes. Do not display a stock shortlist for those families until the underlying data pipeline, corporate-action adjustments, and calculation checks are implemented. Research runs older than seven days are labelled historical on the page and must not be represented as a current shortlist.
