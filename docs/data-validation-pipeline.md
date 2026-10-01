# Automatic NIFTY evidence validation

The enabled supervisor resumes version-2 year downloads, observes Groww independently, checks feed freshness every minute, compares matching spot timestamps hourly, and starts chronological research tests after the Upstox download pass finishes. It never sends broker orders or changes strategy rules, calendar reviews, routing, allocations or unresolved positions.

## Data integrity
Groww uses seven-calendar-day requests. Invalid OHLC, timestamps and conflicting chunks remain gaps; rejected candles are preserved compressed. Authentication, rate limiting, server errors and low disk space stop and retry a worker. Other bad chunks do not block unrelated contracts. Upstox metadata is registered alongside candles for option type, strike, expiry and verified lot size. A finished pass is not proof of complete coverage.

## Tests and paper observation
Nine existing minute strategies use a frozen 75/25 split of observed sessions, next-open fills and base/doubled costs. Completed phases are checkpointed. At least 30 closed trades and positive net P&L in both cost scenarios are required separately in training and validation. This is a research screen, not proof of profitability. Previously inspected dates cannot be called an untouched holdout.

Missing dated event reviews remain blocked. Two original snapshot strategies are replayed separately for the final 30 calendar days with their existing cost model. News needs actual point-in-time logs; price history cannot recreate it. Candles have no bid/ask depth and cannot validate one-second execution.

Candidate readiness is rechecked every minute. Both current feeds must be fresh, paper trading enabled, and comparison free of flagged Upstox gaps and spot discrepancies above 5 basis points. Outside market hours readiness is withheld. Candidates are observed in existing paper accounts, without resetting or allocating live capital. Agent states and recent decisions are recorded every minute for 365 days. Same-volume archives are not independently verified disaster-recovery backups.

The private admin panel displays freshness, comparison, phase, compact results and gaps. Detailed trades and watchlist decisions remain on the persistent volume. Failed experiments expose a status for investigation rather than endlessly rerunning.
