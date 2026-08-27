# Historical Intelligence Engine (Phase 7.2)

The warehouse stores what happened. This engine explains what it meant — and it
is explicit about where the evidence stops.

- **Package** `intelligence-engine/historical_intelligence/`
- **Ask route** KUL provider `historical_intelligence`
- **Engine API** `/v1/historical-intelligence/*`
- **Acceptance** `intelligence-engine/scripts/historical_intelligence_acceptance_v1.py`

It collects nothing. Every input arrives from the Institutional Data Warehouse.

---

## The problem it solves

Before this engine, "when was Axis Bank cheapest on price to book" returned
today's multiple — the same answer as "is Axis Bank expensive". Every number was
real; the answer addressed a different question.

The failure mode in the other direction is worse. Point a reasoning layer at a
41-point P/B series starting May 2023, tell it to always conclude, and it will
report that the stock is at its cheapest ever. That is a fabricated claim built
entirely from accurate data.

So reasoning here is **coverage-aware**: what may be concluded is decided by what
was observed, before any module runs.

---

## Two gates

### 1. Coverage engine — per metric, not per dataset

Coverage is measured for each metric separately. That distinction is load
bearing: inside one valuation table Axis Bank's price reaches back to 1998 while
its P/B reaches May 2023, because each multiple depends on a different statement
input. A dataset-level answer would claim decades of P/B history that does not
exist.

Every metric reports earliest, latest, observation count, span in years, density
against the cadence the source publishes, gaps, recency and a confidence band.
Confidence comes from coverage — span, density, continuity, recency — not from
how much prose was produced.

Fiscal labels resolve to comparable dates, so `FY07` orders against `2007-03-31`.
Without that, "revenue since 2005" against a series running FY07 to FY26 computed
a zero overlap and the engine declined a question it could largely answer.

### 2. Span guard — what may be claimed

| Verdict | Meaning | May conclude |
|---|---|---|
| `covered` | the asked period sits inside the observed window | yes, including all-time claims |
| `partial_window` | only part of the asked period is observed | yes, restricted to the overlap |
| `outside_window` | the asked period is entirely unobserved | no |
| `no_data` | nothing observed for this metric | no |

Depth is judged at the *start* of the window. A series ending at last month's
close still covers "since 2010"; that trailing gap is freshness, reported
separately rather than demoting a complete history to partial.

An all-time claim requires `covered`. Otherwise the answer is qualified — "within
the observed window only (2023-05-31 to present)" — and says outright that it is
not a statement about the company's full listing history.

---

## The five modules

| Module | Answers | Grounded in |
|---|---|---|
| **Trend** | did it compound, where did it turn, is the change structural | prices, statements, ratios |
| **Historical Valuation** | where does today sit against its own past, did it re-rate | valuation history |
| **Corporate Event Timeline** | what the company did and what the shares did around it | corporate actions, research timeline, prices |
| **Historical Comparison** | who did better, over the window both were observed | any series, two or more companies |
| **Explainability** | what changed, why it mattered, evidence, window, confidence | the module above it |

Trend names inflection points rather than reporting a single average, and
distinguishes a sustained run from a volatile one by how many periods moved with
the overall direction. Valuation separates a re-rating from a fundamental move,
because a multiple that expanded is a source of return that does not repeat.

Comparison only uses the window both companies were observed, and says so.
Ranking a twenty-year record against a three-year one would be a statement about
coverage, not about the businesses.

Events state the move observed around a dated action and stop there: with daily
closes and a dated event, association is what the evidence supports, so the
answer says the warehouse "records the move alongside the event; it does not
establish that the event caused it."

---

## Deferred modules

Declared in the API response so a consumer knows these are absent by design
rather than broken.

| Module | Blocked on |
|---|---|
| Consensus Evolution | more than one consensus snapshot — consensus now appends daily, so this unblocks itself with time |
| Management Evolution | structured CEO, chairman and CFO tenure history |
| Business Evolution | historical segment, product and geography mix |
| Cycle Intelligence | a macro regime series in the warehouse |

Building these on the data available today would mean inventing their inputs.

---

## Ask integration

The planner consults `historical_intelligence` ahead of the raw data providers on
company-shaped questions. The provider returns empty for non-historical
questions, so current-state answers are unaffected.

Intent detection covers historical markers (since, during, over time, trend,
evolution, cheapest, highest, all-time) and extracts the period asked about:
`since 2005`, `over the last 10 years`, `in 2019`, `cheapest ever`, and named
episodes — COVID, the global financial crisis, demonetisation, the taper tantrum,
the dot-com cycle.

---

## What a good answer looks like

```
Observed history: FY07 to FY26. Revenue rose from 5,900 in FY07 to 33,042 in
FY26, compounding at 9.49% a year. The move ran in one direction throughout, up
460% end to end, without a material reversal. 94.7% of periods moved with the
overall direction, which reads as a sustained trend rather than a series of
reversals. Compounding of 9.49% with 94.7% of periods moving the same way is the
signature of a business scaling rather than one recovering. The question asks
about since 2005, and AGIB observes revenue only from FY07 — findings cover
FY07 onward; earlier history is unavailable, so no claim is made about it.
Confidence is high: a long, dense series with few gaps.
```

And when nothing can be concluded, the disclosure *is* the answer:

```
The question asks about the global financial crisis, but AGIB's price history for
THIN only covers 2023-01-28 to present. That period is not observed, so no
conclusion is drawn.
```

---

## Acceptance

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m pytest historical_intelligence/tests -q

INSTITUTIONAL_WAREHOUSE_ROOT=/tmp/wh_acceptance PYTHONPATH=. \
  python3 scripts/historical_intelligence_acceptance_v1.py
```

250 questions across trend, valuation, extremes, events, cycles, single years,
all-time claims and comparison, generated over the companies the warehouse
actually holds.

**A correctly coverage-limited answer counts as correct.** The suite does not
reward confident prose; it hunts for dishonesty:

- a conclusion drawn outside the observed window
- an unqualified all-time claim on a partial window
- an answer that states no observation window
- a chronology error
- history attributed to the wrong company

Current result: **250/250, zero honesty violations** — 224 answers carrying
reasoning, 28 correctly coverage-limited.

---

## Known limits

- **Fundamental depth caps the reasoning.** No company yet holds ten years of
  statements, so multi-decade fundamental narratives are unavailable regardless
  of how good the reasoning is. That is the Capital IQ historical export.
- **Causation is never asserted.** The engine reports association between events
  and price moves; establishing cause needs evidence the warehouse does not hold.
- **Named periods are conventions.** "During COVID" resolves to a fixed window,
  not to a company-specific disruption period.
- **Reporting lags are conventions too**, inherited from the warehouse's
  point-in-time reconstruction rather than actual filing dates.
