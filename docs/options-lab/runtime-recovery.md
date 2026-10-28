# Paper runtime recovery — 10 October 2026

Production audit: last processed frame 9 October 15:29:59 IST; three benchmark positions halted; no completed trade dated 9 October in the displayed journals. Mean reversion's last decision was dated 8 October, so that risk message was not proof of a 9 October risk block.

Changes:
- Live legacy and spread benchmarks attempt an explicit data-gap recovery exit at the first eligible fresh recorded quote/basket. Original entries and earlier trades remain. Recovery trades retain adverse slippage, costs, timestamps and an impaired-evidence label. No presumed stop/target fill within the gap. No new entries for that account on the recovery date.
- Spread exit eligibility includes the final two expiry days; entry eligibility remains 2–14 days. Both exit legs must pass existing synchronization, depth, contract-identity and price checks.
- Historical replay retains the original halt behavior (recovery is enabled only by the live stream caller).
- Repeated halt messages no longer evict useful journal decisions. Per-agent evaluation timestamps are shown independently of the last decision.
- Upstox news polls every 120 seconds with persisted exponential error cooldown. Failed coverage remains unavailable. Yahoo switches from the 404 topstories address to general finance RSS with a 30-minute cooldown after errors. Replacement Yahoo returned 429 locally, so restoration remains unverified.

No broker orders or balance resets. Calendar review and entry/risk rules remain. Today is Saturday: production position recovery requires a subsequent open-market fresh quote; expired/unquoted contracts require separate recorded-evidence review. Next session's event-calendar review is still required, and news recovery must be verified with real successful provider responses.
