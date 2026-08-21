# Mis-scaled aggregate money: census and remediation plan

Read-only throughout. Nothing in this document has been applied. No row has been
changed, retired or quarantined.

## What was measured

A complete census of both fundamentals tabs — 69,156 annual and 33,666 quarterly
rows, every row, no sampling.

Three independent signals, kept apart rather than merged into a score:

| signal | meaning | strength |
| --- | --- | --- |
| `ratio` | another row for the same company and period holds the same field 1e6 or 1e7 apart, in a ±10% window | strongest — no business difference is exactly a million-fold |
| `magnitude` | the value cannot be INR million under any reading (>1e8, ~10× India's GDP) | weakest — a heuristic with no witness |
| `source` | the feed documents a unit and the stored magnitude contradicts it | corroborating |

A 10× gap is deliberately **not** a signal: a consolidated figure really can be
ten times its standalone counterpart.

## Findings

| | annual | quarterly |
| --- | ---: | ---: |
| rows | 69,156 | 33,666 |
| two signals agree | **2,385** | 0 |
| ratio only | 549 | 0 |
| magnitude only | 9,497 | 14,957 |
| **rows to examine** | **12,431** (18.0%) | **14,957** (44.4%) |

The quarterly tab has no ratio corroboration at all: where its values are
mis-scaled, there is no correctly scaled peer row for the same company and
period to compare against. Its 14,957 rows rest on the magnitude heuristic
alone and are the weaker finding, despite being the larger number.

### By writer (annual)

| source | unit method | suspect | of |
| --- | --- | ---: | ---: |
| formula_engine | assumed_canonical | 3,618 | 21,821 |
| yahoo_finance_statements | assumed_canonical | 2,472 | 3,086 |
| formula_engine | NEVER_NORMALISED | 2,289 | 2,302 |
| yahoo_finance_statements | NEVER_NORMALISED | 1,506 | 1,523 |
| financial_connector | assumed_canonical | 1,276 | 1,284 |
| financial_connector | NEVER_NORMALISED | 638 | 642 |
| **capital_iq_workbook** | assumed_canonical | **717** | **38,304** |

Capital IQ is the clean population at 1.9%. Every other source is 95–100%
suspect wherever it wrote.

## Which writers bypass normalisation

**None currently do.** 11,230 rows carry no `sys_unit_method` at all, and every
one was last written between 2026-08-02 and 2026-08-04. `_stamp_units` landed in
`3a3f6188d` on 2026-08-04. Nothing has bypassed the pipeline since; stamped rows
run to today. That population is closed.

## Where new mis-scaled rows still come from

The live source is not a bypass. It is `resolve_unit` falling through.

A feed with no entry in `units.SOURCE_DEFAULT_UNIT` is treated as already
canonical, and its raw rupees are stored in a column meaning INR million. Two
feeds are in that state and both created such rows on 2026-08-21:

- `earnings_intelligence_p21` — 5,019 of 5,129 rows created that day
- `financial_connector` — 1,036 of 1,047

Example: 360ONE FY2027Q3 revenue stored as 7,598,300,000 INR million. Read as
rupees it is ₹759.83 crore, which is an ordinary quarterly revenue. The number
is right; the column it sits in is wrong by a million.

`free_cash_flow` is the most-named annual field (8,121 rows touched today),
because the formula engine computes it from mis-scaled inputs and writes the
error into a derived column. The corruption spreads without new bad input.

## Remediation plan

Every step names exact row ids and is reversible. **None have been run.**

### Step 0 — establish the two undocumented units (blocking)

Neither `earnings_intelligence_p21` nor `financial_connector` has a documented
unit. Adding one on the assumption that it is rupees repeats the original
mistake in the opposite direction. Establish each from vendor documentation or
a response payload, not from the stored values.

Until this is done nothing else should run.

### Step 1 — enable the guard in report mode

`scale_guard` defaults to `off`. Set `report`: it counts what it would have
isolated and stores everything. Watch for a week. No behaviour changes.

### Step 2 — add the SOURCE_DEFAULT_UNIT entries

Once step 0 establishes the units. This stops new mis-scaled rows at the source.
Forward-only — it does not touch stored rows. Reversible by removing the entry.

### Step 3 — guard to isolate mode

New implausible rows go to quarantine rather than the tab. Reversible by
returning the mode to `report`.

### Step 4 — correct stored rows, highest confidence first

Only the 2,385 annual rows where two signals agree. Multiply the named fields by
1e-6, recording every row id and prior value in the run tables from PR #774, so
the operation reverses against exactly the rows it touched.

The 549 ratio-only rows follow after review. The 24,454 magnitude-only rows
should **not** be corrected in bulk — one heuristic is not enough to justify
rewriting a financial value, and the quarterly tab is entirely in this category.

### Step 5 — recompute derived columns

`free_cash_flow` and `book_value` are computed from the corrected inputs, so
they must be recomputed after step 4 rather than corrected directly.

## What this does not establish

Plausibility is validation evidence, not proof of provenance. A row that looks
right may still have come from the wrong feed, and a row named here is a row to
examine. In particular, the 717 suspect Capital IQ rows are not evidence that
Capital IQ is unreliable — at 1.9% against 95–100% elsewhere, they are more
likely rows another feed overwrote.
