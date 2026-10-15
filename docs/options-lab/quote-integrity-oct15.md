# Paper quote integrity — 15 October 2026

The production journals show spread recovery exits seconds after entry. Code inspection found that any cross-leg timestamp skew above one second immediately latched a halt, although each leg could still be fresh and liquid. The next synchronized basket then forced a recovery exit. This is a confirmed code path, not proof that it caused every historical gap exit.

Live benchmark spreads now wait at most five seconds since the last executable basket when *only* synchronization fails. Marks remain unchanged; no trade is filled at mismatched quotes. Missing/stale/thin/mismatched legs, actual worker gaps and session boundaries retain protective halts. An extended skew still halts and any subsequent recovery remains impaired evidence. Replay keeps the prior immediate-halt behavior. Held exits no longer depend on the availability of an entry-eligible expiry elsewhere in the chain.

Groww startup stages and sanitized exception classes/HTTP codes are persisted. Old connection verification is cleared on a failed new attempt. Verification requires an actual fresh message. A stream with no messages for 120 seconds restarts through the existing five-minute retry supervisor. No automatic failover or order access is introduced.

Yahoo's configured general RSS endpoint returned HTTP404 directly. It remains unavailable and retries at most daily for404/410 instead of every30minutes; temporary failures retain30minute cooldown. An alternative symbol RSS URL returned429, so it was not installed as a purported working replacement. Upstox news remains the existing news-agent input.

Trade journals/balances are not rewritten. Event calendar review remains mandatory and is not automatically marked clear. Existing recorded losses remain recorded. 96 focused tests passed, including quote-skew recovery, stale/depth failures, near-expiry exits, redacted Groww errors and Yahoo backoff.
