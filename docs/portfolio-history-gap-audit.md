# Portfolio history gap audit — 2 October 2026

Verified original source tickers in the signed-in Vested portfolio UI. No weights or holdings changed.

| Copied holding | Verified Yahoo ticker | Source evidence |
|---|---|---|
| Heico Corp | HEI | Defense Details company link; Space Tech and Deglobalization allocation image labels |
| Lennar Corp. | LEN | Berkshire allocation image label |
| LIBERTY MEDIA CORP-LIBERTY-C | LLYVK | Berkshire allocation image label; do not substitute FWONK based on the legacy name |
| Madison Square Garden Company | MSGS | Gates allocation image label |

Exact source URLs are recorded in instruments.json. All four Yahoo histories fetched successfully. Recalculated current public API allocations with unchanged methodology. Complete results by 1/3/6/12 months: 25/25/23/22 of 26, up from 20/20/19/18 (18 additional results).

Remaining gaps:
- Alphabet 1Y: PAYP history starts 2026-03-12, LIFE 2026-01-29.
- Digital Cash 6M/1Y: WSE US history starts 2026-05-11. FISV additionally lacks 2025-11-12 in both Yahoo chart endpoints and the displayed history table, confirmed by a focused retry. No interpolation used.
- Space Tech 6M/1Y: SPCX history starts 2026-06-12, HONA 2026-06-15. Parent/predecessor prices are not equivalent holdings.
- US Top10 all periods: source shows only LLY 9.97%, MRK 9.93%, TMO 9.70% and explicitly says investment is required to unlock all allocations. No investment made, no access control bypassed, no unknown weights guessed.

Prices remain cut off at the last completed US session, 2026-10-01. Same-period daily history remains mandatory. Tests: all six portfolioHistory tests passed. Snapshot is manually refreshed; this does not create a live record or a scheduler.
