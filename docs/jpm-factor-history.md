# India factor research charts — source audit

Source workbook: JPM_India_Equity_Strateg_2026-10-01_5453010.xlsm.
SHA256: 0b0b30980afa1df4c3d137f54ebbeb683f3bce333bf950bf4ede45e5030e612b.

Read cached values without running macros or modifying the source. Extractor: scripts/research/extract-factor-history.py. Data: Factor Performance A and N:R, 4,368 valid daily observations, 2010-01-04 through 2026-09-30. The blank 2009-12-31 baseline and 2010-01-01 #NAME? values are excluded. A synthetic 100 baseline on 2010-01-01 is identified explicitly; it is not an observed return. There are no internal invalid rows in the extracted five series.

## Reconciliation finding

The saved chart references Temp rows 167:329 (2025-12-31 to 2026-08-14). All 163 points for each of the five factors (815 total) reproduce exactly from Temp's saved daily values using geometric compounding. Performance Summary C18:C22 also matches. However, Temp's 2026-08-14 daily returns differ from Factor Performance on the same date. Thus the screenshot is not a consistent representation of the main source table. The website uses the main dated source table throughout; it never splices in cached-chart values.

| Factor | Saved chart Jan–14 Aug 2026 | Main source same window |
|---|---:|---:|
| Momentum | 3.815782% | 2.618031% |
| Value | -7.805881% | -8.473332% |
| Growth | 15.922257% | 15.618069% |
| Quality | -2.946605% | -3.457861% |
| All-Weather | 6.855107% | 4.772124% |

Factor Definitions gives score composition but does not establish full portfolio construction, cost treatment or investability. Consequently the UI calls these research series, not absolute portfolio returns or a verified long-short implementation. No NIFTY 500 benchmark is invented from the workbook's label. Current AGI holdings and Upstox tracking remain separate.

## Range convention

30 days is calendar days; 3/6 months and 1/3/5 years use calendar offsets with month-end clamping, measured back from the source as-of date. Custom dates are bounded by source coverage. Baseline is the last available source date on/before the requested start; observations after that date compound to the last date on/before the end. The actual interval is displayed. All charts share the same interval and initial 100. Missing values are never converted to zero. Data remains a workbook snapshot until a new verified extract is supplied.

## Validation

Extraction asserts unique ascending dates, finite observations, no interior missing rows and exact saved-chart reconciliation. Node tests cover compounding, date boundaries, calendar clamping, source totals and discrepancy preservation. Production build checks frontend integration.
