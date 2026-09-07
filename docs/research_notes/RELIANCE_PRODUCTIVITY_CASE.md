# Reliance Investment Note — Analyst Productivity Case

**Question answered:** Does AGIB make a professional analyst materially more productive?  
*(More valuable than “Does it beat Bloomberg?”)*

**Related:** IB-01 Section G · PAT proves software · IB proves competitive intelligence · this case measures **throughput with quality control**

---

## Measured metrics

| Metric | Result | Notes |
| --- | ---: | --- |
| Time to first draft | **1.09 s** | AGIB Research Writer + Decision soft assemble |
| Factual corrections | **8** | Listed below |
| Completeness (edited) | **78 / 100** | Structure strong; primary evidence thin |
| Blind reviewer quality | **72 / 100** | Provisional rubric on edited note (see below) |
| **Buy-side PM review** | **67 / 100** | See `RELIANCE_PM_REVIEW.md` — *Good first draft. Don't publish.* |
| Confidence level | **0.45 (Low–Medium)** | Capped until filings attached |
| Sources cited | **5** (0 primary filings in-graph) | Honesty over fabrication |
| Publication gates | **FAIL** | 0/7 blocking gates passed — scaffold only |

**Analyst edit time (human):** ~18 minutes to correct, segment-map, and write the investment note  
**Counterfactual (from blank page):** typically 2–4 hours for a first institutional draft of similar scope  
**Implied productivity:** first-draft scaffolding compressed from hours → seconds; **quality still requires an analyst**

---

## Factual corrections log (8)

1. **Wrong sector monitors** — Decision upgrade/downgrade used NIM, NPA, credit costs, liability franchise (bank language) for Reliance.  
2. **Stance conflict** — Engine recommendation `SELL` vs writer `Neutral`; editor resolved to Neutral / Monitor.  
3. **Confidence = 0** with `MEDIUM` conviction — inconsistent; set explicit 0.45 with unknowns.  
4. **Thesis contamination** — Academy-book fragment noise (“price of ice cream”) removed.  
5. **Empty citations** — Writer emitted `citations: []`; added source table + flagged missing filings.  
6. **Missing segment map** — Added O2C / Retail / Jio / New Energy explicitly.  
7. **Bank retail growth condition** — Removed “Retail growth accelerates with controlled risk” as bank-style upgrade.  
8. **No fabricated numbers** — Refused to invent GRM/ARPU/EPS; marked financials evidence-limited.

---

## Completeness rubric (78/100)

| Dimension | Score | Max |
| --- | ---: | ---: |
| Business quality / segments | 16 | 20 |
| Risks | 14 | 15 |
| Valuation framing | 10 | 15 |
| Catalysts | 10 | 10 |
| Evidence / sources | 8 | 20 |
| Missing information honesty | 12 | 10* |
| Scenarios | 8 | 10 |

\*Honesty bonus applied; evidence dimension penalized for missing primary filings.

---

## Blind reviewer quality (provisional 72/100)

Rubric applied to the **edited** note as if debranded (Report X):

| Criterion | Score | Max |
| --- | ---: | ---: |
| Decision usefulness | 14 | 20 |
| Evidence discipline | 16 | 20 |
| Sector correctness | 18 | 20 |
| Clarity / structure | 14 | 20 |
| Actionability of monitors | 10 | 20 |

**Reviewer note:** Usable as a monitoring memo; not yet a Capital IQ–depth initiation. Strength is honesty about gaps; weakness is thin primary evidence.

---

## Confidence

| Layer | Level |
| --- | --- |
| Franchise existence | High |
| Segment economics (this run) | Low |
| Valuation edge | Low |
| Overall file confidence | **0.45** |

---

## Productivity verdict

| Claim | Verdict |
| --- | --- |
| AGIB replaces the analyst | **No** |
| AGIB beats Bloomberg out of the box (this run) | **Not evidenced** |
| AGIB makes a professional analyst materially more productive | **Yes — for first draft & structure**, if corrections are enforced |
| Publication-ready (PM bar) | **No — 67/100 scaffold** |

**Working rule:** Ship AGIB drafts only with an explicit corrections checklist and evidence-gate before distribution.

**Publication rule:** Block distribution until `publication_gates.publication_allowed` is true (thesis bullets, financials, segments, valuation, triggers, evidence links, single recommendation).

---

## What would make this 85+/100 (PM)

1. Investment Thesis (3–5 evidence-backed bullets)  
2. Key Financial Metrics (5-year + TTM)  
3. Segment Economics (O2C, Retail, Jio, New Energy — quantified)  
4. Valuation (SOTP + peers + sensitivity)  
5. Decision Triggers (upgrade / downgrade)  
6. Evidence Links (primary filings per material claim)  
7. Contradiction Check (single recommendation only)  

Encoded in `institutional_grade_benchmark/publication_gates.py`.
