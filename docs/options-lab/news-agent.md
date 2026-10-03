# Nifty news reaction paper experiment

Version: `nifty-news-reaction-v1`. Added 29 September 2026. Forward-only, private admin dashboard. No live orders, brokerage credentials or order API calls in this module.

## Research basis and limits

- [Upstox News API](https://upstox.com/developer/api-documentation/get-news/) provides seven-day instrument-tagged news with publication timestamps; at most 30 instruments per request. The existing 50-stock collector makes two paginated batches every minute. This is sampled instrument news, not a guaranteed complete macro newswire. Current constituent membership is shown as unverified if its refresh fails.
- [Upstox Analytics Token](https://upstox.com/developer/api-documentation/announcements/analytics-token/) supports News and market data, but cannot place, modify or cancel orders. Existing Render credentials suffice for this paper integration.
- [Market Data Feed V3](https://upstox.com/developer/api-documentation/v3/get-market-data-feed/) supplies quotes to the existing one-second recorder. A one-second check is not a promise of a new exchange tick each second.
- [Federal Reserve research, 2026](https://www.federalreserve.gov/econres/feds/the-effect-of-the-federal-reserve-on-the-stock-market-magnitudes-channels-and-shocks.htm) distinguishes monetary policy surprises and different information channels. This motivates observing price response rather than assigning direction from a word such as “cut.” It does not establish these Nifty rules as profitable.
- [NBER, So Many Jumps, So Few News](https://www.nber.org/papers/w32746) studies rapid price responses around news. This motivates explicit timing/latency evidence; one-minute polling cannot claim to capture the first reaction.
- [Novel and topical business news (author paper)](https://arxiv.org/abs/1507.06477) studies novelty and price/volume response. We implement conservative duplicate rejection, not a trained novelty model.

The parameters below are initial research choices, not empirically optimal estimates. They have not been calibrated to today's trades. No claims about future returns are made. Yahoo RSS remains an attributed reading feed and is not used for this strategy.

## Capture and eligibility

Keep first receipt, original publication and original headline immutable. Changes to provider timestamp/headline mark a revision. Bootstrap results, pre-activation records and first collection after a process restart are not prospective events. A new article is eligible only after successful continuous collection (previous complete successful batch within 180 seconds). No startup news is inserted into past trading history.

At most five minutes between original publication and first receipt. Reject future/inconsistent timestamps. Eligibility expires ten minutes after original publication. Exact headline fingerprints and the same macro topic within 30 minutes are conservatively deduplicated. An event is consumed on candidate creation even if its subsequent fill fails, preventing repeated chasing.

Allow only rule matches describing actual RBI rate/liquidity decisions, Indian CPI/inflation/GDP/industrial-production releases, Fed rate decisions or OPEC supply decisions. Reject predictions, recaps, questions, rumour language, denials and ordinary company stories. These are topic labels, not verification of underlying facts or a sentiment model. Missing an event is preferable to claiming a company headline is index-wide evidence.

## Price confirmation and accounts

Two independent ₹100,000 virtual accounts begin together:

1. **News + price confirmation:** require a fresh eligible event whose receipt preceded the confirmation minute.
2. **Price-only comparison:** same breakout, contract, fees and risk rules without the news requirement.

Build sampled one-minute OHLC from recorded seconds. Each minute must cover its beginning/end and contain at least 55 distinct seconds. Require four contiguous complete minutes. A >5-second feed gap discards incomplete context. A close above the preceding three-minute high by 0.03% signals a call, or below the low by 0.03% signals a put. Reject a preceding range >0.4% or breakout overshoot >0.6%. Recheck the breakout direction before the fill.

Both accounts require a reviewed current-day event calendar and respect its blackout windows and the existing desk pause. Entry hours 09:25–14:30 IST. Exits are monitored once per second, even while new entries are paused or news is unavailable.

Buy one whole lot of the nearest eligible option, within 100 Nifty points and 2–14 calendar days to expiry. Reject stale (>5 seconds), crossed, wide (>5%) or undersized quotes. The option quote must be newer than the signal. Fill at ask plus 0.5% adverse slippage; liquidate at bid minus 0.5%. Use the existing dated NSE/Upstox fee model. If the nearest whole lot exceeds budget, skip instead of selecting distant cheap options.

Per account: maximum ₹5,000 total premium and entry fees; two entries/day; daily loss trigger ₹2,000; 20% premium stop; 40% target; 20-minute holding limit; exits from 15:15 IST; 10-minute cooldown after exit. The daily trigger is not a guaranteed maximum loss. A long option can lose its entire premium; gaps and exit costs can exceed planned stops.

Missing exit data preserves an unresolved position and its last mark. On the first usable quote, simulate a recovery close at that actual current quote, flag the trade `data_gap=true`, and lock further entries for the day. Never fill retrospectively at an unobserved stop. Keep the loss in total P&L and show the impaired-trade count separately.

## Evidence and comparison

Persist the agent alongside quote frames in the same SQLite transaction. Pin held and pending contracts into stream subscriptions. Both accounts have separate paths after skipped entries. Journal source link, original publication, receipt time, bar evidence, signal, option quote timestamp, entry/exit, costs, rule version, exit reason and data quality. Preserve state across restarts; exception isolation leaves existing eleven strategies running.

The dashboard shows both accounts, rejection reasons and journals. It is forward-only and intentionally not included in the existing eleven-strategy historical replay. Current news cannot reconstruct historical knowledge.

Evaluate on a predeclared unseen period, report trade counts and coverage, then net return, drawdown, win rate and expectancy. Report missing-feed periods and recovery trades separately. Price-only versus news-gated differences are descriptive evidence, not causal proof or a guaranteed edge. Do not pick an evaluation end date based on which account happens to lead.
